#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web scraping utilities for JFK Files Scraper.

This module provides functionality for scraping JFK files from web sources,
with pagination handling and error recovery.
"""

import os
import time
import asyncio
import logging
from pathlib import Path
from bs4 import BeautifulSoup

# Import custom exceptions and utilities
from src.utils.logging_utils import track_error
from src.utils.checkpoint_utils import save_checkpoint

# Initialize logger
logger = logging.getLogger("jfk_scraper.scrape")

# Check for Crawl4AI availability
try:
    from crawl4ai import AsyncWebCrawler
    from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
    HAS_CRAWL4AI = True
    logger.info("Successfully imported Crawl4AI for web scraping")
except ImportError:
    HAS_CRAWL4AI = False
    logger.warning("Crawl4AI not available - web scraping functionality will be limited")


async def _scrape_page(crawler, page_url, run_config, retry_count=5):
    """
    Scrape a single page with retries.
    
    Args:
        crawler: AsyncWebCrawler instance
        page_url (str): URL of the page to scrape
        run_config: CrawlerRunConfig object
        retry_count (int): Number of retries on failure
        
    Returns:
        tuple: (success, pdf_files, error_message)
    """
    for attempt in range(1, retry_count + 1):
        try:
            # Use arun with proper configuration
            result = await crawler.arun(
                url=page_url,
                config=run_config
            )
            
            # Check if the crawl was successful
            if not result.success:
                logger.warning(f"Crawl failed: {result.error_message}")
                if attempt < retry_count:
                    logger.warning(f"Retrying page (attempt {attempt}/{retry_count})")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    error_msg = f"Failed to crawl page after {retry_count} attempts"
                    return False, [], error_msg
            
            # Extract PDF links from the page
            pdf_files = []
            
            # Create BeautifulSoup object from the HTML content
            soup = BeautifulSoup(result.html, 'html.parser')
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                # Check if it's a PDF link
                if href.lower().endswith('.pdf'):
                    # Make relative URLs absolute
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            href = f"https://www.archives.gov{href}"
                        else:
                            base_url = page_url.split('?')[0]
                            href = f"{base_url}/{href}"
                    pdf_files.append(href)
            
            return True, pdf_files, None
            
        except Exception as e:
            if attempt < retry_count:
                logger.warning(f"Error scraping page (attempt {attempt}/{retry_count}): {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                error_msg = f"Failed to scrape page after {retry_count} attempts: {e}"
                return False, [], error_msg


async def _async_scrape_jfk_files(base_url, start_page, end_page, total_pages):
    """
    Internal async function to scrape JFK files.
    
    Args:
        base_url (str): Base URL for scraping
        start_page (int): Starting page number
        end_page (int): Ending page number
        total_pages (int): Total number of pages
        
    Returns:
        list: List of PDF file URLs
    """
    # Create proper configurations for Crawl4AI
    browser_config = BrowserConfig(
        verbose=True
        # Note: Update this configuration based on the actual Crawl4AI API
    )
    run_config = CrawlerRunConfig(
        word_count_threshold=10,
        process_iframes=True,
        remove_overlay_elements=True
    )
    
    # Initialize the crawler with proper configuration
    async with AsyncWebCrawler(config=browser_config) as crawler:
        pdf_files = []
        page = start_page
        
        # Track processed pages for checkpointing
        processed_pages = 0
        
        # Process each page
        while page <= end_page:
            page_url = f"{base_url}?page={page}"
            logger.info(f"Scraping page {page} of {total_pages}: {page_url}")
            
            success, page_pdf_files, error_msg = await _scrape_page(crawler, page_url, run_config)
            
            if success:
                # Log the results and add to our collection
                logger.info(f"Found {len(page_pdf_files)} PDF files on page {page}")
                pdf_files.extend(page_pdf_files)
                
                # Save page checkpoint for resumable scraping
                checkpoint_data = {
                    "last_processed_page": page,
                    "total_pdf_files": len(pdf_files),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                save_checkpoint(checkpoint_data, f"scrape_page_{page}")
                
                processed_pages += 1
                
                # Add delay to avoid overloading server
                # Adaptive delay - slower for large batches
                delay = min(2.0, 0.5 + (processed_pages / 20))
                logger.debug(f"Waiting {delay:.2f}s before next page")
                await asyncio.sleep(delay)
            else:
                logger.error(error_msg)
                track_error("scraping", Exception(error_msg), page_url)
            
            page += 1
            
            # Every 10 pages, save a comprehensive checkpoint
            if page % 10 == 0:
                logger.info(f"Progress checkpoint: {processed_pages}/{total_pages} pages, {len(pdf_files)} PDF files")
                comprehensive_checkpoint = {
                    "pdf_urls": pdf_files,
                    "processed_pages": processed_pages,
                    "total_pages": total_pages,
                    "last_page": page - 1,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                save_checkpoint(comprehensive_checkpoint, "scrape_progress")
    
        # Save final checkpoint
        final_checkpoint = {
            "pdf_urls": pdf_files,
            "processed_pages": processed_pages,
            "total_pages": total_pages,
            "complete": True,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        save_checkpoint(final_checkpoint, "scrape_complete")
        
        # Close the crawler
        await crawler.close()
        logger.info(f"Total PDF files found: {len(pdf_files)}")
        return pdf_files


def scrape_jfk_files(base_url, start_page=1, end_page=None):
    """
    Scrapes JFK file URLs from the National Archives website, handling pagination.

    Args:
        base_url (str): The base URL of the JFK records page.
        start_page (int): The page to start scraping from.
        end_page (int): The page to end scraping at. If None, scrapes all pages.

    Returns:
        list: A list of PDF file URLs.
    """
    logger.info("Initializing web crawler with proper configuration")
    
    if not HAS_CRAWL4AI:
        logger.error("Crawl4AI not available - cannot perform web scraping")
        return []
    
    # Set total pages - default to all 113 pages from Archive
    if end_page is None:
        total_pages = 113  # Full JFK Archive has 113 pages
        logger.info(f"Using default total pages: {total_pages}")
        end_page = total_pages
    else:
        total_pages = end_page
        logger.info(f"Using specified end page: {total_pages}")
    
    # Run the async function and return the results
    try:
        return asyncio.run(_async_scrape_jfk_files(base_url, start_page, end_page, total_pages))
    except Exception as e:
        error_msg = f"Failed to scrape JFK files: {e}"
        logger.error(error_msg)
        track_error("scraping", e, base_url, fatal=True)
        return []