/*
 * Solar-Powered Outdoor Weather Station
 *
 * Complete sensor integration with deep sleep and LoRa transmission
 *
 * Hardware:
 * - ESP32 Dev Kit
 * - BME680 (Temperature, Humidity, Pressure, Gas/VOC)
 * - PMS7003 (Particulate Matter PM1.0, PM2.5, PM10)
 * - Anemometer (Wind Speed)
 * - INA219 (Battery/Power Monitoring)
 * - Grove LoRa E5 Module (Long-range transmission)
 * - Solar Panel + TP4056/BMS (Charging)
 *
 * Wiring:
 *   BME680 (I2C Bus 1 - separate):
 *     SDA → GPIO32
 *     SCL → GPIO33
 *     VCC → 3.3V
 *     GND → GND
 *
 *   INA219 (I2C Bus 0 - addr 0x45):
 *     SDA → GPIO21
 *     SCL → GPIO22
 *     VCC → 3.3V
 *     GND → GND
 *     VIN+ → Battery (+)
 *     VIN- → Load/ESP32
 *
 *   PMS7003 (UART):
 *     TX (Pin 5) → GPIO25 (ESP32 RX)
 *     RX (Pin 4) → GPIO26 (ESP32 TX)
 *     SET (Pin 3) → GPIO27 (Sleep control)
 *     VCC → 5V
 *     GND → GND
 *
 *   Anemometer (FG-000WIND-004):
 *     Green wire → GND
 *     Red wire → GPIO4 (with internal pull-up)
 *
 *   Grove LoRa E5:
 *     Yellow (RX) → GPIO17 (ESP32 TX2)
 *     White (TX) → GPIO16 (ESP32 RX2)
 *     Red (VCC) → 5V
 *     Black (GND) → GND
 *
 * Libraries:
 *   - Adafruit BME680 Library
 *   - Adafruit INA219
 *   - RadioHead by Mike McCauley
 */

#include <Wire.h>
#include <HardwareSerial.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME680.h>
#include <Adafruit_INA219.h>
#include <RH_RF95.h>
#include <esp_sleep.h>
#include <driver/gpio.h>

// ===== PIN DEFINITIONS =====
// I2C Bus 0 - INA219
#define I2C_SDA 21
#define I2C_SCL 22

// I2C Bus 1 - BME680 (separate bus)
#define I2C2_SDA 32
#define I2C2_SCL 33

// PMS7003 (UART1)
#define PMS_RX 25       // ESP32 receives from PMS TX
#define PMS_TX 26       // ESP32 sends to PMS RX
#define PMS_SET_PIN 27  // Sleep/wake control (moved to avoid conflict with anemometer)

// Anemometer (FG-000WIND-004)
#define ANEMOMETER_PIN 4  // Green wire → GND, Red wire → GPIO4

// LoRa (UART2)
#define LORA_RX 16
#define LORA_TX 17

// ===== CONFIGURATION =====
// Sleep configuration
#define SLEEP_MINUTES 15
#define SLEEP_DURATION_US (SLEEP_MINUTES * 60 * 1000000ULL)

// Listen check interval (for on-demand requests)
#define LISTEN_CHECK_MINUTES 1  // Every 1 minute for better on-demand responsiveness
#define LISTEN_CHECK_DURATION_US (LISTEN_CHECK_MINUTES * 60 * 1000000ULL)
#define LISTEN_WINDOW_MS 8000  // Listen for 8 seconds during check (longer = more reliable)

// Request protocol (must match indoor station)
#define REQUEST_MAGIC_1 0xAA
#define REQUEST_MAGIC_2 0x55
#define CMD_REQUEST_DATA 0x01

// LoRa configuration
#define LORA_FREQUENCY 868.0  // 868.0 MHz for EU, 915.0 for US

// Sensor timing
#define PMS_WARMUP_MS 30000      // 30 seconds for PMS7003 fan stabilization
#define WIND_SAMPLE_MS 5000     // 5 seconds for wind measurement (longer window captures gusts)
#define DEBOUNCE_TIME_MS 10     // 10ms debounce for anemometer

