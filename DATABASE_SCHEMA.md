# Catalyst Database Schema

> Django + PostgreSQL. All models live under `servers/catalyst/<app>/models.py`.

---

## Table of Contents

- [users](#users-app)
  - [User](#user)
  - [UserProfile](#userprofile)
  - [UserStats](#userstats)
  - [UserDailyActivity](#userdailyactivity)
  - [Subscriber](#subscriber)
- [question](#question-app)
  - [Question](#question)
- [roadmap](#roadmap-app)
  - [Roadmap](#roadmap)
  - [RoadmapQuestion](#roadmapquestion)
  - [RoadmapJob](#roadmapjob)
- [practice](#practice-app)
  - [Answer](#answer)
- [notifications](#notifications-app)
  - [Notification](#notification)
  - [WebPushSubscription](#webpushsubscription)

---

## users app

`servers/catalyst/users/models.py`

### User

Extends Django's `AbstractUser`. `username` is removed; `email` is the login field.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | int (auto) | PK | Django default |
| `name` | varchar(255) | NOT NULL | |
| `email` | varchar(255) | UNIQUE, NOT NULL | Used as `USERNAME_FIELD` |
| `password` | varchar(255) | NOT NULL | Hashed by Django |
| `auth_provider` | varchar(255) | NOT NULL, default `"PLATFORM"` | e.g. `"PLATFORM"`, `"GOOGLE"` |
| `first_name` | varchar(150) | inherited | from AbstractUser |
| `last_name` | varchar(150) | inherited | from AbstractUser |
| `is_staff` | bool | inherited | |
| `is_active` | bool | inherited | |
| `date_joined` | datetime | inherited | |
| `last_login` | datetime | inherited, nullable | |

---

### UserProfile

One-to-one with `User`. Primary key is the user FK.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `user_id` | int | PK, FK → User | CASCADE on delete |
| `learning_streak` | int | nullable | |
| `bio` | text(500) | nullable | |
| `phone` | varchar(20) | nullable | |
| `profile_image` | image | nullable, default `profile_images/default.jpg` | stored in media |
| `strong_topics` | text[] | NOT NULL, default `[]` | Postgres array |
| `weak_topics` | text[] | NOT NULL, default `[]` | Postgres array |
| `average_accuracy` | float | nullable | |
| `avg_difficulty` | float | nullable | |
| `average_time_per_question` | float | nullable | seconds |
| `taste_keywords_list` | jsonb | default `[]` | |
| `primary_goal_onboarding` | varchar(26) | default `"other"` | choices: school exams, competitive exams, university semester exams, professional certification, general knowledge |
| `daily_target_time` | int | nullable | minutes |
| `embedding_list` | jsonb | default `[]` | vector embedding |
| `created_at` | datetime | auto, nullable | |
| `modified_at` | datetime | auto_now, nullable | |

---

### UserStats

One-to-one with `User`. Aggregated lifetime stats.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `user_id` | int | PK, FK → User | CASCADE on delete |
| `total_attempted` | int | default `0` | |
| `total_time_spent_seconds` | int | default `0` | |
| `easy_correct` | int | default `0` | |
| `medium_correct` | int | default `0` | |
| `hard_correct` | int | default `0` | |
| `current_streak` | int | default `0` | days |
| `max_streak` | int | default `0` | days |
| `last_activity_date` | date | nullable | |
| `updated_at` | datetime | auto_now | |

---

### UserDailyActivity

Per-user, per-day activity snapshot.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | int (auto) | PK | |
| `user_id` | int | FK → User | CASCADE on delete |
| `date` | date | NOT NULL | |
| `total_attempted` | int | default `0` | |
| `total_correct` | int | default `0` | |
| `time_spent_seconds` | int | default `0` | |

**Constraints:** `UNIQUE (user, date)`
**Indexes:** `(user, date)`

---

### Subscriber

Email-only mailing list opt-in.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | int (auto) | PK | |
| `email` | varchar | UNIQUE, NOT NULL | |
| `created_at` | datetime | auto | |

---

## question app

`servers/catalyst/question/models.py` — db_table: `questions`

### Question

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, auto | |
| `topic` | varchar(255) | nullable | |
| `subject` | varchar(255) | nullable | |
| `difficulty` | varchar(50) | nullable | e.g. `"easy"`, `"medium"`, `"hard"` |
| `source` | text | nullable | where the question came from |
| `options` | text[] | NOT NULL | list of answer options |
| `correct_index` | int | NOT NULL | 0-based index into `options` |
| `text` | text | NOT NULL | question body |
| `explanation` | text | nullable | explanation of the correct answer |

---

## roadmap app

`servers/catalyst/roadmap/models.py`

### Roadmap

db_table: `roadmaps`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, auto | |
| `user_id` | int | FK → User, nullable | CASCADE on delete |
| `title` | varchar(255) | nullable | |
| `subject` | varchar(255) | nullable | |
| `topics` | text[] | nullable | list of topic strings |
| `description` | text | nullable | |
| `created_at` | datetime | auto, nullable | |
| `modified_at` | datetime | auto_now, nullable | |
| `progress_percntg` | decimal(6,2) | default `0.00` | 0–100 |
| `avg_difficulty` | varchar(20) | default `"Medium"` | choices: easy, medium, hard |
| `generated_json` | jsonb | nullable | raw AI-generated roadmap payload |
| `search_vector_en` | tsvector | nullable | full-text search (English) |
| `search_vector_smpl` | tsvector | nullable | full-text search (simple) |

**Indexes:** GIN on `search_vector_en`, GIN on `search_vector_smpl`

---

### RoadmapQuestion

Junction table linking roadmaps to questions.

db_table: `roadmap_question`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | int (auto) | PK | |
| `roadmap_id` | UUID | FK → Roadmap | CASCADE on delete |
| `question_id` | UUID | FK → Question | CASCADE on delete |
| `status` | varchar(50) | default `"unanswered"` | choices: answered, unanswered |

**Constraints:** `UNIQUE (roadmap, question)`

---

### RoadmapJob

Async job tracking for roadmap generation.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, auto | |
| `user_id` | int | FK → User | CASCADE on delete |
| `input_data` | jsonb | NOT NULL | request payload |
| `status` | varchar(20) | default `"queued"` | choices: queued, processing, completed, failed |
| `error_message` | text | nullable | |
| `roadmap_id` | UUID | FK → Roadmap, nullable | CASCADE on delete; set after completion |
| `created_at` | datetime | auto | |
| `updated_at` | datetime | auto_now | |

**Indexes:** `(user, status, created_at)`

---

## practice app

`servers/catalyst/practice/models.py` — db_table: `answers`

### Answer

Records each answer submission.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, auto | |
| `user_id` | int | FK → User, nullable | DO_NOTHING on delete |
| `roadmap_id` | UUID | FK → Roadmap, nullable | DO_NOTHING on delete |
| `question_id` | UUID | FK → Question, nullable | DO_NOTHING on delete |
| `selected_index` | int | NOT NULL | 0-based index into `question.options` |
| `is_correct` | bool | nullable | derived from `selected_index == question.correct_index` |
| `answered_at` | datetime | auto | |
| `time_taken_seconds` | int | nullable | |

---

## notifications app

`servers/catalyst/notifications/models.py`

### Notification

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | int (auto) | PK | |
| `user_id` | int | FK → User | CASCADE on delete |
| `message` | text | NOT NULL | |
| `delivery_status` | varchar(20) | default `"pending"` | choices: pending, sent, failed |
| `created_at` | datetime | auto | |
| `read` | bool | default `false` | |
| `channel` | varchar(16) | NOT NULL | choices: push, email |
| `keyword_used` | varchar(256) | nullable | keyword that triggered this notification |

---

### WebPushSubscription

Stores browser push subscription info (Web Push Protocol).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | int (auto) | PK | |
| `user_id` | int | FK → User | CASCADE on delete |
| `endpoint` | text | UNIQUE, NOT NULL | push service URL |
| `p256dh` | text | NOT NULL | public key |
| `auth` | text | NOT NULL | auth secret |
| `created_at` | datetime | auto | |

---

## Entity Relationships (summary)

```
User (1) ──────────────── (1) UserProfile
User (1) ──────────────── (1) UserStats
User (1) ──────────────── (N) UserDailyActivity
User (1) ──────────────── (N) Roadmap
User (1) ──────────────── (N) RoadmapJob
User (1) ──────────────── (N) Answer
User (1) ──────────────── (N) Notification
User (1) ──────────────── (N) WebPushSubscription

Roadmap  (1) ──────────── (N) RoadmapQuestion
Question (1) ──────────── (N) RoadmapQuestion
                                    ↑
                         junction table (Roadmap ↔ Question)

Roadmap  (1) ──────────── (N) Answer
Question (1) ──────────── (N) Answer
RoadmapJob (N) ─────────── (1) Roadmap  (nullable, set on completion)
```

---

## Adding a New Field — Checklist

1. Edit the relevant `models.py`
2. Run `python manage.py makemigrations <app>`
3. Run `python manage.py migrate`
4. Update this file with the new column entry