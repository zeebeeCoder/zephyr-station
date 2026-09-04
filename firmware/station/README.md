# Outdoor station firmware

Main sketch: [`station.ino`](station.ino)

The outdoor ESP32 reads the BME680, PMS7003, anemometer, and INA219; transmits
a 24-byte weather packet over 868 MHz LoRa; and uses deep sleep between cycles.

## Arduino libraries

- Adafruit Unified Sensor
- Adafruit BME680 Library
- Adafruit INA219
- RadioHead

The sketch includes its hardware wiring and pin assignments in the header.

## Migration

Copied without code changes from:

```text
miko-arduino/weather-station/weather_station_solar/weather_station_solar.ino
```
