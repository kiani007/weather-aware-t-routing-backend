import hashlib
import logging
from typing import Protocol

from django.core.cache import cache

from apps.core.exceptions import ExternalServiceError

from .clients import OpenMeteoGeocodingClient, PhotonClient
from .domain import Place

logger = logging.getLogger(__name__)

CACHE_SECONDS = 60 * 60 * 24
# After a provider fails, skip it for a while so each keystroke doesn't wait for it to time out again
PROVIDER_COOLDOWN_SECONDS = 10 * 60


class GeocodingClient(Protocol):
    name: str

    def search(self, query: str, limit: int) -> list[Place]: ...


class GeocodingService:
    """Searches places with the first available provider, falling back to the next one if it fails."""

    def __init__(self, clients: list[GeocodingClient] | None = None):
        self.clients = clients or [PhotonClient(), OpenMeteoGeocodingClient()]

    def search(self, query: str, limit: int = 5) -> list[Place]:
        normalized = " ".join(query.lower().split())
        key = "geocode:" + hashlib.sha1(f"{normalized}|{limit}".encode()).hexdigest()
        cached = cache.get(key)
        if cached is not None:
            return cached
        places = self._unique(self._search_providers(normalized, limit))
        cache.set(key, places, CACHE_SECONDS)
        return places

    def _search_providers(self, query: str, limit: int) -> list[Place]:
        available = [client for client in self.clients if not cache.get(_cooldown_key(client))]
        # If every provider is cooling down, try them all again rather than fail without asking
        error: ExternalServiceError | None = None
        for client in available or self.clients:
            try:
                return client.search(query, limit)
            except ExternalServiceError as exc:
                logger.warning("Geocoder %s failed; trying the next provider", client.name)
                cache.set(_cooldown_key(client), True, PROVIDER_COOLDOWN_SECONDS)
                error = exc
        raise error or ExternalServiceError("Place search is unavailable. Please retry shortly.")

    @staticmethod
    def _unique(places: list[Place]) -> list[Place]:
        seen: set[str] = set()
        result = []
        for place in places:
            if place.label not in seen:
                seen.add(place.label)
                result.append(place)
        return result


def _cooldown_key(client: GeocodingClient) -> str:
    return f"geocode:cooldown:{client.name}"
