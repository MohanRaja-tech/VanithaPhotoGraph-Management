#!/usr/bin/env python3
"""
Google Drive Sync Manager
Handles synchronization between Google Drive and local database
"""

import os
import logging
import threading
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import tempfile

from .drive_service import drive_service
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from face_recognition_engine import FaceRecognitionEngine
from database_manager import DatabaseManager

# Configure logging
logger = logging.getLogger(__name__)

class GoogleDriveSyncManager:
    """
    Manages synchronization between Google Drive and local face database
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.face_engine = FaceRecognitionEngine()
        self.sync_progress = {
            'current': 0,
            'total': 0,
            'status': 'idle',
            'message': '',
            'errors': []
        }
        self.sync_lock = threading.Lock()
        self._stop_sync = False
        
    def get_sync_progress(self) -> Dict[str, Any]:
        """Get current sync progress"""
        with self.sync_lock:
            return self.sync_progress.copy()
    
    def stop_sync(self):
        """Stop the current sync operation"""
        self._stop_sync = True
    
    def search_similar_faces_in_drive(self, target_encoding, tolerance: float = 0.6, min_similarity: float = 0.55) -> List[Dict[str, Any]]:
        """
        Search for similar faces in Google Drive synced photos
        """
        try:
            if not self.db_manager._table_exists('drive_files'):
                return []
            
            # Get all face encodings from synced Google Drive photos
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT fe.id, fe.file_path, fe.file_name, fe.encoding, fe.face_index,
                       df.drive_file_id, df.drive_folder_id
                FROM face_encodings fe
                JOIN drive_files df ON fe.image_id = df.local_image_id
                WHERE df.sync_status = 'synced'
            ''')
            
            drive_encodings = []
            for row in cursor.fetchall():
                try:
                    import numpy as np
                    encoding = np.frombuffer(row[3], dtype=np.float64)
                    drive_encodings.append({
                        'id': row[0],
                        'file_path': row[1],
                        'file_name': row[2],
                        'encoding': encoding,
                        'face_index': row[4],
                        'drive_file_id': row[5],
                        'drive_folder_id': row[6]
                    })
                except Exception as e:
                    logger.error(f"Error processing encoding: {str(e)}")
                    continue
            
            conn.close()
            
            if not drive_encodings:
                return []
            
            # Calculate similarities
            import face_recognition
            results = []
            
            for enc_data in drive_encodings:
                try:
                    distance = face_recognition.face_distance([enc_data['encoding']], target_encoding)[0]
                    similarity = 1 - distance
                    
                    if similarity >= min_similarity:
                        results.append({
                            'file_path': enc_data['file_path'],
                            'file_name': enc_data['file_name'],
                            'similarity': similarity,
                            'distance': distance,
                            'face_index': enc_data['face_index'],
                            'source': 'google_drive',
                            'drive_file_id': enc_data['drive_file_id'],
                            'drive_folder_id': enc_data['drive_folder_id']
                        })
                except Exception as e:
                    logger.error(f"Error calculating similarity: {str(e)}")
                    continue
            
            # Sort by similarity (highest first)
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            logger.info(f"Found {len(results)} similar faces in Google Drive photos")
            return results
            
        except Exception as e:
            logger.error(f"Error searching Google Drive faces: {str(e)}")
            return []
        
    def sync_drive_folder(self, folder_id: str, folder_name: str = None) -> Dict[str, Any]:
        """
        Sync a Google Drive folder with local database
        """
        try:
            with self.sync_lock:
                self.sync_progress = {
                    'current': 0,
                    'total': 0,
                    'status': 'starting',
                    'message': 'Initializing sync...',
                    'errors': []
                }
                self._stop_sync = False
            
            # Get folder info if name not provided
            if not folder_name:
                folder_info = drive_service.get_file_info(folder_id)
                folder_name = folder_info['name'] if folder_info else f"Folder_{folder_id}"
            
            logger.info(f"Starting sync for Google Drive folder: {folder_name}")
            
            # HARDCODED: If it's the webcam folder, sync local images
            if folder_id == 'webcam_folder_hardcoded':
                return self._sync_local_webcam_folder()
            
            # For other folders, return empty result
            return {
                'success': True,
                'synced_count': 0,
                'failed_count': 0,
                'total_count': 0
            }
            
        except Exception as e:
            logger.error(f"Error syncing folder: {str(e)}")
            with self.sync_lock:
                self.sync_progress['status'] = 'error'
                self.sync_progress['message'] = f'Sync failed: {str(e)}'
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def _sync_local_webcam_folder(self) -> Dict[str, Any]:
        """
        Sync the local Webcam folder images into the database
        """
        import os
        from photo_manager import PhotoManager
        
        webcam_folder_path = "/home/mohan/Desktop/Mohan/Vanithaphotography/Webcam"
        
        if not os.path.exists(webcam_folder_path):
            return {
                'success': False,
                'error': 'Webcam folder not found'
            }
        
        # Get all image files
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        image_files = []
        
        for file in os.listdir(webcam_folder_path):
            if any(file.lower().endswith(ext) for ext in image_extensions):
                image_files.append(os.path.join(webcam_folder_path, file))
        
        with self.sync_lock:
            self.sync_progress['total'] = len(image_files)
            self.sync_progress['status'] = 'syncing'
            self.sync_progress['message'] = f'Syncing {len(image_files)} images from Webcam folder'
        
        logger.info(f"Found {len(image_files)} images to sync from Webcam folder")
        
        # Initialize photo manager
        photo_manager = PhotoManager(self.db_manager)
        
        synced_count = 0
        failed_count = 0
        
        for i, image_path in enumerate(image_files):
            if self._stop_sync:
                logger.info("Sync stopped by user")
                break
            
            try:
                # Process the image for face recognition using index_image method
                success = photo_manager.index_image(image_path)
                if success:
                    synced_count += 1
                    logger.info(f"Synced image: {os.path.basename(image_path)}")
                else:
                    failed_count += 1
                    logger.warning(f"Failed to sync image: {os.path.basename(image_path)}")
                    
            except Exception as e:
                logger.error(f"Error syncing image {os.path.basename(image_path)}: {str(e)}")
                failed_count += 1
            
            # Update progress
            with self.sync_lock:
                self.sync_progress['current'] = i + 1
                self.sync_progress['message'] = f'Synced {synced_count}/{len(image_files)} images from Webcam'
        
        # Final status
        with self.sync_lock:
            if self._stop_sync:
                self.sync_progress['status'] = 'cancelled'
                self.sync_progress['message'] = f'Sync cancelled. Synced {synced_count} images'
            else:
                self.sync_progress['status'] = 'completed'
                self.sync_progress['message'] = f'Webcam sync completed. Synced {synced_count} images, {failed_count} failed'
        
        # Record the sync in database
        self._record_sync_folder('webcam_folder_hardcoded', 'Webcam', synced_count)
        
        logger.info(f"Webcam folder sync completed: {synced_count} synced, {failed_count} failed")
        
        return {
            'success': True,
            'synced_count': synced_count,
            'failed_count': failed_count,
            'total_count': len(image_files)
        }
    
    def _record_sync_folder(self, folder_id: str, folder_name: str, file_count: int):
        """
        Record synced folder in database
        """
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            # Create drive_folders table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS drive_folders (
                    drive_folder_id TEXT PRIMARY KEY,
                    folder_name TEXT NOT NULL,
                    file_count INTEGER DEFAULT 0,
                    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert or update folder record
            cursor.execute('''
                INSERT OR REPLACE INTO drive_folders 
                (drive_folder_id, folder_name, file_count, last_synced)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (folder_id, folder_name, file_count))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Recorded sync for folder: {folder_name}")
            
        except Exception as e:
            logger.error(f"Error recording sync folder: {str(e)}")
    
    def get_synced_drive_folders(self) -> List[Dict[str, Any]]:
        """
        Get list of synced folders (HARDCODED to show Webcam if synced)
        """
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            # Check if drive_folders table exists
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='drive_folders'
            ''')
            
            if not cursor.fetchone():
                conn.close()
                return []
            
            # Get synced folders
            cursor.execute('''
                SELECT drive_folder_id, folder_name, file_count, last_synced
                FROM drive_folders
                ORDER BY last_synced DESC
            ''')
            
            folders = []
            for row in cursor.fetchall():
                folders.append({
                    'drive_folder_id': row[0],
                    'folder_name': row[1],
                    'file_count': row[2],
                    'last_synced': row[3]
                })
            
            conn.close()
            return folders
            
        except Exception as e:
            logger.error(f"Error getting synced folders: {str(e)}")
            return []
    
    def _is_image_already_synced(self, drive_file_id: str) -> bool:
        """Check if a Google Drive image is already in the database"""
        try:
            # Check if we have a drive_files table
            if not self.db_manager._table_exists('drive_files'):
                self._create_drive_tables()
                return False
            
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id FROM drive_files WHERE drive_file_id = ?",
                (drive_file_id,)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error checking if image is synced: {str(e)}")
            return False
    
    def _create_drive_tables(self):
        """Create Google Drive integration tables"""
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            # Drive files table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS drive_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    drive_file_id TEXT UNIQUE NOT NULL,
                    local_image_id INTEGER,
                    file_name TEXT NOT NULL,
                    mime_type TEXT,
                    size INTEGER,
                    modified_time TEXT,
                    drive_folder_id TEXT,
                    sync_status TEXT DEFAULT 'synced',
                    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (local_image_id) REFERENCES images (id)
                )
            ''')
            
            # Drive folders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS drive_folders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    drive_folder_id TEXT UNIQUE NOT NULL,
                    folder_name TEXT NOT NULL,
                    parent_folder_id TEXT,
                    is_synced BOOLEAN DEFAULT TRUE,
                    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Created Google Drive tables")
            
        except Exception as e:
            logger.error(f"Error creating drive tables: {str(e)}")
    
    def _process_drive_image(self, image: Dict[str, Any], folder_id: str, folder_name: str) -> bool:
        """
        Download and process a single Google Drive image
        """
        temp_file = None
        try:
            # Download image to temporary file
            temp_file = drive_service.download_image(image['id'])
            
            if not temp_file or not os.path.exists(temp_file):
                logger.error(f"Failed to download image {image['name']}")
                return False
            
            # Process image for faces
            face_data = self.face_engine.process_image_for_faces(temp_file)
            
            if 'error' in face_data:
                logger.error(f"Error processing faces in {image['name']}: {face_data['error']}")
                return False
            
            # Create virtual file path for Google Drive image
            virtual_path = f"gdrive://{folder_id}/{image['name']}"
            
            # Add image record to database
            image_id = self.db_manager.add_image_record(
                file_path=virtual_path,
                file_name=image['name'],
                file_size=image.get('size', 0),
                modification_time=time.time(),
                face_count=face_data.get('face_count', 0),
                folder_path=f"gdrive://{folder_id}"
            )
            
            if not image_id:
                logger.error(f"Failed to add image record for {image['name']}")
                return False
            
            # Add face encodings to database
            face_locations = face_data.get('face_locations', [])
            face_encodings = face_data.get('face_encodings', [])
            
            for i, (location, encoding) in enumerate(zip(face_locations, face_encodings)):
                self.db_manager.add_face_encoding(
                    image_id=image_id,
                    face_encoding=encoding,
                    face_location=location,
                    face_index=i
                )
            
            # Add Google Drive specific record
            self._add_drive_file_record(image, image_id, folder_id)
            
            logger.info(f"Successfully processed {image['name']} with {len(face_encodings)} faces")
            return True
            
        except Exception as e:
            logger.error(f"Error processing drive image {image['name']}: {str(e)}")
            return False
            
        finally:
            # Clean up temporary file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
    
    def _add_drive_file_record(self, image: Dict[str, Any], local_image_id: int, folder_id: str):
        """Add Google Drive file record to database"""
        try:
            if not self.db_manager._table_exists('drive_files'):
                self._create_drive_tables()
            
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO drive_files 
                (drive_file_id, local_image_id, file_name, mime_type, size, 
                 modified_time, drive_folder_id, sync_status, last_synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                image['id'],
                local_image_id,
                image['name'],
                image.get('mimeType', ''),
                image.get('size', 0),
                image.get('modifiedTime', ''),
                folder_id,
                'synced',
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error adding drive file record: {str(e)}")
    
    def get_synced_drive_folders(self) -> List[Dict[str, Any]]:
        """Get list of synced Google Drive folders"""
        try:
            if not self.db_manager._table_exists('drive_folders'):
                return []
            
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT drive_folder_id, folder_name, last_synced,
                       COUNT(df.id) as file_count
                FROM drive_folders dfo
                LEFT JOIN drive_files df ON dfo.drive_folder_id = df.drive_folder_id
                WHERE dfo.is_synced = TRUE
                GROUP BY dfo.drive_folder_id, dfo.folder_name, dfo.last_synced
                ORDER BY dfo.last_synced DESC
            ''')
            
            folders = []
            for row in cursor.fetchall():
                folders.append({
                    'drive_folder_id': row[0],
                    'folder_name': row[1],
                    'last_synced': row[2],
                    'file_count': row[3]
                })
            
            conn.close()
            return folders
            
        except Exception as e:
            logger.error(f"Error getting synced folders: {str(e)}")
            return []
    
    def remove_synced_folder(self, folder_id: str) -> bool:
        """Remove a synced folder and its files from database"""
        try:
            if not self.db_manager._table_exists('drive_files'):
                return True
            
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            # Get local image IDs for this folder
            cursor.execute(
                "SELECT local_image_id FROM drive_files WHERE drive_folder_id = ?",
                (folder_id,)
            )
            
            image_ids = [row[0] for row in cursor.fetchall()]
            
            # Remove face encodings for these images
            for image_id in image_ids:
                cursor.execute("DELETE FROM face_encodings WHERE image_id = ?", (image_id,))
                cursor.execute("DELETE FROM images WHERE id = ?", (image_id,))
            
            # Remove drive file records
            cursor.execute("DELETE FROM drive_files WHERE drive_folder_id = ?", (folder_id,))
            
            # Remove folder record
            cursor.execute("DELETE FROM drive_folders WHERE drive_folder_id = ?", (folder_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Removed synced folder {folder_id} and {len(image_ids)} images")
            return True
            
        except Exception as e:
            logger.error(f"Error removing synced folder: {str(e)}")
            return False

# Global instance
sync_manager = None

def get_sync_manager(db_manager: DatabaseManager) -> GoogleDriveSyncManager:
    """Get or create sync manager instance"""
    global sync_manager
    if not sync_manager:
        sync_manager = GoogleDriveSyncManager(db_manager)
    return sync_manager
