#!/usr/bin/env python3
"""
Contract Data Extractor - Extracts structured data from contract JSON using Claude API.

Usage:
    source venv/bin/activate
    python contract_extractor.py seebeks.json --url https://sec.gov/...
"""

import argparse
import csv
import json
import os
import re
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

# Section-to-field mapping for targeted extraction
SECTION_FIELD_MAPPING = {
    # Section keywords (regex) → Fields to extract
    "preamble|recitals": [
        "form", "exhibit", "date", "buyer", "buyer_location", "seller", "seller_location",
        "issuer", "issuer_location", "agreement_type"
    ],
    "payment|fee|price|consideration|purchase|invoice|charge": [
        "fee_model", "fee_type", "fee_amount", "fee_mode", "fee_percent",
        "charged_per", "payment_freq", "tranche_trigger", "delivery_trigger",
        "payment_timing", "payment_method"
    ],
    "license|rights|intellectual|property|ip|grant": [
        "license_transferable", "sublicensing", "exclusive",
        "title_and_interest_sold", "ip_sold", "deliverables",
        "derivative_work_owned_by"
    ],
    "term|renewal|termination|scope": [
        "auto_renews", "term", "can_terminate", "termination_notice",
        "breach_terminable", "breach_notice", "breach_prorated",
        "coc_terminable", "coc_notice"
    ],
    "price|adjustment|change": [
        "prices_adjustable", "price_change_notice", "price_change_requires",
        "no_price_changes"
    ],
    "expense|tax|cost|travel": [
        "who_pays_sales_tax", "who_pays_expenses", "expenses_include"
    ],
    "warrant|representation": [
        "reps_and_warranties_mutual", "reps_and_warranties_seller",
        "reps_and_warranties_buyer", "warranty_period"
    ],
    "indemnif|liabilit|damage|limitation": [
        "indemnification", "indemnity_notify", "indemnity_discovery_trigger",
        "liable_for_indirect_damages", "max_liability", "liability_time_limit"
    ],
    "sla|service.level|support|maintenance|error|resolution|response": [
        "has_sla", "sla_tiers", "sla_has_service_credits", "sla_credit_cap_pct",
        "sla_critical_response", "sla_critical_fulltime", "sla_medium_fix",
        "sla_low_fix_required", "sla_goals_strict", "are_upgrades_provided"
    ],
    "govern|law|jurisdiction|venue|arbitration|miscellaneous": [
        "law_in_state_of", "arbitration_in_state_of"
    ],
    "exhibit": [
        "fee_amount", "fee_model", "charged_per", "payment_freq"
    ]
}

# TSV columns in order (68 total)
TSV_COLUMNS = [
    "idx", "form", "exhibit", "date", "buyer", "buyer_location",
    "seller", "seller_location", "issuer", "issuer_location", "url",
    "agreement_type", "license_transferable", "sublicensing", "exclusive",
    "title_and_interest_sold", "ip_sold", "deliverables", "fee_model",
    "fee_type", "fee_amount", "fee_mode", "fee_percent", "charged_per",
    "payment_freq", "tranche_trigger", "delivery_trigger", "auto_renews",
    "term", "can_terminate", "termination_notice", "breach_terminable",
    "breach_notice", "breach_prorated", "coc_terminable", "coc_notice",
    "derivative_work_owned_by", "prices_adjustable", "price_change_notice",
    "price_change_requires", "no_price_changes", "payment_timing",
    "who_pays_sales_tax", "who_pays_expenses", "expenses_include",
    "payment_method", "are_upgrades_provided", "reps_and_warranties_mutual",
    "reps_and_warranties_seller", "reps_and_warranties_buyer",
    "warranty_period", "indemnification", "indemnity_notify",
    "indemnity_discovery_trigger", "liable_for_indirect_damages",
    "max_liability", "liability_time_limit", "has_sla", "sla_tiers",
    "sla_has_service_credits", "sla_credit_cap_pct", "sla_critical_response",
    "sla_critical_fulltime", "sla_medium_fix", "sla_low_fix_required",
    "sla_goals_strict", "law_in_state_of", "arbitration_in_state_of"
]