// Anemometer calibration (FG-000WIND-004)
// Per datasheet: 1 switch closure/sec = 2.4 km/h = 0.667 m/s
#define ANEMOMETER_KMH_PER_HZ 2.4
#define ANEMOMETER_MS_PER_HZ (ANEMOMETER_KMH_PER_HZ / 3.6)  // 0.667 m/s per Hz

// Battery configuration
#define VOLTAGE_FULL 4.2
#define VOLTAGE_EMPTY 3.0
#define BATTERY_CAPACITY_MAH 10200.0  // Adjust for your battery
#define DEEP_SLEEP_CURRENT_MA 0.01    // ~10µA

// INA219 address (adjust if using different A0/A1 config)
#define INA219_ADDRESS 0x45

// Sea level pressure for altitude (adjust for your location)
#define SEALEVELPRESSURE_HPA 1013.25

// ===== RTC MEMORY (persists through deep sleep) =====
RTC_DATA_ATTR int bootCount = 0;
RTC_DATA_ATTR uint16_t packetCounter = 0;
RTC_DATA_ATTR float totalMahUsed = 0.0;
RTC_DATA_ATTR float lastActiveCurrent = 50.0;
RTC_DATA_ATTR uint8_t listenCheckCount = 0;  // Count listen checks between full readings
#define LISTEN_CHECKS_PER_FULL_READ (SLEEP_MINUTES / LISTEN_CHECK_MINUTES)  // e.g., 15/2 = 7

// ===== GLOBAL OBJECTS =====
TwoWire I2C_BME = TwoWire(1);  // Second I2C bus for BME680
Adafruit_BME680 bme(&I2C_BME);
Adafruit_INA219 ina219(INA219_ADDRESS);
HardwareSerial pmsSerial(1);   // UART1 for PMS7003
HardwareSerial loraSerial(2);  // UART2 for LoRa
RH_RF95 rf95(loraSerial);

// ===== SENSOR STATUS FLAGS =====
bool bmeInitialized = false;
bool inaInitialized = false;
bool loraInitialized = false;

// ===== DATA STRUCTURES =====
struct WeatherData {
  float temperature;      // °C
  float humidity;         // %
  float pressure;         // hPa
  float gasResistance;    // kOhms
  float windSpeed;        // m/s
  uint16_t pm1_0;         // µg/m³
  uint16_t pm2_5;         // µg/m³
  uint16_t pm10;          // µg/m³
  float batteryVoltage;   // V
  float batteryCurrent;   // mA
  uint8_t batteryPercent; // 0-100
  bool pmsValid;
  bool bmeValid;
} weatherData;

// ===== ANEMOMETER INTERRUPT VARIABLES =====
volatile uint32_t windPulseCount = 0;
volatile unsigned long lastPulseTime = 0;

// Interrupt Service Routine for anemometer
void IRAM_ATTR anemometerISR() {
  unsigned long currentTime = millis();
  if (currentTime - lastPulseTime > DEBOUNCE_TIME_MS) {
    windPulseCount++;
    lastPulseTime = currentTime;
  }
}

// ===== INITIALIZATION FUNCTIONS =====

void initI2C() {
  // Bus 0 for INA219 (default Wire)
  Wire.begin(I2C_SDA, I2C_SCL);

  // Bus 1 for BME680 (separate bus)
  I2C_BME.begin(I2C2_SDA, I2C2_SCL);

  delay(100);
}

bool initBME680() {
  Serial.print("  BME680... ");

  if (!bme.begin()) {
    Serial.println("NOT FOUND");
    return false;
  }

  // Configure BME680 oversampling and filter
  bme.setTemperatureOversampling(BME680_OS_4X);  // Reduced from 8X for faster readings, less thermal drift
  bme.setHumidityOversampling(BME680_OS_2X);
  bme.setPressureOversampling(BME680_OS_4X);
  bme.setIIRFilterSize(BME680_FILTER_SIZE_3);
  bme.setGasHeater(320, 150);  // 320°C for 150ms

  delay(500);  // Allow sensor to thermally stabilize after init

  Serial.println("OK");
  return true;
}

