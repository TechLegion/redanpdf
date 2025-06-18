from typing import Union, BinaryIO
import os
import shutil
from .log import logger

class Storage:
    def __init__(self):
        # Get the absolute path to the project root
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage"))
        logger.info(f"Initializing storage at: {self.base_dir}")
        
        # Create base storage directory
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Create documents directory
        self.documents_dir = os.path.join(self.base_dir, "documents")
        os.makedirs(self.documents_dir, exist_ok=True)
        logger.info(f"Initialized documents directory at: {self.documents_dir}")

    def _normalize_path(self, path: str) -> str:
        """
        Normalize a path to use forward slashes and remove any double slashes
        """
        # Replace all backslashes with forward slashes
        path = path.replace("\\", "/")
        # Remove any double slashes
        while "//" in path:
            path = path.replace("//", "/")
        return path

    def _convert_to_system_path(self, storage_path: str) -> str:
        """
        Convert a storage path (using forward slashes) to a system path
        """
        # Normalize the storage path first
        storage_path = self._normalize_path(storage_path)
        
        # Split the path into parts
        parts = storage_path.split('/')
        if len(parts) != 3 or parts[0] != 'documents':
            raise ValueError(f"Invalid storage path format: {storage_path}")
        
        # Create the full path using os.path.join
        doc_dir = os.path.join(self.documents_dir, parts[1])
        full_path = os.path.join(doc_dir, parts[2])
        
        # Ensure the path is properly normalized for the current OS
        return os.path.normpath(full_path)

    def _ensure_directory_exists(self, file_path: str) -> None:
        """
        Ensure the directory for a file exists
        """
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")

    def upload_file(self, file_or_path: Union[str, BinaryIO], storage_path: str) -> str:
        """
        Upload a file to storage
        Args:
            file_or_path: Either a file path (str) or a file-like object (BinaryIO)
            storage_path: The path where the file should be stored (format: "documents/doc_id/filename")
        Returns:
            The storage path of the uploaded file
        """
        try:
            # Normalize the storage path
            storage_path = self._normalize_path(storage_path)
            
            # Convert storage path to system path
            full_path = self._convert_to_system_path(storage_path)
            logger.info(f"Full system path: {full_path}")
            
            # Ensure directory exists
            self._ensure_directory_exists(full_path)
            
            # Handle both file paths and file objects
            if isinstance(file_or_path, str):
                # If it's a file path, copy the file
                shutil.copy2(file_or_path, full_path)
            else:
                # If it's a file object, read and write the content
                with open(full_path, 'wb') as f:
                    f.write(file_or_path.read())
            
            # Verify file was created
            if not os.path.exists(full_path):
                raise Exception(f"File was not created at {full_path}")
            
            return storage_path
            
        except Exception as e:
            logger.error(f"Error uploading file to storage: {str(e)}")
            raise Exception(f"Failed to upload file to storage: {str(e)}")

    def get_file(self, storage_path: str) -> str:
        """
        Get the full path to a stored file
        """
        # Normalize the storage path
        storage_path = self._normalize_path(storage_path)
        full_path = self._convert_to_system_path(storage_path)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {full_path}")
            
        return full_path

    def delete_file(self, storage_path: str) -> None:
        """
        Delete a file from storage
        """
        try:
            # Normalize the storage path
            storage_path = self._normalize_path(storage_path)
            full_path = self.get_file(storage_path)
            if os.path.exists(full_path):
                os.remove(full_path)
        except Exception as e:
            logger.error(f"Error deleting file from storage: {str(e)}")
            raise Exception(f"Failed to delete file from storage: {str(e)}") 