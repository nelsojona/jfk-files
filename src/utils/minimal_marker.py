#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal Marker implementation for PDF to Markdown conversion.

This is a compatibility wrapper that now uses the new pdf2md_wrapper
to maintain backwards compatibility with code that expects the MinimalMarker class.
"""

import os
import logging
import re
from pathlib import Path

# Initialize logger
logger = logging.getLogger("jfk_scraper.minimal_marker")

class MinimalMarker:
    """
    A compatibility wrapper for the Marker PDF to Markdown converter.
    Now uses the pdf2md_wrapper internally for all conversions.
    """
    
    def __init__(self):
        """Initialize the minimal marker with dependencies check."""
        self.pdf2md_available = False
        try:
            from src.utils.pdf2md_wrapper import convert_pdf_to_markdown
            self.pdf2md_available = True
            logger.info("MinimalMarker: pdf2md_wrapper available")
        except ImportError as e:
            logger.warning(f"MinimalMarker: pdf2md_wrapper not available: {e}")
            
            # Fallback to check PyMuPDF
            self.pymupdf_available = False
            try:
                import fitz  # PyMuPDF
                self.pymupdf_available = True
                logger.info("MinimalMarker: PyMuPDF available (fallback)")
            except ImportError as e:
                logger.warning(f"MinimalMarker: PyMuPDF not available: {e}")
    
    def markdown(self, pdf_path, force_ocr=False, ocr_quality="high"):
        """
        Convert a PDF file to markdown text using pdf2md_wrapper.
        
        Args:
            pdf_path (str): Path to the PDF file to convert
            force_ocr (bool): Whether to force OCR processing
            ocr_quality (str): OCR quality setting ("low", "medium", "high")
            
        Returns:
            str: Markdown text from the PDF
        """
        logger.info(f"MinimalMarker: Converting {pdf_path} to markdown")
        
        if not os.path.exists(pdf_path):
            logger.error(f"MinimalMarker: PDF file not found: {pdf_path}")
            return self._fallback_convert(pdf_path)
            
        # Use pdf2md_wrapper if available
        if self.pdf2md_available:
            try:
                from src.utils.pdf2md_wrapper import convert_pdf_to_markdown
                logger.info(f"MinimalMarker: Using pdf2md_wrapper for {pdf_path}")
                return convert_pdf_to_markdown(
                    pdf_path,
                    force_ocr=force_ocr,
                    ocr_quality=ocr_quality
                )
            except Exception as e:
                logger.error(f"MinimalMarker: Error using pdf2md_wrapper: {e}")
                # Fall through to fallback methods
        
        # Fallback to PyMuPDF directly if available
        if self.pymupdf_available:
            try:
                logger.info(f"MinimalMarker: Using PyMuPDF fallback for {pdf_path}")
                return self._convert_with_pymupdf(pdf_path)
            except Exception as e:
                logger.error(f"MinimalMarker: Error with PyMuPDF fallback: {e}")
                # Fall through to basic fallback
                
        # Last resort fallback
        logger.warning(f"MinimalMarker: All conversion methods failed for {pdf_path}")
        return self._fallback_convert(pdf_path)
    
    def _convert_with_pymupdf(self, pdf_path):
        """Extract text from PDF using PyMuPDF."""
        try:
            import fitz  # PyMuPDF
            
            # Open the PDF
            doc = fitz.open(pdf_path)
            
            # Extract filename for title
            filename = os.path.basename(pdf_path)
            base_name, _ = os.path.splitext(filename)
            
            # Create markdown content
            md_parts = [f"# {base_name}"]
            
            # Add metadata
            md_parts.append("\n## Document Information\n")
            
            try:
                metadata = doc.metadata
                if metadata:
                    md_parts.append("| Attribute | Value |")
                    md_parts.append("| --- | --- |")
                    for key, value in metadata.items():
                        if value and str(value).strip():
                            md_parts.append(f"| {key} | {value} |")
            except Exception as e:
                logger.debug(f"MinimalMarker: Error extracting metadata: {e}")
            
            md_parts.append(f"\n- **Pages**: {len(doc)}")
            md_parts.append(f"- **Filename**: {filename}")
            
            # Extract text from each page
            md_parts.append("\n## Document Content\n")
            
            for page_num in range(len(doc)):
                try:
                    page = doc.load_page(page_num)
                    page_text = page.get_text()
                    
                    # Clean up text
                    page_text = self._clean_text(page_text)
                    
                    # Add page header and text
                    md_parts.append(f"\n### Page {page_num + 1}\n")
                    md_parts.append(page_text)
                    
                except Exception as e:
                    logger.warning(f"MinimalMarker: Error extracting text from page {page_num + 1}: {e}")
                    md_parts.append(f"\n### Page {page_num + 1}\n")
                    md_parts.append(f"*Error extracting text: {str(e)}*")
            
            # Close the document
            doc.close()
            
            # Join all parts into a single markdown string
            markdown = "\n".join(md_parts)
            return markdown
            
        except Exception as e:
            logger.error(f"MinimalMarker: Error converting PDF with PyMuPDF: {e}")
            raise
    
    def _clean_text(self, text):
        """Clean up extracted text for better markdown formatting."""
        if not text:
            return ""
            
        # Replace multiple spaces with a single space
        text = re.sub(r'\s{2,}', ' ', text)
        
        # Replace multiple newlines with at most two
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove lone hyphens at the end of lines (often word breaks)
        text = re.sub(r'-\n', '', text)
        
        return text
    
    def _fallback_convert(self, pdf_path):
        """Fallback PDF to Markdown conversion when extraction fails."""
        logger.warning(f"MinimalMarker: Using basic fallback conversion for {pdf_path}")
        
        # Simple fallback that creates a basic markdown structure
        try:
            # Create a minimal markdown representation based on the PDF filename
            filename = os.path.basename(pdf_path)
            base_name, _ = os.path.splitext(filename)
            
            # Return a basic markdown structure
            markdown = f"""# {base_name}

