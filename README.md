# AI Software Failure Investigator

> **Phase 1 — Foundation**  
> AI-assisted software failure investigation and root-cause analysis platform.

---

## 1. Project Overview

Modern software ecosystems produce vast volumes of telemetry when incidents occur: Git commits, issue tickets, stack traces, log dumps, and test execution results. Pinpointing the root cause of an incident typically requires developers to manually correlate across these disparate data silos.

**AI Software Failure Investigator** is engineered to automate and accelerate this investigation pipeline. In future phases, it will ingest multi-modal telemetry—combining:
- Git repository history, commit diffs, and code blame
- Bug reports and reproduction steps
- Structured application logs (stdout/stderr)
- Stack traces and exception call hierarchies
- Automated test failure reports

Through machine learning and LLM-powered root-cause analysis, the system will pinpoint regression sources, explain why failures occurred, and suggest remediation steps.

> **Phase 1 Scope**: Establishes the core foundation, repository layout, developer dashboard, FastAPI backend service, and Supabase PostgreSQL data integration. No ML or LLM integration is included in this phase.

---

## 2. Architecture

The platform follows a clean, decoupled three-tier architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                 React 19 Frontend Dashboard                 │
│              (Vite, TypeScript, Tailwind CSS)               │
└──────────────────────────────┬──────────────────────────────┘
                               │
                       HTTP / REST APIs
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend Server                   │
│             (Uvicorn, Pydantic v2, Python 3.14)             │
│   Endpoints: /api/health, /api/health/db, /api/projects     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                       Supabase Python SDK
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                  Supabase PostgreSQL Database                │
│                 (Table: projects, RLS Enabled)              │
└─────────────────────────────────────────────────────────────┘
```

> **Security Guardrail**: The frontend *never* communicates directly with Supabase for data operations and never holds database secrets or service-role keys. All data access is gated through the FastAPI backend.

---

## 3. Technology Stack

### Frontend
- **React 19** & **TypeScript**
- **Vite 8** (Build tool & development server)
- **Tailwind CSS v4** (Modern dark developer-tool UI)
- **Lucide React** (Clean developer iconography)

### Backend
- **Python 3.14+**
- **FastAPI** (High-performance asynchronous REST API framework)
- **Uvicorn** (ASGI production server)
- **Pydantic v2** & **pydantic-settings** (Typed validation and settings)
- **Supabase Python SDK** (PostgreSQL database integration)
- **Pytest** & **HTTPX** (Automated endpoint test suite)

### Database
- **Supabase PostgreSQL**
- **Row Level Security (RLS)**

### Version Control
- **Git** & **GitHub**

---

## 4. Project Structure

```
ai-software-failure-investigator/
│
├── frontend/                     # React + Vite + TypeScript frontend
│   ├── src/
│   │   ├── components/           # UI components
│   │   │   ├── Header.tsx        # Developer tool header & refresh controls
│   │   │   ├── SystemStatus.tsx  # Real-time health diagnostic cards
│   │   │   ├── ProjectsList.tsx  # Project list & empty state
│   │   │   └── FutureInvestigationArea.tsx # Engine pipeline preview
│   │   ├── pages/
│   │   │   └── DashboardPage.tsx # Main dashboard orchestrator
│   │   ├── services/
│   │   │   └── api.ts            # Typed frontend HTTP service layer
│   │   ├── types/
│   │   │   └── index.ts          # TypeScript interfaces & types
│   │   ├── App.tsx               # Root component
│   │   ├── main.tsx              # React DOM entrypoint
│   │   └── index.css             # Tailwind CSS & base theme styles
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── .env.example
│
├── backend/                      # FastAPI Python backend service
│   ├── app/
│   │   ├── api/                  # API routers
│   │   │   ├── health.py         # /api/health and /api/health/db endpoints
│   │   │   └── projects.py       # /api/projects endpoint
│   │   ├── core/                 # Configuration & database client
│   │   │   ├── config.py         # Environment variables & CORS config
│   │   │   └── database.py       # Supabase client & connectivity probe
│   │   ├── models/               # Pydantic data models & schemas
│   │   │   └── project.py        # Project and health response models
│   │   ├── services/             # Business logic layer
│   │   │   └── project_service.py# Supabase data retrieval & health probe
│   │   └── main.py               # FastAPI application entrypoint
│   ├── requirements.txt          # Python dependencies
│   └── .env.example
│
├── tests/                        # Automated backend tests
│   ├── test_health.py            # /api/health and /api/health/db tests
│   └── test_projects.py          # /api/projects test cases
│
├── data/
│   └── schema.sql                # Supabase table definitions & sample seed data
│
├── .env.example                  # Root environment template
├── .gitignore                    # Comprehensive ignore rules
├── README.md                     # Project documentation
└── LICENSE                       # MIT License
```

---

## 5. Supabase Setup Guide

Follow these steps to configure your Supabase PostgreSQL database:

### Step 1: Create a Supabase Project
1. Go to [supabase.com](https://supabase.com) and log in or sign up.
2. Click **New Project**, specify an organization, enter a project name (e.g. `ai-software-failure-investigator`), and set a strong database password.
3. Choose your preferred region and click **Create new project**.

### Step 2: Create the `projects` Table
1. In your Supabase project dashboard, navigate to the **SQL Editor** tab (left sidebar).
2. Open the file [`data/schema.sql`](data/schema.sql) in this repository and copy its entire contents:
   ```sql
   CREATE TABLE IF NOT EXISTS public.projects (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       name TEXT NOT NULL,
       description TEXT,
       created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
   );

   ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

   CREATE POLICY "Allow public read access to projects"
       ON public.projects FOR SELECT USING (true);

   CREATE POLICY "Allow public insert access to projects"
       ON public.projects FOR INSERT WITH CHECK (true);

   -- Seed sample records
   INSERT INTO public.projects (id, name, description, created_at)
   VALUES 
       ('a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d', 'checkout-service-incident-402', 'Investigation into intermittent 504 gateway timeouts in checkout pipeline.', now() - INTERVAL '2 days'),
       ('b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e', 'auth-worker-memory-leak', 'Memory leak in OAuth JWT validation background worker.', now() - INTERVAL '6 hours')
   ON CONFLICT (id) DO NOTHING;
   ```
3. Paste into the SQL Editor and click **Run**.
4. Check the **Table Editor** to confirm the `projects` table and sample rows are visible.

### Step 3: Obtain API Credentials
1. In your Supabase dashboard, navigate to **Project Settings** (gear icon) -> **API**.
2. Copy:
   - **Project URL** (e.g., `https://xyzcompany.supabase.co`)
   - **Project API Keys** -> `anon` / `public` key

