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

---

## 8. Running Locally

### Prerequisites
- **Node.js** (v18+ recommended, v24 verified)
- **Python** (v3.10+ recommended, v3.14 verified)
- **Git** (installed and available in system `PATH`)

---

### Backend Setup & Startup

1. **Navigate to the repository root**:
   ```bash
   cd "c:\Users\Amogh\Desktop\AI Software Failure Investigator"
   ```

2. **Activate the virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     .\backend\.venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     source backend/.venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Start the FastAPI backend server**:
   ```bash
   python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
   ```

Interactive Swagger API docs are available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

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

3. **Start the Vite development server**:
   ```bash
   npm run dev
   ```

4. **Open the Developer Dashboard**:
   Navigate to [http://localhost:5173](http://localhost:5173).

---

## 9. Running Tests

Run the full automated test suite (Phase 1 + Phase 2):
```powershell
.\backend\.venv\Scripts\pytest.exe tests -v
```

Verify frontend TypeScript compilation and production build:
```powershell
npm --prefix frontend run build
```

---

## 10. Next Steps (Future Phases)

- **Phase 3**: Telemetry parser for structured logs and multi-frame exception stack traces.
- **Phase 4**: Root-cause analysis engine correlating logs with code diffs and commits.
- **Phase 5**: Automated remediation suggestions and test generation.
