import time
import re
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.config import settings

logger = logging.getLogger("ai_investigator.access")
REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{8,64}$")


def get_trusted_client_ip(request: Request) -> str:
    """
    Derive the client IP address respecting the TRUSTED_PROXY_COUNT configuration.
    If TRUSTED_PROXY_COUNT == 0, never trust X-Forwarded-For and use socket client host.
    """
    fallback = request.client.host if request.client else "127.0.0.1"
    if settings.TRUSTED_PROXY_COUNT <= 0:
        return fallback

    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return fallback

    parts = [p.strip() for p in forwarded.split(",") if p.strip()]
    if not parts:
        return fallback

    # Select client IP by indexing back past trusted reverse proxies
    idx = -settings.TRUSTED_PROXY_COUNT
    if abs(idx) <= len(parts):
        return parts[idx]
    return parts[0]


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware providing Request ID propagation, execution timing, and structured audit logging.
    Strictly redacts sensitive credentials, payloads, and tokens.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Validate or generate request_id
        incoming_id = request.headers.get("x-request-id", "").strip()
        if incoming_id and REQUEST_ID_REGEX.match(incoming_id):
            request_id = incoming_id
        else:
            request_id = f"req_{uuid.uuid4().hex[:16]}"

        request.state.request_id = request_id
        start_time = time.perf_counter()
        client_ip = get_trusted_client_ip(request)

        try:
            response = await call_next(request)
        except Exception:
            # Let global exception handler process and log trace, but measure duration
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            user_id = getattr(request.state, "user_id", "unauthenticated")
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} -> 500 ERROR ({duration_ms}ms) "
                f"client={client_ip} user={user_id}"
            )
            raise

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        user_id = getattr(request.state, "user_id", "unauthenticated")
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms) "
            f"client={client_ip} user={user_id}"
        )

        return response
