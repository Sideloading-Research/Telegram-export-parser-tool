"""
Telegram HTML Export Parser

This module parses Telegram chat export HTML files into structured data.
It extracts messages, user information, media references, and metadata
from exported Telegram conversation files. Results can be saved as
JSON or plaintext formats.

The parser handles both single files and directories containing multiple
HTML exports from the same conversation.

Version: 1.0.0
Author: [Your Name]
Created: April 14, 2025
Last Modified: April 14, 2025
License: MIT

To cite this code, use:
[Your Name]. (2025). Telegram HTML Export Parser [Computer software].
Retrieved from https://github.com/yourusername/telegram-parser
"""

from bs4 import BeautifulSoup
import sys
import traceback
import os
import json
import re
from datetime import datetime
import glob
import argparse


def count_text_divs(html_content):
    """
    Count the number of text divs in the HTML using simple text search.
    
    This provides a baseline metric to compare against actual extracted
    message count for diagnostic purposes.
    
    Args:
        html_content (str): Raw HTML content from Telegram export file
        
    Returns:
        int: Count of '<div class="text">' instances in the HTML
    """
    return html_content.count('<div class="text">')


def count_message_text_chars(soup):
    """
    Count characters in message text content, excluding UI elements.
    
    This function focuses only on actual message content to provide
    accurate metrics for extraction quality assessment.
    
    Args:
        soup (BeautifulSoup): Parsed HTML document
        
    Returns:
        int: Total character count from all message text divs
    """
    total_chars = 0
    
    # Find the parent div containing all conversation messages
    history_div = soup.select_one('div.history')
    if not history_div:
        # Return zero if history container not found
        return 0
    
    # Process only actual message divs, not service notifications
    for message_div in history_div.select('div.message.default'):
        # Extract just the message content text
        text_div = message_div.select_one('div.text')
        if text_div:
            # Get plain text and count characters
            text_content = text_div.get_text(strip=True)
            total_chars += len(text_content)
    
    return total_chars


def extract_text_with_formatting(element):
    """
    Extract text recursively while preserving key formatting elements.
    
    This preserves line breaks, blockquotes, and text hierarchy to
    maintain readability of the extracted messages.
    
    Args:
        element (bs4.element): HTML element to extract text from
        
    Returns:
        str: Text content with preserved formatting
    """
    # Handle text nodes directly
    if element.name is None:
        return element.string or ""
    
    # Convert <br> tags to newlines
    if element.name == "br":
        return "\n"
    
    # Format blockquotes with proper indentation
    if element.name == "blockquote":
        # Get all text within the blockquote
        inner_text = "".join(extract_text_with_formatting(child) for child in element.children)
        # Apply standard '>' prefix to each line
        indented_text = "\n".join("> " + line for line in inner_text.split("\n"))
        # Add spacing before and after blockquote
        return "\n\n" + indented_text + "\n\n"
    
    # For all other elements, process child nodes
    return "".join(extract_text_with_formatting(child) for child in element.children)


def sort_telegram_files(file_list):
    """
    Sort Telegram message files in chronological order.
    
    Telegram exports use numbered files for pagination. This function
    ensures messages are processed in correct sequence.
    
    Args:
        file_list (list): Paths to HTML files to sort
        
    Returns:
        list: Sorted file paths with messages.html first
    """
    def get_file_number(filename):
        # Extract number from filename or assign priority
        basename = os.path.basename(filename)
        
        # Base file always comes first
        if basename == 'messages.html':
            return 0
        
        # Extract number from messagesX.html pattern
        match = re.search(r'messages(\d+)\.html', basename)
        if match:
            return int(match.group(1))
            
        # Any other files come last
        return float('inf')
    
    # Sort files based on numeric order
    return sorted(file_list, key=get_file_number)


def find_telegram_files(directory):
    """
    Find all Telegram message HTML files in the specified directory.
    
    Searches for message*.html pattern and returns them in proper
    chronological order for processing.
    
    Args:
        directory (str): Path to directory containing exported files
        
    Returns:
        list: Sorted list of message file paths
    """
    # Match pattern for Telegram export files
    pattern = os.path.join(directory, 'messages*.html')
    # Find all matching files
    files = glob.glob(pattern)
    # Return files in correct order
    return sort_telegram_files(files)


