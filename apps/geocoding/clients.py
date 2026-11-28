from django.conf import settings

from apps.core.http import JsonHttpClient

from .domain import Place

# Place search backs an autocomplete, and there is a fallback provider:
# give up quickly instead of making the user wait for long retries.
FAST_TIMEOUT = (3.0, 8.0)  # (connect, read) seconds


def _label(parts: list[str | None], lat: float, lon: float) -> str:
    unique: list[str] = []
    for part in parts:
        if part and part not in unique:
            unique.append(part)
    return ", ".join(unique) or f"{lat:.4f}, {lon:.4f}"


class PhotonClient:
    """OpenStreetMap-based geocoder by Komoot (free, keyless). Primary provider: finds addresses as well as places."""

    name = "photon"
    LABEL_FIELDS = ("name", "city", "state", "country")

    def __init__(self, http: JsonHttpClient | None = None):
        self.http = http or JsonHttpClient(
            settings.EXTERNAL_APIS["PHOTON_BASE_URL"], "Photon geocoder", timeout=FAST_TIMEOUT, retries=0
        )

    def search(self, query: str, limit: int) -> list[Place]:
        payload = self.http.get("/api/", params={"q": query, "limit": limit, "lang": "en"})
        return [self._to_place(feature) for feature in payload.get("features", [])]

    def _to_place(self, feature: dict) -> Place:
        props = feature.get("properties", {})
        lon, lat = feature["geometry"]["coordinates"]
        return Place(label=_label([props.get(f) for f in self.LABEL_FIELDS], lat, lon), lat=lat, lon=lon)


class OpenMeteoGeocodingClient:
    """Open-Meteo place search (free, keyless). Fallback provider: cities and towns only, ranked by population."""

    name = "open-meteo"

    def __init__(self, http: JsonHttpClient | None = None):
        self.http = http or JsonHttpClient(
            settings.EXTERNAL_APIS["OPEN_METEO_GEOCODING_BASE_URL"],
            "Open-Meteo geocoder",
            timeout=FAST_TIMEOUT,
            retries=1,
        )

    def search(self, query: str, limit: int) -> list[Place]:
        payload = self.http.get("/v1/search", params={"name": query, "count": limit, "language": "en", "format": "json"})
        return [self._to_place(result) for result in payload.get("results", [])]

    @staticmethod
    def _to_place(result: dict) -> Place:
        lat, lon = result["latitude"], result["longitude"]
        label = _label([result.get("name"), result.get("admin1"), result.get("country")], lat, lon)
        return Place(label=label, lat=lat, lon=lon)
