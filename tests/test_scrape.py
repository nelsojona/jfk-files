#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for JFK Files web scraping functionality.

This script tests the web scraping functionality using Crawl4AI.
"""

import sys
import os
import logging

# Add parent directory to python path to import from jfk_scraper.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Try to import the scrape_jfk_files function from jfk_scraper
    # Note: We need to modify this to work with AsyncWebCrawler
    from jfk_scraper import scrape_jfk_files, logger, create_directories
    
    # Make sure our directories exist
    create_directories()
    
    # Configure test-specific logging
    logger.info("Starting web scraping test")
    
    # Test scraping with a single page
    base_url = "https://www.archives.gov/research/jfk/release-2025"
    pdf_files = scrape_jfk_files(base_url, start_page=1, end_page=1)
    
    # Log results
    if pdf_files:
        logger.info(f"Successfully found {len(pdf_files)} PDF files on the first page")
        logger.info("Sample URLs:")
        for url in pdf_files[:5]:  # Show first 5 URLs
            logger.info(f"  - {url}")
        logger.info("Web scraping test PASSED")
    else:
        logger.error("No PDF files found. Test FAILED")
    
except ImportError as e:
    print(f"Error importing from jfk_scraper.py: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error during web scraping test: {e}")
    sys.exit(1)
