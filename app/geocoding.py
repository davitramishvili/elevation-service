"""Geocoding client for the public Nominatim (OpenStreetMap) API.

Complies with the Nominatim usage policy:
- identifying User-Agent on every request,
- at most one request per second (enforced with an async throttle),
- results are cached by the caller (see app.cache).
"""

import asyncio
import time
from dataclasses import dataclass

import httpx

from .errors import AddressNotFoundError, UpstreamServiceError, UpstreamTimeoutError


@dataclass(frozen=True)
class GeocodeResult:
    latitude: float
    longitude: float
    display_name: str


class NominatimGeocoder:
    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        user_agent: str,
        min_interval_s: float = 1.0,
    ):
        self._client = client
        self._search_url = base_url.rstrip("/") + "/search"
        self._user_agent = user_agent
        self._min_interval_s = min_interval_s
        self._lock = asyncio.Lock()
        self._last_request_at = 0.0

    async def _throttle(self) -> None:
        """Space out requests so we never exceed 1 request/second."""
        async with self._lock:
            wait_s = self._min_interval_s - (time.monotonic() - self._last_request_at)
            if wait_s > 0:
                await asyncio.sleep(wait_s)
            self._last_request_at = time.monotonic()

    async def geocode(self, address: str) -> GeocodeResult:
        """Resolve a German postal address to WGS84 coordinates.

        Restricts results to Germany (countrycodes=de). For ambiguous input,
        Nominatim ranks matches by relevance and we take the best one.
        """
        await self._throttle()
        params = {
            "q": address,
            "format": "jsonv2",
            "countrycodes": "de",
            "limit": 1,
        }
        try:
            response = await self._client.get(
                self._search_url,
                params=params,
                headers={"User-Agent": self._user_agent},
            )
        except httpx.TimeoutException:
            raise UpstreamTimeoutError("Geocoding service timed out")
        except httpx.HTTPError as exc:
            raise UpstreamServiceError(f"Geocoding service unreachable: {exc}")

        if response.status_code != 200:
            raise UpstreamServiceError(
                f"Geocoding service returned HTTP {response.status_code}"
            )

        try:
            results = response.json()
        except ValueError:
            raise UpstreamServiceError("Geocoding service returned invalid JSON")

        if not results:
            raise AddressNotFoundError(
                f"No location in Germany matched the address: {address!r}"
            )

        best = results[0]
        try:
            # Nominatim returns lat/lon as strings.
            return GeocodeResult(
                latitude=float(best["lat"]),
                longitude=float(best["lon"]),
                display_name=best.get("display_name", ""),
            )
        except (KeyError, TypeError, ValueError):
            raise UpstreamServiceError("Geocoding service returned an unexpected payload")
