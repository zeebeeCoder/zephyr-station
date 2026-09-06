/*
 * Solar Weather Station - Indoor Receiver with Cloud Upload
 *
 * Receives and decodes 24-byte binary packets from outdoor station
 * Displays weather data on 2.4" ILI9341 TFT (320x240 landscape)
 * Uploads data to Zephyr cloud API via WiFi
 * Press button to request fresh data from outdoor station on-demand
 *
 * Hardware:
 * - ESP32 Dev Kit
 * - Seeed Grove LoRa Radio 868MHz with UART bridge
 * - Waveshare 2.4" ILI9341 TFT (240x320, SPI) in landscape mode
 * - Push button (or use built-in BOOT button on GPIO0)
 *
 * Wiring:
 *   Seeed Grove LoRa Radio 868MHz (UART bridge):
 *     Yellow (RX) → GPIO17 (ESP32 TX2)
 *     White (TX)  → GPIO16 (ESP32 RX2)
 *     Red (VCC)   → 5V
 *     Black (GND) → GND
 *
 *   ILI9341 TFT (SPI):
 *     DIN (MOSI) → GPIO23 (VSPI default MOSI)
 *     CLK        → GPIO18 (VSPI default CLK)
 *     CS         → GPIO5  (VSPI default CS)
 *     DC         → GPIO2  (Data/Command)
 *     RST        → GPIO4  (Reset)
 *     BL         → 3.3V
 *     VCC        → 3.3V
 *     GND        → GND
 *
 *   Request Button (optional - can use BOOT button):
 *     One side  → GPIO0
 *     Other side → GND
 *
 * Libraries:
 *   - Seeed Grove LoRa Radio 433MHz/868MHz library (UART RH_RF95 fork)
 *   - Adafruit GFX Library
 *   - Adafruit ILI9341
 *   - ArduinoJson
 */

#include <SPI.h>
#include <HardwareSerial.h>
#include <RH_RF95.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <math.h>
#include <time.h>
#include "config.h"

// ===== PIN DEFINITIONS =====
// LoRa
#define LORA_RX 16
#define LORA_TX 17

// TFT (SPI)
#define TFT_CS   5
#define TFT_DC   2
#define TFT_RST  4
// Backlight wired directly to 3.3V (no GPIO control needed)

// Request Button
#define BUTTON_PIN 0  // GPIO0 (BOOT button on most ESP32 dev boards)

// ===== TFT CONFIGURATION =====
#define SCREEN_WIDTH 320
#define SCREEN_HEIGHT 240

// ===== COLOR PALETTE (retro red/white) =====
#define COLOR_BG      0x0000  // black
#define COLOR_TEXT     0xFFFF  // white
#define COLOR_DIM     0x6B4D  // dim gray
#define COLOR_HEADER  0x6000  // dark red fill
#define COLOR_ACCENT  0xF800  // red (borders, accents)
#define COLOR_WARM    0xFB40  // light red/salmon
#define COLOR_GREEN   0xF800  // red (replaces green for theme)
#define COLOR_RED     0xF800  // red
#define COLOR_YELLOW  0xFB40  // light red (replaces yellow)
#define COLOR_OK      0x07E0  // actual green for OK status only
#define COLOR_FAIL    0xF800  // red for FAIL status
#define COLOR_BLUE    0x04DF  // medium blue (rain)
#define COLOR_LTBLUE  0x867F  // light blue (low rain)
#define COLOR_CYAN    0x07FF  // cyan (low temps)

// ===== LORA CONFIGURATION =====
#define LORA_FREQUENCY 868.0  // Must match transmitter

// ===== DISPLAY PAGES =====
#define PAGE_MAIN 0
#define PAGE_AIR_QUALITY 1
#define PAGE_STATUS 2
#define PAGE_FORECAST_HOURLY 3
#define PAGE_FORECAST_DAILY 4
#define NUM_PAGES 5
#define PAGE_DURATION 10000  // 10 seconds per page

// ===== REQUEST PROTOCOL =====
#define CMD_REQUEST_DATA 0x01
#define REQUEST_MAGIC_1 0xAA
#define REQUEST_MAGIC_2 0x55
#define REQUEST_TIMEOUT_MS 120000  // 2 minute timeout waiting for response
#define BUTTON_DEBOUNCE_MS 300

// ===== GLOBAL OBJECTS =====
// Hardware SPI: VSPI defaults (CLK=GPIO18, MOSI=GPIO23)
Adafruit_ILI9341 tft = Adafruit_ILI9341(TFT_CS, TFT_DC, TFT_RST);
HardwareSerial loraSerial(2);
RH_RF95 rf95(loraSerial);

// ===== STATISTICS =====
uint32_t packetsReceived = 0;
uint32_t packetsFailed = 0;
unsigned long lastPacketTime = 0;
uint8_t currentPage = PAGE_MAIN;
unsigned long lastPageChange = 0;

// ===== DISPLAY STATE TRACKING =====
int8_t lastRenderedPage = -1;       // -1=none, -2=waiting, -3=requesting
uint16_t lastRenderedPacket = 0xFFFF;
bool lastRenderedWifi = false;

// ===== BUTTON STATE =====
unsigned long lastButtonPress = 0;
bool requestPending = false;
unsigned long requestSentTime = 0;
unsigned long lastRequestResend = 0;
#define REQUEST_RESEND_INTERVAL_MS 2000  // Resend request every 2 seconds

// ===== WIFI STATE =====
bool wifiConnected = false;
unsigned long lastWiFiCheck = 0;
unsigned long lastWiFiAttempt = 0;

// ===== CLOUD TELEMETRY =====
struct CloudTelemetry {
  uint32_t totalRequests;
  uint32_t successCount;
  uint32_t failCount;
  int lastHttpCode;
  uint32_t lastLatencyMs;
  uint32_t avgLatencyMs;
  uint64_t totalLatencyMs;
  String lastError;
  String lastResponseDeviceId;
  String lastResponseTimestamp;
  bool lastValidationOk;
} cloudTelemetry;

// ===== DATA STRUCTURE =====
struct ReceivedData {
  float temperature;      // °C
  float humidity;         // %
  float pressure;         // hPa
  float gasResistance;    // kOhms
  float windSpeed;        // m/s
  uint16_t pm1_0;         // µg/m³
  uint16_t pm2_5;         // µg/m³
  uint16_t pm10;          // µg/m³
  float batteryVoltage;   // V
  uint8_t batteryPercent; // 0-100
  uint16_t packetCounter; // Packet number
  uint8_t sensorStatus;   // Status flags
  int16_t rssi;           // Signal strength
  bool valid;             // Data received flag
} rxData;

// ===== FORECAST DATA =====
#define FORECAST_DAYS 3
#define FORECAST_HOURS 4       // Next 4 half-hour slots (covers ~2 hours)
#define FORECAST_INTERVAL_MS 1800000  // Fetch every 30 minutes

struct ForecastDay {
  char date[11];       // "2026-03-30"
  float tempMax;
  float tempMin;
  int precipChance;    // 0-100%
  int weatherCode;     // WMO code
};

struct ForecastHour {
  char time[6];        // "14:00"
  float temp;
  int precipChance;
  int weatherCode;
};

struct {
  ForecastDay days[FORECAST_DAYS];
  ForecastHour hours[FORECAST_HOURS];
  int hourCount;
  bool valid;
  unsigned long lastFetch;
} forecast;

// ===== HELPER FUNCTIONS =====

const char* getAirQualityLevel(uint16_t pm25) {
  if (pm25 <= 12) return "Good";
  if (pm25 <= 35) return "Moderate";
  if (pm25 <= 55) return "Sensitive";
  if (pm25 <= 150) return "Unhealthy";
  if (pm25 <= 250) return "Very Bad";
  return "Hazardous";
}

const char* getAirQualityShort(uint16_t pm25) {
  if (pm25 <= 12) return "Good";
  if (pm25 <= 35) return "Mod";
  if (pm25 <= 55) return "Sens";
  if (pm25 <= 150) return "Bad";
  return "Hazard";
}

const char* getBatteryStatus(uint8_t percent) {
  if (percent > 75) return "Full";
  if (percent > 50) return "Good";
  if (percent > 25) return "Low";
  if (percent > 10) return "VLow";
  return "Crit";
}

float msToKmh(float ms) {
  return ms * 3.6;
}

uint16_t getAirQualityColor(uint16_t pm25) {
  if (pm25 <= 12) return COLOR_TEXT;      // Good = white
  if (pm25 <= 35) return COLOR_WARM;      // Moderate = light red
  if (pm25 <= 55) return COLOR_ACCENT;    // Sensitive = red
  return COLOR_ACCENT;                    // Bad+ = red
}

