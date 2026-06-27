# Zealthy Mini-EMR + Patient Portal — Low-Level Design

> Blueprint locked before implementation. Source requirements: `Zealthy Take Home Exercise.md`. Seed data: `data.json`.

---

## 1. Overview

A full-stack application with two surfaces sharing one backend + database:

| Surface | Path | Auth | Purpose |
|---|---|---|---|
| **Mini-EMR** (admin) | `/admin` | None (per spec) | Manage patients, appointments, prescriptions (CRUD) |
| **Patient Portal** | `/` | Login (email + password) | Patient views appointments, refills, notifications |

**Core design principle:** recurring appointments and prescription refills are stored as **rules** (a start + a repeat schedule + an optional end), never as materialized future rows. Concrete occurrences are **computed on demand** by a pure, unit-tested function for any date window ("next 7 days", "next 3 months"). This is the iCalendar RRULE pattern in miniature.

---

## 2. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js (App Router) + TypeScript + Tailwind | Spec requires React/Next; App Router for clean routing; TS for safety |
| Backend | FastAPI + Pydantic | Async Python, auto OpenAPI, Pydantic = authoritative validation |
| ORM / DB | SQLAlchemy + Alembic + **SQLite** | Zero-config, file-based, ideal for a seeded demo; portable to Postgres via connection string |
| Auth | `passlib[bcrypt]` + JWT (httpOnly cookie) | Hashed passwords (still testable with seed creds); stateless sessions |
| FE validation | Zod | Instant inline form errors + safe response parsing |
| Type bridge | `openapi-typescript` against FastAPI `/openapi.json` | Generates TS types from Python models → end-to-end type safety across the language boundary |
| Deploy | Vercel (web) + Railway/Render/Fly (api) | Standard, free tiers |

---

## 3. Monorepo Structure

```
zealthy/
├─ web/                       # Next.js frontend
│  ├─ app/
│  │  ├─ (portal)/            # Patient portal — root "/"
│  │  │  ├─ page.tsx          # Login
│  │  │  ├─ dashboard/        # Summary: 7-day appts + refills + patient info
│  │  │  ├─ appointments/     # Full upcoming schedule (up to 3 months)
│  │  │  └─ prescriptions/    # All prescriptions
│  │  ├─ admin/               # Mini-EMR — "/admin"
│  │  │  ├─ page.tsx          # Patient table (search/sort, at-a-glance counts)
│  │  │  ├─ patients/new/     # New patient form
│  │  │  └─ patients/[id]/    # Drill-down: appts + rx + calendar
│  │  └─ layout.tsx
│  ├─ components/             # Tables, forms, calendar, notification bell, dialogs
│  ├─ lib/
│  │  ├─ api.ts               # Typed fetch client (uses generated types)
│  │  ├─ schemas.ts           # Zod schemas (forms)
│  │  └─ types.gen.ts         # Generated from OpenAPI
│  └─ ...
├─ api/                       # FastAPI backend
│  ├─ app/
│  │  ├─ main.py              # App factory, CORS, router registration
│  │  ├─ db.py                # Engine, session, Base
│  │  ├─ models.py            # SQLAlchemy ORM models
│  │  ├─ schemas.py           # Pydantic request/response models
│  │  ├─ auth.py              # bcrypt + JWT helpers, current-patient dependency
│  │  ├─ recurrence.py        # ⭐ pure occurrence-expansion engine
│  │  ├─ notifications.py     # Notification service (emit on mutation)
│  │  ├─ routers/
│  │  │  ├─ patients.py
│  │  │  ├─ appointments.py
│  │  │  ├─ prescriptions.py
│  │  │  ├─ auth.py
│  │  │  └─ me.py             # Portal: summary, schedule, notifications
│  │  └─ seed.py              # Idempotent seed from ../data.json
│  ├─ tests/
│  │  ├─ test_recurrence.py   # ⭐ unit tests for the engine
│  │  └─ test_api.py
│  ├─ alembic/                # Migrations
│  └─ pyproject.toml
├─ data.json                  # Seed data (provided)
├─ LLD.md                     # This document
└─ README.md                  # Setup, architecture decisions, demo creds
```

---

## 4. Data Model

### Entity-Relationship

```
Patient 1──* Appointment
Patient 1──* Prescription
Patient 1──* Notification
Medication (lookup)    Dosage (lookup)
```

