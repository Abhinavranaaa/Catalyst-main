import time
from typing import Tuple
from django.conf import settings
from .RateLimitExceeded import RateLimitExceeded
from upstash_redis import Redis
from ..constants import SLIDING_WINDOW_LUA
import logging
from redis.exceptions import NoScriptError

redis = Redis.from_env()

SCRIPT_SHA = redis.script_load(SLIDING_WINDOW_LUA)

logger = logging.getLogger(__name__)
class SlidingWindowRateLimitter:
    def __init__(self,limit:int,window_sec:int):
        self.limit=limit
        self.window=window_sec
    
    def buildKey(self,user_id:int)->str:
        return f"rate_limit:roadmap:{user_id}"
    
    def check(self,user_id)->Tuple[bool,int]:
        
        key=self.buildKey(user_id)
        now=int(time.time())
        member = f"{user_id}-{time.time_ns()}"

        try:
            result = redis.evalsha(
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





