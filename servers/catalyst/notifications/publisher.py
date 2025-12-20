from google.cloud import tasks_v2
import os
from dotenv import load_dotenv
from catalyst.constants import ASIA_SOUTH1, NOTIFICATION_QUEUE, PROJECT_ID


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
QUEUE_REGION = os.getenv(ASIA_SOUTH1)
QUEUE_ID = os.getenv(NOTIFICATION_QUEUE)
PROJECT_ID = os.getenv(PROJECT_ID)


def loadQueueAndPublish(task):
    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(
        PROJECT_ID,
        QUEUE_REGION,
        QUEUE_ID,
    )
    client.create_task(parent=parent, task=task)
