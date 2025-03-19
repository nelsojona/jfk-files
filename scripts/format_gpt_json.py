#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPT Knowledge Format Script for JFK Files

This script takes the consolidated JSON file and reformats it for optimal GPT
knowledge upload. It transforms the structure to be more efficient for GPT processing
while preserving all essential document information.

Author: Cline
Date: March 18, 2025
"""

import os
import json
import argparse
import logging
import sys
from datetime import datetime

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

def format_for_gpt(input_data):
    """
    Reformat the consolidated JSON data for optimal GPT knowledge upload.
    
    Args:
        input_data (list): The consolidated JSON data
        
    Returns:
        list: Reformatted data optimized for GPT
    """
    logger.info("Reformatting JSON data for GPT knowledge upload")
    
    # Create a new structured array for GPT
    gpt_formatted_data = []
    
    # Metadata for the GPT knowledge base
    metadata = {
        "type": "metadata",
        "knowledge_base_name": "JFK Files Archive",
        "description": "Declassified documents from the JFK Assassination Records Collection",
        "document_count": 0,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0"
    }
    
    # Track unique documents to avoid duplicates (some appear multiple times in input)
    processed_docs = set()
    
    # Process each entry in the input data
    for i, entry in enumerate(input_data):
        # Debug entry keys
        if isinstance(entry, dict):
            logger.info(f"Entry {i} keys: {list(entry.keys())}")
        else:
            logger.info(f"Entry {i} is not a dict: {type(entry)}")
        
        # First entry is metadata, we can skip it
        if i == 0 and isinstance(entry, dict) and 'metadata' in entry:
            logger.info(f"Found first entry with metadata, skipping")
            continue
            
        # For our format, the entries are directly documents
        if not isinstance(entry, dict) or 'document_id' not in entry:
            logger.warning(f"Skipping invalid entry: {type(entry)}")
            continue
            
        doc_id = entry.get('document_id')
        
        # Skip duplicates
        if doc_id in processed_docs:
            logger.info(f"Skipping duplicate document: {doc_id}")
            continue
            
        processed_docs.add(doc_id)
        
        # Create a formatted document entry
        doc_entry = {
            "type": "document",
            "id": doc_id,
            "title": entry.get('metadata', {}).get('title', doc_id),
            "content": "",  # Will be filled with concatenated page content
            "metadata": {
                "source": f"{doc_id}.json",
                "timestamp": entry.get('metadata', {}).get('conversion_timestamp', ''),
                "total_pages": entry.get('total_pages', 0),
                "conversion_method": entry.get('metadata', {}).get('conversion_method', 'unknown')
            }
        }
        
        # Concatenate page content with appropriate formatting
        concatenated_content = []
        for page in entry.get('pages', []):
            if page.get('title') and page.get('title') != "Unknown":
                concatenated_content.append(f"## {page['title']}")
            
            if page.get('content'):
                # Clean up content (remove unnecessary markdown headers and extra newlines)
                page_content = page['content']
                if page_content.startswith(f"# {doc_id}"):
                    page_content = page_content.replace(f"# {doc_id}", "", 1).lstrip()
                    
                concatenated_content.append(page_content.strip())
        
        # Set the concatenated content
        doc_entry["content"] = "\n\n".join(concatenated_content).strip()
        
        # Add document to the output array
        gpt_formatted_data.append(doc_entry)
    
    # Update metadata with actual document count
    metadata["document_count"] = len(processed_docs)
    
    # Add metadata as first element
    gpt_formatted_data.insert(0, metadata)
    
    logger.info(f"Reformatted {len(processed_docs)} unique documents for GPT knowledge upload")
    return gpt_formatted_data

def main():
    """Main function to parse arguments and format JSON for GPT."""
    parser = argparse.ArgumentParser(description="Format consolidated JSON for GPT knowledge upload")
    parser.add_argument("--input-file", default="lite_llm/jfk_files.json", 
                        help="Path to the consolidated JSON file")
    parser.add_argument("--output-file", default="lite_llm/jfk_files_gpt.json", 
                        help="Path to save the GPT-formatted JSON file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set log level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Log arguments
    logger.info(f"Starting GPT JSON formatting")
    logger.info(f"Input file: {args.input_file}")
    logger.info(f"Output file: {args.output_file}")
    
    # Load the consolidated JSON data
    input_data = load_json_file(args.input_file)
    if input_data is None:
        logger.error(f"Failed to load input file: {args.input_file}")
        return 1
    
    # Format the data for GPT
    gpt_formatted_data = format_for_gpt(input_data)
    
    # Save the GPT-formatted data
    success = save_json_file(gpt_formatted_data, args.output_file)
    
    if success:
        logger.info("Successfully formatted JSON for GPT knowledge upload")
        # Return file size in MB
        size_mb = os.path.getsize(args.output_file) / (1024 * 1024)
        logger.info(f"Output file size: {size_mb:.2f} MB")
        return 0
    else:
        logger.error("Failed to save GPT-formatted JSON")
        return 1

if __name__ == "__main__":
    sys.exit(main())
