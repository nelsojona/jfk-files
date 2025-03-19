#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced wrapper for pdf2md implementation

This module provides a comprehensive interface to convert PDFs to markdown
using a combination of approaches including pdf2md, PyMuPDF, and pytesseract.
It's designed to replace the Marker bridge completely.
"""

import os
import logging
import tempfile
import traceback
import time
import re
import datetime
from pathlib import Path
from PIL import Image
import io

# Initialize logger
logger = logging.getLogger("jfk_scraper.pdf2md")

class PDF2MarkdownWrapper:
    """
    A comprehensive wrapper for PDF to Markdown conversion with multiple
    approaches and enhanced OCR capabilities.
    """
    
    def __init__(self):
        """Initialize the wrapper with all available conversion methods."""
        # Initialize flags for available modules
        self.pdf2md_available = False
        self.pymupdf_available = False
        self.pytesseract_available = False
        self.pdf2image_available = False
        
        logger.info("Initializing Enhanced PDF to Markdown Wrapper")
        
        # Check for PyMuPDF
        try:
            import fitz
            self.pymupdf_available = True
            logger.info("PyMuPDF available for text extraction")
        except ImportError:
            logger.warning("PyMuPDF not available")
        
        # Check for pytesseract
        try:
            import pytesseract
            self.pytesseract_available = True
            logger.info("Pytesseract available for OCR")
        except ImportError:
            logger.warning("Pytesseract not available")
        
        # Check for pdf2image
        try:
            import pdf2image
            self.pdf2image_available = True
            logger.info("pdf2image available for PDF conversion")
        except ImportError:
            logger.warning("pdf2image not available")
        
        # Check for pdf2md (our local implementation)
        try:
            from src.utils.pdf2md import page_image2md, get_page_images
            self.pdf2md_available = True
            logger.info("Local pdf2md implementation available")
        except ImportError:
            logger.warning("Local pdf2md implementation not available")
    
    def markdown(self, pdf_path, force_ocr=False, ocr_quality="high", use_gpt=False):
        """
        Convert a PDF file to markdown using the best available method.
        
        Args:
            pdf_path (str): Path to the PDF file to convert
            force_ocr (bool): Whether to force OCR processing even for digital PDFs
            ocr_quality (str): OCR quality setting ("low", "medium", "high")
            use_gpt (bool): Whether to use GPT-based conversion (requires API key)
            
        Returns:
            str: Markdown text from the PDF, or a fallback representation if conversion fails
        """
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return self._fallback_convert(pdf_path)
        
        # Determine if PDF needs OCR
        needs_ocr = force_ocr
        if not needs_ocr and not force_ocr:
            try:
                needs_ocr = self._is_likely_scanned(pdf_path)
                logger.info(f"PDF scan detection: {'scanned' if needs_ocr else 'digital'} PDF detected")
            except Exception as e:
                logger.warning(f"Error detecting if PDF is scanned: {e}")
                # Default to OCR if we can't detect
                needs_ocr = True
        
        # Log OCR decision
        logger.info(f"OCR decision for {pdf_path}: {'Using' if needs_ocr else 'Not using'} OCR")
        
        # Track conversion attempts for better error reporting
        conversion_attempts = []
        
        # If GPT-based conversion requested and available, try that first
        if use_gpt and self.pdf2md_available:
            try:
                logger.info(f"Attempting GPT-based conversion for {pdf_path}")
                markdown_text = self._convert_with_gpt(pdf_path, quality=ocr_quality)
                if markdown_text and len(markdown_text.strip()) > 100:
                    return markdown_text
                logger.warning("GPT-based conversion produced insufficient content")
            except Exception as e:
                error_details = f"GPT-based conversion failed: {str(e)}\n{traceback.format_exc()}"
                logger.warning(error_details)
                conversion_attempts.append(("gpt", error_details))
        
        # For digital PDFs, try PyMuPDF first (no OCR needed)
        if not needs_ocr and self.pymupdf_available:
            try:
                markdown_text = self._convert_with_pymupdf(pdf_path)
                if markdown_text and len(markdown_text.strip()) > 100:
                    return markdown_text
                logger.warning("PyMuPDF extraction produced insufficient content")
            except Exception as e:
                error_details = f"PyMuPDF conversion failed: {str(e)}\n{traceback.format_exc()}"
                logger.warning(error_details)
                conversion_attempts.append(("pymupdf", error_details))
        
        # For scanned PDFs or if PyMuPDF failed, try pytesseract OCR
        if (needs_ocr or not markdown_text) and self.pytesseract_available and self.pdf2image_available:
            try:
                markdown_text = self._convert_with_pytesseract(pdf_path, quality=ocr_quality)
                if markdown_text and len(markdown_text.strip()) > 100:
                    return markdown_text
                logger.warning("Pytesseract OCR produced insufficient content")
            except Exception as e:
                error_details = f"Pytesseract OCR failed: {str(e)}\n{traceback.format_exc()}"
                logger.warning(error_details)
                conversion_attempts.append(("pytesseract", error_details))
        
        # Last attempt with PyMuPDF if we skipped it before
        if needs_ocr and self.pymupdf_available:
            try:
                markdown_text = self._convert_with_pymupdf(pdf_path)
                if markdown_text and len(markdown_text.strip()) > 100:
                    return markdown_text
                logger.warning("Fallback PyMuPDF extraction produced insufficient content")
            except Exception as e:
                error_details = f"Fallback PyMuPDF conversion failed: {str(e)}\n{traceback.format_exc()}"
                logger.warning(error_details)
                conversion_attempts.append(("pymupdf_fallback", error_details))
        
        # If all else fails, use the fallback converter with detailed error info
        return self._fallback_convert(pdf_path, conversion_attempts)
    
    def _is_likely_scanned(self, pdf_path):
        """
        Detect if a PDF is likely a scanned document that would benefit from OCR.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            bool: True if the PDF is likely scanned, False if it's likely digital
        """
        # Try PyMuPDF for detection if available
        if self.pymupdf_available:
            try:
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
                logger.debug(f"Scanned PDF detection: text_blocks={text_blocks}, image_blocks={image_blocks}")
                return is_scanned
                
            except Exception as e:
                logger.debug(f"Error in PyMuPDF scan detection: {e}")
                # Fall through to basic check
        
        # Basic check based on file size if PyMuPDF fails
        try:
            file_size_kb = os.path.getsize(pdf_path) / 1024
            
            # Large PDFs with little text are often scans
            if file_size_kb > 1000:  # Larger than 1MB
                # Try to read the first few kb to check for text
                with open(pdf_path, 'rb') as f:
                    header = f.read(1024)  # Read first KB
                    # Check for text markers in PDF
                    if b'/Text' in header and b'/Font' in header:
                        return False  # Likely has text
                    else:
                        return True  # Likely scanned
            else:
                # Smaller PDFs are less likely to be scans
                return False
        except Exception as e:
            logger.debug(f"Error in basic scan detection: {e}")
            # Default to assuming it's scanned to be safe
            return True
    
    def _convert_with_pymupdf(self, pdf_path):
        """
        Extract text from PDF using PyMuPDF with enhanced formatting.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            str: Markdown text or None if extraction failed
        """
        logger.info(f"Attempting PyMuPDF extraction for {pdf_path}")
        
        try:
            # Only import fitz when needed
            import fitz
            
            # Open the PDF document
            doc = fitz.open(pdf_path)
            
            # Get document metadata
            metadata = {}
            try:
                metadata = doc.metadata
            except:
                pass
            
            # Format document title
            title = os.path.splitext(os.path.basename(pdf_path))[0]
            if metadata.get("title"):
                title = f"{title} - {metadata['title']}"
            
            # Extract text from each page with formatting
            full_text = [f"# {title}\n"]
            
            # Add metadata if available
            if metadata and any(metadata.values()):
                full_text.append("## Document Metadata\n")
                for key, value in metadata.items():
                    if value:
                        full_text.append(f"- **{key.capitalize()}**: {value}")
                full_text.append("")  # Empty line after metadata
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Get basic text
                text = page.get_text()
                
                # Check if the page has meaningful content
                if text and len(text.strip()) > 20:
                    # Add page header
                    full_text.append(f"## Page {page_num+1}\n")
                    
                    # Try to get structured content with blocks
                    try:
                        blocks = page.get_text("blocks")
                        if blocks:
                            # Process blocks to better preserve layout
                            processed_text = []
                            for block in blocks:
                                block_text = block[4].strip()
                                if block_text:
                                    # Try to detect headers vs paragraphs
                                    if len(block_text) < 100 and block_text.isupper():
                                        processed_text.append(f"### {block_text}")
                                    else:
                                        processed_text.append(block_text)
                            
                            full_text.append("\n\n".join(processed_text))
                        else:
                            full_text.append(text)
                    except:
                        # Fall back to basic text
                        full_text.append(text)
            
            doc.close()
            
            # Create final markdown
            if len(full_text) > 1:  # If we have more than just the title
                markdown = "\n\n".join(full_text)
                logger.info(f"Successfully extracted text with PyMuPDF from {pdf_path}")
                return self._post_process_markdown(markdown)
            else:
                logger.warning(f"PyMuPDF extraction produced no meaningful text for {pdf_path}")
                return None
                
        except ImportError:
            logger.warning("PyMuPDF (fitz) not available")
            return None
        except Exception as e:
            logger.warning(f"Error in PyMuPDF extraction: {str(e)}")
            return None
    
    def _convert_with_pytesseract(self, pdf_path, quality="high"):
        """
        Convert PDF to markdown using pytesseract OCR.
        
        Args:
            pdf_path (str): Path to the PDF file
            quality (str): OCR quality setting ("low", "medium", "high")
            
        Returns:
            str: Markdown text or None if extraction failed
        """
        logger.info(f"Attempting pytesseract OCR for {pdf_path} (Quality: {quality})")
        
        if not self.pytesseract_available or not self.pdf2image_available:
            logger.warning("Pytesseract or pdf2image not available")
            return None
        
        try:
            # Import required modules
            import pytesseract
            from pdf2image import convert_from_path
            
            # Set up OCR parameters based on quality
            dpi = 150  # Default DPI
            ocr_config = ""
            if quality == "high":
                dpi = 300
                ocr_config = "--oem 1 --psm 6"  # High quality, more accurate
            elif quality == "medium":
                dpi = 200
                ocr_config = "--oem 1 --psm 6"  # Default tesseract settings
            else:  # low
                dpi = 150
                ocr_config = "--oem 1 --psm 6"  # Use standard engine for compatibility
            
            # Get the PDF filename for title
            filename = os.path.basename(pdf_path)
            base_name = os.path.splitext(filename)[0]
            
            # Initialize markdown with document title
            markdown_parts = [f"# {base_name}\n"]
            
            # Convert PDF to images
            try:
                pdf_images = convert_from_path(
                    pdf_path,
                    dpi=dpi,
                    thread_count=4,
                    fmt="ppm"  # Format with good OCR results
                )
                
                # Process each page with OCR
                for i, image in enumerate(pdf_images):
                    logger.info(f"Processing page {i+1} of {len(pdf_images)} with OCR")
                    
                    # Add page header
                    markdown_parts.append(f"## Page {i+1}\n")
                    
                    # Perform OCR
                    try:
                        text = pytesseract.image_to_string(image, config=ocr_config)
                        if text and len(text.strip()) > 20:  # If we got meaningful text
                            # Process the extracted text
                            lines = text.split('\n')
                            processed_lines = []
                            
                            # Simple processing to detect potential headers
                            for line in lines:
                                if line.strip():
                                    if line.isupper() and len(line) < 100:
                                        processed_lines.append(f"### {line}")
                                    else:
                                        processed_lines.append(line)
                            
                            # Join lines with proper spacing
                            markdown_parts.append('\n'.join(processed_lines))
                        else:
                            markdown_parts.append("*No text detected on this page*\n")
                    except Exception as e:
                        logger.warning(f"OCR failed for page {i+1}: {str(e)}")
                        markdown_parts.append(f"*OCR processing failed for this page: {str(e)}*\n")
            except Exception as e:
                logger.error(f"PDF to image conversion failed: {str(e)}")
                return None
            
            # Combine all parts into final markdown
            markdown = "\n\n".join(markdown_parts)
            logger.info(f"Successfully extracted text with pytesseract from {pdf_path}")
            return self._post_process_markdown(markdown)
            
        except ImportError as e:
            logger.warning(f"Import error in pytesseract OCR: {str(e)}")
            return None
        except Exception as e:
            logger.warning(f"Error in pytesseract OCR: {str(e)}")
            return None
    
    def _convert_with_gpt(self, pdf_path, quality="high"):
        """
        Convert PDF to markdown using our local pdf2md implementation with GPT.
        
        Args:
            pdf_path (str): Path to the PDF file
            quality (str): Image quality setting ("low", "medium", "high")
            
        Returns:
            str: Markdown text or None if extraction failed
        """
        logger.info(f"Attempting GPT-based conversion for {pdf_path}")
        
        if not self.pdf2md_available:
            logger.warning("Local pdf2md implementation not available")
            return None
        
        try:
            # Import our local pdf2md implementation
            from src.utils.pdf2md import main, get_page_images
            
            # Set up parameters based on quality
            dpi = 150
            if quality == "high":
                dpi = 300
            elif quality == "medium":
                dpi = 200
            
            # Set up output file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as temp_output:
                output_path = temp_output.name
            
            try:
                # Convert PDF to markdown using our implementation
                pdf_path_obj = Path(pdf_path)
                main(
                    pdf_path_obj,
                    cache_pages=True,  # Cache pages to avoid repeated processing
                    page_dpi=dpi,
                    output_file=open(output_path, 'w')
                )
                
                # Read the output file
                with open(output_path, 'r', encoding='utf-8') as f:
                    markdown_text = f.read()
                
                # Post-process the markdown
                return self._post_process_markdown(markdown_text)
                
            finally:
                # Clean up temporary file
                try:
                    if os.path.exists(output_path):
                        os.unlink(output_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file: {str(e)}")
            
        except ImportError as e:
            logger.warning(f"Import error in GPT-based conversion: {str(e)}")
            return None
        except Exception as e:
            logger.warning(f"Error in GPT-based conversion: {str(e)}")
            return None
    
    def _post_process_markdown(self, markdown_text):
        """
        Improve markdown formatting and readability.
        
        Args:
            markdown_text (str): Raw markdown text
            
        Returns:
            str: Improved markdown text
        """
        if not markdown_text:
            return markdown_text
            
        # Fix common formatting issues
        result = markdown_text
        
        # Fix excessive newlines
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        # Fix bullet lists that got broken
        result = re.sub(r'(\n\s*[-*].*)\n([^-*\n])', r'\1\n\n\2', result)
        
        # Fix headers with missing newlines
        result = re.sub(r'(##+.*)\n([^#\n])', r'\1\n\n\2', result)
        
        # Remove common OCR artifacts
        result = re.sub(r'[­]', '', result)  # Remove soft hyphens
        
        return result
    
    def _fallback_convert(self, pdf_path, conversion_attempts=None):
        """
        Create a basic markdown representation when other methods fail.
        
        Args:
            pdf_path (str): Path to the PDF file
            conversion_attempts (list): List of previous conversion attempts and errors
            
        Returns:
            str: Basic markdown representation
        """
        logger.warning(f"Using fallback conversion for {pdf_path}")
        
        try:
            # Create a minimal markdown representation
            filename = os.path.basename(pdf_path)
            base_name, _ = os.path.splitext(filename)
            
            # Check file size for info
            file_size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
            file_size_kb = file_size / 1024
            
            # Check file type more specifically
            file_type = "Unknown"
            try:
                with open(pdf_path, 'rb') as f:
                    header = f.read(1024)
                    if header.startswith(b'%PDF-'):
                        file_type = f"PDF (version {header[5:8].decode('utf-8', errors='ignore')})"
                    elif header.startswith(b'\xff\xd8'):
                        file_type = "JPEG image"
                    elif header.startswith(b'\x89PNG'):
                        file_type = "PNG image"
                    elif header.startswith(b'GIF'):
                        file_type = "GIF image"
            except Exception:
                pass
            
            # Current date/time
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Create more detailed error information
            error_details = ""
            if conversion_attempts:
                error_details = "\n\n## Conversion Attempts\n\n"
                for method, error in conversion_attempts:
                    error_details += f"### {method.title()} Conversion\n\n"
                    error_details += f"```\n{error.splitlines()[0]}\n```\n\n"
            
            # Return a more detailed fallback markdown structure
            markdown = f"""# {base_name}

