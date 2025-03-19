#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch processing utilities for JFK Files Scraper.

This module provides functionality for processing files in batches,
with performance tracking and error handling.
"""

import os
import time
import logging
import concurrent.futures
from pathlib import Path

# Import custom exceptions and utilities
from src.utils.logging_utils import (
    track_error, update_performance_metrics
)
from src.utils.checkpoint_utils import save_checkpoint, load_checkpoint
from src.utils.download_utils import download_pdf
from src.utils.conversion_utils import pdf_to_markdown, markdown_to_json

# Initialize logger
logger = logging.getLogger("jfk_scraper.batch")


def process_file(url, with_ocr=False, ocr_quality="high", organize_directories=True, with_performance_monitoring=True):
    """
    Process a single file through the complete pipeline (download → PDF → Markdown → JSON).
    
    Args:
        url (str): URL of the PDF file to process
        with_ocr (bool): Whether to force OCR for PDF to Markdown conversion
        ocr_quality (str): OCR quality setting ("low", "medium", "high")
        organize_directories (bool): Whether to organize PDFs into subdirectories by collection
        with_performance_monitoring (bool): Whether to monitor and report performance
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    logger.info(f"Processing file: {url}")
    logger.info(f"Options: OCR={with_ocr}, Quality={ocr_quality}, Organized={organize_directories}")
    
    # Update performance metrics
    update_performance_metrics(processed_files=1)
    
    # Initialize performance monitoring if requested
    if with_performance_monitoring:
        try:
            from src.performance_monitoring import PerformanceMetrics, MonitoringConfig
            monitoring_config = MonitoringConfig()
            metrics = PerformanceMetrics(monitoring_config)
        except ImportError:
            logger.warning("Performance monitoring module not available")
            with_performance_monitoring = False
    
    try:
        # Step 1: Download PDF with organization option
        pdf_path = download_pdf(url, organize_by_collection=organize_directories)
        if not pdf_path:
            logger.error(f"Failed to download PDF from {url}")
            update_performance_metrics(failed_files=1)
            return False
        
        # Step 2: Convert PDF to Markdown with enhanced OCR options
        markdown_path, _ = pdf_to_markdown(pdf_path, force_ocr=with_ocr, ocr_quality=ocr_quality)
        if not markdown_path:
            logger.error(f"Failed to convert PDF to Markdown: {pdf_path}")
            update_performance_metrics(failed_files=1)
            return False

        # Step 3: Convert Markdown to JSON with enhanced schema
        json_path, json_content = markdown_to_json(markdown_path)
        if not json_path:
            logger.error(f"Failed to convert Markdown to JSON: {markdown_path}")
            update_performance_metrics(failed_files=1)
            return False
            
        # Step 4: Store in Lite LLM format
        from src.utils.storage import store_json_data
        lite_llm_path = "lite_llm/jfk_files.json"
        stored = store_json_data(json_path, lite_llm_path)
        if not stored:
            logger.warning(f"Failed to store JSON data in Lite LLM format: {json_path}")
            # Continue anyway, don't consider this a fatal error

        # Update performance metrics
        update_performance_metrics(successful_files=1)
        
        # Generate performance report if monitoring is enabled
        if with_performance_monitoring:
            try:
                metrics._generate_json_report()
            except Exception as e:
                logger.warning(f"Error generating performance report: {e}")
        
        logger.info(f"Successfully processed file: {url}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing file {url}: {e}")
        logger.error(traceback.format_exc())
        track_error("general", e, url)
        update_performance_metrics(failed_files=1)
        return False


