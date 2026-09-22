from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Applies security headers to every HTTP response in accordance with Phase 5 requirements.
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - Referrer-Policy: strict-origin-when-cross-origin
    - Strict-Transport-Security: only in production or HTTPS environments
    - Explicitly omits obsolete X-XSS-Protection
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Standard modern security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"

        # HSTS only when in production or on https request
        is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
        if settings.ENVIRONMENT.lower() == "production" or is_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
