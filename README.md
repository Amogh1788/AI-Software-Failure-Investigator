# AI Software Failure Investigator

> **Phase 2 — Repository Ingestion & Codebase Analysis**  
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

> [!IMPORTANT]
> **Phase 2 Scope & Boundary**: Phase 2 provides safe public GitHub repository ingestion, static codebase structure mapping, language detection, and recent Git history extraction. **Phase 2 does not perform AI/ML failure investigation yet.** Machine learning, LLM integration, bug localization, and automated remediation will be implemented in subsequent phases.

---

## 2. Architecture & Data Flow

The platform follows a clean, decoupled three-tier architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                 React 19 Frontend Dashboard                 │
│              (Vite, TypeScript, Tailwind CSS)               │
│   Components: Header, SystemStatus, ProjectsList,           │
│               RepositoryAnalyzer, RepositorySummary,        │
│               RepositoryFiles (Tree), RepositoryHistory     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                       HTTP / REST APIs
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend Server                   │
│             (Uvicorn, Pydantic v2, Python 3.14)             │
│   Endpoints:                                                │
│     • GET  /api/health                                      │
│     • GET  /api/health/db                                   │
│     • GET  /api/projects                                    │
│     • POST /api/repositories/analyze                        │
│     • GET  /api/repositories                                │
│     • GET  /api/repositories/{id}                           │
│     • GET  /api/repositories/{id}/files                     │
│     • GET  /api/repositories/{id}/commits                   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                       Supabase Python SDK
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                  Supabase PostgreSQL Database                │
│   Tables:                                                   │
│     • projects                                              │
│     • repositories                                          │
│     • repository_files                                      │
│     • repository_commits                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Supported Repositories & Ingestion Rules

Phase 2 strictly ingests **public GitHub HTTPS repositories**.

### Accepted Formats
- `https://github.com/owner/repository`
- `https://github.com/owner/repository.git`

### Rejected Formats (HTTP 400)
- SSH URLs (e.g. `git@github.com:owner/repo.git`)
- Non-GitHub hosts (e.g. GitLab, Bitbucket, self-hosted Git)
- Private repositories requiring credentials
- Arbitrary non-HTTPS URLs or file paths (`file://`, `ftp://`)
- Malformed URLs or directory traversal attempts

---

## 4. Security Restrictions & Untrusted Input Policy

Repository contents are treated as **untrusted input**:

1. **Zero Code Execution**: The backend **never** executes scripts, binaries, or build commands from analyzed repositories. The following commands are strictly prohibited and never invoked:
   - `npm install` / `npm run` / `yarn` / `pnpm`
   - `pip install` / `python`
   - `gradle` / `maven` / `make`
   - Shell scripts, batch files, or compiled binaries
2. **Static-Only Analysis**: Codebase inspection is performed strictly through static file tree walks, extension-to-language mapping, and safe text line counting.
3. **Isolated Temporary Directories**: Clones are performed into isolated OS temporary directories (`tempfile.mkdtemp`), scanned, and immediately deleted via `shutil.rmtree` in a guaranteed `finally` block.
4. **Hard Enforced Limits**:
   - **Clone Timeout**: 60-second process termination.
   - **Repository Size Limit**: 100 MB maximum on disk.
   - **File Count Limit**: Maximum 10,000 files inspected per repository.
   - **Individual File Size Limit**: Maximum 1 MB for line counting.
   - **Commit Depth**: Shallow clone (`--depth 50`, `--single-branch`).
5. **No Source Code Stored in Database**: Only file paths, extensions, languages, file sizes, and lines of code are stored in Supabase. Full source code contents and Git diffs are **never** stored in the database.
6. **No Credentials Stored**: `GIT_TERMINAL_PROMPT=0` and `GIT_ASKPASS=""` are enforced during clones to reject private repos without prompting.

---

## 5. Technology Stack

### Frontend
- **React 19** & **TypeScript**
- **Vite 8** (Build tool & development server)
- **Tailwind CSS v4** (Modern dark developer-tool UI)
- **Lucide React** (Clean developer iconography)

### Backend
- **Python 3.14+**
- **FastAPI** (Asynchronous REST API framework)
- **Uvicorn** (ASGI production server)
- **GitPython** (Safe Git object inspection)
- **Pydantic v2** & **pydantic-settings** (Typed validation and settings)
- **Supabase Python SDK** (PostgreSQL database client)
- **Pytest** & **HTTPX** (Automated endpoint test suite)

### Database
- **Supabase PostgreSQL**
- **Row Level Security (RLS)**

---

## 6. Database Schema & Migrations

### Phase 1 Schema: [`data/schema.sql`](data/schema.sql)
Contains the core `projects` table.

### Phase 2 Migration: [`data/phase2_migration.sql`](data/phase2_migration.sql)
Run this migration in your Supabase SQL Editor to add Phase 2 tables:

```sql
-- 1. repositories table
CREATE TABLE IF NOT EXISTS public.repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES public.projects(id) ON DELETE SET NULL,
    github_url TEXT NOT NULL,
    owner TEXT NOT NULL,
    name TEXT NOT NULL,
    default_branch TEXT,
    description TEXT,
    primary_language TEXT,
    total_files INTEGER NOT NULL DEFAULT 0,
    source_files INTEGER NOT NULL DEFAULT 0,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 2. repository_files table
CREATE TABLE IF NOT EXISTS public.repository_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES public.repositories(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    extension TEXT,
    language TEXT,
    file_size INTEGER NOT NULL DEFAULT 0,
    lines_of_code INTEGER NOT NULL DEFAULT 0,
    is_source_file BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 3. repository_commits table
CREATE TABLE IF NOT EXISTS public.repository_commits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES public.repositories(id) ON DELETE CASCADE,
    commit_hash TEXT NOT NULL,
    author_name TEXT,
    author_email TEXT,
    commit_message TEXT,
    committed_at TIMESTAMPTZ,
    files_changed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 4. Indexes
CREATE INDEX IF NOT EXISTS idx_repo_files_repo_id ON public.repository_files(repository_id);
CREATE INDEX IF NOT EXISTS idx_repo_commits_repo_id ON public.repository_commits(repository_id);
CREATE INDEX IF NOT EXISTS idx_repo_commits_hash ON public.repository_commits(commit_hash);
CREATE INDEX IF NOT EXISTS idx_repositories_owner_name ON public.repositories(owner, name);
```

