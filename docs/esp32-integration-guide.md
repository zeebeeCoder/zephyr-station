# ESP32 Integration Guide — Zephyr Weather Station

This guide describes the current private MVP ingest contract for the ESP32 master node.

## Network and TLS prerequisites

Before sending readings:

- Direct UDM DNS must resolve `omarchy.tail4e6e78.ts.net` to `192.168.1.50` on the approved IoT network.
- The station/master must have a narrow firewall allowance to TCP 443 on `192.168.1.50`; no other Zephyr host ports should be exposed.
- NTP must set an accurate system clock **before** the TLS connection. Do not send a fabricated epoch timestamp when time sync fails.
- The client must trust the certificate's CA chain and verify the hostname `omarchy.tail4e6e78.ts.net`.
- Never use an insecure TLS bypass such as `setInsecure()` or connect by IP instead of the verified hostname.
- Provision Wi-Fi credentials, trust anchors, and the ingest key outside source control. Never log them.

## Endpoint and authentication

```text
POST https://omarchy.tail4e6e78.ts.net/v1/ingest
Content-Type: application/json
x-api-key: <INGEST_API_KEY>
```

The complete HTTP request body must be no larger than 4096 bytes. Ingest is limited to **120 requests per minute per source IP**.

## Request payload

```json
{
  "device_id": "mstation",
  "timestamp": "2026-01-18T14:30:00Z",
  "readings": {
    "temperature_c": 5.2,
    "humidity_pct": 78,
    "pressure_hpa": 1013,
    "gas_density": 150.5,
    "pm1": 5,
    "pm25": 12,
    "pm10": 18,
    "wind_speed_ms": 2.3
  },
  "meta": {
    "battery_v": 3.92,
    "system_amps": 0.12,
    "rssi": -65
  }
}
```

### Required fields

| Field | Type | Allowed value |
|---|---|---|
| `device_id` | string | 1–64 characters; use `mstation` for the current station |
| `timestamp` | string | Valid ISO 8601 date-time from synchronized UTC time |
| `readings.temperature_c` | number | -50 to 60 °C |
| `readings.humidity_pct` | number | 0 to 100% |
| `readings.pressure_hpa` | number | 800 to 1200 hPa |
| `readings.pm25` | integer | 0 to 1000 µg/m³ |
| `readings.pm10` | integer | 0 to 1000 µg/m³ |
| `meta.battery_v` | number | 2.5 to 4.5 V |
| `meta.rssi` | integer | -120 to 0 dBm |

### Optional fields

| Field | Type | Allowed value |
|---|---|---|
| `readings.gas_density` | number | 0 to 1000 |
| `readings.pm1` | integer | 0 to 1000 µg/m³ |
| `readings.wind_speed_ms` | number | 0 to 100 m/s |
| `meta.system_amps` | number | 0 to 5 A |

Unknown schema behavior should not be relied on; send only documented fields.

## Generic Arduino/ESP32 example

Keep `secrets.h` out of version control. It should provide `WIFI_SSID`, `WIFI_PASSWORD`, and `INGEST_API_KEY`. `trust_anchor.h` should provide the appropriate public `ROOT_CA_PEM` trust anchor.

