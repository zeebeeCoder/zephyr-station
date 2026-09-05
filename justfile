set shell := ["bash", "-euo", "pipefail", "-c"]

# List the available project command namespaces.
default:
    @"{{ just_executable() }}" --list

# Inspect, build, and eventually deliver ESP32 firmware.
mod esp
