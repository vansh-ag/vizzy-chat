<<<<<<< HEAD
# Vizzy Chat — Backend API

Vizzy Chat is a conversational image-generation application. This repository contains the **FastAPI backend** (Phase 1 — foundation).

---

## Phase 1 Scope

Phase 1 implements the application foundation only. **No AI functionality is included.**

| Component | Status |
|-----------|--------|
| FastAPI application setup | ✅ |
| Configuration management (Pydantic Settings) | ✅ |
| Structured logging | ✅ |
| Global exception handling | ✅ |
| Supabase client setup (anon + service-role) | ✅ |
| JWT / access-token verification | ✅ |
| `GET /api/v1/health` | ✅ |
| `GET /api/v1/users/me` (auth required) | ✅ |
| Supabase Storage service foundation | ✅ |
| Image file validation utilities | ✅ |
| Unit + integration tests | ✅ |
| CORS configuration | ✅ |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Framework | FastAPI |
| Schemas | Pydantic v2 |
| Config | Pydantic Settings |
| Auth / DB / Storage | Supabase |
| HTTP client | httpx |
| Image validation | Pillow |
| Package manager | uv |
| ASGI server | Uvicorn |
| Tests | pytest + pytest-asyncio |
| Linting | Ruff |
| Type checking | mypy |

---

## Folder Structure

```
backend/
├── README.md
├── pyproject.toml
├── uv.lock
├── .env                        ← local secrets (never committed)
├── .env.example                ← template for secrets
├── .gitignore
├── Dockerfile
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_config.py
│   │   └── test_security.py
│   └── integration/
│       ├── test_health.py
│       ├── test_auth.py
│       └── test_storage.py
│
└── app/
    ├── __init__.py
    ├── main.py
    ├── core/
    │   ├── config.py           ← Pydantic Settings
    │   ├── logging.py          ← logging setup
    │   ├── security.py         ← JWT verification
    │   ├── exceptions.py       ← custom exceptions + handlers
    │   └── constants.py        ← app-level constants
    ├── api/
    │   ├── dependencies.py     ← get_current_user()
    │   └── routes/
    │       ├── health.py       ← GET /api/v1/health
    │       └── users.py        ← GET /api/v1/users/me
    ├── schemas/
    │   └── common.py           ← HealthResponse, UserResponse, ErrorResponse
    ├── db/
    │   ├── supabase.py         ← Supabase client factory
    │   └── repositories/
    │       └── user.py         ← minimal UserRepository
    ├── services/
    │   └── storage_service.py  ← Supabase Storage abstraction
    └── utils/
        └── file_validation.py  ← image upload validation
```

---

## Local Setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) installed globally
- A Supabase project

### 1. Clone and install

```bash
cd backend
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in your Supabase credentials
```

### 3. Run the development server

```bash
uv run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

---

## uv Commands

| Action | Command |
|--------|---------|
| Install dependencies | `uv sync` |
| Run dev server | `uv run uvicorn app.main:app --reload` |
| Run tests | `uv run pytest` |
| Run tests (verbose) | `uv run pytest -v` |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` |
| Type check | `uv run mypy app` |
| Add a dependency | `uv add <package>` |
| Add a dev dependency | `uv add --dev <package>` |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the required values.

| Variable | Required | Description |
|----------|----------|-------------|
| `APP_NAME` | No | Application name (default: `vizzy-api`) |
| `APP_ENV` | No | Environment name (default: `development`) |
| `DEBUG` | No | Enable debug logging (default: `false`) |
| `CORS_ORIGINS` | No | Comma-separated allowed origins (default: `http://localhost:3000`) |
| `SUPABASE_URL` | **Yes** | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | **Yes** | Supabase anonymous/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | **Yes** | Supabase service-role key (server-only, never exposed) |
| `INPUT_IMAGE_BUCKET` | No | Storage bucket for user uploads (default: `input-images`) |
| `GENERATED_IMAGE_BUCKET` | No | Storage bucket for outputs (default: `generated-images`) |
| `MAX_UPLOAD_SIZE_MB` | No | Max upload size in MB (default: `10`) |
| `MAX_INPUT_IMAGES` | No | Max images per request (default: `5`) |

> The following variables are declared in `.env.example` for future phases but are **not used in Phase 1**:
> `GROQ_API_KEY`, `GROQ_MODEL`, `HF_TOKEN`, `IMAGE_PROVIDER`, `IMAGE_GENERATION_MODEL`, `IMAGE_EDIT_MODEL`

---

## Supabase Setup

### Project credentials

You need three values from your Supabase project dashboard (`Settings → API`):

1. **Project URL** → `SUPABASE_URL`
2. **anon / public key** → `SUPABASE_ANON_KEY`
3. **service_role key** → `SUPABASE_SERVICE_ROLE_KEY`

### Storage buckets

Create two **private** storage buckets in your Supabase dashboard (`Storage → New bucket`):

