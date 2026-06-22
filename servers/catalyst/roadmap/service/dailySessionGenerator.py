import json
import logging
import uuid
from datetime import timedelta
from typing import Optional

from django.db.models import Min, Max
from django.utils import timezone
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI
from qdrant_client import QdrantClient
import os
from dotenv import load_dotenv

from catalyst.ai_resources import generate_embedding_from_text
from catalyst.constants import (
    COLLECTION_NAME_CONSTANT, GROK_API_KEY, LLM_PROVIDER, GROK, OPENAI,
    OPENAI_API_KEY, SESSION_PLAN_PROMPT, LLM_MODEL_ROADMAP,
)
from catalyst.utils import remove_think_blocks
from practice.models import Answer
from practice.service.sessionTopicAccuracy import get_session_topic_accuracy
from question.models import Question
from roadmap.models import DailySession
from roadmap.service.generate import parse_llm_response_to_json

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..', '..'))

if os.getenv("RENDER") != "true":
    load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)

_VECTOR_DB_URL = os.getenv("VECTOR_DB_URL")
_VECTOR_DB_KEY = os.getenv("VECTOR_DB_KEY")
_COLLECTION_NAME = os.getenv(COLLECTION_NAME_CONSTANT)
_GROK_KEY = os.getenv(GROK_API_KEY)
_OPENAI_KEY = os.getenv(OPENAI_API_KEY)
_ROADMAP_MODEL = os.getenv(LLM_MODEL_ROADMAP) or "llama-3.3-70b-versatile"
_LLM_PROVIDER = os.getenv(LLM_PROVIDER, GROK)

qdrant = QdrantClient(url=_VECTOR_DB_URL, api_key=_VECTOR_DB_KEY)

if _LLM_PROVIDER == GROK:
    _llm = ChatOpenAI(
        model=_ROADMAP_MODEL,
        api_key=_GROK_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.2,
        max_tokens=600,
    )
else:
    _llm = ChatOpenAI(
        model=_ROADMAP_MODEL,
        api_key=_OPENAI_KEY,
        temperature=0.2,
        max_tokens=600,
    )

# Difficulty integer ranges per session area type
_DIFFICULTY_RANGES = {
    "new":      {1, 2},
    "weakness": {1, 2, 3, 4, 5},
    "review":   {2, 3, 4, 5},
    "advance":  {4, 5},          # hard questions only — Bloom's progression
}

_BLOOM_RANGES = {
    "new":      {1, 2, 3},           # Remember, Understand, Apply — build foundations
    "weakness": {1, 2, 3},           # same — shore up basics before higher-order thinking
    "review":   {2, 3, 4},           # Understand, Apply, Analyze — consolidate
    "advance":  {4, 5, 6},           # Analyze, Evaluate, Create — push mastered topics
}

_DEFAULT_COUNTS = {"weakness": 8, "new": 6, "review": 5, "advance": 4}
_DIFFICULTY_LABEL = {"new": "easy", "weakness": "mixed", "review": "medium", "advance": "hard"}


# ── Public entry point ────────────────────────────────────────────────────────

