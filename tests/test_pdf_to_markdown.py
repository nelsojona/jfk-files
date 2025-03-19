#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for PDF to Markdown conversion functionality with Marker.

This script tests converting PDF documents to Markdown using the Marker library,
with validation for conversion quality and OCR functionality.
"""

import sys
import os
import logging
import argparse
import re

# Add parent directory to python path to import from jfk_scraper.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def validate_markdown_quality(markdown_content):
    """
    Validates the quality of converted markdown content.
    
    Args:
        markdown_content (str): The markdown content to validate
        
    Returns:
        tuple: (is_valid, results) where is_valid is a boolean indicating if the content meets 
               quality standards and results is a dict with validation metrics
    """
    results = {
        "has_title": False,
        "has_paragraphs": False,
        "paragraph_count": 0,
        "word_count": 0,
        "has_structure": False,
        "quality_score": 0
    }
    
    # Check for title (# heading)
    if re.search(r'^#\s+.+', markdown_content, re.MULTILINE):
        results["has_title"] = True
    
    # Count paragraphs (text blocks separated by blank lines)
    paragraphs = re.split(r'\n\s*\n', markdown_content)
    non_empty_paragraphs = [p for p in paragraphs if p.strip()]
    results["paragraph_count"] = len(non_empty_paragraphs)
    results["has_paragraphs"] = results["paragraph_count"] > 0
    
    # Count words
    results["word_count"] = len(re.findall(r'\b\w+\b', markdown_content))
    
    # Check for document structure (headers, lists, etc.)
    structure_patterns = [
        r'^#{2,}\s+.+',  # ## headings
        r'^\s*[-*+]\s+.+',  # bullet lists
        r'^\s*\d+\.\s+.+',  # numbered lists
        r'^\s*>.+',  # blockquotes
        r'^\s*```',  # code blocks
        r'\|.+\|'  # tables
    ]
    
    for pattern in structure_patterns:
        if re.search(pattern, markdown_content, re.MULTILINE):
            results["has_structure"] = True
            break
    
    # Calculate quality score (0-100)
    score = 0
    if results["has_title"]:
        score += 20
    
    # Score based on paragraph count (max 30)
    para_score = min(30, results["paragraph_count"] * 5)
    score += para_score
    
    # Score based on word count (max 30)
    word_score = min(30, results["word_count"] / 10)
    score += word_score
    
    # Score for structure (20)
    if results["has_structure"]:
        score += 20
    
    results["quality_score"] = score
    
    # Consider valid if score is above 60
    is_valid = score >= 60
    
    return is_valid, results

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test PDF to Markdown conversion with Marker")
    parser.add_argument("--pdf", default="pdfs/docid-32204484.pdf", help="Path to PDF file for testing")
    parser.add_argument("--force-ocr", action="store_true", help="Force OCR processing for conversion")
    parser.add_argument("--validate", action="store_true", help="Perform quality validation on output")
    args = parser.parse_args()

    try:
        # Import required functions
        from jfk_scraper import pdf_to_markdown, create_directories, logger, HAS_MARKER
        
        # Make sure directories exist
        create_directories()
        
        # Configure test-specific logging
        logger.info("=" * 80)
        logger.info("Starting PDF to Markdown conversion test with Marker")
        logger.info(f"Marker library available: {HAS_MARKER}")
        if args.force_ocr:
            logger.info("OCR processing enabled for testing")
        
        # Check if the specified PDF exists
        pdf_path = args.pdf
        if not os.path.exists(pdf_path):
            logger.error(f"Test PDF file not found at {pdf_path}")
            logger.info("Checking for any available PDF file...")
            
            # Try to find any PDF in the pdfs directory as a fallback
            pdf_dir = "pdfs"
            pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
            if pdf_files:
                pdf_path = os.path.join(pdf_dir, pdf_files[0])
                logger.info(f"Using alternative PDF file: {pdf_path}")
            else:
                logger.error("No PDF files found in pdfs directory. Did you run test_download_pdf.py first?")
                sys.exit(1)
        
        # Convert the PDF to Markdown with or without OCR
        logger.info(f"Converting {pdf_path} to Markdown")
        markdown_path, markdown_content = pdf_to_markdown(pdf_path, force_ocr=args.force_ocr)
        
        # Verify the conversion was successful
        if markdown_path and os.path.exists(markdown_path) and markdown_content:
            file_size = os.path.getsize(markdown_path)
            logger.info(f"Successfully converted PDF to Markdown at {markdown_path}")
            logger.info(f"Markdown file size: {file_size} bytes")
            preview = markdown_content[:200].replace('\n', ' ')
            logger.info(f"Content preview: {preview}...")
            
            # If validate flag is set, perform quality validation
            if args.validate:
                logger.info("Performing quality validation on Markdown output...")
                is_valid, results = validate_markdown_quality(markdown_content)
                
                logger.info(f"Validation results:")
                logger.info(f"  Has title: {results['has_title']}")
                logger.info(f"  Paragraph count: {results['paragraph_count']}")
                logger.info(f"  Word count: {results['word_count']}")
                logger.info(f"  Has structure: {results['has_structure']}")
                logger.info(f"  Quality score: {results['quality_score']}/100")
                
                if is_valid:
                    logger.info("Quality validation PASSED")
                else:
                    logger.warning("Quality validation FAILED - content may be low quality")
            
            logger.info("PDF to Markdown conversion test PASSED")
        else:
            logger.error("Failed to convert PDF to Markdown. Test FAILED")
        
    except ImportError as e:
        logger.error(f"Error importing from jfk_scraper.py: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during PDF to Markdown conversion test: {e}")
        logger.exception("Detailed error information:")
        sys.exit(1)

if __name__ == "__main__":
    main()
