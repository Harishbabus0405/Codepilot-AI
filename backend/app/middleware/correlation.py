import contextvars
import logging
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.config.settings import settings

# Context variable for request correlation ID
correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="-")


class CorrelationIdFilter(logging.Filter):
    """Logging filter that injects the current request correlation ID into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_ctx.get("-")
        return True


logger = logging.getLogger("codepilot.access")


class CorrelationAndLoggingMiddleware(BaseHTTPMiddleware):
    """
    Production-grade middleware that:
    1. Injects and tracks X-Correlation-ID across the request lifecycle.
    2. Enforces maximum payload size limits to protect against memory exhaustion.
    3. Emits structured access logs with execution durations and response status codes.
    4. Ensures secrets/tokens are never logged.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1. Extract or generate Correlation ID
        cid = request.headers.get("X-Correlation-ID")
        if not cid or not cid.strip():
            cid = str(uuid.uuid4())
        else:
            # Sanitize correlation id: keep alphanumeric and dashes
            cid = "".join(c for c in cid if c.isalnum() or c in "-_")[:64] or str(uuid.uuid4())

        token = correlation_id_ctx.set(cid)
        request.state.correlation_id = cid

        # 2. Enforce Content-Length payload limits
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                cl_int = int(content_length)
                if cl_int > settings.MAX_PAYLOAD_SIZE_BYTES:
                    logger.warning(
                        "Payload too large",
                        extra={"correlation_id": cid, "size": cl_int, "path": request.url.path},
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Payload size {cl_int} bytes exceeds maximum allowed limit of {settings.MAX_PAYLOAD_SIZE_BYTES} bytes."
                        },
                        headers={"X-Correlation-ID": cid},
                    )
            except ValueError:
                pass

        start_time = time.perf_counter()
        try:
            response: Response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            response.headers["X-Correlation-ID"] = cid

            # Log request outcome (excluding noisy health probes from high-volume logs)
            if not request.url.path.endswith("/health"):
                logger.info(
                    f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms) [cid: {cid}]"
                )
            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"Unhandled error processing {request.method} {request.url.path} ({duration_ms}ms) [cid: {cid}]: {exc}",
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error occurred.", "correlation_id": cid},
                headers={"X-Correlation-ID": cid},
            )
        finally:
            correlation_id_ctx.reset(token)
