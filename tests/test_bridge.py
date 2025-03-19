#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the pdf2md_wrapper module
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_pdf2md")

# Ensure we have a test PDF
test_pdf_path = "test_data/test_document.pdf"
if not os.path.exists(test_pdf_path):
    logger.error(f"Test PDF not found: {test_pdf_path}")
    logger.info("Please create a test PDF first or run test_marker.py to generate one")
    sys.exit(1)

logger.info(f"Using test PDF: {test_pdf_path}")

# Try to import the pdf2md_wrapper module
try:
    from src.utils.pdf2md_wrapper import PDF2MarkdownWrapper, convert_pdf_to_markdown
    logger.info("Successfully imported pdf2md_wrapper")
    
    # Test if the wrapper works
    wrapper = PDF2MarkdownWrapper()
    logger.info(f"Created PDF2MarkdownWrapper instance: {wrapper.__class__.__name__}")
    
    # Log available modules
    logger.info(f"Available modules:")
    logger.info(f"- PyMuPDF: {'Available' if wrapper.pymupdf_available else 'Not available'}")
    logger.info(f"- pytesseract: {'Available' if wrapper.pytesseract_available else 'Not available'}")
    logger.info(f"- pdf2image: {'Available' if wrapper.pdf2image_available else 'Not available'}")
    logger.info(f"- pdf2md: {'Available' if wrapper.pdf2md_available else 'Not available'}")
    
    # Convert a PDF to markdown
    logger.info(f"Converting PDF to markdown with wrapper...")
    markdown = wrapper.markdown(test_pdf_path)
    
    # Save the result
    output_path = "test_output/pdf2md_test.md"
    os.makedirs("test_output", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    
    logger.info(f"Saved markdown to {output_path}")
    logger.info(f"Markdown length: {len(markdown)} characters")
    
    # Print an excerpt
    excerpt_length = 200
    excerpt = markdown[:excerpt_length] + ("..." if len(markdown) > excerpt_length else "")
    logger.info(f"Excerpt: {excerpt}")
    
    # Success!
    logger.info("PDF2MarkdownWrapper is working correctly!")
    
except Exception as e:
    logger.error(f"Error testing PDF2MarkdownWrapper: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)