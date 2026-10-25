# Station PCB requirements

Status: **F1 draft for review**, 25.10.2026, written by `mobric/pcb-opus-5-5`. Nothing here is approved until mobric signs off the decisions in [ARCHITECTURE.md](ARCHITECTURE.md).

This board replaces the current outdoor-station prototype: an ESP32 DevKit, a Grove LoRa module, a 5 V step-up, a DFRobot INA219 wattmeter and a CN3791 charger module, all on wires. The goals are a much lower sleep current, charging that is safe for the cells in winter, and fewer loose parts, while the station stays radio-compatible with the unchanged gateway.

## Labels and sources

Every number carries a label:

- **datasheet**: a published manufacturer document, standard, library source or dataset (including PVGIS model output).
- **measured**: a bench measurement by a third party. Nobody has measured this station yet.
- **assumed**: an engineering assumption.
- **computed**: derived from labelled inputs. The formulas are in ARCHITECTURE.md.

Project sources:

- `MIKO-DATA.md` and photos from mobric, 25.10.2026, kept outside the repo.
- `firmware/station/station.ino` and `firmware/gateway/gateway.ino` at commit 82ee40d.
- `docs/prd-tech-design.md`.

Datasheet and dataset links are listed in [ARCHITECTURE.md § Sources](ARCHITECTURE.md#sources).

## 1. Current station (as found)

### Hardware

| Item | Fact | Label |
|---|---|---|
| Panel | SunUP SR10-36M, mono, 36 cells, 10 W ±3 %, Vmp 18.7 V, Imp 0.54 A, Voc 22.4 V, Isc 0.59 A | datasheet (panel label, photo IMG_2738) |
| Battery | 3 × 18650 in parallel (1S3P), 10 200 mAh, 3.0–4.2 V. mobric said "szeregowo" (series), but 3.7 V nominal means parallel | datasheet (MIKO-DATA) |
| Protection | External "BMS 1S 10A" board: two ST 95N3LLH6 MOSFETs and a small protection IC. Cells on B+/B−; charger and load share P+/C− | datasheet (listing screenshot, bms.png) |
| Charger | Generic CN3791 MPPT module, pad set to "12V", feeding the protection board. A TP4056 module also feeds the protection board, probably for USB charging (unconfirmed) | datasheet (MIKO-DATA) |
| Load path | Protection board → INA219 (DFRobot SEN0291, 0x45) → 5 V step-up → DevKit VIN. The DevKit's AMS1117 makes 3.3 V for BME680 and INA219; the DevKit 5V pin feeds PMS7003 and the Grove LoRa module | datasheet (MIKO-DATA, confirmed by mobric) |
| Cables | Two-wire runs to the anemometer and the panel, each < 1 m; Cat5e run to the BME680, < 1 m | datasheet (MIKO-DATA) |
| Gateway distance | About 20 m | datasheet (MIKO-DATA) |
| Location | 50.90 N, 15.73 E (Jelenia Góra valley), as used for forecasts in `frontend/lib/tools/forecast.ts` | assumed: the station sits at the forecast point |

### Problems found while reading the sources

These are the reasons for the new board. None of them has been measured on the station.

1. **High sleep current, estimated at 22–46 mA from the battery.** The firmware assumes 10 µA (`DEEP_SLEEP_CURRENT_MA 0.01`). Contributors:
   - The DevKit itself sleeps at 3.8–12.2 mA when fed at 5 V (measured, two third-party boards). Its AMS1117 alone has 5 mA quiescent current (datasheet).
   - The Grove LoRa module draws 8.4 mA in standby (datasheet, Seeed).
   - The firmware never calls `rf95.sleep()`, so after every listen window the radio stays in receive mode through deep sleep (datasheet, RadioHead source: `available()` switches to RX).
   - The INA219 draws 0.7 mA and is never powered down (datasheet).
   - The PMS7003 draws ≤ 200 µA in standby (datasheet).
   - The step-up module idles at about 1–1.5 mA (measured, informal).

   The total is computed. At that rate the sleep current alone uses 0.53–1.10 Ah/day, and a full pack lasts about 6–12 days without sun.
2. **About 30 % of panel power is wasted by the MPPT setting.** The module's "12V" pad most likely holds the panel near 11.9 V (computed, from a third-party teardown of the divider values), against a Vmp of 18.7 V. A 36-cell panel at 12 V delivers about 7 W instead of 10 W (assumed I-V curve shape).
3. **No cold-charge protection.** The CN3791 has no temperature (NTC) input (datasheet), and the 18650 cells must not be charged below 0 °C (datasheet: Panasonic NCR18650B, LG MJ1, Samsung 35E). In December, 37 % of the PV energy here arrives while the air is below 0 °C (datasheet, PVGIS ERA5 2005–2023).
4. **Reported battery current is probably 10× too low.**
   - The firmware calls `ina219.begin()` without calibration. Adafruit_INA219 then assumes a 0.1 Ω shunt.
   - The DFRobot SEN0291 board has a 10 mΩ shunt (datasheet).
   - Reported current is therefore 1/10 of the real value (computed). Needs a bench check.
   - The current is used only for local estimates; it isn't sent in the packet.
5. **The cycle is about 19.4 min, not 15 min.** The firmware sleeps a fixed 60 s after every wake. One cycle is 16 sleeps, 15 listen wakes of about 9.4 s and one full read of about 65 s (computed from the source code).
6. **The radio transmits at about 10 dBm, not 13 dBm.** The Seeed fork maps `setTxPower(13, false)` to register value 0x88, which is 10 dBm. RadioHead 1.147 maps the same call to 13 dBm (datasheet: both library sources and the SX1276 register table).

## 2. Requirements

Each requirement has an ID. "Verify" says how F2–F6 check it.

### Function and interfaces

| ID | Requirement | Verify |
|---|---|---|
| R-F1 | Keep all current measurements: BME680 (T, RH, p, gas), PMS7003 (PM1, PM2.5, PM10), wind speed (reed anemometer FG-000WIND-004, 2.4 km/h per Hz), battery voltage and current (INA219 at 0x45) | F2 netlist review |
| R-F2 | BME680 stays off-board in a radiation shield on the existing < 1 m Cat5e cable, on its own I²C bus (GPIO32/33). The board provides 3.3 V, GND, SDA and SCL with pull-ups and ESD protection at the connector | F2 review, F6 test |
| R-F3 | PMS7003 runs from a 5 V rail (4.5–5.5 V, datasheet) that the firmware switches off completely between readings. The rail must truly disconnect (no path from the battery through the boost) | F2 review, F6 measure |
| R-F4 | An unpowered PMS7003 must not be back-powered through its UART or SET lines: series resistors on the board plus a firmware pin-parking routine | F6 measure |
| R-F5 | Anemometer input with debounce filter and ESD protection; keep GPIO4 | F2 review |
| R-F6 | Reserve an ADC1 input with connector for a future wind vane (PRD), and an optional 1-Wire header (DS18B20) | F2 review |
| R-F7 | Radio: an SX1276 868 MHz module on SPI, interoperating with the unchanged gateway at 868.0 MHz with RadioHead defaults (BW125, CR4/5, SF7, CRC on, sync word 0x12, 4-byte RadioHead header, broadcast address) and the same 24-byte packet | F6 bench test against the gateway |
| R-F8 | External 868 MHz antenna: u.FL on the board, pigtail to an SMA bulkhead on the enclosure, 50 Ω track, matching-network footprint, low-capacitance ESD diode | F3 layout review, F6 RSSI test |
| R-F9 | Programming and logs over USB-C with auto-reset. The USB-UART bridge runs from USB power only, so it draws nothing from the battery when USB is unplugged | F6 measure |
| R-F10 | Readable charger status (CN3791 CHRG) on a GPIO | F2 review |

### Power

| ID | Requirement | Verify |
|---|---|---|
| R-P1 | Panel input 0–26 V. Cold open-circuit voltage at −20 °C is about 25.4 V (computed from the assumed −0.30 %/°C coefficient). Reverse-polarity protected, no battery drain through the input at night. Power parts on this net rated ≥ 40 V (assumed margin) | F2 review |
| R-P2 | MPPT charging from the panel with the operating point set for Vmp 18.7 V. CN3791 regulation 1.205 V ±2 % (datasheet) gives about 18.3–19.1 V | F2 calculation, F6 measure |
| R-P3 | Charge current limited to about 1.5 A (CN3791 RCS 0.082 Ω). Charge voltage 4.2 V ±1 % (datasheet) | F2 calculation |
| R-P4 | **No charging below 0 °C or above 45 °C at the cells**, enforced in hardware, independent of firmware. An NTC sits on the cell holder. An open or shorted NTC must block charging | F6 test with heat and cold spray, or a resistor substitute |
| R-P5 | Battery input 3.0–4.2 V from the protection board's P+/C−. Polarised connector, reverse-polarity protection and a fuse on the board | F2 review |
| R-P6 | 3.3 V rail held at 3.3 V across the whole 3.0–4.2 V battery range, ≥ 500 mA capability. ESP32 requires 3.0–3.6 V and a ≥ 0.5 A supply (datasheet) | F2 review, F6 measure |
| R-P7 | **Sleep current from the battery ≤ 100 µA** for the whole board in deep sleep with radio and sensors asleep. The design estimate is 53 µA (computed) | F6 measure with a µA meter |
| R-P8 | A removable link in the battery path, so sleep current can be measured with a meter in series | F3 layout review |
| R-P9 | INA219 at 0x45 measures the battery path (signed: charge and discharge) with a 0.1 Ω shunt. This matches the Adafruit library's default calibration, so the reported current becomes correct without a firmware change | F6 compare with a meter |
| R-P10 | Energy: average December harvest covers the daily use, and the battery bridges the worst recorded dark spell. See the budget in ARCHITECTURE.md | F1 review (this phase) |

### Environment

| ID | Requirement | Verify |
|---|---|---|
| R-E1 | Operating range inside the enclosure −20 to +50 °C (assumed). PVGIS ERA5 gives a December absolute minimum of −20.2 °C and a typical coldest hour of −10.6 °C (datasheet). Prefer parts rated −40 °C; list every part rated only to −20 °C | F2 BOM review |
| R-E2 | Known limits: PMS7003 operates only from −10 °C (datasheet), so the firmware skips PM readings below −10 °C. RFM95W is rated −20 to +70 °C (datasheet, V1.0) | F5 firmware |
| R-E3 | ESD or TVS protection on every line that leaves the enclosure: panel, anemometer, BME680 cable, wind vane, 1-Wire, antenna | F2 review |
| R-E4 | Condensation in the outdoor box: no exposed unprotected high-impedance nodes. Conformal coating is an option for mobric to decide (open question) | F3 review |

### Compatibility and firmware

| ID | Requirement | Verify |
|---|---|---|
| R-C1 | Keep current GPIOs where possible. Every change is listed with its firmware impact in [ARCHITECTURE.md § Pin table](ARCHITECTURE.md#3-pin-table) | F1 and F2 review |
| R-C2 | Radio output ≤ 25 mW ERP (14 dBm) in 868.0–868.6 MHz with ≤ 1 % duty cycle (datasheet: ERC/REC 70-03, EN 300 220). Firmware sets `setTxPower(10, false)` to match today's output | F6 measure |
| R-C3 | Firmware is only compiled (`just esp cook station`), never flashed without mobric, per the PKM lock 2026-09-04-T0001 | process |
| R-C4 | The same module family as today: ESP32 (D0WD-V3 class) with 4 MB flash, so the Arduino core and sketch settings stay the same | F2 review |

### Manufacturing and service

| ID | Requirement | Verify |
|---|---|---|
| R-M1 | JLCPCB, 2 layers, 1.6 mm FR-4, SMD assembly. Every part has an LCSC number, stock and a check date | F2 BOM |
| R-M2 | Board outline is a parameter (D11 open): outline, mounting holes and connector edge come from a few values in one place | F3 |
| R-M3 | Locking polarised connectors (JST-PH or -XH), with silkscreen labels and polarity marks | F3 review |
| R-M4 | Test points on every rail (VBAT, VPANEL, 3V3, 5V_PMS) and on UART0, I²C0 and I²C1 | F3 review |
| R-M5 | M3 mounting holes | F3 review |

### Out of scope for v1

- Wi-Fi or BLE use on the station. The ESP32 radio stays off.
- Changes to the gateway hardware or firmware.
- A custom BME680 sensor board. The existing breakout and cable stay.
- On-board cell protection (see D5.2 in ARCHITECTURE.md).
- A graphical schematic. atopile code is the schematic.

## 3. Energy summary

Full details, inputs and sources are in [ARCHITECTURE.md § Power budget](ARCHITECTURE.md#4-power-budget).

| Case | Result (computed) |
|---|---|
| Deep sleep, whole board, from the battery | 53 µA (1.3 mAh/day) |
| Daily use, minimum firmware changes, intended cadence (1-min listen, 15-min full read) | 372 mAh (1.38 Wh), up to 517 mAh (1.91 Wh) pessimistic |
| Daily use with the optional firmware changes | 182–218 mAh (0.67–0.81 Wh) |
| December mean harvest into the battery, 60° south, no charging below 0 °C | 8.7 Wh/day |
| Worst 14-day period (Dec 2018) mean harvest into the battery | 1.6 Wh/day, about break-even |
| Autonomy with no sun at all | 15–21 days (minimum firmware changes), 36–43 days (optional changes) |

**Verdict:** 10 W and 10.2 Ah are enough for the new board. The main uncertainties are shading by buildings or trees (the December sun peaks at 15.6°), snow on the panel, and the real ESP32 awake current.

## 4. Open questions for mobric

See [ARCHITECTURE.md § Open questions](ARCHITECTURE.md#8-open-questions-for-mobric); the list is kept in one place.