bool initINA219() {
  Serial.print("  INA219... ");

  if (!ina219.begin()) {
    Serial.printf("NOT FOUND (addr 0x%02X)\n", INA219_ADDRESS);
    return false;
  }

  Serial.printf("OK (addr 0x%02X)\n", INA219_ADDRESS);
  return true;
}

void initPMS7003() {
  Serial.print("  PMS7003... ");

  // Release GPIO hold from deep sleep (so we can control it again)
  gpio_hold_dis((gpio_num_t)PMS_SET_PIN);

  // Configure SET pin for sleep control
  pinMode(PMS_SET_PIN, OUTPUT);
  digitalWrite(PMS_SET_PIN, LOW);  // Start in sleep mode

  // Initialize UART
  pmsSerial.begin(9600, SERIAL_8N1, PMS_RX, PMS_TX);

  Serial.println("OK (sleeping)");
}

void initAnemometer() {
  Serial.print("  Anemometer... ");

  pinMode(ANEMOMETER_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ANEMOMETER_PIN), anemometerISR, FALLING);

  Serial.println("OK");
}

bool initLoRa() {
  Serial.print("  LoRa... ");

  loraSerial.begin(57600, SERIAL_8N1, LORA_RX, LORA_TX);
  delay(500);

  if (!rf95.init()) {
    Serial.println("INIT FAILED");
    return false;
  }

  if (!rf95.setFrequency(LORA_FREQUENCY)) {
    Serial.println("FREQ FAILED");
    return false;
  }

  rf95.setTxPower(13, false);

  Serial.printf("OK (%.1f MHz)\n", LORA_FREQUENCY);
  return true;
}

// ===== SENSOR READING FUNCTIONS =====

bool readBME680() {
  if (!bmeInitialized) {
    weatherData.bmeValid = false;
    return false;
  }

  // Perform reading without gas first for accurate temperature
  // (gas heater self-heating affects temp sensor)
  bme.setGasHeater(0, 0);  // Disable gas heater temporarily
  if (!bme.performReading()) {
    Serial.println("  BME680 read FAILED");
    weatherData.bmeValid = false;
    return false;
  }

  weatherData.temperature = bme.temperature;
  weatherData.humidity = bme.humidity;
  weatherData.pressure = bme.pressure / 100.0;  // Pa to hPa

  // Now do gas reading separately
  bme.setGasHeater(320, 150);
  if (bme.performReading()) {
    weatherData.gasResistance = bme.gas_resistance / 1000.0;  // Ohms to kOhms
  }

  weatherData.bmeValid = true;
  return true;
}

void readINA219() {
  if (!inaInitialized) {
    weatherData.batteryVoltage = 0;
    weatherData.batteryCurrent = 0;
    weatherData.batteryPercent = 0;
    return;
  }

  weatherData.batteryVoltage = ina219.getBusVoltage_V();
  weatherData.batteryCurrent = ina219.getCurrent_mA();

  // Handle negative current
  if (weatherData.batteryCurrent < 0) {
    weatherData.batteryCurrent = 0;
  }

  // Calculate battery percentage
  if (weatherData.batteryVoltage >= VOLTAGE_FULL) {
    weatherData.batteryPercent = 100;
  } else if (weatherData.batteryVoltage <= VOLTAGE_EMPTY) {
    weatherData.batteryPercent = 0;
  } else {
    weatherData.batteryPercent = (uint8_t)((weatherData.batteryVoltage - VOLTAGE_EMPTY) /
                                           (VOLTAGE_FULL - VOLTAGE_EMPTY) * 100);
  }
}

