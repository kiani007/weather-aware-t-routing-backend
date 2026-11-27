from datetime import datetime, timezone

from django.test import SimpleTestCase

from apps.core.geo import Coordinate
from apps.weather.domain import HourlySeries
from apps.weather.heatmap import corridor_grid

T0 = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
SERIES = HourlySeries((T0, T0 + 3600), (10.0, 30.0), (0.0, 0.2), (0.0, 1.0))


class HourlySeriesTests(SimpleTestCase):
    def test_interpolates_between_hours(self):
        conditions = SERIES.at(datetime.fromtimestamp(T0 + 1800, timezone.utc))
        self.assertEqual((conditions.wind_mph, conditions.rain_in_hr, conditions.snow_in_hr), (20.0, 0.1, 0.5))

    def test_exact_hour(self):
        self.assertEqual(SERIES.at(datetime.fromtimestamp(T0, timezone.utc)).wind_mph, 10.0)

    def test_outside_window_returns_none(self):
        self.assertIsNone(SERIES.at(datetime.fromtimestamp(T0 + 7200, timezone.utc)))


class CorridorGridTests(SimpleTestCase):
    def test_grid_respects_point_budget(self):
        path = [Coordinate(35 + i * 0.05, -100 + i * 0.1) for i in range(200)]
        cell, points = corridor_grid([path], max_points=120)
        self.assertLessEqual(len(points), 120)
        self.assertGreaterEqual(cell, 0.2)
