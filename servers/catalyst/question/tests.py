import uuid
from django.test import TestCase
from question.models import EnrichmentStatus, Question


class QuestionExplanationFieldTest(TestCase):
    def _make_question(self, **kwargs):
        defaults = dict(
            topic="Algebra",
            subject="Mathematics",
            difficulty=3,
            options=["A", "B", "C", "D"],
            correct_index=0,
            text="What is 2 + 2?",
        )
        defaults.update(kwargs)
        return Question.objects.create(**defaults)

    def test_explanation_defaults_to_null(self):
        q = self._make_question()
        self.assertIsNone(q.explanation)

    def test_explanation_can_be_stored_and_retrieved(self):
        text = "The correct answer is A because 2 + 2 = 4."
        q = self._make_question(explanation=text)
        q.refresh_from_db()
        self.assertEqual(q.explanation, text)

    def test_explanation_can_be_updated(self):
        q = self._make_question()
        q.explanation = "Updated explanation."
        q.save(update_fields=["explanation"])
        q.refresh_from_db()
        self.assertEqual(q.explanation, "Updated explanation.")

    def test_question_without_explanation_is_valid(self):
        """Existing questions not yet enriched by the FastAPI service are still valid."""
        q = self._make_question(explanation=None)
        self.assertIsNone(q.explanation)
        self.assertEqual(q.text, "What is 2 + 2?")


class EnrichmentStatusTransitionTest(TestCase):
    def _make_question(self, status=EnrichmentStatus.RAW):
        return Question.objects.create(
            topic="Algebra",
            subject="Mathematics",
            difficulty=3,
            options=["A", "B", "C", "D"],
            correct_index=0,
            text="What is 2 + 2?",
            enrichment_status=status,
        )

    # --- defaults ---

    def test_new_question_defaults_to_raw(self):
        q = self._make_question()
        self.assertEqual(q.enrichment_status, EnrichmentStatus.RAW)

    def test_enrichment_attempts_defaults_to_zero(self):
        q = self._make_question()
        self.assertEqual(q.enrichment_attempts, 0)

    def test_enriched_at_defaults_to_null(self):
        q = self._make_question()
        self.assertIsNone(q.enriched_at)

    # --- happy-path transitions ---

    def test_raw_to_pending(self):
        q = self._make_question(EnrichmentStatus.RAW)
        q.transition_status(EnrichmentStatus.PENDING_ENRICHMENT)
        q.refresh_from_db()
        self.assertEqual(q.enrichment_status, EnrichmentStatus.PENDING_ENRICHMENT)

    def test_pending_to_enriching(self):
        q = self._make_question(EnrichmentStatus.PENDING_ENRICHMENT)
        q.transition_status(EnrichmentStatus.ENRICHING)
        q.refresh_from_db()
        self.assertEqual(q.enrichment_status, EnrichmentStatus.ENRICHING)

    def test_enriching_to_enriched_sets_enriched_at(self):
        q = self._make_question(EnrichmentStatus.ENRICHING)
        q.transition_status(EnrichmentStatus.ENRICHED)
        q.refresh_from_db()
        self.assertEqual(q.enrichment_status, EnrichmentStatus.ENRICHED)
        self.assertIsNotNone(q.enriched_at)

    def test_enriching_to_failed(self):
        q = self._make_question(EnrichmentStatus.ENRICHING)
        q.transition_status(EnrichmentStatus.FAILED)
        q.refresh_from_db()
        self.assertEqual(q.enrichment_status, EnrichmentStatus.FAILED)

    def test_failed_to_pending(self):
        q = self._make_question(EnrichmentStatus.FAILED)
        q.transition_status(EnrichmentStatus.PENDING_ENRICHMENT)
        q.refresh_from_db()
        self.assertEqual(q.enrichment_status, EnrichmentStatus.PENDING_ENRICHMENT)

    def test_pending_back_to_raw(self):
        q = self._make_question(EnrichmentStatus.PENDING_ENRICHMENT)
        q.transition_status(EnrichmentStatus.RAW)
        q.refresh_from_db()
        self.assertEqual(q.enrichment_status, EnrichmentStatus.RAW)

    # --- illegal transitions ---

    def test_enriched_to_raw_is_blocked(self):
        q = self._make_question(EnrichmentStatus.ENRICHED)
        with self.assertRaises(ValueError):
            q.transition_status(EnrichmentStatus.RAW)

    def test_enriched_to_pending_is_blocked(self):
        q = self._make_question(EnrichmentStatus.ENRICHED)
        with self.assertRaises(ValueError):
            q.transition_status(EnrichmentStatus.PENDING_ENRICHMENT)

    def test_raw_to_enriched_is_blocked(self):
        q = self._make_question(EnrichmentStatus.RAW)
        with self.assertRaises(ValueError):
            q.transition_status(EnrichmentStatus.ENRICHED)

    def test_illegal_transition_does_not_persist(self):
        """DB row must be unchanged after a rejected transition."""
        q = self._make_question(EnrichmentStatus.ENRICHED)
        with self.assertRaises(ValueError):
            q.transition_status(EnrichmentStatus.RAW)
        q.refresh_from_db()
        self.assertEqual(q.enrichment_status, EnrichmentStatus.ENRICHED)