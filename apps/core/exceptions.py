import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .context import request_id_var

logger = logging.getLogger(__name__)


class DomainError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "domain_error"
    default_detail = "The request could not be processed."


class ExternalServiceError(DomainError):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_code = "external_service_error"
    default_detail = "An upstream data provider failed to respond."


class NotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "not_found"
    default_detail = "The requested resource was not found."


class UnprocessableError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "unprocessable"
    default_detail = "The request is valid but cannot be fulfilled."


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled error", exc_info=exc)
        return Response(
            _error_body("server_error", "An unexpected error occurred."),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code = getattr(exc, "default_code", "error")
    if isinstance(exc, APIException):
        codes = exc.get_codes()
        code = codes if isinstance(codes, str) else code
    if isinstance(response.data, dict) and set(response.data) == {"detail"}:
        body = _error_body(code, str(response.data["detail"]))
    else:
        body = _error_body("validation_error", "Invalid input.", details=response.data)
    response.data = body
    return response


def _error_body(code: str, message: str, details=None) -> dict:
    body = {"code": code, "message": message, "request_id": request_id_var.get()}
    if details is not None:
        body["details"] = details
    return {"error": body}
