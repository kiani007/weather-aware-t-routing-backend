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
    assessment: RiskAssessment


@dataclass(frozen=True)
class EvaluatedRoute:
    index: int
    path: RoutePath
    checkpoints: list[AssessedCheckpoint]
    risk_miles: dict[RiskLevel, float]
    average_risk: float
    max_risk: RiskLevel
    forecast_coverage: float
