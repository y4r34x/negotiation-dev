#!/usr/bin/env python3
"""
SEC EDGAR HTML Parser

Parses SEC EDGAR HTML/HTM contract filings and converts them to structured JSON
with metadata and numbered sections.
"""

import re
import json
import argparse
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString


def parse_metadata(html_content: str) -> dict:
    """
    Extract SEC EDGAR metadata from the document header.

    The metadata appears in a non-standard format:
    <type>EX-10.2
    <sequence>2
    <filename>filename.htm
    <description>DESCRIPTION TEXT

    Args:
        html_content: Raw HTML content as string

    Returns:
        Dictionary with type, sequence, filename, description
    """
    metadata = {
        "type": "",
        "sequence": "",
        "filename": "",
        "description": ""
    }

    # Extract each metadata field using regex
    type_match = re.search(r'<type>([^\n<]+)', html_content, re.IGNORECASE)
    if type_match:
        metadata["type"] = type_match.group(1).strip()

    seq_match = re.search(r'<sequence>([^\n<]+)', html_content, re.IGNORECASE)
    if seq_match:
        metadata["sequence"] = seq_match.group(1).strip()

    filename_match = re.search(r'<filename>([^\n<]+)', html_content, re.IGNORECASE)
    if filename_match:
        metadata["filename"] = filename_match.group(1).strip()

    desc_match = re.search(r'<description>([^\n<]+)', html_content, re.IGNORECASE)
    if desc_match:
        metadata["description"] = desc_match.group(1).strip()

    return metadata


