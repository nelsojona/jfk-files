#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OPT-3: Optimize for full-scale processing (all 1,123 files)

This module enhances the JFK Files Scraper for processing all 1,123 files efficiently by:
1. Implementing advanced threading strategies
2. Adding resource monitoring and adaptive throttling
3. Creating enhanced checkpointing mechanisms
4. Optimizing memory usage during large-scale processing
"""

import os
import sys
import time
import signal
import psutil
import threading
import queue
import json
import logging
import pickle
import hashlib
import concurrent.futures
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to python path to import from jfk_scraper.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import required functions from jfk_scraper
from jfk_scraper import (
    logger, process_file, create_directories, track_error, 
    performance_metrics, error_counts, save_checkpoint, load_checkpoint
)

# Configure constants for optimization
class OptimizationConfig:
    """Configuration settings for optimization."""
    # Threading settings
    MAX_WORKERS = 10  # Maximum number of worker threads
    MIN_WORKERS = 2   # Minimum number of worker threads
    INITIAL_WORKERS = 5  # Initial number of worker threads
    
    # Rate limiting and throttling
    BASE_RATE_LIMIT = 0.5  # Base delay between operations (seconds)
    MIN_RATE_LIMIT = 0.2   # Minimum delay (seconds)
    MAX_RATE_LIMIT = 2.0   # Maximum delay (seconds)
    
    # Resource thresholds
    CPU_THRESHOLD_HIGH = 80  # CPU percentage to trigger throttling
    CPU_THRESHOLD_LOW = 40   # CPU percentage to trigger acceleration
    MEM_THRESHOLD_HIGH = 75  # Memory percentage to trigger throttling
    MEM_THRESHOLD_LOW = 50   # Memory percentage to trigger acceleration
    
    # Checkpointing
    CHECKPOINT_INTERVAL = 10  # Files processed between checkpoints
    CHECKPOINT_TIME = 300     # Time between checkpoints (seconds)
    
    # Batching
    BATCH_SIZE = 50  # Number of files to process in a batch
    
    # Retry settings
    MAX_RETRIES = 3  # Maximum number of retries for failed downloads
    RETRY_DELAY = 5  # Delay between retries (seconds)
    
    # Performance monitoring
    MONITOR_INTERVAL = 10  # Seconds between resource usage checks
    
    # Emergency handling
    MAX_ERRORS_BEFORE_PAUSE = 5  # Maximum consecutive errors before pausing
    PAUSE_DURATION = 60  # Duration to pause after too many errors (seconds)

# Class for adaptive thread pool management
class AdaptiveThreadPool:
    """Thread pool that adapts to system load and processing metrics."""
    
    def __init__(self, config=None):
        """Initialize thread pool with configuration settings."""
        self.config = config or OptimizationConfig()
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.INITIAL_WORKERS
        )
        self.active_workers = self.config.INITIAL_WORKERS
        self.rate_limit = self.config.BASE_RATE_LIMIT
        self.shutdown_requested = False
        self.lock = threading.Lock()
        self.pause_event = threading.Event()
        self.pause_event.set()  # Not paused initially
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info(f"AdaptiveThreadPool initialized with {self.active_workers} workers")
        logger.info(f"Rate limit set to {self.rate_limit} seconds")
    
    def _monitor_resources(self):
        """Continuously monitor system resources and adjust thread pool accordingly."""
        consecutive_high_load = 0
        consecutive_low_load = 0
        
        while not self.shutdown_requested:
            try:
                # Get system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                mem_percent = psutil.virtual_memory().percent
                
                # Log current resource usage
                logger.debug(f"System resources: CPU: {cpu_percent}%, Memory: {mem_percent}%")
                
                # Adapt based on CPU usage
                if cpu_percent > self.config.CPU_THRESHOLD_HIGH:
                    consecutive_high_load += 1
                    consecutive_low_load = 0
                elif cpu_percent < self.config.CPU_THRESHOLD_LOW:
                    consecutive_low_load += 1
                    consecutive_high_load = 0
                else:
                    consecutive_high_load = 0
                    consecutive_low_load = 0
                
                # Take action if consistently high or low load
                if consecutive_high_load >= 3:
                    self._throttle_processing()
                    consecutive_high_load = 0
                elif consecutive_low_load >= 3:
                    self._accelerate_processing()
                    consecutive_low_load = 0
                
                # Additional throttling based on memory usage
                if mem_percent > self.config.MEM_THRESHOLD_HIGH:
                    self._throttle_processing()
                
                # Sleep before next check
                time.sleep(self.config.MONITOR_INTERVAL)
            
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
                time.sleep(self.config.MONITOR_INTERVAL)
    
    def _throttle_processing(self):
        """Reduce resource usage by throttling processing."""
        with self.lock:
            # Only throttle if we're not already at minimum
            if (self.active_workers > self.config.MIN_WORKERS or 
                    self.rate_limit < self.config.MAX_RATE_LIMIT):
                
                # Reduce workers if possible
                if self.active_workers > self.config.MIN_WORKERS:
                    new_workers = max(self.config.MIN_WORKERS, self.active_workers - 1)
                    logger.info(f"Throttling: Reducing workers from {self.active_workers} to {new_workers}")
                    self.active_workers = new_workers
                    
                    # We can't directly resize ThreadPoolExecutor
                    # We'll let natural worker completion handle the reduction
                
                # Increase rate limit
                new_rate = min(self.config.MAX_RATE_LIMIT, self.rate_limit * 1.5)
                logger.info(f"Throttling: Increasing rate limit from {self.rate_limit} to {new_rate}")
                self.rate_limit = new_rate
    
    def _accelerate_processing(self):
        """Increase resource usage to accelerate processing."""
        with self.lock:
            # Only accelerate if we're not already at maximum
            if (self.active_workers < self.config.MAX_WORKERS or 
                    self.rate_limit > self.config.MIN_RATE_LIMIT):
                
                # Increase workers if possible
                if self.active_workers < self.config.MAX_WORKERS:
                    new_workers = min(self.config.MAX_WORKERS, self.active_workers + 1)
                    logger.info(f"Accelerating: Increasing workers from {self.active_workers} to {new_workers}")
                    self.active_workers = new_workers
                    
                    # We can't directly resize ThreadPoolExecutor
                    # We'll utilize the new worker count in submit operations
                
                # Decrease rate limit
                new_rate = max(self.config.MIN_RATE_LIMIT, self.rate_limit / 1.5)
                logger.info(f"Accelerating: Decreasing rate limit from {self.rate_limit} to {new_rate}")
                self.rate_limit = new_rate
    
    def submit(self, fn, *args, **kwargs):
        """Submit a task to the thread pool with adaptive rate limiting."""
        # Wait for any active pause to end
        self.pause_event.wait()
        
        # Apply rate limiting
        time.sleep(self.rate_limit)
        
        # Submit task only if we haven't reached maximum active workers
        with self.lock:
            future = self.executor.submit(fn, *args, **kwargs)
            return future
    
    def pause_processing(self, duration=None):
        """Pause processing for a specified duration or until resumed."""
        duration = duration or self.config.PAUSE_DURATION
        logger.info(f"Pausing processing for {duration} seconds")
        self.pause_event.clear()
        
        # Schedule automatic resume after duration
        threading.Timer(duration, self.resume_processing).start()
    
    def resume_processing(self):
        """Resume processing after a pause."""
        logger.info("Resuming processing")
        self.pause_event.set()
    
    def shutdown(self):
        """Shutdown the thread pool."""
        logger.info("Shutting down Adaptive Thread Pool")
        self.shutdown_requested = True
        self.executor.shutdown(wait=True)
        logger.info("Thread pool shut down successfully")

# Enhanced checkpointing system for large-scale processing
class EnhancedCheckpointManager:
    """Manages checkpoints for resumable large-scale processing."""
    
    def __init__(self, config=None, base_dir=".checkpoints"):
        """Initialize checkpoint manager with configuration settings."""
        self.config = config or OptimizationConfig()
        self.base_dir = base_dir
        self.last_checkpoint_time = time.time()
        self.processed_since_checkpoint = 0
        self.lock = threading.Lock()
        
        # Create checkpoint directory
        os.makedirs(self.base_dir, exist_ok=True)
        
        logger.info(f"EnhancedCheckpointManager initialized with {self.config.CHECKPOINT_INTERVAL} file interval")
        logger.info(f"Time-based checkpoints every {self.config.CHECKPOINT_TIME} seconds")
    
    def should_checkpoint(self):
        """Determine if a checkpoint should be created based on time or count."""
        with self.lock:
            current_time = time.time()
            time_elapsed = current_time - self.last_checkpoint_time
            
            # Check if either condition is met
            if (self.processed_since_checkpoint >= self.config.CHECKPOINT_INTERVAL or
                    time_elapsed >= self.config.CHECKPOINT_TIME):
                return True
            return False
    
    def create_checkpoint(self, data, name="enhanced"):
        """Create a checkpoint with the provided data."""
        with self.lock:
            # Add enhanced metadata to the checkpoint
            data["checkpoint_metadata"] = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "checkpoint_type": "time" if time.time() - self.last_checkpoint_time >= self.config.CHECKPOINT_TIME else "count"
            }
            
            # Create a hash of the main parameters to ensure consistency
            if "params" in data:
                hash_input = str(sorted([(k, str(v)) for k, v in data["params"].items()]))
                param_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
                data["param_hash"] = param_hash
                checkpoint_file = f"{self.base_dir}/{name}_{param_hash}.checkpoint"
            else:
                checkpoint_file = f"{self.base_dir}/{name}.checkpoint"
            
            # Also create a timestamped version for history
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            history_file = f"{self.base_dir}/{name}_{timestamp}.history"
            
            # Save to temporary files first
            temp_checkpoint_file = f"{checkpoint_file}.temp"
            temp_history_file = f"{history_file}.temp"
            
            try:
                # Serialize and save the checkpoint data
                with open(temp_checkpoint_file, 'wb') as f:
                    pickle.dump(data, f)
                
                # Also save the history version
                with open(temp_history_file, 'wb') as f:
                    pickle.dump(data, f)
                
                # Rename to final filenames
                os.replace(temp_checkpoint_file, checkpoint_file)
                os.replace(temp_history_file, history_file)
                
                # Reset counters
                self.last_checkpoint_time = time.time()
                self.processed_since_checkpoint = 0
                
                logger.info(f"Enhanced checkpoint saved: {checkpoint_file}")
                return checkpoint_file
            
            except Exception as e:
                logger.error(f"Error saving enhanced checkpoint: {e}")
                return None
    
    def record_processed(self):
        """Record that another file has been processed."""
        with self.lock:
            self.processed_since_checkpoint += 1
    
    def load_latest_checkpoint(self, name="enhanced", param_hash=None):
        """Load the latest checkpoint."""
        try:
            # Find the most recent checkpoint file
            if param_hash:
                checkpoint_pattern = f"{name}_{param_hash}.checkpoint"
                checkpoint_file = os.path.join(self.base_dir, checkpoint_pattern)
                if not os.path.exists(checkpoint_file):
                    logger.info(f"No checkpoint found with hash {param_hash}")
                    return None
            else:
                # Find all checkpoints with this name prefix
                checkpoint_pattern = f"{name}_*.checkpoint"
                checkpoint_files = list(Path(self.base_dir).glob(checkpoint_pattern))
                
                if not checkpoint_files:
                    # Try without hash
                    checkpoint_file = os.path.join(self.base_dir, f"{name}.checkpoint")
                    if not os.path.exists(checkpoint_file):
                        logger.info(f"No checkpoint found with name {name}")
                        return None
                else:
                    # Use the most recent checkpoint by modification time
                    checkpoint_file = str(sorted(checkpoint_files, key=os.path.getmtime)[-1])
            
            # Load the checkpoint
            with open(checkpoint_file, 'rb') as f:
                data = pickle.load(f)
            
            logger.info(f"Loaded enhanced checkpoint: {checkpoint_file}")
            
            # Verify checkpoint integrity
            if "checkpoint_metadata" in data:
                metadata = data["checkpoint_metadata"]
                logger.info(f"Checkpoint created at: {metadata.get('timestamp', 'unknown')}")
                logger.info(f"Checkpoint type: {metadata.get('checkpoint_type', 'unknown')}")
            else:
                logger.warning("Loaded checkpoint has no metadata - may be from older version")
            
            return data
        
        except Exception as e:
            logger.error(f"Error loading enhanced checkpoint: {e}")
            return None
    
    def prune_old_checkpoints(self, max_age_days=7, max_history=10):
        """Remove old checkpoint history files."""
        try:
            # Find all history files
            history_files = list(Path(self.base_dir).glob("*.history"))
            
            # Group by prefix (name)
            history_by_name = {}
            for history_file in history_files:
                name = history_file.name.split('_')[0]
                if name not in history_by_name:
                    history_by_name[name] = []
                history_by_name[name].append(history_file)
            
            # Process each group
            for name, files in history_by_name.items():
                # Sort by modification time (newest first)
                sorted_files = sorted(files, key=os.path.getmtime, reverse=True)
                
                # Keep the newest max_history files and delete the rest
                for old_file in sorted_files[max_history:]:
                    # Check age against max_age_days
                    file_mtime = os.path.getmtime(old_file)
                    file_age = datetime.now() - datetime.fromtimestamp(file_mtime)
                    
                    if file_age.days >= max_age_days:
                        os.remove(old_file)
                        logger.debug(f"Removed old checkpoint history: {old_file}")
            
            logger.info(f"Pruned checkpoint history files older than {max_age_days} days")
            
        except Exception as e:
            logger.error(f"Error pruning old checkpoints: {e}")

# Memory-optimized file processor for large-scale operations
class LargeScaleProcessor:
    """Handles processing of large file sets with memory optimization."""
    
    def __init__(self, config=None):
        """Initialize large-scale processor with configuration settings."""
        self.config = config or OptimizationConfig()
        self.thread_pool = AdaptiveThreadPool(self.config)
        self.checkpoint_manager = EnhancedCheckpointManager(self.config)
        self.processing_stats = {
            "start_time": time.time(),
            "total_files": 0,
            "processed_files": 0,
            "successful_files": 0,
            "failed_files": 0,
            "skipped_files": 0,
            "in_progress_files": 0
        }
        self.futures = {}  # Track futures by URL
        self.url_status = {}  # Track status of each URL
        self.lock = threading.Lock()
        self.error_tracking = {"consecutive_errors": 0, "last_error_time": None}
        
        # Register signal handlers
        self._register_signal_handlers()
        
        logger.info("Large Scale Processor initialized")
    
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        def signal_handler(sig, frame):
            logger.warning(f"Received signal {sig}, initiating graceful shutdown...")
            self.shutdown()
            sys.exit(0)
        
        # Register for common termination signals
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination request
        
        # On Unix-like systems, also register SIGHUP
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)  # Terminal closed
    
    def _process_file_wrapper(self, url):
        """Wrapper around process_file to handle tracking and checkpointing."""
        try:
            # Mark as in-progress
            with self.lock:
                self.url_status[url] = "in_progress"
                self.processing_stats["in_progress_files"] += 1
            
            # Process the file
            logger.info(f"Processing {url}")
            success = process_file(url)
            
            # Update tracking based on result
            with self.lock:
                self.processing_stats["processed_files"] += 1
                self.processing_stats["in_progress_files"] -= 1
                
                if success:
                    self.url_status[url] = "completed"
                    self.processing_stats["successful_files"] += 1
                    self.error_tracking["consecutive_errors"] = 0
                else:
                    self.url_status[url] = "failed"
                    self.processing_stats["failed_files"] += 1
                    self.error_tracking["consecutive_errors"] += 1
                    self.error_tracking["last_error_time"] = time.time()
                
                # Check if we should checkpoint
                self.checkpoint_manager.record_processed()
                if self.checkpoint_manager.should_checkpoint():
                    self._create_processing_checkpoint()
                    
                # Check if we need to pause due to too many errors
                if self.error_tracking["consecutive_errors"] >= self.config.MAX_ERRORS_BEFORE_PAUSE:
                    logger.warning(f"Detected {self.error_tracking['consecutive_errors']} consecutive errors, pausing processing")
                    self.thread_pool.pause_processing()
                    self.error_tracking["consecutive_errors"] = 0
            
            return success
            
        except Exception as e:
            logger.error(f"Error in process_file_wrapper for {url}: {e}")
            
            with self.lock:
                self.url_status[url] = "error"
                self.processing_stats["failed_files"] += 1
                self.processing_stats["in_progress_files"] -= 1
                self.error_tracking["consecutive_errors"] += 1
                self.error_tracking["last_error_time"] = time.time()
                
                # Handle consecutive errors
                if self.error_tracking["consecutive_errors"] >= self.config.MAX_ERRORS_BEFORE_PAUSE:
                    logger.warning(f"Detected {self.error_tracking['consecutive_errors']} consecutive errors, pausing processing")
                    self.thread_pool.pause_processing()
                    self.error_tracking["consecutive_errors"] = 0
            
            return False
    
    def _create_processing_checkpoint(self):
        """Create a checkpoint of the current processing state."""
        checkpoint_data = {
            "url_status": self.url_status.copy(),
            "processing_stats": self.processing_stats.copy(),
            "params": {
                "max_workers": self.config.MAX_WORKERS,
                "rate_limit": self.config.BASE_RATE_LIMIT
            }
        }
        
        # Add performance metrics and error counts
        checkpoint_data["performance_metrics"] = performance_metrics.copy()
        checkpoint_data["error_counts"] = error_counts.copy()
        
        # Create the checkpoint
        self.checkpoint_manager.create_checkpoint(checkpoint_data, "large_scale_processing")
    
    def resume_from_checkpoint(self):
        """Resume processing from the latest checkpoint."""
        checkpoint_data = self.checkpoint_manager.load_latest_checkpoint("large_scale_processing")
        
        if checkpoint_data:
            logger.info("Resuming from checkpoint")
            
            # Restore URL status
            if "url_status" in checkpoint_data:
                self.url_status = checkpoint_data["url_status"]
                logger.info(f"Restored status for {len(self.url_status)} URLs")
            
            # Restore processing stats
            if "processing_stats" in checkpoint_data:
                # Don't restore start_time or in_progress counts
                checkpoint_stats = checkpoint_data["processing_stats"]
                self.processing_stats["processed_files"] = checkpoint_stats.get("processed_files", 0)
                self.processing_stats["successful_files"] = checkpoint_stats.get("successful_files", 0)
                self.processing_stats["failed_files"] = checkpoint_stats.get("failed_files", 0)
                self.processing_stats["skipped_files"] = checkpoint_stats.get("skipped_files", 0)
                self.processing_stats["total_files"] = checkpoint_stats.get("total_files", 0)
                
                logger.info(f"Restored processing stats: {self.processing_stats['processed_files']} processed, "
                           f"{self.processing_stats['successful_files']} successful")
            
            # Restore performance metrics
            if "performance_metrics" in checkpoint_data:
                for key, value in checkpoint_data["performance_metrics"].items():
                    if key in performance_metrics and key != "start_time":
                        performance_metrics[key] = value
            
            # Restore error counts
            if "error_counts" in checkpoint_data:
                for category, count in checkpoint_data["error_counts"].items():
                    if category in error_counts:
                        error_counts[category] = count
            
            return True
        
        else:
            logger.info("No checkpoint found, starting fresh")
            return False
    
    def process_urls(self, urls, resume=True):
        """Process a list of URLs with optimization for large-scale operations."""
        try:
            # Store total file count
            self.processing_stats["total_files"] = len(urls)
            
            # Initialize URL status if not resuming
            if not resume or not self.resume_from_checkpoint():
                self.url_status = {url: "pending" for url in urls}
            
            # Log initial state
            completed = sum(1 for status in self.url_status.values() if status == "completed")
            pending = sum(1 for status in self.url_status.values() if status == "pending")
            failed = sum(1 for status in self.url_status.values() if status == "failed")
            
            logger.info(f"Starting large-scale processing with {self.processing_stats['total_files']} total files")
            logger.info(f"Initial state: {completed} completed, {pending} pending, {failed} failed")
            
            # Create a processing queue for pending URLs
            url_queue = queue.Queue()
            for url, status in self.url_status.items():
                if status == "pending":
                    url_queue.put(url)
            
            # Process URLs until queue is empty
            active_futures = set()
            max_concurrent = self.thread_pool.active_workers
            
            while not url_queue.empty() or active_futures:
                # Submit new tasks if capacity available
                while len(active_futures) < max_concurrent and not url_queue.empty():
                    url = url_queue.get()
                    future = self.thread_pool.submit(self._process_file_wrapper, url)
                    self.futures[url] = future
                    active_futures.add(future)
                
                # Check for completed futures
                done, active_futures = concurrent.futures.wait(
                    active_futures, 
                    timeout=1.0,
                    return_when=concurrent.futures.FIRST_COMPLETED
                )
                
                # Update max_concurrent based on adaptive thread pool
                max_concurrent = self.thread_pool.active_workers
                
                # Log progress periodically
                if not url_queue.empty() and len(active_futures) > 0:
                    completed = sum(1 for status in self.url_status.values() if status == "completed")
                    pending = sum(1 for status in self.url_status.values() if status == "pending") + url_queue.qsize()
                    failed = sum(1 for status in self.url_status.values() if status == "failed")
                    in_progress = sum(1 for status in self.url_status.values() if status == "in_progress")
                    
                    time_elapsed = time.time() - self.processing_stats["start_time"]
                    files_processed = completed + failed
                    
                    # Calculate processing rate and ETA
                    if files_processed > 0 and time_elapsed > 0:
                        rate = files_processed / time_elapsed
                        remaining_files = pending + in_progress
                        eta_seconds = remaining_files / rate if rate > 0 else 0
                        eta = str(timedelta(seconds=int(eta_seconds)))
                        
                        # Calculate progress percentage
                        progress = (files_processed / self.processing_stats["total_files"]) * 100
                        
                        logger.info(f"Progress: {progress:.1f}% - {completed} completed, {pending} pending, "
                                   f"{failed} failed, {in_progress} in progress | "
                                   f"Rate: {rate:.2f} files/s | ETA: {eta}")
            
            # Final report
            completed = sum(1 for status in self.url_status.values() if status == "completed")
            failed = sum(1 for status in self.url_status.values() if status == "failed")
            total_processed = completed + failed
            
            if total_processed > 0:
                success_rate = (completed / total_processed) * 100
                logger.info(f"Processing complete: {completed}/{total_processed} successful ({success_rate:.1f}%)")
            else:
                logger.info("Processing complete: No files were processed")
            
            # Create final checkpoint
            self._create_processing_checkpoint()
            
            return completed, failed
            
        except Exception as e:
            logger.error(f"Error in large-scale processing: {e}")
            self._create_processing_checkpoint()  # Emergency checkpoint
            raise
    
    def shutdown(self):
        """Shutdown the processor and clean up resources."""
        logger.info("Shutting down Large Scale Processor")
        
        # Create final checkpoint
        self._create_processing_checkpoint()
        
        # Shutdown thread pool
        try:
            self.thread_pool.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down thread pool: {e}")
        
        # Report final metrics
        self._report_final_metrics()
    
    def _report_final_metrics(self):
        """Report final processing metrics."""
        logger.info("=" * 80)
        logger.info("FINAL PROCESSING METRICS")
        logger.info("=" * 80)
        
        # Calculate time stats
        time_elapsed = time.time() - self.processing_stats["start_time"]
        hours, remainder = divmod(time_elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Log time information
        logger.info(f"Total runtime: {int(hours)}h {int(minutes)}m {seconds:.2f}s")
        
        # Log processing stats
        logger.info(f"Total files: {self.processing_stats['total_files']}")
        logger.info(f"Files processed: {self.processing_stats['processed_files']}")
        logger.info(f"Files successful: {self.processing_stats['successful_files']}")
        logger.info(f"Files failed: {self.processing_stats['failed_files']}")
        logger.info(f"Files skipped: {self.processing_stats['skipped_files']}")
        
        # Calculate and log success rate
        if self.processing_stats['processed_files'] > 0:
            success_rate = (self.processing_stats['successful_files'] / 
                           self.processing_stats['processed_files']) * 100
            logger.info(f"Success rate: {success_rate:.2f}%")
        
        # Calculate and log processing rate
        if time_elapsed > 0:
            rate = self.processing_stats['processed_files'] / time_elapsed
            logger.info(f"Processing rate: {rate:.2f} files/second")
        
        # Log error information
        for category, count in error_counts.items():
            if count > 0:
                logger.info(f"Error category '{category}': {count} occurrences")
        
        logger.info("=" * 80)

# Main function to optimize for full-scale processing
def optimize_full_scale_processing(url_list=None, resume=True, config=None):
    """
    Optimize and process a full-scale list of URLs (all 1,123 files).
    
    Args:
        url_list (list): List of URLs to process. If None, will try to load from checkpoint.
        resume (bool): Whether to resume from a checkpoint if available.
        config (OptimizationConfig): Custom configuration settings for optimization.
        
    Returns:
        tuple: (successful_files, failed_files) counts
    """
    # Use default config if none provided
    config = config or OptimizationConfig()
    
    # Initialize processor
    processor = LargeScaleProcessor(config)
    
    try:
        # If no URL list provided, try to load from checkpoint
        if url_list is None:
            checkpoint_data = load_checkpoint("urls")
            if checkpoint_data and "pdf_urls" in checkpoint_data:
                url_list = checkpoint_data["pdf_urls"]
                logger.info(f"Loaded {len(url_list)} URLs from checkpoint")
            else:
                logger.error("No URL list provided and no checkpoint found")
                return 0, 0
        
        # Ensure we have directories for output
        create_directories()
        
        # Log start of large-scale processing
        logger.info(f"Starting optimized full-scale processing of {len(url_list)} files")
        logger.info(f"Maximum workers: {config.MAX_WORKERS}")
        logger.info(f"Base rate limit: {config.BASE_RATE_LIMIT} seconds")
        
        # Process all URLs with optimized settings
        successful, failed = processor.process_urls(url_list, resume=resume)
        
        # Log completion
        logger.info(f"Optimized full-scale processing complete: {successful} successful, {failed} failed")
        
        return successful, failed
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        processor.shutdown()
        return (processor.processing_stats.get("successful_files", 0),
                processor.processing_stats.get("failed_files", 0))
        
    except Exception as e:
        logger.error(f"Error during optimized processing: {e}")
        processor.shutdown()
        return (processor.processing_stats.get("successful_files", 0),
                processor.processing_stats.get("failed_files", 0))
    
    finally:
        try:
            processor.shutdown()
        except:
            pass
