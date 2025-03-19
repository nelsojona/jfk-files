#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON File Combiner for JFK Files

This script combines all individual JSON files in the json/ directory
into a single consolidated JSON file for use with GPT models.

Author: Cline
Date: March 18, 2025
"""

import os
import json
import argparse
import logging
import sys
from datetime import datetime
import hashlib

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

def get_files_in_directory(directory, extension='.json'):
    """
    Get a list of all files with the specified extension in the directory.
    
    Args:
        directory (str): The directory to search in
        extension (str): The file extension to filter by
        
    Returns:
        list: A list of file paths
    """
    if not os.path.exists(directory):
        logger.error(f"Directory does not exist: {directory}")
        return []
    
    files = []
    for filename in os.listdir(directory):
        if filename.lower().endswith(extension.lower()):
            files.append(os.path.join(directory, filename))
    
    logger.info(f"Found {len(files)} {extension} files in {directory}")
    return sorted(files)

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
        logger.error(f"Invalid JSON in {filepath}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        return None

def save_json_file(data, output_file, pretty=True):
    """
    Save data to a JSON file.
    
    Args:
        data (dict/list): The data to save
        output_file (str): The output file path
        pretty (bool): Whether to format the JSON with indentation
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Save to a temporary file first to ensure atomic writes
        temp_file = f"{output_file}.temp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(data, f, indent=2)
            else:
                json.dump(data, f)
        
        # Rename to final filename
        os.rename(temp_file, output_file)
        
        file_size = os.path.getsize(output_file)
        logger.info(f"Successfully saved {file_size} bytes to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving to {output_file}: {e}")
        return False

def generate_file_hash(filepath):
    """
    Generate a hash for the file contents.
    
    Args:
        filepath (str): Path to the file
        
    Returns:
        str: MD5 hash of the file contents
    """
    try:
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            buf = f.read(65536)  # Read in 64k chunks
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Error generating hash for {filepath}: {e}")
        return None

def combine_json_files(input_dir, output_file, format_type='array', metadata=True):
    """
    Combine multiple JSON files into a single JSON file.
    
    Args:
        input_dir (str): Directory containing JSON files
        output_file (str): Path to save the combined JSON
        format_type (str): 'array' or 'object' - how to combine the files
        metadata (bool): Whether to include metadata about the files
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Get all JSON files in the directory
    files = get_files_in_directory(input_dir, '.json')
    if not files:
        logger.error(f"No JSON files found in {input_dir}")
        return False
    
    # Initialize the output structure based on format type
    if format_type == 'array':
        combined_data = []
    else:  # format_type == 'object'
        combined_data = {}
    
    # Metadata for the combined file
    if metadata:
        file_metadata = {
            "source": "JFK Files Scraper",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_files": len(files),
            "file_list": []
        }
    
    # Process each file
    for i, filepath in enumerate(files, 1):
        logger.info(f"Processing file {i}/{len(files)}: {filepath}")
        
        # Load the JSON data
        json_data = load_json_file(filepath)
        if json_data is None:
            continue  # Skip this file if there was an error
        
        # Get filename and hash for metadata
        filename = os.path.basename(filepath)
        if metadata:
            file_hash = generate_file_hash(filepath)
            file_metadata["file_list"].append({
                "filename": filename,
                "path": filepath,
                "hash": file_hash
            })
        
        # Add the data to the combined structure
        if format_type == 'array':
            # For array format, add the document
            if isinstance(json_data, list):
                combined_data.extend(json_data)
            else:
                # Add document_id from filename if not present
                if "document_id" not in json_data:
                    doc_id = os.path.splitext(filename)[0]
                    json_data["document_id"] = doc_id
                combined_data.append(json_data)
        else:  # format_type == 'object'
            # For object format, use filename (without extension) as key
            key = os.path.splitext(filename)[0]
            combined_data[key] = json_data
    
    # Add metadata if requested
    if metadata:
        if format_type == 'array':
            # For array format, add metadata as first element
            combined_data.insert(0, {"metadata": file_metadata})
        else:  # format_type == 'object'
            # For object format, add metadata as a special key
            combined_data["_metadata"] = file_metadata
    
    # Save the combined data
    return save_json_file(combined_data, output_file)

def main():
    """Main function to parse arguments and combine JSON files."""
    parser = argparse.ArgumentParser(description="Combine multiple JSON files into a single file")
    parser.add_argument("--input-dir", default="json", help="Directory containing JSON files")
    parser.add_argument("--output-file", default="lite_llm/consolidated_jfk_files.json", 
                        help="Path to save the combined JSON file")
    parser.add_argument("--format", choices=["array", "object"], default="array",
                        help="Format to combine files: array (list of documents) or object (key-value pairs)")
    parser.add_argument("--no-metadata", action="store_true", 
                        help="Exclude metadata from the combined file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set log level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Log arguments
    logger.info(f"Starting JSON file combination")
    logger.info(f"Input directory: {args.input_dir}")
    logger.info(f"Output file: {args.output_file}")
    logger.info(f"Format: {args.format}")
    logger.info(f"Include metadata: {not args.no_metadata}")
    
    # Combine the files
    success = combine_json_files(
        args.input_dir,
        args.output_file,
        args.format,
        not args.no_metadata
    )
    
    if success:
        logger.info("Successfully combined JSON files")
        # Return file size in MB
        size_mb = os.path.getsize(args.output_file) / (1024 * 1024)
        logger.info(f"Output file size: {size_mb:.2f} MB")
        return 0
    else:
        logger.error("Failed to combine JSON files")
        return 1

if __name__ == "__main__":
    sys.exit(main())
