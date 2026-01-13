#!/usr/bin/env python3
"""
Main pipeline for contract analysis.

This script analyzes HTML files to predict both support contract status
and auto-renewal status, outputting results as tab-separated values.
"""

import sys
import argparse
from pathlib import Path

from detect_support_contract import (
    parse_html_file,
    extract_text_content,
    detect_support_contract,
    detect_auto_renew
)


def main():
    """Main function to run the pipeline."""
    print("Starting contract analysis pipeline...")

    parser = argparse.ArgumentParser(
        description='Analyze HTML file for support contract and auto-renewal status'
    )
    parser.add_argument(
        'html_file',
        type=str,
        help='Path to the HTML file to analyze'
    )
    
    args = parser.parse_args()
    
    # Convert to Path object for better handling
    file_path = Path(args.html_file)
    
    # Parse the HTML file
    soup = parse_html_file(file_path)
    if soup is None:
        sys.exit(1)
    
    # Extract text content
    text = extract_text_content(soup)
    if not text:
        print("Error: Could not extract text content from HTML file.", file=sys.stderr)
        sys.exit(1)
    
    # Detect support contract status
    is_support_contract = detect_support_contract(text)
    
    # Detect auto-renewal status
    is_auto_renew = detect_auto_renew(text)
    
    # Output results as tab-separated values: support_contract<TAB>auto_renewal
    print(f"{is_support_contract}\t{is_auto_renew}")


if __name__ == '__main__':
    main()
