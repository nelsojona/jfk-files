#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-end test for the JFK Files scraper.

This script tests the entire pipeline from downloading a PDF to storing it in Lite LLM format.
"""

import sys
import os
import logging
import json

# Add parent directory to python path to import from jfk_scraper.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import required functions
    from jfk_scraper import process_file, create_directories, logger
    
    # Make sure directories exist
    create_directories()
    
    # Configure test-specific logging
    logger.info("Starting end-to-end test with sample data")
    
    # Sample PDF URL from the National Archives
    test_url = "https://www.archives.gov/files/research/jfk/releases/docid-32204484.pdf"
    
    # Run the entire pipeline
    success = process_file(test_url)
    
    # Verify the results
    if success:
        # Verify PDF was downloaded
        pdf_path = os.path.join("pdfs", "docid-32204484.pdf")
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found at {pdf_path}")
            sys.exit(1)
        
        # Verify Markdown was created
        md_path = os.path.join("markdown", "docid-32204484.md")
        if not os.path.exists(md_path):
            logger.error(f"Markdown file not found at {md_path}")
            sys.exit(1)
        
        # Verify JSON was created
        json_path = os.path.join("json", "docid-32204484.json")
        if not os.path.exists(json_path):
            logger.error(f"JSON file not found at {json_path}")
            sys.exit(1)
        
        # Verify Lite LLM data was stored
        lite_llm_path = os.path.join("lite_llm", "jfk_files.json")
        if not os.path.exists(lite_llm_path):
            logger.error(f"Lite LLM data file not found at {lite_llm_path}")
            sys.exit(1)
        
        # Load and verify Lite LLM data
        with open(lite_llm_path, 'r', encoding='utf-8') as f:
            lite_llm_data = json.load(f)
        
        if isinstance(lite_llm_data, list) and len(lite_llm_data) > 0:
            sample_item = lite_llm_data[0]
            logger.info(f"Lite LLM data contains {len(lite_llm_data)} item(s)")
            logger.info(f"Sample source: {sample_item.get('source', 'unknown')}")
            logger.info(f"Sample timestamp: {sample_item.get('timestamp', 'unknown')}")
            
            # Check if the content has the expected structure
            content = sample_item.get('content', {})
            if isinstance(content, dict) and 'document_id' in content:
                logger.info(f"Content document_id: {content['document_id']}")
                logger.info("All files created and data has valid structure")
                logger.info("End-to-end test PASSED")
            else:
                logger.error("Lite LLM content does not have the expected structure")
                sys.exit(1)
        else:
            logger.error("Lite LLM data does not have the expected structure")
            sys.exit(1)
    else:
        logger.error("Process file returned False. End-to-end test FAILED")
        sys.exit(1)
    
except ImportError as e:
    print(f"Error importing from jfk_scraper.py: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error during end-to-end test: {e}")
    sys.exit(1)
