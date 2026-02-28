# Cursor Prompt: AI-Native Tax Document Processor & Anomaly Detector

## Project Context

I'm building a working AI system prototype for Wealthsimple's AI Builder program application. The goal is to demonstrate **systems thinking, clear human/AI boundaries, and real-world judgment** — NOT a chatbot wrapper. This is a **multi-stage document processing pipeline** that takes Canadian tax documents as input, extracts structured data, cross-references across documents, detects anomalies and missed deductions, and produces a confidence-scored report for the user to review.

This should feel like a **reimagined, AI-native version** of the tax review process — not AI layered on top of an old workflow.

---

## What We're Building

**SlipSense.AI** — an AI-powered tax document analysis system that acts as an intelligent second pair of eyes on a user's tax filing.

### Core Value Proposition
A user uploads their tax slips before or during tax filing. The system:
1. Extracts all relevant financial data from each document
2. Cross-references data across documents for consistency
3. Detects anomalies, inconsistencies, and potential missed deductions/credits
4. Produces a structured, confidence-scored report where every finding is categorized as: **Auto-verified** (high confidence), **Needs Review** (medium confidence, user should double-check), or **Flagged** (low confidence or potential issue requiring action)

The user always makes the final call. The AI never files anything — it analyzes and advises.

---

## Tech Stack

- **Backend**: Python, FastAPI
- **AI/LLM**: OpenAI GPT-4o (for document understanding + reasoning) via API
- **Document Processing**: `pdf2image` + `pytesseract` for OCR fallback, but primarily rely on GPT-4o's vision capabilities for direct PDF/image parsing
- **Database**: SQLite (for prototype — stores extracted data, analysis results, session history)
- **Frontend**: React + TypeScript + Tailwind CSS (clean, minimal UI — not the focus, but needs to be functional and clear)
- **File Handling**: Support PDF and image uploads (JPG, PNG)

---

## Supported Input Documents (Canadian Tax Slips)

The system should handle these common Canadian tax documents:

### Employment & Income
- **T4** — Statement of Remuneration Paid (employment income, CPP/EI/tax deducted)
- **T4A** — Statement of Pension, Retirement, Annuity, and Other Income
- **T4E** — Statement of Employment Insurance and Other Benefits

### Investment & Banking
- **T5** — Statement of Investment Income (interest, dividends, capital gains)
- **T3** — Statement of Trust Income Allocations and Designations

### Education
- **T2202** — Tuition and Enrolment Certificate

### RRSP
- **RRSP Contribution Receipts** — from financial institutions

