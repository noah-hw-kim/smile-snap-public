# Smile Snap — Project Engineering Rules

## Core Principles

1. **Simplest thing first:** Complexity must earn its place. Always ask *"What's the simplest approach that works today, and what problem does anything extra solve right now?"* Avoid over-engineering for this personal project.
2. **Respect constraints and past decisions:** Read `PROJECT_STATE.md` (when present in the workspace) before proposing or making architectural changes — its **"Active Roadmap"** section is the source of truth for what to work on next. Stay within stack, personal budget, AWS Lambda limits, and the diary-generation latency target (p50 < 3s warm). Never silently revert established decisions — flag trade-offs explicitly first.
3. **Small steps, tight scope, review the diff:** Change only what was requested, keep diffs minimal and reviewable, and run/verify each change before moving on. Work one Active Roadmap step at a time.
4. **Verify what's costly to get wrong:** Double-check library versions, AWS/Lambda limits, config syntax, and security (*"How could a malicious user abuse this?"*).
5. **Don't merge what you can't explain:** Keep designs and code transparent so every change is understandable and debuggable.

## Project Overview & Directory Scope

Smile Snap is a personal AI-powered diary generator built on FastAPI, Postgres on Neon (SQLAlchemy 2.0 async + `asyncpg` + Alembic), Firebase Auth, Google Gemini (`google-genai`), and AWS S3 (`boto3`), deployed on AWS Lambda via Mangum. See `PROJECT_STATE.md` "Active Roadmap" for current status.

| Directory | Scope |
|---|---|
| `server/` | Active — primary backend development and upgrade work |
| `frontend/` | Active — minor integration changes only |
| `client_under_development/` | Out of scope — do not modify unless explicitly requested |

## Guardrails (Never Do)

- Never commit `.env`, API keys, service account JSONs, or other secrets.
- Never put AWS access keys (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`) in code, `.env`, or Lambda env vars — use AWS IAM roles on Lambda and an AWS CLI profile (`~/.aws`) for local development.
- Never create, read aloud, or paste real credentials on the user's behalf — the user creates accounts and fills `server/.env` themselves.
- Never modify `client_under_development/` unless explicitly requested.
- Never run destructive database or S3 operations without explicit instruction.
- Never add a new dependency without checking its impact on Lambda package size (250 MB unzipped limit) and Linux wheel compatibility.

## Backend Standards (`server/`)

### Async First
- Prefer native async clients for all I/O inside `async def` functions:
  - `httpx.AsyncClient` instead of `requests`
  - SQLAlchemy 2.0 async + `asyncpg` instead of a sync DB driver
  - `gemini_client.aio` for Gemini API calls
- Wrap unavoidable synchronous SDK calls (`ipinfo`, `boto3` including `.read()` on S3 `StreamingBody`, `firebase_admin.auth` such as `verify_id_token` which can fetch Google public certs over HTTPS) with `asyncio.to_thread(...)`.
- Flag any blocking synchronous call inside an `async def` handler or service.

### Configuration & Validation (Pydantic)
- Define and validate all environment variables through `Settings(BaseSettings)` in `server/config.py`. Never introduce raw `os.getenv()` calls.
- Document every required environment variable in `server/.env.example`.
- Use Pydantic `BaseModel` for request/response contracts and specify `response_model` on JSON-returning routes (omit where not applicable, such as `204 No Content`, redirects, or streaming responses).

### Stateless Cloud Execution (AWS Lambda + Mangum)
- Keep REST handlers strictly stateless:
  - Do not rely on in-memory dictionaries or process-local state across requests or instances.
  - Do not assume container persistence between Lambda invocations.
  - Flag any pattern that breaks under multi-instance or ephemeral execution.
- Use AWS IAM roles for `boto3` and explicit env credentials (`GCP_SERVICE_ACCOUNT_JSON`) for Firebase Admin — do not rely on GCP Application Default Credentials (ADC).

### Lambda Packaging
- Preserve `.dist-info` directories when building Lambda deployment zips (required at runtime by `email-validator` / `importlib.metadata`).
- Respect Lambda's 250 MB unzipped size limit and ensure native wheels (`pydantic_core`, `cryptography`, `grpcio`, `pillow`, `asyncpg`, `greenlet`) match Lambda's Linux OS, architecture, and Python version.

### Separation of Concerns & Error Handling
- Keep route handlers in `server/routers/` lean (request parsing, auth dependencies, response shaping). Place business logic, external API integrations, and database queries in `server/services/`.
- Use FastAPI `Depends()` for authentication, RBAC, and shared resource lookup (`server/dependencies.py`).
- Use Python's `logging` module (`logger.info` / `logger.warning` / `logger.error`) instead of `print()`.
- Log full errors internally and return sanitized error messages to clients — do not leak raw `str(e)` internals in HTTP responses.

### Testing (`server/tests/`)
- Add focused `pytest` unit tests for new or changed service logic.
- Mock all external dependencies (Gemini, ipinfo, OpenWeather, S3, Firebase Auth, the database) — no live network calls or production secrets in unit tests.

## Git Workflow

- Small, focused commits, one logical change each, using Conventional Commit prefixes (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- Never leave a completed roadmap step uncommitted.
- Before committing, check `git diff --cached` for secrets. `PROJECT_STATE.md` is excluded locally via `.git/info/exclude` and is not committed.

## Commands

*(Fill/update remaining entries once verified in Active Roadmap Steps 5–6.)*
- Run locally: `cd server && ../venv/bin/uvicorn main:app --reload` *(verified)*
- Migrations: `cd server && ../venv/bin/alembic upgrade head` *(verified)*
- Tests: `cd server && ../venv/bin/pytest` *(or `cd server && pytest` with `venv` activated — verified)*
- Lint: `ruff check server/` *(not yet configured)*

## Project State & Conventions

- When `PROJECT_STATE.md` is present in the workspace, update its roadmap status and append a Session Log row after completing a milestone or recording a new architectural decision.
- Route and service modules: `snake_case` under `server/routers/` and `server/services/`
- Environment variables: `SCREAMING_SNAKE_CASE`
- CI/CD workflows: `.github/workflows/`

## `REVIEW:` Code Audit Shortcut

When the user prefixes code or a prompt with `REVIEW:`, audit specifically for:
1. Simplicity, correctness, and idiomatic FastAPI/Python patterns
2. Async correctness (blocking calls inside `async def`, missing `await`)
3. Pydantic validation (`BaseSettings`, `BaseModel`, `response_model`)
4. Security and error handling (auth/RBAC gaps, abuse vectors, exposed secrets, leaked `str(e)`)
5. AWS Lambda statelessness and packaging constraints
6. Separation of concerns (`routers/` vs. `services/`, `Depends()`)

Return a prioritized numbered list of issues without rewriting the code unless asked.
