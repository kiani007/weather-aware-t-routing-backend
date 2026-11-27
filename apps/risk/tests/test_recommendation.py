from django.test import SimpleTestCase

from apps.risk.domain import RiskLevel
from apps.risk.recommendation import RouteScore, recommend


def score(index, severe=0.0, high=0.0, no_travel=0.0, avg=0.0, hours=10.0):
    miles = {RiskLevel.SEVERE: severe, RiskLevel.HIGH: high, RiskLevel.NO_TRAVEL: no_travel}
    return RouteScore(index, miles, avg, hours * 3600)


class RecommendationTests(SimpleTestCase):
    def test_fewest_severe_miles_beats_faster_route(self):
        result = recommend([score(0, severe=20, hours=8), score(1, severe=5, hours=12)])
        self.assertEqual(result.route_index, 1)
        self.assertIn("Severe-risk", result.reason)

    def test_high_miles_break_severe_tie(self):
        self.assertEqual(recommend([score(0, high=30), score(1, high=10)]).route_index, 1)

    def test_average_risk_breaks_high_tie(self):
        self.assertEqual(recommend([score(0, avg=0.8), score(1, avg=0.3)]).route_index, 1)

    def test_travel_time_is_final_tiebreaker(self):
        result = recommend([score(0, hours=11), score(1, hours=9), score(2, hours=10)])
        self.assertEqual(result.route_index, 1)
        self.assertIn("travel time", result.reason)

    def test_no_travel_miles_rank_worst(self):
        self.assertEqual(recommend([score(0, no_travel=5), score(1, severe=50)]).route_index, 1)
