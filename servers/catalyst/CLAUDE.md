# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Catalyst is a Django REST API backend for an AI-powered learning platform targeting Indian JEE exam students. It generates personalized study roadmaps using LLMs and manages practice questions with vector similarity search.

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python manage.py runserver

# Migrations
python manage.py makemigrations
python manage.py migrate

# Run tests (per app)
python manage.py test roadmap
python manage.py test users
python manage.py test question
python manage.py test practice

# Celery worker (requires Redis)
celery -A catalyst worker --loglevel=info

# Celery beat scheduler
celery -A catalyst beat --loglevel=info
```

## Architecture

### Django Apps

| App | Responsibility |
|-----|---------------|
| `users/` | Auth (JWT via cookies), user profiles, stats, dashboard cache |
| `roadmap/` | AI roadmap generation, job queue, full-text search |
| `question/` | Question bank, Qdrant vector sync |
| `practice/` | Attempt tracking, accuracy metrics |
| `notifications/` | Push notifications (Web Push/VAPID), email, Celery tasks |
| `dashboard/` | Aggregated user dashboard data |
| `catalyst/` | Project config, middleware, constants, rate limiting |

### Authentication

JWT tokens are stored in **cookies**, not the Authorization header. The custom `CookieJWTAuthentication` in `catalyst/middleware.py` handles extraction and validation. All API views default to `IsAuthenticated` — override with `permission_classes = [AllowAny]` for public endpoints.

Requests also require a `X-Cloudflare-Shield` header validated by `CloudflareShieldMiddleware` (secret in `.env` as `CLOUDFLARE_SHIELD_SECRET`).

### LLM Integration

Provider is selected via `LLM_PROVIDER` env var (`openai`, `grok`, or `cerebras`). All three are wrapped in LangChain's `ChatOpenAI`/`ChatCerebras` interface in `roadmap/service/generate.py`. Model names come from `LLM_MODEL_ROADMAP`, `LLM_MODEL_NOTIFICATIONS`, and `LLM_MODEL_PROFILE` env vars. Prompt templates (V2, V3) live in `catalyst/constants.py`.

### Async Task Flow

Roadmap generation and notifications run as async jobs:
1. Request hits Django view → creates a `RoadmapJob` record → enqueues a Google Cloud Tasks HTTP call to `/roadmap/task-be`
2. Cloud Tasks worker calls back → Celery processes the LLM generation
3. Job status is polled via `/roadmap/job`

Celery beat runs `send_daily_notifications` every 12 hours.

### Vector Search

Questions are embedded with `sentence-transformers` and stored in Qdrant (collection defined by `COLLECTION_NAME_VDB`). Embedding generation lives in `catalyst/ai_resources.py`. The management command `question/management/commands/sync_questions_to_qdrant.py` syncs the question bank to Qdrant.

### Database

PostgreSQL via Supabase (connection pooler on port 6543). `Roadmap` model uses `SearchVectorField` with a `GinIndex` for full-text search. `UserProfile.embedding_list` stores user preference vectors as a plain field.

## Key Configuration

- **Settings**: `catalyst/settings.py` — CORS origins, Celery beat schedule, installed apps
- **Constants/Prompts**: `catalyst/constants.py` — all LLM system prompts and app-wide constants
- **URLs**: `catalyst/urls.py` includes app routers under `/api/`, `/roadmap/`, `/practice/`, `/dashboard/`, `/events/notifications/`

## Deployment

Three Docker images:
- `Dockerfile` — main Django/Gunicorn server (port 8080)
- `Dockerfile.beat` — Celery beat scheduler
- `Dockerfile.worker` — Celery task worker

CI/CD via `cloudbuild.yaml` builds and deploys to Google Cloud Run (us-central1, 2 CPU / 2Gi RAM, 0–5 instances). Production domain: `api.catalystedutech.com`.
