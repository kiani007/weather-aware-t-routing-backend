from datetime import timedelta

import polyline
from django.db import transaction

from apps.core.geo import simplify
from apps.risk.recommendation import Recommendation

from ..domain import AssessedCheckpoint, EvaluatedRoute, TripRequest
from ..models import Checkpoint, Route, Trip
from .evaluation import UNKNOWN_REASON

ROUTE_NAMES = ("Route A", "Route B", "Route C", "Route D", "Route E")
DISPLAY_TOLERANCE_DEG = 0.0004


@transaction.atomic
def save_trip_plan(request: TripRequest, routes: list[EvaluatedRoute], recommendation: Recommendation) -> Trip:
    trip = Trip.objects.create(
        origin_label=request.origin.label,
        origin_lat=request.origin.coordinate.lat,
        origin_lon=request.origin.coordinate.lon,
        destination_label=request.destination.label,
        destination_lat=request.destination.coordinate.lat,
        destination_lon=request.destination.coordinate.lon,
        departure_at=request.departure_at,
        load_weight_lb=request.load_weight_lb,
        sample_interval_mi=request.sample_interval_mi,
    )
    route_models = Route.objects.bulk_create(
        [_build_route(trip, route, request, recommendation) for route in routes]
    )
    Checkpoint.objects.bulk_create(
        [_build_checkpoint(model, cp) for model, route in zip(route_models, routes) for cp in route.checkpoints]
    )
    return trip


def _build_route(trip: Trip, route: EvaluatedRoute, request: TripRequest, recommendation: Recommendation) -> Route:
    recommended = route.index == recommendation.route_index
    display_path = simplify(list(route.path.coordinates), DISPLAY_TOLERANCE_DEG)
    return Route(
        trip=trip,
        index=route.index,
        name=ROUTE_NAMES[route.index],
        summary=route.path.summary[:255],
        polyline=polyline.encode([(p.lat, p.lon) for p in display_path], 5),
        distance_mi=round(route.path.distance_miles, 1),
        duration_s=round(route.path.duration_seconds),
        arrival_at=request.departure_at + timedelta(seconds=route.path.duration_seconds),
        risk_miles={level.key: round(miles, 1) for level, miles in route.risk_miles.items()},
        unknown_miles=round(route.unknown_miles, 1),
        average_risk=round(route.average_risk, 3) if route.average_risk is not None else None,
        max_risk=route.max_risk,
        forecast_coverage=round(route.forecast_coverage, 3),
        is_recommended=recommended,
        recommendation_reason=recommendation.reason if recommended else "",
    )


def _build_checkpoint(route: Route, checkpoint: AssessedCheckpoint) -> Checkpoint:
    sample, conditions, assessment = checkpoint.sample, checkpoint.conditions, checkpoint.assessment
    return Checkpoint(
        route=route,
        sequence=sample.sequence,
        lat=round(sample.coordinate.lat, 5),
        lon=round(sample.coordinate.lon, 5),
        mile_marker=round(sample.mile_marker, 1),
        represented_mi=round(sample.represented_miles, 2),
        eta=sample.eta,
        has_forecast=conditions is not None,
        wind_mph=conditions.wind_mph if conditions else None,
        rain_in_hr=conditions.rain_in_hr if conditions else None,
        snow_in_hr=conditions.snow_in_hr if conditions else None,
        risk_level=assessment.level if assessment else None,
        reasons=list(assessment.reasons) if assessment else [UNKNOWN_REASON],
    )