const char* wmoCodeToText(int code) {
  if (code == 0) return "Clear";
  if (code == 1) return "M.Clear";
  if (code == 2) return "P.Cloud";
  if (code == 3) return "Overcast";
  if (code == 45 || code == 48) return "Fog";
  if (code >= 51 && code <= 55) return "Drizzle";
  if (code >= 56 && code <= 57) return "FrzDriz";
  if (code >= 61 && code <= 65) return "Rain";
  if (code >= 66 && code <= 67) return "FrzRain";
  if (code >= 71 && code <= 75) return "Snow";
  if (code == 77) return "Grains";
  if (code >= 80 && code <= 82) return "Showers";
  if (code >= 85 && code <= 86) return "SnowShr";
  if (code >= 95 && code <= 99) return "Storm";
  return "???";
}

uint16_t getBatteryColor(uint8_t percent) {
  if (percent > 50) return COLOR_TEXT;
  if (percent > 25) return COLOR_DIM;
  if (percent > 10) return COLOR_WARM;
  return COLOR_ACCENT;
}

// ===== WIFI FUNCTIONS =====

void initWiFi() {
  Serial.print("Connecting to WiFi");

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  unsigned long startAttempt = millis();

  while (WiFi.status() != WL_CONNECTED &&
         millis() - startAttempt < WIFI_CONNECT_TIMEOUT_MS) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    Serial.println(" Connected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());

    // Configure NTP
    configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC, NTP_SERVER);
    Serial.println("NTP configured");
  } else {
    wifiConnected = false;
    Serial.println(" Failed!");
  }

  lastWiFiAttempt = millis();
}

void checkWiFiConnection() {
  // Only check periodically
  if (millis() - lastWiFiCheck < 5000) return;
  lastWiFiCheck = millis();

  if (WiFi.status() == WL_CONNECTED) {
    if (!wifiConnected) {
      wifiConnected = true;
      Serial.println("WiFi reconnected!");
    }
  } else {
    if (wifiConnected) {
      wifiConnected = false;
      Serial.println("WiFi disconnected!");
    }

    // Try to reconnect periodically
    if (millis() - lastWiFiAttempt > WIFI_RECONNECT_INTERVAL_MS) {
      Serial.println("Attempting WiFi reconnect...");
      WiFi.disconnect();
      WiFi.begin(WIFI_SSID, WIFI_PASS);
      lastWiFiAttempt = millis();
    }
  }
}

String getISOTimestamp() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    Serial.println("Failed to get time");
    return "1970-01-01T00:00:00Z";
  }

  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
  return String(buffer);
}

// ===== CLOUD UPLOAD FUNCTION =====

void uploadToCloud() {
  if (!wifiConnected) {
    Serial.println("  Cloud upload skipped - WiFi not connected");
    cloudTelemetry.lastError = "WiFi disconnected";
    return;
  }

  if (!rxData.valid) {
    Serial.println("  Cloud upload skipped - no valid data");
    return;
  }

  cloudTelemetry.totalRequests++;

  Serial.println("\n--- CLOUD UPLOAD ---");

  // Build JSON payload
  StaticJsonDocument<512> doc;
  doc["device_id"] = DEVICE_ID;
  doc["timestamp"] = getISOTimestamp();

  JsonObject readings = doc.createNestedObject("readings");
  readings["temperature_c"] = rxData.temperature;
  readings["humidity_pct"] = rxData.humidity;
  readings["pressure_hpa"] = rxData.pressure;
  if (isfinite(rxData.gasResistance) &&
      rxData.gasResistance >= 0.0f && rxData.gasResistance <= 1000.0f) {
    readings["gas_density"] = rxData.gasResistance;
  } else {
    Serial.println("  gas_density omitted (invalid or outside API range)");
  }
  readings["pm1"] = rxData.pm1_0;
  readings["pm25"] = rxData.pm2_5;
  readings["pm10"] = rxData.pm10;
  readings["wind_speed_ms"] = rxData.windSpeed;

  JsonObject meta = doc.createNestedObject("meta");
  meta["battery_v"] = rxData.batteryVoltage;
  meta["rssi"] = rxData.rssi;

  String payload;
  serializeJson(doc, payload);

  Serial.print("Endpoint: ");
  Serial.println(API_ENDPOINT);
  Serial.print("Payload: ");
  Serial.println(payload);

  // Send request
  HTTPClient http;
  http.begin(API_ENDPOINT);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("x-api-key", API_KEY);
  http.setTimeout(10000);

  unsigned long startTime = millis();
  int httpCode = http.POST(payload);
  unsigned long latency = millis() - startTime;

  cloudTelemetry.lastHttpCode = httpCode;
  cloudTelemetry.lastLatencyMs = latency;
  cloudTelemetry.totalLatencyMs += latency;
  cloudTelemetry.avgLatencyMs = cloudTelemetry.totalLatencyMs / cloudTelemetry.totalRequests;

  Serial.printf("HTTP Code: %d | Latency: %lu ms\n", httpCode, latency);

  if (httpCode > 0) {
    String response = http.getString();
    Serial.print("Response: ");
    Serial.println(response);

    // Parse response JSON
    StaticJsonDocument<256> respDoc;
    DeserializationError parseError = deserializeJson(respDoc, response);

    if (!parseError) {
      if (httpCode == 200) {
        // Success!
        cloudTelemetry.successCount++;
        cloudTelemetry.lastError = "";
        cloudTelemetry.lastValidationOk = true;

        if (respDoc.containsKey("device_id")) {
          cloudTelemetry.lastResponseDeviceId = respDoc["device_id"].as<String>();
        }
        if (respDoc.containsKey("timestamp")) {
          cloudTelemetry.lastResponseTimestamp = respDoc["timestamp"].as<String>();
        }

        Serial.println("[OK] Data accepted by server");
        Serial.printf("  Confirmed device: %s\n", cloudTelemetry.lastResponseDeviceId.c_str());
        Serial.printf("  Confirmed time: %s\n", cloudTelemetry.lastResponseTimestamp.c_str());

      } else if (httpCode == 400) {
        // Validation error
        cloudTelemetry.failCount++;
        cloudTelemetry.lastValidationOk = false;

        if (respDoc.containsKey("error")) {
          JsonObject error = respDoc["error"];
          String errorMsg = error["message"].as<String>();
          cloudTelemetry.lastError = errorMsg;

          Serial.printf("[FAIL] Validation Error: %s\n", errorMsg.c_str());

          if (error.containsKey("errors")) {
            JsonArray errors = error["errors"];
            for (JsonObject err : errors) {
              String path = err["path"].as<String>();
              String msg = err["message"].as<String>();
              Serial.printf("  - %s: %s\n", path.c_str(), msg.c_str());
            }
          }
        } else {
          cloudTelemetry.lastError = "Bad request (400)";
        }

      } else if (httpCode == 403) {
        cloudTelemetry.failCount++;
        cloudTelemetry.lastError = "Forbidden - check API key";
        Serial.println("[FAIL] 403 Forbidden - API key may be invalid");

      } else if (httpCode >= 500) {
        cloudTelemetry.failCount++;
        cloudTelemetry.lastError = "Server error " + String(httpCode);
        Serial.printf("[FAIL] Server Error %d\n", httpCode);
      } else {
        cloudTelemetry.failCount++;
        cloudTelemetry.lastError = "HTTP " + String(httpCode);
      }
    } else {
      // Couldn't parse response but got HTTP response
      if (httpCode == 200) {
        cloudTelemetry.successCount++;
        cloudTelemetry.lastError = "";
        Serial.println("[OK] Success (response not JSON)");
      } else {
        cloudTelemetry.failCount++;
        cloudTelemetry.lastError = "HTTP " + String(httpCode);
      }
    }
  } else {
    // Connection error (negative code)
    cloudTelemetry.failCount++;
    cloudTelemetry.lastError = http.errorToString(httpCode);
    Serial.printf("[FAIL] Connection Error: %s\n", cloudTelemetry.lastError.c_str());
  }

  http.end();

  // Print telemetry summary
  Serial.println("--- TELEMETRY ---");
  Serial.printf("Total: %lu | OK: %lu | Fail: %lu | Rate: %.1f%%\n",
                cloudTelemetry.totalRequests,
                cloudTelemetry.successCount,
                cloudTelemetry.failCount,
                (cloudTelemetry.totalRequests > 0) ?
                  (100.0 * cloudTelemetry.successCount / cloudTelemetry.totalRequests) : 0);
  Serial.printf("Avg Latency: %lu ms\n", cloudTelemetry.avgLatencyMs);
  Serial.println("-----------------\n");
}

// ===== FORECAST FETCH =====

