#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF utilities for JFK Files Scraper.

This module provides PDF-related functionality, including checking if a PDF is scanned,
extracting text with PyMuPDF, and handling different document formats.
"""

import os
import logging
import re
import tempfile
import shutil
from pathlib import Path

# Initialize logger
logger = logging.getLogger("jfk_scraper.pdf_utils")

# Check for available PDF libraries
HAS_PYMUPDF = False
HAS_PDF2MD = False

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
    logger.info("PyMuPDF (fitz) is available")
except ImportError:
    logger.warning("PyMuPDF (fitz) not available. Some PDF features will be limited.")

try:
    # Check for our custom pdf2md module
    from src.utils.pdf2md import page_image2md, get_page_images
    HAS_PDF2MD = True
    logger.info("pdf2md module is available")
except ImportError:
    logger.warning("pdf2md module not available. PDF to Markdown conversion will use fallbacks.")


def is_scanned_pdf(pdf_path):
    """
    Determine if a PDF likely contains scanned content that would benefit from OCR.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        bool: True if the PDF appears to be scanned, False if it's digital
    """
    if not HAS_PYMUPDF:
        logger.warning("PyMuPDF not available for scan detection, assuming document needs OCR")
        return True
        
    try:
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
        logger.warning(f"Error in scan detection, assuming document needs OCR: {e}")
        return True


def extract_text_with_pymupdf(pdf_path):
    """
    Extract text from PDF using PyMuPDF with enhanced formatting.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text
    """
    if not HAS_PYMUPDF:
        logger.error("PyMuPDF not available for text extraction")
        return f"Error: PyMuPDF not available for text extraction from {pdf_path}"
    
    try:
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
        
        # Join all text parts
        return "\n\n".join(full_text)
        
    except Exception as e:
        logger.error(f"Error extracting text with PyMuPDF: {e}")
        return f"Error extracting PDF text: {str(e)}"


def detect_document_format(pdf_path, include_details=False):
    """
    Detect the format of a PDF document to determine optimal processing.
    
    Args:
        pdf_path (str): Path to the PDF file
        include_details (bool): Whether to return detailed format information
        
    Returns:
        dict or bool: If include_details is True, returns a dict with format details.
                     Otherwise, returns True if the document needs OCR, False if not.
    """
    if not HAS_PYMUPDF:
        # Without PyMuPDF, we can't detect document formats properly
        if include_details:
            return {
                "needs_ocr": True,
                "is_rare_format": False,
                "warnings": ["PyMuPDF not available for format detection"]
            }
        return True
    
    try:
        # Initialize result structure
        result = {
            "needs_ocr": False,
            "is_rare_format": False,
            "warnings": [],
            "rare_format_type": None,
            "processing_strategy": "standard"
        }
        
        # Basic file size check
        file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        result["file_size_mb"] = file_size_mb
        
        # Check for unusually large or small files
        if file_size_mb > 50:
            result["warnings"].append(f"Unusually large file ({file_size_mb:.1f} MB)")
            
        if file_size_mb < 0.01 and file_size_mb > 0:
            result["warnings"].append(f"Unusually small file ({file_size_mb:.2f} MB)")
            result["is_rare_format"] = True
            result["rare_format_type"] = "potentially_empty"
            result["processing_strategy"] = "cautious"
        
        # Open the PDF for analysis
        doc = fitz.open(pdf_path)
        
        # Check for encryption
        if doc.is_encrypted:
            result["is_rare_format"] = True
            result["rare_format_type"] = "encrypted"
            result["warnings"].append("Document is encrypted")
            result["processing_strategy"] = "decrypt_first"
            
            # Try to decrypt with empty password
            try:
                success = doc.authenticate("")
                if success:
                    result["warnings"].append("Document decrypted with empty password")
                    # If decryption was successful, update the encryption status
                    result["is_rare_format"] = False
                    result["processing_strategy"] = "standard"
                else:
                    result["needs_ocr"] = True
            except:
                result["needs_ocr"] = True
        
        # Check document characteristics
        page_count = len(doc)
        result["page_count"] = page_count
        
        if page_count == 0:
            result["is_rare_format"] = True
            result["rare_format_type"] = "empty_document"
            result["warnings"].append("Document contains no pages")
            result["processing_strategy"] = "cautious"
            result["needs_ocr"] = False  # No point in OCR for empty document
        
        # Check for unusual characteristics based on a sample of pages
        pages_to_check = min(5, page_count)
        text_content = 0
        image_content = 0
        unusual_fonts = 0
        unusual_rotations = 0
        
        for page_idx in range(pages_to_check):
            if page_idx >= page_count:
                break
                
            page = doc[page_idx]
            
            # Check for text content
            text = page.get_text()
            if len(text.strip()) > 100:
                text_content += 1
                
            # Check for images
            images = page.get_images()
            if len(images) > 0:
                image_content += 1
            
            # Check for unusual page characteristics
            if page.rotation != 0:
                unusual_rotations += 1
            
            # Check for unusual fonts (if possible)
            try:
                fonts = page.get_fonts()
                for font in fonts:
                    font_name = font[3] if len(font) > 3 else ""
                    if "symbol" in font_name.lower() or "zapf" in font_name.lower():
                        unusual_fonts += 1
            except:
                pass
        
        # Determine if document likely needs OCR
        if text_content == 0 and image_content > 0:
            result["needs_ocr"] = True
            result["warnings"].append("Document appears to be image-only (scanned)")
            
        elif text_content < image_content:
            result["needs_ocr"] = True
            result["warnings"].append("Document appears to contain more images than text")
            
        # Check for rare formats that may need special handling
        if unusual_rotations > 0:
            result["warnings"].append(f"Document contains {unusual_rotations} unusually rotated pages")
            if unusual_rotations > pages_to_check / 2:
                result["is_rare_format"] = True
                result["rare_format_type"] = "unusual_rotation"
                result["processing_strategy"] = "normalize_pages"
        
        if unusual_fonts > 0:
            result["warnings"].append(f"Document contains {unusual_fonts} unusual font references")
            if unusual_fonts > 3:
                result["is_rare_format"] = True
                result["rare_format_type"] = "unusual_fonts"
                result["processing_strategy"] = "careful_extraction"
        
        # Close the document
        doc.close()
        
        # Return appropriate result
        if include_details:
            return result
        return result["needs_ocr"]
        
    except Exception as e:
        logger.warning(f"Error in document format detection: {e}")
        if include_details:
            return {
                "needs_ocr": True,
                "is_rare_format": False,
                "warnings": [f"Error in format detection: {str(e)}"],
                "processing_strategy": "cautious"
            }
        return True


def repair_document(pdf_path):
    """
    Attempt to repair a problematic PDF document.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str or None: Path to repaired PDF if successful, None if repair failed
    """
    if not HAS_PYMUPDF:
        logger.warning("PyMuPDF not available for document repair")
        return None
    
    try:
        # Create a temporary directory for the repaired file
        temp_dir = tempfile.mkdtemp(prefix="jfk_repair_")
        base_name = os.path.basename(pdf_path)
        repaired_path = os.path.join(temp_dir, f"repaired_{base_name}")
        
        logger.info(f"Attempting to repair {pdf_path}")
        
        # Try opening and resaving with PyMuPDF
        doc = fitz.open(pdf_path)
        
        # If encrypted, try to decrypt
        if doc.is_encrypted:
            try:
                # Try empty password first
                success = doc.authenticate("")
                if not success:
                    logger.warning("Could not decrypt document with empty password")
                    doc.close()
                    return None
            except:
                logger.warning("Error decrypting document")
                doc.close()
                return None
        
        # Save to new file with clean option
        doc.save(repaired_path, clean=True, garbage=4, deflate=True)
        doc.close()
        
        # Verify the repaired file is valid
        try:
            check_doc = fitz.open(repaired_path)
            if len(check_doc) > 0:
                logger.info(f"Successfully repaired document: {repaired_path}")
                check_doc.close()
                return repaired_path
            check_doc.close()
        except:
            logger.warning("Repaired document validation failed")
            return None
            
        # Clean up if repair failed
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
            
        return None
        
    except Exception as e:
        logger.error(f"Error repairing document: {e}")
        return None
