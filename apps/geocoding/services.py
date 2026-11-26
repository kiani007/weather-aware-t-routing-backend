import hashlib

from django.core.cache import cache

from .clients import PhotonClient
from .domain import Place

CACHE_SECONDS = 60 * 60 * 24


class GeocodingService:
    def __init__(self, client: PhotonClient | None = None):
        self.client = client or PhotonClient()

    def search(self, query: str, limit: int = 5) -> list[Place]:
        normalized = " ".join(query.lower().split())
        key = "geocode:" + hashlib.sha1(f"{normalized}|{limit}".encode()).hexdigest()
        cached = cache.get(key)
        if cached is not None:
            return cached
        places = self._unique(self.client.search(normalized, limit))
        cache.set(key, places, CACHE_SECONDS)
        return places

    @staticmethod
    def _unique(places: list[Place]) -> list[Place]:
        seen: set[str] = set()
        result = []
        for place in places:
            if place.label not in seen:
                seen.add(place.label)
                result.append(place)
        return result
