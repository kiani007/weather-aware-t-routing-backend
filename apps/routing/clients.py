from django.conf import settings

from apps.core.geo import METERS_PER_MILE, Coordinate
from apps.core.http import JsonHttpClient

from .domain import RoutePath


class OsrmClient:
    """Open Source Routing Machine HTTP client (public demo server by default)."""

    def __init__(self, http: JsonHttpClient | None = None):
        self.http = http or JsonHttpClient(settings.EXTERNAL_APIS["OSRM_BASE_URL"], "OSRM routing")

    def route(self, waypoints: list[Coordinate], alternatives: int = 0) -> list[RoutePath]:
        locations = ";".join(f"{p.lon:.6f},{p.lat:.6f}" for p in waypoints)
        params = {
            "overview": "full",
            "geometries": "geojson",
            "annotations": "distance,duration",
            "alternatives": str(alternatives) if alternatives else "false",
        }
        payload = self.http.get(f"/route/v1/driving/{locations}", params=params)
        if payload.get("code") != "Ok":
            return []
        return [self._to_path(route) for route in payload.get("routes", [])]

    @staticmethod
    def _to_path(route: dict) -> RoutePath:
        coordinates = tuple(Coordinate(lat, lon) for lon, lat in route["geometry"]["coordinates"])
        miles: list[float] = []
        seconds: list[float] = []
        for leg in route["legs"]:
            miles.extend(d / METERS_PER_MILE for d in leg["annotation"]["distance"])
            seconds.extend(leg["annotation"]["duration"])
        summary = " / ".join(leg["summary"] for leg in route["legs"] if leg.get("summary"))
        return RoutePath(coordinates, tuple(miles), tuple(seconds), summary)
