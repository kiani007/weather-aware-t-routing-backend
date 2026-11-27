"""Builds a weather grid around the trip corridor with 0–48 h hourly frames."""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from apps.core.geo import Coordinate
from apps.risk.services import risk_level_only

from .services import WeatherService, floor_hour

MIN_CELL_DEG = 0.2
CELL_GROWTH = 1.25


@dataclass(frozen=True)
class HeatmapFrames:
    start: datetime
    hours: int
    cell_size_deg: float
    points: list[Coordinate]
    wind: list[list[float | None]]
    precipitation: list[list[float | None]]
    snow: list[list[float | None]]
    risk: list[list[int | None]]


def corridor_grid(paths: list[list[Coordinate]], max_points: int) -> tuple[float, list[Coordinate]]:
    """Snaps route geometry to a grid, dilates by one cell, and coarsens until under `max_points`."""
    cell = MIN_CELL_DEG
    while True:
        occupied = {(math.floor(p.lat / cell), math.floor(p.lon / cell)) for path in paths for p in path}
        dilated = {(r + dr, c + dc) for r, c in occupied for dr in (-1, 0, 1) for dc in (-1, 0, 1)}
        if len(dilated) <= max_points:
            points = [Coordinate(round((r + 0.5) * cell, 4), round((c + 0.5) * cell, 4)) for r, c in sorted(dilated)]
            return cell, points
        cell *= CELL_GROWTH


class HeatmapService:
    def __init__(self, weather: WeatherService | None = None):
        self.weather = weather or WeatherService()

    def build(
        self, paths: list[list[Coordinate]], departure: datetime, load_weight_lb: float, hours: int, max_points: int
    ) -> HeatmapFrames:
        cell, points = corridor_grid(paths, max_points)
        start = floor_hour(departure)
        end = start + timedelta(hours=hours)
        series = self.weather.forecasts(points, start, end)

        wind, precipitation, snow, risk = [], [], [], []
        for hour in range(hours + 1):
            ts = int((start + timedelta(hours=hour)).timestamp())
            frame = [series[p].hour(ts) if p in series else None for p in points]
            wind.append([round(c.wind_mph, 1) if c else None for c in frame])
            precipitation.append([round(c.rain_in_hr, 2) if c else None for c in frame])
            snow.append([round(c.snow_in_hr, 2) if c else None for c in frame])
            risk.append(
                [risk_level_only(c.wind_mph, c.rain_in_hr, c.snow_in_hr, load_weight_lb) if c else None for c in frame]
            )
        return HeatmapFrames(start, hours, round(cell, 4), points, wind, precipitation, snow, risk)
