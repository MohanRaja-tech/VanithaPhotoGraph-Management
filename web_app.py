#!/usr/bin/env python3
"""
Face-Based Photo Search & Management System - Web Interface
Flask web application for face recognition and photo management
"""

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import os
import json
import base64
import numpy as np
from werkzeug.utils import secure_filename
from PIL import Image
import io
import logging
from database_manager import DatabaseManager
from photo_manager import PhotoManager
from face_recognition_engine import FaceRecognitionEngine
from config import Config
import threading
import time

# Conditionally import Google Drive modules
if Config.ENABLE_GOOGLE_DRIVE:
    try:
        from google_drive import drive_auth, drive_service, get_sync_manager
        GOOGLE_DRIVE_AVAILABLE = True
    except ImportError as e:
        print(f"Warning: Google Drive integration disabled due to import error: {e}")
        GOOGLE_DRIVE_AVAILABLE = False
else:
    GOOGLE_DRIVE_AVAILABLE = False
    print("Google Drive integration disabled in configuration")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize components
db_manager = DatabaseManager()
photo_manager = PhotoManager(db_manager)
face_engine = FaceRecognitionEngine()

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/upload_reference', methods=['POST'])
def upload_reference():
    """Upload and process reference image"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process the image for faces
            logger.info(f"Processing image for faces: {filepath}")
            face_data = face_engine.process_image_for_faces(filepath)
            logger.info(f"Face detection result: {face_data}")
            
            if 'error' in face_data:
                logger.error(f"Face detection error: {face_data['error']}")
                return jsonify({'error': face_data['error']}), 400
            
            # Check if any faces were detected
            if not face_data.get('face_locations') or len(face_data['face_locations']) == 0:
                logger.warning("No faces detected in the uploaded image")
                return jsonify({'error': 'No faces detected in the image'}), 400
            
            # Convert face locations and create thumbnails
            faces = []
            for i, (location, encoding) in enumerate(zip(face_data['face_locations'], face_data['face_encodings'])):
                # Extract face thumbnail
                face_image = face_engine.extract_face_from_image(filepath, location)
                if face_image is not None:
                    # Convert to base64 for web display
                    pil_image = Image.fromarray(face_image)
                    buffer = io.BytesIO()
                    pil_image.save(buffer, format='PNG')
                    face_b64 = base64.b64encode(buffer.getvalue()).decode()
                    
                    faces.append({
                        'index': i,
                        'location': location,
                        'thumbnail': f'data:image/png;base64,{face_b64}',
                        'encoding': encoding.tolist()  # Convert numpy array to list for JSON
                    })
            
            # Convert main image to base64 for display
            with open(filepath, 'rb') as img_file:
                img_b64 = base64.b64encode(img_file.read()).decode()
            
            return jsonify({
                'success': True,
                'image': f'data:image/jpeg;base64,{img_b64}',
                'faces': faces,
                'face_count': len(faces)
            })
        
        return jsonify({'error': 'Invalid file type'}), 400
        
    except Exception as e:
        logger.error(f"Error uploading reference: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload_camera_capture', methods=['POST'])
def upload_camera_capture():
    """Process captured image from camera"""
    try:
        data = request.get_json()
        if not data or 'image_data' not in data:
            return jsonify({'error': 'No image data provided'}), 400
        
        image_data = data['image_data']
        
        # Remove data URL prefix if present
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        # Decode base64 image
        try:
            image_bytes = base64.b64decode(image_data)
        except Exception as e:
            return jsonify({'error': 'Invalid image data format'}), 400
        
        # Save the captured image temporarily
        import uuid
        filename = f"camera_capture_{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        
        # Process the image for faces
        logger.info(f"Processing camera capture for faces: {filepath}")
        face_data = face_engine.process_image_for_faces(filepath)
        logger.info(f"Face detection result: {face_data}")
        
        if 'error' in face_data:
            logger.error(f"Face detection error: {face_data['error']}")
            return jsonify({'error': face_data['error']}), 400
        
        # Check if any faces were detected
        if not face_data.get('face_locations') or len(face_data['face_locations']) == 0:
            logger.warning("No faces detected in the captured image")
            return jsonify({'error': 'No faces detected in the captured image'}), 400
        
        # Convert face locations and create thumbnails
        faces = []
        for i, (location, encoding) in enumerate(zip(face_data['face_locations'], face_data['face_encodings'])):
            # Extract face thumbnail
            face_image = face_engine.extract_face_from_image(filepath, location)
            if face_image is not None:
                # Convert to base64 for web display
                pil_image = Image.fromarray(face_image)
                buffer = io.BytesIO()
                pil_image.save(buffer, format='PNG')
                face_b64 = base64.b64encode(buffer.getvalue()).decode()
                
                faces.append({
                    'index': i,
                    'location': location,
                    'thumbnail': f'data:image/png;base64,{face_b64}',
                    'encoding': encoding.tolist()  # Convert numpy array to list for JSON
                })
        
        # Convert main image to base64 for display
        with open(filepath, 'rb') as img_file:
            img_b64 = base64.b64encode(img_file.read()).decode()
        
        return jsonify({
            'success': True,
            'image': f'data:image/jpeg;base64,{img_b64}',
            'faces': faces,
            'face_count': len(faces)
        })
        
    except Exception as e:
        logger.error(f"Error processing camera capture: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/image_thumbnail')
def get_image_thumbnail():
    """Get image thumbnail for display"""
    try:
        file_path = request.args.get('path')
        
        # Handle Google Drive photos by checking if they exist in the actual indexed database
        if file_path and file_path.startswith('/hardcoded/drive/'):
            # For now, return a 404 since these are not real files
            return jsonify({'error': 'Google Drive photo not found - may need to be indexed first'}), 404
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Check if it's an allowed image file
        if not allowed_file(file_path):
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Try to create a thumbnail
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Create thumbnail
                img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                
                # Save to bytes
                img_io = io.BytesIO()
                img.save(img_io, 'JPEG', quality=85)
                img_io.seek(0)
                
                return send_file(img_io, mimetype='image/jpeg')
        except Exception as e:
            logger.warning(f"Could not create thumbnail for {file_path}: {str(e)}")
            # Fallback to original file
            return send_file(file_path)
            
    except Exception as e:
        logger.error(f"Error serving image thumbnail: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search_faces', methods=['POST'])
def search_faces():
    """Search for similar faces with source selection"""
    try:
        data = request.get_json()
        face_encoding = np.array(data['face_encoding'])
        tolerance = data.get('tolerance', 0.6)
        min_similarity = data.get('min_similarity', 0.55)
        search_source = data.get('search_source', 'local')  # 'local' or 'drive'
        
        results = []
        
        if search_source == 'local':
            # Search only in local database
            results = photo_manager.search_similar_faces(
                face_encoding, 
                tolerance=tolerance, 
                min_similarity=min_similarity
            )
            logger.info(f"Local search found {len(results)} results")
            
        elif search_source == 'drive':
           
            logger.info("Searching in hardcoded Google Drive folder: /home/mohan/Desktop/Mohan/Vanithaphotography/Webcam")
            
            try:
               
                webcam_folder = "/home/mohan/Desktop/Mohan/Vanithaphotography/Webcam"
                results = []
                
                if os.path.exists(webcam_folder):
                    # Get all image files in the Webcam folder
                    image_files = []
                    for file in os.listdir(webcam_folder):
                        if allowed_file(file):
                            file_path = os.path.join(webcam_folder, file)
                            image_files.append(file_path)
                    
                    logger.info(f"Found {len(image_files)} images in Webcam folder")
                    
                    # Perform face recognition on each image
                    for image_path in image_files:
                        try:
                            # Process the image for faces
                            face_data = face_engine.process_image_for_faces(image_path)
                            
                            if 'face_encodings' in face_data and len(face_data['face_encodings']) > 0:
                                # Compare with the input face encoding
                                import face_recognition
                                distances = face_recognition.face_distance(face_data['face_encodings'], face_encoding)
                                
                                # Find the best match
                                if len(distances) > 0:
                                    best_distance = min(distances)
                                    similarity = 1 - best_distance
                                    
                                    # Only include if similarity is above threshold
                                    if similarity >= min_similarity:
                                        results.append({
                                            'file_path': image_path,
                                            'file_name': os.path.basename(image_path),
                                            'similarity': similarity,
                                            'source': 'drive'
                                        })
                                        logger.info(f"Match found: {os.path.basename(image_path)} with {similarity:.2f} similarity")
                        
                        except Exception as e:
                            logger.warning(f"Error processing {image_path}: {str(e)}")
                            continue
                    
                    # Sort results by similarity (highest first)
                    results.sort(key=lambda x: x['similarity'], reverse=True)
                    logger.info(f"Google Drive search found {len(results)} results")
                
                else:
                    logger.warning(f"Webcam folder not found: {webcam_folder}")
                    results = []
                    
            except Exception as e:
                logger.error(f"Error searching in hardcoded Google Drive folder: {str(e)}")
                results = []
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
            'search_source': search_source
        })
        
    except Exception as e:
        logger.error(f"Error searching faces: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
        
    except Exception as e:
        logger.error(f"Error searching faces: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/folders', methods=['GET'])
def get_folders():
    """Get search folders"""
    try:
        folders = db_manager.get_search_folders()
        
        # Get image count for each folder
        folder_info = []
        for folder in folders:
            try:
                # Count images in this folder from database
                all_encodings = db_manager.get_all_face_encodings()
                image_count = len([enc for enc in all_encodings if enc['file_path'].startswith(folder)])
                folder_info.append({
                    'path': folder,
                    'image_count': image_count
                })
            except:
                folder_info.append({
                    'path': folder,
                    'image_count': 0
                })
        
        return jsonify({
            'folders': folders,
            'folder_info': folder_info,
            'active_folder': folders[0] if folders else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/folders', methods=['POST'])
def add_folder():
    """Add search folder (replace existing ones for single folder mode)"""
    try:
        data = request.get_json()
        folder_path = data.get('folder_path')
        
        if not folder_path or not os.path.exists(folder_path):
            return jsonify({'error': 'Invalid folder path'}), 400
        
        # Remove all existing folders first (single folder mode)
        existing_folders = db_manager.get_search_folders()
        for existing_folder in existing_folders:
            db_manager.remove_search_folder(existing_folder)
        
        # Add the new folder
        success = db_manager.add_search_folder(folder_path)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to add folder'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/browse_folders')
def browse_folders():
    """Browse folders starting from home directory"""
    try:
        path = request.args.get('path', os.path.expanduser('~'))
        
        if not os.path.exists(path) or not os.path.isdir(path):
            return jsonify({'error': 'Invalid path'}), 400
        
        folders = []
        files = []
        
        # Add parent directory option (except for root)
        if path != '/':
            parent = os.path.dirname(path)
            folders.append({
                'name': '.. (Parent Directory)',
                'path': parent,
                'is_parent': True
            })
        
        try:
            # List directory contents
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                
                if os.path.isdir(item_path):
                    # Count images in this directory
                    image_count = 0
                    try:
                        for file in os.listdir(item_path):
                            if allowed_file(file):
                                image_count += 1
                    except:
                        pass
                    
                    folders.append({
                        'name': item,
                        'path': item_path,
                        'image_count': image_count,
                        'is_parent': False
                    })
        except PermissionError:
            return jsonify({'error': 'Permission denied'}), 403
        
        return jsonify({
            'current_path': path,
            'folders': folders
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/folders/<path:folder_path>', methods=['DELETE'])
def remove_folder(folder_path):
    """Remove search folder"""
    try:
        success = db_manager.remove_search_folder(folder_path)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to remove folder'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/index_folders', methods=['POST'])
def index_folders():
    """Start indexing all folders"""
    try:
        folders = db_manager.get_search_folders()
        if not folders:
            return jsonify({'error': 'No folders to index'}), 400
        
        logger.info(f"Starting indexing for folders: {folders}")
        
        # Start indexing in background thread
        def index_background():
            try:
                image_files = photo_manager.scan_folders_for_images(folders)
                logger.info(f"Found {len(image_files)} images to index")
                
                if image_files:
                    result = photo_manager.index_images_batch(image_files, max_workers=1)
                    logger.info(f"Indexing completed: {result}")
                else:
                    logger.warning("No image files found in folders")
            except Exception as e:
                logger.error(f"Background indexing error: {str(e)}")
        
        threading.Thread(target=index_background, daemon=True).start()
        
        return jsonify({'success': True, 'message': 'Indexing started'})
        
    except Exception as e:
        logger.error(f"Error starting indexing: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/indexing_progress')
def get_indexing_progress():
    """Get current indexing progress"""
    try:
        current, total = photo_manager.get_indexing_progress()
        return jsonify({
            'current': current,
            'total': total,
            'percentage': (current / max(total, 1)) * 100
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """Get database statistics"""
    try:
        stats = db_manager.get_database_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to verify server is working"""
    return jsonify({'status': 'Server is working', 'timestamp': time.time()})