void fetchForecast() {
  if (!wifiConnected) return;

  Serial.println("\n--- FORECAST FETCH ---");

  // Get current hour to filter hourly data
  struct tm timeinfo;
  int currentHour = 12;
  if (getLocalTime(&timeinfo)) {
    currentHour = timeinfo.tm_hour;
  }

  // Fetch daily forecast
  String dailyUrl = "https://api.open-meteo.com/v1/forecast?latitude=";
  dailyUrl += FORECAST_LAT;
  dailyUrl += "&longitude=";
  dailyUrl += FORECAST_LON;
  dailyUrl += "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode";
  dailyUrl += "&timezone=";
  dailyUrl += FORECAST_TIMEZONE;
  dailyUrl += "&forecast_days=3";

  WiFiClientSecure client;
  client.setInsecure();

  HTTPClient http;
  http.begin(client, dailyUrl);
  http.setTimeout(10000);

  int httpCode = http.GET();
  Serial.printf("Daily forecast HTTP: %d\n", httpCode);

  if (httpCode == 200) {
    String response = http.getString();
    StaticJsonDocument<1024> doc;
    DeserializationError err = deserializeJson(doc, response);

    if (!err) {
      JsonObject daily = doc["daily"];
      JsonArray times = daily["time"];
      JsonArray maxTemps = daily["temperature_2m_max"];
      JsonArray minTemps = daily["temperature_2m_min"];
      JsonArray precip = daily["precipitation_probability_max"];
      JsonArray codes = daily["weathercode"];

      for (int i = 0; i < FORECAST_DAYS && i < (int)times.size(); i++) {
        strncpy(forecast.days[i].date, times[i].as<const char*>(), 10);
        forecast.days[i].date[10] = '\0';
        forecast.days[i].tempMax = maxTemps[i].as<float>();
        forecast.days[i].tempMin = minTemps[i].as<float>();
        forecast.days[i].precipChance = precip[i].as<int>();
        forecast.days[i].weatherCode = codes[i].as<int>();

        Serial.printf("  Day %d: %s | %.0f/%.0f C | %d%% rain | %s\n",
                      i, forecast.days[i].date,
                      forecast.days[i].tempMax, forecast.days[i].tempMin,
                      forecast.days[i].precipChance,
                      wmoCodeToText(forecast.days[i].weatherCode));
      }
    } else {
      Serial.printf("[FAIL] Daily JSON parse: %s\n", err.c_str());
    }
  } else {
    Serial.printf("[FAIL] Daily fetch: %s\n", http.errorToString(httpCode).c_str());
  }
  http.end();

  // Fetch hourly forecast
  String hourlyUrl = "https://api.open-meteo.com/v1/forecast?latitude=";
  hourlyUrl += FORECAST_LAT;
  hourlyUrl += "&longitude=";
  hourlyUrl += FORECAST_LON;
  hourlyUrl += "&hourly=temperature_2m,precipitation_probability,weathercode";
  hourlyUrl += "&timezone=";
  hourlyUrl += FORECAST_TIMEZONE;
  hourlyUrl += "&forecast_days=1";

  http.begin(client, hourlyUrl);
  http.setTimeout(10000);

  httpCode = http.GET();
  Serial.printf("Hourly forecast HTTP: %d\n", httpCode);

  if (httpCode == 200) {
    String response = http.getString();
    DynamicJsonDocument doc(4096);
    DeserializationError err = deserializeJson(doc, response);

    if (!err) {
      JsonObject hourly = doc["hourly"];
      JsonArray times = hourly["time"];
      JsonArray temps = hourly["temperature_2m"];
      JsonArray precip = hourly["precipitation_probability"];
      JsonArray codes = hourly["weathercode"];

      forecast.hourCount = 0;
      for (int i = 0; i < (int)times.size() && forecast.hourCount < FORECAST_HOURS; i++) {
        // Parse hour from "2026-03-30T14:00"
        const char* t = times[i].as<const char*>();
        int h = 0;
        if (strlen(t) >= 13) {
          h = (t[11] - '0') * 10 + (t[12] - '0');
        }
        // Only include hours from now onwards
        if (h >= currentHour) {
          snprintf(forecast.hours[forecast.hourCount].time, 6, "%c%c:00", t[11], t[12]);
          forecast.hours[forecast.hourCount].temp = temps[i].as<float>();
          forecast.hours[forecast.hourCount].precipChance = precip[i].as<int>();
          forecast.hours[forecast.hourCount].weatherCode = codes[i].as<int>();

          Serial.printf("  Hour %d: %s | %.1f C | %d%% rain | %s\n",
                        forecast.hourCount, forecast.hours[forecast.hourCount].time,
                        forecast.hours[forecast.hourCount].temp,
                        forecast.hours[forecast.hourCount].precipChance,
                        wmoCodeToText(forecast.hours[forecast.hourCount].weatherCode));
          forecast.hourCount++;
        }
      }
    } else {
      Serial.printf("[FAIL] Hourly JSON parse: %s\n", err.c_str());
    }
  } else {
    Serial.printf("[FAIL] Hourly fetch: %s\n", http.errorToString(httpCode).c_str());
  }
  http.end();

  forecast.valid = true;
  forecast.lastFetch = millis();
  Serial.println("[OK] Forecast updated");
  Serial.println("----------------------\n");
}

// ===== TFT DISPLAY FUNCTIONS =====

// Draw a btop-style panel border
void drawPanel(int x, int y, int w, int h, const char* title = NULL) {
  tft.drawRect(x, y, w, h, COLOR_ACCENT);
  if (title) {
    int titleLen = strlen(title);
    int titlePx = titleLen * 6;  // size 1 = 6px per char
    int titleX = x + 6;
    tft.fillRect(titleX - 2, y - 1, titlePx + 4, 3, COLOR_BG);
    tft.setTextColor(COLOR_ACCENT);
    tft.setTextSize(1);
    tft.setCursor(titleX, y - 3);
    tft.print(title);
  }
}

// Draw header bar
void drawHeader(const char* title) {
  tft.drawRect(0, 0, SCREEN_WIDTH, 18, COLOR_ACCENT);
  tft.fillRect(1, 1, SCREEN_WIDTH - 2, 16, COLOR_HEADER);
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(1);
  tft.setCursor(4, 5);
  tft.print(title);
}

// Draw signal strength as text
void drawSignalText(int x, int y, int16_t rssi) {
  tft.setTextSize(1);
  tft.setCursor(x, y);
  tft.setTextColor(COLOR_DIM);
  tft.printf("RSSI:%d", rssi);
}

void displayPageMainStatic() {
  tft.drawRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_ACCENT);
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(1);
  tft.setCursor(4, 4);
  tft.print("WEATHER STATION");
  tft.drawFastHLine(0, 14, SCREEN_WIDTH, COLOR_ACCENT);

  tft.drawRect(2, 18, 157, 90, COLOR_ACCENT);
  tft.drawRect(161, 18, 157, 90, COLOR_ACCENT);
  tft.drawRect(2, 110, 106, 70, COLOR_ACCENT);
  tft.drawRect(110, 110, 100, 70, COLOR_ACCENT);
  tft.drawRect(212, 110, 106, 70, COLOR_ACCENT);
  tft.drawFastHLine(0, 182, SCREEN_WIDTH, COLOR_ACCENT);

  // Labels
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(2);
  tft.setCursor(8, 22);
  tft.print("TEMP");
  tft.setCursor(168, 22);
  tft.print("HUMID");
  tft.setTextSize(1);
  tft.setCursor(6, 114);
  tft.print("PRESSURE");
  tft.setCursor(114, 114);
  tft.print("WIND");
  tft.setCursor(216, 114);
  tft.print("PM2.5");

  // Static units
  tft.setTextColor(COLOR_DIM);
  tft.setTextSize(1);
  tft.setCursor(6, 162);
  tft.print("hPa");
  tft.setCursor(114, 162);
  tft.print("m/s");
}