bool readPMS7003() {
  Serial.print("  PMS7003 waking... ");

  // Wake up sensor
  digitalWrite(PMS_SET_PIN, HIGH);
  delay(100);

  // Wait for fan warmup
  Serial.print("warmup ");
  for (int i = 0; i < (PMS_WARMUP_MS / 1000); i++) {
    delay(1000);
    Serial.print(".");
  }
  Serial.print(" reading... ");

  // Clear serial buffer
  while (pmsSerial.available()) {
    pmsSerial.read();
  }

  // Read data with retries
  uint8_t buffer[32];
  int attempts = 0;
  bool success = false;

  while (attempts < 10 && !success) {
    if (pmsSerial.available() >= 32) {
      pmsSerial.readBytes(buffer, 32);

      // Check magic header bytes
      if (buffer[0] == 0x42 && buffer[1] == 0x4D) {
        // Calculate checksum
        uint16_t sum = 0;
        for (int i = 0; i < 30; i++) {
          sum += buffer[i];
        }
        uint16_t checksum = (buffer[30] << 8) | buffer[31];

        if (sum == checksum) {
          // Extract PM values (atmospheric environment)
          weatherData.pm1_0 = (buffer[10] << 8) | buffer[11];
          weatherData.pm2_5 = (buffer[12] << 8) | buffer[13];
          weatherData.pm10 = (buffer[14] << 8) | buffer[15];
          weatherData.pmsValid = true;
          success = true;
        }
      }
    }
    delay(500);
    attempts++;
  }

  // Put sensor back to sleep
  digitalWrite(PMS_SET_PIN, LOW);

  if (success) {
    Serial.println("OK");
  } else {
    Serial.println("FAILED");
    weatherData.pm1_0 = 0;
    weatherData.pm2_5 = 0;
    weatherData.pm10 = 0;
    weatherData.pmsValid = false;
  }

  return success;
}

float measureWindSpeed() {
  Serial.print("  Wind speed... ");

  // Allow anemometer to mechanically respond to current conditions
  delay(1000);  // 1 second stabilization

  // Disable interrupts while resetting counter
  noInterrupts();
  windPulseCount = 0;
  interrupts();

  unsigned long startTime = millis();

  // Count pulses for sample window
  while (millis() - startTime < WIND_SAMPLE_MS) {
    delay(10);
  }

  // Read count with interrupts disabled
  noInterrupts();
  unsigned long count = windPulseCount;
  interrupts();

  // Calculate frequency (Hz) = closures per second
  float sampleSeconds = WIND_SAMPLE_MS / 1000.0;
  float frequency = count / sampleSeconds;

  // Per datasheet: 1 closure/sec = 2.4 km/h = 0.667 m/s
  float speed = frequency * ANEMOMETER_MS_PER_HZ;

  Serial.printf("%.2f m/s (%lu pulses, %.1f Hz)\n", speed, count, frequency);

  return speed;
}

// ===== DATA TRANSMISSION =====

// Pack all sensor data into binary payload (24 bytes)
void packPayload(uint8_t* payload) {
  // Bytes 0-1: Temperature (int16, ×100)
  int16_t temp = (int16_t)(weatherData.temperature * 100);
  payload[0] = (temp >> 8) & 0xFF;
  payload[1] = temp & 0xFF;

  // Bytes 2-3: Humidity (uint16, ×100)
  uint16_t hum = (uint16_t)(weatherData.humidity * 100);
  payload[2] = (hum >> 8) & 0xFF;
  payload[3] = hum & 0xFF;

  // Bytes 4-5: Pressure (uint16, ×10)
  uint16_t press = (uint16_t)(weatherData.pressure * 10);
  payload[4] = (press >> 8) & 0xFF;
  payload[5] = press & 0xFF;

  // Bytes 6-7: Gas Resistance (uint16, kOhms)
  uint16_t gas = (uint16_t)(weatherData.gasResistance);
  payload[6] = (gas >> 8) & 0xFF;
  payload[7] = gas & 0xFF;

  // Bytes 8-9: Wind Speed (uint16, ×100)
  uint16_t wind = (uint16_t)(weatherData.windSpeed * 100);
  payload[8] = (wind >> 8) & 0xFF;
  payload[9] = wind & 0xFF;

  // Bytes 10-11: PM1.0
  payload[10] = (weatherData.pm1_0 >> 8) & 0xFF;
  payload[11] = weatherData.pm1_0 & 0xFF;

  // Bytes 12-13: PM2.5
  payload[12] = (weatherData.pm2_5 >> 8) & 0xFF;
  payload[13] = weatherData.pm2_5 & 0xFF;

  // Bytes 14-15: PM10
  payload[14] = (weatherData.pm10 >> 8) & 0xFF;
  payload[15] = weatherData.pm10 & 0xFF;

  // Bytes 16-17: Battery Voltage (uint16, ×100)
  uint16_t volt = (uint16_t)(weatherData.batteryVoltage * 100);
  payload[16] = (volt >> 8) & 0xFF;
  payload[17] = volt & 0xFF;

  // Byte 18: Battery Percent
  payload[18] = weatherData.batteryPercent;

  // Bytes 19-20: Packet Counter
  payload[19] = (packetCounter >> 8) & 0xFF;
  payload[20] = packetCounter & 0xFF;

  // Byte 21: Sensor Status Flags
  uint8_t status = 0;
  if (weatherData.bmeValid) status |= 0x01;
  if (weatherData.pmsValid) status |= 0x02;
  if (inaInitialized) status |= 0x04;
  payload[21] = status;

  // Bytes 22-23: Checksum (simple sum of bytes 0-21)
  uint16_t checksum = 0;
  for (int i = 0; i < 22; i++) {
    checksum += payload[i];
  }
  payload[22] = (checksum >> 8) & 0xFF;
  payload[23] = checksum & 0xFF;
}

