from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import time


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """Small in-memory rate limiter for assessment/demo purposes.

    In production this should be replaced by API gateway, Redis, or WAF-based rate limiting.
    """

    def __init__(self, app, max_requests: int = 120, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        recent_requests = [
            timestamp
            for timestamp in self.clients.get(client_ip, [])
            if now - timestamp < self.window_seconds
        ]

        if len(recent_requests) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

        recent_requests.append(now)
        self.clients[client_ip] = recent_requests
        return await call_next(request)
