# JFK Files Scraper - Installation Guide

This guide will help you set up the environment required to run the JFK Files Scraper with all its features enabled, including OCR capabilities.

## Prerequisites

- **Python**: Version 3.10 or newer (recommended for optimal OCR capabilities)
- **Disk Space**: At least 2GB free space for dependencies and downloaded files
- **Internet Connection**: Required for web scraping and downloading PDFs
- **Node.js & npm**: Optional, required if using the @opendocsg/pdf2md converter

## Automated Installation (Recommended)

We provide an automated setup script that creates a Python 3.10 virtual environment with all required dependencies:

```bash
# Make the script executable if needed
chmod +x setup_ocr_env.sh

# Run the setup script
./setup_ocr_env.sh
```

This script will:
1. Check if Python 3.10 is available
2. Create a virtual environment named `jfk-env-py310`
3. Install all necessary dependencies
4. Verify key packages are correctly installed

After the script completes, you can run the scraper with:

```bash
./run_with_ocr.sh --scrape-all --ocr
```

## Manual Installation

If you prefer to set up the environment manually, follow these steps:

### Step 1: Check Your Python Version

```bash
python --version
```

If your Python version is below 3.10, install Python 3.10:

#### macOS (using brew)
```bash
brew install python@3.10
```

#### macOS (using pyenv)
```bash
brew install pyenv
pyenv install 3.10.0
pyenv global 3.10.0
```

#### Windows
Download the latest Python 3.10+ installer from [python.org](https://www.python.org/downloads/).

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3.10 python3.10-venv python3.10-dev
```

### Step 2: Create a Python 3.10 Virtual Environment

```bash
# Create a virtual environment (use python3.10 explicitly)
python3.10 -m venv jfk-env-py310

# Activate the virtual environment
# On Windows:
jfk-env-py310\Scripts\activate
# On macOS/Linux:
source jfk-env-py310/bin/activate
```

### Step 3: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

## Dependencies Overview

The JFK Files Scraper requires several key dependency categories:

### 1. PDF Processing and OCR

These libraries are used for PDF text extraction and OCR:

- **PyMuPDF** (`pip install PyMuPDF`): Core PDF processing, imported as `fitz` in code
- **pdf2image** (`pip install pdf2image`): PDF to image conversion for OCR processing
- **pytesseract** (`pip install pytesseract`): OCR fallback option
- **pdfplumber** (`pip install pdfplumber`): Alternative PDF text extraction

### 2. Machine Learning Dependencies

Optional dependencies for enhanced OCR capabilities:

- **torch** (`pip install torch`): PyTorch for deep learning
- **torchvision** (`pip install torchvision`): Computer vision extensions for PyTorch
- **transformers** (`pip install transformers`): Hugging Face transformers library

### 3. Web Scraping

For downloading JFK files from the National Archives:

- **crawl4ai** (`pip install crawl4ai`): Advanced web crawling
- **requests** (`pip install requests`): HTTP library
- **beautifulsoup4** (`pip install beautifulsoup4`): HTML parsing

### 4. Data Processing and Utilities

For handling the scraped data:

- **pandas** & **numpy**: Data manipulation
- **jsonschema**: JSON validation
- **matplotlib** & **psutil**: Performance monitoring
- **tqdm**: Progress bars

## Verify Installation

To verify that all dependencies are correctly installed, run:

```bash
# Check PyMuPDF
python -c "import fitz; print('PyMuPDF:', fitz.__version__)"

# Check OCR capabilities
python -c "try: import pytesseract, pdf2image; print('OCR libraries: Available'); except ImportError as e: print(f'OCR libraries not available: {e}')"

# Check PyTorch
python -c "import torch; print('PyTorch:', torch.__version__)"
```

## Troubleshooting

### PyMuPDF Issues

- **Linux dependencies**: `sudo apt install libmupdf-dev`
- **macOS dependencies**: `brew install mupdf`
- **Import error**: If you see "frontend not found" errors, try `pip install --upgrade pip setuptools wheel` before reinstalling PyMuPDF

### OCR Issues

- **Python version**: Pytesseract works best with Python 3.8+ 
- **Missing Tesseract**: Make sure tesseract-ocr is installed on your system:
  ```bash
  # Ubuntu/Debian
  sudo apt-get install tesseract-ocr
  # macOS
  brew install tesseract
  ```
- **PDF conversion**: For pdf2image on Linux, you may need:
  ```bash
  sudo apt-get install poppler-utils
  ```

### General Solutions

- **Clear pip cache**: `pip cache purge`
- **Reinstall problematic packages**: `pip install --force-reinstall [package]`
- **Install dependencies one by one**: For memory issues, install large packages separately

## Using Fallback Methods

If you can't install all OCR dependencies, the script will use fallbacks:

1. **PyMuPDF text extraction**: Simpler but works with searchable PDFs
2. **Basic text extraction**: Will extract whatever text is available
3. **Simple fallback**: Will create basic markdown structure without text extraction

You can still run the scraper even if OCR isn't fully available:

```bash
python jfk_scraper.py --scrape-all
```

For best results with OCR functionality:

```bash
./run_with_ocr.sh --scrape-all --ocr
```