bool transmitData() {
  if (!loraInitialized) {
    Serial.println("  LoRa not initialized - skip transmission");
    return false;
  }

  // Pack payload
  uint8_t payload[24];
  packPayload(payload);

  Serial.print("  Transmitting... ");

  rf95.send(payload, sizeof(payload));
  rf95.waitPacketSent();

  Serial.printf("OK (RSSI: %d dBm)\n", rf95.lastRssi());

  return true;
}

// ===== REQUEST HANDLING =====

bool checkForRequest() {
  // Quick check if LoRa has received data
  if (!loraInitialized) return false;

  if (rf95.available()) {
    uint8_t buf[RH_RF95_MAX_MESSAGE_LEN];
    uint8_t len = sizeof(buf);

    if (rf95.recv(buf, &len)) {
      // Check for valid request packet (3 bytes: magic1, magic2, command)
      if (len == 3 && buf[0] == REQUEST_MAGIC_1 && buf[1] == REQUEST_MAGIC_2) {
        if (buf[2] == CMD_REQUEST_DATA) {
          Serial.println("<<< Data request received from indoor station!");
          return true;
        }
      }
    }
  }
  return false;
}

bool listenForRequest(unsigned long durationMs) {
  Serial.printf("  Listening for requests (%lu ms)... ", durationMs);

  // Small delay to ensure LoRa is fully ready to receive
  delay(100);

  unsigned long startTime = millis();
  while (millis() - startTime < durationMs) {
    if (checkForRequest()) {
      Serial.println("REQUEST RECEIVED!");
      return true;
    }
    delay(5);  // Check more frequently
  }

  Serial.println("none");
  return false;
}

// ===== POWER MANAGEMENT =====

void updatePowerStats() {
  if (!inaInitialized) return;

  // Estimate active time for this cycle (~40 seconds)
  float activeHours = 40.0 / 3600.0;
  float mahThisCycle = weatherData.batteryCurrent * activeHours;

  // Sleep power consumption
  float sleepHours = SLEEP_MINUTES / 60.0;
  float mahSleep = DEEP_SLEEP_CURRENT_MA * sleepHours;

  totalMahUsed += mahThisCycle + mahSleep;
  lastActiveCurrent = weatherData.batteryCurrent;
}

float calculateEstimatedHours() {
  if (!inaInitialized || weatherData.batteryCurrent <= 0) {
    return 9999.0;
  }

  // Calculate duty cycle
  float activeSeconds = 40.0;
  float sleepSeconds = SLEEP_MINUTES * 60.0;
  float totalCycleSeconds = activeSeconds + sleepSeconds;

  // Average current over full cycle
  float avgCurrent = (weatherData.batteryCurrent * activeSeconds +
                      DEEP_SLEEP_CURRENT_MA * sleepSeconds) / totalCycleSeconds;

  // Remaining capacity
  float remainingCapacity = (BATTERY_CAPACITY_MAH * weatherData.batteryPercent) / 100.0;

  return remainingCapacity / avgCurrent;
}

