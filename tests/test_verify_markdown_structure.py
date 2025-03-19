#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST-9: Verify Markdown output structure and content integrity post-Marker conversion.

This script focuses specifically on the structure and content integrity of Markdown files
after conversion from PDFs using the Marker library, examining:
1. Document structure (headings, sections, paragraphs)
2. Content integrity (maintained text, proper formatting)
3. Special elements (tables, lists, footnotes, etc.)
4. Comparison with expected patterns for government documents

Unlike test_validate_pdf_to_markdown.py which focuses on validation quality,
this test specifically analyzes the structural integrity of the produced Markdown.
"""

import sys
import os
import logging
import re
import json
from pathlib import Path
from collections import defaultdict

# Add parent directory to python path to import from jfk_scraper.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import required functions
    from jfk_scraper import create_directories, logger
    
    # Make sure directories exist
    create_directories()
    
    # Configure test-specific logging
    logger.info("Starting Markdown structure and content integrity verification (TEST-9)")
    
    # Use existing Markdown files from the markdown directory
    markdown_dir = "markdown"
    if not os.path.exists(markdown_dir):
        logger.error(f"Markdown directory not found at {markdown_dir}.")
        sys.exit(1)
    
    # Get all markdown files
    markdown_files = [os.path.join(markdown_dir, f) for f in os.listdir(markdown_dir) if f.endswith('.md')]
    
    if not markdown_files:
        logger.error("No Markdown files found to analyze.")
        sys.exit(1)
    
    logger.info(f"Found {len(markdown_files)} Markdown files to analyze")
    
    # Define structural patterns to look for in government documents
    gov_doc_patterns = {
        "classification": re.compile(r'(?i)(unclassified|classified|confidential|secret|top secret)'),
        "agency_headers": re.compile(r'(?i)(central intelligence agency|federal bureau of investigation|department of|commission on)'),
        "date_formats": re.compile(r'\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2} [A-Za-z]+ \d{4}'),
        "document_numbers": re.compile(r'(?i)(document|doc|file|record)\s*(no|number|#)?\s*[:.]?\s*[\w\-]+'),
        "redactions": re.compile(r'(?i)\[redacted\]|\[classified\]|\[deleted\]')
    }
    
    # Structural elements to identify
    structure_elements = {
        "headers": re.compile(r'^#{1,6} '),
        "paragraphs": re.compile(r'^[^#>*\-\d\s][^\n]+$'),
        "bullet_lists": re.compile(r'^\s*[\*\-] '),
        "numbered_lists": re.compile(r'^\s*\d+\. '),
        "block_quotes": re.compile(r'^\s*> '),
        "tables": re.compile(r'^\s*\|.*\|$'),
        "code_blocks": re.compile(r'^```'),
        "horizontal_rules": re.compile(r'^---+$|^\*\*\*+$')
    }
    
    # Results storage
    results = {}
    
    # Special characters that might indicate conversion issues
    problematic_chars = ['�', '□', '■', '▯', '▮', '\ufffd']
    
    # Analysis of all markdown files
    for markdown_file in markdown_files:
        file_basename = os.path.basename(markdown_file)
        logger.info(f"Analyzing structure of: {file_basename}")
        
        try:
            with open(markdown_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Basic metrics
            file_size = os.path.getsize(markdown_file)
            line_count = len(lines)
            char_count = len(content)
            
            # Document structure analysis
            structure_counts = defaultdict(int)
            for element_name, pattern in structure_elements.items():
                matches = [line for line in lines if pattern.match(line)]
                structure_counts[element_name] = len(matches)
            
            # Government document pattern analysis
            gov_pattern_counts = defaultdict(int)
            gov_pattern_examples = defaultdict(list)
            
            for pattern_name, pattern in gov_doc_patterns.items():
                matches = pattern.findall(content)
                gov_pattern_counts[pattern_name] = len(matches)
                # Store up to 5 examples of each pattern
                gov_pattern_examples[pattern_name] = matches[:5]
            
            # Check for problematic characters indicating conversion issues
            problematic_char_count = 0
            for char in problematic_chars:
                problematic_char_count += content.count(char)
            
            # Section analysis - identify logical document sections
            sections = []
            current_section = {"title": "Untitled", "lines": [], "level": 0}
            
            for line in lines:
                # If this is a header, start a new section
                if line.startswith('#'):
                    # If there's content in the current section, save it
                    if current_section["lines"]:
                        sections.append(current_section)
                    
                    # Start a new section
                    level = len(line) - len(line.lstrip('#'))
                    title = line.lstrip('#').strip()
                    current_section = {"title": title, "lines": [], "level": level}
                else:
                    current_section["lines"].append(line)
            
            # Add the last section
            if current_section["lines"]:
                sections.append(current_section)
            
            # Calculate section sizes
            section_sizes = [len(section["lines"]) for section in sections]
            average_section_size = sum(section_sizes) / max(len(section_sizes), 1)
            
            # Analyze header hierarchy correctness
            header_levels = [section["level"] for section in sections]
            header_hierarchy_correct = True
            
            # Check if levels increment correctly (never skip a level)
            for i in range(1, len(header_levels)):
                if header_levels[i] > header_levels[i-1] + 1:
                    header_hierarchy_correct = False
                    break
            
            # Find potential content issues
            potential_issues = []
            
            # Check for very short sections (might indicate structure issues)
            short_sections = [section for section in sections if len(section["lines"]) < 3]
            if short_sections:
                potential_issues.append(f"Found {len(short_sections)} very short sections")
            
            # Check for very short paragraphs (potential conversion issues)
            paragraphs = content.split('\n\n')
            short_paragraphs = [p for p in paragraphs if 0 < len(p) < 10]  # Non-empty but very short
            if len(short_paragraphs) > len(paragraphs) * 0.2:  # More than 20% are very short
                potential_issues.append("High frequency of very short paragraphs")
            
            # Check for potential table issues
            table_rows = [line for line in lines if line.strip().startswith('|') and line.strip().endswith('|')]
            if table_rows:
                col_counts = [line.count('|') for line in table_rows]
                if len(set(col_counts)) > 1:
                    potential_issues.append("Inconsistent table column counts")
            
            # Check for problematic characters
            if problematic_char_count > 0:
                potential_issues.append(f"Found {problematic_char_count} problematic characters")
            
            # Generate structural integrity score (0-100)
            # Scoring factors:
            # - Having headers: 25 points
            # - Having paragraphs: 25 points
            # - Correct header hierarchy: 20 points
            # - Having either lists or tables: 15 points
            # - Low problematic character count: 15 points
            
            structural_score = 0
            
            if structure_counts["headers"] > 0:
                structural_score += 25
            
            if structure_counts["paragraphs"] > 10:  # At least some substantial content
                structural_score += 25
            
            if header_hierarchy_correct:
                structural_score += 20
            
            if structure_counts["bullet_lists"] > 0 or structure_counts["numbered_lists"] > 0 or structure_counts["tables"] > 0:
                structural_score += 15
            
            # Deduct points for problematic characters based on their frequency
            char_score = 15 - min(15, (problematic_char_count / 10))
            structural_score += max(0, char_score)
            
            # Content integrity analysis
            # Look for patterns that suggest the document is a government document
            gov_doc_confidence = 0
            total_gov_patterns = sum(gov_pattern_counts.values())
            
            # More pattern matches = higher confidence
            if total_gov_patterns > 0:
                gov_doc_confidence = min(100, total_gov_patterns * 5)
            
            # Store results for this file
            results[file_basename] = {
                "file_metrics": {
                    "size_bytes": file_size,
                    "line_count": line_count,
                    "char_count": char_count
                },
                "structure_analysis": {
                    "section_count": len(sections),
                    "average_section_size": average_section_size,
                    "header_hierarchy_correct": header_hierarchy_correct,
                    "structure_elements": dict(structure_counts)
                },
                "content_analysis": {
                    "government_document_patterns": dict(gov_pattern_counts),
                    "government_document_examples": {k: v for k, v in gov_pattern_examples.items() if v},
                    "government_document_confidence": gov_doc_confidence,
                    "problematic_char_count": problematic_char_count
                },
                "potential_issues": potential_issues,
                "structural_integrity_score": structural_score
            }
            
            # Log summary for this file
            logger.info(f"Structure analysis for {file_basename}:")
            logger.info(f"  - Sections: {len(sections)}")
            logger.info(f"  - Headers: {structure_counts['headers']}")
            logger.info(f"  - Paragraphs: {structure_counts['paragraphs']}")
            logger.info(f"  - Lists: {structure_counts['bullet_lists'] + structure_counts['numbered_lists']}")
            logger.info(f"  - Tables: {structure_counts['tables']}")
            logger.info(f"  - Structural integrity score: {structural_score}/100")
            
            if potential_issues:
                logger.info(f"  - Potential issues: {', '.join(potential_issues)}")
            
        except Exception as e:
            logger.error(f"Error analyzing {file_basename}: {e}")
            continue
    
    # Save analysis results
    output_file = "performance_metrics/markdown_structure_analysis.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Saved Markdown structure analysis to: {output_file}")
    
    # Calculate overall statistics
    if results:
        avg_structural_score = sum(data["structural_integrity_score"] for data in results.values()) / len(results)
        avg_gov_confidence = sum(data["content_analysis"]["government_document_confidence"] for data in results.values()) / len(results)
        
        total_issues = sum(len(data["potential_issues"]) for data in results.values())
        
        logger.info("=== Overall Markdown Structure Analysis Results ===")
        logger.info(f"Analyzed {len(results)} Markdown files")
        logger.info(f"Average structural integrity score: {avg_structural_score:.1f}/100")
        logger.info(f"Average government document confidence: {avg_gov_confidence:.1f}%")
        logger.info(f"Total potential issues identified: {total_issues}")
        
        if avg_structural_score >= 70:
            logger.info("Markdown structure verification test PASSED")
        else:
            logger.warning("Markdown structure verification test COMPLETED WITH WARNINGS")
            
    else:
        logger.error("No Markdown files were successfully analyzed")
        sys.exit(1)
    
except ImportError as e:
    print(f"Error importing from jfk_scraper.py: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error during Markdown structure verification: {e}")
    import traceback
    print(traceback.format_exc())
    sys.exit(1)
