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

        // File upload
        const uploadArea = document.getElementById('upload-area');
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
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileUpload(files[0]);
            }
        });
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileUpload(e.target.files[0]);
            }
        });

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
        document.getElementById('confirm-operation').addEventListener('click', () => this.confirmOperation());
        document.getElementById('cancel-operation').addEventListener('click', () => this.hideModal());
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
        } else if (tabName === 'drive') {
            this.loadDriveTab();
        } else if (tabName === 'stats') {
            this.loadStats();
        }
    }

    async handleFileUpload(file) {
        if (!file.type.startsWith('image/')) {
            this.showError('Please select a valid image file');
            return;
        }

        this.showLoading('Processing image...');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload_reference', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                this.displaySelectedImage(data.image);
                this.displayDetectedFaces(data.faces);
            } else {
                this.showError(data.error || 'Failed to process image');
            }
        } catch (error) {
            this.showError('Error uploading image: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    displaySelectedImage(imageData) {
        const selectedImageDiv = document.getElementById('selected-image');
        const previewImage = document.getElementById('preview-image');
        
        previewImage.src = imageData;
        selectedImageDiv.style.display = 'block';
        
        // Hide upload area
        document.getElementById('upload-area').style.display = 'none';
    }

    displayDetectedFaces(faces) {
        const facesPanel = document.getElementById('faces-panel');
        const detectedFaces = document.getElementById('detected-faces');
        
        detectedFaces.innerHTML = '';

        if (faces.length === 0) {
            detectedFaces.innerHTML = '<p>No faces detected in the image</p>';
            facesPanel.style.display = 'block';
            return;
        }

        faces.forEach((face, index) => {
            const faceItem = document.createElement('div');
            faceItem.className = 'face-item';
            faceItem.innerHTML = `
                <img src="${face.thumbnail}" alt="Face ${index + 1}">
                <p>Face ${index + 1}</p>
            `;
            
            faceItem.addEventListener('click', () => this.selectFace(faceItem, face));
            detectedFaces.appendChild(faceItem);
        });

        facesPanel.style.display = 'block';
    }

    selectFace(faceElement, faceData) {
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
                    search_source: searchSource  // Add search source
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
                                 onerror="this.src='/static/images/no-image.png'">
                        </div>
                        <div class="result-info">
                            <div class="result-filename">${result.file_name}</div>
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

    getSelectedFiles() {
        return Array.from(document.querySelectorAll('.result-checkbox input:checked'))
                   .map(checkbox => checkbox.closest('.result-item').dataset.path);
    }

    showOperationModal(operation) {
        const selectedFiles = this.getSelectedFiles();
        if (selectedFiles.length === 0) {
            this.showError('Please select files first');
            return;
        }

        this.currentOperation = { type: operation, files: selectedFiles };
        document.getElementById('folder-modal').style.display = 'flex';
        document.getElementById('destination-input').focus();
    }

    hideModal() {
        document.getElementById('folder-modal').style.display = 'none';
        this.currentOperation = null;
    }

    async confirmOperation() {
    if (!this.currentOperation) return;

    const destination = document.getElementById('destination-input').value.trim();
    if (!destination) {
        this.showError('Please enter a destination path');
        return;
    }

    this.hideModal();
    this.showLoading(`${this.currentOperation.type}ing files...`);

    try {
        const response = await fetch('/api/file_operations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                operation: this.currentOperation.type,
                file_paths: this.currentOperation.files,
                destination: destination
            })
        });

        const data = await response.json();
        
        if (data.successful > 0) {
            this.showSuccess(`${this.currentOperation.type}d ${data.successful} files successfully`);
            // Refresh search results if needed
            if (this.currentOperation.type === 'move' || this.currentOperation.type === 'delete') {
                this.searchSimilarFaces();
            }
        }
        
        if (data.failed > 0) {
            this.showError(`Failed to ${this.currentOperation.type} ${data.failed} files`);
        }
    } catch (error) {
        this.showError(`Error ${this.currentOperation.type}ing files: ` + error.message);
    } finally {
        this.hideLoading();
        document.getElementById('destination-input').value = '';
    }
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
            this.searchSimilarFaces(); // Refresh results
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

