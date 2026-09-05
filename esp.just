set shell := ["bash", "-euo", "pipefail", "-c"]

firmware := "./bin/firmware"

# List ESP32 firmware commands without touching hardware or build state.
[private]
default:
    @"{{ just_executable() }}" --list esp

# Check Arduino CLI, ESP32 core, source, and serial access.
doctor:
    @{{ firmware }} doctor

# Read the connected ESP32 chip and flash identity without writing.
inspect:
    @{{ firmware }} identify

# Create a private, checksummed 4 MiB rollback backup.
backup:
    @{{ firmware }} backup

# Compile incrementally; gateway is the default role.
cook role="gateway":
    @printf 'Cooking %s firmware...\n' "{{ role }}"
    @ZEPHYR_CLEAN_BUILD=0 {{ firmware }} compile "{{ role }}"

# Compile from a clean role build directory; removes fast-reflash references.
cook-clean role="gateway":
    @printf 'Clean-cooking %s firmware...\n' "{{ role }}"
    @ZEPHYR_CLEAN_BUILD=1 {{ firmware }} compile "{{ role }}"

# BLOCKED pending PKM task 2026-09-04-T0001; guarded serial delivery.
deliver role="gateway":
    @printf 'Checking whether %s firmware is approved for delivery...\n' "{{ role }}"
    @ZEPHYR_ALLOW_FLASH=1 {{ firmware }} upload "{{ role }}"

# Follow timestamped serial output without toggling DTR/RTS.
observe:
    @printf '%s\n' 'Observing ESP32 serial output; press Ctrl-C to stop...'
    @{{ firmware }} monitor

# BLOCKED pending PKM task 2026-09-04-T0001; guarded deliver, then observe.
dev role="gateway":
    @"{{ just_executable() }}" esp deliver "{{ role }}"
    @"{{ just_executable() }}" esp observe

# Remove a role build directory, including its fast-reflash references.
clean role="gateway":
    @{{ firmware }} clean "{{ role }}"
