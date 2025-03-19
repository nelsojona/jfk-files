#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Storage structure module for JFK Files Scraper.

This module provides functionality for managing the storage structure
for processed files, including organization, metadata management, and
file operations.
"""

import os
import json
import shutil
import logging
import hashlib
import time
from datetime import datetime
from pathlib import Path
import threading

# Initialize logger
logger = logging.getLogger("jfk_scraper.storage")

# Thread lock for file operations
file_lock = threading.Lock()

class StorageManager:
    """
    Manages the storage structure for processed JFK files.
    
    The storage structure organizes files in hierarchical directories
    based on configurable parameters like document ID, date, or batches.
    """
    
    def __init__(self, base_dir=None, structure_type="hierarchical", batch_size=100):
        """
        Initialize the storage manager with the specified parameters.
        
        Args:
            base_dir (str): Base directory for storage. If None, uses default directory structure
            structure_type (str): Type of storage structure ('hierarchical', 'flat', or 'batched')
            batch_size (int): Number of files per batch for 'batched' structure type
        """
        # Set base directory
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path.cwd()
        
        # Set structure type
        self.structure_type = structure_type
        self.batch_size = batch_size
        
        # Create structure for different file types
        self.pdf_dir = self.base_dir / "pdfs"
        self.markdown_dir = self.base_dir / "markdown"
        self.json_dir = self.base_dir / "json"
        self.lite_llm_dir = self.base_dir / "lite_llm"
        self.metadata_dir = self.base_dir / "metadata"
        self.checkpoint_dir = self.base_dir / ".checkpoints"
        
        # Initialize directories
        self.create_directories()
        
        # Initialize metadata index
        self._metadata_index = {}
        self._load_metadata_index()
    
    def create_directories(self):
        """Create all necessary directories for the storage structure."""
        os.makedirs(self.pdf_dir, exist_ok=True)
        os.makedirs(self.markdown_dir, exist_ok=True)
        os.makedirs(self.json_dir, exist_ok=True)
        os.makedirs(self.lite_llm_dir, exist_ok=True)
        os.makedirs(self.metadata_dir, exist_ok=True)
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        logger.info("Created storage directory structure")
    
    def _get_storage_path(self, doc_id, file_type, create=True):
        """
        Get the appropriate storage path for a document based on its ID and file type.
        
        Args:
            doc_id (str): Document ID
            file_type (str): File type ('pdf', 'markdown', 'json', 'metadata')
            create (bool): Whether to create the directory if it doesn't exist
            
        Returns:
            Path: Path object for the storage location
        """
        # Select the base directory based on file type
        if file_type == 'pdf':
            base = self.pdf_dir
        elif file_type == 'markdown':
            base = self.markdown_dir
        elif file_type == 'json':
            base = self.json_dir
        elif file_type == 'metadata':
            base = self.metadata_dir
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        # Determine path based on structure type
        if self.structure_type == 'flat':
            path = base
        elif self.structure_type == 'hierarchical':
            # Create a hierarchical path based on the document ID
            # Use first 2 characters for first level, next 2 for second level
            if len(doc_id) >= 4:
                path = base / doc_id[:2] / doc_id[2:4]
            else:
                path = base / "other"
        elif self.structure_type == 'batched':
            # Compute batch number based on a hash of the doc_id
            doc_hash = int(hashlib.md5(doc_id.encode()).hexdigest(), 16)
            batch_num = (doc_hash % 1000) // self.batch_size
            path = base / f"batch_{batch_num:03d}"
        else:
            raise ValueError(f"Unsupported structure type: {self.structure_type}")
        
        # Create directory if it doesn't exist and create flag is True
        if create and not path.exists():
            os.makedirs(path, exist_ok=True)
        
        return path
    
    def store_file(self, source_path, doc_id, file_type, move=False):
        """
        Store a file in the appropriate location based on the document ID and file type.
        
        Args:
            source_path (str): Path to the source file
            doc_id (str): Document ID
            file_type (str): File type ('pdf', 'markdown', 'json')
            move (bool): Whether to move the file instead of copying it
            
        Returns:
            str: Path to the stored file
        """
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # Get target directory
        target_dir = self._get_storage_path(doc_id, file_type)
        
        # Determine filename extension
        if file_type == 'pdf':
            ext = '.pdf'
        elif file_type == 'markdown':
            ext = '.md'
        elif file_type == 'json':
            ext = '.json'
        else:
            ext = source_path.suffix
        
        # Build target path
        target_path = target_dir / f"{doc_id}{ext}"
        
        # Use file lock to ensure thread safety
        with file_lock:
            # Copy or move the file
            if move:
                logger.info(f"Moving {source_path} to {target_path}")
                shutil.move(source_path, target_path)
            else:
                logger.info(f"Copying {source_path} to {target_path}")
                shutil.copy2(source_path, target_path)
            
            # Update metadata
            self._update_metadata(doc_id, file_type, target_path)
        
        return str(target_path)
    
    def get_file_path(self, doc_id, file_type):
        """
        Get the path to a file based on the document ID and file type.
        
        Args:
            doc_id (str): Document ID
            file_type (str): File type ('pdf', 'markdown', 'json')
            
        Returns:
            str: Path to the file or None if not found
        """
        # Get the directory where the file should be stored
        target_dir = self._get_storage_path(doc_id, file_type, create=False)
        
        # Determine filename extension
        if file_type == 'pdf':
            ext = '.pdf'
        elif file_type == 'markdown':
            ext = '.md'
        elif file_type == 'json':
            ext = '.json'
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        # Build expected path
        file_path = target_dir / f"{doc_id}{ext}"
        
        # Check if file exists
        if file_path.exists():
            return str(file_path)
        
        # If not found in expected location, try to find in metadata
        if doc_id in self._metadata_index and file_type in self._metadata_index[doc_id]:
            return self._metadata_index[doc_id][file_type].get('path')
        
        return None
    
    def _update_metadata(self, doc_id, file_type, file_path):
        """
        Update metadata for a document.
        
        Args:
            doc_id (str): Document ID
            file_type (str): File type ('pdf', 'markdown', 'json')
            file_path (Path): Path to the file
        """
        now = datetime.now().isoformat()
        file_path = Path(file_path)
        
        # Initialize metadata entry if it doesn't exist
        if doc_id not in self._metadata_index:
            self._metadata_index[doc_id] = {}
        
        # Update file type metadata
        self._metadata_index[doc_id][file_type] = {
            'path': str(file_path),
            'size': file_path.stat().st_size,
            'last_modified': now,
            'file_type': file_type
        }
        
        # Save metadata file
        metadata_path = self._get_storage_path(doc_id, 'metadata') / f"{doc_id}.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self._metadata_index[doc_id], f, indent=2)
        
        # Update global metadata index
        self._save_metadata_index()
    
    def _load_metadata_index(self):
        """Load the metadata index from disk."""
        index_path = self.metadata_dir / "index.json"
        if index_path.exists():
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    self._metadata_index = json.load(f)
                logger.info(f"Loaded metadata index with {len(self._metadata_index)} documents")
            except Exception as e:
                logger.error(f"Error loading metadata index: {e}")
                self._metadata_index = {}
    
    def _save_metadata_index(self):
        """Save the metadata index to disk."""
        index_path = self.metadata_dir / "index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(self._metadata_index, f, indent=2)
    
    def list_documents(self, status=None):
        """
        List all documents in the storage.
        
        Args:
            status (str, optional): Filter by processing status
            
        Returns:
            list: List of document IDs
        """
        return list(self._metadata_index.keys())
    
    def get_document_metadata(self, doc_id):
        """
        Get metadata for a document.
        
        Args:
            doc_id (str): Document ID
            
        Returns:
            dict: Document metadata or None if not found
        """
        return self._metadata_index.get(doc_id)
    
    def check_processing_status(self, doc_id):
        """
        Check the processing status of a document.
        
        Args:
            doc_id (str): Document ID
            
        Returns:
            str: Processing status ('complete', 'partial', 'not_found')
        """
        if doc_id not in self._metadata_index:
            return 'not_found'
        
        # Check if all file types are present
        metadata = self._metadata_index[doc_id]
        if all(ft in metadata for ft in ['pdf', 'markdown', 'json']):
            return 'complete'
        else:
            return 'partial'
    
    def get_statistics(self):
        """
        Get statistics about the stored data.
        
        Returns:
            dict: Statistics
        """
        stats = {
            'total_documents': len(self._metadata_index),
            'complete_documents': 0,
            'partial_documents': 0,
            'total_size': {
                'pdf': 0,
                'markdown': 0,
                'json': 0
            }
        }
        
        # Compute statistics
        for doc_id, metadata in self._metadata_index.items():
            status = self.check_processing_status(doc_id)
            if status == 'complete':
                stats['complete_documents'] += 1
            elif status == 'partial':
                stats['partial_documents'] += 1
            
            # Calculate total size by file type
            for file_type in ['pdf', 'markdown', 'json']:
                if file_type in metadata:
                    stats['total_size'][file_type] += metadata[file_type].get('size', 0)
        
        return stats
    
    def cleanup(self, doc_id=None):
        """
        Remove files for a document or clean up temporary files.
        
        Args:
            doc_id (str, optional): Document ID to clean up, or None to clean up all temp files
            
        Returns:
            bool: True if successful
        """
        if doc_id:
            # Remove specific document
            with file_lock:
                for file_type in ['pdf', 'markdown', 'json', 'metadata']:
                    path = self.get_file_path(doc_id, file_type)
                    if path and os.path.exists(path):
                        os.remove(path)
                        logger.info(f"Removed {file_type} file for document {doc_id}")
                
                # Remove from metadata index
                if doc_id in self._metadata_index:
                    del self._metadata_index[doc_id]
                    self._save_metadata_index()
        else:
            # Clean up temporary files
            for directory in [self.pdf_dir, self.markdown_dir, self.json_dir]:
                for root, _, files in os.walk(directory):
                    for file in files:
                        if file.endswith('.temp'):
                            os.remove(os.path.join(root, file))
                            logger.info(f"Removed temporary file: {file}")
        
        return True


# Helper functions

def migrate_existing_files(storage_manager):
    """
    Migrate existing files from the old flat structure to the new structure.
    
    Args:
        storage_manager (StorageManager): Storage manager instance
        
    Returns:
        tuple: (migrated_count, failed_count)
    """
    logger.info("Starting migration of existing files")
    migrated = 0
    failed = 0
    
    # Paths to check
    paths = {
        'pdf': Path('pdfs'),
        'markdown': Path('markdown'),
        'json': Path('json')
    }
    
    for file_type, directory in paths.items():
        if not directory.exists():
            continue
        
        logger.info(f"Checking {directory} for {file_type} files")
        for file_path in directory.glob(f"*.{file_type}" if file_type != 'markdown' else "*.md"):
            try:
                # Extract document ID from filename
                doc_id = file_path.stem
                
                # Store in new structure
                storage_manager.store_file(file_path, doc_id, file_type, move=True)
                migrated += 1
                
                logger.info(f"Migrated {file_type} file: {file_path.name}")
            except Exception as e:
                logger.error(f"Failed to migrate {file_path}: {e}")
                failed += 1
    
    logger.info(f"Migration complete. Migrated {migrated} files, failed {failed} files")
    return migrated, failed


def get_document_path(doc_id, file_type='all'):
    """
    Convenience function to get path for a document.
    
    Args:
        doc_id (str): Document ID
        file_type (str): File type ('pdf', 'markdown', 'json', or 'all')
        
    Returns:
        str or dict: Path to the file or dict of paths if file_type is 'all'
    """
    storage = StorageManager()
    
    if file_type == 'all':
        return {
            'pdf': storage.get_file_path(doc_id, 'pdf'),
            'markdown': storage.get_file_path(doc_id, 'markdown'),
            'json': storage.get_file_path(doc_id, 'json')
        }
    else:
        return storage.get_file_path(doc_id, file_type)


def store_document(doc_id, pdf_path=None, markdown_path=None, json_path=None):
    """
    Store document files in the appropriate locations.
    
    Args:
        doc_id (str): Document ID
        pdf_path (str, optional): Path to PDF file
        markdown_path (str, optional): Path to Markdown file
        json_path (str, optional): Path to JSON file
        
    Returns:
        dict: Paths to stored files
    """
    storage = StorageManager()
    result = {}
    
    if pdf_path:
        result['pdf'] = storage.store_file(pdf_path, doc_id, 'pdf')
    
    if markdown_path:
        result['markdown'] = storage.store_file(markdown_path, doc_id, 'markdown')
    
    if json_path:
        result['json'] = storage.store_file(json_path, doc_id, 'json')
    
    return result


def store_json_data(source_json_path, output_path):
    """
    Store JSON data in the LiteLLM compatible format for API integration.
    
    Args:
        source_json_path (str): Path to the source JSON file
        output_path (str): Path to save the Lite LLM format JSON
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Read the source JSON file
        with open(source_json_path, 'r', encoding='utf-8') as f:
            source_data = json.load(f)
        
        # Create the Lite LLM entry
        lite_llm_entry = {
            "source": f"JFK Files - {os.path.basename(source_json_path)}",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "content": source_data
        }
        
        # Check if output file exists and has content
        if os.path.exists(output_path) and os.path.getsize(output_path) > 10:
            try:
                # Read existing data
                with open(output_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                
                # Append or update entry
                if isinstance(existing_data, list):
                    # Find and replace if this doc_id already exists
                    doc_id = source_data.get("document_id", "")
                    updated = False
                    
                    for i, entry in enumerate(existing_data):
                        if "content" in entry and "document_id" in entry["content"]:
                            if entry["content"]["document_id"] == doc_id:
                                existing_data[i] = lite_llm_entry
                                updated = True
                                break
                    
                    if not updated:
                        existing_data.append(lite_llm_entry)
                else:
                    # Convert to list format
                    existing_data = [existing_data, lite_llm_entry]
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Error reading existing Lite LLM file, creating new: {e}")
                existing_data = [lite_llm_entry]
        else:
            # Create new data structure
            existing_data = [lite_llm_entry]
        
        # Write data back to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Successfully stored JSON data in Lite LLM format at {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing JSON data in Lite LLM format: {e}")
        return False
