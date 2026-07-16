from .settings import *  # noqa: F401, F403

# Use the enrollment-only URL conf so the system check doesn't try to import
# notifications.views (which pulls in torch/numpy at module level).
ROOT_URLCONF = 'enrollments.test_urls'
