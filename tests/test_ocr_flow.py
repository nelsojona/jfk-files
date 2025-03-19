#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the enhanced PDF2Markdown wrapper that replaces Marker.
This script validates the implementation of the pdf-to-markdown integration.
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path

# Add the project root to path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import required utils
try:
    from src.utils.logging_utils import configure_logging
    logger = configure_logging(log_level=logging.INFO)
except ImportError:
    # Fallback if logging_utils is not available
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("test_ocr_flow")

def detect_document_format(pdf_path):
    """
    Detect if a PDF is likely a scanned document that would benefit from OCR.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        dict: Information about the document format
    """
    try:
        # Try to import our own detection function first
        try:
            from src.utils.pdf_utils import detect_document_format
            return detect_document_format(pdf_path, include_details=True)
        except ImportError:
            # Fallback to basic detection
            import fitz
            doc = fitz.open(pdf_path)
            
            # Sample a few pages to determine if the document is scanned
            text_blocks = 0
            image_blocks = 0
            pages_to_check = min(3, len(doc))
            
            for page_idx in range(pages_to_check):
                page = doc[page_idx]
                
                # Check text content
                text = page.get_text()
                if len(text.strip()) > 100:  # More than 100 chars of text
                    text_blocks += 1
                
                # Check image content
                images = page.get_images()
                if len(images) > 0:
                    image_blocks += 1
            
            doc.close()
            
            # If there are more images than text blocks, or very little text, likely scanned
            is_scanned = (image_blocks >= text_blocks) or (text_blocks == 0)
            
            # Create a format info dictionary similar to what our utility function returns
            return {
                "needs_ocr": is_scanned,
                "doc_type": "scanned" if is_scanned else "digital",
                "has_text": text_blocks > 0,
                "has_images": image_blocks > 0,
            }
            
    except Exception as e:
        logger.warning(f"Error in document format detection: {e}")
        return {"needs_ocr": True, "error": str(e)}