## Document Information

- **Filename**: {filename}
- **File Size**: {file_size_kb:.1f} KB
- **File Type**: {file_type}
- **Conversion Timestamp**: {current_time}
- **Conversion Note**: This is a fallback conversion because OCR processing failed

## Content

*This document requires OCR processing with PyMuPDF or pytesseract.*
*Ensure these libraries are properly installed in your Python environment for text extraction.*

{error_details}
"""
            return markdown
            
        except Exception as e:
            logger.error(f"Even fallback conversion failed: {str(e)}")
            return f"# Error Processing {os.path.basename(pdf_path)}\n\nFailed to convert file: {str(e)}"

def convert_pdf_to_markdown(pdf_path, output_path=None, force_ocr=False, ocr_quality="high", use_gpt=False):
    """
    Convert a PDF file to markdown text using our comprehensive wrapper.
    
    Args:
        pdf_path (str): Path to the PDF file to convert
        output_path (str, optional): Path to save the markdown output
        force_ocr (bool): Whether to force OCR processing even for digital PDFs
        ocr_quality (str): OCR quality setting ("low", "medium", "high")
        use_gpt (bool): Whether to use GPT-based conversion (requires API key)
        
    Returns:
        str: Markdown text from the PDF or a fallback representation
    """
    try:
        # Using context manager pattern to ensure cleanup
        logger.info(f"Converting {pdf_path} to markdown (force_ocr={force_ocr}, quality={ocr_quality}, use_gpt={use_gpt})")
        wrapper = PDF2MarkdownWrapper()
        
        # Start timer to track performance
        start_time = time.time()
        
        # Perform the conversion
        markdown_result = wrapper.markdown(pdf_path, force_ocr=force_ocr, ocr_quality=ocr_quality, use_gpt=use_gpt)
        
        # Track performance
        end_time = time.time()
        conversion_time = end_time - start_time
        logger.info(f"Conversion completed in {conversion_time:.2f} seconds")
        
        # Add a metadata block at the end of the markdown with conversion info
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        conversion_info = f"""

