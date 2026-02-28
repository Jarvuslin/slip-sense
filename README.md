# SlipSense.AI — AI-Powered Tax Document Analysis

An intelligent tax document analysis system that acts as a second pair of eyes on your Canadian tax filing. Upload your tax slips, and SlipSense.AI classifies them, extracts structured data, cross-references across documents, detects anomalies, identifies missed deductions, and produces a confidence-scored report — all while making it clear that **you** make the final decisions.

Built as a prototype for the Wealthsimple AI Builder program.

---

## Architecture

```mermaid
flowchart TB
    subgraph frontend [React + Tailwind Frontend]
        Auth["Auth (Login/Signup)"]
        Upload[Upload Page]
        Dashboard[Analysis Dashboard]
    end
    subgraph supa [Supabase]
        SupaAuth[Auth]
        Storage[File Storage]
        PG[(Postgres)]
    end
    subgraph backend [FastAPI Backend]
        MW[JWT Middleware]
        S1[Stage 1: Classifier]
        S2[Stage 2: Extractor]
        S3a[Stage 3a: Rule Engine]
        S3b[Stage 3b: LLM Analyzer]
        S4[Stage 4: Reporter]
    end
    subgraph openai [OpenAI]
        GPT[GPT-4o + Structured Outputs]
    end
    Auth --> SupaAuth
    Upload --> MW --> S1 --> S2 --> S3a --> S3b --> S4
    S1 --> GPT
    S2 --> GPT
    S3b --> GPT
    S4 --> PG
    MW --> Storage
```

### Pipeline Stages

| Stage | What it does | How |
|-------|-------------|-----|
| **1. Classification** | Identifies document type (T4, T5, T2202, RRSP) | GPT-4o vision with structured output |
| **2. Extraction** | Pulls all fields into structured JSON | GPT-4o with per-doc-type schema enforcement |
| **3a. Rule Engine** | Validates CPP/EI rates, tax brackets, RRSP room | Pure Python — deterministic, auditable |
| **3b. LLM Analysis** | Detects missed deductions, patterns, optimization opportunities | GPT-4o with explicit "don't redo the math" instructions |
| **4. Report** | Aggregates findings into tiered, confidence-scored report | Sorted by severity, persisted to Postgres |

---

## Human / AI Boundary

This is the most important design decision in the system.

### AI Handles
- Document classification and data extraction
- Pattern matching and cross-referencing
- Anomaly detection based on known tax rules
- Generating plain-language explanations
- Estimating confidence levels

### AI Does NOT Handle
- Filing taxes or submitting anything to CRA
- Making definitive tax advice claims (always "you may want to check", never "you should")
- Accessing CRA accounts or pulling external data
- Complex scenarios like self-employment, rental income, capital gains (flagged for professional review)
- Storing SIN numbers — they're validated for format, then **immediately masked** before storage

### The UI Communicates
- "This is an analysis tool, not tax advice"
- Confidence scores on every finding
- Whether each finding came from the Rule Engine or AI
- "For complex tax situations, consult a qualified tax professional"

---

## Hybrid Analysis: Why Rule Engine + LLM

The analyzer deliberately splits work between two systems based on what each is good at:

**Rule Engine (deterministic):** Handles all math-based checks — CPP contribution rate validation, EI premium calculations, tax bracket estimates, RRSP room. These are formulas with known correct answers. An LLM adds nothing here and could get them wrong.

**LLM (nuanced):** Handles qualitative analysis — missed deduction identification ("you have tuition but no education credit claim"), lifestyle pattern inference ("multiple T4s suggest mid-year job change"), optimization suggestions. These require contextual reasoning an LLM excels at.

