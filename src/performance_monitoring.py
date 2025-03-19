#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OPT-4: Add performance monitoring

This module adds comprehensive performance monitoring to the JFK Files Scraper by:
1. Implementing detailed metrics collection
2. Providing real-time performance visualization
3. Creating performance reports and alerts
4. Enabling optimization recommendations based on historical data
"""

import os
import sys
import time
import json
import math
import logging
import datetime
import threading
import signal
import traceback
import argparse
import csv
import psutil
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server environments
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict, deque
from pathlib import Path

# Add parent directory to python path to import from jfk_scraper.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import required functions from jfk_scraper and optimization
from jfk_scraper import logger, performance_metrics, error_counts
try:
    # Optional import for advanced monitoring
    from src.optimization import OptimizationConfig
    OPTIMIZATION_AVAILABLE = True
except ImportError:
    OPTIMIZATION_AVAILABLE = False
    logger.warning("Optimization module not available, using basic monitoring only.")


# Performance Monitoring Configuration
class MonitoringConfig:
    """Configuration for performance monitoring."""
    
    # Data collection settings
    METRICS_INTERVAL = 5  # Seconds between metrics collection
    HISTORY_LENGTH = 1000  # Number of data points to keep in memory
    REPORT_INTERVAL = 300  # Seconds between reports (5 minutes)
    
    # Alerting thresholds
    CPU_ALERT_THRESHOLD = 85  # Alert when CPU usage exceeds this percentage
    MEMORY_ALERT_THRESHOLD = 80  # Alert when memory usage exceeds this percentage
    ERROR_RATE_THRESHOLD = 0.1  # Alert when error rate exceeds this value (10%)
    
    # File paths
    METRICS_DIR = "performance_metrics"
    CHARTS_DIR = os.path.join(METRICS_DIR, "charts")
    LOG_FILE = os.path.join(METRICS_DIR, "performance.log")
    CSV_FILE = os.path.join(METRICS_DIR, "metrics.csv")
    JSON_FILE = os.path.join(METRICS_DIR, "metrics.json")
    
    # Visualization settings
    CHART_DPI = 100
    CHART_WIDTH = 12
    CHART_HEIGHT = 8
    
    # Alert settings
    ALERT_COOLDOWN = 300  # Seconds between repeated alerts (5 minutes)
    ALERT_METHODS = ["log"]  # Available: "log", "file", "email"
    ALERT_EMAIL = ""  # Email address for alerts


class BatchMetrics:
    """Tracks and analyzes metrics for batch processing."""
    
    def __init__(self, batch_size=100):
        """Initialize batch metrics tracking."""
        self.batch_size = batch_size
        self.current_batch = 1
        self.batch_start_time = time.time()
        self.batch_metrics = []
        self.overall_start_time = time.time()
        
        # Create batch metrics directory
        os.makedirs("performance_metrics/batch_metrics", exist_ok=True)
    
    def start_batch(self, batch_number=None, files=None):
        """Start tracking a new batch."""
        if batch_number is not None:
            self.current_batch = batch_number
        
        self.batch_start_time = time.time()
        logger.info(f"Starting batch {self.current_batch} with {len(files) if files else self.batch_size} files")
        
        # Reset batch-specific metrics
        self.batch_metrics = {
            'batch_number': self.current_batch,
            'start_time': datetime.datetime.now().isoformat(),
            'files': files if files else [],
            'completed_files': 0,
            'failed_files': 0,
            'processing_times': [],
            'error_counts': defaultdict(int),
            'batch_size': len(files) if files else self.batch_size
        }
    
    def record_file_processed(self, file_path, success, processing_time, errors=None):
        """Record metrics for a processed file."""
        self.batch_metrics['processing_times'].append(processing_time)
        
        if success:
            self.batch_metrics['completed_files'] += 1
        else:
            self.batch_metrics['failed_files'] += 1
            
        # Track error types
        if errors:
            for error_type, _ in errors:
                self.batch_metrics['error_counts'][error_type] += 1
    
    def end_batch(self):
        """End the current batch and save metrics."""
        end_time = time.time()
        batch_duration = end_time - self.batch_start_time
        
        # Calculate batch statistics
        total_files = self.batch_metrics['completed_files'] + self.batch_metrics['failed_files']
        if total_files > 0:
            success_rate = self.batch_metrics['completed_files'] / total_files
        else:
            success_rate = 0
            
        if self.batch_metrics['processing_times']:
            avg_processing_time = sum(self.batch_metrics['processing_times']) / len(self.batch_metrics['processing_times'])
            max_processing_time = max(self.batch_metrics['processing_times'])
            min_processing_time = min(self.batch_metrics['processing_times'])
        else:
            avg_processing_time = max_processing_time = min_processing_time = 0
        
        # Add final metrics to the batch data
        self.batch_metrics.update({
            'end_time': datetime.datetime.now().isoformat(),
            'duration_seconds': batch_duration,
            'success_rate': success_rate,
            'avg_processing_time': avg_processing_time,
            'max_processing_time': max_processing_time,
            'min_processing_time': min_processing_time,
            'files_per_second': total_files / batch_duration if batch_duration > 0 else 0
        })
        
        # Calculate overall metrics
        overall_duration = end_time - self.overall_start_time
        hours, remainder = divmod(overall_duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Add overall progress metrics
        self.batch_metrics.update({
            'overall_duration_seconds': overall_duration,
            'overall_duration_formatted': f"{int(hours)}h {int(minutes)}m {int(seconds)}s",
            'estimated_batches_remaining': self._estimate_remaining_batches(),
            'estimated_completion_time': self._estimate_completion_time(batch_duration)
        })
        
        # Save batch metrics to JSON file
        metrics_file = f"performance_metrics/batch_metrics/batch_{self.current_batch}.json"
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(self.batch_metrics, f, indent=2)
        
        # Generate batch report
        self._generate_batch_report()
        
        # Log batch completion
        logger.info(f"Batch {self.current_batch} completed: "
                   f"{self.batch_metrics['completed_files']}/{total_files} files successful "
                   f"({self.batch_metrics['success_rate']*100:.1f}%) "
                   f"in {batch_duration:.1f} seconds "
                   f"({self.batch_metrics['files_per_second']:.2f} files/sec)")
        
        # Increment batch number for next batch
        self.current_batch += 1
        
        return self.batch_metrics
    
    def _estimate_remaining_batches(self):
        """Estimate number of batches remaining based on total expected files."""
        # This would need information about the total number of files expected
        # For JFK files, we know there are approximately 1,123 files
        total_expected_files = 1123
        
        # Calculate how many files we've processed so far
        files_processed_so_far = (self.current_batch - 1) * self.batch_size + self.batch_metrics['completed_files'] + self.batch_metrics['failed_files']
        
        # Calculate remaining files and batches
        remaining_files = max(0, total_expected_files - files_processed_so_far)
        remaining_batches = remaining_files / self.batch_size if self.batch_size > 0 else 0
        
        return math.ceil(remaining_batches)
    
    def _estimate_completion_time(self, batch_duration):
        """Estimate completion time based on current progress."""
        remaining_batches = self._estimate_remaining_batches()
        
        if remaining_batches <= 0:
            return "Completed"
        
        # Use batch_duration as a basis for estimation
        estimated_remaining_seconds = remaining_batches * batch_duration
        
        # Calculate estimated completion timestamp
        completion_time = datetime.datetime.now() + datetime.timedelta(seconds=estimated_remaining_seconds)
        
        return completion_time.isoformat()
    
    def _generate_batch_report(self):
        """Generate a visual report for the batch."""
        try:
            # Create a figure for batch metrics
            plt.figure(figsize=(12, 8))
            
            # Plot success vs failure
            plt.subplot(2, 2, 1)
            labels = ['Successful', 'Failed']
            sizes = [self.batch_metrics['completed_files'], self.batch_metrics['failed_files']]
            colors = ['#4CAF50', '#F44336']
            plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            plt.axis('equal')
            plt.title(f'Batch {self.current_batch} Success Rate')
            
            # Plot processing time distribution
            if self.batch_metrics['processing_times']:
                plt.subplot(2, 2, 2)
                plt.hist(self.batch_metrics['processing_times'], bins=10, color='#2196F3')
                plt.xlabel('Seconds')
                plt.ylabel('Number of Files')
                plt.title('Processing Time Distribution')
            
            # Plot error types if there are any
            if self.batch_metrics['error_counts']:
                plt.subplot(2, 2, 3)
                error_types = list(self.batch_metrics['error_counts'].keys())
                error_counts = list(self.batch_metrics['error_counts'].values())
                plt.bar(error_types, error_counts, color='#FF9800')
                plt.xlabel('Error Type')
                plt.ylabel('Count')
                plt.title('Errors by Type')
                plt.xticks(rotation=45, ha='right')
            
            # Add batch summary text
            plt.subplot(2, 2, 4)
            plt.axis('off')
            summary_text = (
                f"Batch {self.current_batch} Summary\n\n"
                f"Files Processed: {self.batch_metrics['completed_files'] + self.batch_metrics['failed_files']}\n"
                f"Success Rate: {self.batch_metrics['success_rate']*100:.1f}%\n"
                f"Duration: {self.batch_metrics['duration_seconds']:.1f} seconds\n"
                f"Processing Rate: {self.batch_metrics['files_per_second']:.2f} files/sec\n\n"
                f"Overall Progress:\n"
                f"Elapsed Time: {self.batch_metrics['overall_duration_formatted']}\n"
                f"Estimated Batches Remaining: {self.batch_metrics['estimated_batches_remaining']}\n"
            )
            plt.text(0.1, 0.5, summary_text, fontsize=10, va='center')
            
            plt.tight_layout()
            
            # Save the figure
            report_path = f"performance_metrics/batch_metrics/batch_{self.current_batch}_report.png"
            plt.savefig(report_path, dpi=100)
            plt.close()
            
            logger.info(f"Batch report saved to: {report_path}")
            
        except Exception as e:
            logger.error(f"Error generating batch report: {e}")
    
    def generate_overall_report(self):
        """Generate an overall report for all batches processed so far."""
        try:
            # Collect metrics from all batch files
            all_batches = []
            batch_dir = "performance_metrics/batch_metrics"
            for filename in os.listdir(batch_dir):
                if filename.startswith("batch_") and filename.endswith(".json"):
                    file_path = os.path.join(batch_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            batch_data = json.load(f)
                            all_batches.append(batch_data)
                    except Exception as e:
                        logger.error(f"Error reading batch file {filename}: {e}")
            
            # Sort batches by number
            all_batches.sort(key=lambda x: x.get('batch_number', 0))
            
            if not all_batches:
                logger.warning("No batch data found for overall report")
                return
            
            # Calculate overall statistics
            total_successful = sum(batch.get('completed_files', 0) for batch in all_batches)
            total_failed = sum(batch.get('failed_files', 0) for batch in all_batches)
            total_files = total_successful + total_failed
            overall_success_rate = total_successful / total_files if total_files > 0 else 0
            
            # Get processing times across all batches
            all_processing_times = []
            for batch in all_batches:
                if 'processing_times' in batch:
                    all_processing_times.extend(batch['processing_times'])
            
            avg_processing_time = sum(all_processing_times) / len(all_processing_times) if all_processing_times else 0
            
            # Aggregate error counts
            error_counts = defaultdict(int)
            for batch in all_batches:
                for error_type, count in batch.get('error_counts', {}).items():
                    error_counts[error_type] += count
            
            # Calculate processing rates over time
            batch_numbers = [batch.get('batch_number', i+1) for i, batch in enumerate(all_batches)]
            processing_rates = [batch.get('files_per_second', 0) for batch in all_batches]
            success_rates = [batch.get('success_rate', 0) * 100 for batch in all_batches]
            
            # Create the overall report figure
            plt.figure(figsize=(15, 10))
            
            # Plot overall success vs failure
            plt.subplot(2, 3, 1)
            labels = ['Successful', 'Failed']
            sizes = [total_successful, total_failed]
            colors = ['#4CAF50', '#F44336']
            plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            plt.axis('equal')
            plt.title('Overall Success Rate')
            
            # Plot processing times distribution
            if all_processing_times:
                plt.subplot(2, 3, 2)
                plt.hist(all_processing_times, bins=20, color='#2196F3')
                plt.xlabel('Seconds')
                plt.ylabel('Number of Files')
                plt.title('Overall Processing Time Distribution')
            
            # Plot error distribution
            if error_counts:
                plt.subplot(2, 3, 3)
                error_types = list(error_counts.keys())
                error_values = list(error_counts.values())
                plt.bar(error_types, error_values, color='#FF9800')
                plt.xlabel('Error Type')
                plt.ylabel('Count')
                plt.title('Errors by Type')
                plt.xticks(rotation=45, ha='right')
            
            # Plot processing rate trend
            plt.subplot(2, 3, 4)
            plt.plot(batch_numbers, processing_rates, 'b-', marker='o')
            plt.xlabel('Batch Number')
            plt.ylabel('Files/Second')
            plt.title('Processing Rate Trend')
            plt.grid(True)
            
            # Plot success rate trend
            plt.subplot(2, 3, 5)
            plt.plot(batch_numbers, success_rates, 'g-', marker='o')
            plt.xlabel('Batch Number')
            plt.ylabel('Success Rate (%)')
            plt.title('Success Rate Trend')
            plt.ylim(0, 105)  # 0-100% plus a little margin
            plt.grid(True)
            
            # Add overall summary text
            plt.subplot(2, 3, 6)
            plt.axis('off')
            
            first_batch = all_batches[0] if all_batches else {}
            last_batch = all_batches[-1] if all_batches else {}
            
            # Calculate total elapsed time
            start_time = datetime.datetime.fromisoformat(first_batch.get('start_time', datetime.datetime.now().isoformat()))
            if 'end_time' in last_batch:
                end_time = datetime.datetime.fromisoformat(last_batch['end_time'])
            else:
                end_time = datetime.datetime.now()
            
            elapsed = end_time - start_time
            elapsed_hours = elapsed.total_seconds() / 3600
            
            summary_text = (
                f"Overall Processing Summary\n\n"
                f"Total Files: {total_files}\n"
                f"Successful: {total_successful} ({overall_success_rate*100:.1f}%)\n"
                f"Failed: {total_failed} ({(1-overall_success_rate)*100:.1f}%)\n\n"
                f"Batches Processed: {len(all_batches)}\n"
                f"Avg. Processing Time: {avg_processing_time:.2f} seconds\n"
                f"Elapsed Time: {elapsed.days} days, {elapsed.seconds//3600} hours, {(elapsed.seconds//60)%60} minutes\n\n"
                f"Overall Processing Rate: {total_files/elapsed_hours:.1f} files/hour\n"
                f"Est. Completion: {last_batch.get('estimated_completion_time', 'Unknown')}\n"
            )
            plt.text(0.1, 0.5, summary_text, fontsize=10, va='center')
            
            plt.tight_layout()
            
            # Save the figure
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            report_path = f"performance_metrics/overall_report_{timestamp}.png"
            plt.savefig(report_path, dpi=120)
            plt.close()
            
            # Save summary to JSON
            summary = {
                'timestamp': datetime.datetime.now().isoformat(),
                'total_files': total_files,
                'successful_files': total_successful,
                'failed_files': total_failed,
                'success_rate': overall_success_rate,
                'batches_processed': len(all_batches),
                'avg_processing_time': avg_processing_time,
                'elapsed_time_seconds': elapsed.total_seconds(),
                'elapsed_time_formatted': f"{elapsed.days} days, {elapsed.seconds//3600} hours, {(elapsed.seconds//60)%60} minutes",
                'processing_rate_per_hour': total_files/elapsed_hours if elapsed_hours > 0 else 0,
                'error_counts': dict(error_counts),
                'report_path': report_path
            }
            
            summary_path = f"performance_metrics/overall_summary_{timestamp}.json"
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"Overall report saved to: {report_path}")
            logger.info(f"Overall summary saved to: {summary_path}")
            
            return report_path
            
        except Exception as e:
            logger.error(f"Error generating overall report: {e}")
            logger.error(traceback.format_exc())
            return None


class PerformanceMetrics:
    """Collects and manages performance metrics."""
    
    def __init__(self, config=None):
        """Initialize performance metrics collection."""
        self.config = config or MonitoringConfig()
        self.start_time = time.time()
        self.shutdown_requested = False
        
        # Create metrics directories
        os.makedirs(self.config.METRICS_DIR, exist_ok=True)
        os.makedirs(self.config.CHARTS_DIR, exist_ok=True)
        
        # Initialize metrics storage
        self.metrics_history = {
            "timestamp": deque(maxlen=self.config.HISTORY_LENGTH),
            "cpu_percent": deque(maxlen=self.config.HISTORY_LENGTH),
            "memory_percent": deque(maxlen=self.config.HISTORY_LENGTH),
            "disk_io_read": deque(maxlen=self.config.HISTORY_LENGTH),
            "disk_io_write": deque(maxlen=self.config.HISTORY_LENGTH),
            "network_sent": deque(maxlen=self.config.HISTORY_LENGTH),
            "network_received": deque(maxlen=self.config.HISTORY_LENGTH),
            "processing_rate": deque(maxlen=self.config.HISTORY_LENGTH),
            "success_rate": deque(maxlen=self.config.HISTORY_LENGTH),
            "error_rate": deque(maxlen=self.config.HISTORY_LENGTH),
            "active_threads": deque(maxlen=self.config.HISTORY_LENGTH)
        }
        
        # Initialize counters
        self.previous_io = psutil.disk_io_counters()
        self.previous_net = psutil.net_io_counters()
        self.previous_processed = 0
        
        # Initialize alert tracking
        self.last_alerts = defaultdict(int)
        
        # Set up CSV file
        self._setup_csv()
        
        # Start metrics collection thread
        self.collection_thread = threading.Thread(target=self._collect_metrics)
        self.collection_thread.daemon = True
        self.collection_thread.start()
        
        # Start reporting thread
        self.reporting_thread = threading.Thread(target=self._generate_reports)
        self.reporting_thread.daemon = True
        self.reporting_thread.start()
        
        logger.info("Performance metrics collection started")
    
    def _setup_csv(self):
        """Set up CSV file for metrics storage."""
        csv_exists = os.path.exists(self.config.CSV_FILE)
        
        with open(self.config.CSV_FILE, 'a', newline='') as csvfile:
            fieldnames = [
                'timestamp', 'cpu_percent', 'memory_percent', 
                'disk_io_read', 'disk_io_write', 
                'network_sent', 'network_received',
                'processing_rate', 'success_rate', 'error_rate', 
                'active_threads'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not csv_exists:
                writer.writeheader()
    
    def _collect_metrics(self):
        """Continuously collect performance metrics."""
        while not self.shutdown_requested:
            try:
                # Get current timestamp
                current_time = time.time()
                timestamp = datetime.datetime.fromtimestamp(current_time)
                
                # Get system metrics
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory_percent = psutil.virtual_memory().percent
                
                # Get disk IO
                current_io = psutil.disk_io_counters()
                if self.previous_io:
                    read_bytes = current_io.read_bytes - self.previous_io.read_bytes
                    write_bytes = current_io.write_bytes - self.previous_io.write_bytes
                else:
                    read_bytes = write_bytes = 0
                self.previous_io = current_io
                
                # Get network IO
                current_net = psutil.net_io_counters()
                if self.previous_net:
                    sent_bytes = current_net.bytes_sent - self.previous_net.bytes_sent
                    received_bytes = current_net.bytes_recv - self.previous_net.bytes_recv
                else:
                    sent_bytes = received_bytes = 0
                self.previous_net = current_net
                
                # Get application metrics
                try:
                    # Get current processed files
                    current_processed = performance_metrics.get("processed_files", 0)
                    processing_rate = (current_processed - self.previous_processed) / self.config.METRICS_INTERVAL
                    self.previous_processed = current_processed
                    
                    # Calculate success and error rates
                    successful = performance_metrics.get("successful_files", 0)
                    failed = performance_metrics.get("failed_files", 0)
                    total = successful + failed
                    
                    if total > 0:
                        success_rate = successful / total
                        error_rate = failed / total
                    else:
                        success_rate = 1.0
                        error_rate = 0.0
                    
                    # Get active threads
                    active_threads = threading.active_count()
                    
                except Exception as e:
                    logger.error(f"Error getting application metrics: {e}")
                    processing_rate = 0
                    success_rate = 1.0
                    error_rate = 0.0
                    active_threads = threading.active_count()
                
                # Store metrics
                self.metrics_history["timestamp"].append(timestamp)
                self.metrics_history["cpu_percent"].append(cpu_percent)
                self.metrics_history["memory_percent"].append(memory_percent)
                self.metrics_history["disk_io_read"].append(read_bytes)
                self.metrics_history["disk_io_write"].append(write_bytes)
                self.metrics_history["network_sent"].append(sent_bytes)
                self.metrics_history["network_received"].append(received_bytes)
                self.metrics_history["processing_rate"].append(processing_rate)
                self.metrics_history["success_rate"].append(success_rate)
                self.metrics_history["error_rate"].append(error_rate)
                self.metrics_history["active_threads"].append(active_threads)
                
                # Write to CSV
                with open(self.config.CSV_FILE, 'a', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=self.metrics_history.keys())
                    writer.writerow({
                        'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory_percent,
                        'disk_io_read': read_bytes,
                        'disk_io_write': write_bytes,
                        'network_sent': sent_bytes,
                        'network_received': received_bytes,
                        'processing_rate': processing_rate,
                        'success_rate': success_rate,
                        'error_rate': error_rate,
                        'active_threads': active_threads
                    })
                
                # Check for alert conditions
                self._check_alerts(cpu_percent, memory_percent, error_rate)
                
                # Sleep until next collection
                time.sleep(self.config.METRICS_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                traceback.print_exc()
                time.sleep(self.config.METRICS_INTERVAL)
    
    def _check_alerts(self, cpu_percent, memory_percent, error_rate):
        """Check for alert conditions and trigger alerts if needed."""
        current_time = time.time()
        
        # Check CPU usage
        if cpu_percent > self.config.CPU_ALERT_THRESHOLD:
            alert_key = f"cpu_{int(cpu_percent)}"
            if current_time - self.last_alerts.get(alert_key, 0) > self.config.ALERT_COOLDOWN:
                self._trigger_alert(
                    f"High CPU Usage: {cpu_percent}%",
                    f"CPU usage has exceeded the threshold of {self.config.CPU_ALERT_THRESHOLD}%"
                )
                self.last_alerts[alert_key] = current_time
        
        # Check memory usage
        if memory_percent > self.config.MEMORY_ALERT_THRESHOLD:
            alert_key = f"memory_{int(memory_percent)}"
            if current_time - self.last_alerts.get(alert_key, 0) > self.config.ALERT_COOLDOWN:
                self._trigger_alert(
                    f"High Memory Usage: {memory_percent}%",
                    f"Memory usage has exceeded the threshold of {self.config.MEMORY_ALERT_THRESHOLD}%"
                )
                self.last_alerts[alert_key] = current_time
        
        # Check error rate
        if error_rate > self.config.ERROR_RATE_THRESHOLD:
            alert_key = f"error_{int(error_rate * 100)}"
            if current_time - self.last_alerts.get(alert_key, 0) > self.config.ALERT_COOLDOWN:
                self._trigger_alert(
                    f"High Error Rate: {error_rate * 100:.1f}%",
                    f"Error rate has exceeded the threshold of {self.config.ERROR_RATE_THRESHOLD * 100}%"
                )
                self.last_alerts[alert_key] = current_time
    
    def _trigger_alert(self, title, message):
        """Trigger an alert using configured methods."""
        alert_text = f"ALERT: {title} - {message}"
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        full_alert = f"[{timestamp}] {alert_text}"
        
        for method in self.config.ALERT_METHODS:
            if method == "log":
                logger.warning(alert_text)
            elif method == "file":
                with open(os.path.join(self.config.METRICS_DIR, "alerts.log"), 'a') as f:
                    f.write(f"{full_alert}\n")
            elif method == "email" and self.config.ALERT_EMAIL:
                # This would require additional setup for email sending
                # e.g., using smtplib or a third-party service
                pass
    
    def _generate_reports(self):
        """Periodically generate performance reports and visualizations."""
        # Wait for initial data collection
        time.sleep(self.config.METRICS_INTERVAL * 2)
        
        while not self.shutdown_requested:
            try:
                # Generate JSON report
                self._generate_json_report()
                
                # Generate charts if we have enough data points
                if len(self.metrics_history["timestamp"]) > 5:
                    self._generate_charts()
                
                # Sleep until next report
                time.sleep(self.config.REPORT_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error generating reports: {e}")
                traceback.print_exc()
                time.sleep(self.config.REPORT_INTERVAL)
    
    def _generate_json_report(self):
        """Generate a JSON performance report with enhanced tracking for full-scale processing."""
        try:
            # Calculate summary metrics
            if self.metrics_history["cpu_percent"]:
                avg_cpu = sum(self.metrics_history["cpu_percent"]) / len(self.metrics_history["cpu_percent"])
                max_cpu = max(self.metrics_history["cpu_percent"])
            else:
                avg_cpu = max_cpu = 0
                
            if self.metrics_history["memory_percent"]:
                avg_memory = sum(self.metrics_history["memory_percent"]) / len(self.metrics_history["memory_percent"])
                max_memory = max(self.metrics_history["memory_percent"])
            else:
                avg_memory = max_memory = 0
                
            if self.metrics_history["processing_rate"]:
                avg_rate = sum(self.metrics_history["processing_rate"]) / len(self.metrics_history["processing_rate"])
                max_rate = max(self.metrics_history["processing_rate"])
            else:
                avg_rate = max_rate = 0
            
            # Get application metrics
            files_processed = performance_metrics.get("processed_files", 0)
            files_successful = performance_metrics.get("successful_files", 0)
            files_failed = performance_metrics.get("failed_files", 0)
            
            # Calculate elapsed time
            elapsed_time = time.time() - self.start_time
            hours, remainder = divmod(elapsed_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            # Calculate estimated completion time for full dataset
            estimated_completion = None
            estimated_completion_timestamp = None
            estimated_human = "Unknown"
            
            if files_processed > 0 and avg_rate > 0:
                total_expected = 1123  # Total JFK files expected
                remaining_files = total_expected - files_processed
                if remaining_files > 0:
                    est_seconds_remaining = remaining_files / avg_rate
                    completion_time = datetime.datetime.now() + datetime.timedelta(seconds=est_seconds_remaining)
                    estimated_completion = completion_time.isoformat()
                    estimated_completion_timestamp = completion_time.timestamp()
                    
                    # Format in human-readable form
                    days, seconds = divmod(est_seconds_remaining, 86400)
                    hours, seconds = divmod(seconds, 3600)
                    minutes, seconds = divmod(seconds, 60)
                    
                    if days > 0:
                        estimated_human = f"{int(days)}d {int(hours)}h {int(minutes)}m remaining"
                    elif hours > 0:
                        estimated_human = f"{int(hours)}h {int(minutes)}m remaining"
                    else:
                        estimated_human = f"{int(minutes)}m {int(seconds)}s remaining"
            
            # Generate progress bar
            progress_percentage = (files_processed / 1123) * 100 if files_processed > 0 else 0
            progress_bar = self._generate_progress_bar(progress_percentage, 50)
            
            # Enhanced report with full-scale processing metrics
            report = {
                "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "runtime": {
                    "seconds": elapsed_time,
                    "formatted": f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
                },
                "system": {
                    "cpu": {
                        "current": self.metrics_history["cpu_percent"][-1] if self.metrics_history["cpu_percent"] else 0,
                        "average": avg_cpu,
                        "maximum": max_cpu
                    },
                    "memory": {
                        "current": self.metrics_history["memory_percent"][-1] if self.metrics_history["memory_percent"] else 0,
                        "average": avg_memory,
                        "maximum": max_memory,
                        "total_gb": psutil.virtual_memory().total / (1024 ** 3)
                    },
                    "disk_io": {
                        "read_mb": sum(self.metrics_history["disk_io_read"]) / (1024 ** 2),
                        "write_mb": sum(self.metrics_history["disk_io_write"]) / (1024 ** 2)
                    },
                    "network_io": {
                        "sent_mb": sum(self.metrics_history["network_sent"]) / (1024 ** 2),
                        "received_mb": sum(self.metrics_history["network_received"]) / (1024 ** 2)
                    }
                },
                "application": {
                    "files": {
                        "processed": files_processed,
                        "successful": files_successful,
                        "failed": files_failed,
                        "total_expected": 1123,  # Total JFK files expected
                        "progress_percentage": (files_processed / 1123) * 100 if files_processed > 0 else 0
                    },
                    "rates": {
                        "current": self.metrics_history["processing_rate"][-1] if self.metrics_history["processing_rate"] else 0,
                        "average": avg_rate,
                        "maximum": max_rate,
                        "files_per_hour": avg_rate * 3600 if avg_rate > 0 else 0,
                        "estimated_completion": estimated_completion
                    },
                    "success_rate": files_successful / max(files_processed, 1) * 100,
                    "error_counts": dict(error_counts),
                    "error_rate_trend": self._calculate_error_rate_trend()
                },
                "charts": {
                    "system_resources": f"charts/system_resources_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.png",
                    "processing_metrics": f"charts/processing_metrics_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.png",
                    "io_metrics": f"charts/io_metrics_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                },
                "recommendations": self._generate_recommendations(),
                "full_scale_analysis": self._analyze_full_scale_processing(files_processed, avg_rate)
            }
            
            # Save report to JSON file
            with open(self.config.JSON_FILE, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.debug(f"Enhanced performance report saved to {self.config.JSON_FILE}")
            
        except Exception as e:
            logger.error(f"Error generating JSON report: {e}")

    def _calculate_error_rate_trend(self):
        """Calculate error rate trend over time for full-scale processing analysis."""
        # If we don't have enough data points, return empty trend
        if len(self.metrics_history["error_rate"]) < 10:
            return []
        
        # Calculate moving average of error rates
        window_size = min(10, len(self.metrics_history["error_rate"]))
        trend = []
        
        for i in range(len(self.metrics_history["error_rate"]) - window_size + 1):
            window = self.metrics_history["error_rate"][i:i+window_size]
            avg_error_rate = sum(window) / window_size
            trend.append({
                "timestamp": self.metrics_history["timestamp"][i+window_size-1].isoformat(),
                "error_rate": avg_error_rate * 100  # Convert to percentage
            })
        
        return trend

    def _analyze_full_scale_processing(self, files_processed, avg_rate):
        """
        Perform detailed analysis for full-scale processing metrics.
        
        Args:
            files_processed (int): Number of files processed so far
            avg_rate (float): Average processing rate in files/second
            
        Returns:
            dict: Analysis data
        """
        total_expected = 1123  # Total JFK files expected
        
        # Basic progress metrics
        progress_percentage = (files_processed / total_expected) * 100 if files_processed > 0 else 0
        
        # Calculate time estimates
        remaining_files = max(0, total_expected - files_processed)
        
        if avg_rate > 0:
            est_seconds_remaining = remaining_files / avg_rate
            hours, remainder = divmod(est_seconds_remaining, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_remaining = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
            
            completion_time = datetime.datetime.now() + datetime.timedelta(seconds=est_seconds_remaining)
            estimated_completion = completion_time.isoformat()
        else:
            time_remaining = "Unknown"
            estimated_completion = "Unknown"
        
        # Resource utilization analysis
        if self.metrics_history["cpu_percent"] and self.metrics_history["memory_percent"]:
            cpu_trend = self._detect_resource_trend(self.metrics_history["cpu_percent"])
            memory_trend = self._detect_resource_trend(self.metrics_history["memory_percent"])
            
            # Predict if resources will be constrained
            resource_constraint = None
            if cpu_trend == "increasing" and max(self.metrics_history["cpu_percent"]) > 70:
                resource_constraint = "CPU may become a bottleneck"
            elif memory_trend == "increasing" and max(self.metrics_history["memory_percent"]) > 70:
                resource_constraint = "Memory may become a bottleneck"
        else:
            resource_constraint = "Unknown"
        
        # Process optimization suggestions
        if avg_rate > 0:
            optimal_thread_count = self._estimate_optimal_thread_count(avg_rate)
        else:
            optimal_thread_count = "Unknown"
        
        # Checkpointing frequency recommendation
        if avg_rate > 0:
            # Recommend checkpointing every N files, where N gives us ~5 minute intervals
            checkpoint_interval = max(1, int(300 * avg_rate))  # 300 seconds = 5 minutes
        else:
            checkpoint_interval = 10  # Default
        
        # Calculate progress bar for CLI display
        progress_bar = self._generate_progress_bar(progress_percentage, 50)
        
        return {
            "progress_percentage": progress_percentage,
            "remaining_files": remaining_files,
            "estimated_time_remaining": time_remaining,
            "estimated_completion_time": estimated_completion,
            "estimated_completion_timestamp": estimated_completion_timestamp,
            "estimated_human_readable": estimated_human if 'estimated_human' in locals() else "Unknown",
            "progress_bar": progress_bar,
            "resource_constraint_prediction": resource_constraint,
            "optimization_recommendations": {
                "optimal_thread_count": optimal_thread_count,
                "recommended_checkpoint_interval": checkpoint_interval,
                "batch_size_recommendation": self._recommend_batch_size(avg_rate)
            },
            "scaling_efficiency": self._analyze_scaling_efficiency(),
            "remaining_tasks": self._calculate_remaining_tasks(remaining_files)
        }

    def _detect_resource_trend(self, metric_data):
        """Detect if a resource metric is trending up, down, or stable."""
        if len(metric_data) < 10:
            return "insufficient_data"
        
        # Use a simple linear regression to detect trend
        x = list(range(len(metric_data)))
        y = list(metric_data)
        
        # Calculate slope using simplified linear regression
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_xx = sum(xi * xi for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
        
        # Interpret slope
        if abs(slope) < 0.01:
            return "stable"
        elif slope > 0:
            return "increasing"
        else:
            return "decreasing"

    def _estimate_optimal_thread_count(self, avg_rate):
        """Estimate optimal thread count based on processing rate and system resources."""
        # Get current CPU count
        cpu_count = os.cpu_count() or 4
        
        # Get average CPU usage
        if self.metrics_history["cpu_percent"]:
            avg_cpu = sum(self.metrics_history["cpu_percent"]) / len(self.metrics_history["cpu_percent"])
        else:
            avg_cpu = 0
        
        # If CPU usage is high, reduce thread count; if low, increase it
        current_threads = threading.active_count()
        
        if avg_cpu > 85:
            # CPU is heavily loaded, reduce threads
            optimal = max(1, int(current_threads * 0.7))
        elif avg_cpu < 30:
            # CPU is underutilized, increase threads
            optimal = min(cpu_count * 2, current_threads + 2)
        else:
            # CPU usage is reasonable, maintain similar thread count
            optimal = current_threads
        
        return optimal

    def _recommend_batch_size(self, avg_rate):
        """Recommend optimal batch size based on processing rate."""
        if avg_rate <= 0:
            return 50  # Default conservative batch size
        
        # Calculate a batch size that would take approximately 30 minutes to process
        # This balances progress tracking with checkpoint overhead
        optimal_batch_size = int(avg_rate * 1800)  # 1800 seconds = 30 minutes
        
        # Enforce reasonable limits
        optimal_batch_size = max(10, min(200, optimal_batch_size))
        
        return optimal_batch_size

    def _generate_progress_bar(self, percentage, width=50):
        """Generate a text-based progress bar for CLI display."""
        filled_width = int(width * percentage / 100)
        bar = '█' * filled_width + '░' * (width - filled_width)
        return f"|{bar}| {percentage:.1f}%"
    
    def _calculate_remaining_tasks(self, remaining_files):
        """Calculate and segment remaining tasks for better tracking."""
        # For JFK files project, segment remaining files into logical tasks
        remaining_tasks = []
        
        if remaining_files <= 0:
            return [{
                "name": "All files processed",
                "count": 0,
                "percentage": 100
            }]
            
        # Process remaining files in meaningful chunks for reporting
        page_size = 10  # Files per page
        remaining_pages = math.ceil(remaining_files / page_size)
        
        if remaining_pages > 0:
            remaining_tasks.append({
                "name": "Pages remaining to process",
                "count": remaining_pages,
                "percentage": (remaining_files / 1123) * 100
            })
        
        # Add other logical task groupings
        if remaining_files > 500:
            remaining_tasks.append({
                "name": "Large batch processing",
                "count": 1,
                "percentage": (remaining_files / 1123) * 100,
                "estimated_hours": remaining_files / (3600 * 0.1)  # Assuming 0.1 files/sec
            })
        elif remaining_files > 100:
            remaining_tasks.append({
                "name": "Medium batch processing",
                "count": 1,
                "percentage": (remaining_files / 1123) * 100,
                "estimated_hours": remaining_files / (3600 * 0.1)
            })
        else:
            remaining_tasks.append({
                "name": "Small batch processing",
                "count": 1,
                "percentage": (remaining_files / 1123) * 100,
                "estimated_hours": remaining_files / (3600 * 0.1)
            })
            
        return remaining_tasks
    
    def _analyze_scaling_efficiency(self):
        """Analyze how well the process scales with increasing files."""
        # If we don't have enough processing rate data points, return basic analysis
        if len(self.metrics_history["processing_rate"]) < 20:
            return {
                "scaling_score": "insufficient_data",
                "explanation": "Need more data to analyze scaling efficiency"
            }
        
        # Look at how processing rate changes over time
        early_rates = self.metrics_history["processing_rate"][:10]
        recent_rates = self.metrics_history["processing_rate"][-10:]
        
        if not early_rates or not recent_rates:
            return {
                "scaling_score": "insufficient_data",
                "explanation": "Need more data to analyze scaling efficiency"
            }
        
        avg_early_rate = sum(early_rates) / len(early_rates)
        avg_recent_rate = sum(recent_rates) / len(recent_rates)
        
        # Calculate scaling efficiency
        if avg_early_rate > 0:
            scaling_ratio = avg_recent_rate / avg_early_rate
        else:
            scaling_ratio = 1.0
        
        # Interpret scaling ratio
        if scaling_ratio > 0.95:
            scaling_score = "excellent"
            explanation = "Process maintains efficiency well as dataset grows"
        elif scaling_ratio > 0.8:
            scaling_score = "good"
            explanation = "Process shows slight efficiency decrease with scale"
        elif scaling_ratio > 0.6:
            scaling_score = "fair"
            explanation = "Process shows moderate efficiency decrease with scale"
        else:
            scaling_score = "poor"
            explanation = "Process efficiency decreases significantly with scale"
        
        return {
            "scaling_score": scaling_score,
            "scaling_ratio": scaling_ratio,
            "explanation": explanation
        }
    
    def _generate_charts(self):
        """Generate performance charts."""
        try:
            # Convert timestamps to matplotlib dates
            dates = [t for t in self.metrics_history["timestamp"]]
            dates_fmt = mdates.DateFormatter('%H:%M:%S')
            
            # 1. System Resources Chart (CPU and Memory)
            plt.figure(figsize=(self.config.CHART_WIDTH, self.config.CHART_HEIGHT))
            
            plt.subplot(2, 1, 1)
            plt.plot(dates, self.metrics_history["cpu_percent"], 'b-', label='CPU %')
            plt.axhline(y=self.config.CPU_ALERT_THRESHOLD, color='r', linestyle='--', label=f'CPU Alert Threshold ({self.config.CPU_ALERT_THRESHOLD}%)')
            plt.ylabel('CPU %')
            plt.title('System CPU Usage')
            plt.legend()
            plt.gca().xaxis.set_major_formatter(dates_fmt)
            plt.grid(True)
            
            plt.subplot(2, 1, 2)
            plt.plot(dates, self.metrics_history["memory_percent"], 'g-', label='Memory %')
            plt.axhline(y=self.config.MEMORY_ALERT_THRESHOLD, color='r', linestyle='--', label=f'Memory Alert Threshold ({self.config.MEMORY_ALERT_THRESHOLD}%)')
            plt.xlabel('Time')
            plt.ylabel('Memory %')
            plt.title('System Memory Usage')
            plt.legend()
            plt.gca().xaxis.set_major_formatter(dates_fmt)
            plt.grid(True)
            
            plt.tight_layout()
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            system_chart_path = os.path.join(self.config.CHARTS_DIR, f"system_resources_{timestamp}.png")
            plt.savefig(system_chart_path, dpi=self.config.CHART_DPI)
            plt.close()
            
            # 2. Processing Metrics Chart (Processing Rate, Success Rate, Error Rate)
            plt.figure(figsize=(self.config.CHART_WIDTH, self.config.CHART_HEIGHT))
            
            plt.subplot(3, 1, 1)
            plt.plot(dates, self.metrics_history["processing_rate"], 'b-', label='Files/sec')
            plt.ylabel('Files/sec')
            plt.title('Processing Rate')
            plt.legend()
            plt.gca().xaxis.set_major_formatter(dates_fmt)
            plt.grid(True)
            
            plt.subplot(3, 1, 2)
            plt.plot(dates, [s * 100 for s in self.metrics_history["success_rate"]], 'g-', label='Success %')
            plt.ylabel('Success %')
            plt.title('Success Rate')
            plt.legend()
            plt.gca().xaxis.set_major_formatter(dates_fmt)
            plt.grid(True)
            
            plt.subplot(3, 1, 3)
            plt.plot(dates, [e * 100 for e in self.metrics_history["error_rate"]], 'r-', label='Error %')
            plt.axhline(y=self.config.ERROR_RATE_THRESHOLD * 100, color='r', linestyle='--', label=f'Error Alert Threshold ({self.config.ERROR_RATE_THRESHOLD * 100}%)')
            plt.xlabel('Time')
            plt.ylabel('Error %')
            plt.title('Error Rate')
            plt.legend()
            plt.gca().xaxis.set_major_formatter(dates_fmt)
            plt.grid(True)
            
            plt.tight_layout()
            processing_chart_path = os.path.join(self.config.CHARTS_DIR, f"processing_metrics_{timestamp}.png")
            plt.savefig(processing_chart_path, dpi=self.config.CHART_DPI)
            plt.close()
            
            # 3. I/O Metrics Chart (Disk I/O and Network I/O)
            plt.figure(figsize=(self.config.CHART_WIDTH, self.config.CHART_HEIGHT))
            
            plt.subplot(2, 1, 1)
            plt.plot(dates, [r / (1024 * 1024) for r in self.metrics_history["disk_io_read"]], 'b-', label='Read (MB/s)')
            plt.plot(dates, [w / (1024 * 1024) for w in self.metrics_history["disk_io_write"]], 'g-', label='Write (MB/s)')
            plt.ylabel('MB/s')
            plt.title('Disk I/O')
            plt.legend()
            plt.gca().xaxis.set_major_formatter(dates_fmt)
            plt.grid(True)
            
            plt.subplot(2, 1, 2)
            plt.plot(dates, [s / (1024 * 1024) for s in self.metrics_history["network_sent"]], 'b-', label='Sent (MB/s)')
            plt.plot(dates, [r / (1024 * 1024) for r in self.metrics_history["network_received"]], 'g-', label='Received (MB/s)')
            plt.xlabel('Time')
            plt.ylabel('MB/s')
            plt.title('Network I/O')
            plt.legend()
            plt.gca().xaxis.set_major_formatter(dates_fmt)
            plt.grid(True)
            
            plt.tight_layout()
            io_chart_path = os.path.join(self.config.CHARTS_DIR, f"io_metrics_{timestamp}.png")
            plt.savefig(io_chart_path, dpi=self.config.CHART_DPI)
            plt.close()
            
            logger.debug(f"Performance charts saved to {self.config.CHARTS_DIR}")
            
        except Exception as e:
            logger.error(f"Error generating charts: {e}")
            traceback.print_exc()
    
    def _generate_recommendations(self):
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # CPU recommendations
        if self.metrics_history["cpu_percent"] and max(self.metrics_history["cpu_percent"]) > 80:
            avg_cpu = sum(self.metrics_history["cpu_percent"]) / len(self.metrics_history["cpu_percent"])
            if avg_cpu > 70:
                recommendations.append({
                    "category": "CPU",
                    "severity": "high",
                    "message": "CPU usage consistently high. Consider reducing the number of worker threads or increasing rate limiting."
                })
            else:
                recommendations.append({
                    "category": "CPU",
                    "severity": "medium",
                    "message": "CPU usage occasionally spikes. Consider using adaptive throttling to manage peak loads."
                })
        
        # Memory recommendations
        if self.metrics_history["memory_percent"] and max(self.metrics_history["memory_percent"]) > 80:
            recommendations.append({
                "category": "Memory",
                "severity": "high",
                "message": "Memory usage approaching system limits. Consider processing in smaller batches or implementing memory usage controls."
            })
        
        # Processing rate recommendations
        if self.metrics_history["processing_rate"]:
            avg_rate = sum(self.metrics_history["processing_rate"]) / len(self.metrics_history["processing_rate"])
            if avg_rate < 0.1:  # Less than 0.1 files per second
                recommendations.append({
                    "category": "Performance",
                    "severity": "medium",
                    "message": "Processing rate is low. Consider optimizing file processing pipeline or increasing parallelism if resources permit."
                })
        
        # Error rate recommendations
        if self.metrics_history["error_rate"] and max(self.metrics_history["error_rate"]) > 0.05:  # More than 5% errors
            recommendations.append({
                "category": "Reliability",
                "severity": "high",
                "message": "Error rate is significant. Investigate error patterns and consider implementing more robust error handling or retry mechanisms."
            })
        
        # If optimization module is available, add specific optimization recommendations
        if OPTIMIZATION_AVAILABLE:
            # Thread count recommendations
            if self.metrics_history["active_threads"] and max(self.metrics_history["active_threads"]) > 15:
                recommendations.append({
                    "category": "Concurrency",
                    "severity": "medium",
                    "message": "High thread count detected. Consider using the OptimizationConfig to set appropriate MAX_WORKERS and enable adaptive thread pool management."
                })
            
            # I/O recommendations
            if (self.metrics_history["disk_io_write"] and 
                max(self.metrics_history["disk_io_write"]) > 10 * 1024 * 1024):  # More than 10 MB/s write
                recommendations.append({
                    "category": "I/O",
                    "severity": "medium",
                    "message": "High disk write activity. Consider optimizing storage operations or implementing I/O batching."
                })
        
        # If no recommendations, add a positive note
        if not recommendations:
            recommendations.append({
                "category": "General",
                "severity": "low",
                "message": "Performance metrics are within expected ranges. No specific optimization recommendations at this time."
            })
        
        return recommendations
    
    def shutdown(self):
        """Shutdown the metrics collection and reporting."""
        logger.info("Shutting down performance metrics collection")
        self.shutdown_requested = True
        
        # Generate final report and charts
        try:
            self._generate_json_report()
            self._generate_charts()
            logger.info("Final performance report and charts generated")
        except Exception as e:
            logger.error(f"Error generating final reports: {e}")
        
        # Wait for threads to complete
        if self.collection_thread.is_alive():
            self.collection_thread.join(timeout=2.0)
        if self.reporting_thread.is_alive():
            self.reporting_thread.join(timeout=2.0)


class PerformanceMonitor:
    """Main performance monitoring class with command-line interface."""
    
    def __init__(self, config=None):
        """Initialize the performance monitor."""
        self.config = config or MonitoringConfig()
        self.metrics = None
        
        # Set up signal handlers
        self._register_signal_handlers()
    
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, shutting down performance monitor...")
            if self.metrics:
                self.metrics.shutdown()
            sys.exit(0)
        
        # Register for common termination signals
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination request
        
        # On Unix-like systems, also register SIGHUP
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)  # Terminal closed
    
    def start_monitoring(self):
        """Start performance monitoring."""
        self.metrics = PerformanceMetrics(self.config)
        logger.info("Performance monitor started")
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            logger.info("Performance monitor stopped by user")
            self.metrics.shutdown()
    
    def generate_report(self, include_cli_output=True):
        """Generate a one-time performance report with optional CLI output."""
        temp_metrics = PerformanceMetrics(self.config)
        
        # Wait for initial data collection
        time.sleep(self.config.METRICS_INTERVAL * 2)
        
        # Generate report and charts
        temp_metrics._generate_json_report()
        temp_metrics._generate_charts()
        
        # Print CLI-friendly report if requested
        if include_cli_output:
            self._print_cli_report(temp_metrics)
        
        # Clean up
        temp_metrics.shutdown()
        
        report_path = self.config.JSON_FILE
        logger.info(f"One-time performance report generated at {report_path}")
        return report_path
        
    def _print_cli_report(self, metrics):
        """Print a CLI-friendly performance report for full-scale processing."""
        try:
            # Read the latest generated JSON report
            with open(self.config.JSON_FILE, 'r') as f:
                report = json.load(f)
                
            # Extract key metrics for display
            app_metrics = report.get('application', {})
            files_metrics = app_metrics.get('files', {})
            rates_metrics = app_metrics.get('rates', {})
            
            # Create pretty CLI output
            print("\n" + "=" * 80)
            print(f"JFK FILES PROCESSING STATUS REPORT - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80)
            
            # Display progress bar and statistics
            if 'progress_percentage' in files_metrics:
                progress_pct = files_metrics['progress_percentage']
                processed = files_metrics.get('processed', 0)
                total = files_metrics.get('total_expected', 1123)
                
                # Create progress bar
                width = 50
                filled_width = int(width * progress_pct / 100)
                bar = '█' * filled_width + '░' * (width - filled_width)
                
                print(f"\nPROGRESS: {processed}/{total} files")
                print(f"|{bar}| {progress_pct:.1f}%")
            
            # Show time estimates
            if 'estimated_completion' in rates_metrics:
                try:
                    eta = datetime.datetime.fromisoformat(rates_metrics['estimated_completion'])
                    eta_str = eta.strftime('%Y-%m-%d %H:%M:%S')
                    print(f"\nEstimated completion: {eta_str}")
                except (ValueError, TypeError):
                    print("\nEstimated completion: Unknown")
                    
            # Display processing rates
            print(f"\nProcessing rate: {rates_metrics.get('current', 0):.2f} files/sec")
            print(f"Average rate: {rates_metrics.get('average', 0):.2f} files/sec")
            print(f"Processing speed: {rates_metrics.get('files_per_hour', 0):.1f} files/hour")
            
            # Show success/error rates
            print(f"\nSuccess rate: {app_metrics.get('success_rate', 0):.1f}%")
            
            if 'error_counts' in app_metrics and app_metrics['error_counts']:
                print("\nERROR SUMMARY:")
                for error_type, count in app_metrics['error_counts'].items():
                    print(f"  - {error_type}: {count}")
            
            # Full-scale analysis if available
            if 'full_scale_analysis' in report:
                analysis = report['full_scale_analysis']
                
                if 'optimization_recommendations' in analysis:
                    opts = analysis['optimization_recommendations']
                    print("\nOPTIMIZATION RECOMMENDATIONS:")
                    print(f"  - Optimal thread count: {opts.get('optimal_thread_count', 'Unknown')}")
                    print(f"  - Recommended batch size: {opts.get('batch_size_recommendation', 'Unknown')}")
            
            # Show system resource usage
            system = report.get('system', {})
            cpu = system.get('cpu', {})
            memory = system.get('memory', {})
            
            print("\nSYSTEM RESOURCES:")
            print(f"  - CPU: {cpu.get('current', 0):.1f}% (avg: {cpu.get('average', 0):.1f}%, max: {cpu.get('maximum', 0):.1f}%)")
            print(f"  - Memory: {memory.get('current', 0):.1f}% (avg: {memory.get('average', 0):.1f}%, max: {memory.get('maximum', 0):.1f}%)")
            
            print("\n" + "=" * 80)
            print(f"Detailed charts available in: {self.config.CHARTS_DIR}")
            print("=" * 80 + "\n")
            
        except Exception as e:
            logger.error(f"Error printing CLI report: {e}")
            print("\nError generating CLI report. Please check the JSON report file.")


def main():
    """Command-line interface for the performance monitor."""
    parser = argparse.ArgumentParser(description="JFK Files Scraper Performance Monitor")
    parser.add_argument("--mode", choices=["monitor", "report", "status"], default="monitor",
                      help="Operation mode: 'monitor' for continuous monitoring, 'report' for one-time report, 'status' for CLI status")
    parser.add_argument("--interval", type=int, default=MonitoringConfig.METRICS_INTERVAL,
                      help=f"Metrics collection interval in seconds (default: {MonitoringConfig.METRICS_INTERVAL})")
    parser.add_argument("--report-interval", type=int, default=MonitoringConfig.REPORT_INTERVAL,
                      help=f"Report generation interval in seconds (default: {MonitoringConfig.REPORT_INTERVAL})")
    parser.add_argument("--no-cli", action="store_true", help="Disable CLI output for reports")
    
    args = parser.parse_args()
    
    # Create custom config with command-line settings
    config = MonitoringConfig()
    config.METRICS_INTERVAL = args.interval
    config.REPORT_INTERVAL = args.report_interval
    
    # Create monitor instance
    monitor = PerformanceMonitor(config)
    
    # Run in the appropriate mode
    if args.mode == "monitor":
        logger.info("Starting continuous performance monitoring")
        monitor.start_monitoring()
    elif args.mode == "status":
        logger.info("Generating status report for full-scale processing")
        monitor._print_cli_report(None)  # Print CLI status only
    else:  # report mode
        logger.info("Generating one-time performance report")
        report_path = monitor.generate_report(not args.no_cli)
        if args.no_cli:
            print(f"Performance report generated: {report_path}")


if __name__ == "__main__":
    main()
