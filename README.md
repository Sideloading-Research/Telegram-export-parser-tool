# Telegram Export Parser Documentation

## Overview

The `telegram-export-parser.py` script is a Python utility for processing HTML exports from Telegram conversations. It extracts structured data about messages, senders, dates, media attachments, and other elements from these HTML files. The parser can handle both single files and entire directories of exports, converting them to JSON or plain text formats.

## Requirements

- Python 3.6+
- BeautifulSoup4
- Standard Python libraries: sys, os, json, re, datetime, glob, argparse, traceback

## Installation

1. Ensure Python 3.6+ is installed on your system
2. Install the BeautifulSoup4 library: `pip install beautifulsoup4`
3. Download the `telegram-export-parser.py` script

## Basic Usage

```bash
python telegram-export-parser.py [input_file_or_directory] [options]
```

### Command Line Arguments

- `input`: Path to an HTML file or directory containing HTML files
- `--output`, `-o`: Output file path (optional, default: auto-generated)
- `--format`, `-f`: Output format, either 'txt' or 'json' (optional, default: txt)

### Examples

Process a single export file:
```bash
python telegram-export-parser.py messages.html
```

Process a directory of export files:
```bash
python telegram-export-parser.py ./telegram_exports/
```

Save output as JSON:
```bash
python telegram-export-parser.py messages.html --format json
```

Specify output file:
```bash
python telegram-export-parser.py messages.html --output my_chat.txt
```

## Features

- Extracts message text, timestamps, senders, and media references
- Preserves text formatting including line breaks and blockquotes
- Processes forwarded messages with original sender information
- Captures reply relationships between messages
- Handles multi-file exports by combining them in correct order
- Provides diagnostic information about parsing quality
- Supports both JSON and human-readable text output formats

## Output Formats

### Text Format

The text output format is human-readable, with each message presented as:
```
msg [ID]: [DATETIME] [SENDER] wrote:
[Optional forwarded info]
[Optional reply reference]
[MESSAGE_TEXT]
[Optional media reference]
```

### JSON Format

The JSON output has the following structure:
```json
{
  "chat_name": "Chat Name",
  "messages": [
    {
      "id": "12345",
      "from": "Sender Name",
      "datetime": "14 April 2025 12:34",
      "timestamp": "14.04.2025 12:34:56",
      "text": "Message text",
      "media": {
        "type": "photo|video",
        "src": "file_path",
        "href": "file_path"
      },
      "forwarded_from": "Original sender",
      "forwarded_date": "Date forwarded",
      "reply_to_id": "54321",
      "reply_to_text": "Preview of replied message"
    }
  ],
  "diagnostics": {
    "text_div_count": 150,
    "processed_messages": 145,
    "html_text_chars": 12500,
    "extracted_text_chars": 12000,
    "files_processed": 3
  }
}
```

## Technical Details

### Processing Workflow

1. Parse command line arguments
2. Determine if input is a single file or directory
3. For directories:
   - Find and sort all Telegram HTML files
   - Process each file individually
   - Merge results into a combined dataset
4. Extract structured data:
   - Messages, timestamps, and sender information
   - Message text with preserved formatting
   - Media references (photos, videos)
   - Forwarded message metadata
   - Reply relationships
5. Save results in requested format
6. Display processing statistics and diagnostics

### Key Components

#### HTML Element Detection

The parser identifies various HTML elements in Telegram exports:
- `div.message`: Individual message containers
- `div.service`: Date markers between messages
- `div.from_name`: Message sender information
- `div.text`: Message content
- `div.forwarded.body`: Forwarded message containers
- `div.media_wrap`: Media attachment wrappers
- `div.reply_to`: Reply information

#### Text Extraction

Text extraction preserves formatting elements:
- Line breaks are maintained
- Blockquotes are formatted with ">" prefix
- Text hierarchy is preserved where possible

#### Diagnostics

The parser provides several diagnostic metrics:
- Text div count vs. processed messages
- Character counts in original HTML vs. extracted text
- Processing warnings for potential extraction issues
- File processing statistics for multi-file operations

## Limitations

- Media files are not extracted, only references to them
- Some complex formatting (colors, custom styles) may be lost
- Relies on Telegram's HTML export structure, which may change over time
- Does not process emoji reactions or message edits

## Troubleshooting

### Common Issues

1. **Missing BeautifulSoup4**: Install with `pip install beautifulsoup4`
2. **UnicodeDecodeError**: Ensure files are valid UTF-8 encoded
3. **No files found in directory**: Verify the directory contains files named "messages.html" or "messages{number}.html"
4. **Low character extraction ratio**: May indicate complex or non-standard HTML in the export

### Diagnostic Warnings

- **Text elements not processed**: Indicates potential missed messages
- **Low extraction ratio**: Suggests formatting or content may be lost

## Version History

- 1.0.0: Initial release with support for text and JSON output
