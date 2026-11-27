from django.contrib import admin

from .models import Checkpoint, Route, Trip


class RouteInline(admin.TabularInline):
    model = Route
    extra = 0
    fields = ("name", "distance_mi", "duration_s", "average_risk", "max_risk", "is_recommended")
    readonly_fields = fields
    show_change_link = True


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("origin_label", "destination_label", "departure_at", "load_weight_lb", "created_at")
    inlines = [RouteInline]


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("trip", "name", "distance_mi", "average_risk", "is_recommended")


@admin.register(Checkpoint)
class CheckpointAdmin(admin.ModelAdmin):
    list_display = ("route", "sequence", "mile_marker", "eta", "risk_level")
    list_filter = ("risk_level",)
