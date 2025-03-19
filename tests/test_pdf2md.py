#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the PDF to Markdown conversion functionality
"""

import os
import sys
import logging
from src.utils.pdf2md_wrapper import convert_pdf_to_markdown, PDF2MarkdownWrapper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Check command line arguments
if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <pdf_file>")
    sys.exit(1)

pdf_file = sys.argv[1]
if not os.path.exists(pdf_file):
    print(f"Error: File '{pdf_file}' not found")
    sys.exit(1)

print("Testing pdf2md_wrapper.py with all fallbacks...")
print(f"PDF file: {pdf_file}")

# Create the wrapper
wrapper = PDF2MarkdownWrapper()

# Check available modules
print("\nAvailable modules:")
print(f"- PyMuPDF: {'Available' if wrapper.pymupdf_available else 'Not available'}")
print(f"- pytesseract: {'Available' if wrapper.pytesseract_available else 'Not available'}")
print(f"- pdf2image: {'Available' if wrapper.pdf2image_available else 'Not available'}")
print(f"- pdf2md: {'Available' if wrapper.pdf2md_available else 'Not available'}")

# Try to convert to markdown
try:
    print("\nConverting PDF to markdown...")
    
    # Try without OCR first
    print("\nTrying without forced OCR...")
    md_text_no_ocr = wrapper.markdown(pdf_file, force_ocr=False)
    
    # Try with OCR
    print("\nTrying with forced OCR (high quality)...")
    md_text_ocr = wrapper.markdown(pdf_file, force_ocr=True, ocr_quality="high")
    
    # Show excerpts
    print("\nConversion without OCR (excerpt):")
    print("-" * 80)
    print(md_text_no_ocr[:500] + "..." if len(md_text_no_ocr) > 500 else md_text_no_ocr)
    print("-" * 80)
    
    print("\nConversion with OCR (excerpt):")
    print("-" * 80)
    print(md_text_ocr[:500] + "..." if len(md_text_ocr) > 500 else md_text_ocr)
    print("-" * 80)
    
    # Show status
    print(f"\nConversion completed successfully")
    print(f"Markdown without OCR length: {len(md_text_no_ocr)} characters")
    print(f"Markdown with OCR length: {len(md_text_ocr)} characters")
    
    # Check for fallback indicators
    if "fallback" in md_text_no_ocr.lower() or "error" in md_text_no_ocr.lower():
        print("NOTE: A fallback conversion method was used for non-OCR conversion")
        
    if "fallback" in md_text_ocr.lower() or "error" in md_text_ocr.lower():
        print("NOTE: A fallback conversion method was used for OCR conversion")
    
    # Option to save the output
    should_save = input("\nDo you want to save the output to files? (y/n): ").strip().lower()
    if should_save == 'y':
        basename = os.path.splitext(os.path.basename(pdf_file))[0]
        no_ocr_file = f"{basename}_no_ocr.md"
        ocr_file = f"{basename}_with_ocr.md"
        
        with open(no_ocr_file, 'w', encoding='utf-8') as f:
            f.write(md_text_no_ocr)
        
        with open(ocr_file, 'w', encoding='utf-8') as f:
            f.write(md_text_ocr)
            
        print(f"Files saved: {no_ocr_file}, {ocr_file}")
        
except Exception as e:
    print(f"Error during conversion: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)