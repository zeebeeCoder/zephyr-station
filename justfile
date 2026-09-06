set shell := ["bash", "-euo", "pipefail", "-c"]

# List the available project command namespaces.
default:
    @"{{ just_executable() }}" --list

# Open the private PostgreSQL database in Rainfrog (prompts for its password).
rainfrog:
    bin/open-db

# Inspect, build, and eventually deliver ESP32 firmware.
mod esp
