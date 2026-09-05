# ESP32 firmware development

The repository contains the two active Arduino sketches recovered from
`Mikobric/miko-arduino`:

- [`gateway/gateway.ino`](gateway/gateway.ino) — mains-powered LoRa-to-HTTPS receiver, TFT display, and forecast client
- [`station/station.ino`](station/station.ino) — solar-powered outdoor sensor and LoRa sender

They communicate using a matching 24-byte binary packet over a Seeed Grove
LoRa Radio 868MHz UART bridge. The migration preserved the operational
implementation; build validation does not by itself make the legacy network
and delivery behavior production-safe.

## Validated local target

The connected board was inspected without modifying flash:

- target: `esp32:esp32:esp32` (`ESP32 Dev Module`)
- chip: ESP32-D0WD-V3 revision 3.1
- flash: 4 MB, 80 MHz, DIO
- crystal: 40 MHz
- USB bridge: Silicon Labs CP2102
- stable port: `/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0`
- safe serial/upload rate on this connection: 115200 baud
- partition layout: default 4 MB OTA layout (two 1280 KiB app slots)

Arduino CLI 1.4.1 and Espressif's `esp32:esp32` core 3.3.11 are installed. A temporary minimal sketch compiles successfully with these settings. The existing device image was built with core 3.3.7, so compile and hardware-test the recovered source against 3.3.11 before relying on it.

## Serial permissions (`uucp`)

On this Arch Linux system, `/dev/ttyUSB0` is owned by `root:uucp` with mode `0660`. The user is already listed in the `uucp` group, but existing shells do not gain new group membership automatically.

For the current terminal, start a group-enabled subshell with `newgrp uucp`; otherwise log out and back in. Then verify:

```bash
id -nG | tr ' ' '\n' | grep '^uucp$'
test -r /dev/ttyUSB0 && test -w /dev/ttyUSB0
```

Do not run Arduino CLI as root and do not change the serial device to world-writable. No additional `sudo` setup is required.

## Workflow

The root `justfile` exposes monorepository command namespaces. Mise pins `just`
in `mise.toml`. `just esp` only lists the ESP32 recipes; it does not compile or
access hardware:

```bash
just esp
just esp doctor
just esp inspect
just esp backup
just esp cook                 # gateway by default
just esp cook station
just esp cook-clean gateway
just esp deliver gateway
just esp dev gateway
just esp observe
just esp clean gateway
```

`cook` is incremental and retains the role's build directory. `cook-clean` is
for stale-build diagnosis and release validation: Arduino CLI's `--clean`
removes all existing role build content, including fast-reflash references,
before rebuilding. `clean` removes the complete role build directory, also
including those references. The first build may download pinned profile
packages. Build output remains under ignored `build/firmware/` storage.

The role defaults to `gateway` for cook, cook-clean, deliver, dev, and clean;
pass `station` for the outdoor sender. `observe` attaches a timestamped serial
monitor without toggling reset. `dev` is exactly guarded deliver followed by
observe; a failed delivery prevents observation.

`bin/firmware` remains the sole implementation of role validation, device,
backup, build, clean, and upload policy. The `esp` Just module only delegates.
The former unnamespaced root recipes are not retained as a second public
command surface.

`upload` is deliberately guarded. It:

1. fails closed by default while PKM task `2026-09-04-T0001` remains unresolved;
2. independently requires an explicitly reviewed `ZEPHYR_ALLOW_UNHARDENED_FIRMWARE=1` legacy bench override;
3. independently requires explicit `ZEPHYR_ALLOW_FLASH=1` confirmation;
4. requires a complete checksummed 4 MiB backup;
5. rejects invalid roles and placeholder gateway configuration before compilation;
6. compiles successfully before touching the device;
7. uses DIO, the existing default OTA partition layout, 115200 baud, and no full-flash erase;
8. requests upload verification.

The hardening override is intentionally not set by `just esp deliver` or
`just esp dev`. Remove this temporary override path when the acceptance checks
in PKM task `2026-09-04-T0001` are complete; do not normalize it as the
production deployment interface.

Private backups are written outside Git under `~/.local/state/zephyr-station/firmware-backups/` with restrictive permissions. They may contain Wi-Fi or API credentials from NVS and must never be committed or shared.

The USB connection proved unreliable for long reads above 115200 baud, so the backup command reads verified 64 KiB chunks with retries. Expect it to take several minutes. A valid backup can be reused across ordinary development uploads; take another after intentional changes to on-device configuration or stored data.

## Differential serial flashing

Arduino-ESP32 3.3.11 routes serial upload through its installed `flasher.py`
wrapper and esptool 5.3.1. The wrapper stores these per-role references in
`build/firmware/<role>/` after a successful upload:

```text
<role>.ino_flashed.bin
<role>.ino.bootloader_flashed.bin
<role>.ino.partitions_flashed.bin
boot_app0_flashed.bin
```

On the next upload, available bootloader, partition, and application references
are passed to esptool with `--diff-with`. esptool compares 4 KiB sectors,
retains its on-device MD5 checks and full-write fallback, uses compressed
transfer, and verifies the write. Never add `--trust-flash-content` or disable
verification. Although the wrapper records `boot_app0_flashed.bin`, it always
passes `skip` for `boot_app0.bin` so the OTA-slot selector is fully rewritten.

The installed CLI/platform behavior was observed without a device:

