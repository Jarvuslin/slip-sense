"""Per-document-type extraction prompts for GPT-4o structured output."""

_T4_PROMPT = """You are an expert at extracting data from Canadian T4 tax slips (Statement of Remuneration Paid).

Extract ALL of the following fields from the T4 image. For each field, also provide a confidence score (0.0 to 1.0) in the field_confidences dict, keyed by the field name.

## Fields to Extract
- **tax_year**: The tax year shown on the slip
- **employer_name**: Name of the employer
- **employer_address**: Employer's address
- **employee_name**: Name of the employee
- **sin**: Social Insurance Number (9 digits, format XXX-XXX-XXX)
- **employment_income**: Box 14 – Total employment income
- **cpp_contributions**: Box 16 – Employee's CPP contributions
- **cpp2_contributions**: Box 16A – Second CPP contributions (if present, else null)
- **ei_premiums**: Box 18 – Employee's EI premiums
- **income_tax_deducted**: Box 22 – Income tax deducted
- **pension_adjustment**: Box 52 – Pension adjustment (if present, else null)
- **union_dues**: Box 44 – Union dues (if present, else null)
- **charitable_donations**: Box 46 – Charitable donations (if present, else null)
- **rpp_contributions**: Box 20 – RPP contributions (if present, else null)
- **employment_code**: Box 29 – Employment code (if present, else null)

## Rules
- Return dollar amounts as numbers (not strings), e.g. 52000.00 not "$52,000.00"
- If a field is not visible or not applicable, return null for that field
- For SIN, return the full 9-digit number (it will be masked downstream)
- Confidence should reflect how clearly readable each value is in the image

Return your response as JSON matching the required schema."""

_T5_PROMPT = """You are an expert at extracting data from Canadian T5 tax slips (Statement of Investment Income).

Extract ALL of the following fields from the T5 image. For each field, provide a confidence score (0.0 to 1.0) in field_confidences.

## Fields to Extract
- **tax_year**: The tax year shown on the slip
- **payer_name**: Name of the payer/institution
- **recipient_name**: Name of the recipient
- **sin**: Social Insurance Number
- **actual_dividends_eligible**: Box 10 – Actual amount of eligible dividends
- **actual_dividends_other**: Box 11 – Actual amount of dividends other than eligible
- **interest_income**: Box 13 – Interest from Canadian sources
- **capital_gains_dividends**: Box 18 – Capital gains dividends
- **foreign_income**: Box 15 – Foreign income
- **taxable_dividends_eligible**: Box 24 – Taxable amount of eligible dividends
- **taxable_dividends_other**: Box 25 – Taxable amount of other dividends
- **dividend_tax_credit_eligible**: Box 26 – Dividend tax credit for eligible dividends

## Rules
- Dollar amounts as numbers, null if not present
- Return full SIN for downstream masking

Return your response as JSON matching the required schema."""

_T2202_PROMPT = """You are an expert at extracting data from Canadian T2202 tax forms (Tuition and Enrolment Certificate).

Extract ALL of the following fields. Provide confidence scores in field_confidences.

## Fields to Extract
- **tax_year**: The tax year
- **institution_name**: Name of the educational institution
- **student_name**: Name of the student
- **sin**: Social Insurance Number
- **tuition_fees_eligible**: Box A – Eligible tuition fees
- **months_part_time**: Box B – Number of months part-time
- **months_full_time**: Box C – Number of months full-time

## Rules
- Dollar amounts as numbers, months as integers
- Null for fields not present

Return your response as JSON matching the required schema."""

_RRSP_PROMPT = """You are an expert at extracting data from Canadian RRSP Contribution Receipts.

Extract ALL of the following fields. Provide confidence scores in field_confidences.

## Fields to Extract
- **tax_year**: The tax year the contribution applies to
- **issuer_name**: Name of the financial institution
- **contributor_name**: Name of the contributor
- **sin**: Social Insurance Number
- **contribution_amount**: Total RRSP contribution amount
- **contribution_date**: Date of contribution (YYYY-MM-DD format if possible)
- **first_60_days**: Whether this contribution was made in the first 60 days of the following year (true/false/null if unclear)

## Rules
- Dollar amounts as numbers
- Dates in YYYY-MM-DD format when possible
- Null for fields not present

Return your response as JSON matching the required schema."""

_GENERIC_PROMPT = """You are an expert at extracting data from Canadian tax documents.

This document has been classified but does not match one of the primary supported types (T4, T5, T2202, RRSP).

Extract whatever structured information you can find:
- Document type and tax year
- Names (payer, recipient, employer, employee)
- All dollar amounts with their box numbers or labels
- Any identification numbers (mask SINs after extraction)

Return your findings as a JSON object with descriptive field names and a field_confidences dict."""

_PROMPTS: dict[str, str] = {
    "T4": _T4_PROMPT,
    "T5": _T5_PROMPT,
    "T2202": _T2202_PROMPT,
    "RRSP": _RRSP_PROMPT,
}


def get_extraction_prompt(doc_type: str) -> str:
    return _PROMPTS.get(doc_type, _GENERIC_PROMPT)
