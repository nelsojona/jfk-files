#!/usr/bin/env python3
"""
Upload Consolidated JSON to GPT Knowledge

This script uploads the consolidated JFK Files JSON to the GPT knowledge base.
It handles validation, authentication, and the upload process.
"""

import json
import os
import sys
import argparse
import time
from typing import Dict, List, Tuple, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Constants for OpenAI API interaction
API_BASE = "https://api.openai.com/v1"
MAX_RETRIES = 3
TIMEOUT = 60  # seconds
MAX_UPLOAD_SIZE_MB = 20  # OpenAI's limit for GPT knowledge upload

class GPTUploader:
    """Handles the upload of JSON data to GPT knowledge base."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the uploader with API credentials."""
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Either provide it as a parameter "
                "or set the OPENAI_API_KEY environment variable."
            )
        
        # Configure a session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
    
    def validate_json_file(self, file_path: str) -> Tuple[bool, List[str]]:
        """
        Validate the JSON file before upload.
        
        Returns a tuple: (is_valid, list_of_errors)
        """
        errors = []
        
        # Check if file exists
        if not os.path.exists(file_path):
            errors.append(f"File not found: {file_path}")
            return False, errors
        
        # Check file size
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > MAX_UPLOAD_SIZE_MB:
            errors.append(
                f"File size ({file_size_mb:.2f} MB) exceeds OpenAI's limit "
                f"of {MAX_UPLOAD_SIZE_MB} MB for GPT knowledge upload."
            )
        
        try:
            # Attempt to parse the JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if it's an array
            if not isinstance(data, list):
                errors.append("Root JSON structure must be an array.")
                return False, errors
            
            # Check for metadata object
            if not data or data[0].get("type") != "metadata":
                errors.append("First object in array must be a metadata object with type='metadata'.")
            
            # Check document objects
            document_ids = set()
            for i, item in enumerate(data[1:], start=1):
                # Check document type
                if item.get("type") != "document":
                    errors.append(f"Item at index {i} is not a valid document object (missing or incorrect 'type').")
                
                # Check required fields
                for field in ["id", "content"]:
                    if not item.get(field):
                        errors.append(f"Document at index {i} is missing required field: {field}")
                
                # Check for duplicate IDs
                if "id" in item:
                    if item["id"] in document_ids:
                        errors.append(f"Duplicate document ID found: {item['id']}")
                    document_ids.add(item["id"])
                
                # Check content quality
                if "content" in item and not item["content"].strip():
                    errors.append(f"Document at index {i} has empty content.")
                
                # Check metadata structure consistency
                if i > 1 and "metadata" in item and "metadata" in data[1]:
                    if set(item["metadata"].keys()) != set(data[1]["metadata"].keys()):
                        errors.append(f"Document at index {i} has inconsistent metadata structure.")
        
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {str(e)}")
            return False, errors
        
        return len(errors) == 0, errors
    
    def upload_to_gpt(self, file_path: str, gpt_id: Optional[str] = None) -> Dict:
        """
        Upload the JSON file to GPT knowledge.
        
        Args:
            file_path: Path to the JSON file
            gpt_id: Optional ID of the GPT to upload to
        
        Returns:
            Response data from the API
        """
        # Validate the file before upload
        is_valid, errors = self.validate_json_file(file_path)
        if not is_valid:
            error_msg = "\n".join([f"- {error}" for error in errors])
            raise ValueError(f"JSON validation failed:\n{error_msg}")
        
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Prepare the upload endpoint
        upload_endpoint = f"{API_BASE}/gpts/{gpt_id}/knowledge" if gpt_id else f"{API_BASE}/gpts/knowledge"
        
        # Upload the file
        try:
            response = self.session.post(
                upload_endpoint,
                json={"content": file_content, "file_name": os.path.basename(file_path)},
                timeout=TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        
        except requests.RequestException as e:
            if hasattr(e, 'response') and e.response:
                error_detail = e.response.json().get('error', {}).get('message', str(e))
                raise RuntimeError(f"API error: {error_detail}")
            else:
                raise RuntimeError(f"Request failed: {str(e)}")
    
    def upload_with_progress(self, file_path: str, gpt_id: Optional[str] = None) -> Dict:
        """Upload with progress reporting."""
        print(f"Validating file: {file_path}")
        is_valid, errors = self.validate_json_file(file_path)
        
        if not is_valid:
            print("Validation failed with the following errors:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        
        print("Validation successful! File is ready for upload.")
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        print(f"File size: {file_size_mb:.2f} MB")
        
        print("\nUploading to GPT knowledge...")
        start_time = time.time()
        
        try:
            result = self.upload_to_gpt(file_path, gpt_id)
            elapsed_time = time.time() - start_time
            
            print(f"Upload successful! Completed in {elapsed_time:.2f} seconds.")
            print(f"Upload ID: {result.get('id', 'N/A')}")
            print(f"Status: {result.get('status', 'N/A')}")
            
            return result
        
        except Exception as e:
            print(f"Upload failed: {str(e)}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Upload JSON data to GPT knowledge")
    parser.add_argument(
        "--file",
        default="lite_llm/jfk_files_gpt.json",
        help="Path to the consolidated JSON file to upload"
    )
    parser.add_argument(
        "--gpt-id",
        help="ID of the GPT to upload to (if updating an existing GPT)"
    )
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (defaults to OPENAI_API_KEY environment variable)"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate the file without uploading"
    )
    
    args = parser.parse_args()
    
    try:
        uploader = GPTUploader(api_key=args.api_key)
        
        if args.validate_only:
            print(f"Validating file: {args.file}")
            is_valid, errors = uploader.validate_json_file(args.file)
            
            if is_valid:
                print("Validation successful! File is ready for upload.")
                file_size_mb = os.path.getsize(args.file) / (1024 * 1024)
                print(f"File size: {file_size_mb:.2f} MB")
            else:
                print("Validation failed with the following errors:")
                for error in errors:
                    print(f"  - {error}")
                return 1
        else:
            uploader.upload_with_progress(args.file, args.gpt_id)
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
