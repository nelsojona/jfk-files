"""
JFK Files Scraper utility modules.

This package contains utility modules for the JFK Files Scraper,
including file conversion, logging, web scraping, and batch processing.
"""

from src.utils.logging_utils import (
    configure_logging, log_metrics, update_performance_metrics,
    track_error, retry_with_backoff, 
    ScraperError, DownloadError, ConversionError, CheckpointError, StorageError, RareFormatError
)

from src.utils.checkpoint_utils import (
    save_checkpoint, load_checkpoint, create_directories
)

from src.utils.download_utils import download_pdf, download_file
from src.utils.conversion_utils import pdf_to_markdown, markdown_to_json
from src.utils.pdf_utils import is_scanned_pdf, repair_document, detect_document_format
from src.utils.scrape_utils import scrape_jfk_files
from src.utils.batch_utils import process_file, process_batch, process_all_files

__all__ = [
    'configure_logging', 'log_metrics', 'update_performance_metrics',
    'track_error', 'retry_with_backoff',
    'ScraperError', 'DownloadError', 'ConversionError', 'CheckpointError', 'StorageError', 'RareFormatError',
    'save_checkpoint', 'load_checkpoint', 'create_directories',
    'download_pdf', 'download_file',
    'pdf_to_markdown', 'markdown_to_json',
    'is_scanned_pdf', 'repair_document', 'detect_document_format',
    'scrape_jfk_files',
    'process_file', 'process_batch', 'process_all_files'
]