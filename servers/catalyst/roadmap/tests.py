import uuid
from datetime import timedelta
from types import SimpleNamespace
from django.test import TestCase
from django.utils import timezone
from enrollments.models import CourseEnrollment
from question.models import AttachmentType, Question, QuestionAttachment, QuestionSet
from roadmap.models import DailySession, Roadmap, RoadmapQuestion
from users.models import User
from roadmap.service.generate import reshape_roadmap_for_response, sync_roadmap_json_with_question_status
from roadmap.service.dailySessionGenerator import create_ready_session, resolve_set_membership, _format_question


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user():
    return User.objects.create(
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        password="testpass",
        name="Test User",
    )


def make_question(**kwargs):
    defaults = dict(
        topic="Algebra",
        subject="Mathematics",
        difficulty=3,
        options=["A", "B", "C", "D"],
        correct_index=1,
        text="What is 3 + 3?",
        explanation=None,
        distractor_explanations=None,
        bloom_level=None,
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
        q = make_question(difficulty=5)
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

    def test_distractor_explanations_included_in_output(self):
        q = make_question(distractor_explanations="B is wrong because..., C is wrong because...")
        raw = make_raw_roadmap(str(q.id), q.text, q.topic)

        result = reshape_roadmap_for_response(raw, {str(q.id): q})

        q_out = result["roadmapItems"][0]["questions"][0]
        self.assertEqual(q_out["distractor_explanations"], "B is wrong because..., C is wrong because...")

    def test_distractor_explanations_defaults_to_empty_string_when_null(self):
        q = make_question(distractor_explanations=None)
        raw = make_raw_roadmap(str(q.id))

        result = reshape_roadmap_for_response(raw, {str(q.id): q})

        self.assertEqual(result["roadmapItems"][0]["questions"][0]["distractor_explanations"], "")

    def test_bloom_level_included_in_output(self):
        q = make_question(bloom_level=3)
        raw = make_raw_roadmap(str(q.id))

        result = reshape_roadmap_for_response(raw, {str(q.id): q})

        self.assertEqual(result["roadmapItems"][0]["questions"][0]["bloom_level"], 3)

    def test_bloom_level_is_none_when_not_set(self):
        q = make_question(bloom_level=None)
        raw = make_raw_roadmap(str(q.id))

        result = reshape_roadmap_for_response(raw, {str(q.id): q})

        self.assertIsNone(result["roadmapItems"][0]["questions"][0]["bloom_level"])

    def test_attachments_included_in_output(self):
        q = make_question()
        QuestionAttachment.objects.create(
            question=q,
            attachment_type=AttachmentType.TEXT,
            inline_content="See diagram.",
            metadata={"format": "plain"},
            order=0,
        )
        raw = make_raw_roadmap(str(q.id))

        result = reshape_roadmap_for_response(raw, {str(q.id): q})

        attachments = result["roadmapItems"][0]["questions"][0]["attachments"]
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0]["type"], "text")
        self.assertEqual(attachments[0]["content"], "See diagram.")


# ---------------------------------------------------------------------------
# sync_roadmap_json_with_question_status
# ---------------------------------------------------------------------------

