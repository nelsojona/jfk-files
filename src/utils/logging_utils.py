#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logging utilities for JFK Files Scraper.

This module provides centralized logging configuration, error tracking,
and performance metrics reporting.
"""

import logging
import sys
import traceback
import time
from datetime import datetime
from functools import wraps


# Custom exceptions for specific error scenarios
class ScraperError(Exception):
    """Base exception class for all scraper-related errors."""
    pass


class DownloadError(ScraperError):
    """Exception raised for errors during PDF download."""
    pass


class ConversionError(ScraperError):
    """Exception raised for errors during file conversion."""
    pass


class CheckpointError(ScraperError):
    """Exception raised for errors related to checkpointing."""
    pass


class StorageError(ScraperError):
    """Exception raised for errors during storage operations."""
    pass


class RareFormatError(ScraperError):
    """Exception raised for errors related to unusual document formats."""
    pass


# Initialize error tracking metrics
_error_counts = {
    "scraping": 0,
    "download": 0,
    "pdf_to_markdown": 0,
    "markdown_to_json": 0,
    "storage": 0,
    "checkpoint": 0,
    "general": 0
}

# Initialize performance metrics
_performance_metrics = {
    "start_time": None,  # Will be set at runtime
    "processed_files": 0,
    "successful_files": 0,
    "failed_files": 0,
    "total_download_size": 0,
    "download_times": [],
    "conversion_times": []
}


def configure_logging(log_level=logging.INFO, log_file="jfk_scraper.log"):
    """
    Configure logging with enhanced formatting and multiple handlers.
    
    Args:
        log_level: Logging level to use
        log_file: Path to the log file
        
    Returns:
        logger: Configured logger instance
    """
    # Create formatter with more detailed information
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler for all logs
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    
    # Console handler for INFO and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Error file handler for ERROR and CRITICAL
    error_handler = logging.FileHandler("jfk_scraper_errors.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add the handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(error_handler)
    
    # Create application logger
    logger = logging.getLogger("jfk_scraper")
    
    # Log startup information
    logger.info("=" * 80)
    logger.info("JFK Files Scraper Starting")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Working directory: {sys.path[0]}")
    logger.info(f"Log level: {logging.getLevelName(log_level)}")
    logger.info("=" * 80)
    
    return logger


def track_error(category, error, url=None, fatal=False):
    """
    Track an error in the specified category and log it appropriately.
    
    Args:
        category (str): The category of the error
        error (Exception): The exception that was raised
        url (str, optional): The URL or resource being processed
        fatal (bool): Whether this is a fatal error that should stop processing
        
    Returns:
        bool: True if processing should continue, False if it should stop
    """
    logger = logging.getLogger("jfk_scraper")
    
    if category in _error_counts:
        _error_counts[category] += 1
    else:
        _error_counts["general"] += 1
    
    # Create context for the error
    context = f" while processing {url}" if url else ""
    
    # Get traceback info
    tb_info = traceback.format_exc()
    
    # Log at appropriate level
    if fatal:
        logger.critical(f"FATAL ERROR in {category}{context}: {error}\n{tb_info}")
        return False  # Stop processing
    else:
        logger.error(f"ERROR in {category}{context}: {error}\n{tb_info}")
        return True   # Continue processing


def log_metrics():
    """Log the current error metrics and processing statistics."""
    logger = logging.getLogger("jfk_scraper")
    
    logger.info("=" * 80)
    logger.info("PERFORMANCE METRICS:")
    
    # Calculate elapsed time
    if _performance_metrics["start_time"] is not None:
        elapsed_time = time.time() - _performance_metrics["start_time"]
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        logger.info(f"Total runtime: {int(hours)}h {int(minutes)}m {seconds:.2f}s")
    else:
        logger.info("Total runtime: Not available (start time not set)")
    logger.info(f"Files processed: {_performance_metrics['processed_files']}")
    logger.info(f"Files successful: {_performance_metrics['successful_files']}")
    logger.info(f"Files failed: {_performance_metrics['failed_files']}")
    
    # Calculate processing rate
    if _performance_metrics["start_time"] is not None and time.time() - _performance_metrics["start_time"] > 0:
        elapsed_time = time.time() - _performance_metrics["start_time"]
        rate = _performance_metrics["processed_files"] / elapsed_time
        logger.info(f"Processing rate: {rate:.2f} files/second")
    
    # Calculate average download time if we have data
    if _performance_metrics["download_times"]:
        avg_download_time = sum(_performance_metrics["download_times"]) / len(_performance_metrics["download_times"])
        logger.info(f"Average download time: {avg_download_time:.2f} seconds")
    
    # Calculate average conversion time if we have data
    if _performance_metrics["conversion_times"]:
        avg_conversion_time = sum(_performance_metrics["conversion_times"]) / len(_performance_metrics["conversion_times"])
        logger.info(f"Average conversion time: {avg_conversion_time:.2f} seconds")
    
    # Log total download size
    total_mb = _performance_metrics["total_download_size"] / (1024 * 1024)
    logger.info(f"Total download size: {total_mb:.2f} MB")
    
    logger.info("-" * 80)
    logger.info("ERROR METRICS:")
    for category, count in _error_counts.items():
        if count > 0:
            logger.info(f"  {category.upper()}: {count} errors")
    logger.info("=" * 80)


def retry_with_backoff(max_retries=3, initial_delay=1, backoff_factor=2, exceptions=(Exception,)):
    """
    Decorator for retrying a function with exponential backoff.
    
    Args:
        max_retries (int): Maximum number of retries
        initial_delay (int): Initial delay in seconds
        backoff_factor (int): Factor to multiply delay with after each retry
        exceptions (tuple): Exceptions to catch and retry on
        
    Returns:
        decorator: Retry decorator
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger("jfk_scraper")
            retry = 0
            delay = initial_delay
            
            while retry < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retry += 1
                    if retry >= max_retries:
                        logger.error(f"Failed after {max_retries} retries: {func.__name__}")
                        raise
                    
                    logger.warning(f"Retry {retry}/{max_retries} for {func.__name__} after error: {e}")
                    logger.warning(f"Waiting {delay} seconds before retry")
                    time.sleep(delay)
                    delay *= backoff_factor
            
            # Should not reach here, but just in case
            return func(*args, **kwargs)
        return wrapper
    return decorator


def update_performance_metrics(**metrics):
    """
    Update performance metrics with new values.
    
    Args:
        **metrics: Keyword arguments with metrics to update
    """
    for key, value in metrics.items():
        if key in _performance_metrics:
            if isinstance(_performance_metrics[key], list):
                if isinstance(value, list):
                    _performance_metrics[key].extend(value)
                else:
                    _performance_metrics[key].append(value)
            elif isinstance(_performance_metrics[key], int) or isinstance(_performance_metrics[key], float):
                _performance_metrics[key] += value
            else:
                _performance_metrics[key] = value