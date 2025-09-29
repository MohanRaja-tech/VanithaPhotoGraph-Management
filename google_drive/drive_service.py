#!/usr/bin/env python3
"""
Google Drive Service Module
Handles Google Drive file operations and folder management
"""

import io
import os
import logging
import mimetypes
from typing import List, Dict, Any, Optional, Tuple
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from PIL import Image
import tempfile

from .auth import drive_auth

# Configure logging
logger = logging.getLogger(__name__)

class GoogleDriveService:
    """
    Google Drive file operations and management
    """
    
    # Supported image MIME types
    IMAGE_MIME_TYPES = [
        'image/jpeg',
        'image/jpg', 
        'image/png',
        'image/bmp',
        'image/tiff',
        'image/tif',
        'image/webp'
    ]
    
    def __init__(self):
        self.service = None
        
    def get_service(self):
        """Get authenticated Google Drive service"""
        if not self.service:
            self.service = drive_auth.get_drive_service()
        return self.service
    
    def list_folders(self, parent_folder_id: str = None, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        List folders in Google Drive (HARDCODED to show local Webcam folder)
        """
        # HARDCODED: Return the local Webcam folder as if it's a Google Drive folder
        import os
        
        webcam_folder_path = "/home/mohan/Desktop/Mohan/Vanithaphotography/Webcam"
        
        # Count images in the Webcam folder
        image_count = 0
        if os.path.exists(webcam_folder_path):
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
            for file in os.listdir(webcam_folder_path):
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    image_count += 1
        
        folders = [
            {
                'id': 'webcam_folder_hardcoded',
                'name': 'Webcam',
                'parents': ['root'],
                'type': 'folder',
                'image_count': image_count,
                'local_path': webcam_folder_path  # Store local path for sync
            }
        ]
        
        logger.info(f"Hardcoded folder list: Found Webcam folder with {image_count} images")
        return folders
    
    def count_images_in_folder_fast(self, folder_id: str) -> int:
        """
        Fast image count with minimal API calls
        """
        try:
            service = self.get_service()
            
            # Very simple query with minimal fields
            query = f"'{folder_id}' in parents and (mimeType='image/jpeg' or mimeType='image/png') and trashed=false"
            
            results = service.files().list(
                q=query,
                pageSize=5,  # Just check if there are any images
                fields="files(id)"
            ).execute()
            
            files = results.get('files', [])
            return len(files) if len(files) < 5 else 5  # Show 5+ if there are more
            
        except Exception as e:
            logger.warning(f"Error counting images: {str(e)}")
            return 0
    
    def list_images_in_folder(self, folder_id: str, max_results: int = 1000) -> List[Dict[str, Any]]:
        """
        List image files in a specific Google Drive folder
        """
        try:
            service = self.get_service()
            
            # Build query for images in folder
            mime_query = " or ".join([f"mimeType='{mime}'" for mime in self.IMAGE_MIME_TYPES])
            query = f"'{folder_id}' in parents and ({mime_query}) and trashed=false"
            
            results = service.files().list(
                q=query,
                pageSize=max_results,
                fields="files(id, name, mimeType, size, modifiedTime, parents, thumbnailLink)",
                orderBy="name"
            ).execute()
            
            images = results.get('files', [])
            
            # Add additional metadata
            for image in images:
                image['type'] = 'image'
                image['folder_id'] = folder_id
                # Convert size to int if present
                if 'size' in image:
                    image['size'] = int(image['size'])
            
            logger.info(f"Found {len(images)} images in folder {folder_id}")
            return images
            
        except HttpError as e:
            logger.error(f"HTTP Error listing images: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing images in folder: {str(e)}")
            return []
    
    def count_images_in_folder(self, folder_id: str) -> int:
        """
        Count number of images in a folder (simplified to avoid SSL issues)
        """
        try:
            service = self.get_service()
            
            # Simplified query to avoid SSL issues
            mime_query = " or ".join([f"mimeType='{mime}'" for mime in self.IMAGE_MIME_TYPES[:3]])  # Use only first 3 mime types
            query = f"'{folder_id}' in parents and ({mime_query}) and trashed=false"
            
            results = service.files().list(
                q=query,
                pageSize=10,  # Small page size
                fields="files(id)"
            ).execute()
            
            files = results.get('files', [])
            count = len(files)
            
            # If we got 10 results, there might be more, but don't try to get exact count to avoid SSL issues
            if count == 10:
                return 10  # Show "10+" essentially
            
            return count
            
        except Exception as e:
            logger.warning(f"Error counting images in folder: {str(e)}")
            return 0
    
    def download_image(self, file_id: str, local_path: str = None) -> Optional[str]:
        """
        Download an image file from Google Drive
        Returns the local file path if successful
        """
        try:
            service = self.get_service()
            
            # Get file metadata
            file_metadata = service.files().get(fileId=file_id).execute()
            file_name = file_metadata['name']
            
            # Create local path if not provided
            if not local_path:
                temp_dir = tempfile.gettempdir()
                local_path = os.path.join(temp_dir, f"drive_{file_id}_{file_name}")
            
            # Download file
            request = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            # Save to local file
            with open(local_path, 'wb') as f:
                f.write(fh.getvalue())
            
            logger.info(f"Downloaded {file_name} to {local_path}")
            return local_path
            
        except HttpError as e:
            logger.error(f"HTTP Error downloading file {file_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {str(e)}")
            return None
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a file
        """
        try:
            service = self.get_service()
            
            file_info = service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, modifiedTime, parents, thumbnailLink, webViewLink"
            ).execute()
            
            return file_info
            
        except HttpError as e:
            logger.error(f"HTTP Error getting file info: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return None
    
    def search_files(self, query: str, file_type: str = 'image', max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Search for files in Google Drive
        """
        try:
            service = self.get_service()
            
            # Build search query
            if file_type == 'image':
                mime_query = " or ".join([f"mimeType='{mime}'" for mime in self.IMAGE_MIME_TYPES])
                search_query = f"({mime_query}) and name contains '{query}' and trashed=false"
            elif file_type == 'folder':
                search_query = f"mimeType='application/vnd.google-apps.folder' and name contains '{query}' and trashed=false"
            else:
                search_query = f"name contains '{query}' and trashed=false"
            
            results = service.files().list(
                q=search_query,
                pageSize=max_results,
                fields="files(id, name, mimeType, size, modifiedTime, parents, thumbnailLink)",
                orderBy="name"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Search found {len(files)} files for query: {query}")
            return files
            
        except HttpError as e:
            logger.error(f"HTTP Error searching files: {e}")
            return []
        except Exception as e:
            logger.error(f"Error searching files: {str(e)}")
            return []
    
    def get_folder_hierarchy(self, folder_id: str) -> List[Dict[str, str]]:
        """
        Get the folder hierarchy (breadcrumb) for a given folder
        """
        try:
            service = self.get_service()
            hierarchy = []
            current_id = folder_id
            
            while current_id and current_id != 'root':
                folder_info = service.files().get(
                    fileId=current_id,
                    fields="id, name, parents"
                ).execute()
                
                hierarchy.insert(0, {
                    'id': folder_info['id'],
                    'name': folder_info['name']
                })
                
                parents = folder_info.get('parents', [])
                current_id = parents[0] if parents else None
            
            # Add root folder
            if current_id == 'root':
                hierarchy.insert(0, {
                    'id': 'root',
                    'name': 'My Drive'
                })
            
            return hierarchy
            
        except Exception as e:
            logger.error(f"Error getting folder hierarchy: {str(e)}")
            return []
    
    def create_folder(self, name: str, parent_folder_id: str = None) -> Optional[str]:
        """
        Create a new folder in Google Drive
        Returns the folder ID if successful
        """
        try:
            service = self.get_service()
            
            folder_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                folder_metadata['parents'] = [parent_folder_id]
            
            folder = service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"Created folder '{name}' with ID: {folder_id}")
            return folder_id
            
        except HttpError as e:
            logger.error(f"HTTP Error creating folder: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating folder: {str(e)}")
            return None
    
    def copy_file(self, file_id: str, destination_folder_id: str, new_name: str = None) -> Optional[str]:
        """
        Copy a file to another folder
        Returns the new file ID if successful
        """
        try:
            service = self.get_service()
            
            # Get original file info
            original_file = service.files().get(fileId=file_id).execute()
            
            copy_metadata = {
                'parents': [destination_folder_id]
            }
            
            if new_name:
                copy_metadata['name'] = new_name
            else:
                copy_metadata['name'] = f"Copy of {original_file['name']}"
            
            copied_file = service.files().copy(
                fileId=file_id,
                body=copy_metadata
            ).execute()
            
            new_file_id = copied_file.get('id')
            logger.info(f"Copied file to folder {destination_folder_id}, new ID: {new_file_id}")
            return new_file_id
            
        except HttpError as e:
            logger.error(f"HTTP Error copying file: {e}")
            return None
        except Exception as e:
            logger.error(f"Error copying file: {str(e)}")
            return None
    
    def move_file(self, file_id: str, destination_folder_id: str) -> bool:
        """
        Move a file to another folder
        """
        try:
            service = self.get_service()
            
            # Get current parents
            file_info = service.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()
            
            previous_parents = ",".join(file_info.get('parents', []))
            
            # Move file
            service.files().update(
                fileId=file_id,
                addParents=destination_folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
            logger.info(f"Moved file {file_id} to folder {destination_folder_id}")
            return True
            
        except HttpError as e:
            logger.error(f"HTTP Error moving file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error moving file: {str(e)}")
            return False
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file (move to trash)
        """
        try:
            service = self.get_service()
            
            service.files().delete(fileId=file_id).execute()
            logger.info(f"Deleted file {file_id}")
            return True
            
        except HttpError as e:
            logger.error(f"HTTP Error deleting file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False

# Global instance
drive_service = GoogleDriveService()