### Tables

**patient**
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| name | text | |
| email | text unique | login identifier |
| password_hash | text | bcrypt |
| dob | date? | basic patient info |
| phone | text? | basic patient info |
| created_at | datetime | |
| deleted_at | datetime? | soft delete |

**appointment**
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| patient_id | int FK | |
| provider | text | free-form (per FAQ) |
| start_at | datetime (tz-aware) | first occurrence; preserve offset from seed (`-07:00`) |
| repeat | enum `NONE\|WEEKLY\|MONTHLY` | `NONE` = one-time |
| until | date? | null = open-ended; "end series" sets this |
| created_at | datetime | |
| deleted_at | datetime? | soft delete |

**prescription**
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| patient_id | int FK | |
| medication | text | validated against medication lookup |
| dosage | text | validated against dosage lookup |
| quantity | int > 0 | |
| refill_on | date | first refill |
| refill_schedule | enum `NONE\|WEEKLY\|MONTHLY` | |
| until | date? | end recurring refills |
| created_at | datetime | |
| deleted_at | datetime? | soft delete |

**notification**
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| patient_id | int FK | |
| type | enum | `APPT_SCHEDULED\|APPT_UPDATED\|APPT_CANCELLED\|RX_PRESCRIBED\|RX_UPDATED` |
| message | text | human-readable |
| related_id | int? | the appt/rx id |
| read_at | datetime? | null = unread |
| created_at | datetime | |

**appointment_exception** — a per-occurrence override of a recurring appointment (iCalendar RECURRENCE-ID).
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| appointment_id | int FK | the series |
| occurrence_start | datetime | the **original** slot this overrides (identity) |
| cancelled | bool | true = drop just this occurrence (EXDATE) |
| provider | text? | null = inherit from series |
| start_at | datetime? | null = keep original time; set = rescheduled |
| created_at | datetime | |

`unique(appointment_id, occurrence_start)`. See §5a for how it's applied.

**prescription_exception** — the refill analogue (per-occurrence override of a recurring refill).
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| prescription_id | int FK | the series |
| occurrence_date | date | the **original** refill date this overrides (identity) |
| cancelled | bool | true = skip just this refill |
| refill_on | date? | null = keep original date; set = rescheduled |
| quantity | int? | null = inherit series quantity |
| created_at | datetime | |

`unique(prescription_id, occurrence_date)`. Drug/dosage stay series-level.

**medication** `{ name PK }` · **dosage** `{ value PK }` — seeded from `data.json` arrays; power the prescription form dropdowns.

**audit_log** (Tier 1) `{ id, entity, entity_id, action(CREATE|UPDATE|DELETE), changes(json), at }` — write on every mutation; demonstrates healthcare "never silently mutate records" instinct.

### Mapping from seed `data.json`
- `users[]` → `patient` (hash `password`); embedded `appointments[]`/`prescriptions[]` → own tables with `patient_id`.
- `appointment.datetime`→`start_at`, `appointment.repeat`→`repeat`.
- `prescription.refill_on`→`refill_on`, `refill_schedule`→`refill_schedule`.
- `medications[]`, `dosages[]` → lookup tables.
- Seed rows have no `until` → stored as open-ended recurrences.

---

## 5. ⭐ Recurrence Engine (`recurrence.py`)

The single most important piece for code-quality screening. **Pure functions, no DB, fully unit-tested.**

```python
def expand_occurrences(
    start: datetime,
    repeat: Repeat,            # NONE | WEEKLY | MONTHLY
    until: date | None,
    window_start: datetime,
    window_end: datetime,
) -> list[datetime]:
    """Return every concrete occurrence within [window_start, window_end]."""
```

**Rules**
- `NONE` → `[start]` if it falls in window, else `[]`.
- `WEEKLY` → `start + n*7 days` for n ≥ 0, while ≤ `until` (if set) and within window.
- `MONTHLY` → add n calendar months; clamp end-of-month (Jan 31 + 1mo → Feb 28/29).
- Always bounded by the window → safe for open-ended series (no infinite loops).
- Timezone-aware throughout; "now" and windows computed in a single reference tz.

**Consumers**
- Portal summary: window = `[now, now+7d]` for appts; refill-due window = `[now, now+7d]`.
- Portal drill-downs: window = `[now, now+3 months]`.
- EMR "next occurrence" column: window = `[now, now+far]`, take first.