def merge_parsed_data(data_list):
    """
    Merge multiple parsed data objects into one combined dataset.
    
    Creates a unified representation by joining messages and
    accumulating metrics from multiple export files.
    
    Args:
        data_list (list): List of parsed data dictionaries
        
    Returns:
        dict: Combined data with unified messages and metrics
    """
    # Return default structure for empty input
    if not data_list:
        return {'chat_name': 'Unknown', 'messages': [], 'diagnostics': {}}
    
    # Use chat name from first file
    chat_name = data_list[0]['chat_name']
    
    # Combine all messages from all files
    all_messages = []
    for data in data_list:
        all_messages.extend(data['messages'])
    
    # Aggregate diagnostic metrics
    combined_diagnostics = {
        'text_div_count': sum(data.get('diagnostics', {}).get('text_div_count', 0) for data in data_list),
        'processed_messages': sum(data.get('diagnostics', {}).get('processed_messages', 0) for data in data_list),
        'html_text_chars': sum(data.get('diagnostics', {}).get('html_text_chars', 0) for data in data_list),
        'extracted_text_chars': sum(data.get('diagnostics', {}).get('extracted_text_chars', 0) for data in data_list),
        'files_processed': len(data_list)
    }
    
    # Return unified data structure
    return {
        'chat_name': chat_name,
        'messages': all_messages,
        'diagnostics': combined_diagnostics
    }


def is_valid_date(date_text):
    """
    Validate if text matches Telegram export date formats.
    
    Used to identify true date markers vs. other message content
    that might be misinterpreted as dates.
    
    Args:
        date_text (str): Text to validate as date
        
    Returns:
        bool: True if text matches common Telegram date formats
    """
    # Define recognized date patterns in exports
    date_patterns = [
        r'^\d{1,2}\s+[A-Za-z]+\s+\d{4}$',  # "12 April 2025"
        r'^\d{1,2}\.\d{1,2}\.\d{4}$',       # "12.04.2025"
    ]
    
    # Try matching against each pattern
    for pattern in date_patterns:
        if re.match(pattern, date_text.strip()):
            return True
    
    # Return false if no patterns match
    return False