EXTRACTION_PROMPT = """You are a legal document analyst. Extract structured data from this software contract.

<contract>
{contract_text}
</contract>

Extract the following fields. Return ONLY valid JSON with these exact keys.
Use empty string "" for any field that cannot be determined from the text.

FIELD DEFINITIONS:
- form: SEC form type only (e.g., "10-K", "8-K"). NOT the exhibit type. If metadata shows "EX-10.2", the form is probably "8-K".
- exhibit: Exhibit number only (e.g., "10.6", "10.2"). Extract the number from "EX-10.2" -> "10.2"
- date: Contract date in M/D/YY format (e.g., "2/13/25", "5/26/25")
- buyer: Name of the purchasing party (lowercase, no legal suffixes like "corp.", "inc.", "ltd")
- buyer_location: Buyer's state/country code (e.g., "DE", "FL", "UK", "WY")
- seller: Name of the selling party (lowercase, no legal suffixes like "corp.", "inc.", "ltd")
- seller_location: Seller's state/country code
- issuer: If different from buyer/seller, the SEC filing company (lowercase)
- issuer_location: Issuer's state/country code
- agreement_type: "support", "license", or "purchase"
- license_transferable: "yes" or "no" - can the license be transferred?
- sublicensing: "yes" or "no" - is sublicensing allowed?
- exclusive: "yes" or "no" - is this an exclusive license?
- title_and_interest_sold: "yes" or "no" - is full ownership transferred?
- ip_sold: "yes" or "no" - is intellectual property sold?
- deliverables: What is being delivered (e.g., "support", "license", "software, docs, trade secrets")
- fee_model: "subscription", "usage", "flat", "tranche"
- fee_type: "fixed" or "percentage"
- fee_amount: Numeric amount (e.g., "3500", "960000")
- fee_mode: "dollars", "stock", etc.
- fee_percent: If percentage-based, the decimal (e.g., "0.06")
- charged_per: Time unit for fees (e.g., "month", "claim")
- payment_freq: "monthly", "quarterly", "1", "2" (number of payments)
- tranche_trigger: What triggers each payment (e.g., "software operational")
- delivery_trigger: What triggers delivery (e.g., "first payment")
- auto_renews: "yes" or "no"
- term: Contract duration (e.g., "6mo", "5y", "1y")
- can_terminate: "either side", "mutual agreement", etc.
- termination_notice: Notice period (e.g., "1mo", "6mo", "immediate")
- breach_terminable: "yes" or "no" - can breach terminate the contract?
- breach_notice: Notice period for breach (e.g., "1mo")
- breach_prorated: "yes" or "no" - is payment prorated on breach?
- coc_terminable: "yes" or "no" - can change of control terminate?
- coc_notice: Notice period for change of control
- derivative_work_owned_by: Who owns derivatives ("buyer", "seller")
- prices_adjustable: "yes" or "no"
- price_change_notice: Notice for price changes (e.g., "1mo")
- price_change_requires: What approval needed ("consent", "negotiation")
- no_price_changes: Duration of price freeze (e.g., "6mo")
- payment_timing: When payment is due (e.g., "start + 0d", "end + 30d")
- who_pays_sales_tax: "buyer" or "seller"
- who_pays_expenses: "buyer" or "seller"
- expenses_include: What expenses are covered (quoted string)
- payment_method: "wire", "check", etc.
- are_upgrades_provided: "yes" or "no"
- reps_and_warranties_mutual: Mutual representations (multi-line text)
- reps_and_warranties_seller: Seller's representations (multi-line text)
- reps_and_warranties_buyer: Buyer's representations (multi-line text)
- warranty_period: Duration of warranty (e.g., "0mo", "1y")
- indemnification: Who indemnifies whom (e.g., "seller indemnifies buyer", "mutual")
- indemnity_notify: Notice requirement for indemnification (e.g., "1y")
- indemnity_discovery_trigger: What triggers indemnity (e.g., "constructive")
- liable_for_indirect_damages: "yes" or "no"
- max_liability: Liability cap (e.g., "1x amount paid")
- liability_time_limit: Time limit for liability claims (e.g., "12mo")
- has_sla: "yes" or "no" - does it have Service Level Agreement?
- sla_tiers: Number of SLA tiers (e.g., "3")
- sla_has_service_credits: "yes" or "no"
- sla_credit_cap_pct: Service credit cap as decimal (e.g., "0")
- sla_critical_response: Critical issue response time (e.g., "30m")
- sla_critical_fulltime: "yes" or "no" - 24/7 support for critical?
- sla_medium_fix: Medium issue fix time (e.g., "5d")
- sla_low_fix_required: "yes" or "no" - is low priority fix required?
- sla_goals_strict: "yes" or "no" - are SLA goals binding?
- law_in_state_of: Governing law jurisdiction (e.g., "DE", "FL", "WY")
- arbitration_in_state_of: Arbitration location (e.g., "CA", "FL")

Return a JSON object with all field names as keys. Example:
{{
  "form": "8-K",
  "exhibit": "10.2",
  "date": "5/26/25",
  "buyer": "seebeks",
  "buyer_location": "WY",
  ...
}}
"""


