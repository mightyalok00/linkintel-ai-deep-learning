# LinkIntel AI — Deep Learning Backlink Intelligence API

A modular FastAPI-only project for identifying and ranking **free backlink opportunities** for websites in any category. No Streamlit UI is included.

## What is implemented

- FastAPI REST API and OpenAPI docs.
- Strict zero-cost eligibility gate: unknown costs are never treated as free.
- Domain normalization and deduplication.
- Explainable heuristic scoring with missing-data warnings.
- Optional semantic relevance model using Sentence Transformers / PyTorch.
- ML spam-risk model interface and reproducible training/evaluation script.
- CSV import for prospects and CSV/JSON exports.
- Asynchronous background job queue (HTTP 202 Accepted) with live Server-Sent Events (SSE) progress streaming.
- Real-time multi-bucket search discovery: Directories, PDF whitepapers, Infographics, and Business citations.
- Google Gemini AI outreach email & strategy generator with automatic fault-tolerant fallback.
- Excel (.xlsx), CSV, and JSON report exports.
- Optional Ollama explanations for local offline environments.
- Link URL reachability and dofollow/noindex backlink checker.
- 28 automated tests covering scoring, free-cost gate, domain security/SSRF, async lifecycle, and routes.

## What is not magic

Perfect accuracy is impossible to guarantee. Authority/spam metrics require real data from a licensed/authorized provider or a dataset you supply. The demo provider is synthetic. The ML model is not pretrained on real backlink labels; train it on a carefully labeled dataset before using its predictions. Semantic similarity is a relevance signal, not a guarantee that a publisher will link to you. No live search-engine discovery adapter is enabled by default.

## Architecture

```text
FastAPI API layer
  ├── Analyze / score / import / export / link-check endpoints
  ├── Pydantic schemas + validation
  └── Service orchestration
       ├── Discovery providers (demo, CSV; extend with authorized API)
       ├── Domain normalization + deduplication
       ├── Cost verifier (verified-free / paid / pending)
       ├── Feature engineering
       ├── Deep semantic relevance (optional Sentence Transformers)
       ├── ML spam-risk classifier (train with labeled real data)
       ├── Explainable ranking engine
       ├── GenAI explanation (optional Ollama)
       └── SQLite persistence
```

## Folder structure

```text
app/
  main.py                 FastAPI endpoints
  config.py               environment settings
  db.py                   SQLite persistence
  schemas.py              request/response models
  security.py             domain normalization and public-host checks
  scoring.py              cost policy + transparent scoring
  service.py              orchestration
  providers/
    base.py                provider interface
    demo.py                synthetic local test provider
    csv_provider.py        user-provided CSV import
    live_search.py         live web search & multi-bucket backlink discovery
  deep_learning/
    relevance.py           batch sentence-embedding semantic similarity
  ml/
    features.py            feature validation/engineering
    spam_model.py          load/predict interface
    train_spam_model.py    training and evaluation script
  genai/
    gemini.py              Google Gemini AI pitch & strategy generation
    ollama.py              optional local Ollama explanations
  static/
    index.html             interactive dashboard UI
    styles.css             modern glassmorphic styling
    app.js                 application logic, filters, and modals
tests/
data/
  labeled_backlinks.csv
models/
  spam_risk.joblib
```

## Quick Start (Docker / Global Cloud)

Run anywhere with Docker Compose in a single command:

```bash
docker compose up -d --build
```

Access the interactive dashboard at `http://localhost:8000/`.

## Windows PowerShell setup

Python 3.12 recommended.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000/` for the web UI, or `http://localhost:8000/docs` for OpenAPI docs.

Run tests:

```powershell
pytest -q
```

## API example

`POST /api/v1/analyze`

```json
{
  "website_url": "https://example.com",
  "category": "software",
  "country": "IN",
  "keywords": ["Python", "developer tools"],
  "provider": "demo",
  "use_deep_learning": false
}
```

Try `provider=demo` first. It returns synthetic test records and an explicit warning.

## CSV import

`POST /api/v1/import/csv` accepts multipart form field `file`. Required column: `domain`. Optional columns include:
`page_url,title,description,category,authority_score,backlink_quality,spam_risk,relevance,placement_fee,submission_fee,mandatory_purchase,paid_plan_required,free_submission_available,terms_verified,evidence_url,link_type`.

Use only data you have permission to use. CSV values are not independently verified merely because they were imported.

## Deep learning

Install optional dependencies:

```powershell
pip install -r requirements-ml.txt
```

Then set `ENABLE_DEEP_LEARNING=true` in `.env`. The model uses a sentence-transformer to compare the site's topic/keywords with prospect page text. First run downloads model weights, so the first launch needs network access. If the model is unavailable, the API reports that semantic relevance was not computed.

## Training a spam-risk model

The training script requires a labeled CSV with numeric features and a binary `is_spam` column (1 = spam, 0 = not spam). This repository does not include a fabricated real-world training dataset.

```powershell
python -m app.ml.train_spam_model --input data/labeled_backlinks.csv --output models/spam_risk.joblib
```

Evaluate on a held-out split; use real labels, check class balance, and review precision, recall, F1, ROC-AUC and calibration. Do not use a model trained on synthetic data to make production claims.

## Free-only policy

An opportunity is `verified_free` only if all are explicitly known:

- placement fee is zero;
- submission fee is zero;
- mandatory purchase is false;
- paid plan is not required;
- free submission is available;
- terms were verified.

Any unknown term stays `pending_verification`. The tool cannot promise that every website has a free opportunity or that every submitted link will be approved.

## Security and production

- This starter does not crawl arbitrary prospect pages automatically.
- The URL checker is for user-submitted URLs and is not a full backlink HTML parser.
- Before public deployment, add auth, quotas, network egress controls blocking private/link-local/metadata IPs on every DNS resolution and redirect, secrets management, provider compliance, migrations, observability, and rate limiting.
- Do not bypass access controls or scrape behind logins.
- Domain Authority is a third-party metric, not a Google ranking factor.
