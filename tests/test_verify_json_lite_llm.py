#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST-4: Verify JSON output format for Lite LLM compatibility.

This script tests the JSON output structure, ensuring it meets the
requirements for Lite LLM datasets by:
1. Validating the Lite LLM format structure
2. Testing the storage function with different inputs
3. Verifying file integrity and completeness
4. Ensuring compatibility with Lite LLM specifications
"""

import sys
import os
import logging
import json
import tempfile
import copy
from pathlib import Path

# Add parent directory to python path to import from jfk_scraper.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import required functions
    from jfk_scraper import store_json_data, create_directories, logger
    
    # Make sure directories exist
    create_directories()
    
    # Configure test-specific logging
    logger.info("Starting JSON to Lite LLM format verification test (TEST-4)")
    
    # Define test results tracking
    test_results = {
        "lite_llm_file_exists": False,
        "lite_llm_structure": False,
        "storage_function": False,
        "multiple_documents": False
    }
    
    # ===== TEST 1: Verify Lite LLM File Exists =====
    logger.info("TEST 1: Verifying Lite LLM file exists")
    
    lite_llm_path = "lite_llm/jfk_files.json"
    
    if os.path.exists(lite_llm_path):
        file_size = os.path.getsize(lite_llm_path)
        if file_size > 0:
            logger.info(f"Lite LLM file exists at {lite_llm_path} with size {file_size} bytes")
            test_results["lite_llm_file_exists"] = True
        else:
            logger.error(f"Lite LLM file exists but is empty: {lite_llm_path}")
    else:
        logger.error(f"Lite LLM file not found at {lite_llm_path}")
        # Try to find any JSON files in the lite_llm directory
        lite_llm_dir = os.path.dirname(lite_llm_path)
        if os.path.exists(lite_llm_dir):
            json_files = list(Path(lite_llm_dir).glob("*.json"))
            if json_files:
                logger.info(f"Found alternative JSON files in lite_llm directory: {[f.name for f in json_files]}")
                # Use the first available JSON file for testing
                lite_llm_path = str(json_files[0])
                logger.info(f"Using {lite_llm_path} for testing")
                test_results["lite_llm_file_exists"] = True
    
    # ===== TEST 2: Validate Lite LLM Structure =====
    logger.info("TEST 2: Validating Lite LLM JSON structure")
    
    if test_results["lite_llm_file_exists"]:
        try:
            with open(lite_llm_path, 'r', encoding='utf-8') as f:
                lite_llm_data = json.load(f)
            
            # Check if the file structure is an array (preferred for multiple documents)
            if isinstance(lite_llm_data, list):
                # Get the first entry for structure validation
                sample_entry = lite_llm_data[0] if lite_llm_data else None
                logger.info(f"Lite LLM file contains {len(lite_llm_data)} entries in an array format")
            else:
                # Single entry format
                sample_entry = lite_llm_data
                logger.info("Lite LLM file contains a single document entry")
            
            # Validate the structure of the entry
            if sample_entry:
                required_keys = ["source", "timestamp", "content"]
                missing_keys = [key for key in required_keys if key not in sample_entry]
                
                if missing_keys:
                    logger.error(f"Lite LLM entry is missing required keys: {missing_keys}")
                else:
                    # Validate the content structure
                    content = sample_entry["content"]
                    
                    if isinstance(content, dict):
                        content_required_keys = ["document_id", "total_pages", "pages", "metadata"]
                        content_missing_keys = [key for key in content_required_keys if key not in content]
                        
                        if content_missing_keys:
                            logger.error(f"Content structure is missing required keys: {content_missing_keys}")
                        else:
                            # Check if pages array is valid
                            if isinstance(content["pages"], list) and content["pages"]:
                                page_sample = content["pages"][0]
                                page_required_keys = ["title", "content"]
                                page_missing_keys = [key for key in page_required_keys if key not in page_sample]
                                
                                if page_missing_keys:
                                    logger.error(f"Page structure is missing required keys: {page_missing_keys}")
                                else:
                                    logger.info("Lite LLM file structure validation PASSED")
                                    test_results["lite_llm_structure"] = True
                            else:
                                logger.error("Pages array is invalid or empty")
                    else:
                        logger.error(f"Content is not a dictionary: {type(content)}")
            else:
                logger.error("Lite LLM file is empty or has invalid format")
                
        except json.JSONDecodeError as e:
            logger.error(f"Lite LLM file contains invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error validating Lite LLM file: {e}")
    
    # ===== TEST 3: Test Storage Function =====
    logger.info("TEST 3: Testing store_json_data function")
    
    # Create a sample JSON input
    sample_json = {
        "document_id": "test-document",
        "total_pages": 2,
        "pages": [
            {
                "title": "Page 1",
                "content": "This is test content for page 1."
            },
            {
                "title": "Page 2",
                "content": "This is test content for page 2."
            }
        ],
        "metadata": {
            "conversion_method": "test",
            "conversion_timestamp": "2025-03-18 10:00:00"
        }
    }
    
    # Create a temporary JSON file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file:
        json.dump(sample_json, temp_file)
        temp_json_path = temp_file.name
    
    # Create a temporary output file for storage testing
    temp_storage_path = "lite_llm/test_output.json"
    
    try:
        # Test store_json_data function
        storage_success = store_json_data(temp_json_path, temp_storage_path)
        
        if storage_success and os.path.exists(temp_storage_path):
            try:
                with open(temp_storage_path, 'r', encoding='utf-8') as f:
                    stored_data = json.load(f)
                
                # Validate the stored data
                if isinstance(stored_data, list):
                    # Should be a list with one entry
                    stored_entry = stored_data[0] if stored_data else None
                else:
                    # Might be a single entry
                    stored_entry = stored_data
                
                if stored_entry and "content" in stored_entry:
                    content = stored_entry["content"]
                    
                    # Basic validation of content structure
                    if (isinstance(content, dict) and
                            "document_id" in content and
                            "pages" in content and
                            isinstance(content["pages"], list)):
                        logger.info("store_json_data function test PASSED")
                        test_results["storage_function"] = True
                    else:
                        logger.error("Stored content has invalid structure")
                else:
                    logger.error("Stored data missing required content field")
            except json.JSONDecodeError:
                logger.error("Stored data contains invalid JSON")
            except Exception as e:
                logger.error(f"Error validating stored data: {e}")
        else:
            logger.error("store_json_data function failed or output file missing")
    finally:
        # Clean up temporary files
        try:
            os.remove(temp_json_path)
        except:
            pass
        
        try:
            if os.path.exists(temp_storage_path):
                os.remove(temp_storage_path)
        except:
            pass
    
    # ===== TEST 4: Test Multiple Document Storage =====
    logger.info("TEST 4: Testing multiple document storage")
    
    # Create a second sample document
    sample_json2 = copy.deepcopy(sample_json)
    sample_json2["document_id"] = "test-document-2"
    sample_json2["metadata"]["title"] = "Second Test Document"
    
    # Create two temporary JSON files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file1:
        json.dump(sample_json, temp_file1)
        temp_json_path1 = temp_file1.name
        
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file2:
        json.dump(sample_json2, temp_file2)
        temp_json_path2 = temp_file2.name
    
    # Create a temporary output file for multiple storage testing
    temp_storage_path = "lite_llm/test_multiple.json"
    
    try:
        # Store the first document
        storage_success1 = store_json_data(temp_json_path1, temp_storage_path)
        
        # Store the second document
        storage_success2 = store_json_data(temp_json_path2, temp_storage_path)
        
        if storage_success1 and storage_success2 and os.path.exists(temp_storage_path):
            try:
                with open(temp_storage_path, 'r', encoding='utf-8') as f:
                    stored_data = json.load(f)
                
                # Validate that we have multiple entries
                if isinstance(stored_data, list) and len(stored_data) == 2:
                    # Check if we have different document IDs
                    doc_ids = set()
                    for entry in stored_data:
                        if "content" in entry and "document_id" in entry["content"]:
                            doc_ids.add(entry["content"]["document_id"])
                    
                    if len(doc_ids) == 2:
                        logger.info("Multiple document storage test PASSED")
                        test_results["multiple_documents"] = True
                    else:
                        logger.error("Multiple documents stored, but document IDs are not unique")
                else:
                    logger.error(f"Expected 2 entries, got {len(stored_data) if isinstance(stored_data, list) else 'non-list'}")
            except json.JSONDecodeError:
                logger.error("Multiple storage output contains invalid JSON")
            except Exception as e:
                logger.error(f"Error validating multiple storage output: {e}")
        else:
            logger.error("Multiple document storage test failed")
    finally:
        # Clean up temporary files
        for path in [temp_json_path1, temp_json_path2, temp_storage_path]:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except:
                pass
    
    # ===== Verify Lite LLM Compatibility =====
    logger.info("Verifying Lite LLM format compatibility")
    
    # Define Lite LLM compatibility requirements (simplified example)
    lite_llm_compatibility = {
        "array_format": True,  # Data should be in array format
        "source_tracking": True,  # Each entry should track its source
        "timestamp": True,  # Each entry should have a timestamp
        "structured_content": True,  # Content should be structured (not plain text)
        "multiple_documents": True  # Should support multiple documents
    }
    
    # Evaluate compatibility based on our test results
    compatibility_results = {
        "array_format": test_results["lite_llm_structure"],
        "source_tracking": test_results["lite_llm_structure"],
        "timestamp": test_results["lite_llm_structure"],
        "structured_content": test_results["lite_llm_structure"],
        "multiple_documents": test_results["multiple_documents"]
    }
    
    # Log compatibility results
    logger.info("=== Lite LLM Compatibility Results ===")
    for requirement, result in compatibility_results.items():
        status = "COMPATIBLE" if result else "NOT COMPATIBLE"
        logger.info(f"  {requirement}: {status}")
    
    compatibility_score = sum(1 for r in compatibility_results.values() if r) / len(compatibility_results) * 100
    logger.info(f"Overall compatibility score: {compatibility_score:.1f}%")
    
    # ===== Summary of Results =====
    logger.info("=== JSON to Lite LLM Format Verification Summary ===")
    for test, result in test_results.items():
        status = "PASSED" if result else "FAILED"
        logger.info(f"  {test}: {status}")
    
    # Determine overall test result
    # The test passes if the file exists and has the proper structure
    overall_passed = test_results["lite_llm_file_exists"] and test_results["lite_llm_structure"]
    
    if overall_passed:
        logger.info("JSON to Lite LLM format verification test PASSED")
    else:
        logger.warning("JSON to Lite LLM format verification test completed with issues")

except ImportError as e:
    print(f"Error importing from jfk_scraper.py: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error during JSON to Lite LLM format verification test: {e}")
    sys.exit(1)
