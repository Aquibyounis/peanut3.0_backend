import time
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.redis.client import redis_client

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for static/public stuff if needed
        client_ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:global:{client_ip}"
        
        # Simple sliding window counter via Redis
        if redis_client._redis:
            current_time = time.time()
            # Clear old entries
            await redis_client._redis.zremrangebyscore(key, 0, current_time - self.window_seconds)
            # Count current
            request_count = await redis_client._redis.zcard(key)
            
            if request_count >= self.max_requests:
                raise HTTPException(status_code=429, detail="Too many requests")
                
            # Add new request
            await redis_client._redis.zadd(key, {str(current_time): current_time})
            await redis_client._redis.expire(key, self.window_seconds)
            
        return await call_next(request)
