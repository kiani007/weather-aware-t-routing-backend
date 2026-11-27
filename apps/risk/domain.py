from dataclasses import dataclass
from enum import IntEnum


class RiskLevel(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return self.name.replace("_", " ").title()

    @property
    def key(self) -> str:
        return self.name.lower()


@dataclass(frozen=True)
class WeatherConditions:
    wind_mph: float
    rain_in_hr: float
    snow_in_hr: float


@dataclass(frozen=True)
class RiskAssessment:
    level: RiskLevel
    reasons: tuple[str, ...]
