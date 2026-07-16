from catalyst.infra.redis import redis_client
import json
import datetime
import logging

logger = logging.getLogger(__name__)


def _json_default(obj):
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class DashBoardCacheService:
    def __init__(self,ttl):
        self.ttl=ttl
        self.cache=redis_client

    def key(self,user_id):
        return f"user:{user_id}:dashboard"
    
    def get(self, user_id):
        logger.info(f'fetching cache for user:{user_id}')
        try:
            raw = self.cache.get(self.key(user_id))
            if not raw:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"cache read failed for user_id{user_id}")
            return None
        

    def set(self, user_id, data):
        try:
            self.cache.set(
                self.key(user_id),
                json.dumps(data, default=_json_default),
                ex=self.ttl
            )
        except Exception as e:
            logger.warning(f"Cache write failed for user{user_id} due to exp{e}")

    def invalidate(self, user_id):
        logger.info(f'invalidating and updating cache for user:{user_id}')
        try:
            self.cache.delete(self.key(user_id))
        except Exception as e:
            logger.warning(f'could not update the cache layer for user_id{user_id}')
    