async loadFolders() {
    try {
        const response = await fetch('/api/folders');
        const data = await response.json();
        
        const currentFolderText = document.getElementById('current-folder-text');
        const indexButton = document.getElementById('index-folders-btn');
        
        if (data.folders.length === 0) {
            currentFolderText.textContent = 'No directory selected';
            indexButton.disabled = true;
        } else {
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
        document.querySelectorAll('.result-checkbox').forEach(checkbox => {
            checkbox.checked = true;
            checkbox.closest('.result-item').classList.add('selected');
        });
    }

    clearSelection() {
        document.querySelectorAll('.result-checkbox').forEach(checkbox => {
            checkbox.checked = false;
            checkbox.closest('.result-item').classList.remove('selected');
        });
    }

    getSelectedFiles() {
        return Array.from(document.querySelectorAll('.result-checkbox:checked'))
                   .map(checkbox => checkbox.dataset.path);
    }

    showOperationModal(operation) {
        const selectedFiles = this.getSelectedFiles();
        if (selectedFiles.length === 0) {
            this.showError('Please select files first');
            return;
        }

        this.currentOperation = { type: operation, files: selectedFiles };
        document.getElementById('folder-modal').style.display = 'flex';
        document.getElementById('destination-input').focus();
    }

    hideModal() {
        document.getElementById('folder-modal').style.display = 'none';
        this.currentOperation = null;
    }

    async confirmOperation() {
        if (!this.currentOperation) return;

        const destination = document.getElementById('destination-input').value.trim();
        if (!destination) {
            this.showError('Please enter a destination path');
            return;
        }

        this.hideModal();
        this.showLoading(`${this.currentOperation.type}ing files...`);

        try {
            const response = await fetch('/api/file_operations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    operation: this.currentOperation.type,
                    file_paths: this.currentOperation.files,
                    destination: destination
                })
            });

            const data = await response.json();
            
            if (data.successful > 0) {
                this.showSuccess(`${this.currentOperation.type}d ${data.successful} files successfully`);
                // Refresh search results if needed
                if (this.currentOperation.type === 'move' || this.currentOperation.type === 'delete') {
                    this.searchSimilarFaces();
                }
            }
            
            if (data.failed > 0) {
                this.showError(`Failed to ${this.currentOperation.type} ${data.failed} files`);
            }
        } catch (error) {
            this.showError(`Error ${this.currentOperation.type}ing files: ` + error.message);
        } finally {
            this.hideLoading();
            document.getElementById('destination-input').value = '';
        }
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
                this.searchSimilarFaces(); // Refresh results
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

    async loadFolders() {
        try {
            const response = await fetch('/api/folders');
            const data = await response.json();
            
            const currentFolderText = document.getElementById('current-folder-text');
            const indexButton = document.getElementById('index-folders-btn');
            
            if (data.folders.length === 0) {
                currentFolderText.textContent = 'No directory selected';
                indexButton.disabled = true;
            } else {
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
        if (!isParent) {
            this.loadFolderBrowser(path);
        }
    }

    async selectFolder(folderPath) {
        try {
            const response = await fetch('/api/folders', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ folder_path: folderPath })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('Folder selected successfully');
                this.loadFolders();
            } else {
                this.showError(data.error || 'Failed to select folder');
            }
        } catch (error) {
            this.showError('Error selecting folder: ' + error.message);
        }
    }


    async removeFolder(folderPath) {
        if (!confirm(`Remove folder from search scope?\n${folderPath}`)) {
            return;
        }

        try {
            const response = await fetch(`/api/folders/${encodeURIComponent(folderPath)}`, {
                method: 'DELETE'
            });

            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('Folder removed successfully');
                this.loadFolders();
            } else {
                this.showError(data.error || 'Failed to remove folder');
            }
        } catch (error) {
            this.showError('Error removing folder: ' + error.message);
        }
    }

    async indexFolders() {
        this.showLoading('Starting indexing process...');

        try {
            const response = await fetch('/api/index_folders', {
                method: 'POST'
            });

            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('Indexing started');
                this.startProgressMonitoring();
            } else {
                this.showError(data.error || 'Failed to start indexing');
            }
        } catch (error) {
            this.showError('Error starting indexing: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    startProgressMonitoring() {
        const progressSection = document.getElementById('progress-section');
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        
        progressSection.style.display = 'block';

        const updateProgress = async () => {
            try {
                const response = await fetch('/api/indexing_progress');
                const data = await response.json();
                
                const percentage = data.percentage || 0;
                progressFill.style.width = percentage + '%';
                progressText.textContent = `Indexing: ${data.current}/${data.total} (${percentage.toFixed(1)}%)`;
                
                if (percentage < 100 && data.total > 0) {
                    setTimeout(updateProgress, 1000);
                } else {
                    progressText.textContent = 'Indexing complete';
                    setTimeout(() => {
                        progressSection.style.display = 'none';
                    }, 3000);
                }
            } catch (error) {
                console.error('Error updating progress:', error);
            }
        };

        updateProgress();
    }

    async loadStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();
            
            document.getElementById('total-images').textContent = data.total_images || 0;
            document.getElementById('total-faces').textContent = data.total_faces || 0;
            document.getElementById('active-folders').textContent = data.active_folders || 0;
            document.getElementById('database-size').textContent = 
                ((data.database_size || 0) / (1024 * 1024)).toFixed(2) + ' MB';
        } catch (error) {
            this.showError('Error loading statistics: ' + error.message);
        }
    }

    // Google Drive Methods
    async loadDriveTab() {
        // First check if Google Drive is available
        try {
            const response = await fetch('/api/drive/available');
            const data = await response.json();
            
            if (!data.available) {
                this.showDriveUnavailable();
                return;
            }
        } catch (error) {
            this.showDriveUnavailable();
            return;
        }
        
        this.checkDriveStatus();
        this.setupDriveEventListeners();
    }

    setupDriveEventListeners() {
        // Connect button
        const connectBtn = document.getElementById('connect-drive-btn');
        if (connectBtn) {
            connectBtn.addEventListener('click', () => this.connectGoogleDrive());
        }

        // Disconnect button
        const disconnectBtn = document.getElementById('disconnect-drive-btn');
        if (disconnectBtn) {
            disconnectBtn.addEventListener('click', () => this.disconnectGoogleDrive());
        }

        // Test connection button
        const testBtn = document.getElementById('test-drive-btn');
        if (testBtn) {
            testBtn.addEventListener('click', () => this.testDriveConnection());
        }

        // Stop sync button
        const stopSyncBtn = document.getElementById('stop-sync-btn');
        if (stopSyncBtn) {
            stopSyncBtn.addEventListener('click', () => this.stopSync());
        }
    }

    async checkDriveStatus() {
        try {
            const response = await fetch('/api/drive/status');
            const data = await response.json();
            
            this.updateDriveStatus(data);
            
            if (data.authenticated) {
                this.loadDriveFolders();
                this.loadSyncedFolders();
            }
        } catch (error) {
            console.error('Error checking drive status:', error);
            this.updateDriveStatus({ authenticated: false, error: error.message });
        }
    }

    updateDriveStatus(data) {
        const indicator = document.getElementById('drive-indicator');
        const statusIcon = document.getElementById('status-icon');
        const statusText = document.getElementById('status-text');
        const connectBtn = document.getElementById('connect-drive-btn');
        const disconnectBtn = document.getElementById('disconnect-drive-btn');
        const testBtn = document.getElementById('test-drive-btn');
        const userInfo = document.getElementById('drive-user-info');
        const foldersSection = document.getElementById('drive-folders-section');
        const syncSection = document.getElementById('drive-sync-section');

        if (data.authenticated) {
            indicator.className = 'status-indicator connected';
            statusText.textContent = 'Connected to Google Drive';
            connectBtn.style.display = 'none';
            disconnectBtn.style.display = 'inline-flex';
            testBtn.style.display = 'inline-flex';
            foldersSection.style.display = 'block';
            syncSection.style.display = 'block';

            // Show user info if available
            if (data.connection_test && data.connection_test.success) {
                const userEmail = document.getElementById('user-email');
                const userName = document.getElementById('user-name');
                
                if (userEmail) userEmail.textContent = data.connection_test.user_email || 'Unknown';
                if (userName) userName.textContent = data.connection_test.user_name || 'Unknown';
                
                userInfo.style.display = 'block';
            }
        } else {
            indicator.className = 'status-indicator disconnected';
            statusText.textContent = 'Not connected to Google Drive';
            connectBtn.style.display = 'inline-flex';
            disconnectBtn.style.display = 'none';
            testBtn.style.display = 'none';
            userInfo.style.display = 'none';
            foldersSection.style.display = 'none';
            syncSection.style.display = 'none';
        }
    }

    async connectGoogleDrive() {
        try {
            const response = await fetch('/auth/google');
            const data = await response.json();
            
            if (data.auth_url) {
                // Open authorization URL in new window
                window.open(data.auth_url, 'google-auth', 'width=500,height=600');
                
                // Check for auth completion
                this.checkAuthCompletion();
            }
        } catch (error) {
            this.showError('Error connecting to Google Drive: ' + error.message);
        }
    }

    checkAuthCompletion() {
        // Poll for authentication completion
        const checkInterval = setInterval(async () => {
            try {
                const response = await fetch('/api/drive/status');
                const data = await response.json();
                
                if (data.authenticated) {
                    clearInterval(checkInterval);
                    this.updateDriveStatus(data);
                    this.loadDriveFolders();
                    this.loadSyncedFolders();
                    this.showSuccess('Successfully connected to Google Drive!');
                }
            } catch (error) {
                console.error('Error checking auth status:', error);
            }
        }, 2000);

        // Stop checking after 2 minutes
        setTimeout(() => clearInterval(checkInterval), 120000);
    }

    async disconnectGoogleDrive() {
        if (!confirm('Are you sure you want to disconnect from Google Drive?')) {
            return;
        }

        try {
            const response = await fetch('/api/drive/logout', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateDriveStatus({ authenticated: false });
                this.showSuccess('Disconnected from Google Drive');
            } else {
                this.showError('Error disconnecting from Google Drive');
            }
        } catch (error) {
            this.showError('Error disconnecting: ' + error.message);
        }
    }

    async testDriveConnection() {
        try {
            this.showLoading('Testing Google Drive connection...');
            
            const response = await fetch('/api/drive/status');
            const data = await response.json();
            
            if (data.authenticated && data.connection_test) {
                if (data.connection_test.success) {
                    this.showSuccess(`Connection successful! Found ${data.connection_test.files_accessible} accessible files.`);
                } else {
                    this.showError(`Connection failed: ${data.connection_test.error}`);
                }
            } else {
                this.showError('Not connected to Google Drive');
            }
        } catch (error) {
            this.showError('Error testing connection: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async loadDriveFolders(parentId = null) {
        try {
            this.showLoading('Loading Google Drive folders...');
            
            const url = parentId ? `/api/drive/folders?parent_id=${parentId}` : '/api/drive/folders';
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.displayDriveFolders(data.folders);
                this.showSuccess(`Loaded ${data.folders.length} folders from Google Drive`);
            } else {
                this.showError(data.error || 'Error loading drive folders');
            }
        } catch (error) {
            console.error('Drive folders error:', error);
            this.showError('Error loading drive folders: ' + error.message);
            
            // Show a message in the folders area
            const folderList = document.getElementById('drive-folder-list');
            if (folderList) {
                folderList.innerHTML = `
                    <div class="error-message">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>Failed to load Google Drive folders</p>
                        <button class="retry-btn" onclick="app.loadDriveFolders()">
                            <i class="fas fa-redo"></i> Retry
                        </button>
                    </div>
                `;
            }
        } finally {
            this.hideLoading();
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
                this.showSuccess(`Successfully indexed ${data.indexed_count} photos from ${folderName}`);
                this.loadSyncedFolders(); // Refresh synced folders list
            } else {
                this.showError(data.error || 'Failed to index photos');
            }
        } catch (error) {
            this.showError('Error indexing photos: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async syncDriveFolder(folderId, folderName) {
        try {
            const response = await fetch('/api/drive/sync', {
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
                this.showSuccess('Sync started for ' + folderName);
                this.startSyncProgressMonitoring();
            } else {
                this.showError(data.error || 'Failed to start sync');
            }
        } catch (error) {
            this.showError('Error starting sync: ' + error.message);
        }
    }

    startSyncProgressMonitoring() {
        const progressSection = document.getElementById('sync-progress-section');
        const progressFill = document.getElementById('sync-progress-fill');
        const progressText = document.getElementById('sync-progress-text');
        
        progressSection.style.display = 'block';

        const updateProgress = async () => {
            try {
                const response = await fetch('/api/drive/sync/progress');
                const data = await response.json();
                
                const percentage = data.total > 0 ? (data.current / data.total) * 100 : 0;
                progressFill.style.width = percentage + '%';
                progressText.textContent = `${data.message} (${data.current}/${data.total})`;
                
                if (data.status === 'completed' || data.status === 'cancelled' || data.status === 'error') {
                    setTimeout(() => {
                        progressSection.style.display = 'none';
                        this.loadSyncedFolders(); // Refresh synced folders
                    }, 3000);
                } else {
                    setTimeout(updateProgress, 1000);
                }
            } catch (error) {
                console.error('Error updating sync progress:', error);
            }
        };

        updateProgress();
    }

    async stopSync() {
        try {
            const response = await fetch('/api/drive/sync/stop', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('Sync stopped');
            }
        } catch (error) {
            this.showError('Error stopping sync: ' + error.message);
        }
    }

    async loadSyncedFolders() {
        try {
            const response = await fetch('/api/drive/synced_folders');
            const data = await response.json();
            
            if (data.success) {
                this.displaySyncedFolders(data.folders);
            }
        } catch (error) {
            console.error('Error loading synced folders:', error);
        }
    }

    displaySyncedFolders(folders) {
        const syncedList = document.getElementById('synced-folders-list');
        
        if (folders.length === 0) {
            syncedList.innerHTML = `
                <div class="no-synced-folders">
                    <i class="fas fa-cloud"></i>
                    <p>No folders synced yet. Select a folder from Google Drive to sync.</p>
                </div>
            `;
            return;
        }

        syncedList.innerHTML = folders.map(folder => `
            <div class="synced-folder-item">
                <div class="synced-folder-info">
                    <div class="synced-folder-name">${folder.folder_name}</div>
                    <div class="synced-folder-stats">${folder.file_count} files • Last synced: ${new Date(folder.last_synced).toLocaleDateString()}</div>
                </div>
                <button class="remove-sync-btn" onclick="app.removeSyncedFolder('${folder.drive_folder_id}')">
                    <i class="fas fa-times"></i> Remove
                </button>
            </div>
        `).join('');
    }

    async removeSyncedFolder(folderId) {
        if (!confirm('Remove this folder from sync? This will delete all synced photos from the database.')) {
            return;
        }

        try {
            const response = await fetch(`/api/drive/synced_folders/${folderId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('Folder removed from sync');
                this.loadSyncedFolders();
            } else {
                this.showError('Error removing folder');
            }
        } catch (error) {
            this.showError('Error removing folder: ' + error.message);
        }
    }

    loadInitialData() {
        this.loadStats();
        this.checkForDriveConnection();
    }

    checkForDriveConnection() {
        // Check if user just connected to Google Drive
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('drive_connected') === 'true') {
            this.showSuccess('Successfully connected to Google Drive!');
            // Remove the parameter from URL
            window.history.replaceState({}, document.title, window.location.pathname);
            // Switch to Google Drive tab to show the connection and load folders
            setTimeout(() => {
                this.switchTab('drive');
            }, 1000);
        } else if (urlParams.get('auth') === 'error') {
            const reason = urlParams.get('reason');
            let errorMessage = 'Failed to connect to Google Drive';
            if (reason === 'oauth_failed') {
                errorMessage = 'OAuth authentication failed. Please try again.';
            } else if (reason === 'callback_exception') {
                errorMessage = 'An error occurred during authentication. Please try again.';
            }
            this.showError(errorMessage);
            // Remove the parameter from URL
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    }

    showLoading(message = 'Loading...') {
        document.getElementById('loading-text').textContent = message;
        document.getElementById('loading-overlay').style.display = 'flex';
    }

    hideLoading() {
        document.getElementById('loading-overlay').style.display = 'none';
    }

    showSuccess(message) {
        alert('Success: ' + message);
    }

    showError(message) {
        alert('Error: ' + message);
    }

    showDriveUnavailable() {
        const driveTab = document.getElementById('drive-tab');
        driveTab.innerHTML = `
            <div class="drive-unavailable">
                <div class="unavailable-icon">
                    <i class="fab fa-google-drive" style="font-size: 4rem; color: #ccc;"></i>
                </div>
                <h3>Google Drive Integration Disabled</h3>
                <p>Google Drive integration is currently disabled in the application configuration.</p>
                <div class="unavailable-info">
                    <h4>To enable Google Drive:</h4>
                    <ol>
                        <li>Configure OAuth consent screen in Google Cloud Console</li>
                        <li>Add your email as a test user</li>
                        <li>Set <code>ENABLE_GOOGLE_DRIVE = True</code> in config.py</li>
                        <li>Restart the application</li>
                    </ol>
                </div>
                <div class="local-alternative">
                    <h4>Alternative: Use Local Folders</h4>
                    <p>You can still use all face recognition features with local photo folders.</p>
                    <button class="btn btn-primary" onclick="app.switchTab('manage')">
                        <i class="fas fa-folder"></i> Go to Local Folders
                    </button>
                </div>
            </div>
        `;
    }
}

// Initialize the app when the page loads
const app = new PhotoSearchApp();
