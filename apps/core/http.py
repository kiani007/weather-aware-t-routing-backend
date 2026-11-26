import logging
import time
from typing import Any

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


class JsonHttpClient:
    """Thin requests wrapper with pooling, retries, timeouts and structured logging."""

    def __init__(self, base_url: str, service_name: str):
        config = settings.EXTERNAL_APIS
        self.base_url = base_url.rstrip("/")
        self.service_name = service_name
        self.timeout = config["TIMEOUT_SECONDS"]
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config["USER_AGENT"], "Accept": "application/json"})
        retry = Retry(
            total=config["RETRIES"],
            backoff_factor=0.5,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=("GET",),
            respect_retry_after_header=False,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=16)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        started = time.perf_counter()
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            if response.status_code == 429:
                logger.error("%s rate limit reached: %s", self.service_name, response.text[:200])
                raise ExternalServiceError(f"{self.service_name} rate limit reached. Please try again later.")
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.error("%s request failed: %s", self.service_name, exc)
            raise ExternalServiceError(f"{self.service_name} is unavailable. Please retry shortly.") from exc
        logger.info("%s GET %s (%.0f ms)", self.service_name, path, (time.perf_counter() - started) * 1000)
        return payload
