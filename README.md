# ATS CV Scanner

Scan your CV/resume for **ATS (Applicant Tracking System) friendliness**, get an
overall score out of 100, a per-category breakdown, and concrete,
prioritized recommendations on what to fix.

The analysis is **rule-based + lightweight NLP** — fully deterministic and runs
entirely on your own server with **no third-party API keys** required.

## Features

- **Upload** a CV as **PDF, DOCX or TXT** (drag & drop or click).
- **Optional job description** — paste a posting to score how well your CV
  matches its keywords (mirrors how a real ATS ranks you against a role).
- **Overall ATS score (0–100)** with a rating (Poor → Excellent).
- **Per-category breakdown** with sub-scores and explanations:
  - Contact information (email, phone, LinkedIn/portfolio)
  - Standard sections (Experience, Education, Skills, …)
  - Action verbs
  - Quantified achievements (metrics, %, $, scale)
  - ATS-friendly formatting (bullets, tables/columns, special characters)
  - Length
  - Language quality (weak phrasing & buzzwords)
  - Job-description keyword match (when a JD is provided)
- **"Top things to fix"** — the highest-impact issues first.
- **Full recommendation list** with severity (critical / high / medium / low).

## How the score works

Each category produces a 0–100 sub-score from explicit, auditable rules
(`app/scoring.py`). The overall score is the **weighted average** of the
sub-scores. When a job description is supplied, a heavily-weighted
**keyword-match** category is added and the weights are renormalized.

This is intentionally transparent (no black-box model), so results are
reproducible and easy to extend — add verbs/buzzwords/section synonyms in
`app/data.py`.

## Quickstart

Requires **Python 3.12+**.

```bash
# 1. Install dependencies
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Run the app
./run.sh
#   or: uvicorn app.main:app --reload

# 3. Open the UI
open http://localhost:8000
```

## API

The frontend is a thin client over a small JSON API.

### `POST /api/scan`

Multipart form:

| field             | type   | required | description                          |
| ----------------- | ------ | -------- | ------------------------------------ |
| `file`            | file   | yes      | CV file (PDF / DOCX / TXT, ≤ 5 MB)   |
| `job_description` | string | no       | Job posting text for keyword scoring |

```bash
curl -F "file=@resume.pdf" \
     -F "job_description=Python engineer with FastAPI and Kubernetes" \
     http://localhost:8000/api/scan
```

Response (abridged):

```json
{
  "overall_score": 82,
  "rating": "Good",
  "summary": "Solid resume with a good ATS foundation …",
  "categories": [
    { "key": "contact", "label": "Contact information", "score": 100, "status": "good", "...": "..." }
  ],
  "top_fixes": [
    { "category": "quantified", "severity": "high", "message": "Quantify your impact …" }
  ],
  "recommendations": [ "..." ],
  "stats": { "word_count": 612, "bullet_points": 14, "action_verbs": 11, "quantified_bullets": 6 },
  "matched_keywords": ["python", "fastapi"],
  "missing_keywords": ["kubernetes"]
}
```

### `GET /api/health`

Returns `{"status": "ok", "version": "..."}`.

## Development

```bash
pip install -r requirements-dev.txt

# Lint
ruff check .

# Tests
pytest
```

## Project layout

```
app/
  main.py          FastAPI app + routes, serves the static frontend
  parsing.py       PDF / DOCX / TXT text extraction
  scoring.py       Deterministic rule-based + NLP scoring engine
  data.py          Lexicons: action verbs, buzzwords, section synonyms, stopwords
  static/          Frontend (index.html, style.css, app.js)
tests/             Unit tests (scoring) + API smoke tests
```

## Notes & limitations

- Scores are **guidance**, not a guarantee of any specific ATS outcome —
  different ATS products parse and rank differently.
- Image-only / scanned PDFs can't be read (the app will tell you) — and a real
  ATS usually can't read them either, so export a text-based PDF or DOCX.
