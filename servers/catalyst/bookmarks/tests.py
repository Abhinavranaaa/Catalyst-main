import uuid

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from bookmarks.models import Bookmark, FlagSubmission
from users.models import User

# Same trick payments/tests.py and enrollments/tests.py use: strip
# CloudflareShieldMiddleware (no shield secret needed in tests) and point at
# a local urlconf so the system check doesn't drag in notifications' heavy
# deps (torch/numpy).
_TEST_MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]
_TEST_URLS = 'bookmarks.test_urls'


def _make_user(suffix=''):
    return User.objects.create(
        email=f"bm_{suffix or uuid.uuid4().hex[:8]}@example.com",
        name="Test User",
    )


@override_settings(MIDDLEWARE=_TEST_MIDDLEWARE, ROOT_URLCONF=_TEST_URLS)
class BookmarkTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user()
        self.client.force_authenticate(user=self.user)
        self.question_id = str(uuid.uuid4())

    def test_create_bookmark(self):
        resp = self.client.post("/api/bookmarks/", {
            "question_id": self.question_id,
            "reason": "new_concept",
        })
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["question_id"], self.question_id)
        self.assertEqual(body["reason"], "new_concept")
        self.assertIsNone(body["reason_text"])
        self.assertTrue(
            Bookmark.objects.filter(
                id=body["id"], user_id=str(self.user.id), question_id=self.question_id
            ).exists()
        )

    def test_reason_text_is_optional_and_can_be_provided(self):
        resp = self.client.post("/api/bookmarks/", {
            "question_id": self.question_id,
            "reason": "curious",
            "reason_text": "this one tripped me up",
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["reason_text"], "this one tripped me up")

    def test_invalid_reason_rejected_with_400(self):
        resp = self.client.post("/api/bookmarks/", {
            "question_id": self.question_id,
            "reason": "not_a_real_reason",
        })
        self.assertEqual(resp.status_code, 400)

    def test_owner_can_delete_own_bookmark(self):
        bookmark = Bookmark.objects.create(
            user_id=str(self.user.id), question_id=self.question_id, reason="curious"
        )
        resp = self.client.delete(f"/api/bookmarks/{bookmark.id}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Bookmark.objects.filter(id=bookmark.id).exists())

    def test_non_owner_delete_is_rejected_not_500(self):
        other_user = _make_user("other")
        bookmark = Bookmark.objects.create(
            user_id=str(other_user.id), question_id=self.question_id, reason="curious"
        )
        resp = self.client.delete(f"/api/bookmarks/{bookmark.id}/")
        self.assertIn(resp.status_code, (403, 404))
        self.assertTrue(Bookmark.objects.filter(id=bookmark.id).exists())

    def test_delete_nonexistent_bookmark_is_404_not_500(self):
        resp = self.client.delete(f"/api/bookmarks/{uuid.uuid4()}/")
        self.assertEqual(resp.status_code, 404)

    def test_list_returns_only_own_bookmarks(self):
        other_user = _make_user("other2")
        mine = Bookmark.objects.create(
            user_id=str(self.user.id), question_id=self.question_id, reason="curious"
        )
        Bookmark.objects.create(
            user_id=str(other_user.id), question_id=str(uuid.uuid4()), reason="new_concept"
        )

        resp = self.client.get("/api/bookmarks/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["id"], str(mine.id))

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get("/api/bookmarks/")
        self.assertEqual(resp.status_code, 403)


@override_settings(MIDDLEWARE=_TEST_MIDDLEWARE, ROOT_URLCONF=_TEST_URLS)
class FlagSubmissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user()
        self.client.force_authenticate(user=self.user)
        self.question_id = str(uuid.uuid4())

    def test_create_flag_with_multiple_categories_persists_full_array(self):
        resp = self.client.post("/api/flags/", {
            "question_id": self.question_id,
            "categories": ["confusing_wording", "something_else", "answer_or_explanation_wrong"],
            "description": "multiple things wrong here",
        })
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(
            body["categories"],
            ["confusing_wording", "something_else", "answer_or_explanation_wrong"],
        )

        flag = FlagSubmission.objects.get(id=body["id"])
        self.assertEqual(
            flag.categories,
            ["confusing_wording", "something_else", "answer_or_explanation_wrong"],
        )

    def test_description_is_optional(self):
        resp = self.client.post("/api/flags/", {
            "question_id": self.question_id,
            "categories": ["something_else"],
        })
        self.assertEqual(resp.status_code, 201)
        self.assertIsNone(resp.json()["description"])

    def test_categories_optional_defaults_to_empty_list(self):
        resp = self.client.post("/api/flags/", {"question_id": self.question_id})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["categories"], [])

    def test_invalid_category_rejected_with_clean_400(self):
        resp = self.client.post("/api/flags/", {
            "question_id": self.question_id,
            "categories": ["confusing_wording", "not_a_real_category"],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(
            FlagSubmission.objects.filter(question_id=self.question_id).exists(),
            "invalid category must not be silently accepted into the array",
        )

    def test_second_flag_on_same_question_by_same_user_creates_distinct_row(self):
        first = self.client.post("/api/flags/", {
            "question_id": self.question_id,
            "categories": ["confusing_wording"],
        })
        second = self.client.post("/api/flags/", {
            "question_id": self.question_id,
            "categories": ["something_else"],
        })

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(
            FlagSubmission.objects.filter(
                question_id=self.question_id, user_id=str(self.user.id)
            ).count(),
            2,
        )

    def test_defaults_to_open_status(self):
        resp = self.client.post("/api/flags/", {
            "question_id": self.question_id,
            "categories": ["something_else"],
        })
        self.assertEqual(resp.json()["status"], "open")

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        resp = self.client.post("/api/flags/", {"question_id": self.question_id})
        self.assertEqual(resp.status_code, 403)