---

*Document converted by JFK Files PDF2Markdown converter at {timestamp}*
*OCR: {"Enabled" if force_ocr else "Auto"}*
*Quality: {ocr_quality}*
*GPT-assisted: {"Yes" if use_gpt else "No"}*
*Conversion time: {conversion_time:.2f} seconds*

"""
        markdown_result += conversion_info
        
        # Save to output file if specified
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_result)
        
        return markdown_result
        
    except Exception as e:
        logger.error(f"Unhandled exception in convert_pdf_to_markdown: {e}")
        logger.error(traceback.format_exc())
        return f"# Error Converting {os.path.basename(pdf_path)}\n\nUnhandled exception: {str(e)}"

if __name__ == "__main__":
    # Test the wrapper if run directly
    import sys
    
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <pdf_file> [output_file] [--force-ocr] [--quality=low|medium|high] [--gpt]")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    if not os.path.exists(pdf_file):
        print(f"Error: File '{pdf_file}' not found")
        sys.exit(1)
    
    # Parse arguments
    output_file = None
    force_ocr = False
    quality = "high"
    use_gpt = False
    
    for arg in sys.argv[2:]:
        if arg == "--force-ocr":
            force_ocr = True
        elif arg == "--gpt":
            use_gpt = True
        elif arg.startswith("--quality="):
            quality = arg.split("=")[1]
            if quality not in ["low", "medium", "high"]:
                print(f"Invalid quality setting: {quality}. Using 'high' instead.")
                quality = "high"
        elif not arg.startswith("--"):
            output_file = arg
    
    try:
        # Convert the file
        md_text = convert_pdf_to_markdown(
            pdf_file, 
            output_path=output_file, 
            force_ocr=force_ocr, 
            ocr_quality=quality,
            use_gpt=use_gpt
        )
        
        if not output_file:
            print("\nConversion output:")
            # Print first 500 characters
            print(md_text[:500] + "..." if len(md_text) > 500 else md_text)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)