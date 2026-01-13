#!/usr/bin/env python3
"""
Software Support Contract Detector

This script analyzes HTML files to determine if they represent software support contracts.
It searches for keywords related to maintenance, sustainment, and SLA terms.
Returns 1 if the file is a software support contract, 0 otherwise.
"""

import sys
import argparse
from pathlib import Path
from bs4 import BeautifulSoup


def parse_html_file(file_path):
    """
    Parse an HTML file using Beautiful Soup.
    
    Args:
        file_path: Path to the HTML file
        
    Returns:
        BeautifulSoup object or None if parsing fails
    """
    try:
        # Try to detect encoding automatically, with fallback to windows-1252
        # (common in SEC EDGAR documents)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Parse with html.parser (built-in, no extra dependencies needed)
        soup = BeautifulSoup(content, 'html.parser')
        return soup
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error parsing file: {e}", file=sys.stderr)
        return None


def extract_text_content(soup):
    """
    Extract all text content from the HTML, ignoring tags.
    
    Args:
        soup: BeautifulSoup object
        
    Returns:
        String containing all text content
    """
    if soup is None:
        return ""
    
    # Get all text, stripped of extra whitespace
    text = soup.get_text(separator=' ', strip=False)
    return text


def detect_support_contract(text):
    """
    Determine if the text content represents a software support contract.
    
    Args:
        text: String containing the text content of the HTML
        
    Returns:
        int: 1 if it's a support contract, 0 otherwise
    """
    if not text:
        return 0
    
    # Normalize text to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Strong indicators - explicit contract type mentions
    strong_indicators = [
        'software support agreement',
        'support agreement',
        'software support order',
        'support contract',
        'software maintenance agreement',
        'maintenance agreement'
    ]
    
    # Medium indicators - support-related keywords
    support_keywords = [
        'maintenance and support',
        'software support',
        'support services',
        'maintenance services',
        'sustainment',
        'service level agreement',
        'sla',
        'error resolution',
        'help desk',
        'software maintenance',
        'technical support'
    ]
    
    # Service-specific terms
    service_keywords = [
        'patches',
        'upgrades',
        'bug fixes',
        'trouble tickets',
        'incident response',
        'priority support',
        'response time',
        'uptime guarantee'
    ]
    
    # Check for strong indicators
    for indicator in strong_indicators:
        if indicator in text_lower:
            return 1
    
    # Count occurrences of medium indicators
    support_count = sum(1 for keyword in support_keywords if keyword in text_lower)
    service_count = sum(1 for keyword in service_keywords if keyword in text_lower)
    
    # If multiple support-related keywords are found, likely a support contract
    # Require at least 2-3 strong signals
    if support_count >= 3:
        return 1
    
    # If support keywords AND service keywords are present, likely a support contract
    if support_count >= 2 and service_count >= 2:
        return 1
    
    # If we have a high number of service-specific terms, likely a support contract
    if service_count >= 4:
        return 1
    
    return 0


def detect_auto_renew(text):
    """
    Determine if the contract term will automatically renew.
    
    Args:
        text: String containing the text content of the HTML
        
    Returns:
        int: 1 if the term automatically renews, 0 otherwise
    """
    if not text:
        return 0
    
    # Normalize text to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Strong positive indicators - explicit automatic renewal language
    strong_indicators = [
        'will renew automatically',
        'renew automatically',
        'automatic renewal',
        'auto-renew',
        'automatically renews'
    ]
    
    # Medium positive indicators - renewal-related terms
    medium_indicators = [
        'renewal date',
        'automatic extension',
        'auto renewal',
        'continues automatically',
        'automatic continuation'
    ]
    
    # Negative indicators - explicit non-automatic renewal
    negative_indicators = [
        'will not renew',
        'does not renew automatically',
        'requires renewal',
        'upon mutual agreement',
        'expires unless renewed',
        'requires written notice to renew',
        'must be renewed',
        'renewal requires',
        'no automatic renewal'
    ]
    
    # Check for negative indicators first - if found, return 0
    for indicator in negative_indicators:
        if indicator in text_lower:
            return 0
    
    # Check for strong indicators - if found, return 1
    for indicator in strong_indicators:
        if indicator in text_lower:
            return 1
    
    # Check for medium indicators - multiple medium indicators suggest auto-renewal
    medium_count = sum(1 for indicator in medium_indicators if indicator in text_lower)
    
    # If we find multiple medium indicators, likely auto-renewal
    if medium_count >= 2:
        return 1
    
    # Look for context around "renewal" that suggests automatic renewal
    # Check if "renewal" appears with automatic/auto language nearby
    if 'renewal' in text_lower:
        # Check for automatic renewal context
        renewal_contexts = [
            'renewal date',
            'on the renewal date',
            'at the renewal date',
            'renewal will be automatic',
            'renewal is automatic'
        ]
        for context in renewal_contexts:
            if context in text_lower:
                return 1
    
    return 0


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description='Detect if an HTML file represents a software support contract'
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
    
    # Detect if it's a support contract
    result = detect_support_contract(text)
    
    # Print result (1 or 0) to stdout
    print(result)


if __name__ == '__main__':
    main()