
from users.models import UserProfile
from practice.models import Answer
from roadmap.models import Roadmap, RoadmapQuestion
from django.db.models import Count, Q


def get_user_profile(user_id):
    profile = (
        UserProfile.objects
        .with_computed_fields()
        .filter(user_id=user_id)
        .values(
            'user__name',
            'learning_streak',
            'strong_topics',
            'weak_topics',
            'average_accuracy',
            'avg_difficulty',
            'average_time_per_question',
            'created_at',
            'modified_at',
            'total_roadmaps_generated',
            'total_questions_solved',
        )
        .first()
    )
    if profile:
        profile['name'] = profile.pop('user__name', None)
    return profile or {}

def get_recent_roadmaps_with_progress(user_id, limit=10):
    recent_roadmaps = (
        Roadmap.objects
        .filter(user_id=user_id)
        .order_by('-created_at')[:limit]
        .only('id', 'title', 'created_at')
    )

    roadmap_ids = [r.id for r in recent_roadmaps]

    roadmap_questions = (
        RoadmapQuestion.objects
        .filter(roadmap_id__in=roadmap_ids)
        .values('roadmap_id')
        .annotate(total_questions=Count('question_id'))
    )
    question_count_by_roadmap = {item['roadmap_id']: item['total_questions'] for item in roadmap_questions}

    correct_answers = (
        Answer.objects
        .filter(
            roadmap_id__in=roadmap_ids,
            user_id=user_id,
            is_correct=True
        )
        .values('roadmap_id', 'question_id')
        .distinct()
        .values('roadmap_id')
        .annotate(correct_questions=Count('question_id'))
    )
    correct_by_roadmap = {item['roadmap_id']: item['correct_questions'] for item in correct_answers}

    result = []
    for roadmap in recent_roadmaps:
        total_questions = question_count_by_roadmap.get(roadmap.id, 0)
        correct = correct_by_roadmap.get(roadmap.id, 0)
        percentage_solved = round((correct / total_questions) * 100, 2) if total_questions else 0.0
        result.append({
            "roadmap_id": str(roadmap.id),
            "title": roadmap.title,
            "percentage_solved": percentage_solved,
            "created_at": roadmap.created_at,
        })
    return result

def fetch_user_profile_with_top_roadmaps(user_id):
    profile = get_user_profile(user_id)
    if not profile:
        return {}
    profile["recent_roadmaps"] = get_recent_roadmaps_with_progress(user_id)
    return profile

