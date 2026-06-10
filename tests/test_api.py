import httpx
import respx

from .conftest import BERLIN, HOEHENDATEN_URL, NOMINATIM_URL


@respx.mock
def test_happy_path_returns_coordinates_and_elevation(client):
    respx.get(NOMINATIM_URL).respond(json=BERLIN["nominatim"])
    respx.post(HOEHENDATEN_URL).respond(json=BERLIN["hoehendaten"])

    response = client.get("/elevation", params={"address": "Pariser Platz 1, 10117 Berlin"})

    assert response.status_code == 200
    body = response.json()
    assert body["latitude"] == 52.516275
    assert body["longitude"] == 13.377704
    assert body["elevation_m"] == 34.92
    assert "Pariser Platz" in body["resolved_address"]
    assert body["data_origin"] == "DE-BB"
    assert "OpenStreetMap" in body["attribution"]


@respx.mock
def test_unknown_address_returns_404(client):
    respx.get(NOMINATIM_URL).respond(json=[])

    response = client.get("/elevation", params={"address": "Definitely Not A Real Street 999"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ADDRESS_NOT_FOUND"


@respx.mock
def test_coordinates_outside_germany_return_422(client):
    respx.get(NOMINATIM_URL).respond(json=BERLIN["nominatim"])
    respx.post(HOEHENDATEN_URL).respond(
        status_code=400,
        json={
            "Type": "PointResponse",
            "Attributes": {"Elevation": -8888.0},
            "IsError": True,
            "Error": {"Code": 400, "Title": "no elevation data"},
        },
    )

    response = client.get("/elevation", params={"address": "Pariser Platz 1, Berlin"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "OUTSIDE_COVERAGE"


@respx.mock
def test_geocoder_http_error_returns_502(client):
    respx.get(NOMINATIM_URL).respond(status_code=500)

    response = client.get("/elevation", params={"address": "Pariser Platz 1, Berlin"})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_ERROR"


@respx.mock
def test_geocoder_timeout_returns_504(client):
    respx.get(NOMINATIM_URL).mock(side_effect=httpx.ConnectTimeout("timed out"))

    response = client.get("/elevation", params={"address": "Pariser Platz 1, Berlin"})

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "UPSTREAM_TIMEOUT"


@respx.mock
def test_elevation_service_error_returns_502(client):
    respx.get(NOMINATIM_URL).respond(json=BERLIN["nominatim"])
    respx.post(HOEHENDATEN_URL).respond(status_code=503, json={"IsError": True})

    response = client.get("/elevation", params={"address": "Pariser Platz 1, Berlin"})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_ERROR"


def test_missing_address_param_is_rejected(client):
    response = client.get("/elevation")
    assert response.status_code == 422


def test_blank_address_returns_400(client):
    response = client.get("/elevation", params={"address": "   "})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_ADDRESS"


@respx.mock
def test_repeated_request_is_served_from_cache(client):
    nominatim_route = respx.get(NOMINATIM_URL).respond(json=BERLIN["nominatim"])
    elevation_route = respx.post(HOEHENDATEN_URL).respond(json=BERLIN["hoehendaten"])

    first = client.get("/elevation", params={"address": "Pariser Platz 1, 10117 Berlin"})
    second = client.get("/elevation", params={"address": "  pariser  PLATZ 1,  10117 Berlin "})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    # The second call (same address modulo case/whitespace) must not hit upstream.
    assert nominatim_route.call_count == 1
    assert elevation_route.call_count == 1


def test_healthcheck(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_demo_page_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "elevation" in response.text.lower()
