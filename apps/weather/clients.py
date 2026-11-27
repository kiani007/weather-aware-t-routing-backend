from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from django.conf import settings

from apps.core.exceptions import ExternalServiceError
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
        if len(locations) != len(coordinates):
            raise ExternalServiceError(
                f"Open-Meteo weather returned {len(locations)} locations for {len(coordinates)} requested."
            )
        return [self._to_series(location) for location in locations]

    @staticmethod
    def _to_series(location: dict) -> HourlySeries:
        hourly = location.get("hourly")
        if not isinstance(hourly, dict) or not isinstance(hourly.get("time"), list):
            raise ExternalServiceError("Open-Meteo weather returned a malformed forecast.")
        times = tuple(hourly["time"])

        def values(key: str) -> tuple[float | None, ...]:
            # A missing field means "unknown" for every hour, never zero
            raw = hourly.get(key)
            if not isinstance(raw, list) or len(raw) != len(times):
                return (None,) * len(times)
            return tuple(None if v is None else float(v) for v in raw)

        rain = tuple(None if r is None or s is None else r + s for r, s in zip(values("rain"), values("showers")))
        return HourlySeries(times, values("wind_speed_10m"), rain, values("snowfall"))
