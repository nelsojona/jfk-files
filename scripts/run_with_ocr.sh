#!/bin/bash
# JFK Files Scraper OCR Runner
# This script ensures the Python 3.10 environment is used for OCR processing

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Check if the Python 3.10 environment exists
if [ ! -d "$SCRIPT_DIR/jfk-env-py310" ]; then
    echo "Error: Python 3.10 environment not found at $SCRIPT_DIR/jfk-env-py310"
    echo "Please create the environment first by following the instructions in INSTALLATION.md"
    echo "Running setup script to create the environment..."
    if [ -f "$SCRIPT_DIR/setup_ocr_env.sh" ]; then
        bash "$SCRIPT_DIR/setup_ocr_env.sh"
    else
        echo "Error: setup_ocr_env.sh not found. Please create the environment manually."
        exit 1
    fi
fi

# Activate the virtual environment
echo "Activating Python 3.10 environment..."
source "$SCRIPT_DIR/jfk-env-py310/bin/activate"

# Verify Python version is 3.10
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [[ "$PYTHON_VERSION" != "3.10" ]]; then
    echo "Error: Expected Python 3.10, but got Python $PYTHON_VERSION"
    echo "The activated environment does not have the correct Python version."
    exit 1
fi

# Verify OCR dependencies
echo "Checking OCR dependencies..."

# Check for PyMuPDF - using proper multiline Python code
PYMUPDF_STATUS=$(python -c $'
try:
    import fitz
    print("PyMuPDF available (version " + fitz.__version__ + ")")
except Exception as e:
    print("PyMuPDF not available: " + str(e))
')
echo "- $PYMUPDF_STATUS"

# If PyMuPDF is not available, install it
if [[ "$PYMUPDF_STATUS" == *"not available"* ]]; then
    echo "Installing PyMuPDF..."
    pip install PyMuPDF
fi

# Check for pdf2md_wrapper
PDF2MD_STATUS=$(python -c $'
try:
    from src.utils.pdf2md_wrapper import PDF2MarkdownWrapper
    print("PDF2MarkdownWrapper available")
except Exception as e:
    print("PDF2MarkdownWrapper not available: " + str(e))
')
echo "- $PDF2MD_STATUS"

# Check for torch (required for some OCR operations)
TORCH_STATUS=$(python -c "
try:
    import torch
    print('PyTorch available (version ' + torch.__version__ + ')')
except Exception as e:
    print('PyTorch not available: ' + str(e))
")
echo "- $TORCH_STATUS"

# Check for pytesseract
TESSERACT_STATUS=$(python -c "
try:
    import pytesseract
    print('Pytesseract available!')
except Exception as e:
    print('Pytesseract not available: ' + str(e))
")
echo "- $TESSERACT_STATUS"

# Run the JFK scraper with the specified arguments
echo ""
echo "Running JFK scraper with OCR enabled..."
echo "Command: python jfk_scraper.py $@"
echo ""

# Execute the script with all arguments passed to this script
python jfk_scraper.py "$@"

# Keep the result status
EXIT_STATUS=$?

# Deactivate the virtual environment
deactivate

exit $EXIT_STATUS