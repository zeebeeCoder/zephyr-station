# Master/gateway firmware

Main sketch: [`gateway.ino`](gateway.ino)

The indoor ESP32 receives and validates the outdoor station's LoRa packets,
displays readings and forecasts on an ILI9341 TFT, and uploads readings to the
Zephyr ingestion API over Wi-Fi.

## Local configuration

`gateway.ino` includes `config.h`. A working local configuration was copied
during migration, but it is intentionally ignored by Git because it contains
credentials.

`just esp cook gateway` creates the ignored file from `config.example.h` when it
is absent, allowing a clean checkout to compile. Before uploading, fill in the
Wi-Fi credentials, API key, device ID, and location. The guarded upload command
rejects placeholder configuration and remains default-deny pending PKM task
`2026-09-04-T0001`.
Compilation does not imply deployment approval.

## Build and dependencies

```sh
just esp cook gateway
```

[`sketch.yaml`](sketch.yaml) pins the ESP32 core and indexed Arduino libraries.
The build helper downloads the required Seeed Grove LoRa UART library at an
exact Git commit into the ignored `build/` directory.

The radio dependency is **Seeed Studio's Grove - LoRa Radio 433MHz/868MHz
library**, not standard RadioHead and not the Wio-E5 AT-command library. This
Grove module exposes an SX127x radio through its UART-to-SPI bridge, and Seeed's
fork provides the templated `RH_RF95<HardwareSerial>` driver used by this
sketch.

Other direct dependencies are Adafruit GFX, Adafruit ILI9341, and ArduinoJson.
Wi-Fi, HTTP, secure-client, SPI, and time support come from the ESP32 Arduino
core.

## Migration

Copied without code changes from:

```text
miko-arduino/weather-station/weather_station_receiver_cloud/weather_station_receiver_cloud.ino
```