@app.route('/api/test_copy', methods=['POST'])
def test_copy():
    """Test copy operation with a known file"""
    try:
        test_file = '/home/mohan/Desktop/Mohan/Vanithaphotography/Webcam/2025-09-27-111304.jpg'
        destination = '/home/mohan/Documents'
        
        logger.info(f"Testing copy operation: {test_file} to {destination}")
        
        if not os.path.exists(test_file):
            return jsonify({'error': f'Test file does not exist: {test_file}'}), 400
        
        result = photo_manager.copy_files([test_file], destination)
        logger.info(f"Test copy result: {result}")
        
        return jsonify({
            'success': True,
            'result': result,
            'test_file': test_file,
            'destination': destination
        })
        
    except Exception as e:
        logger.error(f"Test copy error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug_files', methods=['GET'])
def debug_files():
    """Debug endpoint to check available files"""
    try:
        webcam_folder = '/home/mohan/Desktop/Mohan/Vanithaphotography/Webcam'
        files = []
        
        if os.path.exists(webcam_folder):
            for file in os.listdir(webcam_folder):
                if allowed_file(file):
                    file_path = os.path.join(webcam_folder, file)
                    files.append({
                        'name': file,
                        'path': file_path,
                        'exists': os.path.exists(file_path),
                        'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    })
        
        return jsonify({
            'webcam_folder': webcam_folder,
            'files': files,
            'count': len(files)
        })
        
    except Exception as e:
        logger.error(f"Debug files error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/file_operations', methods=['POST'])
def file_operations():
    """Handle file operations (copy, move, delete)"""
    logger.info("File operations endpoint called")
    try:
        data = request.get_json()
        operation = data.get('operation')
        file_paths = data.get('file_paths', [])
        destination = data.get('destination')
        
        logger.info(f"File operation request: operation={operation}, files={len(file_paths)}, destination={destination}")
        logger.info(f"File paths: {file_paths}")
        
        # Validate file paths
        if not file_paths:
            logger.error("No file paths provided")
            return jsonify({'error': 'No files selected'}), 400
        
        # Check if source files exist
        missing_files = []
        for file_path in file_paths:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
                logger.warning(f"Source file does not exist: {file_path}")
        
        if missing_files:
            logger.error(f"Missing source files: {missing_files}")
            return jsonify({'error': f'Source files not found: {missing_files}'}), 400
        
        if operation == 'copy' and destination:
            # Check if destination exists and is writable
            if not os.path.exists(destination):
                logger.info(f"Creating destination directory: {destination}")
                try:
                    os.makedirs(destination, exist_ok=True)
                except Exception as e:
                    logger.error(f"Failed to create destination directory: {e}")
                    return jsonify({'error': f'Cannot create destination directory: {str(e)}'}), 400
            
            if not os.access(destination, os.W_OK):
                logger.error(f"Destination directory not writable: {destination}")
                return jsonify({'error': 'Destination directory is not writable'}), 400
                
            logger.info(f"Copying {len(file_paths)} files to {destination}")
            result = photo_manager.copy_files(file_paths, destination)
            logger.info(f"Copy result: {result}")
            
        elif operation == 'move' and destination:
            # Check if destination exists and is writable
            if not os.path.exists(destination):
                logger.info(f"Creating destination directory: {destination}")
                try:
                    os.makedirs(destination, exist_ok=True)
                except Exception as e:
                    logger.error(f"Failed to create destination directory: {e}")
                    return jsonify({'error': f'Cannot create destination directory: {str(e)}'}), 400
            
            if not os.access(destination, os.W_OK):
                logger.error(f"Destination directory not writable: {destination}")
                return jsonify({'error': 'Destination directory is not writable'}), 400
                
            logger.info(f"Moving {len(file_paths)} files to {destination}")
            result = photo_manager.move_files(file_paths, destination)
            logger.info(f"Move result: {result}")
            
        elif operation == 'delete':
            logger.info(f"Deleting {len(file_paths)} files")
            result = photo_manager.delete_files(file_paths)
            logger.info(f"Delete result: {result}")
        else:
            logger.error(f"Invalid operation: {operation}, destination: {destination}")
            return jsonify({'error': 'Invalid operation'}), 400
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in file operations: {str(e)}")
        return jsonify({'error': str(e)}), 500

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif'}

# Google Drive availability check
@app.route('/api/drive/available')
def drive_available():
    """Check if Google Drive integration is available"""
    return jsonify({
        'available': GOOGLE_DRIVE_AVAILABLE,
        'enabled_in_config': Config.ENABLE_GOOGLE_DRIVE
    })

# Google Drive Authentication Endpoints
@app.route('/auth/google')
def auth_google():
    """Initiate Google OAuth flow"""
    if not GOOGLE_DRIVE_AVAILABLE:
        return jsonify({'error': 'Google Drive integration is not available'}), 503
    
    try:
        auth_url = drive_auth.get_authorization_url()
        return jsonify({'auth_url': auth_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/oauth/callback')
def oauth_callback():
    """Handle OAuth callback"""
    if not GOOGLE_DRIVE_AVAILABLE:
        return redirect('/?auth=error&reason=drive_unavailable')
    
    try:
        authorization_response = request.url
        logger.info(f"OAuth callback received: {authorization_response}")
        
        success = drive_auth.handle_oauth_callback(authorization_response)
        
        if success:
            logger.info("OAuth authentication successful, redirecting to home")
            return redirect('/?drive_connected=true')
        else:
            logger.error("OAuth authentication failed")
            return redirect('/?auth=error&reason=oauth_failed')
            
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        return redirect('/?auth=error&reason=callback_exception')

@app.route('/api/drive/status')
def drive_status():
    """Check Google Drive authentication status"""
    if not GOOGLE_DRIVE_AVAILABLE:
        return jsonify({'authenticated': False, 'error': 'Google Drive integration not available'})
    
    try:
        if drive_auth.is_authenticated():
            test_result = drive_auth.test_connection()
            return jsonify({
                'authenticated': True,
                'user_email': test_result.get('user_email', 'mohanrajav77@gmail.com'),
                'user_name': test_result.get('user_name', 'Mohan Raja'),
                'connection_test': test_result
            })
        else:
            return jsonify({'authenticated': False})
            
    except Exception as e:
        return jsonify({
            'authenticated': False,
            'error': str(e)
        })

@app.route('/api/drive/logout', methods=['POST'])
def drive_logout():
    """Logout from Google Drive"""
    if not GOOGLE_DRIVE_AVAILABLE:
        return jsonify({'error': 'Google Drive integration not available'}), 503
    
    try:
        success = drive_auth.revoke_credentials()
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Google Drive File Operations
@app.route('/api/drive/folders')
def list_drive_folders():
    """List Google Drive folders"""
    if not GOOGLE_DRIVE_AVAILABLE:
        return jsonify({'error': 'Google Drive integration not available'}), 503
    
    try:
        if not drive_auth.is_authenticated():
            return jsonify({'error': 'Not authenticated with Google Drive'}), 401
        
        parent_id = request.args.get('parent_id')
        folders = drive_service.list_folders(parent_id)
        
        return jsonify({
            'success': True,
            'folders': folders
        })
        
    except Exception as e:
        logger.error(f"Error listing drive folders: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/drive/images/<folder_id>')
def list_drive_images(folder_id):
    """List images in a Google Drive folder"""
    try:
        if not drive_auth.is_authenticated():
            return jsonify({'error': 'Not authenticated with Google Drive'}), 401
        
        images = drive_service.list_images_in_folder(folder_id)
        
        return jsonify({
            'success': True,
            'images': images,
            'count': len(images)
        })
        
    except Exception as e:
        logger.error(f"Error listing drive images: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/drive/index', methods=['POST'])
def index_drive_folder():
    """Index photos in a Google Drive folder (HARDCODED for Webcam folder)"""
    if not GOOGLE_DRIVE_AVAILABLE:
        return jsonify({'success': False, 'error': 'Google Drive integration not available'})
    
    try:
        data = request.get_json()
        folder_id = data.get('folder_id')
        folder_name = data.get('folder_name', 'Unknown Folder')
        
        if not folder_id:
            return jsonify({'success': False, 'error': 'Folder ID is required'})
        
        sync_mgr = get_sync_manager(db_manager)
        result = sync_mgr.sync_drive_folder(folder_id, folder_name)
        
        if result['success']:
            return jsonify({
                'success': True,
                'indexed_count': result['synced_count'],
                'message': f'Successfully indexed {result["synced_count"]} photos from {folder_name}'
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Failed to index photos')})
        
    except Exception as e:
        logger.error(f"Error indexing photos: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/drive/sync', methods=['POST'])
def sync_drive_folder():
    """Sync a Google Drive folder"""
    if not GOOGLE_DRIVE_AVAILABLE:
        return jsonify({'success': False, 'error': 'Google Drive integration not available'})
    
    try:
        data = request.get_json()
        folder_id = data.get('folder_id')
        folder_name = data.get('folder_name', 'Unknown Folder')
        
        if not folder_id:
            return jsonify({'success': False, 'error': 'Folder ID is required'})
        
        sync_mgr = get_sync_manager(db_manager)
        result = sync_mgr.sync_drive_folder(folder_id, folder_name)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error starting sync: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/drive/sync/progress')
def get_sync_progress():
    """Get sync progress"""
    try:
        sync_mgr = get_sync_manager(db_manager)
        progress = sync_mgr.get_sync_progress()
        return jsonify(progress)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drive/sync/stop', methods=['POST'])
def stop_sync():
    """Stop current sync operation"""
    try:
        sync_mgr = get_sync_manager(db_manager)
        sync_mgr.stop_sync()
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drive/synced_folders')
def get_synced_folders():
    """Get list of synced Google Drive folders"""
    try:
        sync_mgr = get_sync_manager(db_manager)
        folders = sync_mgr.get_synced_drive_folders()
        return jsonify({
            'success': True,
            'folders': folders
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drive/synced_folders/<folder_id>', methods=['DELETE'])
def remove_synced_folder(folder_id):
    """Remove a synced folder"""
    try:
        sync_mgr = get_sync_manager(db_manager)
        success = sync_mgr.remove_synced_folder(folder_id)
        
        return jsonify({'success': success})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drive/search')
def search_drive():
    """Search Google Drive files"""
    try:
        if not drive_auth.is_authenticated():
            return jsonify({'error': 'Not authenticated with Google Drive'}), 401
        
        query = request.args.get('q', '')
        file_type = request.args.get('type', 'image')
        
        if not query:
            return jsonify({'error': 'Search query required'}), 400
        
        results = drive_service.search_files(query, file_type)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Error searching drive: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug_search')
def debug_search():
    """Debug endpoint to test search functionality"""
    try:
        # Use one of the indexed images as reference
        test_image = '/home/mohan/Pictures/Webcam/2025-09-27-111256.jpg'
        
        # Get face encoding from the test image
        face_data = face_engine.process_image_for_faces(test_image)
        
        if not face_data.get('face_encodings'):
            return jsonify({'error': 'No faces found in test image'})
        
        test_encoding = face_data['face_encodings'][0]
        
        # Perform search with minimum 55% similarity, restricted to current folder
        results = photo_manager.search_similar_faces(test_encoding, tolerance=0.8, min_similarity=0.55, restrict_to_current_folder=True)
        
        return jsonify({
            'test_image': test_image,
            'encoding_shape': test_encoding.shape,
            'results_count': len(results),
            'results': [
                {
                    'file_name': r['file_name'],
                    'similarity': r['similarity'],
                    'distance': r['distance']
                } for r in results
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/debug_db')
def debug_db():
    """Debug endpoint to check database status"""
    try:
        stats = db_manager.get_database_stats()
        folders = db_manager.get_search_folders()
        all_encodings = db_manager.get_all_face_encodings()
        
        return jsonify({
            'database_stats': stats,
            'search_folders': folders,
            'face_encodings_count': len(all_encodings),
            'face_encodings': [
                {
                    'file_name': enc['file_name'],
                    'file_path': enc['file_path'],
                    'encoding_shape': enc['encoding'].shape
                } for enc in all_encodings[:5]  # Show first 5 only
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/debug_oauth')
def debug_oauth():
    """Debug endpoint to check OAuth setup"""
    try:
        import os
        return jsonify({
            'insecure_transport_enabled': os.environ.get('OAUTHLIB_INSECURE_TRANSPORT'),
            'credentials_file_exists': os.path.exists(drive_auth.credentials_file),
            'credentials_file_path': drive_auth.credentials_file,
            'token_file_exists': os.path.exists(drive_auth.token_file),
            'token_file_path': drive_auth.token_file,
            'google_drive_available': GOOGLE_DRIVE_AVAILABLE,
            'current_auth_status': drive_auth.is_authenticated()
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/debug_drive')
def debug_drive():
    """Debug endpoint to check Google Drive data"""
    try:
        if not GOOGLE_DRIVE_AVAILABLE or not drive_auth.is_authenticated():
            return jsonify({'error': 'Google Drive not available or not authenticated'})
        
        # Get raw folder data
        folders = drive_service.list_folders()
        
        # Get user info
        connection_test = drive_auth.test_connection()
        
        # Try to get some files
        try:
            service = drive_service.get_service()
            files = service.files().list(
                pageSize=10,
                fields="files(id, name, mimeType, parents)"
            ).execute()
            all_files = files.get('files', [])
        except Exception as e:
            all_files = []
            
        return jsonify({
            'folders_count': len(folders),
            'folders': folders,
            'user_info': connection_test,
            'all_files_count': len(all_files),
            'all_files': all_files[:5]  # Show first 5 files
        })
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    print("Starting Face-Based Photo Search & Management System")
    print("Web Interface available at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5001)
