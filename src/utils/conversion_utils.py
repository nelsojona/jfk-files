#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Conversion utilities for JFK Files Scraper.

This module provides functionality for converting between different file formats,
including PDF to Markdown and Markdown to JSON.
"""

import os
import re
import json
import logging
import time
import datetime
from pathlib import Path

# Import custom exceptions and utilities
from src.utils.logging_utils import (
    ConversionError, track_error, update_performance_metrics
)
from src.utils.pdf_utils import (
    is_scanned_pdf, repair_document, detect_document_format,
    HAS_PYMUPDF, HAS_PDF2MD
)

# Initialize logger
logger = logging.getLogger("jfk_scraper.conversion")


def post_process_markdown(markdown_text, is_ocr=False):
    """
    Post-processes markdown text to improve quality, especially for OCR output.
    
    Args:
        markdown_text (str): Original markdown text
        is_ocr (bool): Whether this text came from OCR processing
        
    Returns:
        str: Improved markdown text
    """
    # Skip empty content
    if not markdown_text or len(markdown_text.strip()) == 0:
        return markdown_text
    
    # Common fixes for all markdown content
    processed_text = markdown_text
    
    # Fix common OCR issues
    if is_ocr:
        # Fix multiple spaces (common OCR issue)
        processed_text = re.sub(r' {2,}', ' ', processed_text)
        
        # Fix common OCR character confusion (e.g., 0/O, l/I, etc.)
        ocr_fixes = {
            # These are common OCR mistakes - add more based on observations
            r'\bl\b': '1',  # lowercase l to 1
            r'\bO\b': '0',  # capital O to 0 when it's a single digit
            r'[­]': '',     # Remove soft hyphens
        }
        
        for pattern, replacement in ocr_fixes.items():
            processed_text = re.sub(pattern, replacement, processed_text)
    
    # Ensure proper markdown structure
    lines = processed_text.split('\n')
    structured_lines = []
    in_list = False
    prev_was_header = False
    
    for line in lines:
        # Ensure blank line after headers
        if re.match(r'^#+\s', line):
            if not prev_was_header and structured_lines and structured_lines[-1] != '':
                structured_lines.append('')
            structured_lines.append(line)
            prev_was_header = True
            in_list = False
        
        # Handle list items and proper spacing
        elif re.match(r'^\s*[*-]\s', line):
            structured_lines.append(line)
            in_list = True
            prev_was_header = False
        
        # Regular lines
        else:
            if prev_was_header and line.strip() != '':
                structured_lines.append(line)
            elif in_list and line.strip() == '':
                structured_lines.append(line)
                in_list = False
            elif not in_list and line.strip() != '':
                if structured_lines and structured_lines[-1] != '' and not prev_was_header:
                    # Continuation of paragraph
                    structured_lines.append(line)
                else:
                    # Start of new paragraph
                    if structured_lines and structured_lines[-1] != '':
                        structured_lines.append('')
                    structured_lines.append(line)
            else:
                structured_lines.append(line)
            
            prev_was_header = False
    
    return '\n'.join(structured_lines)


def validate_markdown_quality(markdown_text):
    """
    Validates the quality of markdown text, particularly for checking OCR output.
    
    Args:
        markdown_text (str): Markdown text to validate
        
    Returns:
        dict: Quality assessment with score and issues
    """
    issues = []
    scores = []
    
    # Skip empty content
    if not markdown_text or len(markdown_text.strip()) == 0:
        return {"score": 0.0, "issues": ["Empty content"]}
    
    # Check for large sections of garbled text
    garbled_pattern = r'[^\w\s\.\,\?\!\:\;\-\'\"\(\)\[\]\{\}\@\#\$\%\&\*\+\=\/\\|<>~`]+'
    garbled_matches = re.findall(garbled_pattern, markdown_text)
    garbled_ratio = sum(len(m) for m in garbled_matches) / len(markdown_text) if len(markdown_text) > 0 else 0
    
    if garbled_ratio > 0.1:
        issues.append(f"High ratio of garbled characters ({garbled_ratio:.2f})")
        scores.append(0.3)
    else:
        scores.append(0.8)
    
    # Check for balanced structure
    headers = re.findall(r'^#+\s', markdown_text, re.MULTILINE)
    if len(headers) < 2 and len(markdown_text) > 500:
        issues.append("Lack of document structure")
        scores.append(0.5)
    else:
        scores.append(0.9)
    
    # Check for excessive line breaks
    lines = markdown_text.split('\n')
    empty_line_ratio = sum(1 for line in lines if line.strip() == '') / len(lines) if lines else 0
    if empty_line_ratio > 0.4:
        issues.append(f"Excessive empty lines ({empty_line_ratio:.2f} ratio)")
        scores.append(0.6)
    else:
        scores.append(0.9)
    
    # Calculate final score
    avg_score = sum(scores) / len(scores) if scores else 0
    
    return {
        "score": avg_score,
        "issues": issues
    }


def pdf_to_markdown(pdf_path, output_dir="markdown", force_ocr=False, ocr_quality="high"):
    """
    Converts a PDF document to Markdown format using pdf2md_wrapper with enhanced OCR support.
    
    Key improvements:
    - Automatic detection of scanned PDFs requiring OCR
    - Enhanced OCR quality with post-processing
    - Better handling of rare document formats
    - Quality validation of OCR results

    Args:
        pdf_path (str): The path to the PDF file.
        output_dir (str): The directory to save the Markdown to.
        force_ocr (bool): Whether to force OCR processing even for digital PDFs.
        ocr_quality (str): OCR quality setting ("low", "medium", "high").

    Returns:
        tuple: (markdown_path, markdown_content) or (None, None) if conversion failed.
    """
    # Keep the original return value for test compatibility
    return convert_to_markdown_or_json(pdf_path, output_dir, "markdown", force_ocr, ocr_quality)


def markdown_to_json(markdown_path, output_dir="json"):
    """
    Converts a Markdown file to JSON format.

    Args:
        markdown_path (str): The path to the Markdown file.
        output_dir (str): The directory to save the JSON to.
        
    Returns:
        tuple: (json_path, json_content) or (None, None) if conversion failed.
    """
    # Keep the original return value for test compatibility
    return convert_to_markdown_or_json(markdown_path, output_dir, "json")


def convert_to_markdown_or_json(input_path, output_dir, output_format, force_ocr=False, ocr_quality="high"):
    """
    Helper function to convert a PDF to Markdown or Markdown to JSON.

    Args:
        input_path (str): Path to the input file (PDF or Markdown).
        output_dir (str): Directory to save the output file.
        output_format (str): Either "markdown" or "json".
        force_ocr (bool): Only relevant for PDF to Markdown; forces OCR.
        ocr_quality (str): OCR quality setting ("low", "medium", "high").

    Returns:
        tuple: (output_path, output_content) or (None, None) if conversion failed.
    """
    conversion_start = time.time()

    try:
        input_filename = os.path.basename(input_path)
        base_filename = os.path.splitext(input_filename)[0]
        
        if output_format == "markdown":
            output_filename = base_filename + ".md"
        elif output_format == "json":
            output_filename = base_filename + ".json"
        else:
            raise ValueError("Invalid output_format. Must be 'markdown' or 'json'.")
        
        output_path = os.path.join(output_dir, output_filename)

        # Check if output file already exists
        if os.path.exists(output_path):
            logger.info(f"{output_format.capitalize()} file already exists: {output_path}")
            with open(output_path, 'r', encoding='utf-8') as f:
                output_content = json.load(f) if output_format == "json" else f.read()
            conversion_time = time.time() - conversion_start
            update_performance_metrics(conversion_times=conversion_time)
            return output_path, output_content

        # Handle PDF to Markdown conversion
        if output_format == "markdown":
            output_content = _convert_pdf_to_markdown(input_path, force_ocr, ocr_quality)
        # Handle Markdown to JSON conversion
        else:
            output_content = _convert_markdown_to_json(input_path, base_filename)

        # Write output to file
        temp_path = f"{output_path}.temp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            if output_format == "markdown":
                f.write(output_content)
            else:  # json
                json.dump(output_content, f, indent=2, ensure_ascii=False)
        os.rename(temp_path, output_path)

        conversion_time = time.time() - conversion_start
        update_performance_metrics(conversion_times=conversion_time)
        logger.info(f"Successfully converted to {output_path} in {conversion_time:.2f} seconds")
        return output_path, output_content

    except ImportError as e:
        error_message = f"Import error during {output_format} conversion: {e}"
        logger.error(error_message)
        track_error(f"{'pdf_to_markdown' if output_format == 'markdown' else 'markdown_to_json'}", 
                    ConversionError(error_message), input_path)
        return None, None
    except Exception as e:
        error_message = f"Error converting {input_path} to {output_format}: {e}"
        logger.error(error_message)
        track_error(f"{'pdf_to_markdown' if output_format == 'markdown' else 'markdown_to_json'}", 
                    ConversionError(error_message), input_path)
        return None, None


def _convert_pdf_to_markdown(pdf_path, force_ocr=False, ocr_quality="high"):
    """
    Internal function to convert PDF to Markdown with enhanced handling of rare formats.
    
    Args:
        pdf_path (str): Path to the PDF file
        force_ocr (bool): Whether to force OCR processing
        ocr_quality (str): OCR quality setting ("low", "medium", "high")
        
    Returns:
        str: Markdown content
    """
    # Get detailed document format information
    doc_format = detect_document_format(pdf_path, include_details=True)
    needs_ocr = force_ocr or doc_format["needs_ocr"]
    
    # Handle rare format documents
    if doc_format["is_rare_format"]:
        logger.warning(
            f"Rare format detected for {pdf_path}: {doc_format['rare_format_type']}. "
            f"Warnings: {', '.join(doc_format['warnings'])}"
        )
        
        # Apply appropriate processing strategy based on format type
        processing_strategy = doc_format.get("processing_strategy", "standard")
        
        if processing_strategy in ["deep_repair", "cautious"]:
            # Try to repair the document
            logger.info(f"Attempting document repair using strategy: {processing_strategy}")
            repaired_path = repair_document(pdf_path)
            if repaired_path:
                pdf_path = repaired_path
                logger.info(f"Using repaired document: {pdf_path}")
            else:
                logger.warning("Document repair failed, proceeding with original document")
                # Force OCR if repair failed
                needs_ocr = True
                
        elif processing_strategy == "decrypt_first":
            # Handle encrypted documents
            logger.info("Attempting to decrypt document")
            # First try repair (which attempts decryption)
            repaired_path = repair_document(pdf_path)
            if repaired_path:
                pdf_path = repaired_path
                logger.info(f"Successfully decrypted document: {pdf_path}")
            else:
                logger.warning("Decryption failed, proceeding with OCR")
                needs_ocr = True
                
        elif processing_strategy in ["ocr_only", "selective_ocr"]:
            # Force OCR for these strategies
            logger.info(f"Using {processing_strategy} strategy with OCR")
            needs_ocr = True
            
        elif processing_strategy == "normalize_pages":
            # Handle unusual page sizes
            logger.info("Attempting to normalize page sizes")
            repaired_path = repair_document(pdf_path)
            if repaired_path:
                pdf_path = repaired_path
                logger.info(f"Page normalization complete: {pdf_path}")
            
        elif processing_strategy == "careful_extraction":
            # Special handling for unusual fonts or structures
            logger.info("Using careful extraction for unusual document structure")
            # Try multiple extraction methods and use the best one
            needs_ocr = True  # Default to OCR for safety
    
    # Get the document title for use in all methods
    doc_title = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # Use our pdf2md_wrapper for conversion with quality settings
    try:
        # Import our enhanced PDF to Markdown wrapper
        from src.utils.pdf2md_wrapper import convert_pdf_to_markdown
        
        logger.info(f"Converting {pdf_path} to markdown with pdf2md_wrapper (OCR: {needs_ocr}, Quality: {ocr_quality})")
        
        # Use the wrapper with all our enhanced options
        markdown_content = convert_pdf_to_markdown(pdf_path, force_ocr=needs_ocr, ocr_quality=ocr_quality)
        
        # Validate the quality of the markdown output for monitoring
        markdown_quality = validate_markdown_quality(markdown_content)
        logger.info(f"Markdown quality score: {markdown_quality['score']:.2f}")
        
        # Report any quality issues but continue with the result
        if markdown_quality["score"] < 0.5:
            issues = ', '.join(markdown_quality['issues']) if markdown_quality['issues'] else "unknown issues"
            logger.warning(f"Poor quality markdown detected: {issues}")
            
    except ImportError as e:
        logger.error(f"Could not import pdf2md_wrapper: {e}")
        # Fall back to PyMuPDF approach
        try:
            if HAS_PYMUPDF:
                logger.info(f"Falling back to PyMuPDF processing")
                from src.utils.pdf_utils import extract_text_with_pymupdf
                
                # Basic conversion attempt
                extracted_text = extract_text_with_pymupdf(pdf_path)
                markdown_content = post_process_markdown(extracted_text, is_ocr=needs_ocr)
                markdown_content = f"# {doc_title}\n\n{markdown_content}"
            else:
                # Ultimate fallback when nothing is available
                markdown_content = f"# {doc_title}\n\n## Error\n\nNo PDF extraction libraries available. Please install PyMuPDF or configure pdf2md_wrapper."
        except Exception as e:
            logger.error(f"All extraction methods failed: {e}")
            markdown_content = f"# {doc_title}\n\n## Extraction Error\n\nDocument could not be processed: {str(e)}"
    except Exception as e:
        logger.error(f"Error using pdf2md_wrapper: {e}")
        # Create a minimal fallback
        markdown_content = f"# {doc_title}\n\n## Error\n\nFailed to convert PDF: {str(e)}"
    
    # Make sure we return valid markdown regardless of what happened
    if not markdown_content or len(markdown_content.strip()) < 10:
        doc_title = os.path.splitext(os.path.basename(pdf_path))[0]
        markdown_content = f"# {doc_title}\n\n## Error\n\nFailed to extract content from document."
    
    return markdown_content


def transform_pandoc_json_to_standard_format(pandoc_json, doc_id):
    """
    Transform Pandoc JSON format to a standardized JSON format.
    
    Args:
        pandoc_json (dict): JSON output from Pandoc
        doc_id (str): Document ID
        
    Returns:
        dict: Standardized JSON structure
    """
    transformed = {
        "document_id": doc_id,
        "total_pages": 0,
        "pages": [],
        "metadata": {
            "conversion_method": "pandoc",
            "conversion_timestamp": datetime.datetime.now().isoformat()
        }
    }
    
    # Extract pages from Pandoc JSON
    current_page = {"title": "Page 1", "content": ""}
    page_count = 1
    
    # Process based on Pandoc JSON structure
    if "blocks" in pandoc_json:
        for block in pandoc_json["blocks"]:
            if block["t"] == "Header" and block["c"][0] == 1:  # Level 1 header
                # Extract header text
                header_text = ''.join([span["c"] for span in block["c"][2] if span["t"] == "Str"])
                
                # If header contains "Page" or a page number, start a new page
                if "Page" in header_text or any(char.isdigit() for char in header_text):
                    if current_page["content"]:  # Save previous page if it has content
                        transformed["pages"].append(current_page.copy())
                    
                    page_count += 1
                    current_page = {"title": header_text, "content": ""}
                else:
                    # Otherwise, just add the header to the current page content
                    current_page["content"] += f"# {header_text}\n\n"
            elif block["t"] == "Para":
                # Extract paragraph text
                para_text = ''
                for inline in block["c"]:
                    if inline["t"] == "Str":
                        para_text += inline["c"]
                    elif inline["t"] == "Space":
                        para_text += ' '
                
                current_page["content"] += para_text + "\n\n"
    
    # Add the last page
    if current_page["content"]:
        transformed["pages"].append(current_page)
    
    # Set total pages
    transformed["total_pages"] = len(transformed["pages"])
    
    return transformed


def parse_markdown_with_python(markdown_text, doc_id):
    """
    Parse Markdown content using Python (no external dependencies).
    
    Args:
        markdown_text (str): Markdown content
        doc_id (str): Document ID
        
    Returns:
        dict: JSON structure with parsed content
    """
    result = {
        "document_id": doc_id,
        "total_pages": 0,
        "pages": [],
        "metadata": {
            "conversion_method": "python",
            "conversion_timestamp": datetime.datetime.now().isoformat()
        }
    }
    
    # Split by lines for processing
    lines = markdown_text.split('\n')
    
    # Process headers to identify pages
    current_page = {"title": "Page 1", "content": ""}
    page_marker_pattern = re.compile(r'^#{1,2}\s+(?:Page|PAGE)\s+(\d+)', re.IGNORECASE)
    
    for line in lines:
        # Check if this line starts a new page
        page_match = page_marker_pattern.match(line)
        
        if page_match:
            # Save the current page if it has content
            if current_page["content"].strip():
                result["pages"].append(current_page.copy())
            
            # Start a new page
            page_num = page_match.group(1)
            current_page = {"title": f"Page {page_num}", "content": ""}
        else:
            # Add this line to the current page content
            current_page["content"] += line + "\n"
    
    # Add the last page if it has content
    if current_page["content"].strip():
        result["pages"].append(current_page)
    
    # If no pages with page markers were found, try an alternative approach
    if len(result["pages"]) <= 1:
        # Reset and try splitting by level 2 headers
        result["pages"] = []
        current_content = ""
        current_title = "Document Start"
        
        for line in lines:
            if line.startswith('## '):
                # Save previous section
                if current_content.strip():
                    result["pages"].append({
                        "title": current_title,
                        "content": current_content
                    })
                
                # Start new section
                current_title = line[3:].strip()
                current_content = ""
            else:
                current_content += line + "\n"
        
        # Add the last section
        if current_content.strip():
            result["pages"].append({
                "title": current_title,
                "content": current_content
            })
    
    # Update total pages
    result["total_pages"] = len(result["pages"])
    
    # If still no clear pages found, create a single page with all content
    if result["total_pages"] == 0:
        result["pages"] = [{
            "title": "Full Document",
            "content": markdown_text
        }]
        result["total_pages"] = 1
    
    return result


def _convert_markdown_to_json(markdown_path, title=None):
    """
    Internal function to convert Markdown to JSON with enhanced error handling
    and improved document structure detection.
    
    Args:
        markdown_path (str): Path to the Markdown file
        title (str, optional): Document title to use. If None, uses the filename.
        
    Returns:
        dict: JSON content
    """
    try:
        with open(markdown_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        if title is None:
            title = os.path.splitext(os.path.basename(markdown_path))[0]
            
        # Try to extract document ID from title for JFK files
        doc_id = title
        
        # Extract standard JFK document ID patterns
        doc_id_match = re.match(r'^(\d+-\d+-\d+)', title)
        if doc_id_match:
            doc_id = doc_id_match.group(1)
        elif "docid" in title.lower():
            doc_id_match = re.search(r'docid[-\s]?(\d+)', title.lower())
            if doc_id_match:
                doc_id = f"docid-{doc_id_match.group(1)}"
        
        # Handle empty or invalid content
        if not markdown_content or len(markdown_content.strip()) == 0:
            logger.warning(f"Empty markdown file: {markdown_path}")
            return {
                "docId": doc_id,
                "title": title,
                "metadata": {
                    "source": "National Archives",
                    "collection": "JFK Files",
                    "format": "PDF to Markdown to JSON",
                    "warning": "Empty source file",
                    "conversion_timestamp": datetime.datetime.now().isoformat()
                },
                "sections": [],
                "fullText": ""
            }
        
        # Check for our pdf2md_wrapper
        have_pdf2md = False
        try:
            from src.utils.pdf2md_wrapper import PDF2MarkdownWrapper
            have_pdf2md = True
            logger.info("Using PDF2MarkdownWrapper for enhanced section detection")
        except ImportError:
            logger.info("PDF2MarkdownWrapper not available, using basic section extraction")
        
        # Process markdown into sections with enhanced detection
        sections = []
        current_section = {"title": "", "content": []}
        lines = markdown_content.split('\n')
        
        # First-pass extraction with improved section detection
        page_pattern = re.compile(r'^#+\s+Page\s+(\d+)', re.IGNORECASE)
        in_content_block = False
        code_block_markers = 0
        
        for line in lines:
            # Handle code blocks specially
            if line.strip().startswith('```'):
                code_block_markers += 1
                in_content_block = (code_block_markers % 2 == 1)  # Toggle state for each marker
                if current_section["title"]:  # Only add to current section if we have one
                    current_section["content"].append(line)
                continue
                
            # Skip header detection inside code blocks
            if in_content_block:
                if current_section["title"]:
                    current_section["content"].append(line)
                continue
            
            # Try to detect headers
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_match:
                # Save previous section if it exists
                if current_section["title"] and current_section["content"]:
                    # Join content, ensuring proper handling of lists and paragraphs
                    sections.append(current_section.copy())
                
                level = len(header_match.group(1))
                section_title = header_match.group(2).strip()
                
                # Special handling for page markers
                page_match = page_pattern.match(line)
                if page_match:
                    page_num = page_match.group(1)
                    section_title = f"Page {page_num}"
                
                current_section = {
                    "title": section_title,
                    "level": level,
                    "content": []
                }
            elif line.strip():  # Non-empty line
                if current_section["title"]:  # If we're in a section
                    current_section["content"].append(line)
                elif not sections:  # If no sections yet and this is text, create an implicit section
                    current_section = {
                        "title": "Document Content",
                        "level": 1,
                        "content": [line]
                    }
            else:  # Empty line
                if current_section["title"] and current_section["content"]:  # Only add if we have content
                    current_section["content"].append(line)  # Preserve paragraph breaks
        
        # Don't forget the last section
        if current_section["title"] and current_section["content"]:
            sections.append(current_section)
            
        # Handle case where no proper sections were found
        if not sections:
            logger.warning(f"No proper sections found in {markdown_path}, using fallback extraction")
            # Create a fallback section with all content
            sections = [{
                "title": "Document Content",
                "level": 1,
                "content": markdown_content.split('\n')
            }]
        
        # Try to extract date and classification information
        creation_date = None
        classification = None
        agency = None
        
        # Look for date patterns in the first few sections
        date_patterns = [
            r'(?:Date|Dated):\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
            r'(\d{1,2}/\d{1,2}/\d{2,4})'
        ]
        
        # Look for classification patterns
        classification_patterns = [
            r'(?:Classification|Classified):\s*(\w+\s+\w+|\w+)',
            r'(CONFIDENTIAL|SECRET|TOP SECRET|UNCLASSIFIED)'
        ]
        
        # Look for agency patterns
        agency_patterns = [
            r'(?:Agency|From|Originator):\s*([\w\s]+)',
            r'(CIA|FBI|HSCA|NSA|DOS|DOD)'
        ]
        
        # Check the first few sections for metadata
        search_text = "\n".join([section["title"] + "\n" + "\n".join(section["content"]) 
                                for section in sections[:min(3, len(sections))]])
        
        # Extract date
        for pattern in date_patterns:
            date_match = re.search(pattern, search_text, re.IGNORECASE)
            if date_match:
                creation_date = date_match.group(1)
                break
                
        # Extract classification
        for pattern in classification_patterns:
            class_match = re.search(pattern, search_text, re.IGNORECASE)
            if class_match:
                classification = class_match.group(1).upper()
                break
                
        # Extract agency
        for pattern in agency_patterns:
            agency_match = re.search(pattern, search_text, re.IGNORECASE)
            if agency_match:
                agency = agency_match.group(1).strip()
                break
        
        # Create JSON structure with enhanced metadata
        json_content = {
            "docId": doc_id,
            "title": title,
            "metadata": {
                "source": "National Archives",
                "collection": "JFK Files",
                "format": "PDF to Markdown to JSON",
                "conversion_timestamp": datetime.datetime.now().isoformat(),
                "pages": len([s for s in sections if "Page" in s["title"]])
            },
            "sections": [],
            "fullText": markdown_content
        }
        
        # Add extracted metadata if available
        if creation_date:
            json_content["metadata"]["date"] = creation_date
        if classification:
            json_content["metadata"]["classification"] = classification
        if agency:
            json_content["metadata"]["agency"] = agency
            
        # Add sections to JSON with improved content formatting
        for section in sections:
            # Process content to fix formatting
            content_text = "\n".join(section["content"])
            
            # Fix common formatting issues
            content_text = re.sub(r'\n{3,}', '\n\n', content_text)  # Normalize excessive newlines
            
            json_section = {
                "title": section["title"],
                "level": section.get("level", 1),
                "content": content_text
            }
            json_content["sections"].append(json_section)
        
        return json_content
        
    except Exception as e:
        logger.error(f"Error converting markdown to JSON: {e}")
        logger.error(traceback.format_exc())
        
        # Return a minimal valid JSON with error information
        return {
            "docId": title if title else os.path.splitext(os.path.basename(markdown_path))[0],
            "title": title if title else os.path.splitext(os.path.basename(markdown_path))[0],
            "metadata": {
                "source": "National Archives",
                "collection": "JFK Files",
                "format": "PDF to Markdown to JSON",
                "error": f"Conversion error: {str(e)}",
                "conversion_timestamp": datetime.datetime.now().isoformat()
            },
            "sections": [],
            "fullText": ""
        }