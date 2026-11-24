# 📝 Smile Snap - AI Diary Generator

Smile Snap is a full-stack AI diary application that transforms user-uploaded screenshots into personal, witty diary entries enriched with optional geolocation and weather context.

[![Watch the Demo](https://img.youtube.com/vi/j5G1zcZqYFk/0.jpg)](https://www.youtube.com/watch?v=j5G1zcZqYFk)

## ✨ Features

* **Screenshot-Based Diary**: Users upload screenshots to AWS S3 and view them via short-lived presigned URLs.
* **AI-Powered Diary Generation**: Uses Google Gemini (`google-genai`) to analyze screenshots alongside optional IP geolocation (IPinfo) and weather (OpenWeatherMap) context.
* **Redis Caching & Distributed Rate Limiting**: Cache-aside for IP geolocation (24h TTL) and weather lookups (20m TTL), plus per-user atomic fixed-window rate limiting (`INCR` + `EXPIRE ... NX`) on AI diary generation—configured to fail open if Redis is unconfigured or unreachable.
* **Secure Authentication & RBAC**: Firebase Authentication ID tokens (JWT) protecting FastAPI routes with `user` and `admin` roles.
* **User & Admin Dashboards**: React + TypeScript SPA where users upload photos, generate/edit/delete diary entries, or delete their account, and admins inspect users in read-only mode or delete accounts.
* **Automated CI/CD**: GitHub Actions runs frontend typecheck/Vitest/Vite build and backend Ruff/pytest checks on every push and PR, and deploys Python 3.14 Lambda packages via AWS IAM OIDC on `main`.

## 🚀 Tech Stack

* **Frontend**: React 19, TypeScript, Vite, React Router, Bootstrap 5, Vitest (deployed on Vercel)
* **Backend**: Python 3.14, FastAPI, Mangum (deployed on AWS Lambda)
* **Database**: PostgreSQL on Neon (SQLAlchemy 2.0 async + `asyncpg` + Alembic)
* **Cache & Rate Limiting**: Redis via `redis.asyncio` (Upstash serverless Redis)
* **File Storage**: AWS S3 (`boto3` via IAM role)
* **Authentication**: Firebase Authentication (`firebase-admin` + Identity Toolkit REST API)
* **AI**: Google Gemini API (`google-genai`)
* **CI/CD**: GitHub Actions + AWS IAM OIDC

## 🌐 Live Link

* **Live Frontend**: <https://smile-snap.vercel.app/>

---

## 🔧 Local Setup Instructions

This repository is organized into `server/` (FastAPI backend) and `frontend/` (React + TypeScript SPA).

### 1. Backend Setup (`server/`)

**Prerequisites:**
* Python 3.14 (matching the AWS Lambda runtime)
* A PostgreSQL database (e.g., Neon)
* An AWS S3 bucket and local AWS CLI credentials (`~/.aws/credentials` via `aws configure`; on Lambda, IAM execution roles are used automatically)
* Firebase project (Web API key + service account JSON) and Google Gemini API key
* *(Optional)* IPinfo token, OpenWeatherMap API key, and Redis URL (e.g., Upstash `rediss://...` or local Docker `redis://localhost:6379`)

**Steps:**
1. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. **Install dependencies**:
   ```bash
   pip install -r server/requirements.txt -r server/requirements-dev.txt
   ```
3. **Configure environment variables**:
   * Copy `server/.env.example` to `server/.env` and fill in your values. **Never commit `server/.env` or service account keys.**
   * See `server/.env.example` for `DATABASE_URL`, `S3_BUCKET_NAME`, `FIREBASE_WEB_API_KEY`, `GCP_SERVICE_ACCOUNT_JSON`, `GEMINI_API_KEY`, and optional `IPINFO_API_TOKEN`, `WEATHER_API_KEY`, `REDIS_URL`, `GENERATE_RATE_LIMIT`, and `GENERATE_RATE_WINDOW_SECONDS`.
4. **Run database migrations**:
   ```bash
   cd server && alembic upgrade head
   ```
5. **Run the API server**:
   ```bash
   cd server && uvicorn main:app --reload
   ```
   The API will be available at `http://127.0.0.1:8000` (interactive docs at `/docs`).
6. **Run backend checks**:
   ```bash
   cd server && ruff check . && pytest
   ```

### 2. Frontend Setup (`frontend/`)

**Prerequisites:**
* Node.js 24+ and npm

**Steps:**
1. **Install dependencies**:
   ```bash
   cd frontend && npm ci
   ```
2. **Configure environment variables**:
   * Copy `frontend/.env.example` to `frontend/.env.local` and set `VITE_API_BASE_URL` (defaults to `http://localhost:8000` if omitted).
3. **Start the dev server**:
   ```bash
   cd frontend && npm run dev
   ```
   Open `http://localhost:5173`.
4. **Run frontend checks**:
   ```bash
   cd frontend && npm run typecheck && npm test && npm run build
   ```

---

## ⚙️ CI/CD Pipeline

Defined in [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml):
* **Frontend CI**: Runs `npm ci`, `npm run typecheck`, `npm test`, and `npm run build` on pushes and PRs targeting `main`.
* **Backend CI**: Installs `server/requirements.txt` + `server/requirements-dev.txt` on Python 3.14 and runs `ruff check .` and mocked `pytest` unit tests.
* **Deploy Backend to AWS Lambda**: On pushes to `main` after both CI jobs pass, builds a Python 3.14 `x86_64` deployment package, authenticates to AWS via GitHub OIDC (`AWS_ROLE_ARN`), and updates the Lambda function (`LAMBDA_FUNCTION_NAME` in `AWS_REGION`).

---

## 📡 Key API Endpoints

Protected endpoints require `Authorization: Bearer <token>` obtained from `POST /token`.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/token` | Sign in with email/password (`form-data`) and return a Firebase ID token + user profile |
| `POST` | `/users/` | Register a new user in Firebase Auth and Postgres (`role: "user"`) |
| `POST` | `/screenshots/upload` | Upload a screenshot image (`multipart/form-data`) to S3 |
| `POST` | `/screenshots/{photoId}/generate` | Generate an AI diary entry from a photo (rate-limited via Redis when configured) |
| `GET` | `/users/{userId}/entries` | List diary entries for a user (owner or admin) |
| `PUT` | `/users/{userId}/entries/{entryId}` | Edit diary entry content (switches `mode` to `"manual"`) |
| `DELETE` | `/users/{userId}/entries/{entryId}` | Delete a diary entry (owner or admin) |
| `GET` | `/admin/users` | List all non-admin users (admin only) |
