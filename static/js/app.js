// Face-Based Photo Search & Management System - JavaScript

class PhotoSearchApp {
    constructor() {
        this.selectedFaceEncoding = null;
        this.searchResults = [];
        this.currentOperation = null;
        
        this.initializeEventListeners();
        this.loadInitialData();
    }

    initializeEventListeners() {
        // Tab navigation
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Image source toggle
        document.querySelectorAll('input[name="image-source"]').forEach(radio => {
            radio.addEventListener('change', (e) => this.handleImageSourceChange(e.target.value));
        });

        // File upload
        const uploadArea = document.getElementById('file-upload-section');
        const fileInput = document.getElementById('file-input');
        
        uploadArea.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#764ba2';
        });
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.style.borderColor = '#667eea';
        });
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#667eea';
            if (e.dataTransfer.files.length > 0) {
                this.handleFileUpload(e.dataTransfer.files[0]);
            }
        });
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileUpload(e.target.files[0]);
            }
        });

        // Camera capture
        document.getElementById('start-camera-btn').addEventListener('click', () => this.openCameraModal());
        document.getElementById('close-camera-modal').addEventListener('click', () => this.closeCameraModal());
        document.getElementById('capture-btn').addEventListener('click', () => this.capturePhoto());
        document.getElementById('retake-btn').addEventListener('click', () => this.retakePhoto());
        document.getElementById('use-captured-btn').addEventListener('click', () => this.useCapturedPhoto());
        document.getElementById('cancel-camera-btn').addEventListener('click', () => this.closeCameraModal());

        // Search button
        document.getElementById('search-btn').addEventListener('click', () => {
            if (this.selectedFaceEncoding) {
                this.searchSimilarFaces(this.selectedFaceEncoding);
            } else {
                this.showError('Please select a face first');
            }
        });

        // Results toolbar
        document.getElementById('select-all-btn').addEventListener('click', () => this.selectAllResults());
        document.getElementById('clear-selection-btn').addEventListener('click', () => this.clearSelection());
        document.getElementById('copy-btn').addEventListener('click', () => this.showOperationModal('copy'));
        document.getElementById('move-btn').addEventListener('click', () => this.showOperationModal('move'));
        document.getElementById('delete-btn').addEventListener('click', () => this.deleteSelectedFiles());

        // Folder management
        document.getElementById('index-folders-btn').addEventListener('click', () => this.indexFolders());

        // Statistics
        document.getElementById('refresh-stats-btn').addEventListener('click', () => this.loadStats());

        // Modal
        document.getElementById('confirm-operation').addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('Confirm button clicked');
            this.confirmOperation();
        });
        document.getElementById('cancel-operation').addEventListener('click', () => this.hideModal());
        document.getElementById('close-folder-modal').addEventListener('click', () => this.hideModal());
        document.getElementById('select-current-folder-btn').addEventListener('click', () => this.selectCurrentFolder());
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        document.getElementById(`${tabName}-tab`).classList.add('active');

        // Load tab-specific data
        if (tabName === 'manage') {
            this.loadFolders();
            this.loadFolderBrowser();
        } else if (tabName === 'stats') {
            this.loadStats();
        } else if (tabName === 'drive') {
            this.loadDriveStatus();
            this.loadDriveFolders();
            this.loadSyncedFolders();
        }
    }

    async loadInitialData() {
        this.loadStats();
        this.loadDriveStatus();
    }

    async handleFileUpload(file) {
        if (!file.type.startsWith('image/')) {
            this.showError('Please select an image file');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            this.showLoading('Processing image...');

            const response = await fetch('/api/upload_reference', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.faces && data.faces.length > 0) {
                this.displayDetectedFaces(data.faces);
                this.showPreviewImage(file);
                this.showSuccess(`Detected ${data.faces.length} face(s)`);
            } else {
                this.showError('No faces detected in the image');
            }
        } catch (error) {
            this.showError('Error processing image: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    showPreviewImage(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const previewImage = document.getElementById('preview-image');
            previewImage.src = e.target.result;
            document.getElementById('selected-image').style.display = 'block';
        };
        reader.readAsDataURL(file);
    }

    displayDetectedFaces(faces) {
        const facesContainer = document.getElementById('detected-faces');
        facesContainer.innerHTML = faces.map((face, index) => `
            <div class="face-item" onclick="app.selectFace(${index}, this)" data-face-index="${index}">
                <div class="face-thumbnail">
                    <img src="${face.thumbnail}" alt="Face ${index + 1}" onerror="this.style.display='none'">
                </div>
                <span class="face-label">Face ${index + 1}</span>
            </div>
        `).join('');

        document.getElementById('faces-panel').style.display = 'block';
        this.detectedFaces = faces;
    }

    selectFace(index, faceElement) {
        const faceData = this.detectedFaces[index];
        
        // Remove previous selection
        document.querySelectorAll('.face-item').forEach(item => item.classList.remove('selected'));
        
        // Select current face
        faceElement.classList.add('selected');
        this.selectedFaceEncoding = faceData.encoding;
        
        // Enable search button
        document.getElementById('search-btn').disabled = false;
    }

    async searchSimilarFaces(faceEncoding) {
        try {
            this.showLoading('Searching for similar faces...');
            
            // Get selected search source
            const searchSource = document.querySelector('input[name="search-source"]:checked').value;
            
            const response = await fetch('/api/search_faces', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    face_encoding: Array.from(faceEncoding),
                    tolerance: 0.6,
                    min_similarity: 0.55,
                    search_source: searchSource
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.displaySearchResults(data.results, searchSource);
                const sourceText = searchSource === 'local' ? 'Local Storage' : 'Google Drive';
                this.showSuccess(`Found ${data.results.length} similar faces in ${sourceText}`);
            } else {
                this.showError(data.error || 'Search failed');
            }
        } catch (error) {
            this.showError('Error searching faces: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    displaySearchResults(results, searchSource = 'local') {
        const resultsContainer = document.getElementById('search-results');
        
        if (results.length === 0) {
            const sourceText = searchSource === 'local' ? 'Local Storage' : 'Google Drive';
            resultsContainer.innerHTML = `
                <div class="no-results">
                    <i class="fas fa-search"></i>
                    <p>No similar faces found in ${sourceText}</p>
                </div>
            `;
            return;
        }

        resultsContainer.innerHTML = `
            <div class="results-grid">
                ${results.map((result, index) => `
                    <div class="result-item" data-path="${result.file_path}" data-index="${index}" data-source="${searchSource}">
                        <div class="result-checkbox">
                            <input type="checkbox" id="result-${index}">
                        </div>
                        <div class="result-image">
                            <img src="/api/image_thumbnail?path=${encodeURIComponent(result.file_path)}" 
                                 alt="${result.file_name}" 
                                 loading="lazy"
                                 onerror="this.style.display='none'; this.parentElement.classList.add('no-image');">
                            <div class="image-placeholder" style="display: none;">
                                <i class="fas fa-image"></i>
                            </div>
                        </div>
                        <div class="result-info">
                            <div class="result-filename" title="${result.file_name}">${result.file_name}</div>
                            <div class="result-similarity">${Math.round(result.similarity * 100)}% match</div>
                            <div class="result-source">
                                <i class="fas ${searchSource === 'local' ? 'fa-folder' : 'fa-cloud'}"></i>
                                ${searchSource === 'local' ? 'Local' : 'Drive'}
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        
        // Add click handlers for checkboxes
        resultsContainer.querySelectorAll('.result-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.type !== 'checkbox') {
                    const checkbox = item.querySelector('input[type="checkbox"]');
                    checkbox.checked = !checkbox.checked;
                }
                this.updateSelectionUI();
            });
        });
        
        this.updateSelectionUI();
    }

    selectAllResults() {
        document.querySelectorAll('.result-checkbox input').forEach(checkbox => {
            checkbox.checked = true;
            checkbox.closest('.result-item').classList.add('selected');
        });
        this.updateSelectionUI();
    }

    clearSelection() {
        document.querySelectorAll('.result-checkbox input').forEach(checkbox => {
            checkbox.checked = false;
            checkbox.closest('.result-item').classList.remove('selected');
        });
        this.updateSelectionUI();
    }

    updateSelectionUI() {
        const checkboxes = document.querySelectorAll('.result-checkbox input');
        const checkedBoxes = document.querySelectorAll('.result-checkbox input:checked');
        
        // Update visual selection
        checkboxes.forEach(checkbox => {
            const item = checkbox.closest('.result-item');
            if (checkbox.checked) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });

        // Update toolbar buttons
        const hasSelection = checkedBoxes.length > 0;
        document.getElementById('copy-btn').disabled = !hasSelection;
        document.getElementById('move-btn').disabled = !hasSelection;
        document.getElementById('delete-btn').disabled = !hasSelection;
    }

    getSelectedFiles() {
        console.log('=== GETTING SELECTED FILES ===');
        const checkboxes = document.querySelectorAll('.result-checkbox input:checked');
        console.log('Found checkboxes:', checkboxes.length);
        
        const files = Array.from(checkboxes).map((checkbox, index) => {
            const resultItem = checkbox.closest('.result-item');
            const path = resultItem ? resultItem.dataset.path : null;
            console.log(`File ${index + 1}:`, path);
            return path;
        }).filter(path => path !== null && path !== undefined);
        
        console.log('Final selected files:', files);
        return files;
    }

    showOperationModal(operation) {
        const selectedFiles = this.getSelectedFiles();
        if (selectedFiles.length === 0) {
            this.showError('Please select files first');
            return;
        }

        this.currentOperation = { type: operation, files: selectedFiles };
        this.selectedDestination = null;
        
        // Update modal title and button text
        const title = document.getElementById('operation-title');
        const buttonText = document.getElementById('confirm-button-text');
        
        if (operation === 'copy') {
            title.textContent = 'Select Destination to Copy Files';
            buttonText.textContent = 'Copy Files';
        } else if (operation === 'move') {
            title.textContent = 'Select Destination to Move Files';
            buttonText.textContent = 'Move Files';
        }
        
        // Reset UI
        document.getElementById('selected-destination-path').textContent = 'No folder selected';
        document.getElementById('selected-destination-path').className = 'selected-path empty';
        document.getElementById('confirm-operation').disabled = true;
        
        // Show modal and load directory browser
        document.getElementById('folder-modal').style.display = 'flex';
        this.loadModalDirectoryBrowser();
    }

    hideModal() {
        document.getElementById('folder-modal').style.display = 'none';
        this.currentOperation = null;
        this.selectedDestination = null;
        this.currentModalPath = null;
        
        // Reset UI
        document.getElementById('selected-destination-path').textContent = 'No folder selected';
        document.getElementById('selected-destination-path').className = 'selected-path empty';
        document.getElementById('confirm-operation').disabled = true;
    }

    confirmOperation() {
        console.log('=== CONFIRM OPERATION CALLED ===');
        
        console.log('currentOperation:', this.currentOperation);
        console.log('selectedDestination:', this.selectedDestination);
        
        // Validate inputs
        if (!this.currentOperation) {
            console.error('ERROR: No current operation');
            this.showError('No operation selected');
            return;
        }
        
        if (!this.selectedDestination) {
            console.error('ERROR: No destination selected');
            this.showError('Please select a destination folder');
            return;
        }

        if (!this.currentOperation.files || this.currentOperation.files.length === 0) {
            console.error('ERROR: No files in operation');
            this.showError('No files selected');
            return;
        }

        console.log('✓ Validation passed');
        console.log('Operation type:', this.currentOperation.type);
        console.log('Number of files:', this.currentOperation.files.length);
        console.log('Files:', this.currentOperation.files);
        console.log('Destination:', this.selectedDestination);

        this.hideModal();
        this.showLoading(`${this.currentOperation.type}ing files...`);

        const requestData = {
            operation: this.currentOperation.type,
            file_paths: this.currentOperation.files,
            destination: this.selectedDestination
        };
        
        console.log('=== SENDING REQUEST ===');
        console.log('Request data:', requestData);
        
        fetch('/api/file_operations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        })
        .then(response => {
            console.log('=== RESPONSE RECEIVED ===');
            console.log('Response status:', response.status);
            console.log('Response ok:', response.ok);
            
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('=== RESPONSE DATA ===');
            console.log('Full response:', data);
            
            if (data.successful && data.successful > 0) {
                console.log('✓ SUCCESS: Files processed successfully');
                this.showSuccess(`Successfully ${this.currentOperation.type}d ${data.successful} files!`);
                
                // Refresh search results if we're in search view
                if (this.selectedFaceEncoding) {
                    setTimeout(() => {
                        this.searchSimilarFaces(this.selectedFaceEncoding);
                    }, 1000);
                }
            } else if (data.error) {
                console.error('✗ SERVER ERROR:', data.error);
                this.showError(`Error: ${data.error}`);
            } else if (data.failed && data.failed > 0) {
                console.error('✗ OPERATION FAILED:', data.failed, 'files failed');
                this.showError(`Failed to ${this.currentOperation.type} ${data.failed} files`);
            } else {
                console.warn('⚠ NO FILES PROCESSED');
                this.showError('No files were processed');
            }
        })
        .catch(error => {
            console.error('=== REQUEST FAILED ===');
            console.error('Error details:', error);
            this.showError(`Error: ${error.message}`);
        })
        .finally(() => {
            console.log('=== OPERATION COMPLETE ===');
            this.hideLoading();
        });
    }

    async deleteSelectedFiles() {
        const selectedFiles = this.getSelectedFiles();
        if (selectedFiles.length === 0) {
            this.showError('Please select files first');
            return;
        }

        if (!confirm(`Are you sure you want to delete ${selectedFiles.length} files? This action cannot be undone.`)) {
            return;
        }

        this.showLoading('Deleting files...');

        try {
            const response = await fetch('/api/file_operations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    operation: 'delete',
                    file_paths: selectedFiles
                })
            });

            const data = await response.json();
            
            if (data.successful > 0) {
                this.showSuccess(`Deleted ${data.successful} files successfully`);
                // Refresh search results
                if (this.selectedFaceEncoding) {
                    this.searchSimilarFaces(this.selectedFaceEncoding);
                }
            }
            
            if (data.failed > 0) {
                this.showError(`Failed to delete ${data.failed} files`);
            }
        } catch (error) {
            this.showError('Error deleting files: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async loadStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();
            
            document.getElementById('total-images').textContent = data.total_images || 0;
            document.getElementById('total-faces').textContent = data.total_faces || 0;
            document.getElementById('active-folders').textContent = data.active_folders || 0;
            document.getElementById('database-size').textContent = data.database_size || '0 MB';
        } catch (error) {
            this.showError('Error loading statistics: ' + error.message);
        }
    }

    async loadFolders() {
        try {
            const response = await fetch('/api/folders');
            const data = await response.json();
            
            const currentFolderText = document.getElementById('current-folder-text');
            const indexButton = document.getElementById('index-folders-btn');
            
            if (data.folders && data.folders.length > 0) {
                const activeFolder = data.active_folder;
                const folderInfo = data.folder_info.find(info => info.path === activeFolder);
                const imageCount = folderInfo ? folderInfo.image_count : 0;
                
                currentFolderText.innerHTML = `
                    <div style="font-family: monospace; color: #333;">
                        <strong>📁 ${activeFolder}</strong><br>
                        <small style="color: #666;">📸 ${imageCount} images indexed</small>
                    </div>
                `;
                indexButton.disabled = false;
            } else {
                currentFolderText.textContent = 'No directory selected';
                indexButton.disabled = true;
            }
        } catch (error) {
            this.showError('Error loading folders: ' + error.message);
        }
    }

    async loadFolderBrowser(path = null) {
        try {
            const url = path ? `/api/browse_folders?path=${encodeURIComponent(path)}` : '/api/browse_folders';
            const response = await fetch(url);
            const data = await response.json();
            
            if (!data.folders) {
                this.showError('Error loading folder browser');
                return;
            }

            // Update current path display
            document.getElementById('current-path-text').textContent = data.current_path;
            
            // Update folder list
            const folderList = document.getElementById('folder-list');
            folderList.innerHTML = data.folders.map(folder => `
                <div class="folder-list-item ${folder.is_parent ? 'parent' : ''}" 
                     onclick="app.${folder.is_parent ? 'navigateToFolder' : 'handleFolderClick'}('${folder.path}', ${folder.is_parent})">
                    <i class="folder-icon fas ${folder.is_parent ? 'fa-arrow-up' : 'fa-folder'}"></i>
                    <div class="folder-info">
                        <div class="folder-name">${folder.name}</div>
                        ${!folder.is_parent ? `<div class="folder-details">${folder.image_count} images</div>` : ''}
                    </div>
                    ${!folder.is_parent ? `<button class="select-folder-btn" onclick="event.stopPropagation(); app.selectFolder('${folder.path}')">Select</button>` : ''}
                </div>
            `).join('');
        } catch (error) {
            this.showError('Error loading folder browser: ' + error.message);
        }
    }

    navigateToFolder(path) {
        this.loadFolderBrowser(path);
    }

    handleFolderClick(path, isParent) {
        if (isParent) {
            this.navigateToFolder(path);
        } else {
            this.loadFolderBrowser(path);
        }
    }

    async selectFolder(path) {
        try {
            this.showLoading('Selecting folder...');
            
            const response = await fetch('/api/folders', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    folder_path: path
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showSuccess(`Selected folder: ${path}`);
                this.loadFolders(); // Refresh folder display
            } else {
                this.showError(data.error || 'Failed to select folder');
            }
        } catch (error) {
            this.showError('Error selecting folder: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async indexFolders() {
        try {
            this.showLoading('Starting photo indexing...');
            
            const response = await fetch('/api/index_folders', {
                method: 'POST'
            });

            const data = await response.json();
            
            if (data.success) {
                this.showSuccess(data.message || 'Photo indexing started successfully');
                this.showInfo('Indexing is running in the background. Check statistics for updates.');
                
                // Refresh stats after a delay to show updated counts
                setTimeout(() => {
                    this.loadStats();
                }, 2000);
                
                // Refresh stats again after more time for final results
                setTimeout(() => {
                    this.loadStats();
                    this.showInfo('Photo indexing completed. Statistics updated.');
                }, 10000);
                
            } else {
                this.showError(data.error || 'Indexing failed');
            }
        } catch (error) {
            this.showError('Error indexing folders: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    // Directory browser for file operations
    async loadModalDirectoryBrowser(path = null) {
        try {
            const url = path ? `/api/browse_folders?path=${encodeURIComponent(path)}` : '/api/browse_folders';
            const response = await fetch(url);
            const data = await response.json();
            
            if (!data.folders) {
                this.showError('Error loading directory browser');
                return;
            }

            // Update current path display
            document.getElementById('modal-current-path').textContent = data.current_path;
            this.currentModalPath = data.current_path;
            
            // Update folder list
            const folderList = document.getElementById('modal-folder-list');
            folderList.innerHTML = data.folders.map(folder => `
                <div class="modal-folder-item ${folder.is_parent ? 'parent' : ''}" 
                     onclick="app.${folder.is_parent ? 'navigateModalToFolder' : 'handleModalFolderClick'}('${folder.path}', ${folder.is_parent})">
                    <i class="modal-folder-icon fas ${folder.is_parent ? 'fa-arrow-up' : 'fa-folder'}"></i>
                    <div class="modal-folder-info">
                        <div class="modal-folder-name">${folder.name}</div>
                        ${!folder.is_parent ? `<div class="modal-folder-details">${folder.image_count} images</div>` : ''}
                    </div>
                    ${!folder.is_parent ? `
                        <div class="modal-folder-actions">
                            <button class="select-destination-btn" onclick="event.stopPropagation(); app.selectDestinationFolder('${folder.path}')">
                                Select
                            </button>
                        </div>
                    ` : ''}
                </div>
            `).join('');
        } catch (error) {
            this.showError('Error loading directory browser: ' + error.message);
        }
    }

    navigateModalToFolder(path) {
        this.loadModalDirectoryBrowser(path);
    }

    handleModalFolderClick(path, isParent) {
        if (isParent) {
            this.navigateModalToFolder(path);
        } else {
            this.loadModalDirectoryBrowser(path);
        }
    }

    selectDestinationFolder(path) {
        this.selectedDestination = path;
        
        // Update UI
        const selectedPathDiv = document.getElementById('selected-destination-path');
        selectedPathDiv.textContent = path;
        selectedPathDiv.className = 'selected-path';
        
        // Enable confirm button
        document.getElementById('confirm-operation').disabled = false;
        
        // Highlight selected folder
        document.querySelectorAll('.modal-folder-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        // Find and highlight the selected folder
        const folderItems = document.querySelectorAll('.modal-folder-item');
        folderItems.forEach(item => {
            const selectBtn = item.querySelector('.select-destination-btn');
            if (selectBtn && selectBtn.getAttribute('onclick').includes(path)) {
                item.classList.add('selected');
            }
        });
        
        this.showSuccess(`Selected destination: ${path}`);
    }

    selectCurrentFolder() {
        if (this.currentModalPath) {
            this.selectDestinationFolder(this.currentModalPath);
        }
    }

    // Test function to verify file operations work
    testFileOperation() {
        console.log('Testing file operation directly...');
        
        const testData = {
            operation: 'copy',
            file_paths: ['/home/mohan/Desktop/Mohan/Vanithaphotography/Webcam/2025-09-27-111304.jpg'],
            destination: '/home/mohan/Documents'
        };
        
        fetch('/api/file_operations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(testData)
        })
        .then(response => response.json())
        .then(data => {
            console.log('Test result:', data);
            alert('Test completed - check console and Documents folder');
        })
        .catch(error => {
            console.error('Test failed:', error);
            alert('Test failed: ' + error.message);
        });
    }


    // Image source handling
    handleImageSourceChange(source) {
        const fileSection = document.getElementById('file-upload-section');
        const cameraSection = document.getElementById('camera-capture-section');
        
        if (source === 'file') {
            fileSection.style.display = 'block';
            cameraSection.style.display = 'none';
        } else if (source === 'camera') {
            fileSection.style.display = 'none';
            cameraSection.style.display = 'block';
        }
        
        // Clear any existing selection
        this.clearImageSelection();
    }

    clearImageSelection() {
        const selectedImageDiv = document.getElementById('selected-image');
        const previewImage = document.getElementById('preview-image');
        
        selectedImageDiv.style.display = 'none';
        previewImage.src = '';
        previewImage.alt = 'Selected image';
        
        document.getElementById('faces-panel').style.display = 'none';
        document.getElementById('search-btn').disabled = true;
        this.selectedFaceEncoding = null;
        this.detectedFaces = [];
        this.capturedImageData = null;
    }

    // Camera capture methods
    async openCameraModal() {
        const modal = document.getElementById('camera-modal');
        const video = document.getElementById('camera-video');
        const errorDiv = document.getElementById('camera-error');
        const captureBtn = document.getElementById('capture-btn');
        
        modal.style.display = 'flex';
        errorDiv.style.display = 'none';
        
        try {
            // Request camera access
            const stream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    width: { ideal: 640 }, 
                    height: { ideal: 480 },
                    facingMode: 'user' // Front camera for selfies
                } 
            });
            
            video.srcObject = stream;
            this.currentStream = stream;
            
            // Show capture button when video is ready
            video.addEventListener('loadedmetadata', () => {
                captureBtn.style.display = 'inline-block';
            });
            
        } catch (error) {
            console.error('Error accessing camera:', error);
            errorDiv.style.display = 'block';
            
            // Update error message based on error type
            const errorMessage = errorDiv.querySelector('p');
            if (error.name === 'NotAllowedError') {
                errorMessage.textContent = 'Camera access denied. Please allow camera access and try again.';
            } else if (error.name === 'NotFoundError') {
                errorMessage.textContent = 'No camera found. Please connect a camera and try again.';
            } else {
                errorMessage.textContent = 'Unable to access camera. Please check permissions and try again.';
            }
        }
    }

    closeCameraModal() {
        const modal = document.getElementById('camera-modal');
        const video = document.getElementById('camera-video');
        const preview = document.getElementById('camera-preview');
        const captureBtn = document.getElementById('capture-btn');
        const retakeBtn = document.getElementById('retake-btn');
        const useBtn = document.getElementById('use-captured-btn');
        
        // Stop camera stream
        if (this.currentStream) {
            this.currentStream.getTracks().forEach(track => track.stop());
            this.currentStream = null;
        }
        
        // Reset UI
        modal.style.display = 'none';
        video.style.display = 'block';
        preview.style.display = 'none';
        captureBtn.style.display = 'none';
        retakeBtn.style.display = 'none';
        useBtn.style.display = 'none';
        
        // Clear captured image data
        this.capturedImageData = null;
    }

    capturePhoto() {
        const video = document.getElementById('camera-video');
        const canvas = document.getElementById('camera-canvas');
        const preview = document.getElementById('camera-preview');
        const capturedImage = document.getElementById('captured-image');
        const captureBtn = document.getElementById('capture-btn');
        const retakeBtn = document.getElementById('retake-btn');
        const useBtn = document.getElementById('use-captured-btn');
        
        // Set canvas size to match video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        // Draw video frame to canvas
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0);
        
        // Get image data
        this.capturedImageData = canvas.toDataURL('image/jpeg', 0.8);
        
        // Show preview
        capturedImage.src = this.capturedImageData;
        video.style.display = 'none';
        preview.style.display = 'flex';
        
        // Update button visibility
        captureBtn.style.display = 'none';
        retakeBtn.style.display = 'inline-block';
        useBtn.style.display = 'inline-block';
    }

    retakePhoto() {
        const video = document.getElementById('camera-video');
        const preview = document.getElementById('camera-preview');
        const captureBtn = document.getElementById('capture-btn');
        const retakeBtn = document.getElementById('retake-btn');
        const useBtn = document.getElementById('use-captured-btn');
        
        // Show video again
        video.style.display = 'block';
        preview.style.display = 'none';
        
        // Update button visibility
        captureBtn.style.display = 'inline-block';
        retakeBtn.style.display = 'none';
        useBtn.style.display = 'none';
        
        // Clear captured image data
        this.capturedImageData = null;
    }

    async useCapturedPhoto() {
        if (!this.capturedImageData) {
            this.showError('No photo captured');
            return;
        }
        
        try {
            this.showLoading('Processing captured image...');
            
            // First display the captured image immediately
            this.displayCapturedImage(this.capturedImageData);
            
            const response = await fetch('/api/upload_camera_capture', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    image_data: this.capturedImageData
                })
            });
            
            const data = await response.json();
            
            if (data.success && data.faces && data.faces.length > 0) {
                // Close camera modal
                this.closeCameraModal();
                
                // Display detected faces (image is already displayed above)
                this.displayDetectedFaces(data.faces);
                this.showSuccess(`Detected ${data.faces.length} face(s) in captured image`);
            } else {
                // Close camera modal even if no faces detected
                this.closeCameraModal();
                this.showError(data.error || 'No faces detected in the captured image');
            }
        } catch (error) {
            this.closeCameraModal();
            this.showError('Error processing captured image: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    displayCapturedImage(imageData) {
        const previewImage = document.getElementById('preview-image');
        const selectedImageDiv = document.getElementById('selected-image');
        
        // Show the selected image container first
        selectedImageDiv.style.display = 'block';
        
        // Set loading state
        previewImage.style.opacity = '0.5';
        previewImage.alt = 'Loading captured image...';
        
        // Set the image source and ensure it loads properly
        previewImage.src = imageData;
        previewImage.style.display = 'block';
        
        // Ensure the image loads properly
        previewImage.onload = function() {
            previewImage.style.opacity = '1';
            previewImage.alt = 'Captured image from camera';
            console.log('Captured image displayed successfully');
        };
        
        previewImage.onerror = function() {
            previewImage.style.opacity = '1';
            previewImage.alt = 'Error loading captured image';
            console.error('Error loading captured image');
        };
    }

    // Google Drive methods
    async loadDriveStatus() {
        try {
            const response = await fetch('/api/drive/status');
            const data = await response.json();
            
            const statusContainer = document.getElementById('drive-status');
            const foldersSection = document.getElementById('drive-folders-section');
            const syncSection = document.getElementById('drive-sync-section');
            const userInfoSection = document.getElementById('drive-user-info');
            
            if (data.authenticated) {
                // Show connection status
                statusContainer.innerHTML = `
                    <div class="drive-connected">
                        <i class="fas fa-check-circle"></i>
                        <div>
                            <h4>Connected to Google Drive</h4>
                            <p>Email: ${data.user_email}</p>
                            <p>Name: ${data.user_name}</p>
                        </div>
                    </div>
                `;
                
                // Show user info section
                if (userInfoSection) {
                    document.getElementById('user-email').textContent = data.user_email;
                    document.getElementById('user-name').textContent = data.user_name;
                    userInfoSection.style.display = 'block';
                }
                
                // Show folders and sync sections
                if (foldersSection) foldersSection.style.display = 'block';
                if (syncSection) syncSection.style.display = 'block';
                
                // Load folders and synced folders
                this.loadDriveFolders();
                this.loadSyncedFolders();
                
            } else {
                // Hide sections when not authenticated
                if (foldersSection) foldersSection.style.display = 'none';
                if (syncSection) syncSection.style.display = 'none';
                if (userInfoSection) userInfoSection.style.display = 'none';
                
                statusContainer.innerHTML = `
                    <div class="drive-disconnected">
                        <i class="fas fa-times-circle"></i>
                        <div>
                            <h4>Not connected to Google Drive</h4>
                            <button class="btn btn-primary" onclick="app.connectDrive()">
                                <i class="fab fa-google-drive"></i> Connect to Google Drive
                            </button>
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading drive status:', error);
        }
    }

    async connectDrive() {
        try {
            const response = await fetch('/auth/google');
            const data = await response.json();
            
            if (data.auth_url) {
                window.location.href = data.auth_url;
            } else {
                this.showError('Failed to get authorization URL');
            }
        } catch (error) {
            this.showError('Error connecting to Google Drive: ' + error.message);
        }
    }

    async loadDriveFolders() {
        try {
            const folderList = document.getElementById('drive-folder-list');
            folderList.innerHTML = `
                <div class="loading-message">
                    <i class="fas fa-spinner fa-spin"></i> Loading Google Drive folders...
                </div>
            `;
            
            const response = await fetch('/api/drive/folders');
            const data = await response.json();
            
            if (data.success) {
                this.displayDriveFolders(data.folders);
            } else {
                folderList.innerHTML = `
                    <div class="error-message">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>Error loading drive folders: ${data.error || 'Unknown error'}</p>
                        <button class="retry-btn" onclick="app.loadDriveFolders()">
                            <i class="fas fa-redo"></i> Retry
                        </button>
                    </div>
                `;
            }
        } catch (error) {
            const folderList = document.getElementById('drive-folder-list');
            folderList.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Error loading drive folders: ${error.message}</p>
                    <button class="retry-btn" onclick="app.loadDriveFolders()">
                        <i class="fas fa-redo"></i> Retry
                    </button>
                </div>
            `;
        }
    }

    displayDriveFolders(folders) {
        const folderList = document.getElementById('drive-folder-list');
        
        if (folders.length === 0) {
            folderList.innerHTML = `
                <div class="loading-message">
                    <i class="fas fa-folder-open"></i>
                    <p>No folders found</p>
                </div>
            `;
            return;
        }

        folderList.innerHTML = folders.map(folder => `
            <div class="drive-folder-item">
                <i class="drive-folder-icon fas fa-folder"></i>
                <div class="drive-folder-info">
                    <div class="drive-folder-name">${folder.name}</div>
                    <div class="drive-folder-details">${folder.image_count} images</div>
                </div>
                <div class="drive-folder-actions">
                    <button class="index-photos-btn" onclick="app.indexDriveFolder('${folder.id}', '${folder.name}')">
                        <i class="fas fa-search"></i> Index photos
                    </button>
                </div>
            </div>
        `).join('');
    }

    async indexDriveFolder(folderId, folderName) {
        try {
            this.showLoading(`Indexing photos in ${folderName}...`);
            
            const response = await fetch('/api/drive/index', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    folder_id: folderId,
                    folder_name: folderName
                })
            });

            const data = await response.json();
            
            if (data.success) {
                const count = data.indexed_count || 0;
                if (count > 0) {
                    this.showSuccess(`Successfully indexed ${count} photos from ${folderName}`);
                    this.showInfo(`${folderName} folder is now available for face search`);
                } else {
                    this.showInfo(`${folderName} folder processed, but no photos were indexed`);
                }
                
                // Refresh synced folders and stats
                this.loadSyncedFolders();
                this.loadStats();
            } else {
                this.showError(data.error || 'Failed to index photos');
            }
        } catch (error) {
            this.showError('Error indexing photos: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async loadSyncedFolders() {
        try {
            const response = await fetch('/api/drive/synced_folders');
            const data = await response.json();
            
            const syncedContainer = document.getElementById('synced-folders-list');
            if (data.success && data.folders.length > 0) {
                syncedContainer.innerHTML = data.folders.map(folder => `
                    <div class="synced-folder-item">
                        <i class="fas fa-folder-check"></i>
                        <div class="synced-folder-info">
                            <div class="synced-folder-name">${folder.folder_name}</div>
                            <div class="synced-folder-details">${folder.file_count} files • Last synced: ${new Date(folder.last_synced).toLocaleString()}</div>
                        </div>
                    </div>
                `).join('');
            } else {
                syncedContainer.innerHTML = `
                    <div class="no-synced-folders">
                        <p>No folders synced yet. Select a folder from Google Drive to sync.</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading synced folders:', error);
        }
    }

    // Utility methods
    showLoading(message = 'Loading...') {
        const loadingDiv = document.getElementById('loading');
        if (loadingDiv) {
            const span = loadingDiv.querySelector('span');
            if (span) {
                span.textContent = message;
            }
            loadingDiv.style.display = 'flex';
        }
    }

    hideLoading() {
        const loadingDiv = document.getElementById('loading');
        if (loadingDiv) {
            loadingDiv.style.display = 'none';
        }
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showInfo(message) {
        this.showNotification(message, 'info');
    }

    showNotification(message, type = 'info') {
        // Remove any existing notifications
        const existingNotifications = document.querySelectorAll('.notification');
        existingNotifications.forEach(notif => {
            if (document.body.contains(notif)) {
                document.body.removeChild(notif);
            }
        });

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Show notification
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        // Hide notification after 4 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (document.body.contains(notification)) {
                    document.body.removeChild(notification);
                }
            }, 300);
        }, 4000);
    }
}

// Initialize the app when the page loads
const app = new PhotoSearchApp();
