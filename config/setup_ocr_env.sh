#!/bin/bash
# Setup script for OCR dependencies in Python 3.10 environment
# This script creates and configures a Python 3.10 environment with all required OCR dependencies

# Set environment name
ENV_NAME="jfk-env-py310"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "===================================================================="
echo "JFK Files OCR Environment Setup"
echo "===================================================================="
echo "This script will set up a Python 3.10 environment with all required"
echo "OCR dependencies for the JFK Files Scraper."
echo ""

# Check if Python 3.10 is available
if command -v python3.10 &> /dev/null; then
    echo "✅ Python 3.10 found"
    PYTHON_CMD="python3.10"
else
    echo "❌ Python 3.10 not found!"
    echo "Please install Python 3.10 before continuing."
    echo "On macOS: brew install python@3.10"
    echo "On Ubuntu: sudo apt install python3.10 python3.10-venv"
    exit 1
fi

# Check if virtual environment exists
if [ -d "$SCRIPT_DIR/$ENV_NAME" ]; then
    echo "🔄 Environment $ENV_NAME already exists. Updating packages..."
    source "$SCRIPT_DIR/$ENV_NAME/bin/activate"
else
    echo "🔧 Creating new Python 3.10 environment: $ENV_NAME"
    $PYTHON_CMD -m venv "$SCRIPT_DIR/$ENV_NAME"
    source "$SCRIPT_DIR/$ENV_NAME/bin/activate"
fi

# Verify activated environment is using Python 3.10
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [[ "$PYTHON_VERSION" != "3.10" ]]; then
    echo "❌ Error: Expected Python 3.10, but got Python $PYTHON_VERSION"
    echo "The virtual environment is not using the correct Python version."
    deactivate
    exit 1
fi

# Upgrade pip
echo "🔄 Upgrading pip..."
pip install --upgrade pip

# Install dependencies in order of importance
echo "📦 Installing core dependencies..."
pip install PyMuPDF pymupdf-fonts pypdfium2

echo "📦 Installing pdf2md dependencies..."
pip install pdf2image backoff openai Pillow

echo "📦 Installing OCR dependencies..."
pip install marker-pdf pytesseract pdfplumber

echo "📦 Installing machine learning dependencies..."
pip install torch torchvision transformers nltk

echo "📦 Installing web scraping dependencies..."
pip install crawl4ai requests beautifulsoup4

echo "📦 Installing data processing dependencies..."
pip install pandas numpy jsonschema

echo "📦 Installing monitoring and utility dependencies..."
pip install matplotlib psutil tqdm python-dotenv cchardet chardet ftfy

echo "📦 Installing testing dependencies..."
pip install pytest pytest-cov

# Install all requirements from requirements.txt
echo "📦 Installing all dependencies from requirements.txt..."
pip install -r "$SCRIPT_DIR/requirements.txt"

# Verify key installations
echo "🔍 Verifying installations..."

# Check PyMuPDF
python -c "
try:
    import fitz
    print(f'✅ PyMuPDF installed (version {fitz.__version__})')
except ImportError as e:
    print(f'❌ PyMuPDF not installed: {e}')
"

# Check marker-pdf
python -c "
try:
    import marker_pdf
    print('✅ marker-pdf installed')
except ImportError as e:
    print(f'❌ marker-pdf not installed: {e}')
"

# Check torch
python -c "
try:
    import torch
    print(f'✅ PyTorch installed (version {torch.__version__})')
except ImportError as e:
    print(f'❌ PyTorch not installed: {e}')
"

echo "===================================================================="
echo "✅ Setup complete!"
echo "To activate this environment, run:"
echo "source $ENV_NAME/bin/activate"
echo ""
echo "Or use the provided wrapper script:"
echo "./run_with_ocr.sh --scrape-all --ocr"
echo "===================================================================="

# Deactivate the environment
deactivate