def load_contract_json(json_path: str) -> dict:
    """Load and parse contract JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_contract_text(contract_json: dict) -> str:
    """Format contract JSON into readable text for the LLM."""
    parts = []

    # Add metadata
    metadata = contract_json.get("metadata", {})
    if metadata:
        parts.append("=== METADATA ===")
        for key, value in metadata.items():
            parts.append(f"{key}: {value}")
        parts.append("")

    # Add sections
    sections = contract_json.get("sections", [])
    for section in sections:
        number = section.get("number", "")
        title = section.get("title", "")
        text = section.get("text", "")

        if number == "0":
            parts.append(f"=== PREAMBLE ===")
        else:
            parts.append(f"=== Section {number}: {title} ===")
        parts.append(text)
        parts.append("")

    return "\n".join(parts)


def find_relevant_sections(contract_json: dict, keywords: str) -> list:
    """Find sections whose title or number matches any keyword pattern."""
    relevant = []
    sections = contract_json.get("sections", [])

    for section in sections:
        title = section.get("title", "").lower()
        number = section.get("number", "").lower()

        # Check title and section number against keyword pattern
        if re.search(keywords, title, re.IGNORECASE) or re.search(keywords, number, re.IGNORECASE):
            relevant.append(section)

    return relevant


def format_sections_text(sections: list, metadata: dict = None) -> str:
    """Format a list of sections into readable text for the LLM."""
    parts = []

    # Add metadata if provided
    if metadata:
        parts.append("=== METADATA ===")
        for key, value in metadata.items():
            parts.append(f"{key}: {value}")
        parts.append("")

    # Add sections
    for section in sections:
        number = section.get("number", "")
        title = section.get("title", "")
        text = section.get("text", "")

        if number == "0":
            parts.append(f"=== PREAMBLE ===")
        else:
            parts.append(f"=== Section {number}: {title} ===")
        parts.append(text)
        parts.append("")

    return "\n".join(parts)


def get_field_definitions(fields: list) -> str:
    """Get field definitions for a subset of fields."""
    all_definitions = {
        "form": 'form: SEC form type only (e.g., "10-K", "8-K"). NOT the exhibit type. If metadata shows "EX-10.2", the form is probably "8-K".',
        "exhibit": 'exhibit: Exhibit number only (e.g., "10.6", "10.2"). Extract the number from "EX-10.2" -> "10.2"',
        "date": 'date: Contract date in M/D/YY format (e.g., "2/13/25", "5/26/25")',
        "buyer": 'buyer: Name of the purchasing party (lowercase, no legal suffixes like "corp.", "inc.", "ltd")',
        "buyer_location": 'buyer_location: Buyer\'s state/country code (e.g., "DE", "FL", "UK", "WY")',
        "seller": 'seller: Name of the selling party (lowercase, no legal suffixes like "corp.", "inc.", "ltd")',
        "seller_location": "seller_location: Seller's state/country code",
        "issuer": "issuer: If different from buyer/seller, the SEC filing company (lowercase)",
        "issuer_location": "issuer_location: Issuer's state/country code",
        "agreement_type": 'agreement_type: "support", "license", or "purchase"',
        "license_transferable": 'license_transferable: "yes" or "no" - can the license be transferred?',
        "sublicensing": 'sublicensing: "yes" or "no" - is sublicensing allowed?',
        "exclusive": 'exclusive: "yes" or "no" - is this an exclusive license?',
        "title_and_interest_sold": 'title_and_interest_sold: "yes" or "no" - is full ownership transferred?',
        "ip_sold": 'ip_sold: "yes" or "no" - is intellectual property sold?',
        "deliverables": 'deliverables: What is being delivered (e.g., "support", "license", "software, docs, trade secrets")',
        "fee_model": 'fee_model: "subscription", "usage", "flat", "tranche"',
        "fee_type": 'fee_type: "fixed" or "percentage"',
        "fee_amount": 'fee_amount: Numeric amount (e.g., "3500", "960000")',
        "fee_mode": 'fee_mode: "dollars", "stock", etc.',
        "fee_percent": 'fee_percent: If percentage-based, the decimal (e.g., "0.06")',
        "charged_per": 'charged_per: Time unit for fees (e.g., "month", "claim")',
        "payment_freq": 'payment_freq: "monthly", "quarterly", "1", "2" (number of payments)',
        "tranche_trigger": 'tranche_trigger: What triggers each payment (e.g., "software operational")',
        "delivery_trigger": 'delivery_trigger: What triggers delivery (e.g., "first payment")',
        "auto_renews": 'auto_renews: "yes" or "no"',
        "term": 'term: Contract duration (e.g., "6mo", "5y", "1y")',
        "can_terminate": 'can_terminate: "either side", "mutual agreement", etc.',
        "termination_notice": 'termination_notice: Notice period (e.g., "1mo", "6mo", "immediate")',
        "breach_terminable": 'breach_terminable: "yes" or "no" - can breach terminate the contract?',
        "breach_notice": 'breach_notice: Notice period for breach (e.g., "1mo")',
        "breach_prorated": 'breach_prorated: "yes" or "no" - is payment prorated on breach?',
        "coc_terminable": 'coc_terminable: "yes" or "no" - can change of control terminate?',
        "coc_notice": "coc_notice: Notice period for change of control",
        "derivative_work_owned_by": 'derivative_work_owned_by: Who owns derivatives ("buyer", "seller")',
        "prices_adjustable": 'prices_adjustable: "yes" or "no"',
        "price_change_notice": 'price_change_notice: Notice for price changes (e.g., "1mo")',
        "price_change_requires": 'price_change_requires: What approval needed ("consent", "negotiation")',
        "no_price_changes": 'no_price_changes: Duration of price freeze (e.g., "6mo")',
        "payment_timing": 'payment_timing: When payment is due (e.g., "start + 0d", "end + 30d")',
        "who_pays_sales_tax": 'who_pays_sales_tax: "buyer" or "seller"',
        "who_pays_expenses": 'who_pays_expenses: "buyer" or "seller"',
        "expenses_include": "expenses_include: What expenses are covered (quoted string)",
        "payment_method": 'payment_method: "wire", "check", etc.',
        "are_upgrades_provided": 'are_upgrades_provided: "yes" or "no"',
        "reps_and_warranties_mutual": "reps_and_warranties_mutual: Mutual representations (multi-line text)",
        "reps_and_warranties_seller": "reps_and_warranties_seller: Seller's representations (multi-line text)",
        "reps_and_warranties_buyer": "reps_and_warranties_buyer: Buyer's representations (multi-line text)",
        "warranty_period": 'warranty_period: Duration of warranty (e.g., "0mo", "1y")',
        "indemnification": 'indemnification: Who indemnifies whom (e.g., "seller indemnifies buyer", "mutual")',
        "indemnity_notify": 'indemnity_notify: Notice requirement for indemnification (e.g., "1y")',
        "indemnity_discovery_trigger": 'indemnity_discovery_trigger: What triggers indemnity (e.g., "constructive")',
        "liable_for_indirect_damages": 'liable_for_indirect_damages: "yes" or "no"',
        "max_liability": 'max_liability: Liability cap (e.g., "1x amount paid")',
        "liability_time_limit": 'liability_time_limit: Time limit for liability claims (e.g., "12mo")',
        "has_sla": 'has_sla: "yes" or "no" - does it have Service Level Agreement?',
        "sla_tiers": 'sla_tiers: Number of SLA tiers (e.g., "3")',
        "sla_has_service_credits": 'sla_has_service_credits: "yes" or "no"',
        "sla_credit_cap_pct": 'sla_credit_cap_pct: Service credit cap as decimal (e.g., "0")',
        "sla_critical_response": 'sla_critical_response: Critical issue response time (e.g., "30m")',
        "sla_critical_fulltime": 'sla_critical_fulltime: "yes" or "no" - 24/7 support for critical?',
        "sla_medium_fix": 'sla_medium_fix: Medium issue fix time (e.g., "5d")',
        "sla_low_fix_required": 'sla_low_fix_required: "yes" or "no" - is low priority fix required?',
        "sla_goals_strict": 'sla_goals_strict: "yes" or "no" - are SLA goals binding?',
        "law_in_state_of": 'law_in_state_of: Governing law jurisdiction (e.g., "DE", "FL", "WY")',
        "arbitration_in_state_of": 'arbitration_in_state_of: Arbitration location (e.g., "CA", "FL")',
    }

    return "\n".join(f"- {all_definitions[f]}" for f in fields if f in all_definitions)


def extract_fields_grouped(contract_json: dict, model: str = "claude-sonnet-4-20250514", verbose: bool = False) -> dict:
    """Extract fields using section-targeted grouping to reduce token usage."""
    client = anthropic.Anthropic()
    metadata = contract_json.get("metadata", {})
    all_sections = contract_json.get("sections", [])

    merged_results = {}
    total_input_tokens = 0
    total_output_tokens = 0

    for keywords, fields in SECTION_FIELD_MAPPING.items():
        # Find relevant sections
        sections = find_relevant_sections(contract_json, keywords)

        if not sections:
            if verbose:
                print(f"  No sections found for keywords: {keywords}")
            continue

        if verbose:
            section_names = [f"{s.get('number', '?')}: {s.get('title', '?')[:30]}" for s in sections]
            print(f"  Extracting {len(fields)} fields from {len(sections)} sections: {section_names}")

        # Format just these sections
        section_text = format_sections_text(sections, metadata)
        field_defs = get_field_definitions(fields)

        prompt = f"""You are a legal document analyst. Extract structured data from this contract excerpt.

