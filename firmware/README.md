# ESP32 firmware development

The repository reserves two Arduino sketch directories:

- `gateway/gateway.ino` — mains-powered LoRa-to-HTTPS receiver
- `station/station.ino` — outdoor sensor and LoRa sender

Those source files are not present in this checkout yet. The connected board currently runs an existing **Weather Station Receiver (Cloud Edition)** gateway image, so do not replace it with a placeholder sketch. Retrieve the original source before uploading.

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

The root `justfile` is the normal orchestration interface. Mise pins `just` in `mise.toml`. Run `just` to see all recipes:

```bash
just doctor
just inspect
just cook gateway
just backup
just deliver gateway
just observe
```

For the normal edit-build-flash-log loop:

```bash
just dev gateway
```

`cook` means compile, `deliver` means compile + guarded flash + verification, and `observe` means attach a timestamped serial monitor without toggling reset. The role defaults to `gateway`; pass `station` for the outdoor sender.

Builds are incremental by default. Use `just cook-clean gateway` only when diagnosing a stale-build problem or validating a clean release build. Build output stays under the ignored `build/firmware/` directory.

`bin/firmware` remains the lower-level implementation and may be called directly for scripting. The justfile intentionally contains no duplicated device or flash logic.

`upload` is deliberately guarded. It:

1. requires explicit `ZEPHYR_ALLOW_FLASH=1` confirmation;
2. requires a complete checksummed 4 MiB backup;
3. compiles successfully before touching the device;
4. uses DIO, the existing default OTA partition layout, 115200 baud, and no full-flash erase;
5. requests upload verification.

Private backups are written outside Git under `~/.local/state/zephyr-station/firmware-backups/` with restrictive permissions. They may contain Wi-Fi or API credentials from NVS and must never be committed or shared.

The USB connection proved unreliable for long reads above 115200 baud, so the backup command reads verified 64 KiB chunks with retries. Expect it to take several minutes. A valid backup can be reused across ordinary development uploads; take another after intentional changes to on-device configuration or stored data.

## Measured feedback loop

A representative sketch using Wi-Fi, TLS, HTTP, and SPIFFS produced a 910 KB application on this Ryzen 7 8700G host. Arduino CLI 1.4.1 measured:

| Operation | Wall time |
|---|---:|
| Cold build | 17.97 s |
| Unchanged incremental build | 5.44 s |
| One source change, incremental build | 5.54 s |

These are synthetic toolchain measurements; benchmark the recovered gateway source before optimizing further.

The existing gateway image is approximately 1.14 MB and deflates to about 726 KB. At 115200 baud, UART framing makes roughly 63 seconds the payload-only lower bound, before erase, protocol, bootloader, and reset overhead. Expect approximately 70–90 seconds for a real serial upload and roughly 75–100 seconds for an incremental edit-build-upload cycle. This estimate must be replaced with a measured upload time once source is available.

The CP2102 and ESP32 support faster rates. Removing two USB hub tiers improved short transfers: three 64 KiB reads passed with matching checksums at each of 115200, 230400, 460800, and 921600. Sustained 1.25 MiB qualification was different: 921600, 460800, and 230400 each stopped mid-transfer, while 115200 passed twice with matching checksums in approximately 122 seconds per read. Therefore 115200 remains the only qualified safe upload rate.

For a faster serial loop, change one physical variable at a time and repeat the sustained test: use a short known-good shielded data cable, disconnect peripherals that may contend with boot/UART pins or cause power dips, and finally try another ESP32 board/USB-UART bridge. Do not select a rate based only on a short successful transfer. Espressif likewise recommends lowering baud and removing attached GPIO devices when diagnosing esptool communication: <https://docs.espressif.com/projects/esptool/en/latest/esp32/troubleshooting.html>.

After the original gateway source is recovered and serial recovery is proven, consider a development-only authenticated OTA path. The existing two-slot partition table is OTA-capable. OTA avoids the slow UART transfer, but it must not weaken network or update authentication, and the serial backup/recovery path must remain available.

## Toolchain decision

Use Arduino CLI first:

- Espressif's current Arduino-ESP32 documentation targets core 3.3.11, exactly the installed core: <https://docs.espressif.com/projects/arduino-esp32/en/latest/>.
- Arduino CLI build profiles provide reproducible platform and library versions in `sketch.yaml`: <https://arduino.github.io/arduino-cli/1.4/sketch-project-file/>.
- PlatformIO has convenient declarative environments and `lib_deps`, but its official Espressif32 platform currently identifies Arduino 2.0.17 rather than 3.x: <https://github.com/platformio/platform-espressif32/releases>. The community `pioarduino` platform supports 3.3.11, but adopting it now would add a second package ecosystem before a real need is measured.
- ESP-IDF uses Ninja/Make incremental builds: <https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/tools/idf-py.html>. Migrating this existing Arduino application to native IDF is not justified merely to save a few seconds of build time.
- Espressif documents network update behavior and prerequisites here: <https://docs.espressif.com/projects/arduino-esp32/en/latest/ota_web_update.html>.

Re-evaluate PlatformIO or native ESP-IDF only if the recovered source exposes concrete limitations in Arduino CLI (complex multi-environment builds, JTAG debugging, native component requirements, or materially worse measured build times).

## Dependencies and secrets

Do not guess library versions before the firmware source is recovered. Compile first, then install only the libraries required by its includes, for example:

```bash
arduino-cli lib search '<library name>'
arduino-cli lib install '<exact library name>@<version>'
```

Once dependencies are known, record them in an Arduino `sketch.yaml` profile so another machine can reproduce the build.

Keep role-local `secrets.h` and `trust_anchor.h` files out of Git. Follow [`../docs/esp32-integration-guide.md`](../docs/esp32-integration-guide.md): retain TLS hostname and CA verification, synchronize time with NTP, and never use `setInsecure()`.

## Current blocker

Neither local Git history nor any branch contains Arduino source, and the `Mikobric/miko-arduino` repository named in `RECAP.md` is not available to the configured GitHub account. Obtain the gateway/station sketch source (likely from the Mac that built the current image) and place it in the paths above. Compiled flash images cannot be converted back into the original maintainable C++ source.