void displayPageMainDynamic() {
  // Header dynamic: RSSI + BAT
  tft.fillRect(160, 1, 158, 12, COLOR_BG);
  tft.setTextColor(COLOR_DIM);
  tft.setTextSize(1);
  tft.setCursor(160, 4);
  tft.printf("RSSI:%d  BAT:%d%%  [1/3]", rxData.rssi, rxData.batteryPercent);

  // Temperature value
  tft.fillRect(4, 48, 151, 38, COLOR_BG);
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(5);
  tft.setCursor(8, 50);
  tft.printf("%.1f", rxData.temperature);
  int tx = tft.getCursorX();
  tft.setTextSize(2);
  tft.setCursor(tx + 2, 54);
  tft.setTextColor(COLOR_ACCENT);
  tft.print("C");

  // Humidity value
  tft.fillRect(163, 48, 153, 38, COLOR_BG);
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(5);
  tft.setCursor(168, 50);
  tft.printf("%.0f", rxData.humidity);
  int hx = tft.getCursorX();
  tft.setTextSize(2);
  tft.setCursor(hx + 2, 54);
  tft.setTextColor(COLOR_ACCENT);
  tft.print("%");

  // Pressure value
  tft.fillRect(4, 128, 100, 30, COLOR_BG);
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(3);
  tft.setCursor(6, 132);
  tft.printf("%.0f", rxData.pressure);

  // Wind value
  tft.fillRect(112, 128, 94, 30, COLOR_BG);
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(3);
  tft.setCursor(114, 132);
  tft.printf("%.1f", rxData.windSpeed);

  // PM2.5 value
  tft.fillRect(214, 128, 102, 30, COLOR_BG);
  tft.setTextColor(getAirQualityColor(rxData.pm2_5));
  tft.setTextSize(3);
  tft.setCursor(216, 132);
  tft.printf("%d", rxData.pm2_5);
  tft.setTextSize(1);
  tft.fillRect(214, 160, 102, 12, COLOR_BG);
  tft.setCursor(216, 162);
  tft.printf("%s", getAirQualityShort(rxData.pm2_5));

  // Footer
  tft.fillRect(2, 184, 316, SCREEN_HEIGHT - 185, COLOR_BG);
  tft.setTextSize(1);
  tft.setTextColor(COLOR_DIM);
  tft.setCursor(4, 188);
  tft.printf("#%d", rxData.packetCounter);

  tft.setCursor(50, 188);
  tft.print("Air:");
  tft.setTextColor(getAirQualityColor(rxData.pm2_5));
  tft.print(getAirQualityShort(rxData.pm2_5));

  tft.setTextColor(COLOR_DIM);
  tft.setCursor(110, 188);
  tft.print("Cloud:");
  if (cloudTelemetry.totalRequests > 0) {
    bool ok = (cloudTelemetry.lastHttpCode == 200);
    tft.setTextColor(ok ? COLOR_OK : COLOR_FAIL);
    tft.printf("%s %lu/%lu", ok ? "OK" : "ERR",
               cloudTelemetry.successCount, cloudTelemetry.totalRequests);
  } else {
    tft.print("--");
  }

  if (lastPacketTime > 0) {
    unsigned long secsAgo = (millis() - lastPacketTime) / 1000;
    tft.setTextColor(COLOR_DIM);
    tft.setCursor(240, 188);
    tft.printf("%lus ago", secsAgo);
  }

  tft.setTextColor(COLOR_DIM);
  tft.setCursor(4, 200);
  tft.print("WiFi:");
  tft.setTextColor(wifiConnected ? COLOR_OK : COLOR_FAIL);
  tft.print(wifiConnected ? "ON " : "OFF");
}

void displayPageAirStatic() {
  tft.drawRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_ACCENT);
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(1);
  tft.setCursor(4, 4);
  tft.print("AIR QUALITY");
  tft.setTextColor(COLOR_DIM);
  tft.setCursor(280, 4);
  tft.print("[2/3]");
  tft.drawFastHLine(0, 14, SCREEN_WIDTH, COLOR_ACCENT);

  tft.drawRect(2, 18, 106, 100, COLOR_ACCENT);
  tft.drawRect(110, 18, 100, 100, COLOR_ACCENT);
  tft.drawRect(212, 18, 106, 100, COLOR_ACCENT);
  tft.drawRect(2, 120, 210, 50, COLOR_ACCENT);
  tft.drawRect(214, 120, 104, 50, COLOR_ACCENT);
  tft.drawFastHLine(0, 172, SCREEN_WIDTH, COLOR_ACCENT);

  // Labels
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(2);
  tft.setCursor(8, 22);
  tft.print("PM1.0");
  tft.setCursor(116, 22);
  tft.print("PM2.5");
  tft.setCursor(218, 22);
  tft.print("PM10");
  tft.setTextSize(1);
  tft.setCursor(6, 124);
  tft.print("STATUS");
  tft.setCursor(218, 124);
  tft.print("GAS");

  // Units
  tft.setTextColor(COLOR_DIM);
  tft.setCursor(8, 100);
  tft.print("ug/m3");
  tft.setCursor(116, 100);
  tft.print("ug/m3");
  tft.setCursor(218, 100);
  tft.print("ug/m3");
}

void displayPageAirDynamic() {
  // PM1.0 value
  tft.fillRect(4, 48, 100, 40, COLOR_BG);
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(5);
  tft.setCursor(8, 52);
  tft.printf("%d", rxData.pm1_0);

  // PM2.5 value
  tft.fillRect(112, 48, 94, 40, COLOR_BG);
  tft.setTextColor(getAirQualityColor(rxData.pm2_5));
  tft.setTextSize(5);
  tft.setCursor(116, 52);
  tft.printf("%d", rxData.pm2_5);

  // PM10 value
  tft.fillRect(214, 48, 102, 40, COLOR_BG);
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(5);
  tft.setCursor(218, 52);
  tft.printf("%d", rxData.pm10);

  // Status value
  tft.fillRect(4, 134, 204, 32, COLOR_BG);
  tft.setTextSize(3);
  tft.setCursor(8, 138);
  tft.setTextColor(getAirQualityColor(rxData.pm2_5));
  tft.print(getAirQualityLevel(rxData.pm2_5));

  // Gas value
  tft.fillRect(216, 134, 100, 32, COLOR_BG);
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(3);
  tft.setCursor(218, 138);
  tft.printf("%.0f", rxData.gasResistance);

  // Footer
  tft.fillRect(2, 174, 316, SCREEN_HEIGHT - 175, COLOR_BG);
  tft.setTextSize(1);
  tft.setTextColor(COLOR_DIM);
  tft.setCursor(4, 178);
  tft.printf("#%d  Gas unit: kOhm", rxData.packetCounter);
  if (lastPacketTime > 0) {
    unsigned long secsAgo = (millis() - lastPacketTime) / 1000;
    tft.setCursor(250, 178);
    tft.printf("%lus ago", secsAgo);
  }
}

void displayPageStatusStatic() {
  tft.drawRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_ACCENT);
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(1);
  tft.setCursor(4, 4);
  tft.print("SYSTEM STATUS");
  tft.setTextColor(COLOR_DIM);
  tft.setCursor(280, 4);
  tft.print("[3/3]");
  tft.drawFastHLine(0, 14, SCREEN_WIDTH, COLOR_ACCENT);

  tft.drawRect(2, 18, 157, 52, COLOR_ACCENT);
  tft.drawRect(161, 18, 157, 52, COLOR_ACCENT);
  tft.drawRect(2, 72, 157, 52, COLOR_ACCENT);
  tft.drawRect(161, 72, 157, 52, COLOR_ACCENT);
  tft.drawRect(2, 126, 157, 52, COLOR_ACCENT);
  tft.drawRect(161, 126, 157, 52, COLOR_ACCENT);
  tft.drawFastHLine(0, 180, SCREEN_WIDTH, COLOR_ACCENT);

  // Labels
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(1);
  tft.setCursor(6, 22);
  tft.print("TEMP");
  tft.setCursor(166, 22);
  tft.print("BATTERY");
  tft.setCursor(6, 76);
  tft.print("HUMIDITY");
  tft.setCursor(166, 76);
  tft.print("WIND");
  tft.setCursor(6, 130);
  tft.print("PRESSURE");
  tft.setCursor(166, 130);
  tft.print("GAS");

  // Static units
  tft.setTextColor(COLOR_DIM);
  tft.setCursor(6, 168);
  tft.print("hPa");
  tft.setCursor(166, 168);
  tft.print("kOhm");
}