<contract_excerpt>
{section_text}
</contract_excerpt>

Extract ONLY these fields. Return valid JSON with these exact keys.
Use empty string "" for any field that cannot be determined.

FIELDS TO EXTRACT:
{field_defs}

Return a JSON object with only the requested fields. Example format:
{{
  "{fields[0]}": "value",
  ...
}}"""

        response = client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        # Parse JSON from response
        response_text = response.content[0].text
        json_match = re.search(r'```json?\s*([\s\S]*?)\s*```', response_text)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                json_str = json_match.group(0)
            else:
                if verbose:
                    print(f"  Warning: Could not parse JSON for group {keywords}")
                continue

        try:
            group_results = json.loads(json_str)
            # Only merge non-empty values, don't overwrite existing values
            for field, value in group_results.items():
                if field in fields and value and (field not in merged_results or not merged_results[field]):
                    merged_results[field] = value
        except json.JSONDecodeError as e:
            if verbose:
                print(f"  Warning: JSON decode error for group {keywords}: {e}")
            continue

    if verbose:
        print(f"  Total tokens: {total_input_tokens} input, {total_output_tokens} output")

    return merged_results


def extract_fields(contract_text: str, model: str = "claude-sonnet-4-20250514") -> dict:
    """Use Claude to extract structured fields from contract text."""
    client = anthropic.Anthropic()

    prompt = EXTRACTION_PROMPT.format(contract_text=contract_text)

    response = client.messages.create(
        model=model,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse JSON from response
    response_text = response.content[0].text

    # Try to extract JSON from the response
    # Handle case where response might have markdown code blocks
    json_match = re.search(r'```json?\s*([\s\S]*?)\s*```', response_text)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find raw JSON object
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            json_str = json_match.group(0)
        else:
            raise ValueError(f"Could not find JSON in response: {response_text[:500]}")

    return json.loads(json_str)


def get_next_idx(tsv_path: str) -> int:
    """Get the next available index for a new row."""
    if not os.path.exists(tsv_path):
        return 0

    with open(tsv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        rows = list(reader)

    # Skip header rows (first 2 rows)
    data_rows = rows[2:] if len(rows) > 2 else []

    if not data_rows:
        return 0

    max_idx = 0
    for row in data_rows:
        if row and row[0].isdigit():
            max_idx = max(max_idx, int(row[0]))

    return max_idx + 1


def append_to_tsv(tsv_path: str, extracted_data: dict, url: str) -> int:
    """Append extracted data as a new row to the TSV file."""
    idx = get_next_idx(tsv_path)
    extracted_data['idx'] = str(idx)
    extracted_data['url'] = url

    # Build row in correct column order
    row = []
    for col in TSV_COLUMNS:
        value = extracted_data.get(col, "")
        if value is None:
            value = ""
        row.append(str(value))

    # Append to file
    with open(tsv_path, 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(row)

    return idx


def main():
    parser = argparse.ArgumentParser(
        description='Extract contract data using Claude API'
    )
    parser.add_argument(
        'input',
        type=str,
        help='JSON file to process'
    )
    parser.add_argument(
        '--url',
        type=str,
        required=True,
        help='Source URL for the contract'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='raw.tsv',
        help='Output TSV file path (default: raw.tsv)'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='claude-sonnet-4-20250514',
        help='Claude model to use (default: claude-sonnet-4-20250514)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show extracted data without writing to TSV'
    )
    parser.add_argument(
        '--grouped',
        action='store_true',
        help='Use section-targeted extraction (reduces API costs by ~60-70%%)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed extraction progress'
    )

    args = parser.parse_args()

    # Verify API key
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("Error: ANTHROPIC_API_KEY not found in environment.")
        print("Please set it in your .env file.")
        return 1

    # Load and process contract
    print(f"Loading {args.input}...")
    contract_json = load_contract_json(args.input)

    if args.grouped:
        print(f"Extracting fields using section targeting ({args.model})...")
        extracted = extract_fields_grouped(contract_json, args.model, args.verbose)

        # Check if we got enough fields, fallback to full extraction if needed
        expected_fields = len(TSV_COLUMNS) - 2  # Exclude idx and url
        extracted_count = sum(1 for v in extracted.values() if v)
        if extracted_count < expected_fields * 0.3:  # Less than 30% populated
            print(f"  Warning: Only {extracted_count} fields extracted. Falling back to full extraction...")
            contract_text = format_contract_text(contract_json)
            extracted = extract_fields(contract_text, args.model)
    else:
        print("Formatting contract text...")
        contract_text = format_contract_text(contract_json)

        print(f"Extracting fields using {args.model}...")
        extracted = extract_fields(contract_text, args.model)

    if args.dry_run:
        print("\n=== Extracted Data (dry run) ===")
        print(json.dumps(extracted, indent=2))
        return 0

    print(f"Appending to {args.output}...")
    idx = append_to_tsv(args.output, extracted, args.url)

    print(f"Success! Added row with idx={idx}")
    return 0


if __name__ == '__main__':
    exit(main())