def process_batch(urls, batch_number, batch_metrics=None, with_ocr=False, ocr_quality="high", max_workers=None):
    """
    Process a batch of files concurrently with batch metrics tracking.
    
    Args:
        urls (list): List of PDF URLs to process
        batch_number (int): Batch number for tracking
        batch_metrics (object): BatchMetrics object for tracking (optional)
        with_ocr (bool): Whether to force OCR for PDF conversion
        max_workers (int, optional): Maximum number of concurrent workers
        
    Returns:
        tuple: (successful_count, failed_count)
    """
    logger.info(f"Processing batch {batch_number} with {len(urls)} files")
    
    # Start batch tracking if metrics object provided
    if batch_metrics:
        batch_metrics.start_batch(batch_number, urls)
    
    successful = 0
    failed = 0
    
    # Determine optimal max_workers if not specified
    if max_workers is None:
        max_workers = min(10, max(1, os.cpu_count() or 4))
    
    # Split processing into two phases: 
    # 1. Download PDFs concurrently (IO-bound)
    # 2. Process PDFs (CPU-bound with OCR)
    
    downloaded_paths = []
    download_results = {}
    
    # Phase 1: Download PDFs concurrently
    logger.info(f"Starting concurrent downloads with {max_workers} workers")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Prepare download futures
        future_to_url = {
            executor.submit(
                download_pdf, 
                url, 
                "pdfs", 
                retry_count=3, 
                organize_by_collection=True
            ): url for url in urls
        }
        
        # Process download results as they complete
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                pdf_path = future.result()
                if pdf_path:
                    download_results[url] = (True, pdf_path)
                    downloaded_paths.append(pdf_path)
                    logger.info(f"Successfully downloaded {url} -> {pdf_path}")
                else:
                    download_results[url] = (False, None)
                    logger.error(f"Failed to download {url}")
            except Exception as e:
                download_results[url] = (False, None)
                logger.error(f"Download error for {url}: {e}")
    
    # Log download phase results
    successful_downloads = sum(1 for result in download_results.values() if result[0])
    logger.info(f"Download phase complete: {successful_downloads}/{len(urls)} successful")
    
    # Phase 2: Process downloaded PDFs
    # Note: We process one at a time since OCR is CPU and memory intensive
    for url in urls:
        start_time = time.time()
        success = False
        
        download_success, pdf_path = download_results.get(url, (False, None))
        
        if download_success and pdf_path:
            try:
                # Convert the PDF to markdown with quality settings
                markdown_path, _ = pdf_to_markdown(pdf_path, force_ocr=with_ocr, ocr_quality=ocr_quality)
                
                if markdown_path:
                    # Convert the markdown to JSON
                    json_path, json_content = markdown_to_json(markdown_path)
                    
                    if json_path:
                        # Store in Lite LLM format
                        try:
                            from src.utils.storage import store_json_data
                            lite_llm_path = "lite_llm/jfk_files.json"
                            stored = store_json_data(json_path, lite_llm_path)
                        except Exception as e:
                            logger.warning(f"Error storing JSON data in Lite LLM format: {e}")
                        
                        success = True
                        logger.info(f"Successfully processed {url}")
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
        
        processing_time = time.time() - start_time
        
        if success:
            successful += 1
        else:
            failed += 1
        
        # Record metrics if available
        if batch_metrics:
            batch_metrics.record_file_processed(url, success, processing_time)
    
    # End batch tracking if metrics object provided
    if batch_metrics:
        batch_metrics.end_batch()
    
    logger.info(f"Batch {batch_number} complete: {successful} successful, {failed} failed")
    return successful, failed