void displayPageStatusDynamic() {
  // Row 1 values
  tft.fillRect(4, 36, 151, 30, COLOR_BG);
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(3);
  tft.setCursor(6, 38);
  tft.printf("%.1f C", rxData.temperature);

  tft.fillRect(163, 36, 153, 30, COLOR_BG);
  tft.setTextColor(getBatteryColor(rxData.batteryPercent));
  tft.setTextSize(3);
  tft.setCursor(166, 38);
  tft.printf("%.1fV %d%%", rxData.batteryVoltage, rxData.batteryPercent);

  // Row 2 values
  tft.fillRect(4, 90, 151, 30, COLOR_BG);
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(3);
  tft.setCursor(6, 92);
  tft.printf("%.1f %%", rxData.humidity);

  tft.fillRect(163, 90, 153, 30, COLOR_BG);
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(3);
  tft.setCursor(166, 92);
  tft.printf("%.1f m/s", rxData.windSpeed);

  // Row 3 values
  tft.fillRect(4, 144, 151, 20, COLOR_BG);
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(3);
  tft.setCursor(6, 146);
  tft.printf("%.0f", rxData.pressure);

  tft.fillRect(163, 144, 153, 20, COLOR_BG);
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(3);
  tft.setCursor(166, 146);
  tft.printf("%.0f", rxData.gasResistance);

  // Footer
  tft.fillRect(2, 182, 316, SCREEN_HEIGHT - 183, COLOR_BG);
  tft.setTextSize(1);
  tft.setTextColor(COLOR_DIM);
  tft.setCursor(4, 186);
  tft.print("BME:");
  tft.setTextColor((rxData.sensorStatus & 0x01) ? COLOR_OK : COLOR_FAIL);
  tft.print((rxData.sensorStatus & 0x01) ? "OK" : "FL");
  tft.setTextColor(COLOR_DIM);
  tft.print(" PMS:");
  tft.setTextColor((rxData.sensorStatus & 0x02) ? COLOR_OK : COLOR_FAIL);
  tft.print((rxData.sensorStatus & 0x02) ? "OK" : "FL");
  tft.setTextColor(COLOR_DIM);
  tft.print(" INA:");
  tft.setTextColor((rxData.sensorStatus & 0x04) ? COLOR_OK : COLOR_FAIL);
  tft.print((rxData.sensorStatus & 0x04) ? "OK" : "--");
  tft.setTextColor(COLOR_DIM);
  tft.print(" WiFi:");
  tft.setTextColor(wifiConnected ? COLOR_OK : COLOR_FAIL);
  tft.print(wifiConnected ? "ON" : "OFF");

  tft.setTextColor(COLOR_DIM);
  tft.setCursor(4, 198);
  tft.print("Cloud:");
  if (cloudTelemetry.totalRequests > 0) {
    bool ok = (cloudTelemetry.lastHttpCode == 200);
    tft.setTextColor(ok ? COLOR_OK : COLOR_FAIL);
    tft.printf("%s", ok ? "OK" : "ERR");
    tft.setTextColor(COLOR_TEXT);
    tft.printf(" %lu/%lu", cloudTelemetry.successCount, cloudTelemetry.totalRequests);
    float rate = 100.0 * cloudTelemetry.successCount / cloudTelemetry.totalRequests;
    tft.printf(" %.0f%%", rate);
    tft.setTextColor(COLOR_DIM);
    tft.printf(" %lums", cloudTelemetry.avgLatencyMs);
  } else {
    tft.print("--");
  }
  if (wifiConnected) {
    tft.setTextColor(COLOR_DIM);
    tft.setCursor(4, 210);
    tft.print("IP:");
    tft.print(WiFi.localIP());
  }
}

// ===== WEATHER ICONS =====
// Simple pixel-art icons for the TFT, drawn at a given position

// Raindrop: teardrop shape, ~8x12px
void drawRaindrop(int x, int y, uint16_t color) {
  // Point at top, bulge at bottom
  tft.fillTriangle(x+4, y, x+1, y+6, x+7, y+6, color);
  tft.fillCircle(x+4, y+7, 3, color);
}

// Sun: circle with 4 rays, ~14x14px
void drawSunIcon(int x, int y, uint16_t color) {
  tft.fillCircle(x+7, y+7, 4, color);
  tft.drawFastVLine(x+7, y, 3, color);      // top
  tft.drawFastVLine(x+7, y+11, 3, color);   // bottom
  tft.drawFastHLine(x, y+7, 3, color);      // left
  tft.drawFastHLine(x+11, y+7, 3, color);   // right
}

// Cloud: overlapping circles, ~16x10px
void drawCloudIcon(int x, int y, uint16_t color) {
  tft.fillCircle(x+5, y+6, 4, color);
  tft.fillCircle(x+10, y+6, 4, color);
  tft.fillCircle(x+7, y+3, 3, color);
  tft.fillRect(x+3, y+6, 10, 4, color);
}

// Rain: cloud + drops, ~16x16px
void drawRainIcon(int x, int y, uint16_t cloudColor, uint16_t rainColor) {
  drawCloudIcon(x, y, cloudColor);
  tft.fillRect(x+3, y+11, 2, 3, rainColor);
  tft.fillRect(x+7, y+12, 2, 3, rainColor);
  tft.fillRect(x+11, y+11, 2, 3, rainColor);
}

// Snow: asterisk pattern, ~14x14px
void drawSnowIcon(int x, int y, uint16_t color) {
  tft.drawFastVLine(x+7, y+1, 12, color);
  tft.drawFastHLine(x+1, y+7, 12, color);
  tft.drawLine(x+3, y+3, x+11, y+11, color);
  tft.drawLine(x+11, y+3, x+3, y+11, color);
  tft.drawPixel(x+7, y+1, color);
  tft.drawPixel(x+7, y+13, color);
}

// Draw weather icon based on WMO code
void drawWeatherIcon(int x, int y, int code) {
  if (code <= 1) {
    drawSunIcon(x, y, COLOR_WARM);
  } else if (code <= 3) {
    drawCloudIcon(x, y, COLOR_TEXT);
  } else if (code == 45 || code == 48) {
    // Fog: three horizontal lines
    for (int i = 0; i < 3; i++) {
      tft.drawFastHLine(x+1, y+3+i*4, 12, COLOR_DIM);
    }
  } else if ((code >= 51 && code <= 57) || (code >= 61 && code <= 67) || (code >= 80 && code <= 82)) {
    drawRainIcon(x, y, COLOR_TEXT, COLOR_BLUE);
  } else if ((code >= 71 && code <= 77) || (code >= 85 && code <= 86)) {
    drawSnowIcon(x, y, COLOR_CYAN);
  } else if (code >= 95) {
    // Storm: cloud + lightning bolt
    drawCloudIcon(x, y, COLOR_TEXT);
    tft.drawLine(x+7, y+10, x+5, y+13, COLOR_WARM);
    tft.drawLine(x+5, y+13, x+8, y+13, COLOR_WARM);
    tft.drawLine(x+8, y+13, x+6, y+16, COLOR_WARM);
  }
}

// ===== HOURLY FORECAST PAGE =====
// 4 columns, 78px each with 2px gaps. 320 = 4*78 + 3*2 + 4 margin
// Font sizes: s1=6x8  s2=12x16  s3=18x24  s4=24x32  s5=30x40
// Max chars at s2 in 72px usable: 6 chars. At s1: 12 chars.

void displayPageForecastHourlyStatic() {
  tft.drawRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_ACCENT);
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(1);
  tft.setCursor(4, 4);
  tft.print("NEXT HOURS");
  tft.setTextColor(COLOR_TEXT);
  tft.setCursor(274, 4);
  tft.print("[4/5]");
  tft.drawFastHLine(0, 14, SCREEN_WIDTH, COLOR_ACCENT);

  // Column dividers only (no boxes - cleaner look)
  for (int i = 1; i < FORECAST_HOURS; i++) {
    int x = i * 80;
    tft.drawFastVLine(x, 16, 204, COLOR_ACCENT);
  }

  // Bottom border
  tft.drawFastHLine(0, 220, SCREEN_WIDTH, COLOR_ACCENT);
}

void displayPageForecastHourlyDynamic() {
  if (!forecast.valid || forecast.hourCount == 0) {
    tft.fillRect(4, 80, 312, 40, COLOR_BG);
    tft.setTextColor(COLOR_TEXT);
    tft.setTextSize(2);
    tft.setCursor(40, 90);
    tft.print("Fetching forecast...");
    return;
  }

  for (int i = 0; i < forecast.hourCount && i < FORECAST_HOURS; i++) {
    int x = i * 80 + 4;
    int w = 74;

    // Clear column content
    tft.fillRect(x, 17, w, 202, COLOR_BG);

    // Time - prominent
    tft.setTextColor(COLOR_TEXT);
    tft.setTextSize(2);
    tft.setCursor(x + 6, 22);
    tft.print(forecast.hours[i].time);

    // Weather icon
    drawWeatherIcon(x + (w - 16) / 2, 42, forecast.hours[i].weatherCode);

    // Condition text
    tft.setTextColor(COLOR_TEXT);
    tft.setTextSize(1);
    tft.setCursor(x + 6, 60);
    tft.print(wmoCodeToText(forecast.hours[i].weatherCode));

    // Temperature - hero element
    tft.setTextColor(COLOR_TEXT);
    tft.setTextSize(5);
    int temp = (int)round(forecast.hours[i].temp);
    int digits = (temp < 0) ? 1 : 0;
    digits += (abs(temp) >= 10) ? 2 : 1;
    int tempW = digits * 30;
    int tempX = x + (w - tempW - 12) / 2;
    tft.setCursor(tempX, 72);
    tft.printf("%d", temp);
    tft.setTextSize(2);
    tft.print("o");

    // Separator
    tft.drawFastHLine(x + 4, 115, w - 8, COLOR_ACCENT);

    // Raindrop icon + percentage
    int pct = forecast.hours[i].precipChance;
    uint16_t rainColor = pct > 60 ? COLOR_BLUE : (pct > 25 ? COLOR_LTBLUE : COLOR_CYAN);
    drawRaindrop(x + (w/2) - 4, 120, rainColor);

    tft.setTextSize(3);
    tft.setTextColor(rainColor);
    int pctDigits = (pct >= 100) ? 3 : (pct >= 10) ? 2 : 1;
    int pctW = (pctDigits + 1) * 18;
    int pctX = x + (w - pctW) / 2;
    tft.setCursor(pctX, 140);
    tft.printf("%d%%", pct);
  }
}

