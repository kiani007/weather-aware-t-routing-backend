import time
from unittest import mock

import requests
from django.test import SimpleTestCase

from apps.core.exceptions import ExternalServiceError
from apps.core.http import JsonHttpClient


def http_response(status: int, body: bytes = b"{}", headers: dict | None = None) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response._content = body
    response.headers.update(headers or {})
    response.url = "https://example.test/v1/forecast"
    return response


class JsonHttpClientTests(SimpleTestCase):
    def setUp(self):
        self.client = JsonHttpClient("https://example.test", "Open-Meteo weather")

    def test_returns_parsed_json(self):
        with mock.patch.object(self.client.session, "get", return_value=http_response(200, b'{"ok": true}')):
            self.assertEqual(self.client.get("/v1/forecast"), {"ok": True})

    def test_rate_limit_fails_fast_with_clear_message(self):
        limited = http_response(429, b'{"reason": "Daily API request limit exceeded."}', {"Retry-After": "31202"})
        with mock.patch.object(self.client.session, "get", return_value=limited):
            started = time.perf_counter()
            with self.assertRaisesMessage(ExternalServiceError, "Open-Meteo weather rate limit reached"):
                self.client.get("/v1/forecast")
        self.assertLess(time.perf_counter() - started, 1)

    def test_retry_policy_never_waits_on_retry_after(self):
        retry = self.client.session.get_adapter("https://example.test").max_retries
        self.assertFalse(retry.respect_retry_after_header)
        self.assertNotIn(429, retry.status_forcelist)

    def test_server_errors_and_timeouts_become_external_service_errors(self):
        for failure in (http_response(503), requests.Timeout("timed out")):
            with self.subTest(failure=failure):
                patch = {"return_value": failure} if isinstance(failure, requests.Response) else {"side_effect": failure}
                with mock.patch.object(self.client.session, "get", **patch):
                    with self.assertRaisesMessage(ExternalServiceError, "Open-Meteo weather is unavailable"):
                        self.client.get("/v1/forecast")
