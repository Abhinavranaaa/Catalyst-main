from decimal import Decimal
from types import SimpleNamespace

from django.test import TestCase

from practice.service.processSessionAttempts import _is_attempt_correct


class IsAttemptCorrectTest(TestCase):
    def _mcq_question(self, correct_index=1):
        return SimpleNamespace(response_type="mcq", correct_index=correct_index)

    def _numerical_question(self, correct_value="10.00", tolerance="0.5"):
        return SimpleNamespace(
            response_type="numerical",
            correct_value=Decimal(correct_value),
            tolerance=Decimal(tolerance),
        )

    def test_mcq_correct_selection(self):
        q = self._mcq_question(correct_index=2)
        self.assertTrue(_is_attempt_correct(q, 2, None))

    def test_mcq_incorrect_selection(self):
        q = self._mcq_question(correct_index=2)
        self.assertFalse(_is_attempt_correct(q, 1, None))

    def test_mcq_skipped_returns_none(self):
        q = self._mcq_question(correct_index=2)
        self.assertIsNone(_is_attempt_correct(q, None, None))

    def test_numerical_within_tolerance(self):
        q = self._numerical_question(correct_value="10.00", tolerance="0.5")
        self.assertTrue(_is_attempt_correct(q, None, Decimal("10.5")))

    def test_numerical_exactly_at_tolerance_boundary(self):
        q = self._numerical_question(correct_value="10.00", tolerance="0.5")
        self.assertTrue(_is_attempt_correct(q, None, Decimal("9.5")))

    def test_numerical_just_outside_tolerance(self):
        q = self._numerical_question(correct_value="10.00", tolerance="0.5")
        self.assertFalse(_is_attempt_correct(q, None, Decimal("10.51")))

    def test_numerical_skipped_returns_none(self):
        q = self._numerical_question()
        self.assertIsNone(_is_attempt_correct(q, None, None))

    def test_unhandled_response_type_raises(self):
        q = SimpleNamespace(response_type="freeform")
        with self.assertRaises(ValueError):
            _is_attempt_correct(q, None, None)