def generate_daily_session(user_id: int, subject: str) -> dict:
    today = timezone.now().date()

    existing = DailySession.objects.filter(
        user_id=user_id, subject=subject, date=today
    ).first()
    if existing:
        logger.info("Returning cached daily session user=%s subject=%s", user_id, subject)
        return existing.payload_json

    # ── Step 1: load topic accuracy ───────────────────────────────────────────
    topic_accuracy = get_session_topic_accuracy(user_id, subject)

    recently_answered_ids: set[str] = set(
        Answer.objects
        .filter(
            user_id=user_id,
            daily_session__subject=subject,
            answered_at__gte=timezone.now() - timedelta(days=14),
        )
        .values_list("question_id", flat=True)
    )
    recently_answered_ids = {str(i) for i in recently_answered_ids}

    # ── Step 2: LLM session plan (all topics including mastered) ─────────────
    overall_accuracy = _compute_overall_accuracy(topic_accuracy)
    focus_areas = _plan_session(subject, topic_accuracy, overall_accuracy)

    if not focus_areas:
        logger.warning("LLM returned no focus areas — using deterministic fallback")
        focus_areas = _fallback_focus_areas(topic_accuracy)

    # ── Step 2b: embed per-topic accuracy into focus areas (weakness only) ───
    accuracy_map = {t["topic"]: t["accuracy"] for t in topic_accuracy}
    for area in focus_areas:
        area["accuracy"] = accuracy_map.get(area["topic"]) if area["type"] == "weakness" else None

    # ── Step 3: fetch questions per focus area ────────────────────────────────
    # used_ids grows with each area so no question appears in more than one area
    used_ids: set[str] = set(recently_answered_ids)
    all_question_ids: list[str] = []
    for area in focus_areas:
        questions = _fetch_questions_for_area(
            subject=subject,
            topic=area["topic"],
            area_type=area["type"],
            count=area["questionCount"],
            exclude_ids=used_ids,
        )
        area["questions"] = questions
        area["questionCount"] = len(questions)
        fetched_ids = [q["id"] for q in questions]
        all_question_ids.extend(fetched_ids)
        used_ids.update(fetched_ids)

    # ── Step 4: derived fields ────────────────────────────────────────────────
    total_questions = sum(a["questionCount"] for a in focus_areas)
    estimated_minutes = round(total_questions * 1.2)

    bloom_stats = (
        Question.objects
        .filter(id__in=all_question_ids, bloom_level__isnull=False)
        .aggregate(min_bloom=Min("bloom_level"), max_bloom=Max("bloom_level"))
    )
    blooms_range = {
        "min": bloom_stats["min_bloom"] or 1,
        "max": bloom_stats["max_bloom"] or 3,
    }

    monday = today - timedelta(days=today.weekday())
    weekly_completed = DailySession.objects.filter(
        user_id=user_id,
        subject=subject,
        date__gte=monday,
        is_completed=True,
    ).count()

    # ── Step 5: assemble and persist ──────────────────────────────────────────
    session_id = uuid.uuid4()
    payload = {
        "sessionId": str(session_id),
        "date": today.isoformat(),
        "subject": subject,
        "questionCount": total_questions,
        "estimatedMinutes": estimated_minutes,
        "weeklyProgress": weekly_completed,
        "bloomsRange": blooms_range,
        "overallAccuracy": overall_accuracy,
        "focusAreas": focus_areas,
    }

    DailySession.objects.create(
        user_id=user_id,
        subject=subject,
        date=today,
        payload_json=payload,
        session_id=session_id,
        is_completed=False,
    )

    return payload


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compute_overall_accuracy(topic_accuracy: list[dict]) -> int:
    total_attempts = sum(t["attempts"] for t in topic_accuracy)
    if not total_attempts:
        return 0
    total_correct = sum(round(t["accuracy"] * t["attempts"] / 100) for t in topic_accuracy)
    return round(total_correct / total_attempts * 100)


def _plan_session(subject: str, topic_accuracy: list[dict], overall_accuracy: int) -> list[dict]:
    if not topic_accuracy:
        return []

    topics_json = json.dumps(
        [
            {
                "topic": t["topic"],
                "type": t["type"],
                "accuracy": t["accuracy"],
                "attempts": t["attempts"],
            }
            for t in topic_accuracy
        ],
        indent=2,
    )

    prompt = SESSION_PLAN_PROMPT.format(
        subject=subject,
        overall_accuracy=overall_accuracy,
        topics_json=topics_json,
    )

    try:
        response = _llm.invoke([HumanMessage(content=prompt)])
        text = remove_think_blocks(response.content)
        parsed = parse_llm_response_to_json(text, debug_log=logger.debug)
        if parsed and "focusAreas" in parsed:
            areas = parsed["focusAreas"][:4]
            for area in areas:
                area_type = area.get("type", "new")
                area.setdefault("questionCount", _DEFAULT_COUNTS.get(area_type, 6))
                area.setdefault("difficulty", _DIFFICULTY_LABEL.get(area_type, "mixed"))
                area.setdefault("topicHeadline", area.get("topic", "")[:60])
                area.setdefault("reason", "")
            return areas
    except Exception:
        logger.exception("Session plan LLM call failed")

    return []


