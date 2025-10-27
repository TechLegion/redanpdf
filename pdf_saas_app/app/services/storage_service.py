import os
import shutil
import uuid
from typing import BinaryIO, Optional
import boto3
from azure.storage.blob import BlobServiceClient
from app.config import settings

class StorageService:
    """Service for handling file storage operations"""
    
    def __init__(self):
        self.storage_type = settings.STORAGE_TYPE
        
        if self.storage_type == "s3":
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            self.bucket_name = settings.S3_BUCKET_NAME
        
        elif self.storage_type == "azure":
            self.blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_CONNECTION_STRING)
            self.container_name = settings.AZURE_CONTAINER_NAME
        
        elif self.storage_type == "local":
            os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
    
    def _get_unique_filename(self, original_filename: str) -> str:
        """Generate a unique filename to avoid conflicts"""
        filename, extension = os.path.splitext(original_filename)
        return f"{filename}_{str(uuid.uuid4())}{extension}"
    
    def upload_file(self, file_path: str, original_filename: str) -> str:
        """
        Upload a file to the configured storage
        Returns: URL or path of the uploaded file
        """
        unique_filename = self._get_unique_filename(original_filename)
        
        print(f"Storage service - storage_type: {self.storage_type}")
        print(f"Storage service - bucket_name: {self.bucket_name}")
        print(f"Storage service - uploading file: {file_path} as {unique_filename}")
        
        if self.storage_type == "s3":
            # Upload to S3
            with open(file_path, "rb") as file_data:
                self.s3_client.upload_fileobj(
                    file_data, 
                    self.bucket_name, 
                    unique_filename
                )
            s3_url = f"https://{self.bucket_name}.s3.amazonaws.com/{unique_filename}"
            print(f"Storage service - returning S3 URL: {s3_url}")
            return s3_url
        
        elif self.storage_type == "azure":
            # Upload to Azure Blob Storage
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=unique_filename
            )
            with open(file_path, "rb") as file_data:
                blob_client.upload_blob(file_data)
            return blob_client.url
        
        else:
            # Local storage
            # Ensure the storage path exists
            os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
            
            # Create the full destination path using os.path.join
            destination_path = os.path.join(settings.LOCAL_STORAGE_PATH, unique_filename)
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            
            # Copy the file
            shutil.copyfile(file_path, destination_path)
            
            # Return the relative path from LOCAL_STORAGE_PATH
            relative_path = os.path.relpath(destination_path, settings.LOCAL_STORAGE_PATH)
            return relative_path.replace("\\", "/")
    
    def upload_file_object(self, file_object: BinaryIO, original_filename: str) -> str:
        """
        Upload a file-like object to the configured storage
        Returns: URL or path of the uploaded file
        """
        unique_filename = self._get_unique_filename(original_filename)
        
        if self.storage_type == "s3":
            # Upload to S3
            self.s3_client.upload_fileobj(
                file_object, 
                self.bucket_name, 
                unique_filename
            )
            return f"https://{self.bucket_name}.s3.amazonaws.com/{unique_filename}"
        
        elif self.storage_type == "azure":
            # Upload to Azure Blob Storage
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=unique_filename
            )
            blob_client.upload_blob(file_object)
            return blob_client.url
        
        else:
            # Local storage
            # Ensure the storage path exists
            os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
            
            # Create the full destination path using os.path.join
            destination_path = os.path.join(settings.LOCAL_STORAGE_PATH, unique_filename)
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            
            # Write the file
            with open(destination_path, "wb") as dest_file:
                shutil.copyfileobj(file_object, dest_file)
            
            # Return the normalized path with forward slashes
            return destination_path.replace("\\", "/")
    
    def get_file(self, file_identifier: str) -> str:
        """
        Get a file from storage
        For local storage: returns the path
        For S3/Azure: downloads to a temp location and returns that path
        """
        if self.storage_type == "local":
            # For local storage, file_identifier is the path
            # Convert to absolute path if it's relative
            if not os.path.isabs(file_identifier):
                file_identifier = os.path.join(settings.LOCAL_STORAGE_PATH, file_identifier)
            
            # Normalize the path
            file_identifier = os.path.normpath(file_identifier)
            
            if os.path.exists(file_identifier):
                # Ensure we return a string path, not a Path object
                return str(file_identifier)
            else:
                raise FileNotFoundError(f"File not found: {file_identifier}")
        
        # For S3 and Azure, we need to download the file
        temp_dir = os.path.join(os.getcwd(), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        filename = os.path.basename(file_identifier)
        temp_path = os.path.join(temp_dir, filename)
        
        if self.storage_type == "s3":
            # Parse the S3 URL to get the key
            key = file_identifier.split(f"https://{self.bucket_name}.s3.amazonaws.com/")[1]
            self.s3_client.download_file(self.bucket_name, key, temp_path)
        
        elif self.storage_type == "azure":
            # Get blob name from URL
            blob_name = os.path.basename(file_identifier)
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_name
            )
            
            with open(temp_path, "wb") as file:
                download_stream = blob_client.download_blob()
                file.write(download_stream.readall())
        
        # Ensure we return a string path
        return str(temp_path)
    
    def delete_file(self, file_identifier: str) -> bool:
        """Delete a file from storage"""
        try:
            if self.storage_type == "local":
                if os.path.exists(file_identifier):
                    os.remove(file_identifier)
                    return True
                return False
            
            elif self.storage_type == "s3":
                # Parse the S3 URL to get the key
                key = file_identifier.split(f"https://{self.bucket_name}.s3.amazonaws.com/")[1]
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
                return True
            
            elif self.storage_type == "azure":
                # Get blob name from URL
                blob_name = os.path.basename(file_identifier)
                blob_client = self.blob_service_client.get_blob_client(
                    container=self.container_name, 
                    blob=blob_name
                )
                blob_client.delete_blob()
                return True
            
            return False
        except Exception:
            return False