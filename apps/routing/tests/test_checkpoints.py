from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase

from apps.core.geo import Coordinate
from apps.routing.domain import RoutePath
from apps.routing.services import apply_truck_speed_limit, sample_checkpoints

DEPARTURE = datetime(2026, 1, 1, 8, tzinfo=timezone.utc)


def straight_path(miles_per_segment=10.0, segments=6, mph=60.0) -> RoutePath:
    coords = tuple(Coordinate(40.0, -100.0 + i * 0.2) for i in range(segments + 1))
    return RoutePath(coords, (miles_per_segment,) * segments, (miles_per_segment / mph * 3600,) * segments)


class CheckpointSamplingTests(SimpleTestCase):
    def test_checkpoints_every_interval_plus_destination(self):
        samples = sample_checkpoints(straight_path(), 25, DEPARTURE)
        self.assertEqual([s.mile_marker for s in samples], [0, 25, 50, 60])

    def test_eta_follows_cumulative_duration(self):
        samples = sample_checkpoints(straight_path(mph=60), 25, DEPARTURE)
        self.assertEqual(samples[1].eta, DEPARTURE + timedelta(minutes=25))
        self.assertEqual(samples[-1].eta, DEPARTURE + timedelta(hours=1))

    def test_represented_miles_cover_whole_route(self):
        samples = sample_checkpoints(straight_path(), 10, DEPARTURE)
        self.assertAlmostEqual(sum(s.represented_miles for s in samples), 60.0)

    def test_position_is_interpolated_within_segment(self):
        samples = sample_checkpoints(straight_path(), 25, DEPARTURE)
        self.assertAlmostEqual(samples[1].coordinate.lon, -100.0 + 0.5)


class TruckSpeedTests(SimpleTestCase):
    def test_fast_segments_are_slowed_to_truck_speed(self):
        path = apply_truck_speed_limit(straight_path(mph=80), max_speed_mph=65)
        self.assertAlmostEqual(path.duration_seconds, 60 / 65 * 3600)

    def test_slow_segments_are_unchanged(self):
        original = straight_path(mph=40)
        self.assertEqual(apply_truck_speed_limit(original, 65).segment_seconds, original.segment_seconds)
