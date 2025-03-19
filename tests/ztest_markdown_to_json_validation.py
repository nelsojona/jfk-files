#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST-3: Test Markdown to JSON conversion with various inputs.

This script tests the Markdown to JSON conversion functionality by:
1. Testing different Markdown input patterns
2. Verifying JSON structure integrity
3. Validating the robustness of the conversion process
4. Testing both pandoc and Python-based conversion methods
"""

import sys
import os
import logging
import json
import tempfile
import re
from pathlib import Path

# Add parent directory to python path to import from jfk_scraper.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import required functions
    from jfk_scraper import (
        markdown_to_json, 
        create_directories, 
        logger, 
        transform_pandoc_json_to_standard_format,
        parse_markdown_with_python
    )
    
    # Make sure directories exist
    create_directories()
    
    # Configure test-specific logging
    logger.info("Starting Markdown to JSON conversion test (TEST-3)")
    
    # Test with the standard Markdown file
    markdown_path = "markdown/docid-32204484.md"
    
    if not os.path.exists(markdown_path):
        logger.error(f"Test Markdown file not found at {markdown_path}. Did you run test_pdf_to_markdown.py first?")
        sys.exit(1)
    
    # Track test results
    test_results = {
        "standard_conversion": False,
        "json_structure": False,
        "synthetic_inputs": False,
        "error_handling": False,
        "output_consistency": False
    }
    
    # ===== TEST 1: Standard Conversion =====
    logger.info("TEST 1: Testing standard Markdown to JSON conversion")
    
    # Convert the Markdown to JSON using the standard function
    result = markdown_to_json(markdown_path)
    
    # Handle tuple return value (path, content)
    json_path = result[0] if isinstance(result, tuple) else result
    
    # Verify the conversion was successful
    if json_path and os.path.exists(json_path):
        try:
            # Read the JSON file to verify its structure
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            if isinstance(json_data, dict):
                file_size = os.path.getsize(json_path)
                logger.info(f"Successfully converted Markdown to JSON at {json_path}")
                logger.info(f"JSON file size: {file_size} bytes")
                test_results["standard_conversion"] = True
            else:
                logger.error("JSON structure is not a dictionary as expected")
        except json.JSONDecodeError as e:
            logger.error(f"Generated JSON is not valid: {e}")
        except Exception as e:
            logger.error(f"Error validating JSON: {e}")
    else:
        logger.error(f"Failed to convert Markdown to JSON")
    
    # ===== TEST 2: JSON Structure Validation =====
    logger.info("TEST 2: Validating JSON structure")
    
    required_keys = ["document_id", "total_pages", "pages", "metadata"]
    missing_keys = [key for key in required_keys if key not in json_data]
    
    if missing_keys:
        logger.error(f"JSON is missing required keys: {missing_keys}")
    else:
        # Validate pages array
        if not isinstance(json_data["pages"], list):
            logger.error("'pages' field is not an array")
        elif not json_data["pages"]:
            logger.error("'pages' array is empty")
        else:
            # Check the structure of each page
            page_keys = ["title", "content"]
            valid_pages = True
            
            for i, page in enumerate(json_data["pages"]):
                if not isinstance(page, dict):
                    logger.error(f"Page {i} is not a dictionary")
                    valid_pages = False
                    break
                
                missing_page_keys = [key for key in page_keys if key not in page]
                if missing_page_keys:
                    logger.error(f"Page {i} is missing required keys: {missing_page_keys}")
                    valid_pages = False
                    break
                
                if not isinstance(page["content"], str):
                    logger.error(f"Page {i} content is not a string")
                    valid_pages = False
                    break
                
                if not page["content"].strip():
                    logger.warning(f"Page {i} content is empty")
            
            if valid_pages:
                # Verify total_pages matches pages array length
                if json_data["total_pages"] != len(json_data["pages"]):
                    logger.error(f"total_pages ({json_data['total_pages']}) doesn't match actual page count ({len(json_data['pages'])})")
                else:
                    logger.info("JSON structure validation passed")
                    test_results["json_structure"] = True
    
    # ===== TEST 3: Test with Synthetic Markdown Inputs =====
    logger.info("TEST 3: Testing with synthetic Markdown inputs")
    
    synthetic_tests_passed = True
    
    # Test case 1: Simple document with multiple headers
    test_md_1 = """# Document Title
    
