from django.urls import path

from .views import GeocodeSearchView

urlpatterns = [path("search/", GeocodeSearchView.as_view(), name="geocode-search")]