def clean_text(text: str) -> str:
    """
    Clean up text by normalizing whitespace and removing artifacts.

    Args:
        text: Raw text content

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Replace non-breaking spaces and other unicode spaces
    text = text.replace('\xa0', ' ')
    text = text.replace('\u00a0', ' ')

    # Remove HTML comment artifacts (Field: Page, Field: Sequence, etc.)
    text = re.sub(r'Field:\s*/?(?:Page|Sequence|/Page|/Sequence)[^F]*?(?=Field:|$)', '', text)
    text = re.sub(r'Field:\s*\S+[^F]*', '', text)

    # Remove standalone page numbers at end of text (e.g., " 2" or " 3")
    text = re.sub(r'\s+\d{1,2}\s*$', '', text)

    # Normalize multiple spaces to single space
    text = re.sub(r' +', ' ', text)

    # Normalize multiple newlines to double newline (paragraph break)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    # Remove empty lines at start/end
    text = text.strip()

    return text


def find_section_markers(soup) -> list:
    """
    Find all section markers in the document.

    Handles two formats:
    1. Table-based: <td><i>1.</i></td><td><i>Title</i></td>
    2. Paragraph-based: <strong>1.</strong> <strong>TITLE</strong>

    Args:
        soup: BeautifulSoup object

    Returns:
        List of tuples: (section_number, title, element)
    """
    sections = []

    # Pattern for section numbers (1. or 1.1. or 1.1)
    section_pattern = re.compile(r'^(\d+\.?\d*\.?)\s*$')

    # Strategy 1: Look for italic numbers in table cells (seebeks format)
    for td in soup.find_all('td'):
        italic = td.find('i')
        if italic:
            text = italic.get_text(strip=True)
            match = section_pattern.match(text)
            if match:
                section_num = match.group(1).rstrip('.')
                # Find the title in the next td or within this row
                row = td.find_parent('tr')
                if row:
                    tds = row.find_all('td')
                    for next_td in tds:
                        if next_td != td:
                            title_italic = next_td.find('i')
                            if title_italic:
                                title = title_italic.get_text(strip=True)
                                if title and not section_pattern.match(title):
                                    sections.append((section_num, title, row))
                                    break

    # Strategy 2: Look for bold numbers in paragraphs (nexscient format)
    for p in soup.find_all('p'):
        strongs = p.find_all('strong')
        if len(strongs) >= 1:
            first_strong = strongs[0]
            text = first_strong.get_text(strip=True)
            match = section_pattern.match(text)
            if match:
                section_num = match.group(1).rstrip('.')
                # Look for title in subsequent strong tags or text
                title = ""
                for strong in strongs[1:]:
                    title_text = strong.get_text(strip=True)
                    if title_text and not section_pattern.match(title_text):
                        title = title_text
                        break

                # If no title in strong, check remaining text
                if not title:
                    full_text = p.get_text(strip=True)
                    # Remove the section number from the beginning
                    title = re.sub(r'^\d+\.?\d*\.?\s*', '', full_text).strip()

                if title:
                    sections.append((section_num, title, p))

    # Sort by section number (handle 1, 1.1, 1.2, 2, etc.)
    def section_sort_key(item):
        num = item[0]
        parts = num.split('.')
        return tuple(int(p) if p else 0 for p in parts)

    sections.sort(key=section_sort_key)

    # Remove duplicates while preserving order
    seen = set()
    unique_sections = []
    for section in sections:
        key = (section[0], section[1])
        if key not in seen:
            seen.add(key)
            unique_sections.append(section)

    return unique_sections


def get_element_position(element, soup) -> int:
    """
    Get the position of an element in the document.

    Args:
        element: BeautifulSoup element
        soup: Root soup object

    Returns:
        Position index
    """
    all_elements = list(soup.descendants)
    try:
        return all_elements.index(element)
    except ValueError:
        return 0


def extract_text_between_elements(start_elem, end_elem, soup) -> str:
    """
    Extract text content between two elements.

    Args:
        start_elem: Starting element (exclusive)
        end_elem: Ending element (exclusive) or None for end of document
        soup: Root soup object

    Returns:
        Extracted text content
    """
    text_parts = []
    collecting = False

    # Get all elements in document order
    all_elements = list(soup.descendants)

    start_pos = get_element_position(start_elem, soup)
    end_pos = get_element_position(end_elem, soup) if end_elem else len(all_elements)

    for i, elem in enumerate(all_elements):
        if i <= start_pos:
            continue
        if i >= end_pos:
            break

        if isinstance(elem, NavigableString):
            text = str(elem).strip()
            if text:
                text_parts.append(text)

    return ' '.join(text_parts)


def extract_section_content(section_elem, next_section_elem, soup) -> str:
    """
    Extract the text content for a section.

    Args:
        section_elem: The section header element
        next_section_elem: The next section's element or None
        soup: Root soup object

    Returns:
        Section text content
    """
    # Find all siblings and descendants after section_elem until next_section_elem
    content_parts = []

    # Get all text nodes in document order
    current = section_elem

    # Start from the parent to capture content after the header row/paragraph
    if current.name == 'tr':
        current = current.find_parent('table')

    # Iterate through following siblings and their descendants
    found_start = False
    for elem in soup.descendants:
        if elem == section_elem or (hasattr(elem, 'find_parent') and section_elem in (elem.find_parents() if hasattr(elem, 'find_parents') else [])):
            found_start = True
            continue

        if not found_start:
            continue

        if next_section_elem and (elem == next_section_elem or
            (hasattr(elem, 'find_parent') and next_section_elem in (elem.find_parents() if hasattr(elem, 'find_parents') else []))):
            break

        if isinstance(elem, NavigableString):
            text = str(elem).strip()
            # Stop at signature block
            if 'IN WITNESS WHEREOF' in text.upper():
                break
            if text and text != '\xa0':
                content_parts.append(text)

    text = ' '.join(content_parts)
    return clean_text(text)


def extract_preamble(soup, first_section_elem) -> str:
    """
    Extract the preamble content before the first section.

    Args:
        soup: BeautifulSoup object
        first_section_elem: The first section's element

    Returns:
        Preamble text content
    """
    content_parts = []

    # Find the <text> tag or start of body content
    text_tag = soup.find('text')
    start_elem = text_tag if text_tag else soup.find('body')

    if not start_elem:
        return ""

    # Collect text until we hit the first section
    for elem in start_elem.descendants:
        if first_section_elem and (elem == first_section_elem or
            (hasattr(elem, 'find_parent') and first_section_elem in (elem.find_parents() if hasattr(elem, 'find_parents') else []))):
            break

        if isinstance(elem, NavigableString):
            text = str(elem).strip()
            if text and text != '\xa0':
                content_parts.append(text)

    text = ' '.join(content_parts)
    return clean_text(text)


def find_exhibits(soup) -> list:
    """
    Find all exhibit markers in the document (typically after signature block).

    Exhibits are usually formatted as:
    <strong><u>EXHIBIT A</u></strong>
    <strong><u>EXHIBIT TITLE</u></strong>

    Args:
        soup: BeautifulSoup object

    Returns:
        List of tuples: (exhibit_name, title, element)
    """
    exhibits = []
    exhibit_pattern = re.compile(r'^EXHIBIT\s+([A-Z]|\d+)$', re.IGNORECASE)

    for p in soup.find_all('p'):
        # Look for EXHIBIT markers in strong+underline tags
        strong = p.find('strong')
        if strong:
            u_tag = strong.find('u')
            if u_tag:
                text = u_tag.get_text(strip=True)
                match = exhibit_pattern.match(text)
                if match:
                    exhibit_name = f"Exhibit {match.group(1).upper()}"

                    # Look for title in next sibling paragraph
                    title = ""
                    next_p = p.find_next_sibling('p')
                    if next_p:
                        next_strong = next_p.find('strong')
                        if next_strong:
                            next_u = next_strong.find('u')
                            if next_u:
                                potential_title = next_u.get_text(strip=True)
                                # Make sure it's not another EXHIBIT marker
                                if not exhibit_pattern.match(potential_title):
                                    title = potential_title

                    exhibits.append((exhibit_name, title, p))

    return exhibits


def extract_exhibit_content(exhibit_elem, next_exhibit_elem, soup) -> str:
    """
    Extract text content for an exhibit.

    Args:
        exhibit_elem: The exhibit header element
        next_exhibit_elem: The next exhibit's element or None
        soup: Root soup object

    Returns:
        Exhibit text content
    """
    content_parts = []
    found_start = False
    skip_title = True  # Skip the first line after exhibit name (usually the title)

    for elem in soup.descendants:
        if elem == exhibit_elem:
            found_start = True
            continue

        if not found_start:
            continue

        if next_exhibit_elem and elem == next_exhibit_elem:
            break

        if isinstance(elem, NavigableString):
            text = str(elem).strip()
            if text and text != '\xa0':
                # Skip the exhibit title (first non-empty text after exhibit name)
                if skip_title and text:
                    skip_title = False
                    continue
                content_parts.append(text)

    text = ' '.join(content_parts)
    return clean_text(text)


def parse_html_to_json(file_path: str) -> dict:
    """
    Parse an SEC EDGAR HTML file to structured JSON.

    Args:
        file_path: Path to the HTML file

    Returns:
        Dictionary with metadata and sections
    """
    # Read the file
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        html_content = f.read()

    # Parse metadata from raw content (before BeautifulSoup modifies it)
    metadata = parse_metadata(html_content)

    # Parse HTML structure
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find all section markers
    section_markers = find_section_markers(soup)

    # Build sections list
    sections = []

    # Add preamble as section 0
    if section_markers:
        preamble_text = extract_preamble(soup, section_markers[0][2])
        if preamble_text:
            sections.append({
                "number": "0",
                "title": "Preamble",
                "text": preamble_text
            })

    # Extract each section's content
    for i, (section_num, title, elem) in enumerate(section_markers):
        next_elem = section_markers[i + 1][2] if i + 1 < len(section_markers) else None

        section_text = extract_section_content(elem, next_elem, soup)

        # Skip if we hit the signature block
        if 'IN WITNESS WHEREOF' in section_text.upper():
            # Truncate at signature block
            idx = section_text.upper().find('IN WITNESS WHEREOF')
            section_text = section_text[:idx].strip()

        if section_text or title:  # Include section even if text is empty (might just have subsections)
            sections.append({
                "number": section_num,
                "title": title,
                "text": section_text
            })

    # Find and extract exhibits (after signature block)
    exhibits = find_exhibits(soup)
    for i, (exhibit_name, title, elem) in enumerate(exhibits):
        next_elem = exhibits[i + 1][2] if i + 1 < len(exhibits) else None
        exhibit_text = extract_exhibit_content(elem, next_elem, soup)

        if exhibit_text or title:
            sections.append({
                "number": exhibit_name,
                "title": title,
                "text": exhibit_text
            })

    return {
        "metadata": metadata,
        "sections": sections
    }


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description='Parse SEC EDGAR HTML files to structured JSON'
    )
    parser.add_argument(
        'input_files',
        nargs='+',
        type=str,
        help='Path(s) to HTML file(s) to parse'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output file path or directory (for multiple files)'
    )
    parser.add_argument(
        '--pretty',
        action='store_true',
        default=True,
        help='Pretty print JSON output (default: True)'
    )

    args = parser.parse_args()

    for input_file in args.input_files:
        input_path = Path(input_file)

        if not input_path.exists():
            print(f"Error: File not found: {input_file}", file=__import__('sys').stderr)
            continue

        # Parse the file
        result = parse_html_to_json(str(input_path))

        # Determine output
        if args.output:
            output_path = Path(args.output)
            if output_path.is_dir() or (len(args.input_files) > 1 and not output_path.suffix):
                # Output to directory
                output_path.mkdir(parents=True, exist_ok=True)
                output_file = output_path / f"{input_path.stem}.json"
            else:
                output_file = output_path

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2 if args.pretty else None, ensure_ascii=False)
            print(f"Written: {output_file}")
        else:
            # Output to stdout
            print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))


if __name__ == '__main__':
    main()
