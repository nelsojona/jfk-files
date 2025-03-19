# JFK Files Scraper - Running Guide

This guide explains how to run the JFK Files Scraper with full monitoring capabilities to process all 1,123 JFK files from the National Archives website.

## Prerequisites

Make sure you've installed all dependencies according to `INSTALLATION.md`:

```bash
pip install -r requirements.txt
```

## Running with Full OCR Support

For OCR to work properly, you need Python 3.10 with PyMuPDF, pytesseract, and pdf2image installed. Use the provided script:

```bash
# Run with full OCR support
./run_with_ocr.sh --scrape-all --ocr --resume
```

This script:
1. Activates the Python 3.10 environment with all OCR dependencies
2. Verifies that PyMuPDF and Marker PDF are available
3. Runs the scraper with proper OCR support

## Running the Full Scraper (Standard Mode)

### Basic Run (Single Terminal)

For a simple run that processes all files:

```bash
python jfk_scraper.py --scrape-all --ocr --resume
```

Parameters explained:
- `--scrape-all`: Process all 113 pages containing 1,123 JFK files
- `--ocr`: Enable OCR for better text extraction (especially for scanned documents)
- `--resume`: Automatically resume from the last checkpoint if interrupted

### Advanced Run with Monitoring (Two Terminals)

For better visibility into the scraping process, run the scraper in one terminal and the monitoring tool in another:

#### Terminal 1: Run the scraper
```bash
python jfk_scraper.py --scrape-all --ocr --resume --log-level INFO
```

#### Terminal 2: Run the monitor
```bash
python monitor_progress.py --mode monitor
```

This setup provides:
1. Real-time processing in the first terminal
2. Continuous performance monitoring in the second terminal
3. Automatically generated performance charts

## Checking Status

To quickly check the current status without starting continuous monitoring:

```bash
python monitor_progress.py --mode status
```

This will display:
- Current progress percentage
- Files processed
- Processing rates
- Estimated completion time
- Resource usage

## Generating Reports

To generate a comprehensive report with charts:

```bash
python monitor_progress.py --mode report
```

This creates:
- Detailed JSON metrics in `performance_metrics/metrics.json`
- Performance visualizations in `performance_metrics/charts/`
- Summary of processing efficiency

## Handling Interruptions

If you need to stop the scraper (Ctrl+C), it will save its progress automatically. To resume:

```bash
python jfk_scraper.py --scrape-all --ocr --resume
```

## Running Specific Pages

If you want to process only specific pages:

```bash
python jfk_scraper.py --url "https://www.archives.gov/research/jfk/release-2025" --start-page 10 --end-page 20 --ocr
```

## Testing with a Small Sample

To test the system with just a few files:

```bash
python jfk_scraper.py --test
```

## Command-Line Arguments

The scraper supports these arguments:

| Argument | Description | Default |
|----------|-------------|---------|
| `--url` | Base URL for JFK files | https://www.archives.gov/research/jfk/release-2025 |
| `--start-page` | Page to start scraping from | 1 |
| `--end-page` | Page to end scraping at | None (all pages) |
| `--test` | Run in test mode with limited pages | False |
| `--full` | Run full-scale processing | False |
| `--ocr` | Force OCR for all PDF conversions | False |
| `--resume` | Resume from the last checkpoint | True |
| `--scrape-all` | Scrape all 113 pages and process all 1,123 files | False |
| `--log-level` | Set the logging level | INFO |
| `--no-resume` | Do not resume from checkpoint | False |

## Output Files

The scraper generates these outputs:

- **PDFs**: Downloaded PDF files in the `pdfs/` directory
- **Markdown**: Converted Markdown files in the `markdown/` directory
- **JSON**: Structured JSON data in the `json/` directory
- **Checkpoints**: Progress checkpoints in the `.checkpoints/` directory
- **Logs**: Detailed logs in `jfk_scraper.log` and `jfk_scraper_errors.log`
- **Performance**: Metrics and charts in the `performance_metrics/` directory
