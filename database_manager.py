import sqlite3
import json
import numpy as np
import os
from typing import List, Dict, Tuple, Optional
import logging
from datetime import datetime
import pickle

class DatabaseManager:
    """
    Manages the local SQLite database for storing face encodings and image metadata.
    """
    
    def __init__(self, db_path: str = "face_database.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """
        Initialize the database with required tables.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Images table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size INTEGER,
                    modification_time REAL,
                    face_count INTEGER DEFAULT 0,
                    processed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    folder_path TEXT
                )
            ''')
            
            # Face encodings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS face_encodings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_id INTEGER,
                    face_index INTEGER,
                    encoding_data BLOB,
                    face_location TEXT,
                    confidence_score REAL,
                    FOREIGN KEY (image_id) REFERENCES images (id) ON DELETE CASCADE
                )
            ''')
            
            # Search folders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_folders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    folder_path TEXT UNIQUE NOT NULL,
                    added_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_path ON images(file_path)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_face_encodings_image_id ON face_encodings(image_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_folders_active ON search_folders(is_active)')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error initializing database: {str(e)}")
    
    def add_search_folder(self, folder_path: str) -> bool:
        """
        Add a folder to the search scope.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO search_folders (folder_path, is_active)
                VALUES (?, 1)
            ''', (folder_path,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logging.error(f"Error adding search folder {folder_path}: {str(e)}")
            return False
    
    def get_search_folders(self) -> List[str]:
        """
        Get all active search folders.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT folder_path FROM search_folders WHERE is_active = 1')
            folders = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            return folders
            
        except Exception as e:
            logging.error(f"Error getting search folders: {str(e)}")
            return []
    
    def remove_search_folder(self, folder_path: str) -> bool:
        """
        Remove a folder from the search scope.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('UPDATE search_folders SET is_active = 0 WHERE folder_path = ?', (folder_path,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logging.error(f"Error removing search folder {folder_path}: {str(e)}")
            return False
    
    def add_image_record(self, file_path: str, file_name: str, file_size: int, 
                        modification_time: float, face_count: int, folder_path: str) -> Optional[int]:
        """
        Add an image record to the database.
        Returns the image ID if successful.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO images 
                (file_path, file_name, file_size, modification_time, face_count, folder_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (file_path, file_name, file_size, modification_time, face_count, folder_path))
            
            image_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return image_id
            
        except Exception as e:
            logging.error(f"Error adding image record {file_path}: {str(e)}")
            return None
    
    def add_face_encoding(self, image_id: int, face_index: int, encoding: np.ndarray, 
                         face_location: Tuple, confidence_score: float = 1.0) -> bool:
        """
        Add a face encoding to the database.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Serialize the encoding
            encoding_blob = pickle.dumps(encoding)
            location_json = json.dumps(face_location)
            
            cursor.execute('''
                INSERT INTO face_encodings 
                (image_id, face_index, encoding_data, face_location, confidence_score)
                VALUES (?, ?, ?, ?, ?)
            ''', (image_id, face_index, encoding_blob, location_json, confidence_score))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logging.error(f"Error adding face encoding for image {image_id}: {str(e)}")
            return False
    
    def get_image_by_path(self, file_path: str) -> Optional[Dict]:
        """
        Get image record by file path.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, file_path, file_name, file_size, modification_time, 
                       face_count, processed_time, folder_path
                FROM images WHERE file_path = ?
            ''', (file_path,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'file_path': row[1],
                    'file_name': row[2],
                    'file_size': row[3],
                    'modification_time': row[4],
                    'face_count': row[5],
                    'processed_time': row[6],
                    'folder_path': row[7]
                }
            return None
            
        except Exception as e:
            logging.error(f"Error getting image by path {file_path}: {str(e)}")
            return None
    
    def get_all_face_encodings(self) -> List[Dict]:
        """
        Get all face encodings from the database.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT fe.id, fe.image_id, fe.face_index, fe.encoding_data, 
                       fe.face_location, fe.confidence_score, i.file_path, i.file_name
                FROM face_encodings fe
                JOIN images i ON fe.image_id = i.id
            ''')
            
            encodings = []
            for row in cursor.fetchall():
                encoding = pickle.loads(row[3])
                face_location = json.loads(row[4])
                
                encodings.append({
                    'id': row[0],
                    'image_id': row[1],
                    'face_index': row[2],
                    'encoding': encoding,
                    'face_location': face_location,
                    'confidence_score': row[5],
                    'file_path': row[6],
                    'file_name': row[7]
                })
            
            conn.close()
            return encodings
            
        except Exception as e:
            logging.error(f"Error getting all face encodings: {str(e)}")
            return []
    
    def get_face_encodings_by_image(self, image_id: int) -> List[Dict]:
        """
        Get face encodings for a specific image.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, face_index, encoding_data, face_location, confidence_score
                FROM face_encodings WHERE image_id = ?
                ORDER BY face_index
            ''', (image_id,))
            
            encodings = []
            for row in cursor.fetchall():
                encoding = pickle.loads(row[2])
                face_location = json.loads(row[3])
                
                encodings.append({
                    'id': row[0],
                    'face_index': row[1],
                    'encoding': encoding,
                    'face_location': face_location,
                    'confidence_score': row[4]
                })
            
            conn.close()
            return encodings
            
        except Exception as e:
            logging.error(f"Error getting face encodings for image {image_id}: {str(e)}")
            return []
    
    def is_image_processed(self, file_path: str, modification_time: float) -> bool:
        """
        Check if an image has been processed and is up to date.
        """
        try:
            image_record = self.get_image_by_path(file_path)
            if image_record and image_record['modification_time'] >= modification_time:
                return True
            return False
            
        except Exception as e:
            logging.error(f"Error checking if image is processed {file_path}: {str(e)}")
            return False
    
    def delete_image_and_faces(self, file_path: str) -> bool:
        """
        Delete an image and all its associated face encodings.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get image ID first
            cursor.execute('SELECT id FROM images WHERE file_path = ?', (file_path,))
            row = cursor.fetchone()
            
            if row:
                image_id = row[0]
                
                # Delete face encodings
                cursor.execute('DELETE FROM face_encodings WHERE image_id = ?', (image_id,))
                
                # Delete image record
                cursor.execute('DELETE FROM images WHERE id = ?', (image_id,))
                
                conn.commit()
            
            conn.close()
            return True
            
        except Exception as e:
            logging.error(f"Error deleting image and faces {file_path}: {str(e)}")
            return False
    
    def get_database_stats(self) -> Dict:
        """
        Get database statistics.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Count total images
            cursor.execute("SELECT COUNT(*) FROM images")
            total_images = cursor.fetchone()[0]
            
            # Count total faces
            cursor.execute("SELECT COUNT(*) FROM face_encodings")
            total_faces = cursor.fetchone()[0]
            
            # Count active folders
            cursor.execute("SELECT COUNT(*) FROM search_folders")
            active_folders = cursor.fetchone()[0]
            
            # Get database file size
            database_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            
            conn.close()
            
            return {
                'total_images': total_images,
                'total_faces': total_faces,
                'active_folders': active_folders,
                'database_size': database_size
            }
            
        except Exception as e:
            logging.error(f"Error getting database stats: {str(e)}")
            return {
                'total_images': 0,
                'total_faces': 0,
                'active_folders': 0,
                'database_size': 0
            }

    def get_all_face_encodings(self) -> List[Dict]:
        """
        Get all face encodings from the database.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT fe.id, fe.image_id, fe.face_index, fe.encoding_data, 
                       fe.face_location, fe.confidence_score, i.file_path, i.file_name
                FROM face_encodings fe
                JOIN images i ON fe.image_id = i.id
            ''')
            
            encodings = []
            for row in cursor.fetchall():
                encoding = pickle.loads(row[3])
                face_location = json.loads(row[4])
                
                encodings.append({
                    'id': row[0],
                    'image_id': row[1],
                    'face_index': row[2],
                    'encoding': encoding,
                    'face_location': face_location,
                    'confidence_score': row[5],
                    'file_path': row[6],
                    'file_name': row[7]
                })
            
            conn.close()
            return encodings
            
        except Exception as e:
            logging.error(f"Error getting all face encodings: {str(e)}")
            return []
    
    def _table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            ''', (table_name,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result is not None
            
        except Exception as e:
            logging.error(f"Error checking if table exists: {str(e)}")
            return False
    
    def _get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