## Document Information

- **Filename**: {filename}
- **Path**: {pdf_path}
- **Conversion Note**: This is a fallback conversion because all extraction methods failed

## Content

*This document requires better PDF processing capabilities.*
*Ensure PyMuPDF and pdf2md_wrapper are properly installed.*

"""
            return markdown
            
        except Exception as e:
            logger.error(f"MinimalMarker: Even fallback conversion failed: {e}")
            return f"# Error Processing {os.path.basename(pdf_path)}\n\nFailed to convert file: {str(e)}"

def convert_pdf_to_markdown(pdf_path, force_ocr=False, ocr_quality="high"):
    """
    Convenience function to convert a PDF file to markdown text.
    
    Args:
        pdf_path (str): Path to the PDF file to convert
        force_ocr (bool): Whether to force OCR processing
        ocr_quality (str): OCR quality setting ("low", "medium", "high")
        
    Returns:
        str: Markdown text from the PDF
    """
    try:
        # Try to use pdf2md_wrapper directly first
        try:
            from src.utils.pdf2md_wrapper import convert_pdf_to_markdown as pdf2md_convert
            logger.info(f"Using pdf2md_wrapper for {pdf_path}")
            return pdf2md_convert(
                pdf_path,
                force_ocr=force_ocr,
                ocr_quality=ocr_quality
            )
        except ImportError:
            # Fall back to MinimalMarker if pdf2md_wrapper is not available
            logger.info(f"pdf2md_wrapper not available, using MinimalMarker for {pdf_path}")
            marker = MinimalMarker()
            return marker.markdown(pdf_path, force_ocr, ocr_quality)
            
    except Exception as e:
        logger.error(f"Error in convert_pdf_to_markdown: {str(e)}")
        # Return a simple error message
        filename = os.path.basename(pdf_path)
        return f"# {filename}\n\nError processing PDF file: {str(e)}"

if __name__ == "__main__":
    # Test the minimal marker if run directly
    import sys
    import argparse
    
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set up command line arguments
    parser = argparse.ArgumentParser(description="Convert PDF to Markdown")
    parser.add_argument("pdf_file", help="Path to the PDF file to convert")
    parser.add_argument(
        "--output", 
        "-o",
        help="Path to save the output markdown file"
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
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_file):
        print(f"Error: File '{args.pdf_file}' not found")
        sys.exit(1)
    
    try:
        # Convert the PDF
        marker = MinimalMarker()
        md_text = marker.markdown(
            args.pdf_file,
            force_ocr=args.force_ocr,
            ocr_quality=args.quality
        )
        
        # Save to file if output path specified
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(md_text)
            print(f"Markdown saved to: {args.output}")
        else:
            print("\nConversion successful! Excerpt:")
            # Print first 500 characters
            print(md_text[:500] + "..." if len(md_text) > 500 else md_text)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)