| Action | Role build directory | Reference result | Next serial upload |
|---|---|---|---|
| Fresh worktree | absent | none | full |
| First successful upload without references | present | saves all four | subsequent upload can be differential |
| `just esp cook <role>` | retained | existing references unchanged | differential remains available |
| Successful repeat upload | retained | refreshes all four | differential remains available |
| Failed upload | retained | existing references unchanged; none created on first failure | prior state remains |
| `just esp cook-clean <role>` | recreated by Arduino CLI | references removed | full |
| `just esp clean <role>` | removed | references removed | full |
| Manual deletion of ignored build state | absent | references removed | full |

Reference files describe the last successful serial upload from that role build
path. Do not treat them as a backup or copy them between devices. An OTA update,
unknown device state, fresh checkout, or intentionally removed build state
requires the verified full-write fallback. The private 4 MiB backup remains the
recovery artifact.

## Measured feedback loop

Merged firmware on this Ryzen 7 8700G host with Arduino CLI 1.4.1 measured:

| Role | Clean build | Unchanged incremental | Application image |
|---|---:|---:|---:|
| gateway | 21.24 s | 6.57 s | 1,124,912 B |
| station | 9.72 s | 3.41 s | 328,448 B |

A device-free comparison found that a representative same-length one-character
source edit changed 66 bytes across two 4 KiB application sectors for each
role. That is a best case, not a promise for size-changing edits, but it shows
why retaining the platform's reference files can materially reduce serial
transfer.

At 115200 baud, a full gateway upload is still expected to dominate the loop.
Exact full, unchanged, small-edit, and size-changing upload timings must be
measured only after PKM task `2026-09-04-T0001` approves a hardware release.

The CP2102 and ESP32 support faster rates. Removing two USB hub tiers improved short transfers: three 64 KiB reads passed with matching checksums at each of 115200, 230400, 460800, and 921600. Sustained 1.25 MiB qualification was different: 921600, 460800, and 230400 each stopped mid-transfer, while 115200 passed twice with matching checksums in approximately 122 seconds per read. Therefore 115200 remains the only qualified safe upload rate.

For a faster serial loop, change one physical variable at a time and repeat the sustained test: use a short known-good shielded data cable, disconnect peripherals that may contend with boot/UART pins or cause power dips, and finally try another ESP32 board/USB-UART bridge. Do not select a rate based only on a short successful transfer. Espressif likewise recommends lowering baud and removing attached GPIO devices when diagnosing esptool communication: <https://docs.espressif.com/projects/esptool/en/latest/esp32/troubleshooting.html>.

After serial recovery is proven, consider a development-only authenticated OTA path. The existing two-slot partition table is OTA-capable. OTA avoids the slow UART transfer, but it must not weaken network or update authentication, and the serial backup/recovery path must remain available.

## Toolchain decision

Use Arduino CLI first:

- Espressif's current Arduino-ESP32 documentation targets core 3.3.11, exactly the installed core: <https://docs.espressif.com/projects/arduino-esp32/en/latest/>.
- Arduino CLI build profiles provide reproducible platform and library versions in `sketch.yaml`: <https://arduino.github.io/arduino-cli/1.4/sketch-project-file/>.
- PlatformIO has convenient declarative environments and `lib_deps`, but its official Espressif32 platform currently identifies Arduino 2.0.17 rather than 3.x: <https://github.com/platformio/platform-espressif32/releases>. The community `pioarduino` platform supports 3.3.11, but adopting it now would add a second package ecosystem before a real need is measured.
- ESP-IDF uses Ninja/Make incremental builds: <https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/tools/idf-py.html>. Migrating this existing Arduino application to native IDF is not justified merely to save a few seconds of build time.
- Espressif documents network update behavior and prerequisites here: <https://docs.espressif.com/projects/arduino-esp32/en/latest/ota_web_update.html>.

Re-evaluate PlatformIO or native ESP-IDF only if the recovered source exposes concrete limitations in Arduino CLI (complex multi-environment builds, JTAG debugging, native component requirements, or materially worse measured build times).

## Dependencies and local configuration

Each role has a `sketch.yaml` profile that pins Arduino-ESP32 3.3.11 and its
indexed library versions. `just esp cook gateway|station` uses that profile and may
download missing pinned packages.

The radio is the older **Seeed Grove LoRa Radio 433MHz/868MHz** with a UART-to-SPI
bridge. It requires Seeed's templated UART `RH_RF95` fork—not standard RadioHead
and not the Wio-E5 AT-command library. The published 2.0.0 archive does not
compile on ESP32, so `bin/firmware` fetches the reviewed upstream commit
`f82d4dc943e8c91fd80ecef5fa5f1a625466ca0d` into ignored build storage before
compilation.

The gateway expects ignored `gateway/config.h`. On its first build the helper
copies `gateway/config.example.h`, which contains safe placeholders and the
current non-secret API endpoint. Populate credentials and location locally;
the guarded upload refuses placeholder values.

Keep role-local `config.h`, `secrets.h`, and `trust_anchor.h` files out of Git.
Follow [`../docs/esp32-integration-guide.md`](../docs/esp32-integration-guide.md):
retain TLS hostname and CA verification, synchronize time with NTP, and never
use `setInsecure()`.

## Migration provenance and deployment status

The implementation was migrated from:

- station: `weather-station/weather_station_solar/weather_station_solar.ino`
- gateway: `weather-station/weather_station_receiver_cloud/weather_station_receiver_cloud.ino`
- local gateway configuration: `weather-station/weather_station_receiver_cloud/config.h`

The original files remain in `Mikobric/miko-arduino`.

Compilation is only the migration gate. Deployment remains default-deny until
the acceptance criteria in PKM task `2026-09-04-T0001` are complete, including
tests of the legacy gateway's TLS trust, unavailable-time behavior, required
sensor validation, and the station/gateway ACK-buffer-idempotency protocol.
