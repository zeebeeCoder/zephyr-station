set shell := ["bash", "-euo", "pipefail", "-c"]

firmware := "./bin/firmware"

# List the available project commands.
default:
    @just --list

# Check Arduino CLI, ESP32 core, source, and serial access.
doctor:
    @{{ firmware }} doctor

# Read the connected ESP32 chip and flash identity without writing.
inspect:
    @{{ firmware }} identify

# Create a private, checksummed 4 MiB rollback backup.
backup:
    @{{ firmware }} backup

# Compile incrementally: `just cook` or `just cook station`.
cook role="gateway":
    @printf 'Cooking %s firmware...\n' "{{ role }}"
    @ZEPHYR_CLEAN_BUILD=0 {{ firmware }} compile "{{ role }}"

# Compile without cached build artifacts.
cook-clean role="gateway":
    @printf 'Clean-cooking %s firmware...\n' "{{ role }}"
    @ZEPHYR_CLEAN_BUILD=1 {{ firmware }} compile "{{ role }}"

# Compile, validate the rollback backup, flash, and verify.
deliver role="gateway":
    @printf 'Delivering %s firmware over the qualified 115200-baud connection...\n' "{{ role }}"
    @ZEPHYR_ALLOW_FLASH=1 {{ firmware }} upload "{{ role }}"

# Follow timestamped serial output without toggling DTR/RTS.
observe:
    @printf '%s\n' 'Observing ESP32 serial output; press Ctrl-C to stop...'
    @{{ firmware }} monitor

# Deliver a role and immediately attach its serial monitor.
dev role="gateway":
    @just deliver "{{ role }}"
    @just observe

# Remove generated build artifacts for a role.
clean role="gateway":
    @case "{{ role }}" in gateway|station) ;; \
      *) echo "ERROR: role must be 'gateway' or 'station'" >&2; exit 1 ;; \
    esac
    @rm -rf "build/firmware/{{ role }}"
    @printf 'Removed build/firmware/%s\n' "{{ role }}"

alias build := cook
alias flash := deliver
alias identify := inspect
alias monitor := observe
