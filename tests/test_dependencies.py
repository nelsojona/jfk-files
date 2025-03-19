#!/usr/bin/env python3
"""
Script to test if PyMuPDF, pytesseract, and pdf2image dependencies are correctly installed
and working.
"""

import sys
import os

def test_pymupdf():
    """Test if PyMuPDF is correctly installed and can be imported."""
    try:
        import fitz
        print(f"✅ PyMuPDF is available (version: {fitz.__version__})")
        return True
    except ImportError as e:
        print(f"❌ PyMuPDF import error: {e}")
        return False

def test_pytesseract():
    """Test if pytesseract is correctly installed and can be imported."""
    try:
        import pytesseract
        print(f"✅ pytesseract is available")
            
        # Try to get version by running Tesseract
        try:
            version = pytesseract.get_tesseract_version()
            print(f"   Tesseract version: {version}")
        except Exception as e:
            print(f"   Note: Tesseract binary not found or not working: {e}")
            
        return True
    except ImportError as e:
        print(f"❌ pytesseract import error: {e}")
        return False
        
def test_pdf2image():
    """Test if pdf2image is correctly installed and can be imported."""
    try:
        import pdf2image
        print(f"✅ pdf2image is available")
        
        # Try to check the version
        if hasattr(pdf2image, '__version__'):
            print(f"   Version: {pdf2image.__version__}")
        else:
            print("   Version: unknown")
            
        return True
    except ImportError as e:
        print(f"❌ pdf2image import error: {e}")
        return False

def display_python_info():
    """Display Python version and environment info."""
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Working directory: {os.getcwd()}")
    
    # Show installed packages
    try:
        import pkg_resources
        print("\nInstalled packages:")
        for pkg in pkg_resources.working_set:
            if any(name in pkg.key for name in ['pymupdf', 'pdfium', 'fitz', 'pytesseract', 'pdf2image']):
                print(f"  - {pkg.key} {pkg.version}")
    except ImportError:
        print("Could not list installed packages (pkg_resources not available)")

def check_tesseract_cli():
    """Check if tesseract CLI is available."""
    try:
        from shutil import which
        import subprocess
        tesseract_path = which('tesseract')
        if tesseract_path:
            print(f"✅ tesseract CLI is available at: {tesseract_path}")
            # Try to get version
            try:
                output = subprocess.check_output([tesseract_path, '--version'], text=True)
                print(f"   {output.split('\n')[0]}")
            except Exception as e:
                print(f"   Could not get version: {e}")
        else:
            print("❌ tesseract CLI not found in PATH")
    except Exception as e:
        print(f"❌ Error checking tesseract CLI: {e}")

if __name__ == "__main__":
    print("-" * 50)
    print("Dependency Test Script")
    print("-" * 50)
    
    display_python_info()
    
    print("\nTesting dependencies:")
    pymupdf_ok = test_pymupdf()
    pytesseract_ok = test_pytesseract()
    pdf2image_ok = test_pdf2image()
    check_tesseract_cli()
    
    print("\nSummary:")
    if pymupdf_ok:
        print("✅ Core dependency (PyMuPDF) is available!")
        if pytesseract_ok and pdf2image_ok:
            print("✅ OCR dependencies are also available!")
        else:
            print("⚠️ OCR capabilities may be limited (pytesseract and/or pdf2image missing)")
    else:
        print("❌ Core dependency PyMuPDF is missing - PDF processing will fail!")
        
    print("-" * 50)