**Tests** (`test_recurrence.py`): weekly crossing a month boundary, monthly end-of-month clamp, `until` cutoff, one-time in/out of window, empty results, DST/offset correctness.

### 5a. Single-occurrence editing (exceptions)

The system has **two recurring series** — appointments and prescription refills —
and both support editing *one* occurrence (the iCalendar **RECURRENCE-ID / EXDATE**
problem). We keep each series as one rule and add an **exception** row keyed by the
occurrence's **original** slot (`appointment_exception` / `prescription_exception`).

Because both series are structurally identical, the engine is **generic and shared** —
it only knows how to cancel a slot or move it; each domain layers its own field on top
(provider for appointments, quantity for refills):

```python
def expand_slots(start, repeat, until, overrides, window_start, window_end)
    -> list[Slot]:   # Slot(original, effective, cancelled, overridden)
```

The ORM→engine bridge (`occurrences.py`) builds the overrides, calls `expand_slots`,
then re-joins the domain field. Three operations fall out of one table per series —
**reschedule** (set fields), **cancel** (set `cancelled`), **revert** (delete the row).

- **Window membership is decided by the *original* slot** — a rescheduled occurrence
  still belongs to its original week/month. (The alternative, re-windowing moved
  occurrences, is iCalendar-grade complexity not worth the scope.)
- **Portal** hides cancelled occurrences (read-only) and badges overridden ones
  "Rescheduled"; **EMR** shows cancelled ones struck-through so they can be reverted.
- Matching is by instant (tz-aware datetime equality); refills, being date-based, are
  lifted to midnight UTC to flow through the same datetime engine.
- **Known limitation:** editing the *series'* start/rule shifts the original slots,
  which can orphan existing exceptions (they stop matching). iCalendar has the same
  issue; acceptable for this scope.

**Entry point:** the EMR patient-detail **calendars** (appointments + refills) expand
occurrences; clicking one opens an editor to reschedule / cancel / revert that single
occurrence. Each edit emits a patient notification.

---

## 6. API Contract

Base: `/api`. JSON. Pydantic-validated. Errors return `{ "detail": ... }` with proper HTTP codes.

### Admin / EMR (no auth)
| Method | Path | Body / Notes |
|---|---|---|
| GET | `/patients` | list + `appointmentCount`, `prescriptionCount`, `nextAppointment` |
| POST | `/patients` | `{name,email,password,dob?,phone?}` → hashes password |
| GET | `/patients/{id}` | detail + appts + rx |
| PATCH | `/patients/{id}` | update (CRU; no delete per spec) |
| POST | `/patients/{id}/appointments` | `{provider,startAt,repeat,until?}` → emits notification |
| PATCH | `/appointments/{id}` | update / **end series** (set `until`) → emits notification |
| DELETE | `/appointments/{id}` | soft delete → emits cancel notification |
| GET | `/patients/{id}/schedule?months=` | expanded occurrences (with overrides) for the EMR calendar |
| PUT | `/appointments/{id}/exceptions` | edit one occurrence: `{occurrenceStart, cancelled?, provider?, startAt?}` → notification |
| DELETE | `/appointments/{id}/exceptions?at=` | revert one occurrence to the series |
| POST | `/patients/{id}/prescriptions` | `{medication,dosage,quantity,refillOn,refillSchedule,until?}` → notification |
| PATCH | `/prescriptions/{id}` | update → notification |
| DELETE | `/prescriptions/{id}` | soft delete |
| GET | `/patients/{id}/refill-schedule?months=` | expanded refill occurrences (with overrides) for the EMR calendar |
| PUT | `/prescriptions/{id}/exceptions` | edit one refill: `{occurrenceDate, cancelled?, refillOn?, quantity?}` → notification |
| DELETE | `/prescriptions/{id}/exceptions?at=` | revert one refill to the series |
| GET | `/medications`, `/dosages` | form dropdown options |