def process_all_files(urls=None, resume=True, batch_size=50, with_ocr=False, ocr_quality="high", 
                    max_workers=None, organize_directories=True):
    """
    Process all JFK files with batch processing.
    
    Args:
        urls (list): List of URLs to process. If None, will try to load from checkpoint.
        resume (bool): Whether to resume from checkpoint if available.
        batch_size (int): Size of batches for processing.
        with_ocr (bool): Whether to force OCR for all PDF conversions.
        ocr_quality (str): OCR quality setting ("low", "medium", "high").
        max_workers (int): Maximum number of concurrent downloads.
        organize_directories (bool): Whether to organize PDFs into subdirectories.
        
    Returns:
        tuple: (successful_count, failed_count, total_count)
    """
    # Try to import optimization modules
    try:
        from src.optimization import LargeScaleProcessor, OptimizationConfig
        has_optimization = True
        logger.info("Successfully imported optimization modules")
    except ImportError:
        has_optimization = False
        logger.warning("Optimization modules not available - using basic processing")
    
    # Try to import batch metrics
    try:
        from src.performance_monitoring import BatchMetrics
        has_batch_metrics = True
    except ImportError:
        has_batch_metrics = False
        logger.warning("BatchMetrics not available - will process without detailed metrics")
    
    # If optimization is available, use it
    if has_optimization:
        return _process_all_files_optimized(urls, resume)
    
    # Otherwise, use basic batch processing
    logger.info("Starting full-scale processing with basic batch processing")
    
    # If no URLs provided, try to load from checkpoint
    if urls is None:
        checkpoint_data = load_checkpoint("urls")
        if checkpoint_data and "pdf_urls" in checkpoint_data:
            urls = checkpoint_data["pdf_urls"]
            logger.info(f"Loaded {len(urls)} URLs from checkpoint")
        else:
            logger.error("No URL list provided and no checkpoint found")
            return 0, 0, 0
    
    # Initialize metrics if available
    batch_metrics = None
    if has_batch_metrics:
        logger.info("Initializing batch metrics for tracking")
        batch_metrics = BatchMetrics(batch_size=batch_size)
    
    # Create directories
    _create_directories()
    
    # Split URLs into batches
    total_urls = len(urls)
    total_batches = (total_urls + batch_size - 1) // batch_size  # Ceiling division
    
    logger.info(f"Processing {total_urls} URLs in {total_batches} batches")
    
    # Load progress from checkpoint if resuming
    start_batch = 0
    processed_urls = set()
    
    if resume:
        progress_data = load_checkpoint("progress")
        if progress_data:
            if "processed_urls" in progress_data:
                processed_urls = set(progress_data["processed_urls"])
                logger.info(f"Resuming: {len(processed_urls)} URLs already processed")
            if "current_batch" in progress_data:
                start_batch = progress_data["current_batch"]
                logger.info(f"Resuming from batch {start_batch}")
        else:
            # Initialize an empty progress checkpoint if it doesn't exist
            logger.info("No progress checkpoint found, initializing new one")
            progress_data = {
                "current_batch": 0,
                "processed_urls": [],
                "successful": 0,
                "failed": 0,
                "total": len(urls),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            save_checkpoint(progress_data, "progress")
    
    # Filter out already processed URLs
    if processed_urls:
        pending_urls = [url for url in urls if url not in processed_urls]
        logger.info(f"{len(pending_urls)} URLs remaining to process")
    else:
        pending_urls = urls
    
    # Process in batches
    successful_total = 0
    failed_total = 0
    current_batch = start_batch
    
    for i in range(0, len(pending_urls), batch_size):
        batch_urls = pending_urls[i:i+batch_size]
        
        logger.info(f"Processing batch {current_batch + 1}/{total_batches}")
        
        # Process batch with all options
        successful, failed = process_batch(
            batch_urls, 
            current_batch + 1, 
            batch_metrics=batch_metrics,
            with_ocr=with_ocr,
            ocr_quality=ocr_quality,
            max_workers=max_workers
        )
        
        successful_total += successful
        failed_total += failed
        
        # Update progress checkpoint
        processed_urls.update(batch_urls)
        progress_data = {
            "current_batch": current_batch + 1,
            "processed_urls": list(processed_urls),
            "successful": successful_total,
            "failed": failed_total,
            "total": total_urls,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        save_checkpoint(progress_data, "progress")
        
        current_batch += 1
        
        # Log progress
        completed = successful_total + failed_total
        progress_percent = (completed / total_urls) * 100
        logger.info(f"Progress: {progress_percent:.1f}% - {completed}/{total_urls} files processed")
    
    # Generate overall report if batch metrics available
    if batch_metrics:
        batch_metrics.generate_overall_report()
    
    logger.info(f"Full-scale processing complete: {successful_total} successful, {failed_total} failed, {total_urls} total")
    
    return successful_total, failed_total, total_urls


def _process_all_files_optimized(urls=None, resume=True):
    """
    Process all files using the optimized LargeScaleProcessor.
    
    Args:
        urls (list): List of URLs to process. If None, will try to load from checkpoint.
        resume (bool): Whether to resume from checkpoint if available.
        
    Returns:
        tuple: (successful_count, failed_count, total_count)
    """
    try:
        # Import necessary modules
        from src.optimization import LargeScaleProcessor, OptimizationConfig
        
        logger.info("Starting optimized full-scale processing")
        
        # If no URLs provided, try to load from checkpoint
        if urls is None:
            checkpoint_data = load_checkpoint("urls")
            if checkpoint_data and "pdf_urls" in checkpoint_data:
                urls = checkpoint_data["pdf_urls"]
                logger.info(f"Loaded {len(urls)} URLs from checkpoint")
            else:
                logger.error("No URL list provided and no checkpoint found")
                return 0, 0, 0
        
        # Create directories
        _create_directories()
        
        # Set up optimization config
        config = OptimizationConfig()
        config.MAX_WORKERS = min(20, os.cpu_count() * 2 if os.cpu_count() else 8)  # Adaptive based on CPU cores
        config.BATCH_SIZE = 50  # Default batch size
        
        # Initialize processor
        processor = LargeScaleProcessor(config)
        
        # Process all URLs
        total_urls = len(urls)
        logger.info(f"Processing {total_urls} URLs with optimized processor")
        
        # Process with optimized settings
        successful, failed = processor.process_urls(urls, resume=resume)
        
        logger.info(f"Optimized full-scale processing complete: {successful} successful, {failed} failed, {total_urls} total")
        
        return successful, failed, total_urls
        
    except ImportError as e:
        logger.error(f"Failed to import optimization modules: {e}")
        logger.info("Falling back to basic batch processing")
        return process_all_files(urls, resume)
    
    except Exception as e:
        logger.error(f"Error during optimized processing: {e}")
        logger.info("Falling back to basic batch processing")
        return process_all_files(urls, resume)


def _create_directories():
    """Create necessary directories for batch processing."""
    os.makedirs("pdfs", exist_ok=True)
    os.makedirs("markdown", exist_ok=True)
    os.makedirs("json", exist_ok=True)
    os.makedirs("lite_llm", exist_ok=True)
    os.makedirs(".checkpoints", exist_ok=True)
    logger.info("Created output directories for batch processing")