// ===== DAILY FORECAST PAGE =====
// 3 columns, 104px each with 2px gaps. 320 = 3*104 + 2*2 + 4 margin
// Max chars at s2 in 98px usable: 8 chars. At s1: 16 chars.

void displayPageForecastDailyStatic() {
  tft.drawRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_ACCENT);
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(1);
  tft.setCursor(4, 4);
  tft.print("3-DAY FORECAST");
  tft.setTextColor(COLOR_TEXT);
  tft.setCursor(274, 4);
  tft.print("[5/5]");
  tft.drawFastHLine(0, 14, SCREEN_WIDTH, COLOR_ACCENT);

  // Column dividers
  tft.drawFastVLine(106, 16, 206, COLOR_ACCENT);
  tft.drawFastVLine(213, 16, 206, COLOR_ACCENT);

  // Bottom border
  tft.drawFastHLine(0, 222, SCREEN_WIDTH, COLOR_ACCENT);
}

void displayPageForecastDailyDynamic() {
  if (!forecast.valid) {
    tft.fillRect(4, 80, 312, 40, COLOR_BG);
    tft.setTextColor(COLOR_TEXT);
    tft.setTextSize(2);
    tft.setCursor(40, 90);
    tft.print("Fetching forecast...");
    return;
  }

  for (int i = 0; i < FORECAST_DAYS; i++) {
    int x = i * 107 + 2;
    int w = 102;

    // Clear column
    tft.fillRect(x + 1, 17, w - 2, 204, COLOR_BG);

    // Day name - large
    struct tm tm = {};
    int y, m, d;
    sscanf(forecast.days[i].date, "%d-%d-%d", &y, &m, &d);
    tm.tm_year = y - 1900;
    tm.tm_mon = m - 1;
    tm.tm_mday = d;
    mktime(&tm);
    const char* dayNames[] = {"SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"};

    tft.setTextColor(COLOR_TEXT);
    tft.setTextSize(2);
    tft.setCursor(x + 6, 20);
    tft.print(dayNames[tm.tm_wday]);

    // Weather icon next to day name
    drawWeatherIcon(x + w - 22, 18, forecast.days[i].weatherCode);

    // Date + condition on one line
    tft.setTextSize(1);
    tft.setTextColor(COLOR_TEXT);
    tft.setCursor(x + 6, 40);
    tft.printf("%02d/%02d  %s", d, m, wmoCodeToText(forecast.days[i].weatherCode));

    // High temp - hero element
    tft.setTextColor(COLOR_TEXT);
    tft.setTextSize(5);
    int hi = (int)round(forecast.days[i].tempMax);
    tft.setCursor(x + 6, 56);
    tft.printf("%d", hi);
    tft.setTextSize(2);
    tft.print("o");

    // Low temp - in cyan
    tft.setTextColor(COLOR_CYAN);
    tft.setTextSize(3);
    int lo = (int)round(forecast.days[i].tempMin);
    tft.setCursor(x + 6, 100);
    tft.printf("%d", lo);
    tft.setTextSize(1);
    tft.print("o");

    // Separator
    tft.drawFastHLine(x + 4, 128, w - 8, COLOR_ACCENT);

    // Raindrop icon + percentage
    int pct = forecast.days[i].precipChance;
    uint16_t rainColor = pct > 60 ? COLOR_BLUE : (pct > 25 ? COLOR_LTBLUE : COLOR_CYAN);

    drawRaindrop(x + 6, 134, rainColor);

    tft.setTextSize(pct >= 100 ? 3 : 4);
    tft.setTextColor(rainColor);
    tft.setCursor(x + 20, pct >= 100 ? 138 : 134);
    tft.printf("%d%%", pct);
  }
}

// ===== FIGlet SCRIPT FONT BITMAPS =====
// Packed 1-bit bitmaps (MSB first), generated from FIGlet "standard" font

#define WEATHER_W 73
#define WEATHER_H 9
#define WEATHER_BPR 10  // bytes per row
static const uint8_t weather_bmp[] PROGMEM = {
  0xC0,0x60,0x00,0x00,0x18,0x18,0x00,0x00,0x00,0x00,
  0x92,0x48,0x00,0x00,0x12,0x12,0x00,0x00,0x00,0x00,
  0xD5,0x69,0xF8,0x7E,0x3B,0x1B,0xE1,0xF8,0x7E,0x00,
  0xDC,0xEA,0x04,0x81,0x58,0x98,0x12,0x04,0x81,0x00,
  0xDE,0x6F,0xF2,0xFC,0xFF,0x1F,0xCF,0xF3,0xFC,0x80,
  0xDF,0x6E,0x1A,0x86,0x9A,0xDA,0x6E,0x1B,0xA7,0x00,
  0xF9,0xEF,0xFD,0xFE,0x9B,0x3A,0x6F,0xFD,0xA0,0x00,
  0xF0,0xEE,0x03,0x86,0x99,0xDA,0x6E,0x03,0xA0,0x00,
  0xE0,0x73,0xFC,0xFF,0x0F,0x9C,0x73,0xFD,0xC0,0x00,
};

#define STATION_W 66
#define STATION_H 9
#define STATION_BPR 9
static const uint8_t station_bmp[] PROGMEM = {
  0x07,0xE1,0x80,0x00,0x18,0x18,0x00,0x00,0x00,
  0x08,0x12,0x40,0x00,0x24,0x24,0x00,0x00,0x00,
  0x1F,0xCF,0x60,0xFC,0x76,0x38,0xFC,0x7F,0x00,
  0x1B,0xFB,0x11,0x02,0xB1,0x25,0x02,0x80,0x80,
  0x18,0x1F,0xE1,0xF9,0xFE,0x37,0xF9,0xFE,0x40,
  0x0F,0xCB,0x59,0x0D,0x35,0xB7,0x4D,0xD3,0x40,
  0x13,0xEB,0x67,0xFD,0x36,0x77,0x7D,0xD3,0x40,
  0x18,0x73,0x3B,0x0D,0x33,0xB7,0x0E,0xD3,0x40,
  0x0F,0xE1,0xF1,0xFE,0x1F,0x39,0xFC,0xE3,0x80,
};

// Draw a packed bitmap with thin dots: cellW x cellH grid, dot=1 or 2px centered
void drawBitmapThin(int x, int y, const uint8_t* bmp, int bmpW, int bmpH, int bpr,
                    int cellW, int cellH, int dot, uint16_t color) {
  int offX = (cellW - dot) / 2;
  int offY = (cellH - dot) / 2;
  for (int row = 0; row < bmpH; row++) {
    for (int col = 0; col < bmpW; col++) {
      int byteIdx = row * bpr + (col / 8);
      uint8_t bit = 0x80 >> (col % 8);
      if (pgm_read_byte(&bmp[byteIdx]) & bit) {
        int bx = x + col * cellW + offX;
        int by = y + row * cellH + offY;
        tft.fillRect(bx, by, dot, dot, color);
      }
    }
  }
}

// ===== WAITING / HOME SCREEN =====

// Layout: cellW=4, cellH=5, weather 73*4=292px wide, 9*5=45px tall
// Centered: x=(320-292)/2=14, y1=15, y2=15+45+8=68
// Title bottom at 68+45=113, status below

#define TITLE_CW 4
#define TITLE_CH 5
#define TITLE_X  14
#define TITLE_Y1 15
#define TITLE_Y2 68