| Bucket name | Visibility |
|-------------|-----------|
| `input-images` | 🔒 Private |
| `generated-images` | 🔒 Private |

Both buckets must remain **private**. Access is always through server-generated signed URLs.

### Authentication

Supabase Auth handles all user lifecycle management:

- Sign-up
- Login / logout
- Password reset
- Email verification
- Session management

The **backend does NOT implement custom login/signup**. It only verifies access tokens.

### Expected `profiles` table (for future phases)

```sql
CREATE TABLE profiles (
    id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email        TEXT,
    display_name TEXT,
    avatar_url   TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
```

---

## How to Run the Backend

**Development:**

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Production (via Docker):**

```bash
docker build -t vizzy-api .
docker run -p 8000:8000 --env-file .env vizzy-api
```

---

## How to Run Tests

```bash
# All tests
uv run pytest

# With verbose output
uv run pytest -v

# Specific test file
uv run pytest tests/unit/test_config.py -v

# Specific test class
uv run pytest tests/integration/test_auth.py::TestAuthEndpoint -v
```

---

## API Endpoints

### Interactive Documentation

| URL | Description |
|-----|-------------|
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/redoc` | ReDoc |

### Phase 1 Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/health` | ❌ None | Service health check |
| `GET` | `/api/v1/users/me` | ✅ Required | Current authenticated user |

#### `GET /api/v1/health`

```json
{
  "status": "ok",
  "service": "vizzy-api",
  "environment": "development"
}
```

#### `GET /api/v1/users/me`

Request:
```
Authorization: Bearer <supabase_access_token>
```

Response:
```json
{
  "id": "00000000-0000-0000-0000-000000000001",
  "email": "user@example.com",
  "role": "authenticated"
}
```

#### Error responses

All errors follow this envelope:

```json
{
  "error": {
    "code": "AUTHENTICATION_ERROR",
    "message": "Authentication required."
  }
}
```

---

## Authentication Flow

```
Frontend                     FastAPI Backend              Supabase Auth
   │                               │                           │
   │  POST /auth/v1/token          │                           │
   │──────────────────────────────────────────────────────────►│
   │                               │                           │
   │◄──────────────────────────────────────────────────────────│
   │  { access_token, ... }        │                           │
   │                               │                           │
   │  GET /api/v1/users/me         │                           │
   │  Authorization: Bearer <tok>  │                           │
   │──────────────────────────────►│                           │
   │                               │  auth.get_user(token)     │
   │                               │──────────────────────────►│
   │                               │◄──────────────────────────│
   │                               │  User object              │
   │◄──────────────────────────────│                           │
   │  { id, email, role }          │                           │
```

1. The frontend authenticates with Supabase directly (using `supabase-js`).
2. The frontend includes the `access_token` in every API request as a `Bearer` token.
3. FastAPI extracts and verifies the token via Supabase Auth.
4. On success, the route handler receives the authenticated user object.

---

## Storage Setup

Storage operations use the **service-role client** (server-side only).

Both buckets are **private** — files are never directly publicly accessible.

Access is always via **signed URLs** with configurable expiry.

```
Upload flow:
  Client → POST /api/v1/... → FastAPI validates file → StorageService.upload_file()
                                                              ↓
                                                   Supabase private bucket
                                                              ↓
                                              StorageService.create_signed_url()
                                                              ↓
                                                    Signed URL returned to client
```

---

## Security Notes

1. **Never commit `.env`** — it's in `.gitignore`.
2. **Service-role key is server-only** — never returned in API responses.
3. **JWTs are never logged** — Authorization headers are excluded from logs.
4. **User identity comes from verified tokens** — never trust client-supplied `user_id`.
5. **Storage buckets are private** — always use signed URLs for file access.
6. **Upload validation is enforced** — MIME type, extension, size, and Pillow integrity checks.
7. **CORS uses explicit origins** — `*` is never used when credentials are involved.
8. **Error responses are sanitised** — no stack traces or internal details in production.

---

## What Is Intentionally NOT Implemented Yet

The following features belong to future phases:

| Feature | Phase |
|---------|-------|
| Conversations | Phase 2 |
| Messages | Phase 2 |
| Image generation (FLUX) | Phase 2 |
| Image transformation | Phase 2 |
| LangGraph / AI graph | Phase 3 |
| AI intent classification | Phase 3 |
| RAG / vector database | Phase 3 |
| Groq LLM integration | Phase 3 |
| Multi-image input processing | Phase 2 |
| Asset database model | Phase 2 |
| Background workers / Celery | Phase 4 |
| WebSockets / SSE | Phase 4 |
| Rate limiting | Phase 4 |
| Admin panel | Phase 4 |
| Frontend | Separate repo |
=======
# vizzy-chat
>>>>>>> 9f50520d77a48a1d4585a3a8245b7530b72cc654
