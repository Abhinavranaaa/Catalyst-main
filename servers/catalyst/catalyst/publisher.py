from google.cloud import tasks_v2
import logging
logger = logging.getLogger(__name__)
class Publisher:
    def __init__(self,queue_region,q_id,project_id):
        self.queue_region=queue_region
        self.q_id=q_id
        self.project_id=project_id
    
    def loadQueueAndPublish(self,task):
        try:
            client = tasks_v2.CloudTasksClient()
            parent = client.queue_path(
                self.project_id,
                self.queue_region,
                self.q_id
            )
            client.create_task(parent=parent, task=task)
        except Exception as e:
            logger.error(
                f"Failed to publish task {e}"
            )
            raise
