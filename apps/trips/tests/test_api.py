from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from apps.core.exceptions import ExternalServiceError
from apps.core.geo import Coordinate
from apps.routing.domain import RoutePath
from apps.trips.models import Trip
from apps.weather.domain import HourlySeries


def fake_path(offset: float, mph: float) -> RoutePath:
    coords = tuple(Coordinate(40.0 + offset, -100.0 + i * 0.5) for i in range(11))
    return RoutePath(coords, (20.0,) * 10, (20 / mph * 3600,) * 10, f"Road {offset}")


def calm_then_windy(coordinates, start, end):
    start_ts = int(start.timestamp())
    times = tuple(start_ts + h * 3600 for h in range(60))
    return {c: HourlySeries(times, (50.0 if c.lat > 40.5 else 10.0,) * 60, (0.0,) * 60, (0.0,) * 60) for c in coordinates}


class TripPlanApiTests(TestCase):
    def payload(self, **overrides):
        body = {
            "origin": {"label": "A", "lat": 40.0, "lon": -100.0},
            "destination": {"label": "B", "lat": 40.0, "lon": -95.0},
            "departure_at": (timezone.now() + timedelta(hours=1)).isoformat(),
            "load_weight_lb": 35_000,
            "sample_interval_mi": 25,
        }
        body.update(overrides)
        return body

    @mock.patch("apps.weather.services.WeatherService.forecasts", side_effect=calm_then_windy)
    @mock.patch("apps.routing.services.RouteAlternativesService.find")
    def test_plan_recommends_safest_route_and_persists(self, find, _forecasts):
        find.return_value = [fake_path(1.0, 70), fake_path(0.0, 55), fake_path(0.2, 50)]
        response = self.client.post("/api/trips/", self.payload(), content_type="application/json")

        self.assertEqual(response.status_code, 201, response.content)
        routes = response.json()["routes"]
        self.assertEqual(len(routes), 3)
        recommended = [r for r in routes if r["is_recommended"]]
        self.assertEqual(len(recommended), 1)
        self.assertEqual(recommended[0]["summary"], "Road 0.0")
        self.assertEqual(routes[0]["max_risk"]["key"], "no_travel")
        self.assertEqual(Trip.objects.count(), 1)

    @mock.patch("apps.weather.services.WeatherService.forecasts", return_value={})
    @mock.patch("apps.routing.services.RouteAlternativesService.find")
    def test_missing_forecasts_are_reported_as_unknown(self, find, _forecasts):
        find.return_value = [fake_path(0.0, 55)]
        response = self.client.post("/api/trips/", self.payload(), content_type="application/json")

        self.assertEqual(response.status_code, 201, response.content)
        route = response.json()["routes"][0]
        self.assertEqual(route["unknown_miles"], 200.0)
        self.assertEqual(route["risk_miles"]["low"], 0.0)
        self.assertEqual(route["forecast_coverage"], 0.0)
        checkpoint = route["checkpoints"][0]
        self.assertFalse(checkpoint["has_forecast"])
        self.assertIsNone(checkpoint["risk"])

    @mock.patch(
        "apps.weather.services.WeatherService.forecasts",
        side_effect=ExternalServiceError("Open-Meteo weather rate limit reached. Please try again later."),
    )
    @mock.patch("apps.routing.services.RouteAlternativesService.find")
    def test_upstream_failure_returns_502_envelope_and_saves_nothing(self, find, _forecasts):
        find.return_value = [fake_path(0.0, 55)]
        response = self.client.post("/api/trips/", self.payload(), content_type="application/json")

        self.assertEqual(response.status_code, 502)
        error = response.json()["error"]
        self.assertEqual(error["code"], "external_service_error")
        self.assertIn("rate limit", error["message"])
        self.assertTrue(error["request_id"])
        self.assertEqual(Trip.objects.count(), 0)

    def test_rejects_departure_beyond_forecast_horizon(self):
        late = (timezone.now() + timedelta(days=30)).isoformat()
        response = self.client.post("/api/trips/", self.payload(departure_at=late), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("departure_at", response.json()["error"]["details"])

    def test_rejects_invalid_interval(self):
        response = self.client.post("/api/trips/", self.payload(sample_interval_mi=15), content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_unknown_trip_returns_404(self):
        response = self.client.get("/api/trips/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")
