# JFK Files Scraper

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![OCR Support](https://img.shields.io/badge/OCR-Supported-green.svg)](https://github.com/tesseract-ocr/tesseract)
[![GPT Integration](https://img.shields.io/badge/GPT-Integration-orange.svg)](https://platform.openai.com/)

A Python tool for scraping JFK files from the National Archives website, handling pagination, and transforming data from PDF to Markdown to JSON for use as a "Lite LLM" dataset. Includes advanced optimization, performance monitoring, and custom GPT integration for the complete collection of 1,123 declassified documents.

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Installation](#installation)
  - [Development Environment](#development-environment)
  - [Dependencies](#dependencies)
  - [OCR Setup](#ocr-setup)
  - [GPT Integration Setup](#gpt-integration-setup)
- [Usage](#usage)
  - [Basic Operation](#basic-operation)
  - [Command-Line Options](#command-line-options)
  - [Example Commands](#example-commands)
  - [Performance Monitoring](#performance-monitoring)
- [Output Structure](#output-structure)
- [PDF to Markdown Conversion](#pdf-to-markdown-conversion)
  - [Key Features](#key-features)
  - [Testing OCR Capabilities](#testing-ocr-capabilities)
- [Testing](#testing)
- [Advanced Optimization](#advanced-optimization)
- [GPT Integration](#gpt-integration)
  - [GPT Components](#gpt-components)
  - [Using the JFK Files Archivist GPT](#using-the-jfk-files-archivist-gpt)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## 🔍 Project Overview

This project aims to:

1. Scrape JFK file URLs from the [National Archives website](https://www.archives.gov/research/jfk/release-2025)
2. Handle pagination across approximately 113 pages with 1,123 entries
3. Download PDF files from the extracted URLs with parallel processing
4. Convert PDF files to Markdown format with PDF2MD wrapper and OCR capabilities
5. Transform Markdown to JSON format with robust conversion methods
6. Store the processed data for later use as a "Lite LLM" dataset
7. Provide optimization for large-scale processing with adaptive resource management
8. Include comprehensive performance monitoring and visualization
9. Create a custom GPT (JFK Files Archivist) with the processed data
10. Provide tools for querying and analyzing the declassified documents

## ✨ Features

- **Robust Web Scraping**: Handles pagination, rate limiting, and network retries
- **Parallel Processing**: Concurrent downloads with adaptive thread management
- **Smart PDF Processing**:
  - Automatic detection of scanned vs. digital documents
  - OCR support for scanned documents with quality options
  - Document repair capabilities for problematic PDFs
- **Enhanced Markdown Conversion**:
  - Multiple conversion strategies
  - Quality validation and post-processing
  - Fallback mechanisms for reliability
- **JSON Transformation**:
  - Structured format for GPT integration
  - Document metadata extraction
  - Full-text and section-based organization
- **Performance Optimization**:
  - Adaptive thread pool with resource monitoring
  - Checkpointing for resumable operations
  - Memory usage optimization for large-scale processing
- **Monitoring & Visualization**:
  - Real-time performance metrics
  - Resource usage tracking
  - Visual progress indicators and charts
- **GPT Integration**:
  - Configurable GPT capabilities
  - Optimized knowledge upload
  - Test suite for query validation

## 🏗️ System Architecture

The JFK Files Scraper follows a pipeline architecture with these stages:

```mermaid
flowchart LR
    Scrape[Web Scraping] --> Download[PDF Download]
    Download --> PDFtoMD[PDF to Markdown]
    PDFtoMD --> MDtoJSON[Markdown to JSON]
    MDtoJSON --> Store[Storage]
    Store --> GPTPrep[GPT Preparation]
    GPTPrep --> GPTUpload[GPT Upload]
```

Key components:
- **Crawler**: Handles webpage navigation and link extraction
- **Downloader**: Manages parallel retrieval and storage of PDF files
- **Transformer**: Coordinates the PDF → Markdown → JSON pipeline
- **Storage**: Handles file I/O and data persistence
- **Performance Monitor**: Tracks resource usage and optimization opportunities
- **GPT Integrator**: Prepares and uploads data for GPT knowledge base

## 📥 Installation

### Development Environment

This project uses a Python environment with specific dependencies. Set up using either:

**Option 1: Python venv**

```bash
# Create and activate virtual environment
python -m venv jfk-env-py310
source jfk-env-py310/bin/activate  # Linux/macOS
# OR
jfk-env-py310\Scripts\activate  # Windows

# Install dependencies
pip install -r config/requirements.txt
```

**Option 2: Conda Environment**

```bash
# Create and activate conda environment
conda create -n jfkfiles_env python=3.10
conda activate jfkfiles_env

# Install dependencies
pip install -r config/requirements.txt
```

For automatic environment activation with direnv:
```bash
# Create .envrc file
echo "layout python3" > .envrc
direnv allow
```

### Dependencies

The project requires various Python packages and system dependencies:

**Python Packages**
```bash
pip install -r config/requirements.txt
```

Key Python dependencies include:
- Crawl4AI for web scraping
- PyMuPDF (fitz) for PDF processing
- pytesseract and pdf2image for OCR
- psutil for system monitoring
- matplotlib for visualization
- openai and tiktoken for GPT integration

### OCR Setup

For OCR functionality, install these system dependencies:

**Linux (Ubuntu/Debian)**
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils
```

**macOS**
```bash
brew install tesseract poppler
```

**Windows**
1. Download and install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
2. Add Tesseract to your PATH environment variable
3. Install poppler from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases)
4. Add poppler bin directory to your PATH

Verify your OCR installation:
```bash
scripts/run_pdf2md_diagnostic.sh
```

### GPT Integration Setup

For GPT functionality:
```bash
pip install openai tiktoken
```

Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## 🚀 Usage

### Basic Operation

```bash
python src/jfk_scraper.py
```

### Command-Line Options

```
--url               Base URL for the JFK records page (default: https://www.archives.gov/research/jfk/release-2025)
--start-page        Page to start scraping from (default: 1)
--end-page          Page to end scraping at (default: scrape all pages)
--limit             Limit the number of files to process
--test              Run in test mode with a single PDF
--threads           Number of parallel download threads (default: 5)
--rate-limit        Delay between starting new downloads in seconds (default: 0.5)
--checkpoint-interval Save checkpoint after processing this many files (default: 10)
--ocr               Enable OCR processing for scanned documents
--force-ocr         Force OCR processing for all documents
--ocr-quality       OCR quality setting: low, medium, high (default: high)
--resume            Resume from last checkpoint if available
--clean             Clean all checkpoints before starting
--log-level         Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
--max-workers       Maximum number of concurrent downloads
--scrape-all        Scrape all 113 pages and process all 1,123 files
--organize          Organize PDFs into subdirectories by collection (default: True)
--flat              Save PDFs in a flat directory structure
```

### Example Commands

**Basic Usage**
```bash
# Scrape and process a few files for testing
python src/jfk_scraper.py --start-page 1 --end-page 2 --limit 5
```

**OCR Processing**
```bash
# Process all PDFs with OCR support
python src/jfk_scraper.py --ocr

# Control OCR quality (low, medium, high - default is high)
python src/jfk_scraper.py --ocr --ocr-quality medium 

# Force OCR for all documents (even if they appear to be digital)
python src/jfk_scraper.py --force-ocr --ocr-quality high

# Run in test mode with OCR
python src/jfk_scraper.py --test --force-ocr --ocr-quality high
```

**OCR with Convenience Script**
```bash
scripts/run_with_ocr.sh --scrape-all --ocr
scripts/run_with_ocr.sh --scrape-all --ocr --ocr-quality medium
scripts/run_with_ocr.sh --scrape-all --force-ocr
```

**Testing**
```bash
# Test with a single file
python src/jfk_scraper.py --test
```

**Large-Scale Processing**
```bash
# Process specific page range with resource optimization
python src/jfk_scraper.py --start-page 5 --end-page 10 --max-workers 8 --checkpoint-interval 20

# Process all files with maximum optimization
python src/jfk_scraper.py --scrape-all --max-workers 12 --checkpoint-interval 50

# Resume processing from last checkpoint
python src/jfk_scraper.py --resume --max-workers 8
```

### Performance Monitoring

Two options for monitoring performance:

**Using the Performance Monitoring Module**
```bash
python -m src.performance_monitoring --mode monitor
```

**Using the Simplified Monitor Script**
```bash
# View current status
python src/utils/monitor_progress.py --mode status

# Continuous monitoring
python src/utils/monitor_progress.py --mode monitor

# Generate detailed report
python src/utils/monitor_progress.py --mode report
```

Both tools support these monitoring options:
```
--mode              Operation mode: 'monitor' for continuous monitoring, 'status' for current status, 'report' for one-time report
--interval          Metrics collection interval in seconds (default: 5)
--report-interval   Report generation interval in seconds (default: 300)
```

## 📂 Output Structure

The project is organized with the following directory structure:

```
jfk-files/
├── config/                # Configuration files
├── data/                  # Data files
│   ├── json/              # Individual JSON files for each document
│   ├── lite_llm/          # Processed JSON data for Lite LLM dataset
│   │   ├── consolidated_jfk_files.json   # Combined file for GPT upload
│   │   └── gpt_configuration.json        # GPT configuration settings
│   ├── markdown/          # Converted Markdown files
│   └── pdfs/              # Downloaded PDF files
│       └── nara-104/      # Organized by collection
├── docs/                  # Documentation files
├── env/                   # Environment files
├── logs/                  # Log files
├── memory-bank/           # Project memory and context
├── metrics/               # Performance monitoring data
│   ├── charts/            # Generated performance visualization charts
│   ├── metrics.csv        # CSV file with detailed metrics history
│   └── metrics.json       # Latest performance report in JSON format
├── scripts/               # Helper scripts
├── src/                   # Source code
├── test_data/             # Test data files
├── test_output/           # Test output files
└── tests/                 # Test suite
```

## 📄 PDF to Markdown Conversion

The project uses a custom PDF2MD implementation with extensive capabilities:

### Key Features

- **Smart Document Format Detection**: Automatically detects if a PDF is scanned or digital
- **Multi-tier Conversion Strategy**: Uses different approaches based on document type
- **OCR Support**: Integrated OCR for scanned documents using pytesseract
- **Adaptive Quality Settings**: Low, medium, and high-quality OCR modes (150, 200, 300 DPI)
- **Post-processing**: Improves markdown output with consistent formatting
- **Fallback Mechanisms**: Multiple fallback strategies if primary conversion fails
- **Performance Optimization**: Efficient resource usage for large-scale processing
- **Document Repair**: Handles problematic PDFs with repair capabilities

### Testing OCR Capabilities

Test the PDF to Markdown conversion with these utilities:

```bash
# Test with default settings (no OCR)
python tests/test_pdf2md.py path/to/your/document.pdf

# Test with OCR enabled
python tests/test_ocr_flow.py --pdf path/to/your/document.pdf --force-ocr

# Compare different OCR quality levels
python tests/test_ocr_flow.py --pdf path/to/your/document.pdf --compare --output test_output

# Test different OCR quality settings
python tests/test_ocr_flow.py --pdf path/to/your/document.pdf --force-ocr --quality low
python tests/test_ocr_flow.py --pdf path/to/your/document.pdf --force-ocr --quality medium
python tests/test_ocr_flow.py --pdf path/to/your/document.pdf --force-ocr --quality high
```

Run the OCR diagnostic script to verify your system setup:
```bash
scripts/run_pdf2md_diagnostic.sh
```

## 🧪 Testing

The project includes a comprehensive test suite for validating all components:

```bash
# Run all tests
pytest tests/

# Run specific test categories
python tests/test_validate_pdf_to_markdown.py
python tests/test_verify_markdown_structure.py
python tests/test_markdown_to_json_validation.py
python tests/test_verify_json_lite_llm.py
python src/gpt/test_gpt_queries.py
python tests/test_end_to_end.py

# Test with verbose output
pytest -v tests/test_api.py
```

## ⚙️ Advanced Optimization

For large-scale processing with advanced optimization features:

```bash
# Use the optimization module directly
python -c "from src.optimization import optimize_full_scale_processing; optimize_full_scale_processing()"

# Run with all optimization flags
python jfk_scraper.py --scrape-all --max-workers auto --checkpoint-interval 30 --ocr --ocr-quality high
```

The optimization module provides:
- Adaptive thread pool that adjusts based on system resources
- Memory usage monitoring and throttling to prevent OOM errors
- Enhanced checkpointing with atomic writes and versioning
- Optimized PDF processing with parallel OCR for suitable documents

## 🤖 GPT Integration

The project includes components for creating a custom GPT with the JFK files collection:

### GPT Components

- `src/gpt/gpt_config.py`: Configuration for the JFK Files Archivist GPT
- `src/gpt/upload_to_gpt.py`: Script for uploading consolidated JSON to GPT
- `src/gpt/test_gpt_queries.py`: Test script for validating GPT query capabilities
- `src/gpt/refine_instructions.py`: Script for refining GPT instructions based on test results
- `src/gpt/documentation/gpt_usage_guidelines.md`: Comprehensive usage guidelines

### Using the JFK Files Archivist GPT

The JFK Files Archivist GPT provides access to and analysis of the complete collection of declassified JFK files.

**Setup**
```bash
# Configure the GPT settings
python -m src.gpt.gpt_config

# Upload the consolidated JSON file to GPT knowledge
python -m src.gpt.upload_to_gpt

# Test the GPT with sample queries
python -m src.gpt.test_gpt_queries
```

**Capabilities**
1. Retrieve specific documents by record ID
2. Search across documents for topics, people, or events
3. Analyze connections between documents
4. Get historical context for the documents

For detailed usage guidelines, see `src/gpt/documentation/gpt_usage_guidelines.md`

## 📁 Project Structure

```
jfk-files/
├── config/                     # Configuration files
│   ├── requirements.txt        # Python dependencies
│   ├── project_sync.yaml       # Project sync configuration
│   └── setup_ocr_env.sh        # OCR environment setup script
├── data/                       # Data files
│   ├── json/                   # Individual JSON files for each document
│   ├── lite_llm/               # Processed JSON data for Lite LLM dataset
│   │   ├── consolidated_jfk_files.json   # Combined file for GPT upload
│   │   ├── gpt_configuration.json        # GPT configuration settings
│   │   └── validation_report.md          # Validation report for GPT data
│   ├── markdown/               # Converted Markdown files
│   └── pdfs/                   # Downloaded PDF files
│       └── nara-104/           # Organized by collection
├── docs/                       # Documentation
│   ├── CODE_OF_CONDUCT.md      # Code of conduct guidelines
│   ├── CONTRIBUTING.md         # Contribution guidelines
│   ├── INSTALLATION.md         # Installation guide
│   ├── LICENSE                 # License information
│   ├── README.md               # This file
│   ├── RELEASE_NOTES.md        # Release notes
│   ├── ROADMAP.md              # Project roadmap
│   ├── RUN.md                  # Running instructions
│   ├── SECURITY.md             # Security guidelines
│   ├── TASKLIST.md             # Project task list
│   └── refactoring_summary.md  # Summary of refactoring changes
├── env/                        # Environment files
│   ├── activate_env.sh         # Environment activation script
│   ├── activate_jfk_env.sh     # JFK environment activation script
│   └── jfk-env-py310/          # Python virtual environment
├── logs/                       # Log files
│   ├── jfk_scraper.log         # Main scraper log
│   ├── jfk_scraper_errors.log  # Error logs
│   └── run_output.log          # Run output logs
├── metrics/                    # Performance metrics
│   ├── charts/                 # Performance visualization charts
│   ├── marker_diagnosis_results.txt # Marker diagnosis results
│   ├── metrics.json            # Metrics in JSON format
│   ├── metrics.csv             # Metrics in CSV format
│   └── pdf2md_diagnosis_results.txt # PDF2MD diagnosis results
├── scripts/                    # Helper scripts
│   ├── combine_json_files.py   # Script to combine JSON files
│   ├── format_gpt_json.py      # GPT JSON formatting
│   ├── generate_project_overview.sh # Generate project overview
│   ├── run_pdf2md_diagnostic.sh # OCR diagnostics
│   ├── run_test.py             # Test runner
│   ├── run_with_ocr.sh         # OCR convenience script
│   ├── setup.py                # Setup script
│   └── validate_gpt_json.py    # Validate GPT JSON files
├── src/                        # Source code modules
│   ├── __init__.py
│   ├── gpt/                    # GPT integration
│   │   ├── configure_capabilities.py
│   │   ├── documentation/
│   │   │   └── gpt_usage_guidelines.md
│   │   ├── gpt_config.py
│   │   ├── refine_instructions.py
│   │   ├── run_gpt_config.py
│   │   ├── test_gpt_queries.py
│   │   └── upload_to_gpt.py
│   ├── jfk_scraper.py          # Main script
│   ├── optimization.py         # Optimization utilities
│   ├── performance_monitoring.py # Performance tracking
│   └── utils/                  # Core utilities
│       ├── __init__.py
│       ├── batch_utils.py      # Batch processing
│       ├── checkpoint_utils.py # Checkpointing
│       ├── conversion_utils.py # Format conversion
│       ├── download_utils.py   # File downloading
│       ├── logging_utils.py    # Logging
│       ├── minimal_marker.py   # PDF to MD compatibility
│       ├── monitor_progress.py # Progress monitoring
│       ├── pdf2md/             # PDF to Markdown conversion
│       │   ├── __init__.py
│       │   ├── pdf2md.py       # Core PDF to MD functionality
│       │   └── pdf2md_diagnostic.py # PDF2MD diagnostics
│       ├── pdf2md_wrapper.py   # Enhanced PDF conversion
│       ├── pdf_utils.py        # PDF processing utilities
│       ├── scrape_utils.py     # Web scraping
│       └── storage.py          # Data storage
├── test_data/                  # Test data files
│   └── test_document.pdf       # Sample PDF for testing
├── test_output/                # Test output files
│   ├── test_document_minimal.md # Minimal test output
│   ├── test_document_with_ocr_high.md # High-quality OCR test
│   ├── test_document_with_ocr_low.md # Low-quality OCR test
│   ├── test_document_with_ocr_medium.md # Medium-quality OCR test
│   └── test_document_without_ocr.md # Non-OCR test output
└── tests/                      # Test suite
    ├── test_api.py
    ├── test_bridge.py
    ├── test_dependencies.py
    ├── test_download_pdf.py
    ├── test_end_to_end.py
    ├── test_integration.py
    ├── test_markdown_to_json.py
    ├── test_marker_scanned_pdf.py
    ├── test_ocr_flow.py
    ├── test_ocr_minimal.py
    ├── test_pdf2md.py
    ├── test_pdf_to_markdown.py
    ├── test_scrape.py
    ├── test_storage.py
    ├── test_validate_pdf_to_markdown.py
    ├── test_validation.py
    ├── test_verify_json_lite_llm.py
    ├── test_verify_markdown_structure.py
    └── ztest_markdown_to_json_validation.py
```

## 🤝 Contributing

Contributions to the JFK Files Scraper project are welcome! Here's how you can contribute:

1. **Fork the Repository**: Create your own fork of the project
2. **Create a Feature Branch**: `git checkout -b feature/your-feature-name`
3. **Make Your Changes**: Implement your feature or bug fix
4. **Write Tests**: Add tests for your changes
5. **Run the Test Suite**: Ensure all tests pass
6. **Commit Your Changes**: `git commit -m "Add your feature"`
7. **Push to Your Branch**: `git push origin feature/your-feature-name`
8. **Create a Pull Request**: Submit a PR to the main repository

Please follow these guidelines:
- Follow the existing code style and conventions
- Write clear, concise commit messages
- Document your changes
- Add or update tests as necessary
- Ensure your code passes all tests

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Disclaimer**: This project is for educational and research purposes only. All JFK files are publicly available from the National Archives website. Please use this tool responsibly and in accordance with the National Archives' terms of service.
