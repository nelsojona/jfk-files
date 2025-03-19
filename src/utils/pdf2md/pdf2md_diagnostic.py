#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF2MD diagnostic script to check the installation and capabilities of the OCR components.
This helps verify dependencies needed for PDF to Markdown conversion with OCR processing.
"""

import os
import sys
import logging
import importlib.util
import platform
import subprocess
import traceback
import json

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("pdf2md_diagnostic")

def check_python_version():
    """Check if Python version is compatible with PDF2MD."""
    python_version = platform.python_version()
    version_parts = [int(x) for x in python_version.split('.')]
    
    # PDF2MD requires Python 3.10+
    is_compatible = (version_parts[0] >= 3 and version_parts[1] >= 10)
    
    logger.info(f"Python version: {python_version} {'✅' if is_compatible else '❌'}")
    if not is_compatible:
        logger.warning("Python 3.10 or higher is required for PDF2MD")
    
    return is_compatible

def check_module_installed(module_name):
    """Check if a Python module is installed."""
    spec = importlib.util.find_spec(module_name)
    is_installed = spec is not None
    
    logger.info(f"Module {module_name}: {'✅ Installed' if is_installed else '❌ Not installed'}")
    return is_installed

def check_package_version(package_name):
    """Check the version of an installed package."""
    try:
        if package_name == "marker":
            # Special handling for marker package which might have different import names
            for marker_package in ["marker", "marker_pdf"]:
                try:
                    module = __import__(marker_package)
                    version = getattr(module, "__version__", "unknown")
                    logger.info(f"Package {marker_package}: ✅ Version {version}")
                    return True, version
                except ImportError:
                    continue
            logger.warning(f"Package {package_name}: ❌ Not found")
            return False, None
        else:
            module = __import__(package_name)
            version = getattr(module, "__version__", "unknown")
            logger.info(f"Package {package_name}: ✅ Version {version}")
            return True, version
    except ImportError:
        logger.warning(f"Package {package_name}: ❌ Not found")
        return False, None
    except Exception as e:
        logger.error(f"Error checking {package_name} version: {e}")
        return False, None

def check_tesseract_installation():
    """Check if Tesseract OCR is installed and get its version."""
    try:
        # Try to run tesseract command to check version
        result = subprocess.run(
            ["tesseract", "--version"], 
            capture_output=True, 
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            # Extract version from output
            version_line = result.stdout.split('\n')[0]
            logger.info(f"Tesseract OCR: ✅ {version_line}")
            
            # Check available languages
            result = subprocess.run(
                ["tesseract", "--list-langs"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                languages = result.stdout.strip().split('\n')[1:]  # Skip the first line, which is a header
                logger.info(f"Tesseract Languages: {', '.join(languages)}")
                
            return True, version_line
        else:
            logger.warning("Tesseract OCR: ❌ Not found or error running command")
            return False, None
    except Exception as e:
        logger.error(f"Error checking Tesseract installation: {e}")
        return False, None

def check_gpu_support():
    """Check if PyTorch has GPU support."""
    try:
        import torch
        has_cuda = torch.cuda.is_available()
        device_count = torch.cuda.device_count() if has_cuda else 0
        device_info = []
        
        if has_cuda:
            for i in range(device_count):
                device_info.append(f"{i}: {torch.cuda.get_device_name(i)}")
        
        logger.info(f"PyTorch GPU support: {'✅ Available' if has_cuda else '❌ Not available'}")
        if has_cuda:
            logger.info(f"GPU devices ({device_count}): {', '.join(device_info)}")
        
        return has_cuda, device_info
    except ImportError:
        logger.warning("PyTorch: ❌ Not installed")
        return False, []
    except Exception as e:
        logger.error(f"Error checking GPU support: {e}")
        return False, []

# Removed try_load_marker function as it's no longer needed

def check_pdf2md_wrapper():
    """Check if the pdf2md_wrapper.py exists and can be imported."""
    try:
        # Try to import the wrapper directly first
        try:
            from src.utils.pdf2md_wrapper import PDF2MarkdownWrapper, convert_pdf_to_markdown
            logger.info("pdf2md_wrapper: ✅ Imported successfully")
            
            # Check available components
            wrapper = PDF2MarkdownWrapper()
            available_modules = []
            if wrapper.pymupdf_available:
                available_modules.append("PyMuPDF")
            if wrapper.pytesseract_available:
                available_modules.append("pytesseract")
            if wrapper.pdf2image_available:
                available_modules.append("pdf2image")
            if wrapper.pdf2md_available:
                available_modules.append("pdf2md")
                
            logger.info(f"Available modules: {', '.join(available_modules)}")
            return True
        except ImportError:
            # Try to find the file
            try:
                import os
                pdf2md_path = os.path.join("src", "utils", "pdf2md_wrapper.py")
                if os.path.exists(pdf2md_path):
                    logger.info(f"pdf2md_wrapper.py found at {pdf2md_path} but cannot be imported")
                else:
                    logger.warning(f"pdf2md_wrapper.py not found at {pdf2md_path}")
                return False
            except Exception as e:
                logger.error(f"Error checking pdf2md_wrapper path: {e}")
                return False
    except Exception as e:
        logger.error(f"Error checking pdf2md_wrapper: {e}")
        return False

def check_environment_variables():
    """Check for relevant environment variables."""
    # Variables that might affect OCR and PDF processing
    variables_to_check = [
        "PYTHONPATH",
        "TESSDATA_PREFIX",
        "PATH",
        "LD_LIBRARY_PATH",  # Linux
        "DYLD_LIBRARY_PATH"  # macOS
    ]
    
    env_info = {}
    for var in variables_to_check:
        if var in os.environ:
            env_info[var] = os.environ[var]
            logger.info(f"Environment variable {var}: ✅ Set to {os.environ[var]}")
        else:
            env_info[var] = None
            logger.info(f"Environment variable {var}: ℹ️ Not set")
    
    return env_info

def run_diagnostic():
    """Run all diagnostic checks and return a summary."""
    logger.info("=== Running PDF2MD Diagnostic ===")
    
    # Store results
    results = {
        "timestamp": None,
        "system_info": {},
        "python": {},
        "packages": {},
        "pdf2md": {},
        "ocr": {},
        "environment": {},
        "success": False
    }
    
    # System info
    results["system_info"]["os"] = platform.system()
    results["system_info"]["os_version"] = platform.version()
    results["system_info"]["os_release"] = platform.release()
    results["system_info"]["architecture"] = platform.machine()
    
    logger.info(f"System: {results['system_info']['os']} {results['system_info']['os_release']} ({results['system_info']['architecture']})")
    
    # Check Python version
    python_ok = check_python_version()
    results["python"]["version"] = platform.python_version()
    results["python"]["compatible"] = python_ok
    
    # Check required packages
    required_packages = ["torch", "fitz", "numpy", "PIL", "pytesseract"]
    results["packages"]["installed"] = {}
    
    for package in required_packages:
        installed = check_module_installed(package)
        results["packages"]["installed"][package] = installed
    
    # Special handling for PyMuPDF - it provides the 'fitz' module
    if results["packages"]["installed"]["fitz"]:
        results["packages"]["installed"]["PyMuPDF"] = True
        logger.info("Module PyMuPDF: ✅ Installed (via fitz module)")
    else:
        results["packages"]["installed"]["PyMuPDF"] = False
    
    # Check pdf2md_wrapper installation
    pdf2md_ok = check_pdf2md_wrapper()
    results["pdf2md"]["loaded"] = pdf2md_ok
    
    # Check Tesseract installation
    tesseract_ok, tesseract_version = check_tesseract_installation()
    results["ocr"]["tesseract_installed"] = tesseract_ok
    results["ocr"]["tesseract_version"] = tesseract_version
    
    # Check GPU support
    gpu_available, gpu_devices = check_gpu_support()
    results["ocr"]["gpu_available"] = gpu_available
    results["ocr"]["gpu_devices"] = gpu_devices
    
    # Check environment variables
    results["environment"] = check_environment_variables()
    
    # No longer check for Marker as it's been removed
    
    # Determine overall success - consider it successful if:
    # 1. pdf2md_wrapper is available 
    # AND
    # 2. PyMuPDF is available
    # Additional OCR functionality if pytesseract is available
    pymupdf_ok = results["packages"]["installed"]["PyMuPDF"]
    pytesseract_ok = results["packages"]["installed"].get("pytesseract", False)
    
    results["success"] = python_ok and pdf2md_ok and pymupdf_ok
    
    logger.info("\n=== Diagnostic Summary ===")
    
    if results["success"]:
        if pytesseract_ok:
            logger.info("✅ PDF2MD and OCR components are properly installed and ready to use.")
        else:
            logger.info("✅ PDF2MD is properly installed and ready to use.")
            logger.info("Note: Using PyMuPDF text extraction (OCR features not available)")
            logger.info("To enable OCR: pip install pytesseract pdf2image")
    else:
        logger.warning("❌ Some issues were detected with the installation.")
        
        missing_components = []
        if not python_ok:
            missing_components.append("Python 3.10+")
        if not pdf2md_ok:
            missing_components.append("pdf2md_wrapper")
        if not pymupdf_ok:
            missing_components.append("PyMuPDF library")
        if not pytesseract_ok and not tesseract_ok:
            missing_components.append("Pytesseract and/or Tesseract OCR")
        
        if missing_components:
            logger.warning(f"Missing required components: {', '.join(missing_components)}")
            
        logger.info("To install required components:")
        logger.info("1. pip install PyMuPDF")
        logger.info("2. For OCR capabilities: pip install pytesseract pdf2image")
        logger.info("3. On Linux/Mac, install system Tesseract: apt-get install tesseract-ocr or brew install tesseract")
    
    # Save results to file
    try:
        with open("pdf2md_diagnosis_results.txt", "w") as f:
            f.write("=== PDF2MD Diagnostic Results ===\n\n")
            f.write(f"System: {results['system_info']['os']} {results['system_info']['os_release']} ({results['system_info']['architecture']})\n")
            f.write(f"Python: {results['python']['version']} {'✅' if results['python']['compatible'] else '❌'}\n")
            f.write("\nPackages:\n")
            for package, status in results["packages"]["installed"].items():
                f.write(f"- {package}: {'✅' if status else '❌'}\n")
            f.write(f"\nPDF2MD Wrapper: {'✅ Loaded' if results['pdf2md']['loaded'] else '❌ Not loaded'}\n")
            f.write(f"Tesseract OCR: {'✅ ' + results['ocr']['tesseract_version'] if results['ocr']['tesseract_installed'] else '❌ Not installed'}\n")
            f.write(f"GPU Support: {'✅ Available' if results['ocr']['gpu_available'] else '❌ Not available'}\n")
            if results['ocr']['gpu_available'] and results['ocr']['gpu_devices']:
                f.write(f"GPU Devices: {', '.join(results['ocr']['gpu_devices'])}\n")
            
            # No longer show Marker info
            
            f.write("\nOverall Status: ")
            if results["success"]:
                f.write("✅ Ready to use\n")
                if 'pytesseract' in results["packages"]["installed"] and results["packages"]["installed"]['pytesseract']:
                    f.write("PDF2MD wrapper is available with OCR capabilities\n")
                else:
                    f.write("PDF2MD wrapper is available with basic text extraction\n")
                    f.write("To enable OCR features: pip install pytesseract pdf2image\n")
                    
                # System requirements for OCR
                if not results['ocr']['tesseract_installed']:
                    f.write("\nSystem Tesseract not detected. To install:\n")
                    if results['system_info']['os'] == "Linux":
                        f.write("- Ubuntu/Debian: sudo apt-get install tesseract-ocr\n")
                        f.write("- For PDF to image support: sudo apt-get install poppler-utils\n")
                    elif results['system_info']['os'] == "Darwin":  # macOS
                        f.write("- macOS: brew install tesseract\n")
                        f.write("- For PDF to image support: brew install poppler\n")
                    elif results['system_info']['os'] == "Windows":
                        f.write("- Windows: Download and install from https://github.com/UB-Mannheim/tesseract/wiki\n")
            else:
                f.write("❌ Configuration issues detected\n")
                # List missing components
                missing_components = []
                if not results["python"]["compatible"]:
                    missing_components.append("Python 3.10+")
                if not results['pdf2md']['loaded']:
                    missing_components.append("pdf2md_wrapper")
                if not results["packages"]["installed"]["PyMuPDF"]:
                    missing_components.append("PyMuPDF")
                
                if missing_components:
                    f.write(f"Missing required components: {', '.join(missing_components)}\n")
            
        logger.info("Results saved to pdf2md_diagnosis_results.txt")
    except Exception as e:
        logger.error(f"Error saving results: {e}")
    
    return results

if __name__ == "__main__":
    run_diagnostic()
