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
| `roadmap/` | AI roadmap generation, job queue, daily session generation, full-text search |
| `question/` | Question bank, Qdrant vector sync, code snippet fields |
| `practice/` | Attempt tracking, session submit pipeline, accuracy metrics |
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

### Daily Sessions

Daily sessions are generated per user per subject per day by `roadmap/service/dailySessionGenerator.py` and stored in `roadmap.DailySession`. The session flow:

1. `GET /api/sessions/today` — generates or fetches today's `DailySession`, returns focus areas without questions
2. `GET /api/sessions/{session_id}/questions` — returns the full question payload for the session
3. `POST /api/sessions/{session_id}/submit` — DS-009 submit pipeline (see below)

**Submit pipeline** (`practice/service/processSessionAttempts.py`):
- Validates session ownership (403/404), idempotency via `completed_at` (409), and question IDs against the payload (422)
- Recomputes `is_correct` server-side — never trusts the client value
- Dual-writes to `SessionAttempt` (rich analytics) and `Answer` (legacy analytics continuity)
- Invalidates Redis session accuracy cache outside the transaction
- Fetches fresh 30-day rolling topic classifications (same `_classify()` used by session generator) to build `updated_state`
- Returns per-topic `previous_state → updated_state` for the results screen — guaranteed to match what the next session generator will see

**Topic classification thresholds** (shared by submit response and session generator via `_classify()`):

| Condition | Classification |
|---|---|
| < 3 attempts (30-day window) | new |
| ≥ 80% accuracy AND ≥ 5 attempts | mastered |
| < 65% accuracy | weakness |
| 65–79% accuracy | review |

**Models:**
- `roadmap.DailySession` — one per user/subject/day; `completed_at` is the idempotency marker; `session_started_at` stored for duration tracking
- `practice.SessionAttempt` — rich per-attempt record including `topic_name`, `topic_type`, `time_to_first_tap_ms`, `skipped`, `bloom_level`, `sequence_position`
- `practice.Answer` — legacy analytics table; skipped attempts are excluded from this table

**Redis cache keys:**
- `session_accuracy:{user_id}:{subject}` — invalidated on every successful submit

### Code Snippets (CAT-001)

`question.Question` has three optional snippet fields for code-based MCQs:
- `snippet_language` — GeSHi/highlighter language identifier (e.g. `"java"`, `"python"`)
- `snippet_body` — raw source code to display
- `snippet_line_range` — `[start, end]` 1-indexed line numbers to highlight; `null` = show all

All three are included in the roadmap question API response (`roadmap/service/generate.py → reshape_roadmap_for_response`).

### Bloom Level Filtering

Session question fetching filters by both difficulty AND Bloom's Taxonomy level based on the focus area type. This ensures mastered topics push students to higher-order thinking while weak/new topics stay foundational.

| Area type | Bloom levels | Cognitive range |
|---|---|---|
| new | 1, 2, 3 | Remember, Understand, Apply |
| weakness | 1, 2, 3 | Remember, Understand, Apply |
| review | 2, 3, 4 | Understand, Apply, Analyze |
| advance | 4, 5, 6 | Analyze, Evaluate, Create |

Questions with `bloom_level=NULL` are allowed through all filters (graceful fallback for un-enriched questions). Defined in `_BLOOM_RANGES` in `roadmap/service/dailySessionGenerator.py`.

### Vector Search

Questions are embedded with `sentence-transformers` and stored in Qdrant (collection defined by `COLLECTION_NAME_VDB`). Embedding generation lives in `catalyst/ai_resources.py`. The management command `question/management/commands/sync_questions_to_qdrant.py` syncs the question bank to Qdrant.

### Database

PostgreSQL via Supabase (connection pooler on port 6543). `Roadmap` model uses `SearchVectorField` with a `GinIndex` for full-text search. `UserProfile.embedding_list` stores user preference vectors as a plain field.

### Accuracy Caches

Two separate Redis-backed accuracy caches:
- `accuracy:{user_id}:{roadmap_id}` — roadmap topic accuracy, invalidated in `practice/service/topicAccuracy.py`
- `session_accuracy:{user_id}:{subject}` — daily session topic accuracy (30-day window), invalidated in `practice/service/sessionTopicAccuracy.py`

Both use Upstash Redis (`catalyst/infra/redis.py`). Cache invalidation must always happen **outside** the atomic transaction block — only after DB commit.

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
