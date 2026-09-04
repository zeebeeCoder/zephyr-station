#ifndef CONFIG_H
#define CONFIG_H

// Copy this file to config.h and provide local credentials.
// config.h is intentionally ignored by Git.

// ===== WiFi Credentials =====
#define WIFI_SSID "your-wifi-ssid"
#define WIFI_PASS "your-wifi-password"

// ===== Zephyr Cloud API =====
// The endpoint is non-secret; access still requires network reachability and the API key.
#define API_ENDPOINT "https://omarchy.tail4e6e78.ts.net/v1/ingest"
#define API_KEY "your-api-key"
#define DEVICE_ID "mstation"

// ===== NTP Time Server =====
#define NTP_SERVER "pool.ntp.org"
// Keep system time in UTC because gateway timestamps are emitted with a trailing Z.
#define GMT_OFFSET_SEC 0
#define DAYLIGHT_OFFSET_SEC 0

// ===== Weather Forecast (Open-Meteo) =====
#define FORECAST_LAT "your-latitude"
#define FORECAST_LON "your-longitude"
#define FORECAST_TIMEZONE "Europe%2FWarsaw"

// ===== WiFi Settings =====
#define WIFI_CONNECT_TIMEOUT_MS 10000     // 10 seconds to connect
#define WIFI_RECONNECT_INTERVAL_MS 30000  // Try reconnect every 30 seconds

#endif
