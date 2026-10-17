import time
from collections import defaultdict
from threading import Lock
from fastapi import Request, HTTPException

class InMemoryRateLimiter:
    """
    Sliding window rate limiter to protect Gemini API quota and backend resources.
    """
    def __init__(self, requests_per_minute: int = 10):
        self.rpm = requests_per_minute
        self.window_seconds = 60
        self.records = defaultdict(list)
        self.lock = Lock()

    def check(self, identifier: str):
        now = time.time()
        cutoff = now - self.window_seconds

        with self.lock:
            # Prune timestamps older than window
            timestamps = self.records[identifier]
            self.records[identifier] = [t for t in timestamps if t > cutoff]

            if len(self.records[identifier]) >= self.rpm:
                oldest_in_window = self.records[identifier][0]
                retry_after = int(self.window_seconds - (now - oldest_in_window)) + 1
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Maximum {self.rpm} requests per minute allowed.",
                    headers={"Retry-After": str(max(1, retry_after))}
                )

            self.records[identifier].append(now)

    def reset(self):
        """Used in test suites to clear records."""
        with self.lock:
            self.records.clear()

analyze_rate_limiter = InMemoryRateLimiter(requests_per_minute=10)

def rate_limit_analyze(request: Request):
    """
    FastAPI dependency applying rate limits by client IP or authenticated user.
    """
    client_ip = request.client.host if request.client else "unknown"
    auth_header = request.headers.get("Authorization", "")
    identifier = auth_header if auth_header else client_ip
    analyze_rate_limiter.check(identifier)