const char* getBatteryStatus() {
  if (weatherData.batteryPercent > 75) return "Full";
  if (weatherData.batteryPercent > 50) return "Good";
  if (weatherData.batteryPercent > 25) return "Low";
  if (weatherData.batteryPercent > 10) return "Very Low";
  return "Critical";
}

void goToSleep() {
  Serial.printf("\nEntering deep sleep for %d minutes...\n", SLEEP_MINUTES);
  Serial.println("============================================\n");
  Serial.flush();

  // Ensure PMS7003 SET pin is LOW before sleep
  digitalWrite(PMS_SET_PIN, LOW);

  // Hold GPIO state during deep sleep (keeps PMS7003 fan off)
  gpio_hold_en((gpio_num_t)PMS_SET_PIN);
  gpio_deep_sleep_hold_en();

  // Configure timer wakeup
  esp_sleep_enable_timer_wakeup(SLEEP_DURATION_US);

  // Enter deep sleep
  esp_deep_sleep_start();
}

void goToListenSleep() {
  Serial.printf("\nSleeping for %d minutes (listen check interval)...\n", LISTEN_CHECK_MINUTES);
  Serial.println("============================================\n");
  Serial.flush();

  // Ensure PMS7003 SET pin is LOW before sleep
  pinMode(PMS_SET_PIN, OUTPUT);
  digitalWrite(PMS_SET_PIN, LOW);

  // Hold GPIO state during deep sleep (keeps PMS7003 fan off)
  gpio_hold_en((gpio_num_t)PMS_SET_PIN);
  gpio_deep_sleep_hold_en();

  // Configure timer wakeup for listen check interval
  esp_sleep_enable_timer_wakeup(LISTEN_CHECK_DURATION_US);

  // Enter deep sleep
  esp_deep_sleep_start();
}

// ===== DISPLAY FUNCTIONS =====

void printHeader() {
  Serial.println("\n============================================");
  Serial.println("  SOLAR WEATHER STATION");
  Serial.println("============================================");
  Serial.printf("Boot: %d | Packet: %d\n", bootCount, packetCounter);
  Serial.printf("Listen interval: %d min | Full read: %d min\n",
                LISTEN_CHECK_MINUTES, SLEEP_MINUTES);
  Serial.printf("Listen checks: %d/%d\n", listenCheckCount, LISTEN_CHECKS_PER_FULL_READ);

  // Check wakeup reason
  esp_sleep_wakeup_cause_t reason = esp_sleep_get_wakeup_cause();
  if (reason == ESP_SLEEP_WAKEUP_TIMER) {
    Serial.println("Wakeup: Timer");
  } else {
    Serial.println("Wakeup: Power on / Reset");
    listenCheckCount = LISTEN_CHECKS_PER_FULL_READ;  // Force full read on power-on
  }
  Serial.println("--------------------------------------------");
}

void printSensorData() {
  Serial.println("\n--- SENSOR READINGS ---");

  if (weatherData.bmeValid) {
    Serial.printf("Temperature:    %.2f C\n", weatherData.temperature);
    Serial.printf("Humidity:       %.2f %%\n", weatherData.humidity);
    Serial.printf("Pressure:       %.2f hPa\n", weatherData.pressure);
    Serial.printf("Gas Resistance: %.2f kOhms\n", weatherData.gasResistance);
  } else {
    Serial.println("BME680: No data");
  }

  Serial.printf("Wind Speed:     %.2f m/s\n", weatherData.windSpeed);

  if (weatherData.pmsValid) {
    Serial.printf("PM1.0:          %d ug/m3\n", weatherData.pm1_0);
    Serial.printf("PM2.5:          %d ug/m3\n", weatherData.pm2_5);
    Serial.printf("PM10:           %d ug/m3\n", weatherData.pm10);
  } else {
    Serial.println("PMS7003: No data");
  }

  Serial.println("\n--- POWER STATUS ---");
  if (inaInitialized) {
    Serial.printf("Voltage:        %.2f V\n", weatherData.batteryVoltage);
    Serial.printf("Current:        %.0f mA\n", weatherData.batteryCurrent);
    Serial.printf("Battery:        %d%% (%s)\n", weatherData.batteryPercent, getBatteryStatus());
    Serial.printf("Total mAh used: %.2f\n", totalMahUsed);
    Serial.printf("Est. remaining: %.0f hours (%.1f days)\n",
                  calculateEstimatedHours(), calculateEstimatedHours() / 24.0);
  } else {
    Serial.println("INA219: Not connected");
  }

  if (weatherData.batteryPercent <= 10) {
    Serial.println("\n*** WARNING: Battery critically low! ***");
  }
}

