from apps.core.geo import Coordinate
from apps.risk.domain import RiskLevel
from apps.risk.services import assess_risk
from apps.routing.domain import CheckpointSample, RoutePath
from apps.weather.domain import HourlySeries

from ..domain import AssessedCheckpoint, EvaluatedRoute

UNKNOWN_REASON = "No forecast available for this ETA"


def evaluate_route(
    index: int,
    path: RoutePath,
    samples: list[CheckpointSample],
    forecasts: dict[Coordinate, HourlySeries],
    load_weight_lb: float,
) -> EvaluatedRoute:
    checkpoints = [_assess(sample, forecasts.get(sample.coordinate), load_weight_lb) for sample in samples]

    # Unknown weather is tracked separately: it is never counted as Low risk
    risk_miles = {level: 0.0 for level in RiskLevel}
    unknown_miles = 0.0
    for checkpoint in checkpoints:
        if checkpoint.assessment is None:
            unknown_miles += checkpoint.sample.represented_miles
        else:
            risk_miles[checkpoint.assessment.level] += checkpoint.sample.represented_miles

    # With no verified checkpoint there is no risk to report: None, never a "safe" Low / 0.0
    known_miles = sum(risk_miles.values())
    average = sum(level * miles for level, miles in risk_miles.items()) / known_miles if known_miles else None
    known = [c.assessment.level for c in checkpoints if c.assessment is not None]

    return EvaluatedRoute(
        index=index,
        path=path,
        checkpoints=checkpoints,
        risk_miles=risk_miles,
        unknown_miles=unknown_miles,
        average_risk=average,
        max_risk=max(known, default=None),
        forecast_coverage=len(known) / len(checkpoints) if checkpoints else 0.0,
    )


def _assess(sample: CheckpointSample, series: HourlySeries | None, load_weight_lb: float) -> AssessedCheckpoint:
    conditions = series.at(sample.eta) if series else None
    assessment = assess_risk(conditions, load_weight_lb) if conditions else None
    return AssessedCheckpoint(sample, conditions, assessment)
