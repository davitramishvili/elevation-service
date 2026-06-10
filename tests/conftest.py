import os

# Make tests fast and deterministic: no Nominatim throttling, tiny cache TTL
# is NOT set here because cache behaviour is part of what we test.
os.environ.setdefault("NOMINATIM_MIN_INTERVAL_S", "0")

import pytest
from fastapi.testclient import TestClient

from app.main import app

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HOEHENDATEN_URL = "https://api.hoehendaten.de:14444/v1/point"

# Verified live values for the Brandenburg Gate area in Berlin.
BERLIN = {
    "nominatim": [
        {
            "lat": "52.516275",
            "lon": "13.377704",
            "display_name": "Pariser Platz, Mitte, Berlin, 10117, Deutschland",
        }
    ],
    "hoehendaten": {
        "Type": "PointResponse",
        "ID": "test",
        "Attributes": {
            "Longitude": 13.377704,
            "Latitude": 52.516275,
            "Elevation": 34.92,
            "Actuality": "2021-01-01",
            "Origin": "DE-BB",
            "Attribution": "© GeoBasis-DE/LGB, dl-de/by-2-0",
        },
        "IsError": False,
    },
}


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        # Each test starts with an empty cache.
        app.state.cache._store.clear()
        yield test_client
