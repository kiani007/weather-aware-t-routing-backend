from django.test import SimpleTestCase

from apps.risk.domain import RiskLevel, WeatherConditions
from apps.risk.services import assess_risk, risk_level_only


def level(wind=0.0, rain=0.0, snow=0.0, load=10_000):
    return assess_risk(WeatherConditions(wind, rain, snow), load).level


class WindThresholdTests(SimpleTestCase):
    def test_boundaries(self):
        cases = [(24.9, "LOW"), (25, "MODERATE"), (34.9, "MODERATE"), (35, "HIGH"), (44.9, "HIGH"),
                 (45, "SEVERE"), (54.9, "SEVERE"), (55, "NO_TRAVEL")]
        for wind, expected in cases:
            with self.subTest(wind=wind):
                self.assertEqual(level(wind=wind), RiskLevel[expected])


class PrecipitationThresholdTests(SimpleTestCase):
    def test_rain_boundaries(self):
        cases = [(0.09, "LOW"), (0.10, "MODERATE"), (0.25, "HIGH"), (0.50, "SEVERE"), (1.00, "SEVERE"), (1.01, "NO_TRAVEL")]
        for rain, expected in cases:
            with self.subTest(rain=rain):
                self.assertEqual(level(rain=rain), RiskLevel[expected])

    def test_snow_boundaries(self):
        cases = [(0.4, "LOW"), (0.5, "MODERATE"), (1.0, "HIGH"), (2.0, "SEVERE"), (3.0, "SEVERE"), (3.1, "NO_TRAVEL")]
        for snow, expected in cases:
            with self.subTest(snow=snow):
                self.assertEqual(level(snow=snow), RiskLevel[expected])

    def test_worst_condition_wins(self):
        self.assertEqual(level(wind=26, rain=0.3, snow=2.5), RiskLevel.SEVERE)


class LoadRuleTests(SimpleTestCase):
    def test_wind_55_is_no_travel_for_any_load(self):
        self.assertEqual(level(wind=55, load=1_000), RiskLevel.NO_TRAVEL)

    def test_severe_wind_with_heavy_load_is_no_travel(self):
        self.assertEqual(level(wind=50, load=30_001), RiskLevel.NO_TRAVEL)
        self.assertEqual(level(wind=50, load=30_000), RiskLevel.SEVERE)

    def test_high_wind_with_very_heavy_load_is_severe(self):
        self.assertEqual(level(wind=40, load=40_001), RiskLevel.SEVERE)
        self.assertEqual(level(wind=40, load=40_000), RiskLevel.HIGH)

    def test_load_rule_never_downgrades(self):
        self.assertEqual(level(wind=40, snow=3.5, load=45_000), RiskLevel.NO_TRAVEL)

    def test_reasons_explain_load_escalation(self):
        result = assess_risk(WeatherConditions(40, 0, 0), 45_000)
        self.assertTrue(any("Load" in reason for reason in result.reasons))

    def test_bulk_variant_matches(self):
        for args in [(40, 0, 0, 45_000), (50, 0, 0, 35_000), (10, 0.3, 0, 1), (60, 0, 0, 1)]:
            with self.subTest(args=args):
                self.assertEqual(risk_level_only(*args), int(level(args[0], args[1], args[2], args[3])))