### Portal (auth required — JWT cookie)
| Method | Path | Notes |
|---|---|---|
| POST | `/auth/login` | `{email,password}` → sets httpOnly cookie |
| POST | `/auth/logout` | clears cookie |
| GET | `/me` | current patient basic info |
| GET | `/me/summary` | next-7-day appts (expanded), next-7-day refills, patient info |
| GET | `/me/appointments` | full schedule, expanded up to 3 months |
| GET | `/me/prescriptions` | all prescriptions + next refill date |
| GET | `/me/notifications` | list + `unreadCount` |
| PATCH | `/me/notifications/{id}/read` | mark read |
| POST | `/me/notifications/read-all` | mark all read |

**Occurrence expansion happens server-side** — clients receive concrete dated occurrences, never raw rules.

---

## 7. Auth

- **Passwords:** bcrypt via `passlib`. Set in EMR (plaintext in → hashed at rest). Seed creds (`Password123!`) still log in.
- **Sessions:** JWT signed with server secret, stored in **httpOnly, SameSite cookie** (not localStorage → XSS-safer).
- **Guard:** FastAPI dependency `get_current_patient` decodes cookie; portal routers depend on it. `/admin` + EMR routers are open per spec (documented as a deliberate, called-out exception in README).

---

## 8. Notifications (poll-based)

- **Emission:** a single `notifications.emit(patient_id, type, message, related_id)` helper called from the service layer on every appointment/prescription mutation — centralized so no endpoint forgets.
- **"Refill due soon" / "appt soon":** **computed** from the recurrence engine in `/me/summary` (not stored) — consistent with the rule-not-rows principle.
- **Client:** portal fetches `/me/notifications` on load + polls every ~30s; bell shows `unreadCount`; dropdown lists newest-first; mark-as-read / mark-all-read.
- **Scope guardrail:** in-app only (no email/SMS). Respects the "portal is read-only for the patient" constraint — the admin's action generates the notice; the patient only reads it.

---

## 9. Validation Strategy

| Layer | Tool | Role |
|---|---|---|
| Backend | **Pydantic** | Authoritative. Rejects bad payloads, enforces enums, ranges (`quantity>0`), medication/dosage membership |
| Frontend | **Zod** | UX: inline form errors before submit; safe parse of API responses |
| Bridge | **openapi-typescript** | TS types generated from FastAPI OpenAPI → no manual type drift |

Never trust the client; Pydantic is the gate. Zod is for fast feedback.

---

## 10. Frontend Pages

**Mini-EMR (`/admin`)**
- Patient table: name, email, # appts, # rx, next appointment — with **search + sort** (Tier 1).
- New patient form (incl. password).
- Patient detail: editable info; appointment list (CRUD, "end recurrence", calendar view); prescription list (CRUD with medication/dosage dropdowns).
- **Calendar/timeline view** (Tier 2) of expanded appointment occurrences.

**Patient Portal (`/`)**
- Login.
- Dashboard: appts in next 7 days, refills due in next 7 days, patient info, **notification bell**.
- Appointments drill-down: full schedule up to 3 months (list + calendar).
- Prescriptions drill-down: all rx with next refill date.

Every data view has explicit **loading / error / empty** states (Tier 0).

---

## 11. Build Order

1. **Scaffold** monorepo (`web/`, `api/`), FastAPI app, SQLAlchemy models, Alembic init.
2. **Recurrence engine + tests** (TDD — pure, no deps).
3. **Seed script** from `data.json` (idempotent).
4. **Auth** (hash, login, JWT cookie, guard dependency).
5. **EMR API** (patients/appts/rx CRUD + audit + notification emit).
6. **Portal API** (`/me/*` summary, schedule, notifications — using the engine).
7. **OpenAPI → TS types**; typed API client + Zod schemas.
8. **EMR UI** (table, forms, detail, calendar).
9. **Portal UI** (login, dashboard, drill-downs, notification bell).
10. **Polish** (states, validation messages), **README**, **deploy**.

---

## 12. Deferred / Future Work (README "what I'd do next")
- SSE/WebSocket realtime notifications (currently poll).
- Email/SMS notifications.
- Re-anchor occurrence exceptions when a series' rule changes (today they can orphan).
- Real admin authentication + RBAC.

**Now implemented** (post-MVP): CI (typecheck/lint/test); deployed on Render + Vercel;
single-occurrence editing (reschedule / cancel / revert) — see §5a.

---

## 13. Demo Credentials (from seed)
- `mark@some-email-provider.net` / `Password123!`
- `lisa@some-email-provider.net` / `Password123!`
