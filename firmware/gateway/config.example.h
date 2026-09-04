#ifndef CONFIG_H
#define CONFIG_H

// Copy this file to config.h and provide local credentials.
// config.h is intentionally ignored by Git.

// ===== WiFi Credentials =====
#define WIFI_SSID "your-wifi-ssid"
#define WIFI_PASS "your-wifi-password"

// ===== Zephyr Cloud API =====
#define API_ENDPOINT "https://your-api-id.execute-api.eu-central-1.amazonaws.com/v1/ingest"
#define API_KEY "your-api-key"
#define DEVICE_ID "mstation"

// ===== NTP Time Server =====
#define NTP_SERVER "pool.ntp.org"
#define GMT_OFFSET_SEC 3600       // Adjust for your timezone (e.g., 3600 for GMT+1)
#define DAYLIGHT_OFFSET_SEC 3600  // Daylight saving offset (3600 for summer/DST)

// ===== Weather Forecast (Open-Meteo) =====
#define FORECAST_LAT "your-latitude"
#define FORECAST_LON "your-longitude"
#define FORECAST_TIMEZONE "Europe%2FWarsaw"

// ===== WiFi Settings =====
#define WIFI_CONNECT_TIMEOUT_MS 10000     // 10 seconds to connect
#define WIFI_RECONNECT_INTERVAL_MS 30000  // Try reconnect every 30 seconds

#endif
