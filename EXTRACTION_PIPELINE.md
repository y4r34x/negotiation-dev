# Contract Extraction Pipeline

## Overview

This pipeline extracts structured data from SEC EDGAR contract filings and converts them to ML-ready TSV format.

```
SEC EDGAR HTML → html_parser.py → JSON → contract_extractor.py → raw.tsv
```

## Current State (Completed)

### Phase 1: Setup ✅
- Virtual environment: `venv/` with `anthropic`, `python-dotenv`, `beautifulsoup4`
- API key configured in `.env`

### Phase 2: Minimal Extractor ✅
- Created `contract_extractor.py` - LLM-based field extraction
- Updated `html_parser.py` - now parses exhibits after signature block

### Files Modified/Created

| File | Purpose |
|------|---------|
| `html_parser.py` | Parses HTML → JSON, includes exhibits |
| `contract_extractor.py` | Extracts 68 fields using Claude API |
| `.env` | Contains `ANTHROPIC_API_KEY` |
| `venv/` | Python virtual environment |

## Usage

```bash
# Activate venv
source venv/bin/activate

# Parse HTML to JSON (with exhibits)
python html_parser.py contract.html -o contract.json

# Extract fields (dry run)
python contract_extractor.py contract.json --url "https://sec.gov/..." --dry-run

# Extract and append to TSV
python contract_extractor.py contract.json --url "https://sec.gov/..."
```

## TSV Schema (68 columns)

```
idx, form, exhibit, date, buyer, buyer_location, seller, seller_location,
issuer, issuer_location, url, agreement_type, license_transferable,
sublicensing, exclusive, title_and_interest_sold, ip_sold, deliverables,
fee_model, fee_type, fee_amount, fee_mode, fee_percent, charged_per,
payment_freq, tranche_trigger, delivery_trigger, auto_renews, term,
can_terminate, termination_notice, breach_terminable, breach_notice,
breach_prorated, coc_terminable, coc_notice, derivative_work_owned_by,
prices_adjustable, price_change_notice, price_change_requires,
no_price_changes, payment_timing, who_pays_sales_tax, who_pays_expenses,
expenses_include, payment_method, are_upgrades_provided,
reps_and_warranties_mutual, reps_and_warranties_seller,
reps_and_warranties_buyer, warranty_period, indemnification,
indemnity_notify, indemnity_discovery_trigger, liable_for_indirect_damages,
max_liability, liability_time_limit, has_sla, sla_tiers,
sla_has_service_credits, sla_credit_cap_pct, sla_critical_response,
sla_critical_fulltime, sla_medium_fix, sla_low_fix_required,
sla_goals_strict, law_in_state_of, arbitration_in_state_of
```

---

## Phase 3: Section Targeting ✅

### Goal
Reduce API costs by sending only relevant sections for each field group instead of the full contract.

### Approach
Map fields to section keywords, extract only matching sections for each API call.

### Usage
```bash
# Section-targeted extraction (saves ~50% tokens)
python contract_extractor.py nex.json --url "https://sec.gov/..." --grouped --dry-run

# With verbose output to see which sections are matched
python contract_extractor.py nex.json --url "https://sec.gov/..." --grouped --verbose --dry-run
```

### Section-to-Field Mapping

```python
SECTION_FIELD_MAPPING = {
    # Section keywords → Fields to extract
    "preamble|recitals": [
        "date", "buyer", "buyer_location", "seller", "seller_location",
        "issuer", "issuer_location", "agreement_type"
    ],
    "payment|fee|price|consideration|purchase": [
        "fee_model", "fee_type", "fee_amount", "fee_mode", "fee_percent",
        "charged_per", "payment_freq", "tranche_trigger", "delivery_trigger",
        "payment_timing", "payment_method"
    ],
    "license|rights|intellectual|property|ip": [
        "license_transferable", "sublicensing", "exclusive",
        "title_and_interest_sold", "ip_sold", "deliverables",
        "derivative_work_owned_by"
    ],
    "term|renewal|termination": [
        "auto_renews", "term", "can_terminate", "termination_notice",
        "breach_terminable", "breach_notice", "breach_prorated",
        "coc_terminable", "coc_notice"
    ],
    "price|adjustment|change": [
        "prices_adjustable", "price_change_notice", "price_change_requires",
        "no_price_changes"
    ],
    "expense|tax|cost": [
        "who_pays_sales_tax", "who_pays_expenses", "expenses_include"
    ],
    "warrant|representation": [
        "reps_and_warranties_mutual", "reps_and_warranties_seller",
        "reps_and_warranties_buyer", "warranty_period"
    ],
    "indemnif|liability|damage": [
        "indemnification", "indemnity_notify", "indemnity_discovery_trigger",
        "liable_for_indirect_damages", "max_liability", "liability_time_limit"
    ],
    "sla|service.level|support|maintenance": [
        "has_sla", "sla_tiers", "sla_has_service_credits", "sla_credit_cap_pct",
        "sla_critical_response", "sla_critical_fulltime", "sla_medium_fix",
        "sla_low_fix_required", "sla_goals_strict", "are_upgrades_provided"
    ],
    "govern|law|jurisdiction|venue|arbitration": [
        "law_in_state_of", "arbitration_in_state_of"
    ],
    "exhibit": [
        "fee_amount"  # Often in Exhibit A
    ]
}
```