def _fallback_focus_areas(topic_accuracy: list[dict]) -> list[dict]:
    """
    Deterministic fallback — no LLM.
    Mastered topics become "advance"; everything else sorted by priority.
    """
    priority = {"weakness": 0, "new": 1, "review": 2, "mastered": 3}
    sorted_topics = sorted(topic_accuracy, key=lambda t: priority.get(t["type"], 9))

    result = []
    for t in sorted_topics[:4]:
        t_type = t["type"]
        # Promote mastered → advance
        if t_type == "mastered":
            t_type = "advance"
        accuracy_str = f"{t['accuracy']}% on {t['attempts']} attempt(s)."
        result.append({
            "topic": t["topic"],
            "type": t_type,
            "questionCount": _DEFAULT_COUNTS.get(t_type, 6),
            "difficulty": _DIFFICULTY_LABEL.get(t_type, "mixed"),
            "topicHeadline": f"Focus: {t['topic']}"[:60],
            "reason": accuracy_str[:150],
        })
    return result


def _fetch_questions_for_area(
    subject: str,
    topic: str,
    area_type: str,
    count: int,
    exclude_ids: set[str],
) -> list[dict]:
    """
    Fetches `count` questions for a focus area.
    `exclude_ids` contains both recently-answered IDs (cross-session dedup)
    and questions already selected for earlier areas in this session (cross-area dedup).
    """
    difficulty_hint = _DIFFICULTY_LABEL.get(area_type, "mixed")
    query_text = f"Subject: {subject}. Topic: {topic}. Difficulty: {difficulty_hint}"
    query_vector = generate_embedding_from_text(query_text)

    fetch_limit = count + len(exclude_ids) + 10

    hits = qdrant.search(
        collection_name=_COLLECTION_NAME,
        query_vector=query_vector,
        limit=fetch_limit,
        score_threshold=0.45,
        with_payload=False,
    )

    candidate_ids = [
        str(hit.id) for hit in hits
        if str(hit.id) not in exclude_ids
    ]

    questions = _fetch_from_postgres(candidate_ids, area_type)
    questions = questions[:count]

    if len(questions) < count:
        questions = _fill_from_fallback(
            questions, subject, area_type, exclude_ids, count
        )

    return [_format_question(q) for q in questions]


def _fetch_from_postgres(ids: list[str], area_type: str) -> list:
    if not ids:
        return []

    allowed_difficulties = _DIFFICULTY_RANGES.get(area_type, {1, 2, 3, 4, 5})
    allowed_blooms = _BLOOM_RANGES.get(area_type, {1, 2, 3, 4, 5, 6})

    qs = list(
        Question.objects
        .filter(id__in=ids)
        .only(
            "id", "text", "options", "correct_index", "difficulty",
            "explanation", "distractor_explanations", "bloom_level", "topic",
        )
    )

    id_order = {qid: idx for idx, qid in enumerate(ids)}
    qs.sort(key=lambda q: id_order.get(str(q.id), 9999))

    return [
        q for q in qs
        if q.difficulty in allowed_difficulties
        and (q.bloom_level is None or q.bloom_level in allowed_blooms)
    ]


def _fill_from_fallback(
    existing: list,
    subject: str,
    area_type: str,
    exclude_ids: set[str],
    target_count: int,
) -> list:
    needed = target_count - len(existing)
    if needed <= 0:
        return existing

    allowed_difficulties = _DIFFICULTY_RANGES.get(area_type, {1, 2, 3, 4, 5})
    allowed_blooms = _BLOOM_RANGES.get(area_type, {1, 2, 3, 4, 5, 6})
    all_exclude = exclude_ids | {str(q.id) for q in existing}

    from django.db.models import Q

    extra = list(
        Question.objects
        .filter(
            Q(bloom_level__isnull=True) | Q(bloom_level__in=allowed_blooms),
            subject=subject,
            difficulty__in=allowed_difficulties,
        )
        .exclude(id__in=all_exclude)
        .order_by("difficulty", "bloom_level")
        .only(
            "id", "text", "options", "correct_index", "difficulty",
            "explanation", "distractor_explanations", "bloom_level", "topic",
        )[:needed]
    )

    logger.info(
        "Fallback filled %d/%d questions for subject=%s area_type=%s",
        len(extra), needed, subject, area_type,
    )
    return existing + extra


def _format_question(q) -> dict:
    return {
        "id": str(q.id),
        "text": q.text,
        "options": q.options,
        "correct_index": q.correct_index,
        "difficulty": q.difficulty_label,
        "explanation": q.explanation or "",
        "distractor_explanations": q.distractor_explanations or "",
        "bloom_level": q.bloom_level,
        "isBookmarked": False,
        "status": "unanswered",
    }
