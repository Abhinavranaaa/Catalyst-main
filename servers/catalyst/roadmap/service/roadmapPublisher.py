# roadmap/services/task_publisher.py

import json
from google.cloud import tasks_v2
from django.conf import settings
import os
from dotenv import load_dotenv
from catalyst.publisher import Publisher
from catalyst.constants import PROJECT_ID, US_CENTRAL1, ROADMAP_QUEUE,SA_EMAIL,ROADMAP_PROCESS_URL
import logging
from django.core.exceptions import ImproperlyConfigured

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..','..'))
logger = logging.getLogger(__name__)
class RoadmapTaskPublisher:

    def __init__(self):
        self.PROJECT_ID=os.getenv(PROJECT_ID)
        self.target_url = os.getenv(ROADMAP_PROCESS_URL)
        self.QUEUE_ID = os.getenv(ROADMAP_QUEUE)
        self.QUEUE_REGION = os.getenv(US_CENTRAL1)
        self.sa_email = os.getenv(SA_EMAIL)
        
        if not all([
            self.PROJECT_ID,
            self.QUEUE_ID,
            self.QUEUE_REGION,
            self.target_url,
            self.sa_email
        ]): raise ImproperlyConfigured("Cloud Tasks config missing")

    def enqueue(self, job_id: str):


        payload = json.dumps({"job_id": job_id}).encode()

        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": self.target_url,
                "headers": {"Content-Type": "application/json"},
                "body": payload,
                "oidc_token": {
                    "service_account_email": self.sa_email,
                    "audience": self.target_url,
                }
            },
            "dispatch_deadline": {
                "seconds": 300
            }
        }
        
        publisher=Publisher(self.QUEUE_REGION,self.QUEUE_ID,self.PROJECT_ID)
        publisher.loadQueueAndPublish(task)
        
        