class SyncRoadmapJsonTest(TestCase):

    def _make_roadmap_with_question(self, difficulty=3, explanation=None,
                                     distractor_explanations=None, bloom_level=None,
                                     status="unanswered"):
        user = make_user()
        q = make_question(
            difficulty=difficulty,
            explanation=explanation,
            distractor_explanations=distractor_explanations,
            bloom_level=bloom_level,
        )
        generated_json = {
            "roadmapItems": [
                {
                    "id": "block-001",
                    "title": "Block 1",
                    "questions": [
                        {
                            "id": str(q.id),
                            "question_text": q.text,
                            "difficulty": "easy",                  # stale — should be overwritten
                            "explanation": "old text",             # stale — should be overwritten
                            "distractor_explanations": "old text", # stale — should be overwritten
                            "bloom_level": 99,                     # stale — should be overwritten
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
        roadmap, q = self._make_roadmap_with_question(difficulty=5)

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

    def test_sync_updates_distractor_explanations_from_db(self):
        """After enrichment, sync pulls the new distractor_explanations into the JSON."""
        roadmap, q = self._make_roadmap_with_question(distractor_explanations="B wrong, C wrong")

        result = sync_roadmap_json_with_question_status(roadmap)

        q_out = result["roadmapItems"][0]["questions"][0]
        self.assertEqual(q_out["distractor_explanations"], "B wrong, C wrong")

    def test_sync_updates_bloom_level_from_db(self):
        """After enrichment, sync pulls the new bloom_level into the JSON."""
        roadmap, q = self._make_roadmap_with_question(bloom_level=4)

        result = sync_roadmap_json_with_question_status(roadmap)

        self.assertEqual(result["roadmapItems"][0]["questions"][0]["bloom_level"], 4)

    def test_sync_returns_empty_dict_when_no_generated_json(self):
        user = make_user()
        roadmap = Roadmap.objects.create(
            user=user, title="Empty", generated_json=None, subject="Math"
        )
        result = sync_roadmap_json_with_question_status(roadmap)
        self.assertEqual(result, {})


# ---------------------------------------------------------------------------
# create_ready_session — SCHED-01
# ---------------------------------------------------------------------------

class CreateReadySessionScheduledForTest(TestCase):

    def test_scheduled_for_is_set_to_tomorrow_server_date(self):
        """A session created today via create_ready_session has scheduled_for == today + 1 day (server date)."""
        user = make_user()
        enrollment = CourseEnrollment.objects.create(user=user, course="Mathematics")
        today = timezone.now().date()

        session = create_ready_session(
            enrollment=enrollment,
            session_id=uuid.uuid4(),
            payload={"focusAreas": []},
            date=today,
        )

        self.assertEqual(session.scheduled_for, today + timedelta(days=1))


# ---------------------------------------------------------------------------
# resolve_set_membership — QT-02
# ---------------------------------------------------------------------------

class ResolveSetMembershipTest(TestCase):

    def _make_set(self, n=4, topic="Employees per Department"):
        qset = QuestionSet.objects.create(
            topic=topic, difficulty="medium", directions_text="Study the table.",
        )
        members = [
            make_question(
                text=f"Q{i}", topic=topic, set=qset, position_in_set=i,
            )
            for i in range(1, n + 1)
        ]
        return qset, members

    def test_full_set_is_included_when_all_members_available(self):
        qset, members = self._make_set(n=4)

        resolved = resolve_set_membership(members, recently_answered_ids=set())

        self.assertEqual({q.id for q in resolved}, {q.id for q in members})
        self.assertEqual(len(resolved), 4)

    def test_set_dropped_entirely_when_one_member_recently_answered(self):
        """A set with one member excluded (e.g. recently answered) drops as a whole — never partial."""
        qset, members = self._make_set(n=4)
        recently_answered = {str(members[1].id)}  # exclude just one member

        resolved = resolve_set_membership(members, recently_answered_ids=recently_answered)

        self.assertEqual(resolved, [])

    def test_set_resolved_once_even_if_multiple_members_are_candidates(self):
        """Passing several members of the same set as candidates doesn't duplicate the set."""
        qset, members = self._make_set(n=3)

        resolved = resolve_set_membership(members, recently_answered_ids=set())

        self.assertEqual(len(resolved), 3)
        self.assertEqual(len({q.id for q in resolved}), 3)

    def test_set_members_returned_in_position_order(self):
        qset, members = self._make_set(n=3)
        shuffled = [members[2], members[0], members[1]]

        resolved = resolve_set_membership(shuffled, recently_answered_ids=set())

        self.assertEqual([q.position_in_set for q in resolved], [1, 2, 3])

    def test_standalone_questions_unaffected_by_set_resolution(self):
        """Regression: questions with no set pass through untouched, regardless of set logic."""
        standalone = [make_question(text="Solo 1"), make_question(text="Solo 2")]

        resolved = resolve_set_membership(standalone, recently_answered_ids=set())

        self.assertEqual({q.id for q in resolved}, {q.id for q in standalone})

    def test_mixed_standalone_and_full_set(self):
        qset, members = self._make_set(n=3)
        standalone = make_question(text="Solo")

        resolved = resolve_set_membership(members + [standalone], recently_answered_ids=set())

        self.assertEqual(len(resolved), 4)
        self.assertIn(standalone.id, {q.id for q in resolved})


# ---------------------------------------------------------------------------
# _format_question image_url embedding — QT-03
# ---------------------------------------------------------------------------

class FormatQuestionImageUrlTest(TestCase):

    def test_standalone_question_uses_its_own_image_url(self):
        q = make_question(image_url="https://example.com/diagram.png")

        formatted = _format_question(q)

        self.assertEqual(formatted["image_url"], "https://example.com/diagram.png")

    def test_standalone_question_without_image_is_none(self):
        q = make_question()

        formatted = _format_question(q)

        self.assertIsNone(formatted["image_url"])

    def test_set_member_question_uses_the_sets_image_url_not_its_own(self):
        qset = QuestionSet.objects.create(
            topic="Employees per Department",
            difficulty="medium",
            directions_text="Study the table.",
            image_url="https://example.com/dilr-table.png",
        )
        q = make_question(set=qset, position_in_set=1, image_url="https://example.com/should-be-ignored.png")

        formatted = _format_question(q)

        self.assertEqual(formatted["image_url"], "https://example.com/dilr-table.png")

    def test_every_member_of_a_set_gets_the_shared_image_url(self):
        qset = QuestionSet.objects.create(
            topic="Employees per Department",
            difficulty="medium",
            directions_text="Study the table.",
            image_url="https://example.com/dilr-table.png",
        )
        members = [
            make_question(text=f"Q{i}", set=qset, position_in_set=i)
            for i in range(1, 4)
        ]

        formatted = [_format_question(q) for q in members]

        self.assertTrue(all(f["image_url"] == "https://example.com/dilr-table.png" for f in formatted))