```cpp
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include "secrets.h"
#include "trust_anchor.h"

static const char* API_ENDPOINT =
    "https://omarchy.tail4e6e78.ts.net/v1/ingest";

// Return false unless NTP has supplied a valid UTC time.
bool getIsoTimestamp(char* output, size_t outputSize) {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) return false;
  return strftime(output, outputSize, "%Y-%m-%dT%H:%M:%SZ", &timeinfo) > 0;
}

// Return true only after the backend acknowledges the reading with HTTP 200.
bool sendReading(float temperature, float humidity, float pressure,
                 int pm25, int pm10, float battery, int rssi) {
  if (WiFi.status() != WL_CONNECTED) return false;

  char timestamp[25];
  if (!getIsoTimestamp(timestamp, sizeof(timestamp))) return false;

  StaticJsonDocument<512> document;
  document["device_id"] = "mstation";
  document["timestamp"] = timestamp;

  JsonObject readings = document.createNestedObject("readings");
  readings["temperature_c"] = temperature;
  readings["humidity_pct"] = humidity;
  readings["pressure_hpa"] = pressure;
  readings["pm25"] = pm25;
  readings["pm10"] = pm10;

  JsonObject meta = document.createNestedObject("meta");
  meta["battery_v"] = battery;
  meta["rssi"] = rssi;

  String payload;
  serializeJson(document, payload);
  if (payload.length() > 4096) return false;

  WiFiClientSecure tls;
  tls.setCACert(ROOT_CA_PEM);  // Keep hostname and CA verification enabled.

  HTTPClient http;
  if (!http.begin(tls, API_ENDPOINT)) return false;
  http.addHeader("Content-Type", "application/json");
  http.addHeader("x-api-key", INGEST_API_KEY);

  int status = http.POST(payload);
  http.end();
  return status == 200;
}
```

The sender must retain each reading in durable local storage until `sendReading` returns true. Retry connection failures and non-200 responses with bounded exponential backoff. Reusing the same `device_id` and `timestamp` is safe: the backend treats that pair idempotently. A 400 or 403 requires correcting payload/configuration; a 429 requires slowing down. Do not discard the buffered reading until a 200 response is received.

## Responses

| Status | Meaning | Sender action |
|---|---|---|
| `200` | Accepted (including an idempotent duplicate) | Remove the acknowledged item from the local buffer |
| `400` | Invalid JSON or schema validation failure | Retain item; diagnose payload before retrying |
| `403` | Missing or incorrect API key | Retain item; fix provisioning without logging the key |
| `413` | Body exceeds 4096 bytes | Retain item; reduce payload before retrying |
| `429` | More than 120 ingest requests/minute/IP | Retain item and back off |
| `500` | Database/internal failure | Retain item and retry with backoff |

Success response:

```json
{
  "status": "ok",
  "device_id": "mstation",
  "timestamp": "2026-01-18T14:30:00Z"
}
```

## Operator-only curl example

Use an environment variable supplied by an approved secret source; do not place a key in shell history or documentation.

```bash
export INGEST_API_KEY='<INGEST_API_KEY>'
curl --fail-with-body \
  -H "x-api-key: $INGEST_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "device_id": "mstation",
    "timestamp": "2026-01-18T14:30:00Z",
    "readings": {
      "temperature_c": 20.5,
      "humidity_pct": 65,
      "pressure_hpa": 1013,
      "pm25": 10,
      "pm10": 15
    },
    "meta": {
      "battery_v": 3.9,
      "rssi": -60
    }
  }' \
  https://omarchy.tail4e6e78.ts.net/v1/ingest
```

## Health and troubleshooting

Unauthenticated health routes:

- `GET https://omarchy.tail4e6e78.ts.net/up` — process liveness; returns `{"status":"ok"}`.
- `GET https://omarchy.tail4e6e78.ts.net/ready` — database and migration readiness; returns 200 with `{"status":"ready"}` or 503 with a reason.
- `GET https://omarchy.tail4e6e78.ts.net/v1/hello` — service metadata; current API version is `0.3.0`.

| Symptom | Check |
|---|---|
| DNS/connection failure | UDM DNS answer, Wi-Fi association, and the narrow IoT-to-`192.168.1.50:443` rule |
| TLS failure | NTP synchronization, trusted CA chain, and exact hostname verification |
| `403` | Key provisioning and the `x-api-key` header; never print the key |
| `400` or `413` | Required fields, ranges, ISO timestamp, JSON encoding, and serialized size |
| `429` | Aggregate send frequency behind the source IP; apply backoff |
| `500` or `/ready` 503 | Retain buffered data and retry after backend recovery |

Never work around DNS, clock, CA, or hostname errors by disabling TLS verification.
