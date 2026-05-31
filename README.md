# ⚡ Nova AI — Multi-Agent Marketing Audit Engine

Nova AI is a state-of-the-art, 8-agent website marketing audit engine that scans and evaluates websites across 8 core dimensions. Powered by **NVIDIA NIM** (primary provider running Llama-3.3-70b-instruct) and **Google Gemini** (fallback provider running Gemini-1.5-flash) with built-in circuit-breaking resilience.

Nova AI runs all agents in parallel with semaphore-managed concurrency, compiling a comprehensive marketing score (0-100), automated letter grade, executive summary narrative, structured findings list, and prints a white-label **PDF audit report** using ReportLab.

---

## 🚀 Key Features

*   **Concurrency Orchestrator**: Uses async Python task managers with semaphore limits to run all 8 audits in parallel.
*   **Dual LLM Gateway**: Automatic failover, error containment, cost tracking, and circuit breakers.
*   **Structured Outputs**: Custom JSON extraction ensures agent reviews map to standard metrics, findings, and wins.
*   **Google PageSpeed API Integration**: Pulls authentic lab metrics (LCP, CLS, TBT, Performance) or falls back dynamically to response-time heuristics if API keys are absent.
*   **ReportLab PDF Compiler**: Creates standard print-ready executive reports containing Cover Pages, scoring rings, and matrix grids.
*   **Glassmorphic Dark UI**: A React-Vite dashboard featuring custom SVG Score Rings, dynamic Radar charts, active polling, and tabbed audits.

---

## 🧭 Multi-Agent Directory

| Agent | Icon | Weight | Audit Scope |
| :--- | :---: | :---: | :--- |
| **Content & Messaging** | ✍️ | **15%** | Headline clarity, copywriting grade, reading-level match, UVP placement. |
| **Business Strategy** | ♟️ | **13%** | Business model alignment, pricing packages, customer acquisition hooks. |
| **Conversion (CRO)** | 🎯 | **12%** | CTA count, registration/signup friction, trust badges, testimonials. |
| **Technical SEO** | 🔍 | **12%** | Metadata quality, canonical attributes, duplicate H1 tags, image alt texts. |
| **Web Vitals** | ⚡ | **8%** | Page Speed scores, LCP, CLS, and core web vitals parameters. |
| **Competitive Intel** | 🏆 | **8%** | Competitor comparisons, pricing visibility, market differentiation signals. |
| **Accessibility** | ♿ | **6%** | WCAG 2.1 check, ARIA landmarks, keyboard-traversable elements, contrast. |
| **Security & Trust** | 🔒 | **4%** | HTTPS, HSTS, secure cookie flags, security headers (CSP, X-Frame-Options). |

---

## 🛠️ System Architecture

```
                       ┌────────────────────────┐
                       │  Vite React Frontend   │
                       └───────────┬────────────┘
                                   │ (POST /audit)
                                   ▼
                       ┌────────────────────────┐
                       │    FastAPI Backend     │
                       └───────────┬────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼ (Scrapes HTML)              ▼ (Async Pipeline)
          ┌───────────────────┐         ┌────────────────────┐
          │ Async Web Crawler │         │ Agent Orchestrator │
          └───────────────────┘         └─────────┬──────────┘
                                                  │
                               ┌──────────────────┴──────────────────┐
                               ▼ (Semaphore Concurrency = 4)         ▼ (Heuristic Fallback)
                     ┌──────────────────┐                  ┌───────────────────┐
                     │ 7 x LLM Agents   │                  │ Web Vitals Agent  │
                     └─────────┬────────┘                  └─────────┬─────────┘
                               │                                     │
                               ▼ (Failover Gateway)                  ▼ (PageSpeed API)
                     ┌──────────────────┐                  ┌───────────────────┐
                     │ NVIDIA NIM (Llama)│                  │ Google PageSpeed  │
                     └─────────┬────────┘                  └─────────┬─────────┘
                               │ (Fallback)                          │
                               ▼                                     │
                     ┌──────────────────┐                            │
                     │  Google Gemini   │                            │
                     └─────────┬────────┘                            │
                               │                                     │
                               └──────────────────┬──────────────────┘
                                                  │
                                                  ▼
                                     ┌────────────────────────┐
                                     │ Executive Narrative    │
                                     └────────────┬───────────┘
                                                  │
                                     ┌────────────▼───────────┐
                                     │ ReportLab PDF Builder  │
                                     └────────────────────────┘
```

---

## ⚙️ Setup & Installation

### 1. Environment Configuration

Clone the repository and set up your environment variables. Copy the template `.env.example` in the backend folder:

```bash
cd backend
cp ../.env.example .env
```

Edit the `.env` file to add your API credentials:

```ini
# --- NVIDIA NIM (Primary LLM) ---
# Prepend "nvapi-" to your key if not present
NVIDIA_API_KEY= 
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=meta/llama-3.3-70b-instruct

# --- Google Gemini (Fallback LLM) ---
GOOGLE_API_KEY=your-gemini-key

# --- Google PageSpeed Insights (Optional) ---
PAGESPEED_API_KEY=your-pagespeed-key
```

### 2. Backend Setup (FastAPI)

Requires **Python 3.10+**.

```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Launch FastAPI Server
uvicorn app.main:app --reload --port 8000
```
*   **Swagger API Docs**: `http://localhost:8000/docs`
*   **Health Check**: `http://localhost:8000/api/v1/health`

### 3. Frontend Setup (React/Vite)

Requires **Node.js 18+**.

```bash
# Navigate to frontend
cd ../frontend

# Install dependencies
npm install

# Launch Development Server
npm run dev
```
*   **Local Web Dashboard**: `http://localhost:5173/`

---

## 📊 API Reference

### Trigger Audit
*   **Method**: `POST`
*   **Endpoint**: `/api/v1/audit`
*   **Payload**:
    ```json
    { "url": "stripe.com" }
    ```
*   **Response**:
    ```json
    {
      "audit_id": "3b070262-ffcd-4c7f-8b54-4383060eb89f",
      "status": "queued",
      "message": "Audit started. Poll GET /api/v1/audit/{id} for progress."
    }
    ```

### Get Audit Status & Results
*   **Method**: `GET`
*   **Endpoint**: `/api/v1/audit/{audit_id}`
*   **Response Statuses**: `queued`, `crawling`, `analyzing`, `scoring`, `generating_report`, `completed`, `failed`

### Download PDF Report
*   **Method**: `GET`
*   **Endpoint**: `/api/v1/audit/{audit_id}/report`
*   **Response**: File response streaming the compiled white-label PDF.
