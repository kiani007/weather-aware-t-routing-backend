from datetime import datetime, timezone

from django.test import SimpleTestCase

from apps.core.exceptions import ExternalServiceError
from apps.core.geo import Coordinate
from apps.weather.clients import OpenMeteoClient

START = datetime(2026, 1, 1, tzinfo=timezone.utc)
POINTS = [Coordinate(41.9, -87.6), Coordinate(38.6, -90.2)]


class FakeHttp:
    def __init__(self, payload):
        self.payload = payload

    def get(self, path, params=None):
        return self.payload


def location(**hourly):
    return {"hourly": {"time": [0, 3600], **hourly}}


FULL = {"wind_speed_10m": [5, 6], "rain": [0, 0.1], "showers": [0, 0.05], "snowfall": [0, 0]}


class OpenMeteoClientTests(SimpleTestCase):
    def fetch(self, payload, points=POINTS):
        return OpenMeteoClient(http=FakeHttp(payload)).hourly(points, START, START)

    def test_parses_values(self):
        series = self.fetch([location(**FULL), location(**FULL)])[0]
        self.assertEqual(series.wind_mph, (5.0, 6.0))
        self.assertEqual(series.rain_in_hr[0], 0.0)
        self.assertAlmostEqual(series.rain_in_hr[1], 0.15)

    def test_null_values_stay_missing(self):
        hourly = {**FULL, "wind_speed_10m": [None, 6], "showers": [0, None]}
        series = self.fetch([location(**hourly), location(**FULL)])[0]
        self.assertEqual(series.wind_mph, (None, 6.0))
        self.assertEqual(series.rain_in_hr, (0.0, None))

    def test_missing_field_is_unknown_for_every_hour(self):
        hourly = {k: v for k, v in FULL.items() if k != "snowfall"}
        series = self.fetch([location(**hourly), location(**FULL)])[0]
        self.assertEqual(series.snow_in_hr, (None, None))

    def test_wrong_location_count_raises(self):
        with self.assertRaises(ExternalServiceError):
            self.fetch([location(**FULL)])

    def test_malformed_location_raises(self):
        with self.assertRaises(ExternalServiceError):
            self.fetch([{"error": True}, location(**FULL)])

    def test_single_location_object(self):
        series = self.fetch(location(**FULL), points=POINTS[:1])
        self.assertEqual(len(series), 1)
