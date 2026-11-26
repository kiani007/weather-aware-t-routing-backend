import logging
import time
import uuid

from django.http import HttpRequest, HttpResponse

from .context import request_id_var

logger = logging.getLogger("apps.core.requests")

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.request_id = request_id
        request_id_var.set(request_id)
        response = self.get_response(request)
        response[REQUEST_ID_HEADER] = request_id
        return response


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        started = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(
            level,
            "%s %s -> %s (%.0f ms)",
            request.method,
            request.get_full_path(),
            response.status_code,
            elapsed_ms,
        )
        response["Server-Timing"] = f"app;dur={elapsed_ms:.0f}"
        return response
