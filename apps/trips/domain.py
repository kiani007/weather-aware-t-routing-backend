from dataclasses import dataclass
from datetime import datetime

from apps.core.geo import Coordinate
from apps.risk.domain import RiskAssessment, RiskLevel, WeatherConditions
from apps.routing.domain import CheckpointSample, RoutePath


@dataclass(frozen=True)
class Location:
    label: str
    coordinate: Coordinate


@dataclass(frozen=True)
class TripRequest:
    origin: Location
    destination: Location
    departure_at: datetime
    load_weight_lb: int
    sample_interval_mi: int


@dataclass(frozen=True)
class AssessedCheckpoint:
    sample: CheckpointSample
    conditions: WeatherConditions | None
    # None when the weather at this checkpoint's ETA is unknown (no forecast data)
    assessment: RiskAssessment | None


@dataclass(frozen=True)
class EvaluatedRoute:
    index: int
    path: RoutePath
    checkpoints: list[AssessedCheckpoint]
    # Miles per risk level, counting only checkpoints with a forecast
    risk_miles: dict[RiskLevel, float]
    # Miles whose weather could not be verified
    unknown_miles: float
    # Averaged over known miles only, so missing data cannot make a route look safer.
    # Both are None when no checkpoint on the route has a forecast.
    average_risk: float | None
    max_risk: RiskLevel | None
    forecast_coverage: float
