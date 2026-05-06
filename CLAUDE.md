# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SourceAssist is an AI-powered consultant profile extractor for J2W recruiters. It has two halves that ship together:

- **Backend** (`app.py` + `backend/`) — FastAPI service that handles auth and calls Azure OpenAI to turn raw text/screenshots into structured `ConsultantProfile` JSON.
- **Chrome side-panel extension** (`Source-Assist/`) — Manifest V3 extension (`popup.html` / `popup.js` / `popup.css`) that talks to the backend at `http://localhost:8000` and lets recruiters paste text / drop images, then copies an Excel-shaped row to the clipboard.

The extension and backend share a fixed schema (see `EXCEL_ROWS` in `Source-Assist/popup.js` vs. `ConsultantProfile` in `backend/features/profile_extract/schema.py`) — when you add or rename a profile field, update both sides plus the system prompt in `backend/features/profile_extract/service.py`.

## Common commands

Dependencies are managed with `uv` (see `uv.lock`, `.python-version` pins 3.11+).

```bash
uv sync                       # install / refresh deps from uv.lock
uvicorn app:app --reload      # run backend on :8000 (loads .env automatically)
```

There is no test suite, lint config, or formatter wired up. The Chrome extension has no build step — load `Source-Assist/` unpacked in `chrome://extensions` (it expects the backend on `http://localhost:8000`, which is also baked into `manifest.json`'s `host_permissions`).

## Backend architecture

Layered, feature-sliced FastAPI app. `app.py` only wires middleware, mounts routers, and runs `init_db()` on startup.

- `backend/core/` — cross-cutting config and JWT auth.
  - `config.py` defines `ALLOWED_DOMAINS = {"joulestowatts.com", "joulestowatts.co"}` and the JWT params. The same allow-list is duplicated in `backend/infra/database.py` and in `Source-Assist/popup.js`; keep them in sync.
  - `security.py` issues HS256 JWTs (30-day expiry) and exposes `get_current_user` as a `Depends(...)` for protected routes.
- `backend/infra/` — side-effecting adapters.
  - `database.py` talks to Supabase Postgres via `psycopg2`. `_db_kwargs()` parses `SUPABASE_DB_URL` by hand because Supabase passwords often contain `@`, which breaks naive URL parsing. `init_db()` is idempotent (`CREATE TABLE IF NOT EXISTS`) and creates `users`, `otps`, and `activity_log` on startup. All access goes through the `get_db()` context manager which auto-commits / rolls back.
  - `email.py` sends OTP emails. Prefers `GMAIL_USER` + `GMAIL_APP_PASSWORD` (Gmail SMTP); falls back to generic `SMTP_HOST/PORT/USERNAME/PASSWORD` if Gmail creds are absent.
- `backend/features/<feature>/` — each slice owns `routes.py` (router), `service.py` (logic), and `schemas.py` (Pydantic).
  - `auth/` — domain-restricted OTP-then-password registration, password login, plus `/auth/me` and `/auth/activity/me`. The OTP flow is intentionally three steps: `request-otp` (send), `check-otp` (validate without consuming, drives the UI's "OTP correct ✓" state), `verify-otp` (consume OTP + set password + return JWT). Don't collapse `check-otp` into `verify-otp` — the extension uses both.
  - `profile_extract/` — `/extract` (single, multipart with optional `text` and/or `images[]`) and `/extract/batch` (multiple images). Both call `service.call_azure(...)` which uses `response_format={"type":"json_object"}` and parses into `ConsultantProfile`. Every call writes to `activity_log` regardless of success/failure.

## Things to know before changing code

- **Email domain gate is enforced everywhere.** `auth.service.check_domain` rejects any email outside `ALLOWED_DOMAINS`; the extension also blocks the submit button client-side. New auth-touching endpoints must call `check_domain`.
- **Azure OpenAI is the only model backend.** `AZURE_OPENAI_DEPLOYMENT` defaults to `gpt-4o-mini`. The system prompt in `profile_extract/service.py` hard-codes the allowed values for `education` (`EDUCATION_OPTIONS`) and `experience_range` (`EXPERIENCE_OPTIONS`) — if you change those lists in `schema.py`, the prompt picks them up automatically via f-string interpolation, but the extension's display logic in `popup.js` is independent and may need updating.
- **Mobile-number extraction has explicit rules** in the system prompt (digits-only, strip separators, only the candidate's number — not HR/office). When tweaking extraction quality, edit the prompt in `service.py` rather than post-processing in Python.
- **CORS is wide open** (`allow_origins=["*"]`) because the Chrome extension's origin is `chrome-extension://<id>`, which varies. Don't tighten this without a plan for the extension.
- **`init_db()` runs on every startup** and is the only schema migration mechanism — there is no Alembic. Schema changes go directly into the `CREATE TABLE IF NOT EXISTS` block; for column additions you'll need to add explicit `ALTER TABLE … IF NOT EXISTS` statements alongside.

## Required environment variables

`.env` is loaded by `app.py` before any backend imports. See `README.md` for the full list — `SUPABASE_DB_URL`, `JWT_SECRET`, the `AZURE_OPENAI_*` quartet, and either `GMAIL_USER`/`GMAIL_APP_PASSWORD` or the `SMTP_*` set.