---

## 7. REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Backend service health probe |
| `GET` | `/api/health/db` | Database connectivity probe |
| `GET` | `/api/projects` | List projects from Supabase |
| `POST` | `/api/repositories/analyze` | Ingest and statically analyze a public GitHub repository |
| `GET` | `/api/repositories` | List all analyzed repositories |
| `GET` | `/api/repositories/{id}` | Get repository summary by UUID |
| `GET` | `/api/repositories/{id}/files` | Get repository file metadata (tree) |
| `GET` | `/api/repositories/{id}/commits` | Get repository recent commit history |
| `POST` | `/api/investigations` | Create a new investigation case linked to a repository |
| `GET` | `/api/investigations` | List all investigation cases with evidence counts |
| `GET` | `/api/investigations/{id}` | Retrieve full investigation details, repository, and evidence |
| `PATCH` | `/api/investigations/{id}` | Update title, description, or status ('draft' / 'ready') |
| `DELETE` | `/api/investigations/{id}` | Delete investigation case and cascade delete attached evidence |
| `POST` | `/api/investigations/{id}/evidence` | Attach failure evidence (enforces category size limits) |
| `GET` | `/api/investigations/{id}/evidence` | List all evidence items for an investigation |
| `DELETE` | `/api/investigations/{id}/evidence/{evidence_id}` | Delete an individual evidence item |

---

## 8. Phase 3 — Failure Evidence Collection

> [!IMPORTANT]
> **Phase 3 collects and structures failure evidence. AI/ML investigation is not implemented yet.**

### 8.1 Investigation Cases
An **Investigation Case** represents a single failure incident tied to an analyzed GitHub repository. Cases begin in `draft` status and transition to `ready` once all necessary ground-truth failure artifacts are assembled.

### 8.2 Failure Evidence Categories & Hard Limits
Evidence payloads are strictly validated, sized, and stored passively without execution:

| Evidence Type | Purpose | Size Limit | Typography |
|---|---|---|---|
| `bug_report` | Issue description, steps to reproduce, environment details | 50 KB | Standard |
| `application_log` | Telemetry, stdout/stderr streams, timestamped events | 500 KB | Monospaced |
| `stack_trace` | Exception hierarchies, call paths, stack frames | 200 KB | Monospaced |
| `test_output` | Test runner logs, failed assertions, execution diffs | 200 KB | Monospaced |

Oversized inputs exceeding these byte limits are rejected immediately with HTTP 413 (Content Too Large).

### 8.3 Ready Status Validation
The backend prevents premature analysis by enforcing that an investigation **cannot** transition from `draft` to `ready` status unless **all four evidence categories** (`bug_report`, `application_log`, `stack_trace`, `test_output`) have been attached. Attempting to mark a case `ready` with missing evidence yields HTTP 409 (Conflict).

### 8.4 Security & RLS Model
1. **Private RLS Protection**: Row Level Security is enabled on both `investigations` and `investigation_evidence` with **zero public/anon policies**.
2. **Server-Side Mediation**: All CRUD operations are executed exclusively through the FastAPI backend utilizing `SUPABASE_SERVICE_ROLE_KEY`.
3. **Frontend Isolation**: The React frontend does not bundle the Supabase SDK, holds no Supabase URLs or secrets, and routes all operations through the `/api/investigations` REST API.
4. **Untrusted Content Safety**: Evidence payloads are stored as passive text data and are never parsed as executable scripts or executed in any shell.

---

## 9. Running Locally

### Prerequisites
- **Node.js** (v18+ recommended, v24 verified)
- **Python** (v3.10+ recommended, v3.14 verified)
- **Git** (installed and available in system `PATH`)

---

### Database Migrations (Supabase SQL Editor)
Run the migration scripts in order:
1. `data/schema.sql` (Phase 1 foundation)
2. `data/phase2_migration.sql` (Phase 2 repositories)
3. `data/phase3_migration.sql` (Phase 3 investigations & evidence)

---

### Backend Setup & Startup

1. **Install dependencies**:
   ```bash
   py -m pip install -r backend/requirements.txt
   ```

2. **Configure environment**:
   Ensure `backend/.env` has `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY`.

3. **Start the FastAPI backend server**:
   ```bash
   py -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
   ```

Interactive Swagger API docs are available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

### Frontend Setup & Startup

1. **Install frontend dependencies**:
   ```bash
   npm --prefix frontend install
   ```

2. **Start Vite development server**:
   ```bash
   npm --prefix frontend run dev
   ```

3. **Open Developer Dashboard**:
   Navigate to [http://localhost:5173](http://localhost:5173).

---

## 10. Running Tests

Run the full automated test suite (32 tests covering Phase 1, Phase 2, and Phase 3):
```powershell
py -m pytest tests/ -v
```

Verify frontend TypeScript compilation and production build:
```powershell
npm --prefix frontend run build
```

---

## 11. Next Steps (Future Phases)

- **Phase 4**: Multi-modal root-cause analysis engine correlating logs and stack traces with repository AST diffs.
- **Phase 5**: Automated patch generation, regression testing, and failure verification.
