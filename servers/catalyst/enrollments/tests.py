import uuid
import datetime
import unittest.mock
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from users.models import User
from enrollments.models import CourseEnrollment, UserCourseProfile
from enrollments.service import compute_mastery, update_profile_after_submission
from roadmap.models import DailySession

# Minimal settings override for tests:
# - Strip CloudflareShieldMiddleware (no shield secret needed)
# - Use a local URL conf so the system check doesn't import notifications
#   (qloo_service imports torch/numpy at module level — 2GB of deps we don't need)
_TEST_MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]
_TEST_URLS = 'enrollments.test_urls'


def _make_user(suffix=''):
    return User.objects.create(
        email=f"enroll_{suffix or uuid.uuid4().hex[:8]}@example.com",
        name="Test User",
    )


@override_settings(MIDDLEWARE=_TEST_MIDDLEWARE, ROOT_URLCONF=_TEST_URLS)
class EnrollmentCapTests(TestCase):
    """
    Integration tests: all requests hit the real POST /api/enrollments/ view.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = _make_user()
        self.client.force_authenticate(user=self.user)

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_first_enrollment_returns_201(self):
        resp = self.client.post('/api/enrollments/', {'course': 'OS'})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['course'], 'OS')
        self.assertEqual(resp.json()['status'], 'active')

    def test_three_enrollments_all_succeed(self):
        for course in ['OS', 'System Design', 'DBMS']:
            resp = self.client.post('/api/enrollments/', {'course': course})
            self.assertEqual(resp.status_code, 201, f"Expected 201 for {course}, got {resp.status_code}")

    # ------------------------------------------------------------------
    # 402 cap gate — this is the definition-of-done test
    # ------------------------------------------------------------------

    def test_fourth_enrollment_returns_402(self):
        """
        After 3 active enrollments the endpoint must reject the 4th with
        402 Payment Required and the exact body the ticket specifies.
        """
        for course in ['OS', 'System Design', 'DBMS']:
            r = self.client.post('/api/enrollments/', {'course': course})
            self.assertEqual(r.status_code, 201)

        resp = self.client.post('/api/enrollments/', {'course': 'Algorithms'})

        self.assertEqual(resp.status_code, 402)
        body = resp.json()
        self.assertEqual(body['error'], 'upgrade_required')
        self.assertEqual(body['limit'], 3)

    def test_cap_only_counts_active_enrollments(self):
        """
        A paused enrollment does NOT count toward the 3-slot cap.
        Creating 2 active + 1 paused then enrolling a 4th should succeed.
        """
        for course in ['OS', 'System Design']:
            self.client.post('/api/enrollments/', {'course': course})

        # Manually pause one to simulate the paused state
        CourseEnrollment.objects.filter(
            user=self.user, course='OS'
        ).update(status=CourseEnrollment.Status.PAUSED)

        # Add a third active enrollment
        resp3 = self.client.post('/api/enrollments/', {'course': 'DBMS'})
        self.assertEqual(resp3.status_code, 201)

        # Now active=2 (System Design, DBMS), paused=1 (OS) — 4th active should succeed
        resp4 = self.client.post('/api/enrollments/', {'course': 'Algorithms'})
        self.assertEqual(resp4.status_code, 201)

    # ------------------------------------------------------------------
    # Duplicate course
    # ------------------------------------------------------------------

    def test_duplicate_course_returns_409(self):
        self.client.post('/api/enrollments/', {'course': 'OS'})
        resp = self.client.post('/api/enrollments/', {'course': 'OS'})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()['error'], 'already_enrolled')

    # ------------------------------------------------------------------
    # Missing body
    # ------------------------------------------------------------------

    def test_missing_course_field_returns_400(self):
        resp = self.client.post('/api/enrollments/', {})
        self.assertEqual(resp.status_code, 400)

    # ------------------------------------------------------------------
    # Per-user isolation: another user's enrollments don't affect the cap
    # ------------------------------------------------------------------

    def test_cap_is_per_user(self):
        other = _make_user('other')
        other_client = APIClient()
        other_client.force_authenticate(user=other)

        # Fill other user's cap
        for course in ['OS', 'System Design', 'DBMS']:
            other_client.post('/api/enrollments/', {'course': course})

        # Current user has 0 enrollments — their first should still be 201
        resp = self.client.post('/api/enrollments/', {'course': 'OS'})
        self.assertEqual(resp.status_code, 201)


@override_settings(MIDDLEWARE=_TEST_MIDDLEWARE, ROOT_URLCONF=_TEST_URLS)
class ComputeMasteryTests(TestCase):
    """Pure-function tests — no DB."""

    def test_new_when_attempted_lt_3(self):
        self.assertEqual(compute_mastery(2, 2), "new")
        self.assertEqual(compute_mastery(0, 0), "new")

    def test_developing_when_accuracy_below_50(self):
        self.assertEqual(compute_mastery(1, 3), "developing")   # 33%

    def test_proficient_when_50_to_79(self):
        self.assertEqual(compute_mastery(2, 3), "proficient")   # 66%

    def test_mastered_when_80_plus_and_5_attempts(self):
        self.assertEqual(compute_mastery(4, 5), "mastered")     # 80%

    def test_proficient_not_mastered_if_fewer_than_5_attempts(self):
        # 100% accuracy but only 4 attempts → proficient, not mastered
        self.assertEqual(compute_mastery(4, 4), "proficient")


@override_settings(MIDDLEWARE=_TEST_MIDDLEWARE, ROOT_URLCONF=_TEST_URLS)
class UserCourseProfileTests(TestCase):

    def _make_enrollment(self, course='OS'):
        user = _make_user()
        return CourseEnrollment.objects.create(user=user, course=course)

    def test_profile_created_automatically_on_enrollment(self):
        enrollment = self._make_enrollment()
        profile = UserCourseProfile.objects.get(enrollment=enrollment)
        self.assertEqual(profile.topic_accuracy, {})
        self.assertEqual(profile.weekly_sessions_completed, 0)
        self.assertIsNone(profile.weekly_accuracy)

    def test_profile_update_constant_query_count(self):
        """
        Profile update must cost 4 queries regardless of historical topic depth.
        (SAVEPOINT + SELECT FOR UPDATE + UPDATE + RELEASE — constant by construction.)
        """
        enrollment = self._make_enrollment()
        profile = UserCourseProfile.objects.get(enrollment=enrollment)
        # Pre-populate 20 historical topics
        profile.topic_accuracy = {
            f"topic_{i}": {"correct": 5, "attempted": 10, "mastery": "proficient"}
            for i in range(20)
        }
        profile.save(update_fields=["topic_accuracy", "last_updated"])

        session_stats = {
            "Processes": {"correct": 3, "answered": 4},
            "Scheduling": {"correct": 2, "answered": 4},
        }
        with self.assertNumQueries(4):  # SAVEPOINT + SELECT FOR UPDATE + UPDATE + RELEASE
            update_profile_after_submission(
                enrollment_id=enrollment.id,
                topic_stats=session_stats,
                session_accuracy=0.625,
            )

        profile.refresh_from_db()
        self.assertEqual(profile.topic_accuracy["Processes"]["correct"], 3)
        self.assertEqual(profile.topic_accuracy["Processes"]["attempted"], 4)
        self.assertEqual(profile.topic_accuracy["Processes"]["mastery"], "proficient")  # 3/4 = 75%
        # 20 historical topics untouched
        self.assertIn("topic_0", profile.topic_accuracy)
        self.assertEqual(profile.topic_accuracy["topic_0"]["correct"], 5)

    def test_proficient_mastery_after_update(self):
        enrollment = self._make_enrollment()
        session_stats = {"Processes": {"correct": 3, "answered": 4}}
        update_profile_after_submission(
            enrollment_id=enrollment.id,
            topic_stats=session_stats,
            session_accuracy=0.75,
        )
        profile = UserCourseProfile.objects.get(enrollment=enrollment)
        self.assertEqual(profile.topic_accuracy["Processes"]["mastery"], "proficient")

    def test_weekly_sessions_increments_twice(self):
        enrollment = self._make_enrollment()
        stats = {"Processes": {"correct": 3, "answered": 5}}
        update_profile_after_submission(enrollment_id=enrollment.id, topic_stats=stats, session_accuracy=0.6)
        update_profile_after_submission(enrollment_id=enrollment.id, topic_stats=stats, session_accuracy=0.8)

        profile = UserCourseProfile.objects.get(enrollment=enrollment)
        self.assertEqual(profile.weekly_sessions_completed, 2)

    def test_weekly_accuracy_simple_average(self):
        enrollment = self._make_enrollment()
        stats = {"T": {"correct": 1, "answered": 1}}
        update_profile_after_submission(enrollment_id=enrollment.id, topic_stats=stats, session_accuracy=0.80)
        update_profile_after_submission(enrollment_id=enrollment.id, topic_stats=stats, session_accuracy=0.60)

        profile = UserCourseProfile.objects.get(enrollment=enrollment)
        self.assertAlmostEqual(profile.weekly_accuracy, 0.70, places=5)

    def test_weekly_reset_on_new_week(self):
        enrollment = self._make_enrollment()
        # Simulate two sessions completed last week
        stats = {"T": {"correct": 2, "answered": 4}}
        update_profile_after_submission(enrollment_id=enrollment.id, topic_stats=stats, session_accuracy=0.5)
        update_profile_after_submission(enrollment_id=enrollment.id, topic_stats=stats, session_accuracy=0.5)

        # Manually backdate last_updated to the previous ISO week
        last_week = timezone.now() - datetime.timedelta(weeks=1)
        UserCourseProfile.objects.filter(enrollment=enrollment).update(last_updated=last_week)

        # Submit a new session (should trigger reset)
        update_profile_after_submission(
            enrollment_id=enrollment.id,
            topic_stats={"T": {"correct": 3, "answered": 5}},
            session_accuracy=0.6,
        )

        profile = UserCourseProfile.objects.get(enrollment=enrollment)
        # Counter reset then incremented once for the new week's session
        self.assertEqual(profile.weekly_sessions_completed, 1)
        self.assertAlmostEqual(profile.weekly_accuracy, 0.6, places=5)


@override_settings(MIDDLEWARE=_TEST_MIDDLEWARE, ROOT_URLCONF=_TEST_URLS)
class SubmissionAnalysisTests(TestCase):
    """PERF-02 — per-topic mastery breakdown and weekly progress in submit response."""

    def _make_enrollment(self, course='OS'):
        user = _make_user()
        return CourseEnrollment.objects.create(user=user, course=course)

    def _call_update(self, enrollment, topic_stats, session_accuracy=0.7):
        return update_profile_after_submission(
            enrollment_id=enrollment.id,
            topic_stats=topic_stats,
            session_accuracy=session_accuracy,
        )

    # ------------------------------------------------------------------
    # mastery_changed detection
    # ------------------------------------------------------------------

    def test_mastery_changed_new_to_proficient(self):
        """
        Topic starts with no history (mastery=new).
        3 correct out of 4 → proficient. mastery_changed must be True.
        """
        enrollment = self._make_enrollment()
        result = self._call_update(
            enrollment,
            topic_stats={"Processes": {"correct": 3, "answered": 4}},
            session_accuracy=0.75,
        )

        breakdown = result["topic_breakdown"]
        self.assertEqual(len(breakdown), 1)
        topic = breakdown[0]
        self.assertEqual(topic["topic"], "Processes")
        self.assertEqual(topic["mastery"], "proficient")
        self.assertEqual(topic["previous_mastery"], "new")
        self.assertTrue(topic["mastery_changed"])

    def test_mastery_unchanged_stays_developing(self):
        enrollment = self._make_enrollment()
        # First session: 1/3 → developing
        self._call_update(enrollment, {"Scheduling": {"correct": 1, "answered": 3}}, 0.33)
        # Second session: 1/3 more → still developing
        result = self._call_update(enrollment, {"Scheduling": {"correct": 1, "answered": 3}}, 0.33)

        topic = result["topic_breakdown"][0]
        self.assertEqual(topic["previous_mastery"], "developing")
        self.assertEqual(topic["mastery"], "developing")
        self.assertFalse(topic["mastery_changed"])

    # ------------------------------------------------------------------
    # weekly_progress
    # ------------------------------------------------------------------

    def test_weekly_accuracy_simple_average_across_two_sessions(self):
        enrollment = self._make_enrollment()
        self._call_update(enrollment, {"T": {"correct": 1, "answered": 1}}, session_accuracy=0.80)
        result = self._call_update(enrollment, {"T": {"correct": 1, "answered": 1}}, session_accuracy=0.60)

        wp = result["weekly_progress"]
        self.assertEqual(wp["sessions_completed"], 2)
        self.assertAlmostEqual(wp["weekly_accuracy"], 0.70, places=4)

    def test_accuracy_delta_null_on_first_week(self):
        enrollment = self._make_enrollment()
        result = self._call_update(enrollment, {"T": {"correct": 3, "answered": 5}}, 0.6)
        self.assertIsNone(result["weekly_progress"]["accuracy_delta_vs_last_week"])

    def test_accuracy_delta_computed_after_weekly_reset(self):
        """
        Sessions completed last week → weekly reset fires on this week's first session.
        delta must compare this session's accuracy against last week's average.
        """
        enrollment = self._make_enrollment()
        # Simulate two sessions last week: avg = 0.70
        self._call_update(enrollment, {"T": {"correct": 1, "answered": 1}}, session_accuracy=0.80)
        self._call_update(enrollment, {"T": {"correct": 1, "answered": 1}}, session_accuracy=0.60)

        # Backdate last_updated to force a weekly reset on the next call
        last_week = timezone.now() - datetime.timedelta(weeks=1)
        UserCourseProfile.objects.filter(enrollment=enrollment).update(last_updated=last_week)

        # New week: one session at 0.80
        result = self._call_update(enrollment, {"T": {"correct": 1, "answered": 1}}, session_accuracy=0.80)

        wp = result["weekly_progress"]
        self.assertEqual(wp["sessions_completed"], 1)
        self.assertAlmostEqual(wp["weekly_accuracy"], 0.80, places=4)
        # 0.80 (this week) − 0.70 (last week avg) = +0.10
        self.assertIsNotNone(wp["accuracy_delta_vs_last_week"])
        self.assertAlmostEqual(wp["accuracy_delta_vs_last_week"], 0.10, places=4)

    def test_no_enrollment_returns_empty_analysis(self):
        """update_profile_after_submission returns {} for unknown enrollment_id."""
        import uuid
        result = update_profile_after_submission(
            enrollment_id=uuid.uuid4(),
            topic_stats={"T": {"correct": 1, "answered": 2}},
            session_accuracy=0.5,
        )
        self.assertEqual(result, {})


@override_settings(MIDDLEWARE=_TEST_MIDDLEWARE, ROOT_URLCONF=_TEST_URLS)
class GetTodaySessionTests(TestCase):
    """
    GEN-02 — synchronous generation with timeout fallback.

    These tests mock generate_daily_session so they never touch LLM or Qdrant.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('gen02')
        self.client.force_authenticate(user=self.user)
        self.enrollment = CourseEnrollment.objects.create(user=self.user, course='OS')

    def _make_ready_session(self):
        import datetime
        from roadmap.models import DailySession
        return DailySession.objects.create(
            user=self.user,
            enrollment=self.enrollment,
            subject='OS',
            date=datetime.date.today(),
            payload_json={
                "sessionId": "abc",
                "subject": "OS",
                "questionCount": 5,
                "estimatedMinutes": 6,
                "weeklyProgress": 0,
                "bloomsRange": {"min": 1, "max": 3},
                "overallAccuracy": 0,
                "focusAreas": [],
            },
            status='READY',
        )

    def test_ready_session_returned_without_generation(self):
        """Fast path: existing READY session should not call generate_daily_session."""
        self._make_ready_session()

        with unittest.mock.patch(
            'roadmap.views.generate_daily_session',
        ) as mock_gen:
            resp = self.client.get(
                '/api/sessions/today', {'enrollment_id': str(self.enrollment.id)}
            )

        self.assertEqual(resp.status_code, 200)
        mock_gen.assert_not_called()

    def test_ready_session_not_regenerated_on_second_call(self):
        """When a READY session exists, generate_daily_session is never called regardless of call count."""
        self._make_ready_session()

        with unittest.mock.patch('roadmap.views.generate_daily_session') as mock_gen:
            resp1 = self.client.get(
                '/api/sessions/today', {'enrollment_id': str(self.enrollment.id)}
            )
            resp2 = self.client.get(
                '/api/sessions/today', {'enrollment_id': str(self.enrollment.id)}
            )

        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)
        mock_gen.assert_not_called()

    def test_slow_generation_returns_202(self):
        """If generation exceeds the timeout, endpoint returns 202 preparing."""
        import time as _time

        def _slow_generate(enrollment):
            _time.sleep(15)  # longer than _SYNC_GEN_TIMEOUT_SECONDS=9
            return {}, None

        with unittest.mock.patch(
            'roadmap.views.generate_daily_session', side_effect=_slow_generate
        ), unittest.mock.patch(
            'roadmap.views._SYNC_GEN_TIMEOUT_SECONDS', 1
        ):
            resp = self.client.get(
                '/api/sessions/today', {'enrollment_id': str(self.enrollment.id)}
            )

        self.assertEqual(resp.status_code, 202)
        self.assertEqual(resp.json(), {'status': 'preparing'})

    def test_missing_enrollment_id_returns_400(self):
        resp = self.client.get('/api/sessions/today')
        self.assertEqual(resp.status_code, 400)

    def test_wrong_enrollment_id_returns_404(self):
        resp = self.client.get(
            '/api/sessions/today', {'enrollment_id': str(uuid.uuid4())}
        )
        self.assertEqual(resp.status_code, 404)

    def test_paused_enrollment_returns_403(self):
        self.enrollment.status = 'paused'
        self.enrollment.save(update_fields=['status'])
        resp = self.client.get(
            '/api/sessions/today', {'enrollment_id': str(self.enrollment.id)}
        )
        self.assertEqual(resp.status_code, 403)


@override_settings(MIDDLEWARE=_TEST_MIDDLEWARE, ROOT_URLCONF=_TEST_URLS)
class DailySessionEnrollmentFKTests(TestCase):
    """
    Verifies the schema contract: DailySession.enrollment is nullable.
    """

    def test_enrollment_fk_is_nullable(self):
        field = DailySession._meta.get_field('enrollment')
        self.assertTrue(field.null, "DailySession.enrollment must have null=True")
        self.assertTrue(field.blank, "DailySession.enrollment must have blank=True")

    def test_daily_session_can_be_created_without_enrollment(self):
        user = _make_user('ds')
        import datetime
        session = DailySession.objects.create(
            user=user,
            subject='OS',
            date=datetime.date.today(),
            payload_json={},
        )
        self.assertIsNone(session.enrollment_id)
