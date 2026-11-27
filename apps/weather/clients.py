from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from django.conf import settings

from apps.core.geo import Coordinate
from apps.core.http import JsonHttpClient

from .domain import HourlySeries

BATCH_SIZE = 100
HOURLY_FIELDS = "wind_speed_10m,rain,showers,snowfall"


class OpenMeteoClient:
    """Open-Meteo forecast API (free, keyless). Supports many coordinates per request."""

    def __init__(self, http: JsonHttpClient | None = None):
        self.http = http or JsonHttpClient(settings.EXTERNAL_APIS["OPEN_METEO_BASE_URL"], "Open-Meteo weather")

    def hourly(self, coordinates: list[Coordinate], start: datetime, end: datetime) -> list[HourlySeries]:
        batches = [coordinates[i : i + BATCH_SIZE] for i in range(0, len(coordinates), BATCH_SIZE)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = pool.map(lambda batch: self._fetch(batch, start, end), batches)
        return [series for batch in results for series in batch]

    def _fetch(self, coordinates: list[Coordinate], start: datetime, end: datetime) -> list[HourlySeries]:
        params = {
            "latitude": ",".join(f"{c.lat:.4f}" for c in coordinates),
            "longitude": ",".join(f"{c.lon:.4f}" for c in coordinates),
            "hourly": HOURLY_FIELDS,
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "GMT",
            "timeformat": "unixtime",
            "start_hour": start.strftime("%Y-%m-%dT%H:00"),
            "end_hour": end.strftime("%Y-%m-%dT%H:00"),
        }
        payload = self.http.get("/v1/forecast", params=params)
        locations = payload if isinstance(payload, list) else [payload]
        return [self._to_series(location["hourly"]) for location in locations]

    @staticmethod
    def _to_series(hourly: dict) -> HourlySeries:
        def values(key: str) -> tuple[float, ...]:
            return tuple(v or 0.0 for v in hourly.get(key, []))

        rain = tuple(r + s for r, s in zip(values("rain"), values("showers")))
        return HourlySeries(tuple(hourly["time"]), values("wind_speed_10m"), rain, values("snowfall"))
