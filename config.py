"""
Configuration settings for the Face-Based Photo Search & Management System
"""

import os
from typing import Dict, Any

class Config:
    """
    Configuration class for application settings.
    """
    
    # Database settings
    DATABASE_PATH = "face_database.db"
    
    # Face recognition settings
    FACE_RECOGNITION_MODEL = "hog"  # Options: "hog", "cnn"
    FACE_SIMILARITY_TOLERANCE = 0.6  # Lower = more strict matching
    FACE_DETECTION_SCALE_FACTOR = 1.1
    FACE_DETECTION_MIN_NEIGHBORS = 5
    FACE_DETECTION_MIN_SIZE = (30, 30)
    
    # Image processing settings
    SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
    THUMBNAIL_SIZE = (150, 150)
    PREVIEW_IMAGE_SIZE = (300, 300)
    
    # Performance settings
    MAX_WORKER_THREADS = 4
    BATCH_SIZE = 100
    
    # GUI settings
    WINDOW_SIZE = "1200x800"
    MIN_WINDOW_SIZE = "800x600"
    
    # Logging settings
    LOG_LEVEL = "INFO"
    LOG_FILE = "photo_search.log"
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # File operation settings
    ENABLE_FILE_OPERATIONS = True
    CONFIRM_DESTRUCTIVE_OPERATIONS = True
    
    # Cache settings
    ENABLE_THUMBNAIL_CACHE = True
    THUMBNAIL_CACHE_DIR = "thumbnails"
    MAX_CACHE_SIZE_MB = 500
    
    # Google Drive settings
    ENABLE_GOOGLE_DRIVE = True  # Set to False to disable Google Drive integration
    GOOGLE_DRIVE_CREDENTIALS_FILE = "client_secret_707608163201-e7sej2luqsn14bnhh5ro58jdnmno0mvi.apps.googleusercontent.com.json"
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """
        Get configuration as dictionary.
        """
        config = {}
        for attr in dir(cls):
            if not attr.startswith('_') and not callable(getattr(cls, attr)):
                config[attr] = getattr(cls, attr)
        return config
    
    @classmethod
    def update_from_dict(cls, config_dict: Dict[str, Any]):
        """
        Update configuration from dictionary.
        """
        for key, value in config_dict.items():
            if hasattr(cls, key):
                setattr(cls, key, value)
    
    @classmethod
    def save_to_file(cls, file_path: str = "config.json"):
        """
        Save configuration to JSON file.
        """
        import json
        config_dict = cls.get_config_dict()
        
        # Convert sets to lists for JSON serialization
        if 'SUPPORTED_IMAGE_FORMATS' in config_dict:
            config_dict['SUPPORTED_IMAGE_FORMATS'] = list(config_dict['SUPPORTED_IMAGE_FORMATS'])
        
        with open(file_path, 'w') as f:
            json.dump(config_dict, f, indent=4)
    
    @classmethod
    def load_from_file(cls, file_path: str = "config.json"):
        """
        Load configuration from JSON file.
        """
        import json
        
        if not os.path.exists(file_path):
            return
        
        try:
            with open(file_path, 'r') as f:
                config_dict = json.load(f)
            
            # Convert lists back to sets
            if 'SUPPORTED_IMAGE_FORMATS' in config_dict:
                config_dict['SUPPORTED_IMAGE_FORMATS'] = set(config_dict['SUPPORTED_IMAGE_FORMATS'])
            
            cls.update_from_dict(config_dict)
            
        except Exception as e:
            print(f"Warning: Failed to load config from {file_path}: {e}")

# Load configuration from file if it exists
Config.load_from_file()
