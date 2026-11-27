from django.db.models import Prefetch, QuerySet

from apps.core.exceptions import NotFoundError

from .models import Checkpoint, Route, Trip


def recent_trips(limit: int = 20) -> QuerySet[Trip]:
    return Trip.objects.all()[:limit]


def trip_with_routes(trip_id) -> Trip:
    routes = Route.objects.prefetch_related(Prefetch("checkpoints", queryset=Checkpoint.objects.order_by("sequence")))
    trip = Trip.objects.prefetch_related(Prefetch("routes", queryset=routes)).filter(pk=trip_id).first()
    if trip is None:
        raise NotFoundError("Trip not found.")
    return trip
