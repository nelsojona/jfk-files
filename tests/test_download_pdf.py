#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for JFK Files PDF downloading functionality.

This script tests the PDF downloading functionality.
"""

import sys
import os
import logging

# Add parent directory to python path to import from jfk_scraper.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import required functions
    from src.jfk_scraper import download_pdf, create_directories, logger
    
    # Make sure directories exist
    create_directories()
    
    # Configure test-specific logging
    logger.info("Starting PDF download test")
    
    # Test PDF URL - this is a sample PDF from the National Archives website
    # If this specific URL doesn't work in the future, substitute with another valid PDF URL
    test_url = "https://www.archives.gov/files/research/jfk/releases/docid-32204484.pdf"
    
    # Download the test PDF
    pdf_path = download_pdf(test_url)
    
    # Verify the download was successful
    if pdf_path and os.path.exists(pdf_path):
        file_size = os.path.getsize(pdf_path)
        logger.info(f"Successfully downloaded PDF to {pdf_path}")
        logger.info(f"File size: {file_size} bytes")
        logger.info("PDF download test PASSED")
    else:
        logger.error("Failed to download PDF. Test FAILED")
    
except ImportError as e:
    print(f"Error importing from src.jfk_scraper: {e}")
    # Just fail the test instead of exiting
    raise
except Exception as e:
    print(f"Error during PDF download test: {e}")
    sys.exit(1)
