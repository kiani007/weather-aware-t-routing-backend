import uuid

from django.db import models

from apps.risk.domain import RiskLevel


class RiskLevelChoices(models.IntegerChoices):
    LOW = RiskLevel.LOW, "Low"
    MODERATE = RiskLevel.MODERATE, "Moderate"
    HIGH = RiskLevel.HIGH, "High"
    SEVERE = RiskLevel.SEVERE, "Severe"
    NO_TRAVEL = RiskLevel.NO_TRAVEL, "No Travel"


class SampleInterval(models.IntegerChoices):
    TEN = 10, "10 miles"
    TWENTY_FIVE = 25, "25 miles"
    FIFTY = 50, "50 miles"


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class Trip(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    origin_label = models.CharField(max_length=255)
    origin_lat = models.FloatField()
    origin_lon = models.FloatField()
    destination_label = models.CharField(max_length=255)
    destination_lat = models.FloatField()
    destination_lon = models.FloatField()
    departure_at = models.DateTimeField()
    load_weight_lb = models.PositiveIntegerField()
    sample_interval_mi = models.PositiveSmallIntegerField(choices=SampleInterval.choices)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.origin_label} → {self.destination_label}"


class Route(models.Model):
    trip = models.ForeignKey(Trip, related_name="routes", on_delete=models.CASCADE)
    index = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=32)
    summary = models.CharField(max_length=255, blank=True)
    polyline = models.TextField()
    distance_mi = models.FloatField()
    duration_s = models.FloatField()
    arrival_at = models.DateTimeField()
    risk_miles = models.JSONField(default=dict)
    unknown_miles = models.FloatField(default=0.0, help_text="Miles whose weather could not be verified.")
    average_risk = models.FloatField()
    max_risk = models.PositiveSmallIntegerField(choices=RiskLevelChoices.choices)
    forecast_coverage = models.FloatField(help_text="Share of checkpoints with forecast data (0–1).")
    is_recommended = models.BooleanField(default=False)
    recommendation_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["index"]
        constraints = [models.UniqueConstraint(fields=["trip", "index"], name="unique_route_index_per_trip")]

    def __str__(self) -> str:
        return f"{self.trip_id} {self.name}"


class Checkpoint(models.Model):
    route = models.ForeignKey(Route, related_name="checkpoints", on_delete=models.CASCADE)
    sequence = models.PositiveIntegerField()
    lat = models.FloatField()
    lon = models.FloatField()
    mile_marker = models.FloatField()
    represented_mi = models.FloatField()
    eta = models.DateTimeField()
    has_forecast = models.BooleanField(default=True)
    wind_mph = models.FloatField(null=True)
    rain_in_hr = models.FloatField(null=True)
    snow_in_hr = models.FloatField(null=True)
    risk_level = models.PositiveSmallIntegerField(
        choices=RiskLevelChoices.choices, null=True, help_text="Null when the weather is unknown."
    )
    reasons = models.JSONField(default=list)

    class Meta:
        ordering = ["sequence"]
        constraints = [models.UniqueConstraint(fields=["route", "sequence"], name="unique_checkpoint_sequence")]
