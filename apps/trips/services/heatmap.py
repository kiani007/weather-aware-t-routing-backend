import polyline
from django.conf import settings
from django.core.cache import cache

from apps.core.geo import Coordinate
from apps.weather.heatmap import HeatmapFrames, HeatmapService

from ..models import Trip


def trip_heatmap(trip: Trip) -> HeatmapFrames:
    config = settings.TRIP_PLANNING
    key = f"heatmap:{trip.pk}"
    frames = cache.get(key)
    if frames is None:
        paths = [[Coordinate(lat, lon) for lat, lon in polyline.decode(r.polyline, 5)] for r in trip.routes.all()]
        frames = HeatmapService().build(
            paths,
            trip.departure_at,
            trip.load_weight_lb,
            hours=config["HEATMAP_HOURS"],
            max_points=config["HEATMAP_MAX_POINTS"],
        )
        cache.set(key, frames, config["WEATHER_CACHE_SECONDS"])
    return frames
