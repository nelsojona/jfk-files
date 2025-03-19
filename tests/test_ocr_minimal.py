#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal test script for the OCR flow in the JFK Files project

This script tests only the PDF to Markdown conversion using our custom minimal pdf2md implementation.
"""

import os
import sys
import logging
import shutil

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_ocr_minimal")

# Ensure we have a test PDF
test_pdf_path = "test_data/test_document.pdf"
if not os.path.exists(test_pdf_path):
    logger.error(f"Test PDF not found: {test_pdf_path}")
    logger.info("Please run test_marker.py first to create a test PDF")
    sys.exit(1)

logger.info(f"Using test PDF: {test_pdf_path}")

# Create test output directories if they don't exist
os.makedirs("test_output", exist_ok=True)

# Use our minimal marker implementation directly
logger.info("Importing minimal PDF2MD implementation...")
from src.utils.minimal_marker import MinimalMarker  # Compatibility wrapper around pdf2md_wrapper

# Convert the PDF to markdown
logger.info("Converting PDF to markdown with minimal PDF2MD implementation...")
try:
    marker = MinimalMarker()
    markdown_text = marker.markdown(test_pdf_path)
    
    # Save the markdown output
    markdown_path = "test_output/test_document_minimal.md"
    with open(markdown_path, "w", encoding="utf-8") as md_file:
        md_file.write(markdown_text)
    
    logger.info(f"Saved markdown to: {markdown_path}")
    logger.info(f"Markdown length: {len(markdown_text)} characters")
    
    # Test successful
    logger.info("Test completed successfully!")
    logger.info("The minimal PDF2MD implementation is working properly")
    
except Exception as e:
    logger.error(f"Error during minimal PDF2MD test: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)