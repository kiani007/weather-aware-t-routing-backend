from apps.core.geo import Coordinate
from apps.risk.domain import RiskAssessment, RiskLevel
from apps.risk.services import assess_risk
from apps.routing.domain import CheckpointSample, RoutePath
from apps.weather.domain import HourlySeries

from ..domain import AssessedCheckpoint, EvaluatedRoute

NO_FORECAST = RiskAssessment(RiskLevel.LOW, ("No forecast available for this ETA",))


def evaluate_route(
    index: int,
    path: RoutePath,
    samples: list[CheckpointSample],
    forecasts: dict[Coordinate, HourlySeries],
    load_weight_lb: float,
) -> EvaluatedRoute:
    checkpoints = [_assess(sample, forecasts.get(sample.coordinate), load_weight_lb) for sample in samples]

    risk_miles = {level: 0.0 for level in RiskLevel}
    for checkpoint in checkpoints:
        risk_miles[checkpoint.assessment.level] += checkpoint.sample.represented_miles

    total_miles = sum(risk_miles.values()) or 1.0
    average = sum(level * miles for level, miles in risk_miles.items()) / total_miles
    covered = sum(1 for c in checkpoints if c.conditions is not None)

    return EvaluatedRoute(
        index=index,
        path=path,
        checkpoints=checkpoints,
        risk_miles=risk_miles,
        average_risk=average,
        max_risk=max((c.assessment.level for c in checkpoints), default=RiskLevel.LOW),
        forecast_coverage=covered / len(checkpoints) if checkpoints else 0.0,
    )


def _assess(sample: CheckpointSample, series: HourlySeries | None, load_weight_lb: float) -> AssessedCheckpoint:
    conditions = series.at(sample.eta) if series else None
    assessment = assess_risk(conditions, load_weight_lb) if conditions else NO_FORECAST
    return AssessedCheckpoint(sample, conditions, assessment)
