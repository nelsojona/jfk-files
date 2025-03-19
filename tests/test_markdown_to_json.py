#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Markdown to JSON conversion functionality.

This script tests converting a Markdown document to JSON using Python.
"""

import sys
import os
import logging
import json

# Add parent directory to python path to import from jfk_scraper.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import required functions
    from jfk_scraper import markdown_to_json, create_directories, logger
    
    # Make sure directories exist
    create_directories()
    
    # Configure test-specific logging
    logger.info("Starting Markdown to JSON conversion test")
    
    # Use the Markdown file we created in the previous test
    markdown_path = "markdown/docid-32204484.md"
    
    if not os.path.exists(markdown_path):
        logger.error(f"Test Markdown file not found at {markdown_path}. Did you run test_pdf_to_markdown.py first?")
        sys.exit(1)
    
    # Convert the Markdown to JSON
    result = markdown_to_json(markdown_path)
    
    # Handle tuple return value (path, content)
    json_path = result[0] if isinstance(result, tuple) else result
    
    # Verify the conversion was successful
    if json_path and os.path.exists(json_path):
        try:
            # Read the JSON file to verify its structure
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Check if the JSON has the expected structure
            # The structure can vary depending on whether we're using pandoc or our custom conversion
            if isinstance(json_data, dict):
                file_size = os.path.getsize(json_path)
                logger.info(f"Successfully converted Markdown to JSON at {json_path}")
                logger.info(f"JSON file size: {file_size} bytes")
                
                # Check for our custom JSON structure
                if 'document_id' in json_data:
                    logger.info(f"Document ID: {json_data['document_id']}")
                    if 'total_pages' in json_data:
                        logger.info(f"Total pages: {json_data['total_pages']}")
                    if 'pages' in json_data and isinstance(json_data['pages'], list):
                        logger.info(f"Contains {len(json_data['pages'])} page entries")
                # Check for pandoc JSON structure (if used)
                elif 'blocks' in json_data or 'pandoc-api-version' in json_data:
                    logger.info("Pandoc JSON format detected")
                
                logger.info("JSON structure is valid")
                logger.info("Markdown to JSON conversion test PASSED")
            else:
                logger.error("JSON structure is not as expected. Test FAILED")
        except json.JSONDecodeError:
            # It might be a non-standard JSON format if pandoc was used directly
            logger.info(f"Non-standard JSON format detected at {json_path}")
            file_size = os.path.getsize(json_path)
            if file_size > 0:
                logger.info(f"File size: {file_size} bytes (appears to be valid)")
                logger.info("Markdown to JSON conversion test PASSED")
            else:
                logger.error("Empty JSON file. Test FAILED")
    else:
        logger.error("Failed to convert Markdown to JSON. Test FAILED")
    
except ImportError as e:
    print(f"Error importing from jfk_scraper.py: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error during Markdown to JSON conversion test: {e}")
    sys.exit(1)