void displayWaiting(bool fullRedraw) {
  static uint8_t animFrame = 0;
  static bool lastWifiDrawn = false;
  static uint8_t lastDot = 0;

  if (fullRedraw) {
    tft.fillScreen(COLOR_BG);
    animFrame = 0;
    lastDot = 0;
    lastWifiDrawn = !wifiConnected;
  }

  // Pulse animation: alternate dot size 1px ↔ 2px
  uint8_t dot = (animFrame % 2 == 0) ? 1 : 2;

  if (dot != lastDot || fullRedraw) {
    lastDot = dot;

    // Clear title area
    tft.fillRect(TITLE_X, TITLE_Y1, 293, 100, COLOR_BG);

    // Shadow (offset +1)
    drawBitmapThin(TITLE_X + 1, TITLE_Y1 + 1,
                   weather_bmp, WEATHER_W, WEATHER_H, WEATHER_BPR,
                   TITLE_CW, TITLE_CH, dot, 0x3800);
    drawBitmapThin(TITLE_X + 1, TITLE_Y2 + 1,
                   station_bmp, STATION_W, STATION_H, STATION_BPR,
                   TITLE_CW, TITLE_CH, dot, 0x3800);

    // Main
    drawBitmapThin(TITLE_X, TITLE_Y1,
                   weather_bmp, WEATHER_W, WEATHER_H, WEATHER_BPR,
                   TITLE_CW, TITLE_CH, dot, COLOR_ACCENT);
    drawBitmapThin(TITLE_X, TITLE_Y2,
                   station_bmp, STATION_W, STATION_H, STATION_BPR,
                   TITLE_CW, TITLE_CH, dot, COLOR_ACCENT);
  }

  // --- status at bottom ---

  if (lastWifiDrawn != wifiConnected || fullRedraw) {
    lastWifiDrawn = wifiConnected;
    tft.fillRect(4, 200, 160, 10, COLOR_BG);
    tft.setTextSize(1);
    tft.setCursor(6, 202);
    tft.setTextColor(COLOR_DIM);
    tft.print("WiFi:");
    tft.setTextColor(wifiConnected ? COLOR_OK : COLOR_FAIL);
    tft.print(wifiConnected ? "OK" : "OFF");
  }

  tft.fillRect(4, 218, 100, 16, COLOR_BG);
  tft.setTextColor(COLOR_DIM);
  tft.setTextSize(1);
  tft.setCursor(6, 220);
  tft.print("Listening");
  int dots = animFrame % 4;
  for (int i = 0; i < dots; i++) tft.print(".");

  animFrame++;
}

void updateDisplay() {
  // Auto-cycle pages
  if (millis() - lastPageChange > PAGE_DURATION) {
    if (!rxData.valid) {
      // No sensor data yet: cycle waiting → forecast_hourly → forecast_daily
      if (forecast.valid) {
        if (lastRenderedPage == -2) currentPage = PAGE_FORECAST_HOURLY;
        else if (currentPage == PAGE_FORECAST_HOURLY) currentPage = PAGE_FORECAST_DAILY;
        else currentPage = PAGE_MAIN;  // will trigger waiting screen below
      }
    } else {
      // Normal full page rotation
      currentPage = (currentPage + 1) % NUM_PAGES;
    }
    lastPageChange = millis();
  }

  // Show waiting screen for sensor pages when no data
  if (!rxData.valid && currentPage != PAGE_FORECAST_HOURLY && currentPage != PAGE_FORECAST_DAILY) {
    bool fullRedraw = (lastRenderedPage != -2);
    lastRenderedPage = -2;
    displayWaiting(fullRedraw);
    return;
  }

  bool pageChanged = (currentPage != lastRenderedPage);
  bool dataChanged = (rxData.packetCounter != lastRenderedPacket) ||
                     (wifiConnected != lastRenderedWifi);

  if (!pageChanged && !dataChanged) return;

  if (pageChanged) {
    tft.fillScreen(COLOR_BG);
  }

  lastRenderedPage = currentPage;
  lastRenderedPacket = rxData.packetCounter;
  lastRenderedWifi = wifiConnected;

  switch (currentPage) {
    case PAGE_MAIN:
      if (pageChanged) displayPageMainStatic();
      displayPageMainDynamic();
      break;
    case PAGE_AIR_QUALITY:
      if (pageChanged) displayPageAirStatic();
      displayPageAirDynamic();
      break;
    case PAGE_STATUS:
      if (pageChanged) displayPageStatusStatic();
      displayPageStatusDynamic();
      break;
    case PAGE_FORECAST_HOURLY:
      if (pageChanged) displayPageForecastHourlyStatic();
      displayPageForecastHourlyDynamic();
      break;
    case PAGE_FORECAST_DAILY:
      if (pageChanged) displayPageForecastDailyStatic();
      displayPageForecastDailyDynamic();
      break;
  }
}

// ===== PACKET DECODING =====

bool decodePayload(uint8_t* payload, uint8_t len) {
  if (len != 24) {
    Serial.printf("Invalid payload length: %d (expected 24)\n", len);
    return false;
  }

  // Verify checksum
  uint16_t calculatedChecksum = 0;
  for (int i = 0; i < 22; i++) {
    calculatedChecksum += payload[i];
  }
  uint16_t receivedChecksum = (payload[22] << 8) | payload[23];

  if (calculatedChecksum != receivedChecksum) {
    Serial.println("Checksum mismatch!");
    return false;
  }

  // Decode fields
  int16_t temp = (payload[0] << 8) | payload[1];
  rxData.temperature = temp / 100.0;

  uint16_t hum = (payload[2] << 8) | payload[3];
  rxData.humidity = hum / 100.0;

  uint16_t press = (payload[4] << 8) | payload[5];
  rxData.pressure = press / 10.0;

  uint16_t gas = (payload[6] << 8) | payload[7];
  rxData.gasResistance = gas;

  uint16_t wind = (payload[8] << 8) | payload[9];
  rxData.windSpeed = wind / 100.0;

  rxData.pm1_0 = (payload[10] << 8) | payload[11];
  rxData.pm2_5 = (payload[12] << 8) | payload[13];
  rxData.pm10 = (payload[14] << 8) | payload[15];

  uint16_t volt = (payload[16] << 8) | payload[17];
  rxData.batteryVoltage = volt / 100.0;

  rxData.batteryPercent = payload[18];
  rxData.packetCounter = (payload[19] << 8) | payload[20];
  rxData.sensorStatus = payload[21];

  rxData.valid = true;
  return true;
}

// ===== SERIAL OUTPUT =====

void printWeatherData() {
  Serial.println("\n============================================");
  Serial.println("  WEATHER STATION DATA RECEIVED");
  Serial.println("============================================");
  Serial.printf("Packet #%d | RSSI: %d dBm\n", rxData.packetCounter, rxData.rssi);
  Serial.println("--------------------------------------------");
  Serial.printf("Temperature:    %.1f C\n", rxData.temperature);
  Serial.printf("Humidity:       %.1f %%\n", rxData.humidity);
  Serial.printf("Pressure:       %.1f hPa\n", rxData.pressure);
  Serial.printf("Gas Resistance: %.0f kOhms\n", rxData.gasResistance);
  Serial.printf("Wind Speed:     %.1f m/s (%.1f km/h)\n", rxData.windSpeed, msToKmh(rxData.windSpeed));
  Serial.printf("PM1.0: %d | PM2.5: %d | PM10: %d ug/m3\n", rxData.pm1_0, rxData.pm2_5, rxData.pm10);
  Serial.printf("Air Quality:    %s\n", getAirQualityLevel(rxData.pm2_5));
  Serial.printf("Battery:        %.2fV (%d%%) [%s]\n", rxData.batteryVoltage, rxData.batteryPercent, getBatteryStatus(rxData.batteryPercent));
  Serial.printf("Sensors - BME:%s PMS:%s INA:%s\n",
                (rxData.sensorStatus & 0x01) ? "OK" : "FAIL",
                (rxData.sensorStatus & 0x02) ? "OK" : "FAIL",
                (rxData.sensorStatus & 0x04) ? "OK" : "N/A");
  Serial.println("============================================\n");
}

void printJSON() {
  Serial.printf("{\"packet\":%d,\"rssi\":%d,\"temp\":%.2f,\"humidity\":%.2f,\"pressure\":%.2f,\"gas\":%.0f,\"wind\":%.2f,\"pm1\":%d,\"pm25\":%d,\"pm10\":%d,\"battery_v\":%.2f,\"battery_pct\":%d,\"status\":%d}\n",
                rxData.packetCounter, rxData.rssi, rxData.temperature, rxData.humidity,
                rxData.pressure, rxData.gasResistance, rxData.windSpeed,
                rxData.pm1_0, rxData.pm2_5, rxData.pm10,
                rxData.batteryVoltage, rxData.batteryPercent, rxData.sensorStatus);
}

