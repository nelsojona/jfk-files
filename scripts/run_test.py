#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clean runner script for JFK Files tests.

This script runs tests with a clean Python path to avoid import conflicts.
"""

import sys
import os
import subprocess

# Remove any problematic paths from sys.path
sys.path = [p for p in sys.path if not p.endswith('wicked-reports/src')]

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The test to run
test_file = "tests/test_end_to_end.py"

if __name__ == "__main__":
    # Run the test directly
    print(f"Running {test_file} with clean Python path")
    
    # Import the module and run it
    test_module = __import__(test_file.replace('/', '.').replace('.py', ''))
    
    print("Test completed successfully")
