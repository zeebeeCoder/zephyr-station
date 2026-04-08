# Widget + History API Extension Spec

**Status:** Draft
**Date:** 2026-04-08
**Scope:** `infrastructure/src/routes/widget.mjs`, `infrastructure/src/routes/history.mjs`, API Gateway config
**Consumers:** iOS app (`ios/ZephyrStation`), future web dashboard

---

## 1. Motivation

The iOS app today makes two kinds of calls:

1. `GET /v1/widget?device_id=mstation` — latest reading for all 9 metrics, on app open.
2. `GET /v1/history?device_id=mstation&metric={m}&range={r}` — one metric, one range, on every card tap or range switch.

Observed problems:

- **Tap-through latency**: tapping a metric card triggers a cold network round trip before the chart appears. On cellular this is visibly slow.
- **Oversized 24h responses**: `/history` returns raw rows for `24h`. At ~1 reading/min that's ~1440 points to render a ~300px chart — wasted bandwidth and JSON parse time.
- **No HTTP caching**: range switches re-fetch data that hasn't changed (e.g. 30d data shifts only every few hours).
- **Client-side stat computation**: `HistoryChartView` recomputes min/max/avg in Swift on every render — the server already has the data.
- **No compression**: API Gateway responses are uncompressed JSON.

## 2. Design goals

- **Instant tap-through**: chart visible <50ms after a card tap, even on cold cellular.
- **Smaller payloads**: optimize for battery- and data-constrained iOS widget context.
- **No new endpoints unless they earn it**: extend `/widget` and `/history` rather than proliferate routes.
- **Zero new iOS dependencies**: stay on URLSession + Codable.
- **Backwards compatible**: existing callers (web debug, current iOS build) must keep working unchanged.
- **Independently shippable**: each change revertable on its own.

## 3. Non-goals

- GraphQL (rejected — Apollo iOS cost too high for the payload size).
- New `/metric/:name` endpoint (would duplicate `/history` logic).
- Multi-metric history in one call (no current consumer).
- WebSocket / SSE live updates (out of scope).
- Pagination (bounded point counts make it unnecessary).

## 4. Performance targets

| Metric | Today (est.) | Target |
|---|---|---|
| Tap-to-chart latency (cellular, warm app) | 400–900 ms | **<50 ms** (served from in-memory sparkline) |
| `/widget` payload (uncompressed) | ~600 B | <2.5 KB with sparklines |
| `/widget` payload (gzip) | ~600 B | **<700 B with sparklines** |
| `/history?range=24h` payload (gzip) | ~8–15 KB | **<2 KB** |
| `/history?range=7d` payload (gzip) | ~3 KB | <1.5 KB |
| `/history?range=30d` payload (gzip) | ~12 KB | <2 KB |
| Lambda p95 (`/widget` with sparklines) | n/a | <250 ms |
| Lambda p95 (`/history`) | <200 ms | <200 ms (no regression) |
| Lambda invocations / day (steady state) | ~unbounded by client | ≥30% reduction via Cache-Control |

All response point counts are bounded so payload size is independent of cadence/range.

---

## 5. API contract changes

### 5.1 `GET /v1/widget` — opt-in sparklines

**New query parameter:**

| param | type | required | values | default |
|---|---|---|---|---|
| `include` | csv string | no | `sparklines` | unset |

**Behavior:**

- When `include` is unset: response is **identical to today** (full backwards compatibility).
- When `include=sparklines`: response gains a top-level `sparklines` object.

**Sparkline shape:**

```json
{
  "device_id": "mstation",
  "recorded_at": "2026-04-08T10:00:00.000Z",
  "readings": { ...unchanged... },
  "meta": { ...unchanged... },
  "station_status": "online",
  "data_age_seconds": 42,
  "sparklines": {
    "window": "24h",
    "bucket_minutes": 60,
    "bucket_count": 24,
    "bucket_end": "2026-04-08T10:00:00.000Z",
    "metrics": {
      "temperature_c": {
        "unit": "°C",
        "stats": { "min": 4.2, "max": 11.8, "avg": 7.6, "count": 24 },
        "values": [7.1, 6.9, 6.8, /* ...22 more... */ ]
      },
      "humidity_pct": { "unit": "%",   "stats": {...}, "values": [...] },
      "pressure_hpa": { "unit": "hPa", "stats": {...}, "values": [...] },
      "wind_speed_ms":{ "unit": "m/s", "stats": {...}, "values": [...] },
      "pm1":          { "unit": "µg/m³", "stats": {...}, "values": [...] },
      "pm25":         { "unit": "µg/m³", "stats": {...}, "values": [...] },
      "pm10":         { "unit": "µg/m³", "stats": {...}, "values": [...] },
      "gas_density":  { "unit": "kΩ",  "stats": {...}, "values": [...] },
      "battery_v":    { "unit": "V",   "stats": {...}, "values": [...] }
    }
  }
}
```

**Design notes:**

- **No timestamps inside `values`** — they are implicit from `bucket_end`, `bucket_minutes`, and array index. Saves ~60% of bytes vs `[{t,v},...]`.
- `values[i]` is the average for bucket `[bucket_end - (bucket_count - i) * bucket_minutes, bucket_end - (bucket_count - i - 1) * bucket_minutes)`.
- A `null` entry in `values` means "no data in this bucket" (offline window). iOS must handle gaps.
- Always exactly 24 entries per metric, even if some are null. Predictable shape = simpler decoding.
- All sparkline data fetched in **one SQL query** (single round trip to Postgres).

