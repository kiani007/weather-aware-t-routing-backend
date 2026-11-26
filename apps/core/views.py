from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    throttle_classes = []

    @extend_schema(
        tags=["system"],
        summary="Service health check",
        responses=inline_serializer("Health", {"status": serializers.CharField()}),
    )
    def get(self, request):
        return Response({"status": "ok"})
