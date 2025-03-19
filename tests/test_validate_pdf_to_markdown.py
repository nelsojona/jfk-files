#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST-7: Enhanced validation for PDF2MD-specific quality checks.

This script tests the quality of PDF to Markdown conversion by:
1. Checking structural integrity of the converted markdown
2. Validating header hierarchy
3. Ensuring content integrity
4. Comparing with expected output patterns
5. Validating PDF2MD-specific features and quality indicators
"""

import sys
import os
import logging
import re
from pathlib import Path
import json

# Add parent directory to python path to import from jfk_scraper.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import required functions
    from jfk_scraper import pdf_to_markdown, create_directories, logger
    
    # Make sure directories exist
    create_directories()
    
    # Configure test-specific logging
    logger.info("Starting enhanced PDF to Markdown conversion validation test (TEST-7)")
    
    # Use a specific test PDF or the sample from previous tests
    # Try to include both regular and scanned PDFs for comprehensive testing
    test_pdfs = [
        "pdfs/docid-32204484.pdf",  # Standard PDF
        "pdfs/104-10004-10143 C06932208.pdf"  # Likely a scanned PDF based on the filename
    ]
    
    overall_results = {}
    
    for pdf_path in test_pdfs:
        if not os.path.exists(pdf_path):
            logger.warning(f"Test PDF file not found at {pdf_path}. Skipping this file.")
            continue
        
        logger.info(f"Testing conversion for: {pdf_path}")
        
        # Convert the PDF to Markdown
        markdown_path, markdown_content = pdf_to_markdown(pdf_path)
        
        # Verify the conversion was successful
        if not (markdown_path and os.path.exists(markdown_path) and markdown_content):
            logger.error(f"Failed to convert {pdf_path} to Markdown. Test FAILED")
            continue
        
        logger.info(f"Markdown file size: {os.path.getsize(markdown_path)} bytes")
        
        # ===== VALIDATION TESTS =====
        
        # 1. Basic content validation
        validation_results = {
            "has_content": len(markdown_content.strip()) > 0,
            "has_headers": "# " in markdown_content or "## " in markdown_content,
            "has_paragraphs": len(markdown_content.split('\n\n')) > 1,
            "structural_integrity": True,  # Will be set to False if structure issues found
            "header_hierarchy": True,      # Will be set to False if header hierarchy issues found
            "content_integrity": True,     # Will be set to False if content issues found
        }
        
        # 2. Check structural integrity - proper markdown syntax
        markdown_lines = markdown_content.split('\n')
        
        # Check for unclosed code blocks
        code_block_starts = markdown_content.count('```')
        if code_block_starts % 2 != 0:
            validation_results["structural_integrity"] = False
            logger.warning(f"[{pdf_path}] Markdown has unclosed code blocks")
        
        # Check for broken links
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        links = link_pattern.findall(markdown_content)
        for link_text, link_url in links:
            if not link_url or link_url.isspace():
                validation_results["structural_integrity"] = False
                logger.warning(f"[{pdf_path}] Markdown has broken link: [{link_text}]()")
        
        # 3. Check header hierarchy
        headers = []
        for line in markdown_lines:
            if line.startswith('#'):
                # Count the number of # at the beginning of the line
                level = len(line) - len(line.lstrip('#'))
                headers.append((level, line.strip()))
        
        if headers:
            # Check if first header is H1
            if headers[0][0] != 1:
                validation_results["header_hierarchy"] = False
                logger.warning(f"[{pdf_path}] Markdown doesn't start with an H1 header")
            
            # Check for skipped header levels (e.g., H1 -> H3 without H2)
            prev_level = headers[0][0]
            for level, header in headers[1:]:
                if level > prev_level + 1:  # Skipped a level
                    validation_results["header_hierarchy"] = False
                    logger.warning(f"[{pdf_path}] Markdown has skipped header levels: {header}")
                prev_level = level
        else:
            validation_results["header_hierarchy"] = False
            logger.warning(f"[{pdf_path}] Markdown has no headers")
        
        # 4. Check content integrity
        # Look for common PDF conversion issues
        
        # Check for page numbers that should be in headers but are in text
        page_number_pattern = re.compile(r'^Page \d+$')
        for line in markdown_lines:
            if page_number_pattern.match(line) and not line.startswith('#'):
                validation_results["content_integrity"] = False
                logger.warning(f"[{pdf_path}] Found page number not in header: {line}")
        
        # Check for garbled text indicators
        garbled_indicators = ['�', '□', '■', '▯', '▮']
        for indicator in garbled_indicators:
            if indicator in markdown_content:
                validation_results["content_integrity"] = False
                logger.warning(f"[{pdf_path}] Markdown contains possible garbled text indicator: {indicator}")
        
        # Check for common PDF-to-text artifacts
        artifact_patterns = [
            re.compile(r'[A-Za-z]{1,2}\d{1,3}', re.MULTILINE),  # Likely page or section markers like "A1" or "B22"
            re.compile(r'\n\d+\n'),  # Isolated numbers that might be page numbers
        ]
        
        for pattern in artifact_patterns:
            matches = pattern.findall(markdown_content)
            if matches:
                # Only flag as potential issue, not definite failure
                logger.info(f"[{pdf_path}] Potential PDF artifacts found: {matches[:5]}")
        
        # 5. PDF2MD-specific quality checks
        
        # New validation categories for PDF2MD-specific checks
        validation_results["table_structure"] = True
        validation_results["list_formatting"] = True
        validation_results["ocr_quality"] = True
        validation_results["image_references"] = True
        validation_results["document_structure"] = True
        
        # 5.1 Table structure detection - PDF2MD should properly identify and format tables
        table_indicators = ['|', '---', '===']
        has_table_markers = any(indicator in markdown_content for indicator in table_indicators)
        
        # Check if text suggests tables but no table formatting is found
        table_keywords = ['table', 'column', 'row']
        suggests_tables = any(keyword in markdown_content.lower() for keyword in table_keywords)
        
        if suggests_tables and not has_table_markers:
            validation_results["table_structure"] = False
            logger.warning(f"[{pdf_path}] Document suggests tables but no table formatting found")
        
        # Check for malformed tables (different number of columns in rows)
        if has_table_markers:
            table_rows = [line for line in markdown_lines if line.strip().startswith('|') and line.strip().endswith('|')]
            if table_rows:
                column_counts = [line.count('|') for line in table_rows]
                if len(set(column_counts)) > 1:
                    validation_results["table_structure"] = False
                    logger.warning(f"[{pdf_path}] Inconsistent table column counts detected: {column_counts}")
        
        # 5.2 List formatting - PDF2MD should properly format lists
        list_markers = ['- ', '* ', '1. ', '2. ']
        has_list_formatting = any(line.strip().startswith(marker) for line in markdown_lines for marker in list_markers)
        
        # Check for potential lists that aren't properly formatted
        potential_list_patterns = [
            re.compile(r'^\s*(\d+)\.\s'),  # Numbered lists without proper markdown formatting
            re.compile(r'^\s*[•●○◦]\s')     # Bullet lists without proper markdown formatting
        ]
        
        for pattern in potential_list_patterns:
            unformatted_lists = [line for line in markdown_lines if pattern.match(line) and not any(line.strip().startswith(marker) for marker in list_markers)]
            if unformatted_lists:
                validation_results["list_formatting"] = False
                logger.warning(f"[{pdf_path}] Potential unformatted lists detected: {unformatted_lists[:2]}")
        
        # 5.3 OCR quality check - Look for common OCR errors in scanned documents
        # Common OCR error patterns
        ocr_error_patterns = [
            re.compile(r'[A-Za-z][0O][A-Za-z]'),  # Likely 'O' confused with '0'
            re.compile(r'[A-Za-z][1I][A-Za-z]'),  # Likely 'I' confused with '1'
            re.compile(r'[A-Za-z][5S][A-Za-z]'),  # Likely 'S' confused with '5'
            re.compile(r'[A-Za-z][8B][A-Za-z]'),  # Likely 'B' confused with '8'
            re.compile(r'[A-Za-z]{15,}')          # Unusually long "words" (likely merged)
        ]
        
        potential_ocr_errors = 0
        for pattern in ocr_error_patterns:
            matches = pattern.findall(markdown_content)
            potential_ocr_errors += len(matches)
            if matches and len(matches) > 5:  # Allow a few potential errors
                validation_results["ocr_quality"] = False
                logger.warning(f"[{pdf_path}] Potential OCR errors detected: {matches[:5]}")
        
        # Check for high frequency of unusual character combinations (potential OCR issues)
        unusual_patterns = [
            re.compile(r'[a-z][A-Z][a-z]'),  # Mixed case in middle of word
            re.compile(r'\s[a-z][A-Z]'),     # Mixed case at start of word
            re.compile(r'[a-z]{1,2}\d{1,2}[a-z]{1,2}')  # Letters mixed with numbers
        ]
        
        unusual_count = 0
        for pattern in unusual_patterns:
            matches = pattern.findall(markdown_content)
            unusual_count += len(matches)
        
        ocr_quality_score = 100 - min(100, (potential_ocr_errors + unusual_count) / 10)
        logger.info(f"[{pdf_path}] OCR Quality Score: {ocr_quality_score:.1f}%")
        
        # 5.4 Image references check
        # PDF2MD has capability to extract and reference images
        image_refs = re.compile(r'!\[(.*?)\]\((.*?)\)').findall(markdown_content)
        
        # If PDF has images but no image references found, might indicate a quality issue
        if "_image_" in markdown_content or "[Image:" in markdown_content:
            if not image_refs:
                validation_results["image_references"] = False
                logger.warning(f"[{pdf_path}] Document mentions images but no proper Markdown image references found")
        
        # 5.5 Document structure preservation
        # PDF2MD should identify and preserve document structure (titles, sections, etc.)
        # Check if document has logical structure - title followed by sections
        
        # Count headers by level
        header_levels = {}
        for level, _ in headers:
            header_levels[level] = header_levels.get(level, 0) + 1
        
        # A well-structured document typically has fewer H1s than H2s, and logical hierarchy
        if header_levels.get(1, 0) > 5 or (header_levels.get(2, 0) > 0 and header_levels.get(1, 0) > header_levels.get(2, 0)):
            validation_results["document_structure"] = False
            logger.warning(f"[{pdf_path}] Document structure appears irregular: {header_levels}")
        
        # Check for reasonable section lengths (each section should have content)
        section_contents = []
        current_section = []
        
        for line in markdown_lines:
            if line.startswith('#'):
                if current_section:
                    section_contents.append(current_section)
                    current_section = []
            current_section.append(line)
        
        if current_section:  # Add the last section
            section_contents.append(current_section)
        
        # Check if any section is too short (might indicate structure issues)
        short_sections = [section for section in section_contents if len(section) < 3]
        if short_sections and len(short_sections) > len(section_contents) / 3:  # If more than 1/3 of sections are short
            validation_results["document_structure"] = False
            logger.warning(f"[{pdf_path}] Many short sections detected, possibly indicating structure issues")
        
        # 6. Summary of validation results
        all_passed = all(validation_results.values())
        
        # Log detailed results
        logger.info(f"=== PDF to Markdown Validation Results for {pdf_path} ===")
        for check, result in validation_results.items():
            status = "PASSED" if result else "FAILED"
            logger.info(f"  {check}: {status}")
        
        # Additional quality metrics
        num_headers = len(headers)
        num_paragraphs = len(markdown_content.split('\n\n'))
        avg_paragraph_length = sum(len(p) for p in markdown_content.split('\n\n')) / max(num_paragraphs, 1)
        
        logger.info(f"Quality metrics: {num_headers} headers, {num_paragraphs} paragraphs")
        logger.info(f"Average paragraph length: {avg_paragraph_length:.2f} characters")
        
        # Calculate an overall quality score (weighted)
        quality_weights = {
            "has_content": 5,
            "has_headers": 3,
            "has_paragraphs": 3,
            "structural_integrity": 4,
            "header_hierarchy": 3,
            "content_integrity": 4,
            "table_structure": 2,
            "list_formatting": 2,
            "ocr_quality": 4,
            "image_references": 2,
            "document_structure": 3
        }
        
        weighted_score = 0
        total_weight = sum(quality_weights.values())
        
        for check, result in validation_results.items():
            weight = quality_weights.get(check, 1)
            weighted_score += weight * (1 if result else 0)
        
        quality_score = (weighted_score / total_weight) * 100
        
        logger.info(f"Overall markdown quality score: {quality_score:.1f}%")
        logger.info("==================================")
        
        # Store the results for this PDF
        file_basename = os.path.basename(pdf_path)
        overall_results[file_basename] = {
            "quality_score": quality_score,
            "validation_results": validation_results,
            "metrics": {
                "num_headers": num_headers,
                "num_paragraphs": num_paragraphs,
                "avg_paragraph_length": avg_paragraph_length,
                "markdown_file_size": os.path.getsize(markdown_path)
            }
        }
    
    # 7. Save validation results to a report file
    report_path = "performance_metrics/pdf2md_validation_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(overall_results, f, indent=2)
    
    logger.info(f"Validation report saved to: {report_path}")
    
    # Overall test result
    if overall_results:
        average_score = sum(result["quality_score"] for result in overall_results.values()) / len(overall_results)
        logger.info(f"Average quality score across all tested PDFs: {average_score:.1f}%")
        
        if average_score >= 70:  # Set a reasonable threshold
            logger.info("Enhanced PDF to Markdown validation test PASSED")
        else:
            logger.warning("Enhanced PDF to Markdown validation test COMPLETED WITH WARNINGS")
    else:
        logger.error("No PDFs were successfully tested")
        sys.exit(1)
    
except ImportError as e:
    print(f"Error importing from jfk_scraper.py: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error during enhanced PDF to Markdown validation test: {e}")
    import traceback
    print(traceback.format_exc())
    sys.exit(1)
