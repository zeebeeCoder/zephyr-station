# Zephyr firmware

This directory contains the active ESP32 firmware migrated from the
`Mikobric/miko-arduino` repository. The source files were copied without
implementation changes; the originals remain in that repository.

## Components

- [`station/`](station/) — solar-powered outdoor sensor station and LoRa sender.
- [`gateway/`](gateway/) — indoor LoRa master, TFT display, Wi-Fi client, and Zephyr API uploader.

The station and gateway currently communicate using a matching 24-byte binary
packet on 868 MHz. Keep both sketches protocol-compatible when making changes.

## Configuration

Gateway credentials remain local in `gateway/config.h`, which is ignored by
Git. For a new checkout:

```sh
cp firmware/gateway/config.example.h firmware/gateway/config.h
```

Then populate the Wi-Fi and API settings.

## Migration sources

- Station: `weather-station/weather_station_solar/weather_station_solar.ino`
- Gateway: `weather-station/weather_station_receiver_cloud/weather_station_receiver_cloud.ino`
- Gateway configuration: `weather-station/weather_station_receiver_cloud/config.h`
