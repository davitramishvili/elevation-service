"""Elevation lookup backed by the hoehendaten.de point API.

hoehendaten.de serves official DGM1 (1 m grid) terrain models from all 16
German federal states. The API accepts WGS84 decimal degrees directly, so the
coordinates we get from geocoding can be passed through without a projection
step.

The provider is kept behind a small interface so an alternative backend
(e.g. a local raster lookup over downloaded DGM tiles) could be swapped in
without touching the API layer.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from .errors import OutsideCoverageError, UpstreamServiceError, UpstreamTimeoutError

# The API reports this elevation value when no dataset covers the coordinates.
NO_DATA_SENTINEL = -8888.0


@dataclass(frozen=True)
class ElevationResult:
    elevation_m: float
    attribution: str | None = None
    origin: str | None = None  # federal-state dataset code, e.g. "DE-BB"


class ElevationProvider(ABC):
    @abstractmethod
    async def get_elevation(self, latitude: float, longitude: float) -> ElevationResult: ...


class HoehendatenClient(ElevationProvider):
    """Client for POST https://api.hoehendaten.de:14444/v1/point.

    Note: the service runs on port 14444; the default HTTPS port serves a
    different certificate and must not be used.
    """

    def __init__(self, client: httpx.AsyncClient, url: str, user_agent: str):
        self._client = client
        self._url = url
        self._user_agent = user_agent

    async def get_elevation(self, latitude: float, longitude: float) -> ElevationResult:
        payload = {
            "Type": "PointRequest",
            "ID": uuid.uuid4().hex,
            "Attributes": {
                "Longitude": longitude,
                "Latitude": latitude,
            },
        }
        try:
            response = await self._client.post(
                self._url,
                json=payload,
                headers={
                    "User-Agent": self._user_agent,
                    # The API validates this header and rejects requests without it.
                    "Accept": "application/json",
                },
            )
        except httpx.TimeoutException:
            raise UpstreamTimeoutError("Elevation service timed out")
        except httpx.HTTPError as exc:
            raise UpstreamServiceError(f"Elevation service unreachable: {exc}")

        try:
            body = response.json()
        except ValueError:
            raise UpstreamServiceError(
                f"Elevation service returned invalid JSON (HTTP {response.status_code})"
            )

        attributes = body.get("Attributes") or {}
        elevation = attributes.get("Elevation")
        is_error = bool(body.get("IsError")) or response.status_code != 200

        if is_error or elevation is None or float(elevation) == NO_DATA_SENTINEL:
            if elevation is not None and float(elevation) == NO_DATA_SENTINEL:
                raise OutsideCoverageError(
                    "The resolved coordinates are outside the German elevation datasets"
                )
            error = body.get("Error") or {}
            detail = error.get("Detail") or error.get("Title") or f"HTTP {response.status_code}"
            raise UpstreamServiceError(f"Elevation service error: {detail}")

        return ElevationResult(
            elevation_m=float(elevation),
            attribution=attributes.get("Attribution"),
            origin=attributes.get("Origin"),
        )
