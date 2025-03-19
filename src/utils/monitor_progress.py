#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JFK Files Scraper - Progress Monitor

This script provides real-time monitoring for the JFK Files Scraper process.
It can be run alongside the main scraper to track progress, resource usage,
and overall performance.

Usage:
    python monitor_progress.py --mode [monitor|status|report]

Author: Cline
Date: March 19, 2025
"""

import os
import sys
import time
import argparse
import json
from datetime import datetime

# Try to import performance monitoring module
try:
    from src.performance_monitoring import PerformanceMonitor, MonitoringConfig
    HAS_MONITORING = True
except ImportError:
    HAS_MONITORING = False
    print("WARNING: Performance monitoring module not available.")
    print("Install dependencies with: pip install -r requirements.txt")

# Define colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_color(text, color):
    """Print colored text to terminal."""
    print(f"{color}{text}{Colors.ENDC}")

def print_header(text):
    """Print a formatted header."""
    width = min(os.get_terminal_size().columns, 80)
    print("\n" + "=" * width)
    print_color(f"{text.center(width)}", Colors.BOLD + Colors.HEADER)
    print("=" * width)

def generate_progress_bar(percentage, width=50):
    """Generate a text-based progress bar."""
    filled_width = int(width * percentage / 100)
    bar = '█' * filled_width + '░' * (width - filled_width)
    return f"|{bar}| {percentage:.1f}%"

def count_files_recursively(directory, extension):
    """Count files with given extension recursively in directory and subdirs."""
    count = 0
    if not os.path.exists(directory):
        return 0
        
    for root, dirs, files in os.walk(directory):
        count += sum(1 for f in files if f.lower().endswith(extension))
    return count

def get_latest_files(directory, extension, count=5):
    """Get the most recently modified files with the given extension."""
    if not os.path.exists(directory):
        return []
        
    files = []
    for root, dirs, filenames in os.walk(directory):
        for filename in filenames:
            if filename.lower().endswith(extension):
                filepath = os.path.join(root, filename)
                mtime = os.path.getmtime(filepath)
                files.append((filepath, mtime))
    
    # Sort by modification time (newest first) and return the top N
    return [f[0] for f in sorted(files, key=lambda x: x[1], reverse=True)[:count]]

def basic_status_check():
    """Perform a basic status check without the monitoring module."""
    # Check for PDF files (recursively)
    pdf_count = count_files_recursively('pdfs', '.pdf')
    
    # Check for Markdown files
    md_count = count_files_recursively('markdown', '.md')
    
    # Check for JSON files
    json_count = count_files_recursively('json', '.json')
    
    # Get count of files in lite_llm directory
    lite_llm_count = 0
    if os.path.exists('lite_llm'):
        lite_llm_json_files = [f for f in os.listdir('lite_llm') if f.lower().endswith('.json')]
        if lite_llm_json_files:
            # Try to count the entries in the consolidated file
            consolidated_path = os.path.join('lite_llm', 'consolidated_jfk_files.json')
            if os.path.exists(consolidated_path):
                try:
                    with open(consolidated_path, 'r', encoding='utf-8') as f:
                        consolidated_data = json.load(f)
                        if isinstance(consolidated_data, list):
                            lite_llm_count = len(consolidated_data)
                        elif isinstance(consolidated_data, dict) and 'documents' in consolidated_data:
                            lite_llm_count = len(consolidated_data['documents'])
                except Exception as e:
                    print(f"Error reading consolidated JSON: {e}")
                    lite_llm_count = len(lite_llm_json_files)
            else:
                lite_llm_count = len(lite_llm_json_files)
    
    # Calculate percentage based on expected 1,123 files
    total_expected = 1123
    progress_percentage = (pdf_count / total_expected) * 100 if total_expected > 0 else 0
    
    # Print status
    print_header("JFK FILES SCRAPER - BASIC STATUS")
    print(f"\nPROGRESS SUMMARY:")
    print(f"PDF files downloaded: {pdf_count}/{total_expected}")
    print(f"Markdown files generated: {md_count}/{total_expected}")
    print(f"JSON files created: {json_count}/{total_expected}")
    print(f"Documents in LiteLLM format: {lite_llm_count}/{total_expected}")
    
    # Show directory structure details
    if pdf_count > 0:
        print(f"\nPDF DIRECTORY STRUCTURE:")
        pdf_subdirs = []
        if os.path.exists('pdfs'):
            pdf_subdirs = [d for d in os.listdir('pdfs') if os.path.isdir(os.path.join('pdfs', d))]
            if pdf_subdirs:
                for subdir in sorted(pdf_subdirs):
                    subdir_path = os.path.join('pdfs', subdir)
                    subdir_count = len([f for f in os.listdir(subdir_path) if f.lower().endswith('.pdf')])
                    print(f"  - {subdir}: {subdir_count} files")
            else:
                print(f"  - (flat structure): {pdf_count} files")
    
    # Show recently modified files
    print(f"\nRECENTLY PROCESSED FILES:")
    latest_pdfs = get_latest_files('pdfs', '.pdf', 3)
    if latest_pdfs:
        print(f"Latest PDFs:")
        for pdf in latest_pdfs:
            rel_path = os.path.relpath(pdf)
            mod_time = datetime.fromtimestamp(os.path.getmtime(pdf)).strftime('%Y-%m-%d %H:%M:%S')
            print(f"  - {rel_path} (modified: {mod_time})")
    
    latest_jsons = get_latest_files('json', '.json', 3)
    if latest_jsons:
        print(f"Latest JSONs:")
        for json_file in latest_jsons:
            rel_path = os.path.relpath(json_file)
            mod_time = datetime.fromtimestamp(os.path.getmtime(json_file)).strftime('%Y-%m-%d %H:%M:%S')
            print(f"  - {rel_path} (modified: {mod_time})")
    
    print(f"\nPROGRESS BAR:")
    print(generate_progress_bar(progress_percentage))
    
    # Check for log files
    print(f"\nLOG FILES:")
    if os.path.exists('jfk_scraper.log'):
        print(f"Main log: jfk_scraper.log")
    if os.path.exists('jfk_scraper_errors.log'):
        print(f"Error log: jfk_scraper_errors.log")
    
    # Check for checkpoint files
    print(f"\nCHECKPOINTS:")
    if os.path.exists('.checkpoints'):
        checkpoint_files = os.listdir('.checkpoints')
        if checkpoint_files:
            for cp in checkpoint_files[:5]:  # Show up to 5 checkpoints
                print(f"- {cp}")
            if len(checkpoint_files) > 5:
                print(f"... and {len(checkpoint_files) - 5} more")
        else:
            print("No checkpoints found")
    else:
        print("Checkpoint directory not found")

def monitor_mode():
    """Run continuous monitoring."""
    if not HAS_MONITORING:
        print_color("ERROR: Performance monitoring module not available.", Colors.RED)
        return
    
    try:
        # Create custom config
        config = MonitoringConfig()
        config.METRICS_INTERVAL = 5  # 5 seconds between measurements
        
        # Start the monitor
        monitor = PerformanceMonitor(config)
        print_color("Starting continuous monitoring. Press Ctrl+C to stop.", Colors.BLUE)
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print_color("\nMonitoring stopped by user.", Colors.YELLOW)
    except Exception as e:
        print_color(f"Error during monitoring: {e}", Colors.RED)

def status_mode():
    """Show current status."""
    if not HAS_MONITORING:
        basic_status_check()
        return
    
    try:
        # Create monitor instance
        monitor = PerformanceMonitor()
        
        # Generate CLI report
        try:
            monitor._print_cli_report(None)
        except:
            # Fall back to basic status if CLI report fails
            print_color("Detailed status not available, showing basic status:", Colors.YELLOW)
            basic_status_check()
    except Exception as e:
        print_color(f"Error generating status: {e}", Colors.RED)
        basic_status_check()

def report_mode():
    """Generate a one-time report."""
    if not HAS_MONITORING:
        print_color("ERROR: Performance monitoring module not available.", Colors.RED)
        basic_status_check()
        return
    
    try:
        # Create monitor instance
        monitor = PerformanceMonitor()
        
        # Generate report
        report_path = monitor.generate_report(include_cli_output=True)
        print_color(f"\nDetailed report saved to: {report_path}", Colors.GREEN)
        
        # Check for charts
        charts_dir = os.path.join("performance_metrics", "charts")
        if os.path.exists(charts_dir):
            chart_files = [f for f in os.listdir(charts_dir) if f.endswith('.png')]
            if chart_files:
                print_color(f"Performance charts available in: {charts_dir}", Colors.GREEN)
                print("Charts:")
                for chart in sorted(chart_files)[-3:]:  # Show the 3 most recent charts
                    print(f"- {os.path.join(charts_dir, chart)}")
    except Exception as e:
        print_color(f"Error generating report: {e}", Colors.RED)
        basic_status_check()

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="JFK Files Scraper Progress Monitor")
    parser.add_argument("--mode", choices=["monitor", "status", "report"], default="status",
                      help="Operation mode: 'monitor' for continuous monitoring, 'status' for current status, 'report' for detailed report")
    
    args = parser.parse_args()
    
    if args.mode == "monitor":
        monitor_mode()
    elif args.mode == "report":
        report_mode()
    else:  # status mode
        status_mode()

if __name__ == "__main__":
    main()
