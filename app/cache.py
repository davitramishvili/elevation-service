"""Small in-memory TTL + LRU cache.

Caching geocoding results client-side is explicitly required by the Nominatim
usage policy, and elevation values for a fixed address never change, so both
are safe to cache aggressively.
"""

import time
from collections import OrderedDict
from typing import Any, Hashable


class TTLCache:
    def __init__(self, max_entries: int = 1024, ttl_s: float = 86400.0):
        self._max_entries = max_entries
        self._ttl_s = ttl_s
        self._store: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()

    def get(self, key: Hashable) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() >= expires_at:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key: Hashable, value: Any) -> None:
        self._store[key] = (time.monotonic() + self._ttl_s, value)
        self._store.move_to_end(key)
        while len(self._store) > self._max_entries:
            self._store.popitem(last=False)

    def __len__(self) -> int:
        return len(self._store)
