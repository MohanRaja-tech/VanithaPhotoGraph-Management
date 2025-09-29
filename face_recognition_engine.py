import face_recognition
import numpy as np
from PIL import Image
import os
from typing import List, Tuple, Dict, Optional
import pickle
import logging

class FaceRecognitionEngine:
    """
    Core engine for face detection, recognition, and feature extraction.
    """
    
    def __init__(self):
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        
    def detect_faces_opencv(self, image_path: str) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces using face_recognition library (fallback method).
        Returns list of (x, y, width, height) tuples.
        """
        try:
            # Load image and get face locations
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image, model="hog")
            
            # Convert from (top, right, bottom, left) to (x, y, width, height)
            faces = []
            for (top, right, bottom, left) in face_locations:
                x, y = left, top
                w, h = right - left, bottom - top
                faces.append((x, y, w, h))
            
            return faces
        except Exception as e:
            logging.error(f"Error detecting faces in {image_path}: {str(e)}")
            return []
    
    def extract_face_encodings(self, image_path: str) -> List[np.ndarray]:
        """
        Extract face encodings using face_recognition library.
        Returns list of 128-dimensional face encodings.
        """
        try:
            # Load image
            image = face_recognition.load_image_file(image_path)
            
            # Find face locations
            face_locations = face_recognition.face_locations(image, model="hog")
            
            # Extract face encodings
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            return face_encodings
        except Exception as e:
            logging.error(f"Error extracting face encodings from {image_path}: {str(e)}")
            return []
    
    def get_face_locations_and_encodings(self, image_path: str) -> Tuple[List[Tuple], List[np.ndarray]]:
        """
        Get both face locations and encodings for an image.
        Returns (face_locations, face_encodings).
        """
        try:
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image, model="hog")
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            return face_locations, face_encodings
        except Exception as e:
            logging.error(f"Error processing {image_path}: {str(e)}")
            return [], []
    
    def compare_faces(self, known_encoding: np.ndarray, unknown_encodings: List[np.ndarray], tolerance: float = 0.6) -> List[bool]:
        """
        Compare a known face encoding against a list of unknown encodings.
        Returns list of boolean matches.
        """
        try:
            if len(unknown_encodings) == 0:
                return []
            
            matches = face_recognition.compare_faces(unknown_encodings, known_encoding, tolerance=tolerance)
            return matches
        except Exception as e:
            logging.error(f"Error comparing faces: {str(e)}")
            return []
    
    def face_distance(self, known_encoding: np.ndarray, unknown_encodings: List[np.ndarray]) -> List[float]:
        """
        Calculate face distances (lower is more similar).
        Returns list of distances.
        """
        try:
            if len(unknown_encodings) == 0:
                return []
            
            distances = face_recognition.face_distance(unknown_encodings, known_encoding)
            return distances.tolist()
        except Exception as e:
            logging.error(f"Error calculating face distances: {str(e)}")
            return []
    
    def extract_face_from_image(self, image_path: str, face_location: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """
        Extract a specific face region from an image.
        face_location: (top, right, bottom, left)
        """
        try:
            image = face_recognition.load_image_file(image_path)
            top, right, bottom, left = face_location
            
            # Extract face region
            face_image = image[top:bottom, left:right]
            return face_image
        except Exception as e:
            logging.error(f"Error extracting face from {image_path}: {str(e)}")
            return None
    
    def is_supported_image(self, file_path: str) -> bool:
        """
        Check if the file is a supported image format.
        """
        return os.path.splitext(file_path.lower())[1] in self.supported_formats
    
    def process_image_for_faces(self, image_path: str) -> Dict:
        """
        Complete face processing for an image.
        Returns dictionary with face locations, encodings, and metadata.
        """
        if not self.is_supported_image(image_path):
            return {"error": "Unsupported image format"}
        
        if not os.path.exists(image_path):
            return {"error": "File not found"}
        
        try:
            face_locations, face_encodings = self.get_face_locations_and_encodings(image_path)
            
            result = {
                "image_path": image_path,
                "face_count": len(face_locations),
                "face_locations": face_locations,
                "face_encodings": face_encodings,
                "timestamp": os.path.getmtime(image_path),
                "file_size": os.path.getsize(image_path)
            }
            
            return result
        except Exception as e:
            return {"error": f"Processing failed: {str(e)}"}
    
    def save_encodings_to_file(self, encodings_data: Dict, file_path: str):
        """
        Save face encodings data to a pickle file.
        """
        try:
            with open(file_path, 'wb') as f:
                pickle.dump(encodings_data, f)
        except Exception as e:
            logging.error(f"Error saving encodings to {file_path}: {str(e)}")
    
    def load_encodings_from_file(self, file_path: str) -> Dict:
        """
        Load face encodings data from a pickle file.
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    return pickle.load(f)
            return {}
        except Exception as e:
            logging.error(f"Error loading encodings from {file_path}: {str(e)}")
            return {}
