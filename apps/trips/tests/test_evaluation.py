from datetime import datetime, timezone

from django.test import SimpleTestCase

from apps.core.geo import Coordinate
from apps.risk.domain import RiskLevel
from apps.routing.domain import CheckpointSample, RoutePath
from apps.trips.services.evaluation import evaluate_route
from apps.weather.domain import HourlySeries

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
TS = int(T0.timestamp())
PATH = RoutePath((Coordinate(40, -100), Coordinate(40, -99)), (100.0,), (6000.0,))


def series(wind: float | None) -> HourlySeries:
    return HourlySeries((TS,), (wind,), (0.0,), (0.0,))


def samples(count: int) -> list[CheckpointSample]:
    return [CheckpointSample(i, Coordinate(40, -100 + i), i * 25.0, T0, 25.0) for i in range(count)]


class EvaluateRouteTests(SimpleTestCase):
    def test_missing_forecast_is_unknown_not_low(self):
        points = samples(4)
        forecasts = {points[0].coordinate: series(10.0), points[1].coordinate: series(10.0)}

        route = evaluate_route(0, PATH, points, forecasts, load_weight_lb=35_000)

        self.assertEqual(route.risk_miles[RiskLevel.LOW], 50.0)
        self.assertEqual(route.unknown_miles, 50.0)
        self.assertEqual(route.forecast_coverage, 0.5)
        self.assertIsNone(route.checkpoints[2].assessment)

    def test_null_weather_value_is_unknown(self):
        points = samples(1)
        route = evaluate_route(0, PATH, points, {points[0].coordinate: series(None)}, load_weight_lb=35_000)

        self.assertEqual(route.unknown_miles, 25.0)
        self.assertEqual(route.risk_miles[RiskLevel.LOW], 0.0)

    def test_route_without_any_forecast_reports_no_risk_level(self):
        route = evaluate_route(0, PATH, samples(4), {}, load_weight_lb=35_000)

        self.assertEqual(route.forecast_coverage, 0.0)
        self.assertEqual(route.unknown_miles, 100.0)
        self.assertIsNone(route.max_risk)
        self.assertIsNone(route.average_risk)

    def test_average_and_max_use_known_miles_only(self):
        points = samples(2)
        route = evaluate_route(0, PATH, points, {points[0].coordinate: series(60.0)}, load_weight_lb=35_000)

        known_level = route.checkpoints[0].assessment.level
        self.assertGreater(known_level, RiskLevel.LOW)
        self.assertEqual(route.average_risk, float(known_level))
        self.assertEqual(route.max_risk, known_level)
