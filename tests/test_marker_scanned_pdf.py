#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test module for validating PDF to Markdown OCR functionality with scanned PDFs.
This uses the new pdf2md_wrapper implementation.
"""

import os
import sys
import unittest
import logging
from pathlib import Path

# Add the project root to path to ensure imports work
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import required utils 
from src.utils.logging_utils import configure_logging
from src.utils.pdf_utils import is_scanned_pdf, detect_document_format
from src.utils.conversion_utils import pdf_to_markdown, validate_markdown_quality
from src.utils.pdf2md_wrapper import convert_pdf_to_markdown, PDF2MarkdownWrapper

# Configure logging
logger = configure_logging(log_level=logging.INFO)

class TestPDFToMarkdownOCR(unittest.TestCase):
    """Test case for validating pdf2md_wrapper OCR extraction from scanned PDFs."""

    @classmethod
    def setUpClass(cls):
        """Set up the test environment once before all tests."""
        # Define test PDF and output paths
        cls.test_data_dir = os.path.join(parent_dir, "test_data")
        cls.test_output_dir = os.path.join(parent_dir, "test_output")
        cls.test_doc_path = os.path.join(cls.test_data_dir, "test_document.pdf")
        
        # If test_document.pdf doesn't exist, try to find any PDF in the pdfs directory
        if not os.path.exists(cls.test_doc_path):
            cls.pdfs_dir = os.path.join(parent_dir, "pdfs")
            if os.path.exists(cls.pdfs_dir):
                for root, _, files in os.walk(cls.pdfs_dir):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            cls.test_doc_path = os.path.join(root, file)
                            logger.info(f"Using {cls.test_doc_path} for tests")
                            break
                    if os.path.exists(cls.test_doc_path):
                        break
        
        # Create output directory if it doesn't exist
        os.makedirs(cls.test_output_dir, exist_ok=True)

    def setUp(self):
        """Set up before each test."""
        # Skip all tests if no test document is found
        if not os.path.exists(self.test_doc_path):
            self.skipTest("No test document found")
    
    def test_document_format_detection(self):
        """Test if document format detection correctly identifies scanned PDFs."""
        # Check if the document exists
        self.assertTrue(os.path.exists(self.test_doc_path), 
                       f"Test document not found at {self.test_doc_path}")
        
        # Get document format information
        format_info = detect_document_format(self.test_doc_path, include_details=True)
        
        # Validate format information structure
        self.assertIsInstance(format_info, dict, "Format info should be a dictionary")
        self.assertIn("doc_type", format_info, "Format info should include document type")
        self.assertIn("has_text", format_info, "Format info should indicate if text exists")
        self.assertIn("needs_ocr", format_info, "Format info should indicate if OCR is needed")
        
        # Log format information for review
        logger.info(f"Document format detection results: {format_info}")

    def test_scanned_pdf_detection(self):
        """Test if scanned PDF detection identifies scanned documents correctly."""
        # Check basic function call
        is_scanned = is_scanned_pdf(self.test_doc_path)
        logger.info(f"Document detected as {'scanned' if is_scanned else 'digital'} PDF")
        
        # This is more of an informational test since we don't know ahead of time
        # if the test document is actually scanned
        self.assertIsInstance(is_scanned, bool, "Detection result should be boolean")

    def test_ocr_conversion(self):
        """Test OCR conversion with various quality settings."""
        # Set output paths for different quality settings
        low_quality_path = os.path.join(self.test_output_dir, "test_document_with_ocr_low.md")
        medium_quality_path = os.path.join(self.test_output_dir, "test_document_with_ocr_medium.md")
        high_quality_path = os.path.join(self.test_output_dir, "test_document_with_ocr_high.md")
        
        # Try conversion with different OCR quality settings if not already done
        if not os.path.exists(low_quality_path):
            logger.info("Converting with low quality OCR...")
            low_quality_content = convert_pdf_to_markdown(
                self.test_doc_path, force_ocr=True, ocr_quality="low"
            )
            with open(low_quality_path, 'w', encoding='utf-8') as f:
                f.write(low_quality_content)
        
        if not os.path.exists(medium_quality_path):
            logger.info("Converting with medium quality OCR...")
            medium_quality_content = convert_pdf_to_markdown(
                self.test_doc_path, force_ocr=True, ocr_quality="medium"
            )
            with open(medium_quality_path, 'w', encoding='utf-8') as f:
                f.write(medium_quality_content)
                
        if not os.path.exists(high_quality_path):
            logger.info("Converting with high quality OCR...")
            high_quality_content = convert_pdf_to_markdown(
                self.test_doc_path, force_ocr=True, ocr_quality="high"
            )
            with open(high_quality_path, 'w', encoding='utf-8') as f:
                f.write(high_quality_content)
        
        # Verify files were created
        self.assertTrue(os.path.exists(low_quality_path), "Low quality output file not created")
        self.assertTrue(os.path.exists(medium_quality_path), "Medium quality output file not created")
        self.assertTrue(os.path.exists(high_quality_path), "High quality output file not created")
        
        # Check file sizes (expect higher quality to generally produce more content)
        low_size = os.path.getsize(low_quality_path)
        medium_size = os.path.getsize(medium_quality_path)
        high_size = os.path.getsize(high_quality_path)
        
        logger.info(f"Low quality file size: {low_size} bytes")
        logger.info(f"Medium quality file size: {medium_size} bytes")
        logger.info(f"High quality file size: {high_size} bytes")
        
        # This is an informational test, not a strict assertion since
        # in some cases lower quality OCR could produce more text due to artifacts
        if high_size < low_size:
            logger.warning("Unexpected: High quality file is smaller than low quality")

    def test_ocr_vs_non_ocr(self):
        """Compare results between OCR and non-OCR extraction."""
        # Set output paths
        ocr_path = os.path.join(self.test_output_dir, "test_document_with_ocr_high.md")
        non_ocr_path = os.path.join(self.test_output_dir, "test_document_without_ocr.md")
        
        # Run conversions if not already done
        if not os.path.exists(ocr_path):
            logger.info("Running conversion with OCR...")
            ocr_content = convert_pdf_to_markdown(
                self.test_doc_path, force_ocr=True, ocr_quality="high"
            )
            with open(ocr_path, 'w', encoding='utf-8') as f:
                f.write(ocr_content)
        
        if not os.path.exists(non_ocr_path):
            logger.info("Running conversion without OCR...")
            non_ocr_content = convert_pdf_to_markdown(
                self.test_doc_path, force_ocr=False, ocr_quality="high"
            )
            with open(non_ocr_path, 'w', encoding='utf-8') as f:
                f.write(non_ocr_content)
        
        # Verify files were created
        self.assertTrue(os.path.exists(ocr_path), "OCR output file not created")
        self.assertTrue(os.path.exists(non_ocr_path), "Non-OCR output file not created")
        
        # Read file contents
        with open(ocr_path, 'r', encoding='utf-8') as f:
            ocr_content = f.read()
        
        with open(non_ocr_path, 'r', encoding='utf-8') as f:
            non_ocr_content = f.read()
        
        # Compare content lengths
        ocr_length = len(ocr_content)
        non_ocr_length = len(non_ocr_content)
        
        logger.info(f"OCR content length: {ocr_length} characters")
        logger.info(f"Non-OCR content length: {non_ocr_length} characters")
        
        # Calculate content difference percentage
        if non_ocr_length > 0:
            diff_percentage = ((ocr_length - non_ocr_length) / non_ocr_length) * 100
            logger.info(f"Content difference: {diff_percentage:.1f}%")
            
            # Validate OCR quality
            ocr_quality = validate_markdown_quality(ocr_content)
            non_ocr_quality = validate_markdown_quality(non_ocr_content)
            
            logger.info(f"OCR quality score: {ocr_quality['score']:.2f}")
            logger.info(f"Non-OCR quality score: {non_ocr_quality['score']:.2f}")
            
            if ocr_quality['issues']:
                logger.info(f"OCR quality issues: {', '.join(ocr_quality['issues'])}")
            
            if non_ocr_quality['issues']:
                logger.info(f"Non-OCR quality issues: {', '.join(non_ocr_quality['issues'])}")

    def test_pdf2md_wrapper(self):
        """Test the functionality of the PDF2MarkdownWrapper class."""
        # Create a wrapper instance
        wrapper = PDF2MarkdownWrapper()
        
        # Test markdown conversion
        logger.info("Testing PDF2MarkdownWrapper.markdown method...")
        markdown_content = wrapper.markdown(self.test_doc_path, force_ocr=True, ocr_quality="high")
        
        # Check that markdown content is generated
        self.assertIsNotNone(markdown_content, "Markdown content should not be None")
        self.assertIsInstance(markdown_content, str, "Markdown content should be a string")
        self.assertGreater(len(markdown_content), 0, "Markdown content should not be empty")
        
        # Write output to file for manual inspection
        output_path = os.path.join(self.test_output_dir, "test_document_minimal.md")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
            
        logger.info(f"PDF2MarkdownWrapper test output saved to {output_path}")
        
        # Test post-processing
        processed_content = wrapper._post_process_markdown(markdown_content)
        self.assertIsNotNone(processed_content, "Processed content should not be None")
        self.assertIsInstance(processed_content, str, "Processed content should be a string")

if __name__ == "__main__":
    unittest.main()