import logging
import time
from uuid import uuid4

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger("story-consistency-agent")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started_at = time.perf_counter()
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_id=%s path=%s method=%s status=%s duration_ms=%s",
            request_id,
            request.url.path,
            request.method,
            response.status_code,
            duration_ms,
        )
        return response

app = FastAPI(title=settings.app_name)
app.add_middleware(RequestLoggingMiddleware)
app.include_router(router, prefix=settings.api_prefix)
