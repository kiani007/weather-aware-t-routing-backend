from .domain import RiskAssessment, RiskLevel, WeatherConditions
from .rules import LOAD_RULES, RAIN, SNOW, WIND


def assess_risk(conditions: WeatherConditions, load_weight_lb: float) -> RiskAssessment:
    level = RiskLevel.LOW
    reasons: list[str] = []

    for metric, value in ((WIND, conditions.wind_mph), (RAIN, conditions.rain_in_hr), (SNOW, conditions.snow_in_hr)):
        metric_level = metric.classify(value)
        if metric_level > RiskLevel.LOW:
            reasons.append(f"{metric.name} {value:g} {metric.unit} → {metric_level.label}")
        level = max(level, metric_level)

    for rule in LOAD_RULES:
        if rule.matches(conditions.wind_mph, load_weight_lb) and rule.level > level:
            reasons.append(
                f"Load {load_weight_lb:,.0f} lb in {conditions.wind_mph:g} mph wind → {rule.level.label}"
            )
            level = rule.level

    return RiskAssessment(level=level, reasons=tuple(reasons))


def risk_level_only(wind_mph: float, rain_in_hr: float, snow_in_hr: float, load_weight_lb: float) -> int:
    """Allocation-light variant for bulk heatmap scoring."""
    level = max(WIND.classify(wind_mph), RAIN.classify(rain_in_hr), SNOW.classify(snow_in_hr))
    for rule in LOAD_RULES:
        if rule.matches(wind_mph, load_weight_lb):
            level = max(level, rule.level)
    return int(level)
