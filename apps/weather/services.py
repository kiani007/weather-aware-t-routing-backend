import logging
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.core.cache import cache

from apps.core.geo import Coordinate

from .clients import OpenMeteoClient
from .domain import HourlySeries

logger = logging.getLogger(__name__)

LOCATION_PRECISION_DEG = 0.1


def floor_hour(moment: datetime) -> datetime:
    return moment.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


class WeatherService:
    """Fetches hourly forecasts for many points, deduplicated on a ~7 mi grid and cached."""

    def __init__(self, client: OpenMeteoClient | None = None):
        self.client = client or OpenMeteoClient()
        self.cache_seconds = settings.TRIP_PLANNING["WEATHER_CACHE_SECONDS"]

    def forecasts(self, coordinates: list[Coordinate], start: datetime, end: datetime) -> dict[Coordinate, HourlySeries]:
        """Maps each *input* coordinate to the series of its grid cell."""
        start, end = floor_hour(start), floor_hour(end) + timedelta(hours=1)
        cells = {c: c.rounded(LOCATION_PRECISION_DEG) for c in coordinates}
        series_by_cell = self._load(sorted(set(cells.values())), start, end)
        return {c: series_by_cell[cell] for c, cell in cells.items() if cell in series_by_cell}

    def _load(self, cells: list[Coordinate], start: datetime, end: datetime) -> dict[Coordinate, HourlySeries]:
        window = f"{int(start.timestamp())}:{int(end.timestamp())}"
        keys = {cell: f"wx:{cell.lat}:{cell.lon}:{window}" for cell in cells}
        cached = cache.get_many(list(keys.values()))
        result = {cell: cached[key] for cell, key in keys.items() if key in cached}

        missing = [cell for cell in cells if cell not in result]
        if missing:
            fetched = dict(zip(missing, self.client.hourly(missing, start, end)))
            cache.set_many({keys[cell]: series for cell, series in fetched.items()}, self.cache_seconds)
            result.update(fetched)
        logger.info("Weather for %d cells (%d cached, %d fetched)", len(cells), len(cells) - len(missing), len(missing))
        return result
