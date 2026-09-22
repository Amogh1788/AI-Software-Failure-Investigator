# AI Software Failure Investigator — Production Deployment Guide

> **Phase 5 Production MVP (v1.0.0)**
> Comprehensive deployment, operations, hardening, and environment reference.

---

## 1. System Architecture Overview

```
                          ┌───────────────────────────┐
                          │   Client Browser / User   │
                          └─────────────┬─────────────┘
                                        │
                         HTTPS / TLS    │
            ┌───────────────────────────┴───────────────────────────┐
            │                                                       │
            ▼                                                       ▼
┌───────────────────────────────┐               ┌───────────────────────────────┐
│     Frontend (Vercel/CDN)     │               │   Backend (Render / Railway)  │
│  React 19 + Vite + Tailwind   │               │   FastAPI + Uvicorn + Python  │
│  • Client-side routing        │               │   • SecurityHeadersMiddleware │
│  • Supabase Auth SDK session  │               │   • RequestLoggingMiddleware  │
│  • Zero direct DB queries     │               │   • RateLimitMiddleware       │
│  • Error boundary & retry     │               │   • PyJWT Token Verification  │
└───────────────┬───────────────┘               └───────────────┬───────────────┘
                │                                               │
                │ Bearer <Supabase-JWT>                         │ Service Role Key
                └───────────────────────────────────────────────┤
                                                                ▼
                                                ┌───────────────────────────────┐
                                                │       Supabase Managed        │
                                                │   • PostgreSQL Database (RLS) │
                                                │   • Supabase GoTrue Auth      │
                                                │   • Zero Public Anon Tables   │
                                                └───────────────────────────────┘
```

The system is decoupled into three isolated layers:
1. **Frontend**: Static single-page application (SPA) built with Vite and React 19. It uses `@supabase/supabase-js` exclusively for authentication and session management. It **never** issues direct queries to the database.
2. **Backend**: Asynchronous REST API service powered by FastAPI and Uvicorn. Validates JWT Bearer tokens issued by Supabase Auth, enforces strict ownership authorization on all cases and evidence, performs rate limiting, applies security headers, and orchestrates the deterministic Phase 4 Investigation Intelligence Engine.
3. **Database**: Supabase PostgreSQL hardened with Row Level Security (RLS). Under Phase 5 production rules, public `anon` access is revoked from all tables. All database interactions occur via the backend using the privileged `service_role` key.

---

## 2. Environment Variables Matrix

### Backend (`backend/.env` or hosting provider environment)

| Variable | Type | Default / Required | Description |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | string | `production` | Environment mode (`production` or `development`). In production, interactive OpenAPI docs (`/docs`) are disabled and strict CORS is enforced. |
| `LOG_LEVEL` | string | `INFO` | Python logging severity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `ENABLE_DOCS` | boolean | `false` | When `false`, `/docs` and `/redoc` return 404. |
| `SUPABASE_URL` | string | **Required** | Your Supabase project URL (`https://<project-ref>.supabase.co`). |
| `SUPABASE_SERVICE_ROLE_KEY` | string | **Required** | Privileged service key for server-to-database communication. Never expose to client. |
| `SUPABASE_JWT_SECRET` | string | **Required** | Supabase project JWT secret (found under *Project Settings -> API -> JWT Secret*). Used for cryptographic signature verification. |
| `CORS_ORIGINS` | string | **Required** | Comma-separated list of allowed frontend origins (e.g. `https://investigator.example.com`). Wildcards (`*`) are strictly blocked in production. |
| `RATE_LIMIT_ENABLED` | boolean | `true` | Enables/disables IP sliding-window rate limiting. |
| `RATE_LIMIT_STANDARD_PER_MINUTE` | int | `120` | Max requests per minute for standard read/write endpoints. |
| `RATE_LIMIT_HEAVY_PER_MINUTE` | int | `6` | Max requests per minute for resource-intensive endpoints (`/repositories/analyze`, `/investigations/{id}/analyze`). |
| `TRUSTED_PROXY_COUNT` | int | `1` | Number of trusted reverse-proxy hops (see Section 6). Set to `1` on Render/Railway/Fly.io, `2` behind Cloudflare. |
| `MAX_EVIDENCE_SIZE_TOTAL_PER_CASE_BYTES` | int | `2097152` | Hard cap (2 MB) on aggregate evidence size per investigation. |
| `BOOTSTRAP_OWNER_USER_ID` | string | `00000000-0000-0000-0000-000000000001` | Migration configuration: Supabase Auth UUID of the real project owner to backfill existing Phase 3/4 investigations. |

### Frontend (`frontend/.env` or hosting provider environment)

| Variable | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `VITE_API_BASE_URL` | string | Yes | Fully-qualified public URL of the backend API (e.g. `https://api.investigator.example.com`). |
| `VITE_SUPABASE_URL` | string | Yes | Your Supabase project URL (`https://<project-ref>.supabase.co`). |
| `VITE_SUPABASE_ANON_KEY` | string | Yes | Supabase public anonymous key (used solely by the browser for user sign-in/up). |

---

## 3. Supabase Database Migration Order

Before deploying the backend or frontend, initialize and migrate your Supabase PostgreSQL database by executing the following migration scripts in order in the **Supabase SQL Editor**:

