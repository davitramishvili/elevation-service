"""German address elevation service.

GET /elevation?address=<German postal address>
    -> {"latitude": ..., "longitude": ..., "elevation_m": ...}

Pipeline: address -> Nominatim geocoding (Germany only) -> hoehendaten.de
elevation lookup (official DGM1 federal-state data) -> JSON response.
"""

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

from .cache import TTLCache
from .config import load_settings
from .elevation import HoehendatenClient
from .errors import InvalidAddressError, ServiceError
from .geocoding import NominatimGeocoder
from .schemas import ElevationResponse, ErrorResponse

OSM_ATTRIBUTION = "Geocoding © OpenStreetMap contributors (ODbL)"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    client = httpx.AsyncClient(timeout=settings.request_timeout_s)
    app.state.geocoder = NominatimGeocoder(
        client,
        base_url=settings.nominatim_base_url,
        user_agent=settings.user_agent,
        min_interval_s=settings.nominatim_min_interval_s,
    )
    app.state.elevation = HoehendatenClient(
        client, url=settings.hoehendaten_url, user_agent=settings.user_agent
    )
    app.state.cache = TTLCache(
        max_entries=settings.cache_max_entries, ttl_s=settings.cache_ttl_s
    )
    try:
        yield
    finally:
        await client.aclose()


app = FastAPI(
    title="German Address Elevation Service",
    version="1.0.0",
    description=(
        "Resolves a German postal address to coordinates and terrain elevation. "
        "Geocoding by OpenStreetMap Nominatim; elevation from the official DGM1 "
        "datasets of the German federal states via hoehendaten.de."
    ),
    lifespan=lifespan,
)


@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.get(
    "/elevation",
    response_model=ElevationResponse,
    response_model_exclude_none=True,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid address input"},
        404: {"model": ErrorResponse, "description": "Address not found in Germany"},
        422: {"model": ErrorResponse, "description": "Coordinates outside dataset coverage"},
        502: {"model": ErrorResponse, "description": "Upstream service error"},
        504: {"model": ErrorResponse, "description": "Upstream service timeout"},
    },
)
async def get_elevation(
    request: Request,
    address: str = Query(
        ...,
        description="German postal address, e.g. 'Pariser Platz 1, 10117 Berlin'",
    ),
) -> ElevationResponse:
    normalized = " ".join(address.split())
    if not normalized:
        raise InvalidAddressError("Address must not be empty")

    cache = request.app.state.cache
    cache_key = normalized.lower()
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    geocoded = await request.app.state.geocoder.geocode(normalized)
    elevation = await request.app.state.elevation.get_elevation(
        geocoded.latitude, geocoded.longitude
    )

    attribution_parts = [OSM_ATTRIBUTION]
    if elevation.attribution:
        attribution_parts.append(f"Elevation: {elevation.attribution}")

    result = ElevationResponse(
        latitude=geocoded.latitude,
        longitude=geocoded.longitude,
        # The DGM1 source is a 1 m grid; round off float32 representation noise.
        elevation_m=round(elevation.elevation_m, 2),
        resolved_address=geocoded.display_name or None,
        data_origin=elevation.origin,
        attribution="; ".join(attribution_parts),
    )
    cache.set(cache_key, result)
    return result


@app.get("/healthz", include_in_schema=False)
async def healthz() -> dict:
    return {"status": "ok"}