Both produce findings with confidence scores. Rule engine findings get high confidence (they're math). LLM findings are capped at 85% confidence because they're suggestions, not verified facts. The UI labels each finding's source so users know what to trust.

---

## Confidence Scoring

Confidence is **composable**, not a single LLM number:

| Signal | Weight | Source |
|--------|--------|--------|
| Extraction confidence | 40% | Average of per-field LLM confidence scores |
| Rule confidence | 30% | 1.0 if check passes, degrades with deviation |
| Cross-reference confidence | 30% | Agreement score across documents |

**Tier mapping:**
- **>= 90%** → Auto-Verified (green) — high confidence, no action needed
- **60–90%** → Needs Review (amber) — probably correct, worth double-checking
- **< 60%** → Flagged (red) — potential issue requiring user action

---

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy (async), Supabase (Postgres + Auth + Storage)
- **AI:** OpenAI GPT-4o with Structured Outputs (JSON schema enforcement)
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS
- **OCR Fallback:** pytesseract + pdf2image (when GPT-4o vision fails)

---

## Supported Documents

| Document | Description | Status |
|----------|------------|--------|
| T4 | Statement of Remuneration Paid | Supported |
| T5 | Statement of Investment Income | Supported |
| T2202 | Tuition and Enrolment Certificate | Supported |
| RRSP | Contribution Receipt | Supported |
| T4A | Pension/Other Income | Coming soon |
| T3 | Trust Income | Coming soon |
| T4E | EI Benefits | Coming soon |

---

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose
- A [Supabase](https://supabase.com/) project (free tier works)
- An [OpenAI API key](https://platform.openai.com/) with GPT-4o access

### 1. Supabase Setup

1. Create a new Supabase project
2. Go to the SQL Editor and run `supabase/migrations/001_initial_schema.sql`
3. Note your project URL, anon key, service role key, JWT secret, and database connection string

### 2. Environment Variables

```bash
cp .env.example .env
```

Fill in the values:

```env
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_JWT_SECRET=your-jwt-secret
DATABASE_URL=postgresql+asyncpg://postgres.xxx:password@aws-0-region.pooler.supabase.com:6543/postgres
```

### 3. Run with Docker

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

### 4. Run Locally (Development)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### 5. Generate Sample Documents

```bash
cd sample_documents
pip install reportlab
python generate_samples.py
```

This creates four sample PDFs with realistic but fictional data, including an intentional CPP anomaly for the detector to catch.

---

## Privacy Considerations

- **SIN masking:** SINs are validated for format (Luhn check), then immediately replaced with `***-***-XXX` before any storage
- **Row-Level Security:** All database tables have RLS policies — users can only see their own data
- **Storage isolation:** Uploaded files are stored in per-user folders with access policies
- **No permanent retention:** Sessions and all associated data can be deleted by the user
- **OpenAI API:** Document images are sent to OpenAI for processing — in production, this would need a data processing agreement and potentially on-premises inference
- **No CRA integration:** The system never connects to government services

---

## Known Limitations

This is a prototype. A production version would need:

- **Encryption at rest** for all stored documents and extracted data
- **SOC 2 compliance** and security audit
- **On-premises LLM inference** to avoid sending sensitive data to third-party APIs
- **Multi-year support** with configurable tax constants per year
- **Provincial tax calculations** (currently only estimates federal)
- **Self-employment, rental income, and capital gains** analysis
- **CRA Notice of Assessment** integration for accurate RRSP room
- **Rate limiting and queue management** for OpenAI API calls
- **Comprehensive test suite** with mocked LLM responses
- **Accessibility audit** (WCAG 2.1 AA compliance)

---

## Project Structure

```
slip-sense/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── middleware/auth.py       # Supabase JWT verification
│   ├── routers/
│   │   ├── upload.py            # File upload + classification
│   │   ├── analysis.py          # Pipeline trigger (SSE) + report fetch
│   │   └── documents.py         # Document management + findings
│   ├── services/
│   │   ├── classifier.py        # Stage 1: Document classification
│   │   ├── extractor.py         # Stage 2: Data extraction
│   │   ├── analyzer.py          # Stage 3: Hybrid rule engine + LLM
│   │   ├── reporter.py          # Stage 4: Report generation
│   │   └── llm.py               # OpenAI wrapper with structured outputs
│   ├── models/
│   │   ├── schemas.py           # Pydantic models (tax docs, findings, API)
│   │   ├── tables.py            # SQLAlchemy ORM models
│   │   └── database.py          # Async database session factory
│   ├── prompts/
│   │   ├── classification.py    # Document classification prompts
│   │   ├── extraction.py        # Per-doc-type extraction prompts
│   │   └── analysis.py          # LLM analysis instructions
│   ├── utils/
│   │   ├── tax_rules.py         # 2024 Canadian tax constants + rule engine
│   │   ├── confidence.py        # Composable confidence scoring
│   │   └── validators.py        # SIN validation/masking, field checks
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/          # Reusable UI components
│   │   ├── pages/               # Login, Signup, Upload, Results
│   │   ├── hooks/useAnalysis.ts # API + SSE state management
│   │   ├── context/AuthContext   # Supabase auth provider
│   │   ├── lib/                 # Supabase client, API client
│   │   └── types/               # TypeScript interfaces
│   ├── Dockerfile
│   └── nginx.conf
├── supabase/
│   └── migrations/              # SQL schema + RLS policies
├── sample_documents/
│   └── generate_samples.py      # Mock tax document PDF generator
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## License

MIT
