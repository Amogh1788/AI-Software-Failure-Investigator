# RepoDetective

### AI-Powered Software Failure Investigation

> **Phase 5 — Production Readiness, Security Hardening & MVP Polish (v1.0.0)**
> Explainable, deterministic software failure investigation and root-cause localization platform.

[![Python](https://img.shields.io/badge/Python-3.14+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8+-3178C6.svg)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF.svg)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-v4-38B2AC.svg)](https://tailwindcss.com/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL%20%2B%20Auth-3ECF8E.svg)](https://supabase.com/)
[![Tests](https://img.shields.io/badge/Tests-70%20Backend%20%7C%2012%20Frontend%20Passing-brightgreen.svg)]()

---

## 1. Executive Overview

When complex software fails in staging or production, developers and SREs face a flood of disconnected telemetry: Git commit logs, stack traces, test execution reports, system logs, and user bug tickets. Manually synthesizing these disparate silos to identify the faulty file and regression-introducing commit is error-prone, slow, and expensive.

**RepoDetective** is an enterprise-grade root-cause localization and failure intelligence platform. It ingests multi-modal incident evidence, indexes repository codebases safely without arbitrary code execution, and applies a multi-factor deterministic scoring engine to pinpoint the most suspicious files and identify the causal Git commit.

> [!NOTE]
> **Deterministic Intelligence**: The intelligence engine in v1.0.0 uses **100% deterministic, explainable algorithms**—combining exact frame parsing, term frequency correlation, call hierarchy inspection, and Git commit diff analysis. It intentionally requires **zero external LLMs, zero third-party AI APIs, and zero vector databases**, guaranteeing reproducible, auditable, and sub-second investigation results without token costs or hallucinations.

---

## 2. Completed Project Milestones (Phases 1–5)

| Phase | Milestone | Key Deliverables & Capabilities | Status |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **Foundation** | Decoupled FastAPI backend, React 19 frontend, Supabase database client, environment architecture, health checks. | Complete |
| **Phase 2** | **Repository Ingestion** | Safe HTTPS GitHub shallow cloning (`--depth 50`), static file-tree indexing, language detection, commit history extraction, and resource sandboxing. | Complete |
| **Phase 3** | **Evidence Collection** | Investigation case management, multi-modal evidence ingestion (Stack Traces, Failing Tests, Logs, Bug Reports), aggregate size enforcement (2MB cap), and strict state transitions (`draft` → `ready` → `analyzing` → `completed`). | Complete |
| **Phase 4** | **Investigation Intelligence Engine** | Multi-factor evidence scoring formula, candidate file ranking, line-level suspicion mapping, Git causal-commit correlation (differentiating regression-introducing commits from test-detection commits), and unified investigation reports. | Complete |
| **Phase 5** | **Production Readiness & Hardening** | Supabase Auth (JWT verification), case ownership authorization, IP sliding-window rate limiting, security headers (nosniff, DENY, HSTS), sanitized error handling with `X-Request-ID`, deep readiness probe (`/api/health/ready`), React ErrorBoundary, and zero-anon database lockdown. | Complete |

---

## 3. System Architecture

```
                               ┌───────────────────────────┐
                               │   Client Browser / User   │
                               └─────────────┬─────────────┘
                                             │
                              HTTPS / TLS    │
                 ┌───────────────────────────┴───────────────────────────┐
                 │                                                       │
                 ▼                                                       ▼
     ┌───────────────────────┐                               ┌───────────────────────┐
     │   React 19 Frontend   │                               │    FastAPI Backend    │
     │   • Vite 8 + TS       │                               │   • Python 3.14       │
     │   • Supabase Auth SDK │  Bearer <Supabase-JWT> Token  │   • Security Headers  │
     │   • React ErrorBound  │ ────────────────────────────> │   • Sliding RateLimit │
     │   • 0 Direct DB Query │                               │   • PyJWT Auth Guard  │
     └───────────────────────┘                               │   • Ownership Filter  │
                                                             └───────────┬───────────┘
                                                                         │
                                                 Supabase Service Role   │
                                                                         ▼
                                                             ┌───────────────────────┐
                                                             │   Supabase PostgreSQL │
                                                             │   • Row Level Security│
                                                             │   • Zero Public Anon  │
                                                             │   • Structured Schema │
                                                             └───────────────────────┘
```

---

## 4. Phase 4 Scoring Methodology

The Investigation Intelligence Engine ranks suspicious candidate files by evaluating five weighted evidence dimensions:

$$\text{EvidenceScore} = 0.35 \cdot S + 0.25 \cdot T + 0.20 \cdot L + 0.10 \cdot B + 0.10 \cdot G$$

Where:
- **$S$ (Stack Trace, 35%)**: Direct matching against top-of-stack exception frames, file basenames, and package-to-source directory mapping.
- **$T$ (Failing Tests, 25%)**: Detection of failing test class names, test fixture methods, and inverse naming conventions (e.g. `CheckoutServiceTest` $\rightarrow$ `CheckoutService`).
- **$L$ (Application Logs, 20%)**: Term-frequency matching against warning and error log snippets, component names, and log context.
- **$B$ (Bug Report, 10%)**: Natural keyword matches against user-reported symptoms, reproduction steps, and component tags.
- **$G$ (Git History, 10%)**: Frequency of recent commit activity and churn in the repository's shallow commit history.

### Git Causal-Commit Correlation
The engine inspects Git diffs of recent commits touching candidate files to distinguish between:
1. **Likely regression-introducing commits**: Commits modifying the candidate file, introducing relevant defect terms, and occurring prior to test commits.
2. **Regression-detection/testing commits**: Commits adding or updating automated tests that detected the failure.
3. **Baseline setup commits**: Older foundational commits establishing initial component architecture.

---

## 5. Security Hardening & Untrusted Input Policy

1. **Zero Untrusted Code Execution**: The backend **never** compiles, installs, or executes code from ingested repositories. Scripts (`npm`, `pip`, `make`, shell scripts) are strictly prohibited.
2. **Isolated Ephemeral Sandboxes**: Repositories are cloned into temporary OS directories (`tempfile.mkdtemp`), processed with shallow depth (`--depth 50`), and purged immediately in a guaranteed `finally` block.
3. **Zero-Anon Database Security**: Supabase public `anon` role permissions are completely revoked from all application tables. All server database operations are channeled through the backend using the privileged `service_role` key.
4. **Strict JWT Verification & User Isolation**: Every mutation and read request requires a valid Supabase JWT Bearer token. Backend authorization enforces `authenticated_user.id == investigation.owner_user_id` strictly without exception (no universal bootstrap bypass, no NULL legacy bypass). The database column `owner_user_id` is enforced `NOT NULL` post-migration. In production, `SUPABASE_SERVICE_ROLE_KEY` is mandatory for server operations and silent fallback to publishable `anon` keys is blocked with a controlled configuration error.
5. **Rate Limiting**: In-memory sliding-window limiter prevents abuse:
   - **Standard endpoints**: 120 requests/min.
   - **Heavy endpoints** (`/analyze`): 6 requests/min.
6. **Hard Size Boundaries**:
   - Repository clone size: 100 MB max.
   - Individual evidence item: 500 KB max.
   - Aggregate evidence per case: 2 MB max.
   - Single file inspection: 1 MB max.

---

## 6. API Reference

### Health & Monitoring
- `GET /api/health/live` — Liveness probe (process responsiveness).
- `GET /api/health/ready` — Readiness probe (validates Git CLI and Supabase PostgreSQL connectivity).
- `GET /api/health` — Basic API status.

### Repositories
- `GET /api/repositories` — List indexed repositories for the authenticated user.
- `GET /api/repositories/{id}` — Retrieve repository metadata and summary.
- `GET /api/repositories/{id}/files` — Retrieve indexed file tree.
- `GET /api/repositories/{id}/commits` — Retrieve recent commit history.
- `POST /api/repositories/analyze` — Clone and ingest a public GitHub HTTPS repository.

### Investigations & Evidence
- `GET /api/investigations?repository_id={id}` — List investigations for a repository.
- `POST /api/investigations` — Create a new investigation case (`draft`).
- `GET /api/investigations/{id}` — Retrieve investigation details and attached evidence.
- `PATCH /api/investigations/{id}` — Update investigation metadata or status.
- `DELETE /api/investigations/{id}` — Delete an investigation and cascade its evidence.
- `POST /api/investigations/{id}/evidence` — Upload evidence item (stack trace, test output, log, or bug report).
- `DELETE /api/investigations/{id}/evidence/{evidence_id}` — Remove an evidence item.

### Investigation Intelligence Engine
- `POST /api/investigations/{id}/analyze` — Run the deterministic intelligence engine against candidate files and Git history.
- `GET /api/investigations/{id}/analysis` — Retrieve canonical investigation report and ranking results.

---

## 7. Database Migrations

Apply SQL migrations in your Supabase SQL Editor in the following order:

1. [`data/schema.sql`](data/schema.sql) — Phase 1 projects schema
2. [`data/phase2_migration.sql`](data/phase2_migration.sql) — Phase 2 repository indexing schema
3. [`data/phase3_migration.sql`](data/phase3_migration.sql) — Phase 3 investigation & evidence schema
4. [`data/phase4_migration.sql`](data/phase4_migration.sql) — Phase 4 intelligence analysis persistence
5. [`data/phase5_production_security.sql`](data/phase5_production_security.sql) — Phase 5 ownership authorization & zero-anon lockdown

---

## 8. Local Development Setup

### Prerequisites
- Python 3.12+ (Python 3.14 recommended)
- Node.js 20+ and npm
- Git CLI on system PATH
- Supabase account & project

### Backend Setup
```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and SUPABASE_JWT_SECRET

uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env
# Edit .env with VITE_API_BASE_URL=http://localhost:8000, VITE_SUPABASE_URL, and VITE_SUPABASE_ANON_KEY

npm run dev
```

### Running Test Suites

#### Backend Pytest Suite (64 Tests)
```bash
backend/.venv/Scripts/python.exe -m pytest -v
```

#### Frontend Vitest Suite (12 Tests)
```bash
npm --prefix frontend test -- --run
```

#### Production Build Validation
```bash
npm --prefix frontend run build
```

---

## 9. Production Deployment

For complete production hosting instructions (Vercel, Render, Railway, Docker, Cloudflare), see the [Production Deployment Guide](DEPLOYMENT.md).
