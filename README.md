# German Address Elevation Service

A small HTTP service that resolves a German postal address to its coordinates
and terrain elevation.

```
GET /elevation?address=Pariser Platz 1, 10117 Berlin
```

```json
{
  "latitude": 52.516275,
  "longitude": 13.377704,
  "elevation_m": 34.92,
  "resolved_address": "Pariser Platz, Mitte, Berlin, 10117, Deutschland",
  "data_origin": "DE-BB",
  "attribution": "Geocoding © OpenStreetMap contributors (ODbL); Elevation: © GeoBasis-DE/LGB, dl-de/by-2-0"
}
```

## How it works

1. **Geocoding** — the address is resolved to WGS84 coordinates with
   [Nominatim](https://nominatim.org/) (OpenStreetMap), restricted to Germany
   (`countrycodes=de`). For ambiguous input the highest-ranked match is used.
2. **Elevation** — the coordinates are looked up against the official **DGM1**
   (1 m grid) terrain models of the 16 German federal states via the
   [hoehendaten.de](https://hoehendaten.de) point API.
3. The combined result is returned as JSON and cached in memory.

## Quickstart

### Local

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

```bash
curl "http://127.0.0.1:8000/elevation?address=Pariser%20Platz%201%2C%2010117%20Berlin"
```

Interactive API docs: http://127.0.0.1:8000/docs

### Docker

```bash
docker build -t elevation-service .
docker run --rm -p 8000:8000 elevation-service
```

### Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The test suite mocks both upstream APIs (no network needed) and covers the
happy path, every error path, input validation, and cache behaviour.

## API

### `GET /elevation?address=...`

| Status | Meaning |
|---|---|
| 200 | Success — body matches the example above |
| 400 | `INVALID_ADDRESS` — blank address |
| 404 | `ADDRESS_NOT_FOUND` — nothing in Germany matched the address |
| 422 | `OUTSIDE_COVERAGE` — resolved coordinates have no German elevation data |
| 502 | `UPSTREAM_ERROR` — a dependency failed or answered unexpectedly |
| 504 | `UPSTREAM_TIMEOUT` — a dependency timed out |

Errors share one shape:

```json
{ "error": { "code": "ADDRESS_NOT_FOUND", "message": "..." } }
```

### `GET /healthz`

Liveness probe, returns `{"status": "ok"}`.

## Design decisions

- **Pass-through coordinates, no projection step.** The hoehendaten.de point
  API accepts WGS84 decimal degrees directly, so Nominatim output feeds
  straight into the elevation lookup. (Gotcha handled: the API is served on
  port `14444`; the standard HTTPS port presents a different certificate.)
- **Nominatim usage policy compliance.** Identifying `User-Agent`, at most one
  request per second (enforced with an async throttle), and client-side
  caching of results.
- **Caching.** Address → result is cached in an in-memory TTL/LRU cache
  (default 24 h, 1024 entries): elevations for a fixed address do not change,
  and it keeps repeated queries from hitting the rate-limited upstreams.
- **Explicit error taxonomy.** Each failure mode maps to a stable `code` and
  an appropriate HTTP status (table above) so clients can branch on outcomes
  instead of parsing messages.
- **Provider abstraction.** The elevation backend sits behind a small
  interface (`ElevationProvider`), so a local raster lookup over downloaded
  DGM GeoTIFF tiles could replace the hosted API without touching the HTTP
  layer.
- **Configuration via environment.** Upstream URLs, timeouts, throttle and
  cache parameters are env-configurable (see `app/config.py`) — also used by
  the tests to run deterministically.

## Limitations and possible next steps

- The public Nominatim instance is rate-limited (1 req/s); for production
  traffic, a self-hosted Nominatim or a commercial geocoder would replace it
  (one constructor argument).
- In-memory cache resets on restart; Redis would be the natural next step for
  multiple replicas.
- Elevation is looked up for the single best geocoding match. A `candidates`
  mode (return all matches with elevations) would be a small extension.
- No authentication — out of scope for the assessment.
