from users.models import User
import logging
from django.http import JsonResponse
from catalyst.constants import *
import os
from dotenv import load_dotenv
from google.cloud import tasks_v2
import json
from datetime import datetime, timedelta
from google.protobuf import timestamp_pb2
import os
from dotenv import load_dotenv
from catalyst.constants import US_CENTRAL1, NOTIFICATION_QUEUE, PROJECT_ID
from catalyst.publisher import Publisher


logger = logging.getLogger(__name__)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..','..'))
QUEUE_REGION = os.getenv(US_CENTRAL1)
QUEUE_ID = os.getenv(NOTIFICATION_QUEUE)
PROJECT_ID = os.getenv(PROJECT_ID)

def batchProcess(request):

    publish = Publisher(QUEUE_REGION,QUEUE_ID,PROJECT_ID)

    logger.info("triggering notification batch")
    batches = iter_user_ids(BATCH_SIZE)
    target_url = os.getenv(PROCESS_URL)
    sa_email = os.getenv(SA_EMAIL)

    successful_batches = 0
    failed_batches = 0
    total_batches = 0
    BASE_DELAY_MINUTES = 20

    for i, batch in enumerate(batches):
        total_batches += 1
        delay_minutes = i * BASE_DELAY_MINUTES

        schedule_time = timestamp_pb2.Timestamp()
        schedule_time.FromDatetime(
            datetime.utcnow() + timedelta(minutes=delay_minutes)
        )

        payload = {"user_ids": batch}

        task = {
            "http_request": {
                "url": target_url,
                "http_method": tasks_v2.HttpMethod.POST,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(payload).encode(),
                "oidc_token": {
                    "service_account_email": sa_email,
                    "audience": target_url,
                },
            },
            "schedule_time": schedule_time,
            "dispatch_deadline": {
                "seconds": 1800
            }
        }

        try:
            publish.loadQueueAndPublish(task)
            successful_batches += 1
        except Exception as e:
            failed_batches += 1
            logger.error(
                f"Failed to publish batch {i} (size: {len(batch)}): {e}"
            )

    status_message = (
        "batches_enqueued"
        if failed_batches == 0
        else "partial_failure_batches_enqueued"
    )

    return JsonResponse({
        "status": status_message,
        "total_batches": total_batches,
        "successful_batches": successful_batches,
        "failed_batches": failed_batches,
        "batch_size": BATCH_SIZE,
    })

        

def iter_user_ids(batch_size):

    qs = (
        User.objects
        .order_by("id")
        .values_list("id", flat=True)
    )
    last_id = None
    while True:
        chunk = qs
        if last_id is not None:
            chunk = chunk.filter(id__gt=last_id)

        batch = list(chunk[:batch_size])
        if not batch:
            break
        last_id = batch[-1]
        yield batch
