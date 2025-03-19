#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test basic imports to ensure modules can be loaded"""

import sys
import os
import unittest

class TestImports(unittest.TestCase):
    """Test that critical modules can be imported without errors"""
    
    def test_pdf2md_import(self):
        """Test that we can import the pdf2md module without prompts"""
        # Set CI environment to prevent OpenAI key prompting
        os.environ['CI'] = 'true'
        
        try:
            import src.utils.pdf2md.pdf2md
            from src.utils.pdf2md_wrapper import PDF2MarkdownWrapper
            self.assertTrue(True, "Imports succeeded")
        except Exception as e:
            self.fail(f"Failed to import module: {e}")
    
    def test_utils_imports(self):
        """Test that we can import utility modules"""
        try:
            from src.utils import batch_utils, checkpoint_utils, conversion_utils, logging_utils
            self.assertTrue(True, "Utility imports succeeded")
        except Exception as e:
            self.fail(f"Failed to import utility modules: {e}")

if __name__ == "__main__":
    unittest.main()