def test_pdf_to_markdown_conversion(pdf_path, output_dir=None, force_ocr=False, quality="high", use_gpt=False):
    """
    Test the PDF to markdown conversion with our new wrapper.
    
    Args:
        pdf_path (str): Path to the PDF file to test
        output_dir (str, optional): Directory to save the output markdown
        force_ocr (bool): Whether to force OCR processing
        quality (str): OCR quality setting ("low", "medium", "high")
        use_gpt (bool): Whether to use GPT-based conversion
        
    Returns:
        dict: Conversion results and metrics
    """
    try:
        # Try to import our new wrapper
        try:
            from src.utils.pdf2md_wrapper import convert_pdf_to_markdown
            logger.info("Using new pdf2md_wrapper implementation")
        except ImportError:
            logger.error("pdf2md_wrapper not found")
            return {"success": False, "error": "No conversion implementation available"}
        
        # Ensure the input file exists
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return {"success": False, "error": "PDF file not found"}
        
        # Create output directory if needed
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Create output path
        basename = os.path.basename(pdf_path)
        base_name, _ = os.path.splitext(basename)
        output_suffix = ""
        if force_ocr:
            output_suffix += f"_with_ocr_{quality}"
        else:
            output_suffix += "_without_ocr"
        
        output_path = None
        if output_dir:
            output_path = os.path.join(output_dir, f"{base_name}{output_suffix}.md")
        
        # Analyze the document format
        format_start = time.time()
        format_info = detect_document_format(pdf_path)
        format_time = time.time() - format_start
        
        # Log document format info
        logger.info(f"Document format detection for {basename}:")
        logger.info(f"  - Is scanned: {format_info.get('needs_ocr', 'Unknown')}")
        logger.info(f"  - Document type: {format_info.get('doc_type', 'Unknown')}")
        logger.info(f"  - Has text: {format_info.get('has_text', 'Unknown')}")
        logger.info(f"  - Detection time: {format_time:.2f}s")
        
        # Convert PDF to markdown
        logger.info(f"Converting {pdf_path} to markdown:")
        logger.info(f"  - Force OCR: {force_ocr}")
        logger.info(f"  - Quality: {quality}")
        logger.info(f"  - Use GPT: {use_gpt}")
        
        conversion_start = time.time()
        markdown_text = convert_pdf_to_markdown(
            pdf_path,
            output_path=output_path,
            force_ocr=force_ocr,
            ocr_quality=quality,
            use_gpt=use_gpt if 'use_gpt' in locals() else False  # Only pass use_gpt if supported
        )
        conversion_time = time.time() - conversion_start
        
        # Check if conversion was successful
        success = markdown_text and len(markdown_text.strip()) > 100
        content_length = len(markdown_text) if markdown_text else 0
        
        if success:
            logger.info(f"Successfully converted {pdf_path} to markdown:")
            logger.info(f"  - Content length: {content_length} characters")
            logger.info(f"  - Conversion time: {conversion_time:.2f}s")
            
            if output_path:
                logger.info(f"  - Output saved to: {output_path}")
        else:
            logger.error(f"Conversion failed or produced insufficient content")
        
        # Return comprehensive results
        return {
            "success": success,
            "output_path": output_path,
            "content_length": content_length,
            "conversion_time": conversion_time,
            "format_detection_time": format_time,
            "format_info": format_info,
            "total_time": conversion_time + format_time
        }
            
    except Exception as e:
        logger.error(f"Error testing PDF to markdown conversion: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def batch_test_ocr(pdf_dir, quality="high", output_dir=None, compare_methods=False):
    """
    Test OCR conversion on all PDFs in a directory.
    
    Args:
        pdf_dir (str): Directory containing PDF files to test
        quality (str): OCR quality setting (low, medium, high)
        output_dir (str): Directory to save output files
        compare_methods (bool): Whether to compare OCR vs non-OCR methods
        
    Returns:
        dict: Summary of results
    """
    if not os.path.isdir(pdf_dir):
        logger.error(f"PDF directory not found: {pdf_dir}")
        return {}
        
    # Find all PDF files in the directory
    pdf_files = [os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir) 
                if f.lower().endswith('.pdf') and os.path.isfile(os.path.join(pdf_dir, f))]
    
    if not pdf_files:
        logger.error(f"No PDF files found in directory: {pdf_dir}")
        return {}
        
    logger.info(f"Found {len(pdf_files)} PDF files to test")
    
    # Process each PDF file and collect results
    results = {}
    total_time = 0
    success_count = 0
    scanned_count = 0
    
    for pdf_path in pdf_files:
        pdf_filename = os.path.basename(pdf_path)
        logger.info(f"\n--- Testing PDF to Markdown conversion on {pdf_filename} ---")
        
        # Test with the specified settings
        conversion_results = test_pdf_to_markdown_conversion(
            pdf_path, 
            output_dir=output_dir, 
            force_ocr=True,  # Always use OCR for batch test
            quality=quality
        )
        
        if conversion_results.get("success", False):
            success_count += 1
            total_time += conversion_results.get("total_time", 0)
            
            if conversion_results.get("format_info", {}).get("needs_ocr", False):
                scanned_count += 1
                
            results[pdf_filename] = conversion_results
        
        # If comparing methods, also test without OCR
        if compare_methods:
            logger.info(f"\n--- Testing without OCR on {pdf_filename} ---")
            noocr_results = test_pdf_to_markdown_conversion(
                pdf_path, 
                output_dir=output_dir, 
                force_ocr=False,
                quality=quality
            )
            
            # Add to the results
            if pdf_filename in results:
                results[pdf_filename]["noocr_results"] = noocr_results
                
                # Log comparison if both methods succeeded
                if noocr_results.get("success", False) and results[pdf_filename].get("success", False):
                    ocr_length = results[pdf_filename].get("content_length", 0)
                    noocr_length = noocr_results.get("content_length", 0)
                    length_diff = ocr_length - noocr_length
                    time_diff = results[pdf_filename].get("conversion_time", 0) - noocr_results.get("conversion_time", 0)
                    
                    logger.info(f"Comparison for {pdf_filename}:")
                    logger.info(f"  - OCR content length: {ocr_length} chars")
                    logger.info(f"  - Non-OCR content length: {noocr_length} chars")
                    logger.info(f"  - Content difference: {length_diff} chars ({length_diff/max(1, noocr_length)*100:.1f}%)")
                    logger.info(f"  - Time difference: {time_diff:.2f}s ({time_diff/max(0.1, noocr_results.get('conversion_time', 0.1))*100:.1f}%)")
    
    # Summarize the batch results
    if results:
        avg_time = total_time / success_count if success_count > 0 else 0
        logger.info(f"\n=== Batch Testing Summary ===")
        logger.info(f"Total PDF files tested: {len(pdf_files)}")
        logger.info(f"Successfully processed: {success_count}")
        logger.info(f"Detected as scanned: {scanned_count}")
        logger.info(f"Average processing time: {avg_time:.2f} seconds")
        logger.info(f"Total processing time: {total_time:.2f} seconds")
    
    return results

