# Outdoor station firmware

Main sketch: [`station.ino`](station.ino)

The outdoor ESP32 reads the BME680, PMS7003, anemometer, and INA219; transmits
a 24-byte weather packet over 868 MHz LoRa; and uses deep sleep between cycles.

## Build and dependencies

```sh
just cook station
```

Compilation is supported, but deployment remains default-deny pending PKM task
`2026-09-04-T0001`, including the station ACK/buffer/idempotency acceptance work.

[`sketch.yaml`](sketch.yaml) pins the ESP32 core and indexed Arduino libraries.
The build helper downloads the required Seeed Grove LoRa UART library at an
exact Git commit into the ignored `build/` directory.

The radio dependency is **Seeed Studio's Grove - LoRa Radio 433MHz/868MHz
library**, not standard RadioHead and not the Wio-E5 AT-command library. This
Grove module exposes an SX127x radio through its UART-to-SPI bridge, and Seeed's
fork provides the templated `RH_RF95<HardwareSerial>` driver used by the
sketch.

Other direct dependencies are Adafruit Unified Sensor, Adafruit BME680, and
Adafruit INA219. The sketch includes its hardware wiring and pin assignments
in the header.

## Migration

Copied without code changes from:

```text
miko-arduino/weather-station/weather_station_solar/weather_station_solar.ino
```
