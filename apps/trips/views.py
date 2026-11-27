from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from . import selectors
from .serializers import HeatmapSerializer, TripDetailSerializer, TripPlanRequestSerializer, TripSummarySerializer
from .services import TripPlanner, trip_heatmap


@extend_schema_view(
    list=extend_schema(summary="List recently planned trips", responses=TripSummarySerializer(many=True)),
    retrieve=extend_schema(summary="Get a planned trip with routes and checkpoints", responses=TripDetailSerializer),
)
@extend_schema(tags=["trips"])
class TripViewSet(viewsets.ViewSet):
    lookup_value_regex = "[0-9a-f-]{36}"

    def list(self, request):
        return Response(TripSummarySerializer(selectors.recent_trips(), many=True).data)

    def retrieve(self, request, pk=None):
        return Response(TripDetailSerializer(selectors.trip_with_routes(pk)).data)

    @extend_schema(
        summary="Plan a weather-aware trip",
        description=(
            "Generates up to 3 route options, samples weather at each checkpoint using the truck's ETA, "
            "classifies risk with load rules and flags the recommended route."
        ),
        request=TripPlanRequestSerializer,
        responses={
            201: TripDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
            422: OpenApiResponse(description="No route could be found"),
            502: OpenApiResponse(description="Upstream provider failure"),
        },
    )
    def create(self, request):
        payload = TripPlanRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        trip = TripPlanner().plan(payload.to_domain())
        return Response(TripDetailSerializer(selectors.trip_with_routes(trip.pk)).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Weather heatmap frames (0–48 h) along the trip corridor",
        responses=HeatmapSerializer,
    )
    @action(detail=True, methods=["get"])
    def heatmap(self, request, pk=None):
        frames = trip_heatmap(selectors.trip_with_routes(pk))
        return Response(HeatmapSerializer(frames).data)

    def get_throttles(self):
        if self.action == "create":
            self.throttle_scope = "trip_plan"
            return [ScopedRateThrottle()]
        return super().get_throttles()