### Step 4: Configure Backend Environment
1. Create a `backend/.env` file (copied from `backend/.env.example`):
   ```bash
   cp backend/.env.example backend/.env
   ```
2. Populate the keys:
   ```env
   SUPABASE_URL=https://xyzcompany.supabase.co
   SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   BACKEND_HOST=127.0.0.1
   BACKEND_PORT=8000
   CORS_ORIGINS=http://localhost:5173,http://localhost:3000
   ```

---

## 6. Running Locally

### Prerequisites
- **Node.js** (v18+ recommended, v24 verified)
- **Python** (v3.10+ recommended, v3.14 verified)
- **Git**

---

### Backend Setup & Startup

1. **Navigate to the repository root**:
   ```bash
   cd "c:\Users\Amogh\Desktop\AI Software Failure Investigator"
   ```

2. **Create and activate a virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv backend/.venv
     .\backend\.venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv backend/.venv
     source backend/.venv/bin/activate
     ```

3. **Install backend dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Configure environment variables**:
   Create `backend/.env` as described in [Supabase Setup](#step-4-configure-backend-environment).

5. **Start the FastAPI backend server**:
   ```bash
   python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
   ```

6. **Verify Backend Status**:
   - API Health: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
   - DB Health: [http://127.0.0.1:8000/api/health/db](http://127.0.0.1:8000/api/health/db)
   - Projects: [http://127.0.0.1:8000/api/projects](http://127.0.0.1:8000/api/projects)
   - Interactive Swagger Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### Frontend Setup & Startup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install frontend dependencies**:
   ```bash
   npm install
   ```

3. **Configure environment variables**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Ensure it points to the FastAPI backend:
   ```env
   VITE_API_BASE_URL=http://localhost:8000/api
   ```

4. **Start the Vite development server**:
   ```bash
   npm run dev
   ```

5. **Open the Developer Dashboard**:
   Navigate to [http://localhost:5173](http://localhost:5173).

---

## 7. Running Tests

Automated backend tests verify endpoint schemas, service boundaries, and graceful error handling when Supabase is disconnected.

Run tests using pytest:
```bash
pytest tests/ -v
```

Verify frontend TypeScript typecheck and build:
```bash
cd frontend
npm run build
```

---

## 8. Security Highlights

- **Zero Secrets Committed**: `.gitignore` strictly excludes all `.env`, `.env.*`, keys, and credentials.
- **Backend-Only Database Gateway**: The frontend never has direct access to Supabase or private database credentials.
- **CORS Restricted**: Backend CORS is explicitly parameterized and restricted to known frontend origins.
- **Row Level Security (RLS)**: Included in the SQL schema for PostgreSQL access control.

---

## 9. Next Steps (Future Phases)

- **Phase 2**: Ingestion pipeline for Git repositories (commits, diffs, blame) and issue trackers.
- **Phase 3**: Telemetry parser for structured logs and multi-frame exception stack traces.
- **Phase 4**: Root-cause analysis engine correlating logs with code diffs.
- **Phase 5**: Automated remediation suggestions and test generation.
