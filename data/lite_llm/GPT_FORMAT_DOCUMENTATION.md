# GPT Knowledge Upload Format Documentation

## Overview

This document describes the GPT-optimized JSON structure created for the JFK Files Archive project. This format is specifically designed for efficient GPT knowledge upload, ensuring that the documents are properly structured for optimal retrieval and use by GPT models.

## File Structure

The GPT-formatted JSON file (`jfk_files_gpt.json`) follows an array-based structure with the following key elements:

1. **Metadata Object** (first array element)
2. **Document Objects** (remaining array elements)

### Metadata Object

The metadata object provides high-level information about the entire knowledge base:

```json
{
  "type": "metadata",
  "knowledge_base_name": "JFK Files Archive",
  "description": "Declassified documents from the JFK Assassination Records Collection",
  "document_count": 11,
  "created_at": "2025-03-18 23:10:49",
  "version": "1.0"
}
```

| Field | Description |
|-------|-------------|
| `type` | Always "metadata" to identify this as the metadata object |
| `knowledge_base_name` | Name of the knowledge base for GPT reference |
| `description` | Brief description of the knowledge base contents |
| `document_count` | Number of unique documents in the knowledge base |
| `created_at` | Timestamp when the knowledge base was created |
| `version` | Version of the format structure |

### Document Objects

Each document object represents a single JFK file with its contents and metadata:

```json
{
  "type": "document",
  "id": "104-10004-10156",
  "title": "104-10004-10156",
  "content": "## Page 1\n\nThis is a placeholder Markdown file...",
  "metadata": {
    "source": "104-10004-10156.json",
    "timestamp": "2025-03-18 22:46:07",
    "total_pages": 3,
    "conversion_method": "python"
  }
}
```

| Field | Description |
|-------|-------------|
| `type` | Always "document" to identify this as a document object |
| `id` | Unique document identifier (matches the original document ID) |
| `title` | Document title (defaults to document ID if no title available) |
| `content` | The full document content with page markers in Markdown format |
| `metadata` | Object containing additional document metadata |

#### Metadata Sub-fields

| Field | Description |
|-------|-------------|
| `source` | Original source file name |
| `timestamp` | When the document was processed |
| `total_pages` | Number of pages in the original document |
| `conversion_method` | Method used to convert the document (e.g., "python") |

## Content Format

The `content` field uses Markdown formatting with the following conventions:

1. **Page Markers**: Each page is prefixed with a level-2 header (`## Page X`)
2. **Content Cleaning**: Document ID headers are removed to avoid redundancy
3. **Whitespace Optimization**: Extra newlines are trimmed while preserving paragraph structure
4. **Concatenation**: All pages are concatenated with appropriate spacing for readability

## GPT Knowledge Upload Guidelines

For optimal GPT knowledge upload, follow these guidelines:

1. **File Size**: Ensure the formatted JSON file is within GPT's knowledge upload limits (typically 10-20MB depending on the GPT tier)
2. **Chunking**: For very large collections, consider splitting into multiple knowledge bases
3. **Content Focus**: Prefer more informative content over repetitive or uninformative text
4. **Metadata Importance**: Include clear metadata to help GPT understand the context of the documents
5. **Formatting**: Markdown formatting helps GPT understand document structure

## Validation Requirements

Before uploading to GPT, validate that the formatted JSON meets these requirements:

1. **Valid JSON**: The file must be valid JSON without syntax errors
2. **Required Fields**: All document objects must have `type`, `id`, and `content` fields
3. **Unique IDs**: All document IDs must be unique within the knowledge base
4. **Content Quality**: Documents should have meaningful content (not empty)
5. **Metadata Consistency**: All documents should have consistent metadata structures

## Usage Example

To validate and upload the formatted JSON to GPT:

1. Use the validation script: `python scripts/validate_json_structure.py --input-file lite_llm/jfk_files_gpt.json`
2. If validation passes, upload the file to GPT using the GPT interface
3. Configure GPT to use the knowledge base for answering queries about JFK files

## Future Enhancements

Potential improvements for future versions:

1. **Enhanced Metadata**: Add more detailed metadata like document categories, classification status, etc.
2. **Structured Content**: Further refine the content structure for better information retrieval
3. **Cross-References**: Add explicit links between related documents
4. **Named Entities**: Extract and highlight named entities (people, organizations, etc.)