1. **[`data/schema.sql`](data/schema.sql)**: Foundation schema creating the `projects` table and initial extensions (`uuid-ossp`).
2. **[`data/phase2_migration.sql`](data/phase2_migration.sql)**: Tables and indexes for `repositories`, `repository_files`, and `repository_commits`.
3. **[`data/phase3_migration.sql`](data/phase3_migration.sql)**: Tables for `investigations` and `evidence_items` with initial statuses and evidence categories.
4. **[`data/phase4_migration.sql`](data/phase4_migration.sql)**: Analysis persistence table `investigation_analyses` storing deterministic candidate rankings, scores, and Git correlations.
5. **[`data/phase5_production_security.sql`](data/phase5_production_security.sql)**:
   - Adds `owner_user_id` column to `investigations`.
   - Creates index on `owner_user_id`.
   - Backfills all pre-existing Phase 3/4 investigations to the configured project owner's real Supabase Auth UUID (`BOOTSTRAP_OWNER_USER_ID`).
   - Enforces `ALTER COLUMN owner_user_id SET NOT NULL`.
   - Enables RLS on all tables (`projects`, `repositories`, `repository_files`, `repository_commits`, `investigations`, `evidence_items`, `investigation_analyses`).
   - Revokes all permissions from the public `anon` role.
   - Grants full access exclusively to the backend `service_role` role.

> [!IMPORTANT]
> **Strict Multi-Tenant Authorization**: Backend authorization enforces `authenticated_user.id == investigation.owner_user_id` without exception. There is no universal bootstrap bypass and no NULL legacy bypass. Every investigation belongs to one authenticated user. Server-side database operations in production strictly require `SUPABASE_SERVICE_ROLE_KEY` (silent fallback to `anon` is blocked).

---

## 4. Backend Deployment (Render / Railway / Fly.io / Container)

### Requirements
- **Python**: 3.12, 3.13, or 3.14
- **System Git**: Git CLI (`git`) must be installed on the host system. The backend invokes `git` for shallow cloning and diff extraction.

### Option A: Render (Web Service)
1. Create a new **Web Service** pointing to your repository.
2. **Root Directory**: `backend`
3. **Environment**: `Python 3`
4. **Build Command**:
   ```bash
   pip install --upgrade pip && pip install -r requirements.txt
   ```
5. **Start Command**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
   ```
6. **Environment Variables**: Add all backend variables from Section 2.
7. **Health Check Path**: `/api/health/live`

### Option B: Railway / Dockerfile
If using Docker, ensure Git is installed in the base container:
```dockerfile
FROM python:3.14-slim

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

ENV ENVIRONMENT=production
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 5. Frontend Deployment (Vercel / Netlify / Cloudflare Pages)

### Vercel Deployment
1. Import repository into Vercel.
2. Set **Root Directory** to `frontend`.
3. **Framework Preset**: Vite
4. **Build Command**: `npm run build`
5. **Output Directory**: `dist`
6. **Install Command**: `npm install`
7. Add Frontend Environment Variables (`VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`).
8. Add a rewrite rule for single-page routing if needed (Vercel handles Vite out of the box).

---

## 6. Security, Rate Limiting & Proxy Configuration

### Reverse Proxy & IP Derivation
The backend includes `RateLimitMiddleware` and `RequestLoggingMiddleware` that derive client IPs from the `X-Forwarded-For` header.

> [!WARNING]
> Set `TRUSTED_PROXY_COUNT` accurately to prevent IP spoofing:
> - Direct connection (no proxy): `TRUSTED_PROXY_COUNT=0`
> - Behind one proxy (Render, Railway, Heroku, AWS ALB): `TRUSTED_PROXY_COUNT=1`
> - Behind two proxies (e.g. Cloudflare -> Render): `TRUSTED_PROXY_COUNT=2`

### In-Memory Sliding Window Scalability
The built-in rate limiter is an in-memory sliding window:
- **Single-instance deployments**: Works out of the box without any external services.
- **Horizontal scaling (multi-replica)**: In multi-worker or multi-container clusters, replace the in-memory window with a Redis-backed rate limiter (e.g. `redis-py` or an API gateway like Cloudflare Rate Limiting or Kong) to maintain unified rate counters across nodes.

### Security Headers
The backend automatically injects the following headers on all responses:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload` (enforced when `ENVIRONMENT=production`)
- Obsolete headers like `X-XSS-Protection` are intentionally omitted.

---

## 7. Health & Monitoring Probes

| Endpoint | Probe Type | Purpose | HTTP 200 Condition | Failure Code |
| :--- | :--- | :--- | :--- | :--- |
| `GET /api/health/live` | **Liveness** | Container orchestrator health check. Verifies process is up and responding. | Service is running. | 500 |
| `GET /api/health/ready` | **Readiness** | Ingress traffic gate. Deep dependency verification. | Git CLI is available on PATH AND Supabase PostgreSQL responds to `SELECT 1`. | 503 |

Configure your orchestrator (Kubernetes, Render, AWS ECS) to route traffic only when `/api/health/ready` returns `200 OK`.

---

## 8. Rollback & Disaster Recovery Procedures

1. **Database Rollbacks**:
   - Database migrations in `data/` are designed to be forward-compatible.
   - If rolling back from Phase 5 to Phase 4, the `owner_user_id` column remains nullable and does not break Phase 4 operations.
2. **Frontend Rollbacks**:
   - Vercel and Netlify support instantaneous one-click rollbacks to previous immutable deployments.
3. **Backend Rollbacks**:
   - Redeploy the previous Git commit hash or container image tag. Health probes will ensure traffic does not shift until the previous version is ready.