def parse_telegram_html(html_file):
    """
    Parse Telegram HTML export file and extract structured message data.
    
    This is the main parsing function that processes the HTML structure
    of Telegram exports to extract messages, media, metadata, and
    conversation structure into a structured format.
    
    Args:
        html_file (str): Path to HTML file to parse
        
    Returns:
        dict: Structured data containing messages and chat metadata
    """
    try:
        # Load HTML file with UTF-8 encoding
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Get baseline text div count for diagnostics
        text_div_count = count_text_divs(html_content)
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Calculate message text character count
        text_chars_count = count_message_text_chars(soup)
        
        # Extract chat name from header
        chat_name = soup.select_one('div.text.bold')
        chat_name = chat_name.get_text(strip=True) if chat_name else 'Unknown Chat'
        
        # Find the message history container
        history_div = soup.select_one('div.history')
        if not history_div:
            return {"error": "Could not find message history"}
        
        # Initialize message collection
        messages = []
        current_date = None
        previous_sender = None
        total_extracted_chars = 0
        
        # Process each message div in the history
        for message_div in history_div.select('div.message'):
            message_data = {}
            
            # Check if this is a date marker (service message)
            if 'service' in message_div.get('class', []):
                date_text = message_div.select_one('div.body.details')
                if date_text:
                    date_text_value = date_text.get_text(strip=True)
                    # Validate format before accepting as date
                    if is_valid_date(date_text_value):
                        current_date = date_text_value
                continue
            
            # Extract message ID from div id attribute
            message_id = message_div.get('id', '').replace('message', '')
            message_data['id'] = message_id
            
            # Check if this is a continuation from the same user
            is_joined = 'joined' in message_div.get('class', [])
            
            # Extract sender information
            from_name = message_div.select_one('div.from_name')
            if from_name:
                # New sender identified
                sender_name = from_name.get_text(strip=True)
                previous_sender = sender_name
            elif is_joined and previous_sender:
                # Use previous sender for joined messages
                sender_name = previous_sender
            else:
                # Fallback for unknown sender
                sender_name = 'Unknown'
                
            message_data['from'] = sender_name
            
            # Extract message timestamp
            date_details = message_div.select_one('div.pull_right.date.details')
            if date_details:
                time = date_details.get_text(strip=True)
                
                # Try to get precise timestamp from title attribute
                title_datetime = date_details.get('title')
                if title_datetime:
                    # Extract date part from the full timestamp
                    date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', title_datetime)
                    if date_match:
                        # Extract the date component
                        extracted_date = date_match.group(1)
                        # Convert date format for readability
                        try:
                            day, month, year = extracted_date.split('.')
                            month_name = ["", "January", "February", "March", "April", "May", "June", 
                                         "July", "August", "September", "October", "November", "December"][int(month)]
                            formatted_date = f"{int(day)} {month_name} {year}"
                            full_datetime = f"{formatted_date} {time}"
                        except:
                            # Use raw date if conversion fails
                            full_datetime = f"{extracted_date} {time}"
                    else:
                        # Use current_date from context if available
                        full_datetime = f"{current_date} {time}" if current_date else time
                    
                    message_data['datetime'] = full_datetime
                    message_data['timestamp'] = title_datetime
                else:
                    # Use contextual date if title attribute isn't available
                    full_datetime = f"{current_date} {time}" if current_date else time
                    message_data['datetime'] = full_datetime
            
            # Process forwarded messages
            forwarded_body = message_div.select_one('div.forwarded.body')
            if forwarded_body:
                # Extract original sender information
                forwarded_from = forwarded_body.select_one('div.from_name')
                if forwarded_from:
                    forwarded_text = forwarded_from.get_text(strip=True)
                    
                    # Try to extract forwarded date if present
                    date_span = forwarded_from.select_one('span.date.details')
                    if date_span:
                        # Remove date from sender string
                        forwarded_text = forwarded_text.replace(date_span.get_text(strip=True), '').strip()
                        message_data['forwarded_date'] = date_span.get_text(strip=True)
                    
                    message_data['forwarded_from'] = forwarded_text
                
                # Extract the forwarded message content
                forwarded_text_div = forwarded_body.select_one('div.text')
                if forwarded_text_div:
                    message_text = extract_text_with_formatting(forwarded_text_div).strip()
                    message_data['text'] = message_text
                    # Count characters for diagnostics
                    total_extracted_chars += len(message_text.replace('\n\n', ' ').replace('\n', ' ').strip())
                
                # Check for media in forwarded message
                forwarded_media = forwarded_body.select_one('div.media_wrap')
                if forwarded_media:
                    # Process photos in forwarded content
                    photo = forwarded_media.select_one('a.photo_wrap')
                    if photo:
                        img = photo.select_one('img.photo')
                        if img:
                            message_data['media'] = {
                                'type': 'photo',
                                'src': img.get('src'),
                                'href': photo.get('href')
                            }
                    
                    # Process videos in forwarded content
                    video = forwarded_media.select_one('a.video_file_wrap')
                    if video:
                        video_duration = video.select_one('div.video_duration')
                        message_data['media'] = {
                            'type': 'video',
                            'href': video.get('href'),
                            'duration': video_duration.get_text(strip=True) if video_duration else None
                        }
            else:
                # Extract text from regular (non-forwarded) messages
                text_div = message_div.select_one('div.text')
                if text_div:
                    # Extract text with formatting preserved
                    message_text = extract_text_with_formatting(text_div).strip()
                    message_data['text'] = message_text
                    # Count normalized text for diagnostics
                    total_extracted_chars += len(message_text.replace('\n\n', ' ').replace('\n', ' ').strip())
                
                # Extract media attachments
                media_wrap = message_div.select_one('div.media_wrap')
                if media_wrap:
                    # Process photo attachments
                    photo = media_wrap.select_one('a.photo_wrap')
                    if photo:
                        img = photo.select_one('img.photo')
                        if img:
                            message_data['media'] = {
                                'type': 'photo',
                                'src': img.get('src'),
                                'href': photo.get('href')
                            }
                    
                    # Process video attachments
                    video = media_wrap.select_one('a.video_file_wrap')
                    if video:
                        video_duration = video.select_one('div.video_duration')
                        message_data['media'] = {
                            'type': 'video',
                            'href': video.get('href'),
                            'duration': video_duration.get_text(strip=True) if video_duration else None
                        }
            
            # Extract reply information if message is a reply
            reply_to = message_div.select_one('div.reply_to.details')
            if reply_to:
                # Try to get the ID of the message being replied to
                reply_link = reply_to.select_one('a')
                if reply_link:
                    href = reply_link.get('href', '')
                    reply_id_match = re.search(r'message(\d+)', href)
                    if reply_id_match:
                        message_data['reply_to_id'] = reply_id_match.group(1)
                        
                # Include the reply-to text preview
                message_data['reply_to_text'] = reply_to.get_text(strip=True)
            
            # Add complete message to collection
            messages.append(message_data)
        
        # Return structured data with diagnostics
        return {
            'chat_name': chat_name,
            'messages': messages,
            'diagnostics': {
                'text_div_count': text_div_count,
                'processed_messages': len(messages),
                'html_text_chars': text_chars_count,
                'extracted_text_chars': total_extracted_chars
            }
        }
            
    except Exception as e:
        # Return error information for debugging
        return {
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def save_as_json(data, output_file):
    """
    Save parsed data as formatted JSON file.
    
    Writes the structured message data to a JSON file
    with proper Unicode handling and readable indentation.
    
    Args:
        data (dict): Parsed message data to save
        output_file (str): Path to output JSON file
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        # Save with Unicode character preservation and formatting
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_as_txt(data, output_file):
    """
    Save parsed data as human-readable plain text.
    
    Creates a text file with formatted conversation including
    senders, timestamps, replies, and media references.
    
    Args:
        data (dict): Parsed message data to save
        output_file (str): Path to output text file
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write chat name header
        f.write(f"Chat: {data['chat_name']}\n\n")
        
        # Process each message
        for msg in data['messages']:
            # Write message header with ID, time and sender
            f.write(f"msg {msg.get('id', '')}: [{msg.get('datetime', 'Unknown time')}] {msg.get('from', 'Unknown')} wrote: \n")
            
            # Add forwarded information if present
            if 'forwarded_from' in msg:
                f.write(f"[Forwarded from: {msg['forwarded_from']}")
                if 'forwarded_date' in msg:
                    f.write(f" on {msg['forwarded_date']}")
                f.write("]\n")
            
            # Add reply reference if message is a reply
            if 'reply_to_text' in msg:
                if 'reply_to_id' in msg:
                    f.write(f"└─ In reply to msg {msg['reply_to_id']}\n")
                else:
                    f.write(f"└─ {msg['reply_to_text']}\n")
            
            # Write message text content
            if 'text' in msg:
                f.write(f"{msg['text']}\n")
            
            # Add media references
            if 'media' in msg:
                media_type = msg['media']['type']
                if media_type == 'photo':
                    f.write(f"[Photo: {msg['media']['href']}]\n")
                elif media_type == 'video':
                    duration = f", duration: {msg['media']['duration']}" if 'duration' in msg['media'] else ""
                    f.write(f"[Video{duration}: {msg['media']['href']}]\n")
                else:
                    f.write(f"[Media: {media_type} - {msg['media']['href']}]\n")
            
            # Add spacing between messages
            f.write("\n")


def process_single_file(html_file):
    """
    Process a single HTML file and return structured data.
    
    Handles the parsing of one Telegram export file with
    user feedback on progress.
    
    Args:
        html_file (str): Path to HTML file to process
        
    Returns:
        dict: Structured data from parsed file
    """
    print(f"Parsing {html_file}...")
    return parse_telegram_html(html_file)


def main():
    """
    Main function handling command-line arguments and workflow.
    
    Processes command line arguments, handles file selection,
    processes input files, and generates requested output format.
    """
    # Set up command-line argument parser
    parser = argparse.ArgumentParser(description='Parse Telegram HTML exports and convert to text or JSON')
    parser.add_argument('input', help='Input file or directory of HTML files')
    parser.add_argument('--output', '-o', help='Output file path (default: auto-generated)')
    parser.add_argument('--format', '-f', choices=['txt', 'json'], default='txt', help='Output format (default: txt)')
    
    # Parse command line arguments
    args = parser.parse_args()
    
    # Handle directory vs. single file input
    if os.path.isdir(args.input):
        # Process multiple files in directory mode
        html_files = find_telegram_files(args.input)
        
        if not html_files:
            print(f"No Telegram HTML files found in {args.input}")
            sys.exit(1)
        
        # Show files to be processed
        print(f"Found {len(html_files)} Telegram HTML files")
        for i, file in enumerate(html_files, 1):
            print(f"  {i}. {os.path.basename(file)}")
        
        # Process each file in the directory
        parsed_data_list = []
        for html_file in html_files:
            try:
                data = process_single_file(html_file)
                if 'error' in data:
                    print(f"Error parsing {html_file}: {data['error']}")
                    if 'traceback' in data:
                        print(data['traceback'])
                    continue
                parsed_data_list.append(data)
            except Exception as e:
                print(f"Failed to process {html_file}: {str(e)}")
                traceback.print_exc()
        
        # Combine data from all files
        combined_data = merge_parsed_data(parsed_data_list)
        
        # Generate output filename if not specified
        if args.output:
            output_file = args.output
        else:
            # Use directory name as base for output file
            dir_name = os.path.basename(os.path.normpath(args.input))
            output_file = f"{dir_name}_combined.{args.format}"
        
    else:
        # Process in single file mode
        html_file = args.input
        if not os.path.exists(html_file):
            print(f"Error: File {html_file} not found")
            sys.exit(1)
        
        # Parse the single file
        combined_data = process_single_file(html_file)
        
        # Generate output filename if not specified
        if args.output:
            output_file = args.output
        else:
            base_name = os.path.splitext(html_file)[0]
            output_file = f"{base_name}.{args.format}"
    
    # Check for parsing errors
    if 'error' in combined_data:
        print(f"Error parsing file: {combined_data['error']}")
        if 'traceback' in combined_data:
            print(combined_data['traceback'])
        sys.exit(1)
    
    # Save data in requested format
    if args.format == 'json':
        save_as_json(combined_data, output_file)
    else:
        save_as_txt(combined_data, output_file)
    
    # Show success message with stats
    message_count = len(combined_data['messages'])
    print(f"Successfully parsed {message_count} messages from {combined_data['chat_name']}")
    print(f"Output saved to {output_file}")
    
    # Display diagnostic information
    if 'diagnostics' in combined_data:
        diag = combined_data['diagnostics']
        print(f"\nDiagnostics:")
        if 'files_processed' in diag:
            print(f"Files processed: {diag['files_processed']}")
        print(f"Total <div class='text'> elements in HTML: {diag['text_div_count']}")
        print(f"Total messages processed: {diag['processed_messages']}")
        
        # Character count comparison for validation
        html_chars = diag['html_text_chars']
        extracted_chars = diag['extracted_text_chars']
        char_ratio = (extracted_chars / html_chars) * 100 if html_chars > 0 else 0
        
        print(f"Total text characters in HTML: {html_chars}")
        print(f"Total characters extracted: {extracted_chars}")
        print(f"Character extraction ratio: {char_ratio:.1f}%")
        
        # Warning for potential extraction issues
        if diag['text_div_count'] > diag['processed_messages']:
            print(f"Warning: {diag['text_div_count'] - diag['processed_messages']} text elements may not have been processed!")
            
        if char_ratio < 90:
            print(f"Warning: Only {char_ratio:.1f}% of original text characters were extracted!")


if __name__ == "__main__":
    main()
