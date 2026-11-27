from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field, inline_serializer
from rest_framework import serializers

from apps.core.geo import Coordinate
from apps.risk.domain import RiskLevel

from .domain import Location, TripRequest
from .models import Checkpoint, Route, SampleInterval, Trip

PAST_DEPARTURE_GRACE = timedelta(hours=1)


class LocationInputSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=255)
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)


class TripPlanRequestSerializer(serializers.Serializer):
    origin = LocationInputSerializer()
    destination = LocationInputSerializer()
    departure_at = serializers.DateTimeField()
    load_weight_lb = serializers.IntegerField(min_value=1, max_value=200_000)
    sample_interval_mi = serializers.ChoiceField(choices=SampleInterval.choices, default=SampleInterval.TWENTY_FIVE)

    def validate_departure_at(self, value):
        now = timezone.now()
        max_ahead = timedelta(days=settings.TRIP_PLANNING["MAX_DEPARTURE_DAYS_AHEAD"])
        if value < now - PAST_DEPARTURE_GRACE:
            raise serializers.ValidationError("Departure cannot be in the past.")
        if value > now + max_ahead:
            raise serializers.ValidationError(f"Departure must be within {max_ahead.days} days (forecast horizon).")
        return value

    def validate(self, attrs):
        origin, destination = attrs["origin"], attrs["destination"]
        if (origin["lat"], origin["lon"]) == (destination["lat"], destination["lon"]):
            raise serializers.ValidationError("Origin and destination must differ.")
        return attrs

    def to_domain(self) -> TripRequest:
        data = self.validated_data
        return TripRequest(
            origin=_location(data["origin"]),
            destination=_location(data["destination"]),
            departure_at=data["departure_at"],
            load_weight_lb=data["load_weight_lb"],
            sample_interval_mi=int(data["sample_interval_mi"]),
        )


def _location(data: dict) -> Location:
    return Location(label=data["label"], coordinate=Coordinate(data["lat"], data["lon"]))


RISK_LEVEL_SCHEMA = inline_serializer(
    "RiskLevel",
    {"value": serializers.IntegerField(), "key": serializers.CharField(), "label": serializers.CharField()},
)


@extend_schema_field(RISK_LEVEL_SCHEMA)
class RiskLevelField(serializers.Field):
    """Serializes an integer risk level as {value, label, key}."""

    def to_representation(self, value):
        level = RiskLevel(value)
        return {"value": int(level), "key": level.key, "label": level.label}


class CheckpointSerializer(serializers.ModelSerializer):
    risk = RiskLevelField(source="risk_level")

    class Meta:
        model = Checkpoint
        fields = (
            "sequence",
            "lat",
            "lon",
            "mile_marker",
            "represented_mi",
            "eta",
            "has_forecast",
            "wind_mph",
            "rain_in_hr",
            "snow_in_hr",
            "risk",
            "reasons",
        )


class RouteSerializer(serializers.ModelSerializer):
    max_risk = RiskLevelField()
    checkpoints = CheckpointSerializer(many=True, read_only=True)

    class Meta:
        model = Route
        fields = (
            "id",
            "index",
            "name",
            "summary",
            "polyline",
            "distance_mi",
            "duration_s",
            "arrival_at",
            "risk_miles",
            "average_risk",
            "max_risk",
            "forecast_coverage",
            "is_recommended",
            "recommendation_reason",
            "checkpoints",
        )


class TripSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = (
            "id",
            "origin_label",
            "destination_label",
            "departure_at",
            "load_weight_lb",
            "sample_interval_mi",
            "created_at",
        )


class TripDetailSerializer(TripSummarySerializer):
    origin = serializers.SerializerMethodField()
    destination = serializers.SerializerMethodField()
    routes = RouteSerializer(many=True, read_only=True)

    class Meta(TripSummarySerializer.Meta):
        fields = TripSummarySerializer.Meta.fields + ("origin", "destination", "routes")

    def get_origin(self, trip: Trip) -> dict:
        return {"label": trip.origin_label, "lat": trip.origin_lat, "lon": trip.origin_lon}

    def get_destination(self, trip: Trip) -> dict:
        return {"label": trip.destination_label, "lat": trip.destination_lat, "lon": trip.destination_lon}


class HeatmapSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    hours = serializers.IntegerField()
    cell_size_deg = serializers.FloatField()
    points = serializers.ListField(child=serializers.ListField(child=serializers.FloatField()))
    metrics = serializers.SerializerMethodField()

    def get_metrics(self, frames) -> dict:
        return {
            "wind": frames.wind,
            "precipitation": frames.precipitation,
            "snow": frames.snow,
            "risk": frames.risk,
        }
