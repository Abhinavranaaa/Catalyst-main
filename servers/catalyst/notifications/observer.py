# notifications/observers.py

from django.core.mail import send_mail
from catalyst.constants import CATALYST_EMAIL
from .models import WebPushSubscription
from pywebpush import webpush, WebPushException
import json
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from smtplib import SMTPException
import logging 
from .services.qloo_service import get_audience

logger = logging.getLogger(__name__)

class NotificationObserver:
    def send(self, user, message, **kwargs):
        raise NotImplementedError

class EmailObserver(NotificationObserver):
    def send(self, user, message, **kwargs):
        subject = "Your New Learning Notification"

        domain_url = kwargs.get('domain_url', 'https://catalyst-main-1036749949194.asia-south2.run.app')
        user_name = getattr(user, 'name', None) or getattr(user, 'user_name', None) or user.email
        html_content = render_to_string('email/notification.html', {
            'subject': subject,
            'user_name': user_name,
            'message': message,
            'domain_url': domain_url,
        })

        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=CATALYST_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")
        try:
            sent = email.send()
            if sent != 1:
                raise Exception("Email backend did not accept message")
        except SMTPException as e:
            logger.error(f"SMTP failure for {user.email}: {e}")
            raise
        except Exception as e:
            logger.error(f"Email send failed for {user.email}: {e}")
            raise


class PushObserver(NotificationObserver):
    def send(self, user, message, **kwargs):
        subs = WebPushSubscription.objects.filter(user=user)
        for sub in subs:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub.endpoint,
                        "keys": {"p256dh": sub.p256dh, "auth": sub.auth}
                    },
                    ttl=3600,
                    data=json.dumps({
                        "version": 1,
                        "type": "daily_notification",
                        "title": "Catalyst",
                        "body": message
                        }),
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": "mailto:rmitu22@gmail.com","aud":get_audience(sub.endpoint)},
                )
            except WebPushException as e:
                if hasattr(e, "response") and e.response and e.response.status_code in [404, 410]:
                    sub.delete()

class NotificationDistributor:
    def __init__(self):
        self.observers = []

    def register(self, observer):
        self.observers.append(observer)

    def notify(self, user, message, **kwargs):
        for observer in self.observers:
            observer.send(user, message, **kwargs)
