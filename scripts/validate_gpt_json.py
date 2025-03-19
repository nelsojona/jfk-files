#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPT Knowledge JSON Validator

This script validates the GPT-formatted JSON file structure and content
to ensure it meets all requirements for GPT knowledge upload.

Author: Cline
Date: March 18, 2025
"""

import os
import json
import argparse
import logging
import sys
from datetime import datetime
import re

# Configure logging
def configure_logging(log_level=logging.INFO):
    """Configure logging with proper formatting."""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

# Initialize logger
logger = configure_logging()

def load_json_file(filepath):
    """
    Load a JSON file and return its contents.
    
    Args:
        filepath (str): Path to the JSON file
        
    Returns:
        dict/list: The JSON contents or None if there was an error
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error loading {filepath}: {str(e)}")
        return None

def validate_json_structure(data):
    """
    Validate the basic structure of the GPT-formatted JSON data.
    
    Args:
        data: The loaded JSON data
        
    Returns:
        bool: True if the structure is valid, False otherwise
        list: List of validation errors
    """
    errors = []
    
    # Check if it's a list
    if not isinstance(data, list):
        errors.append("JSON data must be an array/list")
        return False, errors
    
    # Check if it's empty
    if len(data) == 0:
        errors.append("JSON array is empty")
        return False, errors
    
    # Check if first element is metadata
    first_element = data[0]
    if not isinstance(first_element, dict):
        errors.append("First element must be a metadata object")
        return False, errors
    
    # Check metadata structure
    required_metadata_fields = ["type", "knowledge_base_name", "description", "document_count", "created_at", "version"]
    for field in required_metadata_fields:
        if field not in first_element:
            errors.append(f"Metadata missing required field: {field}")
    
    if first_element.get("type") != "metadata":
        errors.append("Metadata 'type' field must be 'metadata'")
    
    # Check if document count matches
    if "document_count" in first_element:
        expected_count = first_element["document_count"]
        actual_count = len(data) - 1  # Subtract 1 for metadata
        if expected_count != actual_count:
            errors.append(f"Document count mismatch: metadata says {expected_count}, but found {actual_count} documents")
    
    # Check document structure for each document
    document_ids = set()
    for i, document in enumerate(data[1:], 1):
        if not isinstance(document, dict):
            errors.append(f"Document at index {i} is not an object")
            continue
        
        # Check required fields
        required_document_fields = ["type", "id", "title", "content", "metadata"]
        for field in required_document_fields:
            if field not in document:
                errors.append(f"Document at index {i} missing required field: {field}")
        
        # Check type field
        if document.get("type") != "document":
            errors.append(f"Document at index {i} has incorrect 'type' value (should be 'document')")
        
        # Check ID uniqueness
        doc_id = document.get("id")
        if doc_id:
            if doc_id in document_ids:
                errors.append(f"Duplicate document ID: {doc_id}")
            else:
                document_ids.add(doc_id)
        
        # Check metadata structure
        metadata = document.get("metadata", {})
        if not isinstance(metadata, dict):
            errors.append(f"Document at index {i} has invalid metadata (not an object)")
        else:
            required_metadata_fields = ["source", "timestamp", "total_pages"]
            for field in required_metadata_fields:
                if field not in metadata:
                    errors.append(f"Document at index {i} metadata missing required field: {field}")
    
    return len(errors) == 0, errors

def validate_content_quality(data):
    """
    Validate the content quality of the GPT-formatted JSON data.
    
    Args:
        data: The loaded JSON data
        
    Returns:
        bool: True if the content quality is acceptable, False otherwise
        list: List of validation warnings
    """
    warnings = []
    
    # Skip if structure is invalid
    if not isinstance(data, list) or len(data) <= 1:
        warnings.append("Cannot validate content quality due to structural issues")
        return False, warnings
    
    # Check each document's content
    for i, document in enumerate(data[1:], 1):
        if not isinstance(document, dict) or "content" not in document or "id" not in document:
            continue
        
        doc_id = document["id"]
        content = document["content"]
        
        # Check if content is empty
        if not content or content.strip() == "":
            warnings.append(f"Document '{doc_id}' has empty content")
            continue
        
        # Check content length
        if len(content) < 50:  # Arbitrary minimum content length
            warnings.append(f"Document '{doc_id}' has very short content ({len(content)} chars)")
        
        # Check for placeholder content
        if "placeholder" in content.lower() or "this is a test" in content.lower():
            warnings.append(f"Document '{doc_id}' appears to contain placeholder text")
        
        # Check page markers
        page_headers = re.findall(r'## Page \d+', content)
        if not page_headers:
            warnings.append(f"Document '{doc_id}' is missing page markers")
        
        # Check content structure (look for paragraphs)
        paragraphs = [p for p in content.split("\n\n") if p.strip()]
        if len(paragraphs) < 2:
            warnings.append(f"Document '{doc_id}' may have poor content structure (few paragraphs)")
        
        # Checks for metadata consistency
        metadata = document.get("metadata", {})
        total_pages = metadata.get("total_pages", 0)
        if total_pages > 0 and len(page_headers) < total_pages:
            warnings.append(f"Document '{doc_id}' has {total_pages} pages but only {len(page_headers)} page headers")
    
    return len(warnings) == 0, warnings

