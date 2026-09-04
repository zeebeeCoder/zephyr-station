# Master/gateway firmware

Main sketch: [`gateway.ino`](gateway.ino)

The indoor ESP32 receives and validates the outdoor station's LoRa packets,
displays readings and forecasts on an ILI9341 TFT, and uploads readings to the
Zephyr ingestion API over Wi-Fi.

## Local configuration

`gateway.ino` includes `config.h`. A working local configuration was copied
during migration, but it is intentionally ignored by Git because it contains
credentials.

For a fresh checkout:

```sh
cp firmware/gateway/config.example.h firmware/gateway/config.h
```

Then fill in the Wi-Fi credentials, API endpoint/key, device ID, and location.

## Arduino libraries

- RadioHead
- Adafruit GFX Library
- Adafruit ILI9341
- ArduinoJson

Wi-Fi, HTTP, secure-client, SPI, and time support are provided by the ESP32
Arduino core.

## Migration

Copied without code changes from:

```text
miko-arduino/weather-station/weather_station_receiver_cloud/weather_station_receiver_cloud.ino
```
