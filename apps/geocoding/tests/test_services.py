from django.core.cache import cache
from django.test import SimpleTestCase

from apps.core.exceptions import ExternalServiceError
from apps.geocoding.clients import OpenMeteoGeocodingClient, PhotonClient
from apps.geocoding.domain import Place
from apps.geocoding.services import GeocodingService

DENVER = Place("Denver, Colorado, United States", 39.74, -104.98)


class FakeClient:
    def __init__(self, name, places=None, fails=False):
        self.name = name
        self.places = places or []
        self.fails = fails
        self.calls = 0

    def search(self, query, limit):
        self.calls += 1
        if self.fails:
            raise ExternalServiceError(f"{self.name} is unavailable.")
        return self.places


class FakeHttp:
    def __init__(self, payload):
        self.payload = payload

    def get(self, path, params=None):
        return self.payload


class GeocodingServiceTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_uses_the_primary_provider_when_it_works(self):
        primary, backup = FakeClient("photon", [DENVER]), FakeClient("open-meteo", [])
        self.assertEqual(GeocodingService([primary, backup]).search("Denver"), [DENVER])
        self.assertEqual(backup.calls, 0)

    def test_falls_back_when_the_primary_provider_fails(self):
        primary, backup = FakeClient("photon", fails=True), FakeClient("open-meteo", [DENVER])
        self.assertEqual(GeocodingService([primary, backup]).search("Denver"), [DENVER])

    def test_skips_a_failed_provider_for_a_while(self):
        primary, backup = FakeClient("photon", fails=True), FakeClient("open-meteo", [DENVER])
        service = GeocodingService([primary, backup])
        service.search("Denver")
        service.search("Chicago")
        self.assertEqual(primary.calls, 1)
        self.assertEqual(backup.calls, 2)

    def test_raises_when_every_provider_fails(self):
        service = GeocodingService([FakeClient("photon", fails=True), FakeClient("open-meteo", fails=True)])
        with self.assertRaises(ExternalServiceError):
            service.search("Denver")


class ClientParsingTests(SimpleTestCase):
    def test_open_meteo_results_become_labelled_places(self):
        payload = {"results": [{"name": "Denver", "admin1": "Colorado", "country": "United States",
                                "latitude": 39.74, "longitude": -104.98}]}
        places = OpenMeteoGeocodingClient(http=FakeHttp(payload)).search("denver", 5)
        self.assertEqual(places, [DENVER])

    def test_open_meteo_with_no_results(self):
        self.assertEqual(OpenMeteoGeocodingClient(http=FakeHttp({})).search("zzzz", 5), [])

    def test_photon_features_become_labelled_places(self):
        payload = {"features": [{"geometry": {"coordinates": [-104.98, 39.74]},
                                 "properties": {"name": "Denver", "state": "Colorado", "country": "United States"}}]}
        self.assertEqual(PhotonClient(http=FakeHttp(payload)).search("denver", 5), [DENVER])