// ===== REQUEST FUNCTIONS =====

void sendRequestPacket() {
  uint8_t request[3] = {REQUEST_MAGIC_1, REQUEST_MAGIC_2, CMD_REQUEST_DATA};
  rf95.send(request, sizeof(request));
  rf95.waitPacketSent();
}

void sendDataRequest() {
  Serial.println("\n>>> Sending data request to outdoor station...");

  sendRequestPacket();

  requestPending = true;
  requestSentTime = millis();
  lastRequestResend = millis();

  Serial.println(">>> Request sent! Will keep sending until outdoor station responds...");
}

void resendRequestIfNeeded() {
  if (!requestPending) return;

  // Resend request every few seconds to catch the outdoor station when it wakes
  if (millis() - lastRequestResend > REQUEST_RESEND_INTERVAL_MS) {
    Serial.println(">>> Re-sending request...");
    sendRequestPacket();
    lastRequestResend = millis();
  }
}

void displayRequesting(bool fullRedraw) {
  if (fullRedraw) {
    tft.fillScreen(COLOR_BG);
    tft.drawRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_ACCENT);

    tft.setTextColor(COLOR_ACCENT);
    tft.setTextSize(1);
    tft.setCursor(4, 4);
    tft.print("REQUESTING DATA");
    tft.drawFastHLine(0, 14, SCREEN_WIDTH, COLOR_ACCENT);

    tft.setTextColor(COLOR_TEXT);
    tft.setTextSize(3);
    tft.setCursor(10, 30);
    tft.print("Sending...");

    tft.setTextColor(COLOR_DIM);
    tft.setTextSize(2);
    tft.setCursor(10, 100);
    tft.print("Waiting for wakeup");

    // Progress bar outline
    tft.drawRect(10, 140, 300, 24, COLOR_ACCENT);
  }

  // Dynamic: request count
  tft.fillRect(10, 65, 300, 28, COLOR_BG);
  unsigned long elapsed = millis() - requestSentTime;
  int requestsSent = (elapsed / REQUEST_RESEND_INTERVAL_MS) + 1;
  tft.setCursor(10, 65);
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(3);
  tft.printf("Sent: %d", requestsSent);

  // Dynamic: progress bar fill
  tft.fillRect(12, 142, 296, 20, COLOR_BG);
  int barWidth = ((elapsed % REQUEST_RESEND_INTERVAL_MS) * 296) / REQUEST_RESEND_INTERVAL_MS;
  if (barWidth > 0) {
    tft.fillRect(12, 142, barWidth, 20, COLOR_ACCENT);
  }

  // Dynamic: timeout
  tft.fillRect(10, 180, 300, 30, COLOR_BG);
  int remaining = (REQUEST_TIMEOUT_MS - elapsed) / 1000;
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(3);
  tft.setCursor(10, 180);
  tft.printf("Timeout: %ds", remaining);
}

void handleButton() {
  // Check if button is pressed (active LOW on most ESP32 boards)
  if (digitalRead(BUTTON_PIN) == LOW) {
    // Debounce
    if (millis() - lastButtonPress > BUTTON_DEBOUNCE_MS) {
      lastButtonPress = millis();

      if (!requestPending) {
        sendDataRequest();
      } else {
        Serial.println("Request already pending...");
      }
    }
  }
}

// ===== SETUP =====

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n============================================");
  Serial.println("  WEATHER STATION RECEIVER (Cloud Edition)");
  Serial.println("============================================");

  // Initialize TFT
  Serial.print("Initializing TFT (ILI9341)... ");
  tft.begin();
  tft.setRotation(3);  // Landscape, flipped
  Serial.println("OK");

  tft.fillScreen(COLOR_BG);
  tft.drawRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_ACCENT);
  tft.drawRect(1, 1, SCREEN_WIDTH - 2, SCREEN_HEIGHT - 2, COLOR_ACCENT);
  drawPanel(10, 60, 300, 120, "BOOT");
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(2);
  tft.setCursor(20, 80);
  tft.print("Initializing...");

  // Initialize LoRa
  Serial.print("Initializing LoRa... ");
  loraSerial.begin(57600, SERIAL_8N1, LORA_RX, LORA_TX);
  delay(500);

  tft.setTextSize(1);
  tft.setTextColor(COLOR_DIM);
  tft.setCursor(20, 105);
  tft.print("LoRa: ");

  if (!rf95.init()) {
    Serial.println("FAILED!");
    tft.setTextColor(COLOR_FAIL);
    tft.print("FAILED");
    while (1) delay(1000);
  }

  if (!rf95.setFrequency(LORA_FREQUENCY)) {
    Serial.println("Frequency set FAILED!");
    tft.setTextColor(COLOR_FAIL);
    tft.print("FREQ FAIL");
    while (1) delay(1000);
  }

  Serial.printf("OK (%.1f MHz)\n", LORA_FREQUENCY);
  tft.setTextColor(COLOR_OK);
  tft.printf("OK %.0f MHz", LORA_FREQUENCY);

  // Initialize WiFi
  tft.setTextColor(COLOR_DIM);
  tft.setCursor(20, 120);
  tft.print("WiFi: ");

  initWiFi();

  tft.setTextColor(wifiConnected ? COLOR_OK : COLOR_FAIL);
  tft.print(wifiConnected ? "Connected" : "Failed");

  // NTP
  tft.setTextColor(COLOR_DIM);
  tft.setCursor(20, 135);
  tft.print("NTP:  ");
  tft.setTextColor(COLOR_OK);
  tft.print("OK");

  // Ready
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(2);
  tft.setCursor(20, 155);
  tft.print("> READY");
  delay(1500);

  // Initialize button
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  Serial.println("Button initialized (GPIO0)");

  // Initialize state
  rxData.valid = false;
  memset(&cloudTelemetry, 0, sizeof(cloudTelemetry));
  forecast.valid = false;
  forecast.lastFetch = 0;
  Serial.println("\nListening for packets...");
  Serial.println("Press BOOT button to request fresh data from outdoor station.\n");
}

// ===== MAIN LOOP =====

void loop() {
  // Check WiFi connection periodically
  checkWiFiConnection();

  // Fetch forecast periodically
  if (wifiConnected && (!forecast.valid || millis() - forecast.lastFetch > FORECAST_INTERVAL_MS)) {
    fetchForecast();
  }

  // Handle button press or serial command
  handleButton();
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'r' || c == 'R') {
      if (!requestPending) {
        Serial.println(">>> Serial request triggered");
        sendDataRequest();
      } else {
        Serial.println("Request already pending...");
      }
    }
  }

  // Keep resending request while waiting
  resendRequestIfNeeded();

  // Check for request timeout
  if (requestPending && (millis() - requestSentTime > REQUEST_TIMEOUT_MS)) {
    Serial.println(">>> Request timed out. Outdoor station may be out of range.");
    requestPending = false;
  }

  // Check for incoming packets
  if (rf95.available()) {
    uint8_t buf[RH_RF95_MAX_MESSAGE_LEN];
    uint8_t len = sizeof(buf);

    if (rf95.recv(buf, &len)) {
      rxData.rssi = rf95.lastRssi();

      if (decodePayload(buf, len)) {
        packetsReceived++;
        lastPacketTime = millis();
        currentPage = PAGE_MAIN;         // Jump to main page on new data
        lastPageChange = millis();

        // Clear request pending if this was a response
        if (requestPending) {
          Serial.println(">>> Response received from outdoor station!");
          requestPending = false;
        }

        printWeatherData();
        Serial.print("JSON: ");
        printJSON();

        // Upload to cloud
        uploadToCloud();

      } else {
        packetsFailed++;
        Serial.println("Packet decode failed!");
      }
    } else {
      packetsFailed++;
      Serial.println("Receive failed!");
    }
  }

  // Update TFT display
  static unsigned long lastDisplayUpdate = 0;
  if (millis() - lastDisplayUpdate > 500) {  // Update display every 500ms
    if (requestPending) {
      bool fullRedraw = (lastRenderedPage != -3);
      lastRenderedPage = -3;
      displayRequesting(fullRedraw);
    } else {
      updateDisplay();
    }
    lastDisplayUpdate = millis();
  }

  // Serial status if no packets for a while
  static unsigned long lastStatusTime = 0;
  if (millis() - lastStatusTime > 60000) {
    lastStatusTime = millis();
    if (!rxData.valid || (millis() - lastPacketTime > 60000)) {
      Serial.printf("... waiting for packet ... (WiFi: %s, Cloud: %lu/%lu)\n",
                    wifiConnected ? "OK" : "Disconnected",
                    cloudTelemetry.successCount, cloudTelemetry.totalRequests);
    }
  }
}
