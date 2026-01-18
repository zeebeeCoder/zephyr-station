# ESP32 Integration Guide - Zephyr Weather Station

This guide explains how to send sensor data from the ESP32 to the Zephyr cloud backend.

---

## Endpoint

```
POST https://yvsssrfmu6.execute-api.eu-central-1.amazonaws.com/v1/ingest
```

---

## Authentication

All requests must include the API key in the header:

```
x-api-key: QbPVnWBMOh4fqrhYFaq0h18La6EvEMI98CL9hO7E
```

---

## Request Format

**Content-Type:** `application/json`

### JSON Payload

```json
{
  "device_id": "station-01",
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

---

## Field Reference

### Required Fields

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `device_id` | string | 1-64 chars | Station identifier (use `"station-01"`) |
| `timestamp` | string | ISO 8601 | Reading time (e.g., `"2026-01-18T14:30:00Z"`) |
| `readings.temperature_c` | number | -50 to 60 | Temperature in Celsius |
| `readings.humidity_pct` | number | 0 to 100 | Relative humidity % |
| `readings.pressure_hpa` | number | 800 to 1200 | Atmospheric pressure in hPa |
| `readings.pm25` | integer | 0 to 1000 | PM2.5 in µg/m³ |
| `readings.pm10` | integer | 0 to 1000 | PM10 in µg/m³ |
| `meta.battery_v` | number | 2.5 to 4.5 | Battery voltage |
| `meta.rssi` | integer | -120 to 0 | LoRa signal strength in dBm |

### Optional Fields

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `readings.gas_density` | number | 0 to 1000 | Gas sensor reading |
| `readings.pm1` | integer | 0 to 1000 | PM1.0 in µg/m³ |
| `readings.wind_speed_ms` | number | 0 to 100 | Wind speed in m/s |
| `meta.system_amps` | number | 0 to 5 | System current draw in A |

---

## Arduino/ESP32 Example

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

const char* WIFI_SSID = "your-wifi";
const char* WIFI_PASS = "your-password";

const char* API_ENDPOINT = "https://yvsssrfmu6.execute-api.eu-central-1.amazonaws.com/v1/ingest";
const char* API_KEY = "QbPVnWBMOh4fqrhYFaq0h18La6EvEMI98CL9hO7E";

void sendReading(float temp, float humidity, float pressure, int pm25, int pm10, float battery, int rssi) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected");
    return;
  }

  HTTPClient http;
  http.begin(API_ENDPOINT);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("x-api-key", API_KEY);

  // Build JSON payload
  StaticJsonDocument<512> doc;
  doc["device_id"] = "station-01";
  doc["timestamp"] = getISOTimestamp();  // Implement this to return ISO 8601 string

  JsonObject readings = doc.createNestedObject("readings");
  readings["temperature_c"] = temp;
  readings["humidity_pct"] = humidity;
  readings["pressure_hpa"] = pressure;
  readings["pm25"] = pm25;
  readings["pm10"] = pm10;

  JsonObject meta = doc.createNestedObject("meta");
  meta["battery_v"] = battery;
  meta["rssi"] = rssi;

  String payload;
  serializeJson(doc, payload);

  Serial.println("Sending: " + payload);

  int httpCode = http.POST(payload);

  if (httpCode == 200) {
    Serial.println("Success!");
    String response = http.getString();
    Serial.println(response);
  } else {
    Serial.printf("Error: %d\n", httpCode);
    Serial.println(http.getString());
  }

  http.end();
}

// Helper: Get ISO 8601 timestamp
String getISOTimestamp() {
  // If using NTP time:
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    return "1970-01-01T00:00:00Z";
  }
  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
  return String(buffer);
}
```

---

## Response Codes

| Code | Meaning | Action |
|------|---------|--------|
| **200** | Success | Data stored successfully |
| **400** | Bad Request | Check payload format/validation |
| **403** | Forbidden | Check API key is correct |
| **500** | Server Error | Retry after delay |

### Success Response

```json
{
  "status": "ok",
  "device_id": "station-01",
  "timestamp": "2026-01-18T14:30:00Z"
}
```

### Validation Error Response

```json
{
  "error": {
    "message": "Validation failed",
    "errors": [
      { "path": "readings.temperature_c", "message": "Required" }
    ]
  }
}
```

---

## Testing with curl

```bash
curl -X POST https://yvsssrfmu6.execute-api.eu-central-1.amazonaws.com/v1/ingest \
  -H "x-api-key: QbPVnWBMOh4fqrhYFaq0h18La6EvEMI98CL9hO7E" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "station-01",
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
  }'
```

---

## Rate Limits

| Limit | Value |
|-------|-------|
| Requests per second | 5 |
| Burst limit | 10 |
| Daily quota | 10,000 |

For a reading every 5 minutes: ~288 requests/day (well within limits).

---

## Health Check

To verify the API is running:

```bash
curl https://yvsssrfmu6.execute-api.eu-central-1.amazonaws.com/v1/hello
```

Response:
```json
{
  "message": "Hello from Zephyr!",
  "service": "zephyr",
  "version": "0.2.0"
}
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 403 Forbidden | Verify `x-api-key` header is correct |
| 400 Bad Request | Check JSON format, required fields, value ranges |
| Connection timeout | Check WiFi, verify endpoint URL |
| SSL error | Ensure ESP32 has updated root CA certificates |

---

## Contact

Questions? Check the main repo: https://github.com/zeebeeCoder/zephyr-station
