import logging
from datetime import timedelta

from django.conf import settings

from apps.risk.recommendation import RouteScore, recommend
from apps.routing.services import RouteAlternativesService, apply_truck_speed_limit, sample_checkpoints
from apps.weather.services import WeatherService

from ..domain import TripRequest
from ..models import Trip
from .evaluation import evaluate_route
from .persistence import save_trip_plan

logger = logging.getLogger(__name__)


class TripPlanner:
    """Orchestrates routing → checkpoint sampling → ETA-matched weather → risk → recommendation."""

    def __init__(self, routing: RouteAlternativesService | None = None, weather: WeatherService | None = None):
        self.routing = routing or RouteAlternativesService()
        self.weather = weather or WeatherService()
        self.config = settings.TRIP_PLANNING

    def plan(self, request: TripRequest) -> Trip:
        paths = self.routing.find(
            request.origin.coordinate, request.destination.coordinate, self.config["ROUTE_OPTIONS"]
        )
        paths = [apply_truck_speed_limit(path, self.config["TRUCK_MAX_SPEED_MPH"]) for path in paths]
        samples = [sample_checkpoints(path, request.sample_interval_mi, request.departure_at) for path in paths]

        latest_arrival = request.departure_at + timedelta(seconds=max(p.duration_seconds for p in paths))
        coordinates = [s.coordinate for route_samples in samples for s in route_samples]
        forecasts = self.weather.forecasts(coordinates, request.departure_at, latest_arrival)

        evaluated = [
            evaluate_route(i, path, route_samples, forecasts, request.load_weight_lb)
            for i, (path, route_samples) in enumerate(zip(paths, samples))
        ]
        recommendation = recommend(
            [RouteScore(r.index, r.risk_miles, r.average_risk, r.path.duration_seconds) for r in evaluated]
        )
        logger.info(
            "Planned %d routes, %d checkpoints; recommended index %d",
            len(evaluated),
            len(coordinates),
            recommendation.route_index,
        )
        return save_trip_plan(request, evaluated, recommendation)