**iOS consumption pattern:**

1. App open → `GET /v1/widget?device_id=mstation&include=sparklines`. Cache the response in `WeatherService`.
2. Card tap → `MiniChartSheet` renders **immediately** from the cached sparkline values + stats.
3. Optionally fire a background `GET /v1/history?range=24h&...` for the high-res 96-point version and swap it in once it arrives.

### 5.2 `GET /v1/history` — bounded point counts + stats block

**Query parameters:** unchanged (`device_id`, `metric`, `range`).

**Behavior changes:**

- All responses are downsampled server-side to a fixed, bounded point count.
- Response gains a `stats` block.
- `points` shape unchanged (`{t, v}`) for backwards compatibility.

**Bucketing table:**

| range | current behavior | new behavior | bucket size | point count |
|---|---|---|---|---|
| `24h` | raw rows (~1440) | 15-min averages | 15 min | **96** |
| `7d`  | hourly averages (168) | 2-hour averages | 2 hr | **84** |
| `30d` | hourly averages (720) | 6-hour averages | 6 hr | **120** |

All three responses are ~100 points. iPhone screens are ~300–400 px wide; >100 points is wasted resolution.

**New response shape:**

```json
{
  "device_id": "mstation",
  "metric": "temperature_c",
  "range": "24h",
  "unit": "°C",
  "bucket_minutes": 15,
  "stats": {
    "min": 4.2,
    "max": 11.8,
    "avg": 7.6,
    "count": 96
  },
  "points": [
    { "t": "2026-04-07T10:15:00.000Z", "v": 7.1 },
    { "t": "2026-04-07T10:30:00.000Z", "v": 6.9 }
  ]
}
```

**Compatibility note:** Adding `bucket_minutes` and `stats` is additive — existing decoders that ignore unknown fields continue to work. iOS `HistoryResponse` can adopt them and delete the client-side min/max/avg loop in `HistoryChartView`.

**Null handling:** `v` may be `null` for buckets with no readings. iOS chart already handles missing points; behavior unchanged.

### 5.3 HTTP caching headers

Add `Cache-Control` to both endpoints. Values chosen so cached data is never staler than the underlying data cadence:

| endpoint | header |
|---|---|
| `GET /v1/widget` (with or without sparklines) | `Cache-Control: public, max-age=30` |
| `GET /v1/history?range=24h` | `Cache-Control: public, max-age=60` |
| `GET /v1/history?range=7d`  | `Cache-Control: public, max-age=300` |
| `GET /v1/history?range=30d` | `Cache-Control: public, max-age=900` |

**Rationale:** widget cadence is ~1 min so 30s is fresh enough. 30d data shifts only every few hours of new readings, so 15 min cache is safe and dramatically cuts Lambda invocations.

`ETag` / `If-None-Match` is a nice-to-have but out of scope for this spec.

### 5.4 Compression

Enable gzip on API Gateway for all `application/json` responses. JSON compresses ~5×. One config flag in Pulumi.

---

## 6. Implementation order

Each step is independently valuable, independently revertable, and additive (no breaking changes).

1. **gzip on API Gateway** — config flag, ~5× payload reduction across the board, zero code.
2. **`/v1/history` downsampling + stats block** — one SQL change, additive response fields, immediate iOS payload win.
3. **`Cache-Control` headers** — one-line per route, cuts Lambda bill and warms responses for repeat callers.
4. **`/v1/widget?include=sparklines`** — needs design review (changes the widget contract surface). Ship last so the rest can land independently.

iOS adoption is a separate, follow-up change:

- After step 2: delete client-side min/max/avg loop in `HistoryChartView`, read from `stats`.
- After step 4: extend `WeatherService` to request `include=sparklines`, cache the response, render `MiniChartSheet` from the in-memory sparkline before falling back to a `/history` call.

## 7. Risks and open questions

- **Sparkline payload growth**: 9 metrics × 24 floats ≈ 216 numbers. With stats blocks and JSON overhead, ~2 KB uncompressed. Acceptable for the once-per-app-open call but worth measuring after gzip.
- **Bucket alignment**: should `bucket_end` snap to wall-clock hour boundaries or be "now"? Wall-clock alignment improves cache hit rate (multiple clients within the same minute share a cached response). Recommend: snap `bucket_end` to the nearest minute and let `Cache-Control` do the rest.
- **Null bucket density**: if the station is offline for hours, sparklines fill with nulls. Confirm iOS chart renders gaps gracefully (it does today for `/history`).
- **Cache invalidation on fresh ingest**: with `max-age=30` on `/widget`, a brand-new reading may take up to 30s to appear. Acceptable given the 1-min cadence; document for the user.
- **API Gateway gzip min size**: AWS only gzips responses above a configurable threshold (default 0, but worth verifying for the small `/widget` baseline payload).

## 8. Out of scope (future work)

- ETag / 304 Not Modified support.
- WebSocket / SSE for sub-second live updates.
- Multi-metric history endpoint (`?metrics=temp,humidity`) — revisit if a web dashboard ships with multi-series charts.
- A web dashboard would be the strongest justification for revisiting GraphQL; iOS alone is not.
