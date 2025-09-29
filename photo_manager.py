import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from face_recognition_engine import FaceRecognitionEngine
from database_manager import DatabaseManager

class PhotoManager:
    """
    Manages photo indexing, searching, and file operations.
    """
    
    def __init__(self, database_manager: DatabaseManager):
        self.db_manager = database_manager
        self.face_engine = FaceRecognitionEngine()
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        self.indexing_progress = 0
        self.indexing_total = 0
        self.indexing_lock = threading.Lock()
        
    def scan_folders_for_images(self, folders: List[str]) -> List[str]:
        """
        Recursively scan folders for image files.
        """
        image_files = []
        
        for folder in folders:
            if not os.path.exists(folder):
                logging.warning(f"Folder does not exist: {folder}")
                continue
                
            try:
                for root, dirs, files in os.walk(folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if self.face_engine.is_supported_image(file_path):
                            image_files.append(file_path)
            except Exception as e:
                logging.error(f"Error scanning folder {folder}: {str(e)}")
        
        return image_files
    
    def index_image(self, image_path: str) -> bool:
        """
        Index a single image - extract faces and store in database.
        """
        try:
            # Check if file exists
            if not os.path.exists(image_path):
                return False
            
            # Get file metadata
            file_stat = os.stat(image_path)
            modification_time = file_stat.st_mtime
            file_size = file_stat.st_size
            file_name = os.path.basename(image_path)
            folder_path = os.path.dirname(image_path)
            
            # Check if already processed and up to date
            if self.db_manager.is_image_processed(image_path, modification_time):
                return True
            
            # Process the image for faces
            face_data = self.face_engine.process_image_for_faces(image_path)
            
            if "error" in face_data:
                logging.error(f"Error processing {image_path}: {face_data['error']}")
                return False
            
            # Add image record to database
            image_id = self.db_manager.add_image_record(
                image_path, file_name, file_size, modification_time,
                face_data['face_count'], folder_path
            )
            
            if image_id is None:
                return False
            
            # Add face encodings
            for i, (location, encoding) in enumerate(zip(face_data['face_locations'], face_data['face_encodings'])):
                self.db_manager.add_face_encoding(image_id, i, encoding, location)
            
            return True
            
        except Exception as e:
            logging.error(f"Error indexing image {image_path}: {str(e)}")
            return False
    
    def index_images_batch(self, image_paths: List[str], max_workers: int = 4) -> Dict:
        """
        Index multiple images using multi-threading.
        """
        self.indexing_total = len(image_paths)
        self.indexing_progress = 0
        
        successful = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_path = {executor.submit(self.index_image, path): path for path in image_paths}
            
            # Process completed tasks
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    result = future.result()
                    if result:
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    logging.error(f"Error processing {path}: {str(e)}")
                    failed += 1
                
                # Update progress
                with self.indexing_lock:
                    self.indexing_progress += 1
        
        return {
            'total': self.indexing_total,
            'successful': successful,
            'failed': failed,
            'progress': self.indexing_progress
        }
    
    def get_indexing_progress(self) -> Tuple[int, int]:
        """
        Get current indexing progress.
        Returns (current, total).
        """
        with self.indexing_lock:
            return self.indexing_progress, self.indexing_total
    
    def search_similar_faces(self, reference_encoding, tolerance: float = 0.6, min_similarity: float = 0.55, restrict_to_current_folder: bool = True) -> List[Dict]:
        """
        Search for images containing similar faces.
        Only returns faces with similarity >= min_similarity (default 55%)
        If restrict_to_current_folder is True, only searches in the currently selected folder
        """
        try:
            # Get all face encodings from database
            all_encodings = self.db_manager.get_all_face_encodings()
            
            if not all_encodings:
                return []
            
            # Get currently selected folders for filtering
            current_folders = []
            if restrict_to_current_folder:
                current_folders = self.db_manager.get_search_folders()
            
            matches = []
            
            for face_data in all_encodings:
                # If restricting to current folder, check if the image is in one of the current folders
                if restrict_to_current_folder and current_folders:
                    image_in_current_folder = False
                    for folder in current_folders:
                        if face_data['file_path'].startswith(folder):
                            image_in_current_folder = True
                            break
                    
                    # Skip this image if it's not in the current folder(s)
                    if not image_in_current_folder:
                        continue
                
                # Compare with reference encoding
                distance = self.face_engine.face_distance([face_data['encoding']], reference_encoding)[0]
                similarity = 1.0 - distance  # Convert distance to similarity score
                
                # Only include faces with similarity >= min_similarity (55% by default)
                if distance <= tolerance and similarity >= min_similarity:
                    matches.append({
                        'file_path': face_data['file_path'],
                        'file_name': face_data['file_name'],
                        'face_location': face_data['face_location'],
                        'distance': distance,
                        'similarity': similarity,
                        'face_index': face_data['face_index']
                    })
            
            # Sort by similarity (highest first)
            matches.sort(key=lambda x: x['similarity'], reverse=True)
            
            return matches
            
        except Exception as e:
            logging.error(f"Error searching similar faces: {str(e)}")
            return []
    
    def copy_files(self, source_paths: List[str], destination_folder: str) -> Dict:
        """
        Copy files to destination folder.
        """
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)
        
        successful = 0
        failed = 0
        errors = []
        
        for source_path in source_paths:
            try:
                if os.path.exists(source_path):
                    file_name = os.path.basename(source_path)
                    dest_path = os.path.join(destination_folder, file_name)
                    
                    # Handle duplicate names
                    counter = 1
                    base_name, ext = os.path.splitext(file_name)
                    while os.path.exists(dest_path):
                        new_name = f"{base_name}_{counter}{ext}"
                        dest_path = os.path.join(destination_folder, new_name)
                        counter += 1
                    
                    shutil.copy2(source_path, dest_path)
                    successful += 1
                else:
                    failed += 1
                    errors.append(f"File not found: {source_path}")
                    
            except Exception as e:
                failed += 1
                errors.append(f"Error copying {source_path}: {str(e)}")
        
        return {
            'successful': successful,
            'failed': failed,
            'errors': errors
        }
    
    def move_files(self, source_paths: List[str], destination_folder: str) -> Dict:
        """
        Move files to destination folder.
        """
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)
        
        successful = 0
        failed = 0
        errors = []
        
        for source_path in source_paths:
            try:
                if os.path.exists(source_path):
                    file_name = os.path.basename(source_path)
                    dest_path = os.path.join(destination_folder, file_name)
                    
                    # Handle duplicate names
                    counter = 1
                    base_name, ext = os.path.splitext(file_name)
                    while os.path.exists(dest_path):
                        new_name = f"{base_name}_{counter}{ext}"
                        dest_path = os.path.join(destination_folder, new_name)
                        counter += 1
                    
                    shutil.move(source_path, dest_path)
                    
                    # Update database with new path
                    self.db_manager.delete_image_and_faces(source_path)
                    successful += 1
                else:
                    failed += 1
                    errors.append(f"File not found: {source_path}")
                    
            except Exception as e:
                failed += 1
                errors.append(f"Error moving {source_path}: {str(e)}")
        
        return {
            'successful': successful,
            'failed': failed,
            'errors': errors
        }
    
    def delete_files(self, file_paths: List[str]) -> Dict:
        """
        Delete files and remove from database.
        """
        successful = 0
        failed = 0
        errors = []
        
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.db_manager.delete_image_and_faces(file_path)
                    successful += 1
                else:
                    # Still try to remove from database
                    self.db_manager.delete_image_and_faces(file_path)
                    failed += 1
                    errors.append(f"File not found: {file_path}")
                    
            except Exception as e:
                failed += 1
                errors.append(f"Error deleting {file_path}: {str(e)}")
        
        return {
            'successful': successful,
            'failed': failed,
            'errors': errors
        }
    
    def get_image_thumbnail(self, image_path: str, size: Tuple[int, int] = (150, 150)) -> Optional[str]:
        """
        Generate thumbnail for an image.
        Returns path to thumbnail or None if failed.
        """
        try:
            from PIL import Image
            
            # Create thumbnails directory
            thumb_dir = os.path.join(os.path.dirname(__file__), "thumbnails")
            if not os.path.exists(thumb_dir):
                os.makedirs(thumb_dir)
            
            # Generate thumbnail filename
            file_name = os.path.basename(image_path)
            name, ext = os.path.splitext(file_name)
            thumb_name = f"{name}_thumb{ext}"
            thumb_path = os.path.join(thumb_dir, thumb_name)
            
            # Check if thumbnail already exists and is newer than original
            if os.path.exists(thumb_path):
                thumb_time = os.path.getmtime(thumb_path)
                image_time = os.path.getmtime(image_path)
                if thumb_time >= image_time:
                    return thumb_path
            
            # Create thumbnail
            with Image.open(image_path) as img:
                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(thumb_path)
                return thumb_path
                
        except Exception as e:
            logging.error(f"Error creating thumbnail for {image_path}: {str(e)}")
            return None
    
    def cleanup_database(self):
        """
        Remove database entries for files that no longer exist.
        """
        try:
            # Get all image records
            all_encodings = self.db_manager.get_all_face_encodings()
            
            removed_count = 0
            for face_data in all_encodings:
                if not os.path.exists(face_data['file_path']):
                    self.db_manager.delete_image_and_faces(face_data['file_path'])
                    removed_count += 1
            
            logging.info(f"Cleaned up {removed_count} orphaned database entries")
            return removed_count
            
        except Exception as e:
            logging.error(f"Error cleaning up database: {str(e)}")
            return 0