### Other
- **T5007** — Statement of Benefits (social assistance, workers' comp)
- **Charitable Donation Receipts** — from registered charities

For the prototype, focus on **T4, T5, T2202, and RRSP receipts** as the primary supported document types. The others can be listed as "coming soon" in the UI.

---

## System Architecture & Pipeline

### Stage 1: Document Ingestion & Classification
```
User uploads PDF/image → System classifies document type → Routes to appropriate extraction template
```
- Accept single or batch uploads
- Use GPT-4o vision to identify the document type (T4, T5, T2202, etc.)
- If the document can't be classified with >80% confidence, flag it and ask the user to manually identify it
- Store the raw upload and classification result

### Stage 2: Structured Data Extraction
```
Classified document → GPT-4o extracts all fields into structured JSON → Validation checks
```
- For each document type, define an expected schema (e.g., T4 should have: employer name, employment income Box 14, CPP contributions Box 16, EI premiums Box 18, income tax deducted Box 22, etc.)
- Extract all fields into structured JSON
- Run basic validation: Are numeric fields actually numbers? Are SIN formats valid (mask after validation)? Are tax year fields matching the expected year?
- Assign a **field-level confidence score** to each extracted value
- If any critical field has <70% confidence, flag it for user verification

### Stage 3: Cross-Document Analysis
```
All extracted data → Cross-reference engine → Consistency checks + deduction identification
```
This is the most important stage — this is where the system shows real intelligence:

**Consistency Checks:**
- Total income reported across all T4s — does it seem reasonable?
- If multiple T4s exist, flag potential overlap periods (same employer, overlapping dates)
- T5 dividend income — check if eligible vs. ineligible dividend classification is consistent
- RRSP contributions — cross-reference contribution receipts against T4 Box 52 (pension adjustment) to estimate remaining room

**Anomaly Detection:**
- T4 income tax deducted seems unusually low/high relative to employment income
- CPP/EI contributions don't match expected rates for the reported income
- Missing expected documents: e.g., user has T4 showing union dues but no union dues receipt
- T2202 tuition amount seems inconsistent with expected full-time/part-time status

**Missed Deduction/Credit Identification:**
- Has T2202 but may not be claiming education credits
- Has RRSP room remaining based on income but no RRSP contribution receipts
- Has employment income but no claims for work-from-home expenses
- Has medical expenses mentioned nowhere — prompt user to check
- Has charitable donations that could be optimized by combining with spouse

### Stage 4: Report Generation
```
Analysis results → Structured report with confidence tiers → User-facing dashboard
```

Generate a report with three sections:

**✅ Auto-Verified (High Confidence — 90%+)**
Items the system is confident about. Example: "Your T4 from [Employer] reports employment income of $X. All fields extracted successfully and cross-check passed."

**⚠️ Needs Review (Medium Confidence — 60-90%)**
Items that are probably correct but the user should verify. Example: "Your RRSP contribution of $X was detected. Based on your income, you may have approximately $Y of remaining RRSP room. Please verify against your CRA Notice of Assessment."

**🚩 Flagged (Low Confidence or Anomaly Detected — <60% or anomaly)**
Items requiring user action. Example: "Your T4 shows income tax deducted of $X, which appears lower than expected for your income bracket. This could indicate you claimed additional deductions with your employer, or it may be an error. Please verify."

Each finding should include:
- Clear plain-language explanation of what was found
- Why it matters
- What the user should do about it
- The confidence level and what drove it

---

## Human/AI Boundary (CRITICAL — this is what Wealthsimple will evaluate)

Be explicit about these boundaries in both the code and the UI:

### AI Handles:
- Document classification and data extraction
- Pattern matching and cross-referencing
- Anomaly detection based on known tax rules
- Generating plain-language explanations
- Estimating confidence levels

### AI Does NOT Handle:
- Filing taxes or submitting anything to CRA
- Making definitive tax advice claims (always framed as "you may want to check" not "you should do X")
- Accessing CRA accounts or pulling external data
- Handling edge cases like self-employment income, rental income, capital gains calculations (flag these as "complex scenario — consult a tax professional")
- Storing or transmitting SIN numbers (mask immediately after validation)

### The UI Should Clearly Communicate:
- "This is an analysis tool, not tax advice"
- "All findings are suggestions — you make the final decisions"
- "For complex tax situations, consult a qualified tax professional"
- Confidence scores on every finding so users know what to trust

---

## Frontend Requirements

### Upload Page
- Drag-and-drop zone for multiple files
- Show upload progress and document classification in real-time
- List of uploaded documents with their detected type and a "correct this" option if misclassified
- "Analyze" button to kick off the pipeline

### Analysis Dashboard
- Summary card at top: total documents processed, total income detected, number of findings by tier
- Three collapsible sections for Auto-Verified / Needs Review / Flagged findings
- Each finding is a card with: icon, title, description, confidence badge, and action suggestion
- Ability to mark findings as "Reviewed" or "Not Applicable"
- A progress indicator showing which pipeline stage is currently running during analysis

### Document Viewer (nice-to-have)
- Side panel showing the original uploaded document
- When clicking a finding, highlight the relevant area of the source document

---

## Project Structure
```
taxlens/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── routers/
│   │   ├── upload.py            # File upload endpoints
│   │   ├── analysis.py          # Analysis trigger + results endpoints
│   │   └── documents.py         # Document management endpoints
│   ├── services/
│   │   ├── classifier.py        # Document type classification (Stage 1)
│   │   ├── extractor.py         # Structured data extraction (Stage 2)
│   │   ├── analyzer.py          # Cross-document analysis engine (Stage 3)
│   │   ├── reporter.py          # Report generation (Stage 4)
│   │   └── llm.py               # OpenAI API wrapper with retry/error handling
│   ├── models/
│   │   ├── schemas.py           # Pydantic models for each tax document type
│   │   ├── findings.py          # Finding/anomaly data models
│   │   └── database.py          # SQLite models
│   ├── prompts/
│   │   ├── classification.py    # System prompts for document classification
│   │   ├── extraction.py        # System prompts for field extraction (per doc type)
│   │   └── analysis.py          # System prompts for cross-reference analysis
│   └── utils/
│       ├── confidence.py        # Confidence scoring logic
│       ├── tax_rules.py         # Canadian tax rules/thresholds (CPP rates, EI max, brackets)
│       └── validators.py        # Field validation helpers
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── UploadZone.tsx
│   │   │   ├── DocumentList.tsx
│   │   │   ├── AnalysisDashboard.tsx
│   │   │   ├── FindingCard.tsx
│   │   │   ├── ConfidenceBadge.tsx
│   │   │   └── PipelineProgress.tsx
│   │   ├── pages/
│   │   │   ├── Upload.tsx
│   │   │   └── Results.tsx
│   │   ├── hooks/
│   │   │   └── useAnalysis.ts
│   │   └── types/
│   │       └── index.ts
│   └── ...
├── sample_documents/           # Sample/mock tax documents for demo
├── README.md
└── docker-compose.yml
```

---

## Key Implementation Details

### Confidence Scoring System
Create a composable confidence score system:
- **Extraction confidence**: How sure are we about the extracted value? (based on OCR clarity, format matching, LLM confidence)
- **Cross-reference confidence**: Does this value make sense in context of other documents?
- **Rule-based confidence**: Does this value fall within expected ranges based on Canadian tax rules?
- **Overall finding confidence**: Weighted combination of the above

Store the 2025 (for 2024 tax year) Canadian tax constants:
- CPP contribution rate: 5.95%, max pensionable earnings: $68,500, basic exemption: $3,500
- EI premium rate: 1.66%, max insurable earnings: $63,200
- Federal tax brackets and rates
- Basic personal amount: $15,705

### Error Handling & Edge Cases
- What if OCR fails? → Fall back to asking user to re-upload or manually enter key fields
- What if the document is for the wrong tax year? → Flag it clearly
- What if the user uploads a non-tax document? → Classify as "Unknown" and ask them to remove it
- What if the LLM hallucinates a field value? → Cross-check against format validators before accepting
- Rate limiting on OpenAI API → Queue system with status updates to the user

### Privacy Considerations (mention in README)
- SIN numbers are detected, validated for format, then immediately masked in storage
- No data is sent to external services beyond the OpenAI API call (note this as a production concern)
- All uploads are session-scoped and can be deleted by the user
- In production, would need encryption at rest, SOC2 compliance, etc.

---

## README Should Include
- Project overview and motivation
- Architecture diagram (use Mermaid)
- Human/AI boundary explanation
- How confidence scoring works
- Known limitations and what a production version would need
- How to run locally
- Sample walkthrough with screenshots

---

## What "Done" Looks Like
1. User can upload 2-4 sample tax documents (provide realistic mock PDFs in sample_documents/)
2. System classifies each document correctly
3. System extracts structured data and shows it to the user
4. System runs cross-document analysis and produces findings
5. Dashboard displays findings organized by confidence tier
6. Each finding has a clear explanation, confidence score, and suggested action
7. The whole thing runs locally with `docker-compose up`
8. README clearly articulates the system design, human/AI boundaries, and tradeoffs

---

## Important Notes
- This is a PROTOTYPE for a job application. It needs to work and demonstrate clear thinking, but it doesn't need to handle every edge case perfectly.
- Prioritize the **pipeline architecture and analysis logic** over frontend polish. The systems thinking is what gets evaluated.
- Use real Canadian tax rules and thresholds — don't fake the numbers.
- Every design decision should be defensible. If you make a tradeoff, add a comment explaining why.
- The confidence scoring system is the secret sauce — make it thoughtful, not just random numbers.