### Implementation Steps

1. **Add section selector function** to `contract_extractor.py`:
   ```python
   def find_relevant_sections(contract_json, keywords):
       """Find sections whose title matches any keyword."""
       relevant = []
       for section in contract_json["sections"]:
           title = section["title"].lower()
           for kw in keywords:
               if re.search(kw, title, re.IGNORECASE):
                   relevant.append(section)
                   break
       return relevant
   ```

2. **Modify extraction to use groups**:
   - For each field group, find relevant sections
   - Send smaller prompt with just those sections
   - Merge results from all groups

3. **Add fallback**:
   - If section matching fails, fall back to full text
   - Log which sections were used for debugging

### Actual Cost Savings

| Approach | Input Tokens | Output Tokens | Cost (Sonnet) |
|----------|--------------|---------------|---------------|
| Full text | ~10,000 | ~1,000 | ~$0.04 |
| Section-targeted | ~5,200 | ~800 | ~$0.02 |

**~50% cost reduction** (tested on nex.json support agreement)

---

## Phase 4: Batch Processing (TODO)

### Features to Add

1. **Batch CLI**:
   ```bash
   python contract_extractor.py --batch json_dir/ --url-mapping urls.csv
   ```

2. **URL mapping file** (urls.csv):
   ```csv
   filename,url
   contract1.json,https://sec.gov/...
   contract2.json,https://sec.gov/...
   ```

3. **Retry logic**:
   - Retry on rate limit (exponential backoff)
   - Retry on transient API errors
   - Skip already-processed URLs

4. **Progress tracking**:
   - Log processed/failed files
   - Resume from last successful

---

## Known Issues / Notes

1. **form field**: Not in contract JSON, comes from SEC filing metadata. May need CLI arg `--form 10-K`.

2. **Exhibit parsing**: Added to `html_parser.py`. Finds `EXHIBIT A`, `EXHIBIT B`, etc. after signature block.

3. **Duration format**: Use `Xd` (days), `Xmo` (months), `Xy` (years).

4. **Boolean fields**: Use `yes`, `no`, or empty string.

5. **Party names**: Lowercase, no legal suffixes (corp., inc., ltd).

---

## Test Commands

```bash
# Re-parse HTML with exhibits
python html_parser.py nexcient-i2-250213.html -o nex.json

# Test extraction (dry run)
python contract_extractor.py nex.json --url "https://www.sec.gov/..." --dry-run

# Full extraction test
python contract_extractor.py seebeks.json --url "https://example.com/test" --dry-run
```

## Example JSON Structure (from html_parser.py)

```json
{
  "metadata": {
    "type": "EX-10.6",
    "sequence": "2",
    "filename": "nexscient_ex106.htm",
    "description": "SOFTWARE SUPPORT AGREEMENT"
  },
  "sections": [
    {"number": "0", "title": "Preamble", "text": "..."},
    {"number": "1", "title": "SCOPE OF THE AGREEMENT", "text": ""},
    {"number": "1.1", "title": "Term of the Agreement", "text": "..."},
    ...
    {"number": "Exhibit A", "title": "SOFTWARE SUPPORT ORDER", "text": "...$3,500 per month..."},
    {"number": "Exhibit B", "title": "WIRE TRANSFER INSTRUCTIONS", "text": "..."}
  ]
}
```
