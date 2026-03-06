import time
from typing import Tuple
from django.conf import settings
from .RateLimitExceeded import RateLimitExceeded
from upstash_redis import Redis
from ..constants import SLIDING_WINDOW_LUA
import logging
from redis.exceptions import NoScriptError
from ..infra.redis import redis_client

SCRIPT_SHA = redis_client.script_load(SLIDING_WINDOW_LUA)
# load once per process and while app instantiation

logger = logging.getLogger(__name__)
class SlidingWindowRateLimitter:
    def __init__(self,limit:int,window_sec:int):
        self.limit=limit
        self.window=window_sec
        # injected from infra
        self.redis=redis_client
    
    
    def check(self,user_id)->Tuple[bool,int]:
        
        key=self.buildKey(user_id)
        now=int(time.time())
        member = f"{user_id}-{time.time_ns()}"

        try:
            result = self.redis.evalsha(
                SCRIPT_SHA,
                keys=[key],
                args=[self.limit, self.window, now, member],
            )
        except NoScriptError:
            logger.exception(
                "Redis rate limiter failed",
                extra={"user_id": user_id}
            )
            return True, 0
            

        allowed = bool(result[0])
        current_count = int(result[1])

        if not allowed:
            raise RateLimitExceeded(
                f"Rate limit exceeded. Allowed: {self.limit} per {self.window} seconds."
            )

        return allowed, current_count





