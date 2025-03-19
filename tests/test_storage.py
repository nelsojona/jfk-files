#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the storage module.

This script tests the functionality of the storage structure implementation.
"""

import sys
import os
import logging
import json
from pathlib import Path
import shutil

# Add parent directory to python path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_storage")

try:
    # Import storage module
    from src.utils.storage import StorageManager, store_document, get_document_path, migrate_existing_files
    
    def setup_test_environment():
        """Create test files and directories."""
        # Create test files directory
        test_dir = Path("test_files")
        if test_dir.exists():
            shutil.rmtree(test_dir)
        
        test_dir.mkdir()
        
        # Create test PDF file
        pdf_path = test_dir / "test-doc-123.pdf"
        with open(pdf_path, 'w') as f:
            f.write("This is a test PDF file content")
        
        # Create test Markdown file
        md_path = test_dir / "test-doc-123.md"
        with open(md_path, 'w') as f:
            f.write("# Test Document\n\n## Page 1\n\nThis is a test markdown file.")
        
        # Create test JSON file
        json_path = test_dir / "test-doc-123.json"
        with open(json_path, 'w') as f:
            json.dump({"document_id": "test-doc-123", "content": "Test content"}, f)
        
        return test_dir, pdf_path, md_path, json_path
    
    def test_storage_initialization():
        """Test storage manager initialization."""
        logger.info("Testing storage manager initialization...")
        
        # Create storage manager with test directory
        storage = StorageManager(base_dir="test_storage")
        
        # Check if directories were created
        assert os.path.exists("test_storage/pdfs")
        assert os.path.exists("test_storage/markdown")
        assert os.path.exists("test_storage/json")
        assert os.path.exists("test_storage/metadata")
        assert os.path.exists("test_storage/.checkpoints")
        
        logger.info("Storage initialization test PASSED")
        return storage
    
    def test_file_storage(storage, pdf_path, md_path, json_path):
        """Test storing files in the storage structure."""
        logger.info("Testing file storage...")
        
        doc_id = "test-doc-123"
        
        # Store test files
        pdf_stored = storage.store_file(pdf_path, doc_id, "pdf")
        md_stored = storage.store_file(md_path, doc_id, "markdown")
        json_stored = storage.store_file(json_path, doc_id, "json")
        
        # Check if files were stored
        assert os.path.exists(pdf_stored)
        assert os.path.exists(md_stored)
        assert os.path.exists(json_stored)
        
        # Check if metadata was created
        assert doc_id in storage._metadata_index
        assert "pdf" in storage._metadata_index[doc_id]
        assert "markdown" in storage._metadata_index[doc_id]
        assert "json" in storage._metadata_index[doc_id]
        
        logger.info("File storage test PASSED")
        return pdf_stored, md_stored, json_stored
    
    def test_file_retrieval(storage, doc_id="test-doc-123"):
        """Test retrieving files from the storage structure."""
        logger.info("Testing file retrieval...")
        
        # Get file paths
        pdf_path = storage.get_file_path(doc_id, "pdf")
        md_path = storage.get_file_path(doc_id, "markdown")
        json_path = storage.get_file_path(doc_id, "json")
        
        # Check if paths are valid
        assert pdf_path and os.path.exists(pdf_path)
        assert md_path and os.path.exists(md_path)
        assert json_path and os.path.exists(json_path)
        
        # Test convenience function
        all_paths = get_document_path(doc_id)
        assert all_paths["pdf"] == pdf_path
        assert all_paths["markdown"] == md_path
        assert all_paths["json"] == json_path
        
        logger.info("File retrieval test PASSED")
    
    def test_processing_status(storage, doc_id="test-doc-123"):
        """Test checking processing status."""
        logger.info("Testing processing status check...")
        
        # Check status of complete document
        status = storage.check_processing_status(doc_id)
        assert status == "complete"
        
        # Check status of non-existent document
        status = storage.check_processing_status("nonexistent-doc")
        assert status == "not_found"
        
        # Create partial document
        partial_id = "partial-doc"
        with open("test_files/partial.pdf", "w") as f:
            f.write("Partial PDF content")
        
        storage.store_file("test_files/partial.pdf", partial_id, "pdf")
        
        # Check status of partial document
        status = storage.check_processing_status(partial_id)
        assert status == "partial"
        
        logger.info("Processing status test PASSED")
    
    def test_statistics(storage):
        """Test statistics generation."""
        logger.info("Testing statistics generation...")
        
        stats = storage.get_statistics()
        
        # Check statistics
        assert stats["total_documents"] > 0
        assert stats["complete_documents"] > 0
        assert stats["partial_documents"] > 0
        assert stats["total_size"]["pdf"] > 0
        
        logger.info(f"Statistics: {stats}")
        logger.info("Statistics test PASSED")
    
    def test_cleanup(storage, doc_id="partial-doc"):
        """Test cleanup functionality."""
        logger.info("Testing cleanup...")
        
        # Clean up partial document
        storage.cleanup(doc_id)
        
        # Check if document was removed
        status = storage.check_processing_status(doc_id)
        assert status == "not_found"
        
        # Clean up temporary files
        storage.cleanup()
        
        logger.info("Cleanup test PASSED")
    
    def run_all_tests():
        """Run all storage tests."""
        logger.info("Starting storage module tests")
        
        # Setup test environment
        test_dir, pdf_path, md_path, json_path = setup_test_environment()
        
        try:
            # Run tests
            storage = test_storage_initialization()
            test_file_storage(storage, pdf_path, md_path, json_path)
            test_file_retrieval(storage)
            test_processing_status(storage)
            test_statistics(storage)
            test_cleanup(storage)
            
            logger.info("All storage tests PASSED")
        finally:
            # Clean up test directories
            if os.path.exists("test_storage"):
                shutil.rmtree("test_storage")
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
    
    if __name__ == "__main__":
        run_all_tests()

except ImportError as e:
    logger.error(f"Error importing storage module: {e}")
    logger.error("Make sure the 'src/utils/storage.py' file exists")
except Exception as e:
    logger.error(f"Error during test: {e}")
    import traceback
    traceback.print_exc()