// ===== FULL SENSOR READING CYCLE =====

void doFullReading() {
  Serial.println("\n=== FULL SENSOR READING ===");

  // Initialize I2C bus
  Serial.println("\nInitializing sensors:");
  initI2C();

  // Initialize all sensors
  bmeInitialized = initBME680();
  inaInitialized = initINA219();
  initPMS7003();
  initAnemometer();

  Serial.println("\n--- READING SENSORS ---");

  // Read BME680 (fast)
  Serial.print("  BME680... ");
  if (readBME680()) {
    Serial.println("OK");
  }

  // Read INA219 (fast)
  Serial.print("  INA219... ");
  readINA219();
  if (inaInitialized) {
    Serial.printf("%.2fV, %.0fmA\n", weatherData.batteryVoltage, weatherData.batteryCurrent);
  } else {
    Serial.println("skipped");
  }

  // Read PMS7003 (slow - 30s warmup)
  readPMS7003();

  // Measure wind speed (3s)
  weatherData.windSpeed = measureWindSpeed();

  // Print all sensor data
  printSensorData();

  // Update power statistics
  updatePowerStats();

  // Transmit data via LoRa
  Serial.println("\n--- TRANSMISSION ---");
  if (transmitData()) {
    packetCounter++;
  }

  // Reset listen check counter
  listenCheckCount = 0;
}

// ===== QUICK LISTEN CHECK =====

bool doListenCheck() {
  Serial.println("\n=== QUICK LISTEN CHECK ===");
  Serial.printf("Listen check #%d of %d before full reading\n",
                listenCheckCount + 1, LISTEN_CHECKS_PER_FULL_READ);

  // Only initialize LoRa for quick check
  loraSerial.begin(57600, SERIAL_8N1, LORA_RX, LORA_TX);
  delay(500);  // Match main init delay for reliability

  if (!rf95.init()) {
    Serial.println("  LoRa init failed for listen check");
    return false;
  }

  if (!rf95.setFrequency(LORA_FREQUENCY)) {
    Serial.println("  Frequency set failed!");
    return false;
  }
  loraInitialized = true;

  // Listen for request
  bool requestReceived = listenForRequest(LISTEN_WINDOW_MS);

  listenCheckCount++;

  return requestReceived;
}

// ===== MAIN SETUP (all work happens here) =====

void setup() {
  Serial.begin(115200);
  delay(500);

  bootCount++;

  printHeader();

  // Determine wake type
  bool isScheduledFullRead = (listenCheckCount >= LISTEN_CHECKS_PER_FULL_READ);
  bool requestReceived = false;

  // If not time for full reading, do a quick listen check first
  if (!isScheduledFullRead) {
    // Initialize LoRa only
    loraInitialized = initLoRa();

    // Check for request from indoor station
    requestReceived = listenForRequest(LISTEN_WINDOW_MS);

    if (!requestReceived) {
      // No request - go back to sleep quickly
      Serial.printf("\nNo request. Listen check %d/%d complete.\n",
                    listenCheckCount + 1, LISTEN_CHECKS_PER_FULL_READ);
      listenCheckCount++;

      // Short sleep until next listen check
      goToListenSleep();
      return;  // Never reached
    }

    // Request received - fall through to full reading
    Serial.println("\n>>> Request received! Performing full sensor reading...");
  }

  // Do full sensor reading (scheduled or on-demand)
  loraInitialized = initLoRa();
  doFullReading();

  // Enter deep sleep until next listen check
  goToListenSleep();
}

void loop() {
  // Never reached - all work done in setup()
  // Deep sleep restarts from setup() on wake
}
