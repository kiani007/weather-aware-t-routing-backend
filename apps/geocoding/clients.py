from django.conf import settings

from apps.core.http import JsonHttpClient

from .domain import Place


class PhotonClient:
    """OpenStreetMap-based geocoder by Komoot (free, keyless)."""

    LABEL_FIELDS = ("name", "city", "state", "country")

    def __init__(self, http: JsonHttpClient | None = None):
        self.http = http or JsonHttpClient(settings.EXTERNAL_APIS["PHOTON_BASE_URL"], "Photon geocoder")

    def search(self, query: str, limit: int) -> list[Place]:
        payload = self.http.get("/api/", params={"q": query, "limit": limit, "lang": "en"})
        return [self._to_place(feature) for feature in payload.get("features", [])]

    def _to_place(self, feature: dict) -> Place:
        props = feature.get("properties", {})
        lon, lat = feature["geometry"]["coordinates"]
        parts: list[str] = []
        for field in self.LABEL_FIELDS:
            value = props.get(field)
            if value and value not in parts:
                parts.append(value)
        return Place(label=", ".join(parts) or f"{lat:.4f}, {lon:.4f}", lat=lat, lon=lon)
