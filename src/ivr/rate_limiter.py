import time

class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client
        
    def check_limit(self, caller_id, limit=5, window=60):
        current = int(time.time())
        window_key = f"ratelimit:{caller_id}:{current // window}"
        pipe = self.redis.pipeline()
        pipe.incr(window_key)
        pipe.expire(window_key, window * 2)
        current_count = pipe.execute()[0]
        return current_count <= limit