def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(description="Test the PDF to markdown conversion wrapper")
    parser.add_argument(
        "--pdf", 
        "-p",
        help="Path to a specific PDF file to test"
    )
    parser.add_argument(
        "--dir", 
        "-d",
        help="Directory containing PDF files to test"
    )
    parser.add_argument(
        "--output-dir", 
        "-o",
        default="test_output",
        help="Directory to save the output markdown (default: test_output)"
    )
    parser.add_argument(
        "--force-ocr", 
        "-f",
        action="store_true",
        help="Force OCR processing even for digital PDFs"
    )
    parser.add_argument(
        "--quality", 
        "-q",
        choices=["low", "medium", "high"],
        default="high",
        help="OCR quality setting (default: high)"
    )
    parser.add_argument(
        "--gpt", 
        "-g",
        action="store_true",
        help="Use GPT-based conversion (requires API key)"
    )
    parser.add_argument(
        "--compare", 
        "-c",
        action="store_true",
        help="Compare OCR vs non-OCR methods"
    )
    parser.add_argument(
        "--test-all", 
        "-a",
        action="store_true",
        help="Test all combinations of OCR and quality settings"
    )
    
    args = parser.parse_args()
    
    # Default to test_document.pdf if no PDF or directory is specified
    if not args.pdf and not args.dir:
        default_test_pdf = "test_data/test_document.pdf"
        if os.path.exists(default_test_pdf):
            args.pdf = default_test_pdf
            logger.info(f"No PDF or directory specified, using default test PDF: {default_test_pdf}")
        else:
            logger.error("No PDF or directory specified, and default test PDF not found")
            return 1
    
    # Create output directory if needed
    if args.output_dir and not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # If testing a directory of PDFs
    if args.dir:
        batch_test_ocr(args.dir, args.quality, args.output_dir, args.compare)
        return 0
    
    # If testing a single PDF file
    if args.test_all:
        # Test all combinations
        results = []
        
        # Test without OCR
        logger.info("Testing without OCR")
        result_no_ocr = test_pdf_to_markdown_conversion(
            args.pdf, 
            args.output_dir, 
            force_ocr=False, 
            quality="high",
            use_gpt=False
        )
        results.append(("No OCR", result_no_ocr.get("success", False)))
        
        # Test with OCR and different quality settings
        for quality in ["low", "medium", "high"]:
            logger.info(f"Testing with OCR, quality={quality}")
            result_ocr = test_pdf_to_markdown_conversion(
                args.pdf, 
                args.output_dir, 
                force_ocr=True, 
                quality=quality,
                use_gpt=False
            )
            results.append((f"OCR {quality}", result_ocr.get("success", False)))
        
        # Test with GPT if requested
        if args.gpt:
            logger.info("Testing with GPT")
            result_gpt = test_pdf_to_markdown_conversion(
                args.pdf, 
                args.output_dir, 
                force_ocr=False, 
                quality="high",
                use_gpt=True
            )
            results.append(("GPT", result_gpt.get("success", False)))
        
        # Print summary
        logger.info("Test summary:")
        for name, success in results:
            logger.info(f"{name}: {'SUCCESS' if success else 'FAILED'}")
        
        # Return success if at least one test succeeded
        return 0 if any(success for _, success in results) else 1
        
    else:
        # Test with specific settings
        result = test_pdf_to_markdown_conversion(
            args.pdf, 
            args.output_dir, 
            force_ocr=args.force_ocr, 
            quality=args.quality,
            use_gpt=args.gpt
        )
        return 0 if result.get("success", False) else 1

if __name__ == "__main__":
    sys.exit(main())