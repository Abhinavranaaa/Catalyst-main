import uuid
from types import SimpleNamespace
from django.test import TestCase
from question.models import Question
from roadmap.models import Roadmap, RoadmapQuestion
from users.models import User
from roadmap.service.generate import reshape_roadmap_for_response, sync_roadmap_json_with_question_status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user():
    return User.objects.create_user(
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        password="testpass",
        name="Test User",
    )


def make_question(**kwargs):
    defaults = dict(
        topic="Algebra",
        subject="Mathematics",
        difficulty="medium",
        options=["A", "B", "C", "D"],
        correct_index=1,
        text="What is 3 + 3?",
        explanation=None,
    )
    defaults.update(kwargs)
    return Question.objects.create(**defaults)


def make_raw_roadmap(question_id: str, question_text: str = "Q?", topic: str = "Algebra"):
    """Returns an LLM-style raw roadmap (input to reshape_roadmap_for_response)."""
    return {
        "roadmap_title": "Test Roadmap",
        "blocks": [
            {
                "block_title": "Block 1",
                "block_description": "Intro block",
                "questions": [
                    {
                        "question_id": question_id,
                        "question_text": question_text,
                        "topic": topic,
                    }
                ],
            }
        ],
    }


# ---------------------------------------------------------------------------
# reshape_roadmap_for_response
# ---------------------------------------------------------------------------

class ReshapeRoadmapForResponseTest(TestCase):

    def test_explanation_included_in_output(self):
        """Questions with an explanation from the FastAPI service are included in the reshaped output."""
        q = make_question(explanation="Because 3 + 3 equals 6.")
        raw = make_raw_roadmap(str(q.id), q.text, q.topic)
        question_lookup = {str(q.id): q}

        result = reshape_roadmap_for_response(raw, question_lookup)

        questions = result["roadmapItems"][0]["questions"]
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["explanation"], "Because 3 + 3 equals 6.")

    def test_explanation_defaults_to_empty_string_when_null(self):
        """Questions not yet enriched return an empty string, not None."""
        q = make_question(explanation=None)
        raw = make_raw_roadmap(str(q.id))
        question_lookup = {str(q.id): q}

        result = reshape_roadmap_for_response(raw, question_lookup)

        questions = result["roadmapItems"][0]["questions"]
        self.assertEqual(questions[0]["explanation"], "")

    def test_difficulty_comes_from_db_not_llm(self):
        """Difficulty stored on the Question model is used, not whatever the LLM put in the block."""
        q = make_question(difficulty="hard")
        raw = make_raw_roadmap(str(q.id))
        question_lookup = {str(q.id): q}

        result = reshape_roadmap_for_response(raw, question_lookup)

        questions = result["roadmapItems"][0]["questions"]
        self.assertEqual(questions[0]["difficulty"], "hard")

    def test_correct_index_and_options_from_db(self):
        """correct_index and options are always taken from the DB, never from the LLM payload."""
        q = make_question(options=["X", "Y", "Z"], correct_index=2)
        raw = make_raw_roadmap(str(q.id))
        question_lookup = {str(q.id): q}

        result = reshape_roadmap_for_response(raw, question_lookup)

        q_out = result["roadmapItems"][0]["questions"][0]
        self.assertEqual(q_out["options"], ["X", "Y", "Z"])
        self.assertEqual(q_out["correct_index"], 2)

    def test_unknown_question_id_is_skipped(self):
        """Questions referenced by the LLM but missing from the DB are silently dropped."""
        raw = make_raw_roadmap("00000000-0000-0000-0000-000000000000")
        result = reshape_roadmap_for_response(raw, {})
        self.assertEqual(result["roadmapItems"][0]["questions"], [])


# ---------------------------------------------------------------------------
# sync_roadmap_json_with_question_status
# ---------------------------------------------------------------------------

class SyncRoadmapJsonTest(TestCase):

    def _make_roadmap_with_question(self, difficulty="medium", explanation=None, status="unanswered"):
        user = make_user()
        q = make_question(difficulty=difficulty, explanation=explanation)
        generated_json = {
            "roadmapItems": [
                {
                    "id": "block-001",
                    "title": "Block 1",
                    "questions": [
                        {
                            "id": str(q.id),
                            "question_text": q.text,
                            "difficulty": "easy",       # stale value — should be overwritten
                            "explanation": "old text",  # stale value — should be overwritten
                            "status": "unanswered",
                        }
                    ],
                }
            ]
        }
        roadmap = Roadmap.objects.create(
            user=user,
            title="Test",
            generated_json=generated_json,
            subject="Mathematics",
        )
        RoadmapQuestion.objects.create(roadmap=roadmap, question=q, status=status)
        return roadmap, q

    def test_sync_updates_explanation_from_db(self):
        """After FastAPI enriches a question, sync pulls the new explanation into the JSON."""
        roadmap, q = self._make_roadmap_with_question(explanation="Correct because 3+3=6.")

        result = sync_roadmap_json_with_question_status(roadmap)

        q_out = result["roadmapItems"][0]["questions"][0]
        self.assertEqual(q_out["explanation"], "Correct because 3+3=6.")

    def test_sync_updates_difficulty_from_db(self):
        """After FastAPI re-analyses difficulty, sync replaces the stale value in JSON."""
        roadmap, q = self._make_roadmap_with_question(difficulty="hard")

        result = sync_roadmap_json_with_question_status(roadmap)

        q_out = result["roadmapItems"][0]["questions"][0]
        self.assertEqual(q_out["difficulty"], "hard")

    def test_sync_updates_status_to_answered(self):
        """Questions marked answered in RoadmapQuestion are reflected in the JSON."""
        roadmap, q = self._make_roadmap_with_question(status="answered")

        result = sync_roadmap_json_with_question_status(roadmap)

        q_out = result["roadmapItems"][0]["questions"][0]
        self.assertEqual(q_out["status"], "answered")

    def test_sync_status_defaults_to_unanswered_when_rq_missing(self):
        """If somehow a question has no RoadmapQuestion row, status falls back to 'unanswered'."""
        user = make_user()
        q = make_question()
        generated_json = {
            "roadmapItems": [
                {
                    "questions": [
                        {"id": str(q.id), "status": "answered"}
                    ]
                }
            ]
        }
        roadmap = Roadmap.objects.create(
            user=user, title="Test", generated_json=generated_json, subject="Math"
        )
        # Intentionally no RoadmapQuestion created

        result = sync_roadmap_json_with_question_status(roadmap)

        q_out = result["roadmapItems"][0]["questions"][0]
        self.assertEqual(q_out["status"], "unanswered")

    def test_sync_returns_empty_dict_when_no_generated_json(self):
        user = make_user()
        roadmap = Roadmap.objects.create(
            user=user, title="Empty", generated_json=None, subject="Math"
        )
        result = sync_roadmap_json_with_question_status(roadmap)
        self.assertEqual(result, {})