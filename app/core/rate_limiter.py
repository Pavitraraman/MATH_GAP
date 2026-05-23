import time
import logging
from collections import defaultdict
from fastapi import HTTPException, Request, status

logger = logging.getLogger("math_gap.rate_limiter")


class SlidingWindowRateLimiter:
    def __init__(self, window_seconds: int = 60, max_requests: int = 100):
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.requests = defaultdict(list)  # Maps key -> list of float timestamps

    async def __call__(self, request: Request):
        """Rates limit active HTTP endpoints using a sliding window algorithm."""
        # 1. Identify client using Authorization token or fall back to remote IP
        client_key = request.headers.get("Authorization") or (request.client.host if request.client else "unknown_ip")
        
        # 2. Check if WebSocket connection upgrade request
        connection_header = request.headers.get("connection", "").lower()
        upgrade_header = request.headers.get("upgrade", "").lower()
        if "upgrade" in connection_header or "websocket" in upgrade_header or request.url.path.startswith("/platform/ws"):
            return  # Allow WebSocket bypass

        now = time.time()
        
        # 3. Clean up timestamps older than the window
        timestamps = self.requests[client_key]
        self.requests[client_key] = [t for t in timestamps if now - t < self.window_seconds]
        
        # 4. Assert rate threshold
        if len(self.requests[client_key]) >= self.max_requests:
            logger.warning("Throttled request from key %s: too many requests.", client_key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.max_requests} requests per {self.window_seconds} seconds.",
            )
            
        self.requests[client_key].append(now)


# Standard default global rate limiter: 100 requests per minute
rate_limiter = SlidingWindowRateLimiter(window_seconds=60, max_requests=100)
