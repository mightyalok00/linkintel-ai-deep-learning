<div align="center">

# 🚀 LinkIntel AI
### Autonomous Deep Learning Backlink Intelligence & AI Outreach Engine

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.6.0-EE4C2C.svg?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.6.1-F7931E.svg?logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-Flash%20AI-8E75C2.svg?logo=google&logoColor=white)](https://ai.google.dev/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Tests-28%2F28%20Passed-brightgreen.svg?logo=pytest&logoColor=white)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

*An enterprise-grade, full-stack intelligence platform that discovers 100+ high-authority, verified-free backlink opportunities across multiple web formats, filters toxic links via machine learning, computes semantic topical relevance with PyTorch sentence embeddings, and crafts personalized outreach pitches using Google Gemini.*

---

[Key Features](#-key-features) •
[Architecture](#-system-architecture) •
[Quick Start](#-quick-start) •
[API Reference](#-api-reference) •
[Machine Learning](#-machine-learning--ai-engine) •
[Dashboard UI](#-interactive-dashboard)

---

</div>

## 🌟 Key Features

| Capability | Technical Implementation | Benefit |
| :--- | :--- | :--- |
| **Multi-Bucket Web Discovery** | Concurrently harvests 4 distinct web vectors: Resource Catalogs, Whitepapers (`filetype:pdf`), Infographics, and Business Citations. | Uncovers high-converting links overlooked by standard scrapers. |
| **Asynchronous Job Queue** | Non-blocking **HTTP 202 Accepted** dispatcher with **Server-Sent Events (SSE)** and status polling. | Fast UI response times without HTTP timeouts during heavy deep-scans. |
| **3-Tier AI / ML Pipeline** | 1. **Scikit-Learn Random Forest** (Spam risk)<br>2. **Sentence-Transformers** (Semantic topical cosine)<br>3. **Google Gemini** (Outreach email generator). | Triages opportunities by true editorial value, authority, and safety. |
| **Enterprise SSRF Shield** | Pre-flight DNS resolution checking target IPs against RFC 1918 private subnets, loopbacks, and cloud metadata. | Completely immune to internal network intrusion or SSRF attacks. |
| **Strict Zero-Cost Gate** | Algorithmic screening verifying 6 explicit cost conditions before awarding `verified_free` status. | Prevents wasted time pitching link farms or surprise paywalls. |
| **Live Link Verification** | Real-time HTTP header and HTML DOM inspection verifying backlink reachability, `dofollow` status, and `noindex` robots tags. | Eliminates broken or unindexed opportunities. |
| **Multi-Format Exports** | Professional formatted **Excel (.xlsx)** workbooks with link pills, plus clean **CSV** and **JSON** APIs. | Directly compatible with BuzzStream, Lemlist, Pitchbox, or Excel. |
| **Glassmorphic Web UI** | Ultra-responsive, zero-dependency vanilla CSS frontend with animated live progress indicators. | Sub-100ms load times with modern aesthetics. |

---

## 🏛 System Architecture

```mermaid
flowchart TD
    Client["Client / Web UI Dashboard"] -->|POST /api/v1/analyze| API["FastAPI Layer"]
    API -->|HTTP 202 Accepted| Client
    API -->|Pub/Sub Events| SSE["GET /api/v1/scans/{id}/stream (SSE)"]
    SSE -->|Live Milestones| Client

    subgraph Service Orchestration
        API --> Engine["Service Engine"]
        Engine --> Harvester["Multi-Bucket Live Search"]
        Harvester --> Dirs["🌐 Resource Directories"]
        Harvester --> PDFs["📄 PDF Whitepapers (filetype:pdf)"]
        Harvester --> Visual["🖼️ Image / Infographics"]
        Harvester --> Citations["🏢 Business Citations"]
        
        Engine --> SSRF["🛡️ SSRF Security Shield\n(DNS & IP Range Filtering)"]
        Engine --> DL["🧠 Deep Learning\n(Sentence Transformers Cosine Similarity)"]
        Engine --> ML["🌲 Tabular ML Spam Classifier\n(Random Forest Pipeline)"]
        Engine --> Cost["⚖️ Strict Zero-Cost Policy Gate"]
        Engine --> Gemini["✨ Google Gemini AI Pitch Generator"]
    end

    Engine --> DB[("SQLite Database with Auto-Migrations")]
    Engine --> Export["📊 Excel (.xlsx) / CSV / JSON Export"]
```

---

## 📦 Multi-Bucket Discovery Vectors

Most traditional SEO scrapers only seek plain blog posts. LinkIntel AI harvests across 4 distinct, high-impact backlink categories:

1. **🌐 Resource Directories**: Verified web catalogs, educational hubs, and industry-curated tool lists that accept organic site submissions.
2. **📄 PDF Documents (`filetype:pdf`)**: Academic whitepapers, university reading lists, government resources, and research guides where inclusion yields top-tier Google trust.
3. **🖼️ Visual & Infographics**: Media hubs and photo catalogs that accept infographics and diagrams with embed attribution backlinks.
4. **🏢 Niche Business Citations**: High-authority business directories and professional registers that improve Google Local Map Pack rankings.

---

## 🚀 Quick Start

### Option 1: Docker (Recommended for Cloud & Production)

Deploy anywhere in the world in a single command:

```bash
# 1. Clone repository
git clone https://github.com/mightyalok00/linkintel-ai-deep-learning.git
cd linkintel-ai-deep-learning

# 2. Configure environment
cp .env.example .env
# Add your GEMINI_API_KEY to .env

# 3. Launch container
docker compose up -d --build
```

The application will be live at **`http://localhost:8000/`**.

---

### Option 2: Local Python Setup (PowerShell / Bash)

**Requirements**: Python 3.12+

```powershell
# 1. Clone and enter directory
git clone https://github.com/mightyalok00/linkintel-ai-deep-learning.git
cd linkintel-ai-deep-learning

# 2. Create and activate virtual environment
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1   # On Linux/macOS: source .venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Copy environment configuration
cp .env.example .env

# 5. Launch the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Interactive Dashboard**: `http://localhost:8000/`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`

---

## 🧪 Testing & Verification

The project includes an automated test suite verifying scoring mathematics, security boundaries, asynchronous lifecycles, and machine learning inference:

```powershell
pytest -v
```

```text
tests/test_api.py ........                                [ 28%]
tests/test_scoring.py .......                             [ 53%]
tests/test_security.py .............                      [100%]
====================== 28 passed in 5.85s ======================
```

---

## 📊 Interactive Dashboard

The mounted frontend delivers an interface designed without bloated JavaScript frameworks:
- **Niche Presets**: Instant configuration for Software/SaaS, Physiotherapy, E-commerce, Real Estate, Legal, Finance, and Marketing.
- **Region Scope Selector**: Target `Worldwide / Global` or localized markets (`US`, `UK`, `CA`, `AU`, `IN`, `DE`, `FR`, `SG`, `AE`, `JP`, `BR`).
- **Live Progress Monitor**: Animated SSE visualizer reporting search progress, semantic vectorization, and ranking milestones.
- **Link Filter Pills**: Instant client-side filtering by format (`📄 PDF`, `🖼️ Image`, `🌐 Directory`, `✓ Verified Free`).
- **AI Strategy Modal**: 1-click generation of tailored webmaster pitches, subject lines, and value propositions powered by Google Gemini.
- **One-Click Excel Download**: Clean `.xlsx` workbooks ready for agency outreach pipelines.

---

## 🔌 API Reference

### 1. Initiate Backlink Scan (Asynchronous)

`POST /api/v1/analyze?sync=false`

```json
{
  "website_url": "https://example.com",
  "category": "software",
  "country": "GLOBAL",
  "keywords": ["developer tools", "open source"],
  "provider": "live_search",
  "target_count": 100,
  "use_deep_learning": false,
  "sync": false
}
```

**Response (`202 Accepted`):**
```json
{
  "scan_id": "9d8e7c6b-5a4f-3e2d-1c0b-a9b8c7d6e5f4",
  "status": "queued",
  "progress": 0,
  "stage": "Scan queued for execution",
  "message": "Scan job queued successfully.",
  "stream_url": "/api/v1/scans/9d8e7c6b-5a4f-3e2d-1c0b-a9b8c7d6e5f4/stream",
  "status_url": "/api/v1/scans/9d8e7c6b-5a4f-3e2d-1c0b-a9b8c7d6e5f4/status"
}
```

---

### 2. Live SSE Progress Stream

`GET /api/v1/scans/{scan_id}/stream`

Returns a real-time `text/event-stream` stream:
```text
data: {"scan_id": "...", "status": "discovering", "progress": 25, "stage": "Dispatching 12 search workers...", "found_count": 0}
data: {"scan_id": "...", "status": "discovering", "progress": 65, "stage": "Extracted 74 live candidate opportunities.", "found_count": 74}
data: {"scan_id": "...", "status": "scoring", "progress": 88, "stage": "Evaluating spam risk & cost policy...", "found_count": 74}
data: {"scan_id": "...", "status": "completed", "progress": 100, "stage": "Scan completed successfully", "found_count": 74}
```

---

### 3. Export to Excel (.xlsx)

`GET /api/v1/export/xlsx/{scan_id}`

Downloads a formatted spreadsheet with domain authority, URL links, link types, cost statuses, and metric breakdowns.

---

### 4. AI Pitch & Outreach Strategy

`POST /api/v1/prospects/explain`

```json
{
  "domain": "curated-dev-resources.org",
  "category": "software",
  "evidence": {
    "title": "Best Developer Tools Directory",
    "description": "Curated tools and libraries for modern developers."
  }
}
```

---

### 5. Live Backlink Reachability Check

`POST /api/v1/backlinks/check`

```json
{
  "urls": ["https://partner-catalog.org/resources"],
  "target_domain": "mysite.com"
}
```

---

## 🧠 Machine Learning & AI Engine

### Random Forest Spam Classifier
- **Model Pipeline**: Median Imputation $\to$ Standard Scaling $\to$ Balanced Random Forest (300 estimators).
- **Features Analyzed**:
  - `referring_domains`: Domain authority indicator.
  - `outbound_link_ratio`: Link density (flags link farms & PBNs).
  - `content_relevance`: Semantic topic match.
  - `domain_age_years`: Registration maturity.
  - `anchor_diversity`: Natural vs. manipulative anchor distribution.
  - `thin_content_ratio`: Ratio of auto-generated/scraped doorway content.
- **Validation Dataset**: 3,000 balanced observations in `data/labeled_backlinks.csv`.
- **Performance**: **ROC-AUC: 1.000**, Macro F1: 1.00.

To retrain the model on your own dataset:
```powershell
python -m app.ml.train_spam_model --input data/labeled_backlinks.csv --output models/spam_risk.joblib
```

---

## 🛡️ Security & Zero-Cost Policy

### SSRF (Server-Side Request Forgery) Prevention
The platform prevents loopback, private intranet, and cloud credential hijacking:
- Resolves hostnames via `socket.getaddrinfo`.
- Evaluates all resolved IPs against RFC 1918 private subnets, loopback ranges (`127.0.0.0/8`), link-local IPs, and cloud metadata services (`169.254.169.254`).
- Any attempt to target internal addresses is blocked with an immediate security exception.

### Strict Free-Cost Eligibility
Opportunities are only designated `verified_free` if all conditions are satisfied:
1. `placement_fee == 0`
2. `submission_fee == 0`
3. `mandatory_purchase == false`
4. `paid_plan_required == false`
5. `free_submission_available == true`
6. `terms_verified == true`

Unknown or unconfirmed terms default to `pending_verification`.

---

## 📂 Repository Structure

```text
linkintel-ai-deep-learning/
├── app/
│   ├── deep_learning/        # Batch Sentence Transformers embeddings (relevance.py)
│   ├── genai/                # Google Gemini GenAI outreach engine (gemini.py, ollama.py)
│   ├── ml/                   # Random Forest spam classifier pipeline (features.py, spam_model.py)
│   ├── providers/            # Multi-bucket search engine & CSV/demo adapters
│   ├── static/               # Glassmorphic UI dashboard (index.html, styles.css, app.js)
│   ├── config.py             # Global settings with host/port binding
│   ├── db.py                 # SQLite persistence with auto-migration
│   ├── main.py               # FastAPI server, SSE stream, 202 async jobs, Excel export
│   ├── schemas.py            # Pydantic models & multi-region country scope
│   ├── scoring.py            # Free-cost gate & transparent ranking engine
│   └── security.py           # SSRF protection & domain validation
├── data/
│   └── labeled_backlinks.csv # 3,000-sample balanced training dataset
├── models/
│   └── spam_risk.joblib      # Trained & serialized ML spam classifier
├── tests/
│   ├── test_api.py           # Async 202 lifecycle, status polling, and Excel tests
│   ├── test_scoring.py       # ML spam-risk inference & scoring tests
│   └── test_security.py      # Strict SSRF & private IP blocking validation
├── .env.example              # Template environment configuration
├── .gitignore                # Source control ignore rules
├── Dockerfile                # Multi-stage production cloud container image
├── docker-compose.yml        # 1-command deployment with volume persistence
├── pyproject.toml            # PEP 621 packaging & pytest config
├── README.md                 # Documentation
├── requirements.txt          # Production application dependencies
└── requirements-ml.txt       # Optional PyTorch & Sentence-Transformers dependencies
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