def generate_summary_report(filepath, structure_pass, structure_errors, content_pass, content_warnings):
    """
    Generate a summary report of the validation results.
    
    Args:
        filepath: Path to the validated file
        structure_pass: Whether structural validation passed
        structure_errors: List of structural errors
        content_pass: Whether content validation passed
        content_warnings: List of content warnings
        
    Returns:
        str: Report text
    """
    file_size = os.path.getsize(filepath) / (1024 * 1024)  # MB
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""
# GPT Knowledge JSON Validation Report

## Summary

- **File**: {filepath}
- **Size**: {file_size:.2f} MB
- **Validation Time**: {timestamp}
- **Structural Validation**: {"PASSED" if structure_pass else "FAILED"}
- **Content Quality Validation**: {"PASSED" if content_pass else "PASSED WITH WARNINGS" if content_warnings else "FAILED"}

## Structural Validation

{f"✓ No structural errors found." if structure_pass else f"✗ Found {len(structure_errors)} structural errors:"}

"""
    
    if not structure_pass:
        for i, error in enumerate(structure_errors, 1):
            report += f"{i}. {error}\n"
    
    report += """
## Content Quality Validation

"""
    
    if content_pass:
        report += "✓ No content quality issues found.\n"
    else:
        report += f"⚠ Found {len(content_warnings)} content quality warnings:\n\n"
        for i, warning in enumerate(content_warnings, 1):
            report += f"{i}. {warning}\n"
    
    report += """
## Recommendations

"""
    
    if structure_pass and content_pass:
        report += "✓ The file is ready for GPT knowledge upload.\n"
    elif structure_pass:
        report += "⚠ The file has passed structural validation but has content quality warnings. Review the warnings and consider improving the content before uploading.\n"
    else:
        report += "✗ The file has structural errors that must be fixed before uploading to GPT. Fix the errors and validate again.\n"
    
    return report

def main():
    """Main function to parse arguments and validate JSON."""
    parser = argparse.ArgumentParser(description="Validate GPT-formatted JSON for knowledge upload")
    parser.add_argument("--input-file", default="lite_llm/jfk_files_gpt.json", 
                        help="Path to the GPT-formatted JSON file")
    parser.add_argument("--report-file", default="lite_llm/validation_report.md", 
                        help="Path to save the validation report")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set log level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Log arguments
    logger.info(f"Starting GPT JSON validation")
    logger.info(f"Input file: {args.input_file}")
    logger.info(f"Report file: {args.report_file}")
    
    # Load the GPT-formatted JSON data
    input_data = load_json_file(args.input_file)
    if input_data is None:
        logger.error(f"Failed to load input file: {args.input_file}")
        return 1
    
    # Validate the structure
    logger.info("Validating JSON structure...")
    structure_pass, structure_errors = validate_json_structure(input_data)
    if structure_pass:
        logger.info("JSON structure validation passed")
    else:
        logger.error(f"JSON structure validation failed with {len(structure_errors)} errors")
        for error in structure_errors:
            logger.error(f"  - {error}")
    
    # Validate the content quality
    logger.info("Validating content quality...")
    content_pass, content_warnings = validate_content_quality(input_data)
    if content_pass:
        logger.info("Content quality validation passed")
    else:
        logger.warning(f"Content quality validation found {len(content_warnings)} warnings")
        for warning in content_warnings:
            logger.warning(f"  - {warning}")
    
    # Generate and save the report
    logger.info("Generating validation report...")
    report = generate_summary_report(
        args.input_file,
        structure_pass,
        structure_errors,
        content_pass,
        content_warnings
    )
    
    try:
        os.makedirs(os.path.dirname(args.report_file), exist_ok=True)
        with open(args.report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"Validation report saved to {args.report_file}")
    except Exception as e:
        logger.error(f"Error saving validation report: {str(e)}")
    
    # Print overall validation result
    if structure_pass and content_pass:
        logger.info("Validation PASSED: The file is ready for GPT knowledge upload")
        return 0
    elif structure_pass:
        logger.warning("Validation PASSED WITH WARNINGS: Review content quality issues")
        return 0
    else:
        logger.error("Validation FAILED: Fix structural errors before uploading")
        return 1

if __name__ == "__main__":
    sys.exit(main())
