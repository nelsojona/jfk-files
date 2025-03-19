#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
** J F K   F I L E S   S C R A P E R **


JFK Files Scraper

A script to scrape JFK files from the National Archives website, handle pagination,
transform the data from PDF to Markdown, and then convert it to JSON.

Author: Cline
Date: March 18, 2025
Version: 1.0.0
Repository: https://github.com/yourusername/jfk-files-scraper
License: MIT

This tool is intended for research and educational purposes only.
Please use responsibly and in accordance with the National Archives' terms of service.
"""

# Standard library imports
import argparse
import logging
import os
import sys
import time

# Import utility modules
from src.utils.logging_utils import (
    configure_logging, log_metrics, update_performance_metrics
)
from src.utils.checkpoint_utils import (
    save_checkpoint, load_checkpoint, create_directories
)
from src.utils.scrape_utils import scrape_jfk_files
from src.utils.download_utils import download_pdf
from src.utils.conversion_utils import (
    pdf_to_markdown, markdown_to_json, 
    transform_pandoc_json_to_standard_format, parse_markdown_with_python
)
from src.utils.batch_utils import (
    process_file, process_batch, process_all_files, _process_all_files_optimized
)
from src.utils.storage import store_json_data, get_document_path

# Initialize the logger with a default configuration for imports
from src.utils.logging_utils import configure_logging
logger = configure_logging()


def main():
    """Main entry point for the JFK Files Scraper."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Scrape JFK files from the National Archives website.")
    parser.add_argument("--url", default="https://www.archives.gov/research/jfk/release-2025", help="Base URL for JFK files.")
    parser.add_argument("--start-page", type=int, default=1, help="Page to start scraping from.")
    parser.add_argument("--end-page", type=int, help="Page to end scraping at. If not provided, scrapes all pages.")
    parser.add_argument("--test", action="store_true", help="Run in test mode with limited pages.")
    parser.add_argument("--full", action="store_true", help="Run full-scale processing.")
    parser.add_argument("--ocr", action="store_true", help="Force OCR for all PDF conversions.")
    parser.add_argument("--force-ocr", action="store_true", help="Same as --ocr, forces OCR for all PDFs regardless of content type.")
    parser.add_argument("--ocr-quality", choices=["low", "medium", "high"], default="high",
                        help="Quality setting for OCR (affects resolution and processing). Default is 'high'.")
    parser.add_argument("--resume", action="store_true", help="Resume from the last checkpoint.")
    parser.add_argument("--no-resume", action="store_false", dest="resume", help="Do not resume from checkpoint.")
    parser.add_argument("--max-workers", type=int, help="Maximum number of concurrent downloads. Default is based on CPU count.")
    parser.add_argument("--scrape-all", action="store_true", help="Scrape all 113 pages and process all 1,123 files.")
    parser.add_argument("--organize", action="store_true", default=True, help="Organize PDFs into subdirectories by collection.")
    parser.add_argument("--flat", action="store_false", dest="organize", help="Save PDFs in a flat directory structure.")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                         help="Set the logging level (default: INFO).")
    parser.set_defaults(resume=True)  # Default to resume if not specified

    args = parser.parse_args()

    # Configure logging based on command-line argument
    global logger
    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")
    logger = configure_logging(log_level=numeric_level)
    
    # Process OCR options - use force_ocr if specified, otherwise fall back to ocr
    use_ocr = args.force_ocr or args.ocr
    
    # Handle test mode
    if args.test:
        logger.info(f"Running in test mode (OCR: {use_ocr}, Quality: {args.ocr_quality}).")
        
        # Test with a few sample PDF URLs directly for testing
        test_urls = [
            "https://www.archives.gov/files/research/jfk/releases/docid-32204484.pdf",
            "https://www.archives.gov/files/research/jfk/releases/104-10007-10345.pdf"
        ]
        
        logger.info(f"Testing with {len(test_urls)} sample URLs")
        
        # Create processing options dictionary
        processing_options = {
            "with_ocr": use_ocr,
            "ocr_quality": args.ocr_quality,
            "organize_directories": args.organize
        }
        
        # Add max_workers if specified
        if args.max_workers:
            processing_options["max_workers"] = args.max_workers
            
        for url in test_urls:
            process_file(url, **processing_options)

    # Handle full-scale processing
    elif args.full:
        logger.info(f"Running full-scale processing (OCR: {use_ocr}, Quality: {args.ocr_quality}).")
        
        # Create processing options dictionary
        processing_options = {
            "resume": args.resume,
            "with_ocr": use_ocr,
            "ocr_quality": args.ocr_quality,
            "organize_directories": args.organize
        }
        
        # Add max_workers if specified
        if args.max_workers:
            processing_options["max_workers"] = args.max_workers
            
        process_all_files(**processing_options)

    # Handle scrape-all mode (PROD-1) 
    elif args.scrape_all:
        logger.info(f"Starting full-scale crawling and processing of all 1,123 JFK files (pages 1-113)")
        logger.info(f"Processing options: OCR={use_ocr}, Quality={args.ocr_quality}, Organized={args.organize}")
        
        # Set end page to 113 (all pages in the archive)
        end_page = 113
        logger.info(f"Scraping pages 1-{end_page} from {args.url}")
        
        # Scrape all URLs
        urls = scrape_jfk_files(args.url, args.start_page, end_page)
        if urls:
            logger.info(f"Successfully scraped {len(urls)} URLs from {end_page} pages")
            # Save the scraped URLs to a checkpoint
            save_checkpoint({"pdf_urls": urls}, "urls")
            
            # Process all scraped files with enhanced options
            logger.info("Starting full-scale processing of all scraped files")
            
            # Create processing options dictionary
            processing_options = {
                "resume": args.resume,
                "with_ocr": use_ocr,
                "ocr_quality": args.ocr_quality,
                "organize_directories": args.organize
            }
            
            # Add max_workers if specified
            if args.max_workers:
                processing_options["max_workers"] = args.max_workers
                
            process_all_files(urls, **processing_options)
        else:
            logger.error("Failed to scrape URLs. Please check the logs for details.")
    
    # If no specific mode is selected, scrape URLs based on provided arguments
    else:
        urls = scrape_jfk_files(args.url, args.start_page, args.end_page)
        if urls:
            logger.info(f"Scraped {len(urls)} URLs. Use --full to process them.")
            # Save the scraped URLs to a checkpoint for later use
            save_checkpoint({"pdf_urls": urls}, "urls")
        else:
            logger.warning("No URLs scraped.")
    
    # Log final metrics
    log_metrics()


if __name__ == "__main__":
    # Reset performance metrics time at start
    update_performance_metrics(start_time=time.time())
    
    # Create necessary directories
    create_directories()
    
    # Run main function
    main()
