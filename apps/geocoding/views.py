from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import GeocodeQuerySerializer, PlaceSerializer
from .services import GeocodingService


class GeocodeSearchView(APIView):
    @extend_schema(
        tags=["geocoding"],
        summary="Search places by free text",
        parameters=[GeocodeQuerySerializer],
        responses=PlaceSerializer(many=True),
    )
    def get(self, request):
        query = GeocodeQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        places = GeocodingService().search(params["q"], params["limit"])
        return Response(PlaceSerializer(places, many=True).data)
