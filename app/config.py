"""Application settings, read from environment variables with sane defaults."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    nominatim_base_url: str
    hoehendaten_url: str
    user_agent: str
    request_timeout_s: float
    nominatim_min_interval_s: float
    cache_ttl_s: float
    cache_max_entries: int


def load_settings() -> Settings:
    return Settings(
        nominatim_base_url=os.getenv(
            "NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org"
        ),
        # Note: the hoehendaten.de API is served on port 14444.
        hoehendaten_url=os.getenv(
            "HOEHENDATEN_URL", "https://api.hoehendaten.de:14444/v1/point"
        ),
        # Nominatim's usage policy requires an identifying User-Agent.
        user_agent=os.getenv(
            "HTTP_USER_AGENT",
            "elevation-service/1.0 (ramishvilid496@gmail.com)",
        ),
        request_timeout_s=float(os.getenv("REQUEST_TIMEOUT_S", "10")),
        # Nominatim allows at most 1 request per second.
        nominatim_min_interval_s=float(os.getenv("NOMINATIM_MIN_INTERVAL_S", "1.0")),
        cache_ttl_s=float(os.getenv("CACHE_TTL_S", "86400")),
        cache_max_entries=int(os.getenv("CACHE_MAX_ENTRIES", "1024")),
    )
