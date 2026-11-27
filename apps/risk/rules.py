"""Risk thresholds and load rules from the assessment brief, expressed as data."""

from dataclasses import dataclass

from .domain import RiskLevel


@dataclass(frozen=True)
class Band:
    threshold: float
    level: RiskLevel
    strict: bool = False

    def matches(self, value: float) -> bool:
        return value > self.threshold if self.strict else value >= self.threshold


@dataclass(frozen=True)
class Metric:
    name: str
    unit: str
    bands: tuple[Band, ...]

    def classify(self, value: float) -> RiskLevel:
        return next((band.level for band in self.bands if band.matches(value)), RiskLevel.LOW)


@dataclass(frozen=True)
class LoadRule:
    min_wind_mph: float
    max_wind_mph: float
    min_weight_lb: float
    level: RiskLevel

    def matches(self, wind_mph: float, weight_lb: float) -> bool:
        return self.min_wind_mph <= wind_mph < self.max_wind_mph and weight_lb > self.min_weight_lb


WIND = Metric(
    "Wind",
    "mph",
    (
        Band(55, RiskLevel.NO_TRAVEL),
        Band(45, RiskLevel.SEVERE),
        Band(35, RiskLevel.HIGH),
        Band(25, RiskLevel.MODERATE),
    ),
)

RAIN = Metric(
    "Rain",
    "in/hr",
    (
        Band(1.00, RiskLevel.NO_TRAVEL, strict=True),
        Band(0.50, RiskLevel.SEVERE),
        Band(0.25, RiskLevel.HIGH),
        Band(0.10, RiskLevel.MODERATE),
    ),
)

SNOW = Metric(
    "Snow",
    "in/hr",
    (
        Band(3.0, RiskLevel.NO_TRAVEL, strict=True),
        Band(2.0, RiskLevel.SEVERE),
        Band(1.0, RiskLevel.HIGH),
        Band(0.5, RiskLevel.MODERATE),
    ),
)

LOAD_RULES = (
    LoadRule(45, 55, 30_000, RiskLevel.NO_TRAVEL),
    LoadRule(35, 45, 40_000, RiskLevel.SEVERE),
)
