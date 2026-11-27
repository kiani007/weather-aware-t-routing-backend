"""Route ranking: fewest No-Travel → Severe → unverified → High miles, then lowest average risk, then fastest.

Unverified (unknown-weather) miles rank right after Severe: a route must not win
because part of it has no forecast, but a verified Severe stretch is still worse.
"""

from dataclasses import dataclass

from .domain import RiskLevel

MILES_PRECISION = 1
RISK_PRECISION = 3


@dataclass(frozen=True)
class RouteScore:
    route_index: int
    risk_miles: dict[RiskLevel, float]
    unknown_miles: float
    average_risk: float
    duration_seconds: float

    def miles(self, level: RiskLevel) -> float:
        return round(self.risk_miles.get(level, 0.0), MILES_PRECISION)

    @property
    def unverified_miles(self) -> float:
        return round(self.unknown_miles, MILES_PRECISION)

    @property
    def sort_key(self) -> tuple:
        return (
            self.miles(RiskLevel.NO_TRAVEL),
            self.miles(RiskLevel.SEVERE),
            self.unverified_miles,
            self.miles(RiskLevel.HIGH),
            round(self.average_risk, RISK_PRECISION),
            self.duration_seconds,
        )


@dataclass(frozen=True)
class Recommendation:
    route_index: int
    reason: str


CRITERIA = (
    ("Fewest No Travel miles", lambda s: s.miles(RiskLevel.NO_TRAVEL), "{:.1f} mi"),
    ("Lowest Severe-risk mileage", lambda s: s.miles(RiskLevel.SEVERE), "{:.1f} mi"),
    ("Less unverified weather", lambda s: s.unverified_miles, "{:.1f} mi"),
    ("Lowest High-risk mileage", lambda s: s.miles(RiskLevel.HIGH), "{:.1f} mi"),
    ("Lowest average weather risk", lambda s: round(s.average_risk, RISK_PRECISION), "{:.2f}"),
    ("Equal weather risk and the shortest travel time", lambda s: s.duration_seconds / 3600, "{:.1f} h"),
)


def recommend(scores: list[RouteScore]) -> Recommendation:
    ranked = sorted(scores, key=lambda s: s.sort_key)
    best = ranked[0]
    if len(ranked) == 1:
        return Recommendation(best.route_index, "Only one viable route was found.")

    runner_up = ranked[1]
    for label, value, fmt in CRITERIA:
        if value(best) != value(runner_up):
            return Recommendation(
                best.route_index,
                f"{label} ({fmt.format(value(best))} vs {fmt.format(value(runner_up))} on the next best route).",
            )
    return Recommendation(best.route_index, "Routes are equivalent; the first option was chosen.")