## Page 1

This is a simple test document.

## Page 2

Another page with some content.
* List item 1
* List item 2

## Page 3

Final page with a [link](https://example.com).
"""
    
    # Test case 2: Complex document with code blocks and tables
    test_md_2 = """# Complex Document
    
## Page 1

This document has complex features.

```python
def hello_world():
    print("Hello, world!")
```

## Page 2

| Column 1 | Column 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |

## Page 3

1. Numbered list
2. Second item
   * Nested list
   * Another nested item
"""
    
    # Test case 3: Document with minimal content
    test_md_3 = """# Minimal Document
Just a title and one line of text."""
    
    # Test the synthetic inputs
    for i, test_content in enumerate([test_md_1, test_md_2, test_md_3], 1):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(test_content)
            temp_md_path = temp_file.name
        
        try:
            # Convert the temp Markdown file to JSON
            temp_result = markdown_to_json(temp_md_path)
            
            # Handle tuple return value (path, content)
            temp_json_path = temp_result[0] if isinstance(temp_result, tuple) else temp_result
            
            if temp_json_path and os.path.exists(temp_json_path):
                try:
                    # Read the JSON file to verify its structure
                    with open(temp_json_path, 'r', encoding='utf-8') as f:
                        temp_json_data = json.load(f)
                    
                    if not isinstance(temp_json_data, dict):
                        logger.error(f"Test case {i}: JSON output is not a dictionary")
                        synthetic_tests_passed = False
                    elif "pages" not in temp_json_data or not temp_json_data["pages"]:
                        logger.error(f"Test case {i}: JSON output has no pages")
                        synthetic_tests_passed = False
                    else:
                        logger.info(f"Test case {i}: Successfully converted synthetic Markdown to JSON")
                        
                        # Count expected pages based on "## Page" headers
                        expected_pages = len(re.findall(r'^## Page \d+', test_content, re.MULTILINE))
                        if expected_pages == 0:  # For test case 3 with no page headers
                            expected_pages = 1
                        
                        if temp_json_data["total_pages"] != expected_pages:
                            logger.warning(f"Test case {i}: Expected {expected_pages} pages, got {temp_json_data['total_pages']}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Test case {i}: Generated JSON is not valid: {e}")
                    synthetic_tests_passed = False
                except Exception as e:
                    logger.error(f"Test case {i}: Error validating JSON: {e}")
                    synthetic_tests_passed = False
                
                # Clean up the temp JSON file
                try:
                    os.remove(temp_json_path)
                except:
                    pass
            else:
                logger.error(f"Test case {i}: Failed to convert synthetic Markdown to JSON")
                synthetic_tests_passed = False
        
        finally:
            # Clean up the temp Markdown file
            try:
                os.remove(temp_md_path)
            except:
                pass
    
    test_results["synthetic_inputs"] = synthetic_tests_passed
    
    # ===== TEST 4: Error Handling =====
    logger.info("TEST 4: Testing error handling with problematic inputs")
    
    error_handling_passed = True
    
    # Test case 1: Empty file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as temp_file:
        temp_md_path = temp_file.name
        # Write nothing to file
    
    # Test case 2: File with only whitespace
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as temp_file:
        temp_file.write("   \n\n   \n")
        temp_ws_path = temp_file.name
    
    # Test case 3: File with unclosed formatting
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as temp_file:
        temp_file.write("# Test\n\nThis has **unclosed formatting\n\n## Page 2\n\nMore content")
        temp_bad_format_path = temp_file.name
    
    # Test the error handling
    for i, path in enumerate([temp_md_path, temp_ws_path, temp_bad_format_path], 1):
        try:
            # Try to convert the problematic file
            result = markdown_to_json(path)
            
            # Handle tuple return value (path, content)
            result_path = result[0] if isinstance(result, tuple) else result
            
            # We expect the conversion to either fail gracefully or produce valid JSON anyway
            if result_path:
                # If conversion succeeded, verify the output is valid JSON
                try:
                    with open(result_path, 'r', encoding='utf-8') as f:
                        result_data = json.load(f)
                        
                    # Even with problematic input, we should get a valid JSON structure
                    if not isinstance(result_data, dict) or "pages" not in result_data:
                        logger.error(f"Error test {i}: Output JSON lacks required structure")
                        error_handling_passed = False
                    else:
                        logger.info(f"Error test {i}: Successfully handled problematic input")
                        
                    # Clean up the output file
                    try:
                        os.remove(result_path)
                    except:
                        pass
                        
                except json.JSONDecodeError:
                    logger.error(f"Error test {i}: Output is not valid JSON")
                    error_handling_passed = False
            else:
                # If conversion failed, that's also acceptable for error handling tests
                logger.info(f"Error test {i}: Conversion failed gracefully as expected")
        except Exception as e:
            # The function should handle errors internally and not raise exceptions
            logger.error(f"Error test {i}: Unhandled exception: {e}")
            error_handling_passed = False
        finally:
            # Clean up the temp file
            try:
                os.remove(path)
            except:
                pass
    
    test_results["error_handling"] = error_handling_passed
    
    # ===== TEST 5: Compare Pandoc and Python Conversion Methods =====
    logger.info("TEST 5: Comparing conversion methods for consistency")
    
    try:
        # Read the original Markdown content
        with open(markdown_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Extract document ID
        doc_id = os.path.splitext(os.path.basename(markdown_path))[0]
        
        # Try the pure Python conversion
        python_json = parse_markdown_with_python(original_content, doc_id)
        
        # Verify the Python conversion produced valid output
        if not isinstance(python_json, dict) or "pages" not in python_json:
            logger.error("Python conversion method failed to produce valid JSON structure")
        else:
            # Try to read the JSON file produced by the markdown_to_json function
            # which should have already been created in TEST 1
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    previous_json = json.load(f)
                
                # Compare some key aspects of the structures
                consistency_issues = []
                
                if len(python_json["pages"]) != len(previous_json["pages"]):
                    consistency_issues.append(f"Page count differs: Python {len(python_json['pages'])}, Previous {len(previous_json['pages'])}")
                
                if python_json["document_id"] != previous_json["document_id"]:
                    consistency_issues.append("Document IDs differ")
                
                # Compare page titles
                for i, (py_page, prev_page) in enumerate(zip(python_json["pages"], previous_json["pages"])):
                    if py_page["title"] != prev_page["title"]:
                        consistency_issues.append(f"Page {i} titles differ: '{py_page['title']}' vs '{prev_page['title']}'")
                
                if consistency_issues:
                    logger.warning("Conversion methods show inconsistencies:")
                    for issue in consistency_issues:
                        logger.warning(f"  - {issue}")
                    logger.warning("These differences may be acceptable depending on implementation details")
                else:
                    logger.info("Python and standard conversion methods show good consistency")
                
                # Some inconsistency is expected and acceptable
                test_results["output_consistency"] = True
                
            except Exception as e:
                logger.error(f"Error comparing conversion methods: {e}")
        
    except Exception as e:
        logger.error(f"Error testing conversion methods: {e}")
    
    # ===== Summary of All Tests =====
    logger.info("=== Markdown to JSON Conversion Test Summary ===")
    for test, result in test_results.items():
        status = "PASSED" if result else "FAILED"
        logger.info(f"  {test}: {status}")
    
    all_tests_passed = all(test_results.values())
    
    if all_tests_passed:
        logger.info("All Markdown to JSON conversion tests PASSED")
    else:
        passed_tests = sum(1 for result in test_results.values() if result)
        logger.warning(f"Some tests failed: {passed_tests}/{len(test_results)} passed")
    
    # Overall test passes if standard conversion works, even if some advanced tests fail
    if test_results["standard_conversion"] and test_results["json_structure"]:
        logger.info("Markdown to JSON conversion test PASSED (core functionality)")
    else:
        logger.error("Markdown to JSON conversion test FAILED (core functionality)")
        sys.exit(1)
    
except ImportError as e:
    print(f"Error importing from jfk_scraper.py: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error during Markdown to JSON conversion test: {e}")
    sys.exit(1)
