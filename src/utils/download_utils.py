#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download utilities for JFK Files Scraper.

This module provides functionality for downloading files from URLs,
with error handling, retry logic, and performance tracking.
"""

import os
import re
import time
import logging
import requests
from pathlib import Path

# Import custom exceptions and utilities
from src.utils.logging_utils import (
    DownloadError, track_error, update_performance_metrics, retry_with_backoff
)

# Initialize logger
logger = logging.getLogger("jfk_scraper.download")


@retry_with_backoff(max_retries=3, initial_delay=1, backoff_factor=2, 
                  exceptions=(requests.exceptions.RequestException, IOError, OSError))
def download_file(url, save_path, timeout=(10, 60), headers=None):
    """
    Downloads a file from the given URL with retries and error handling.
    
    Args:
        url (str): The URL to download from
        save_path (str): The path to save the file to
        timeout (tuple): Connection and read timeouts in seconds
        headers (dict): HTTP headers to use
        
    Returns:
        tuple: (success, file_size, download_time)
    """
    if headers is None:
        headers = {
            'User-Agent': 'JFK-Files-Scraper/1.0 (Research Project)',
            'Accept': '*/*'
        }
    
    start_time = time.time()
    
    logger.info(f"Downloading {url} to {save_path}")
    
    # Make the request with streaming enabled
    response = requests.get(url, stream=True, headers=headers, timeout=timeout)
    response.raise_for_status()
    
    # Get expected file size if available
    expected_size = int(response.headers.get('Content-Length', 0))
    actual_size = 0
    
    # Write directly to the final file path with immediate visibility
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:  # Filter out keep-alive chunks
                f.write(chunk)
                actual_size += len(chunk)
                # Force flush to ensure content is visible immediately
                f.flush()
                os.fsync(f.fileno())
    
    # Verify file size if expected size was provided
    if expected_size > 0 and actual_size != expected_size:
        os.remove(save_path)
        raise DownloadError(f"File size mismatch: expected {expected_size}, got {actual_size}")
    
    download_time = time.time() - start_time
    logger.info(f"Successfully downloaded {save_path} ({actual_size} bytes) in {download_time:.2f} seconds")
    
    return True, actual_size, download_time


def download_pdf(pdf_url, save_dir="pdfs", retry_count=3, organize_by_collection=True):
    """
    Downloads a PDF file from the given URL and saves it locally with enhanced
    directory organization and streaming visibility.

    Args:
        pdf_url (str): The URL of the PDF file.
        save_dir (str): The base directory to save the PDF to.
        retry_count (int): Number of times to retry on failure.
        organize_by_collection (bool): Whether to organize files into subdirectories.

    Returns:
        str: The path to the saved PDF file or None if download failed.
    """
    start_time = time.time()
    
    try:
        # Extract filename from URL
        filename = os.path.basename(pdf_url)
        if not filename.lower().endswith('.pdf'):
            filename = f"{filename}.pdf"
        
        # Create a safe filename
        safe_filename = "".join([c for c in filename if c.isalnum() or c in "._- "]).strip()
        
        # Determine appropriate subdirectory based on document properties
        if organize_by_collection:
            # Extract collection identifier from filename (assumes JFK format like 104-XXXXX-XXXXX)
            collection_match = re.match(r'^(\d+)-', safe_filename)
            doc_type = None
            
            if collection_match:
                collection_id = collection_match.group(1)
                
                # Categorize by collection ID
                if collection_id == "104":
                    doc_type = "nara-104"  # National Archives Record Group 104
                elif collection_id == "124":
                    doc_type = "nara-124"  # National Archives Record Group 124
                elif collection_id == "179":
                    doc_type = "nara-179"  # National Archives Record Group 179
                elif collection_id == "157":
                    doc_type = "hsca"      # House Select Committee on Assassinations
                else:
                    doc_type = f"collection-{collection_id}"
            else:
                # Check for other document identifiers
                if "docid" in safe_filename.lower():
                    doc_type = "misc-docid"
                elif any(s in safe_filename.lower() for s in ["cia", "fbi", "secret"]):
                    doc_type = "agency-docs"
                else:
                    doc_type = "uncategorized"
            
            # Create collection subdirectory
            collection_dir = os.path.join(save_dir, doc_type)
            os.makedirs(collection_dir, exist_ok=True)
            
            # Final save path with organized structure
            save_path = os.path.join(collection_dir, safe_filename)
        else:
            # Simple flat directory structure
            save_path = os.path.join(save_dir, safe_filename)
            os.makedirs(save_dir, exist_ok=True)
            
        # Skip if file already exists
        if os.path.exists(save_path):
            file_size = os.path.getsize(save_path)
            logger.info(f"File already exists: {save_path} (size: {file_size} bytes)")
            
            # Verify file integrity if it exists but has zero size
            if file_size == 0:
                logger.warning(f"Found empty file {save_path}, will retry download")
                os.remove(save_path)  # Remove corrupted/empty file
            else:
                # Update performance metrics for existing file
                update_performance_metrics(
                    total_download_size=file_size,
                    download_times=time.time() - start_time
                )
                return save_path
        
        # Make sure the parent directory exists
        parent_dir = os.path.dirname(save_path)
        os.makedirs(parent_dir, exist_ok=True)
        
        # Download the file
        success, file_size, download_time = download_file(
            pdf_url, 
            save_path,
            headers={
                'User-Agent': 'JFK-Files-Scraper/1.0 (Research Project)',
                'Accept': 'application/pdf'
            }
        )
        
        if success:
            # Update performance metrics
            update_performance_metrics(
                total_download_size=file_size,
                download_times=download_time
            )
            return save_path
        else:
            return None
            
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
        error_msg = f"HTTP error {status_code} downloading {pdf_url}: {e}"
        logger.error(error_msg)
        
        # Don't retry for certain status codes
        if status_code in (404, 403, 401):
            logger.error(f"Permanent HTTP error {status_code}, not retrying")
            track_error("download", DownloadError(error_msg), pdf_url)
            update_performance_metrics(failed_files=1)
            return None
        else:
            raise
            
    except Exception as e:
        error_msg = f"Error downloading {pdf_url}: {e}"
        logger.error(error_msg)
        track_error("download", DownloadError(error_msg), pdf_url)
        update_performance_metrics(failed_files=1)
        return None