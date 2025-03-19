#!/bin/bash
# Script to run PDF2MD diagnostic tests to help with OCR and PDF conversion setup

# Format output
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BOLD}=== PDF2MD Diagnostic Tool ===${NC}"
echo "This script will check your PDF2MD and OCR setup for JFK Files Scraper"
echo

# Ensure correct Python environment
if [ -d "jfk-env-py310" ]; then
    echo -e "${GREEN}Found Python environment at jfk-env-py310${NC}"
    # Activate the environment
    if [ -f "jfk-env-py310/bin/activate" ]; then
        echo "Activating Python environment..."
        source jfk-env-py310/bin/activate
    else
        echo -e "${RED}Error: Cannot find activation script in environment${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Warning: jfk-env-py310 environment not found${NC}"
    echo "Running with system Python (may not have required dependencies)"
fi

# Run the diagnostic
echo -e "\n${BOLD}Running PDF2MD diagnostic...${NC}"
python pdf2md_diagnostic.py

# Check if diagnostic output file exists
if [ -f "pdf2md_diagnosis_results.txt" ]; then
    echo -e "\n${BOLD}Results:${NC}"
    cat pdf2md_diagnosis_results.txt
else
    echo -e "\n${RED}Error: Diagnostic results file not created${NC}"
fi

# Run a test OCR conversion if a sample PDF is available
if [ -d "test_data" ] && [ -f "test_data/test_document.pdf" ]; then
    echo -e "\n${BOLD}Running OCR test on sample document...${NC}"
    python test_ocr_flow.py --pdf "test_data/test_document.pdf" --output "test_output" --compare
else
    echo -e "\n${YELLOW}No sample PDF found in test_data directory${NC}"
    echo "You can run OCR tests manually with:"
    echo "python test_ocr_flow.py --pdf path/to/document.pdf --output test_output --compare"
fi

echo -e "\n${BOLD}Diagnostic complete${NC}"
echo "See pdf2md_diagnosis_results.txt for details"
