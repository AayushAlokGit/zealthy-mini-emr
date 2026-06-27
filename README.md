# Zealthy — Mini-EMR & Patient Portal

[![CI](https://github.com/AayushAlokGit/zealthy-mini-emr/actions/workflows/ci.yml/badge.svg)](https://github.com/AayushAlokGit/zealthy-mini-emr/actions/workflows/ci.yml)

A full-stack mini-EMR and patient portal. Providers manage patients, appointments,
and prescriptions in the EMR; patients log in to a portal to see what's coming up.

- **Patient Portal** at `/` — login, then a dashboard summarising the next 7 days,
  with drill-downs into the full 3-month schedule of appointments and refills.
- **Mini-EMR** at `/admin` (no auth, per spec) — a searchable patient table and
  full CRUD over patients, appointments, and prescriptions.

> **Live demo:** https://zealthy-mini-emr-one.vercel.app · **EMR:** https://zealthy-mini-emr-one.vercel.app/admin
> **Demo login:** `mark@some-email-provider.net` / `Password123!`
>
> _The API is hosted on Render's free tier, which sleeps after ~15 min idle — the first
> request may take ~30–60s to wake. Subsequent requests are fast._

---

## Architecture

A monorepo with a clear front/back split:

```
web/   Next.js 16 (App Router) + TypeScript + Tailwind   → the UI
api/   FastAPI + SQLAlchemy + SQLite                      → the API + data
data.json   seed data (patients, meds, dosages)
LLD.md      the low-level design this was built from
```

| Concern | Choice | Why |
|---|---|---|
| Frontend | Next.js + TypeScript + Tailwind | Required framework; typed end-to-end |
| Data fetching | SWR | Declarative loading/error states + notification polling |
| Forms | react-hook-form + **Zod** | Inline validation; one schema → types + checks |
| Backend | FastAPI + **Pydantic** | Async, auto-OpenAPI, authoritative validation |
| ORM / DB | SQLAlchemy + SQLite | Zero-config; portable to Postgres via one URL |
| Auth | bcrypt + JWT in an httpOnly cookie | Hashed passwords; XSS-safer than localStorage |

**Validation is layered:** Pydantic on the backend is the authoritative gate; Zod on
the frontend mirrors it for instant UX. The backend serves an OpenAPI schema at
`/openapi.json`, so the TS types can be regenerated from it if desired.

### The core idea: recurrence as rules, not rows

Appointments repeat (`weekly`/`monthly`) and refills recur — but a single
`weekly` appointment represents *infinitely many* occurrences. Rather than
materialise future rows, each series is stored once as a **rule**
(`start + cadence + optional end`), and concrete occurrences are **computed on
demand** by a pure function ([`api/app/recurrence.py`](api/app/recurrence.py)):

```python
expand_occurrences(start, repeat, until, window_start, window_end) -> list[datetime]
```

The "next 7 days" summary, the "next 3 months" drill-down, and the EMR's
"next appointment" column are all just different windows over the same function.
It's pure and **unit-tested** (month-boundary rollover, end-of-month clamping,
`until` cutoffs, timezone offsets) — see [`api/tests/test_recurrence.py`](api/tests/test_recurrence.py).
"Ending" a recurring series sets `until` rather than deleting history.

### Other deliberate touches

- **Timezone correctness** — a custom `UTCDateTime` type normalises everything to
  UTC at the DB boundary (SQLite is tz-naive), so "next 7 days" is correct across the
  `-07:00` offsets in the seed data.
- **In-app notifications** — every EMR mutation emits a patient notification; the
  portal polls and shows an unread bell. Admin acts → patient sees it.
- **Soft deletes + audit log** — medical records are never hard-deleted; every
  mutation is recorded. A healthcare-minded default.

---

## Running locally

**Prerequisites:** Python 3.11+ and Node 20+.

### 1. Backend (`api/`)

```bash
cd api
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed                  # create + seed zealthy.db from data.json
uvicorn app.main:app --reload --port 8000
```

API is now at `http://localhost:8000` (docs at `/docs`).

### 2. Frontend (`web/`)

```bash
cd web
npm install
npm run dev                         # http://localhost:3000
```

`web/.env.local` points the frontend at the API:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Tests

```bash
cd api && pytest          # 25 tests: recurrence engine + API flows
cd web && npm run build   # typecheck + production build
```

---

## Demo credentials

| Email | Password |
|---|---|
| `mark@some-email-provider.net` | `Password123!` |
| `lisa@some-email-provider.net` | `Password123!` |

New patients created in the EMR (with a password) can log in to the portal immediately.

---

## Deployment

The two apps deploy independently:

- **`web/`** → Vercel (set `NEXT_PUBLIC_API_URL` to the deployed API URL).
- **`api/`** → any Python host (Render / Railway / Fly). For cross-site cookies set
  `COOKIE_SAMESITE=none`, `COOKIE_SECURE=true`, and `FRONTEND_ORIGINS=<vercel url>`.

See [`api/.env.example`](api/.env.example) for all backend settings.

> SQLite is file-based; on hosts with ephemeral disks it re-seeds from `data.json`
> on deploy. For durable storage, attach a volume or switch `DATABASE_URL` to Postgres.

---

## What I'd do next

Realtime notifications (SSE/WebSocket) instead of polling · edit-this-occurrence vs
edit-series recurrence exceptions · real admin auth + RBAC · Postgres + CI.
