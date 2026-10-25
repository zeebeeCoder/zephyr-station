# Station PCB requirements

Status: **F1 revision 1 for review**, 25.10.2026, written by `mobric/pcb-opus-5-5`.
- It revises the F1 draft (4cd5e93) after the Codex review in [reviews/F1-codex.md](reviews/F1-codex.md). The item-by-item response is in [reviews/F1-response.md](reviews/F1-response.md).
- It folds in mobric's answers to the 14 F1 questions, relayed by the coordinator on 25.10.2026.
- Nothing here is approved until mobric signs off the decisions in [ARCHITECTURE.md](ARCHITECTURE.md).

This board replaces the current outdoor-station prototype: an ESP32 DevKit, a Grove LoRa module, a 5 V step-up, a DFRobot INA219 wattmeter and a CN3791 charger module, all on wires. The goals:
- a much lower sleep current;
- charging that is safe for the cells in winter;
- a winter energy plan that holds up hour by hour;
- fewer loose parts;
- radio compatibility with the unchanged gateway.

## Labels and sources

Every number carries a label:

- **datasheet**: a published manufacturer document, standard or library source.
- **owner/photo**: stated by mobric, or read from mobric's photos and listing screenshots (`MIKO-DATA.md`). It is not a manufacturer specification.
- **measured**: a bench measurement with a traceable source. Nobody has measured this station yet.
- **assumed**: an engineering assumption, including any figure without a traceable source.
- **computed**: arithmetic from labelled inputs. The formulas are in ARCHITECTURE.md.
- **model-derived**: output of a model, either PVGIS or the hourly energy model in [calc/winter_model.py](calc/winter_model.py). It is only as good as its inputs and is not a measurement.

Project sources:

- `MIKO-DATA.md` and photos from mobric, 25.10.2026, kept outside the repo.
- mobric's answers Q1–Q14 to the F1 questions, relayed by the coordinator on 25.10.2026. They are listed in [ARCHITECTURE.md § 8](ARCHITECTURE.md#8-open-questions-and-answers).
- `firmware/station/station.ino` and `firmware/gateway/gateway.ino` at commit 82ee40d.
- `docs/prd-tech-design.md`.

Datasheet and dataset links are listed in [ARCHITECTURE.md § Sources](ARCHITECTURE.md#sources).

## 1. Current station (as found)

### Hardware

| Item | Fact | Label |
|---|---|---|
| Panel | SunUP SR10-36M, mono, 36 cells, 10 W ±3 %, Vmp 18.7 V, Imp 0.54 A, Voc 22.4 V, Isc 0.59 A. Temperature coefficients unknown | owner/photo (panel label, IMG_2738) |
| Panel mounting | Tilt 45°, probably nothing shading it to the south. Azimuth not yet answered; snow not answered | owner/photo (Q4); azimuth assumed south |
| Battery | 3 × 18650 in parallel (1S3P), 3.7 V nominal, 10 200 mAh, 3.0–4.2 V. Cell model unknown | owner/photo (MIKO-DATA, confirmed in Q1) |
| Protection | External "BMS 1S 10A" board at the cells: two ST 95N3LLH6 MOSFETs and an unidentified protection IC. Cells on B+/B−; charger and load share P+/C−. It stays (Q2) | owner/photo (listing screenshot, bms.png) |
| Charger | Generic CN3791 MPPT module, pad set to "12V", feeding the protection board. A TP4056 module also feeds the protection board; its source is unknown. mobric wants USB charging on the new board (Q3) | owner/photo (MIKO-DATA, Q3) |
| Load path | Protection board → INA219 (DFRobot SEN0291, 0x45, VIN+ at the battery, VIN− at the load) → 5 V step-up → DevKit VIN. The DevKit's AMS1117 makes 3.3 V for BME680 and INA219; the DevKit 5V pin feeds PMS7003 and the Grove LoRa module | owner/photo (MIKO-DATA) and the station.ino header |
| Cables | Two-wire runs to the anemometer and the panel, each < 1 m. A Cat5e run to the BME680, < 1 m, soldered at both ends; breakout model unknown | owner/photo (MIKO-DATA, Q6) |
| Enclosure | A clear box. mobric wants a new, better enclosure (Q8) | owner/photo |
| Gateway distance | About 20 m | owner/photo |
| Location | 50.90 N, 15.73 E (Jelenia Góra valley), the forecast point in `frontend/lib/tools/forecast.ts` | assumed: the station sits at the forecast point |

### Problems found while reading the sources

These are the reasons for the new board. None of them has been measured on the station.

1. **High sleep current, estimated at 22–46 mA from the battery.** The firmware assumes 10 µA (`DEEP_SLEEP_CURRENT_MA 0.01`). Contributors:
   - The DevKit itself sleeps at 3.8–12.2 mA when fed at 5 V (measured, two third-party boards). Its AMS1117 alone has 5 mA quiescent current (datasheet).
   - The Grove LoRa module draws 8.4 mA in standby (datasheet, Seeed).
   - The firmware never calls `rf95.sleep()`, so after every listen window the radio stays in receive mode through deep sleep (datasheet: RadioHead source, where `available()` switches to RX).
   - The INA219 draws 0.7 mA and is never powered down (datasheet).
   - The PMS7003 draws ≤ 200 µA in standby (datasheet).
   - The step-up module idles at about 1–1.5 mA (assumed; an informal figure with no traceable source).

   The total is computed. At that rate the sleep current alone uses 0.53–1.10 Ah/day, and a full pack lasts about 6–12 days without sun.
2. **About 30 % of panel power is wasted by the MPPT setting.** The module's "12V" pad most likely holds the panel near 11.9 V (computed, from a third-party teardown of the divider values), against a Vmp of 18.7 V. A 36-cell panel at 12 V delivers about 7 W instead of 10 W (assumed I-V curve shape).
3. **No cold-charge protection.** The CN3791 has no temperature (NTC) input (datasheet), and 18650 cells must not be charged below 0 °C (datasheet: Panasonic NCR18650B, LG MJ1). In December about 37 % of the PV energy at this site arrives while the air is below 0 °C (model-derived: PVGIS SARAH3/ERA5 2005–2023, 45° south).
4. **Reported battery current is probably 10× too low.**
   - The firmware calls `ina219.begin()` without calibration. Adafruit_INA219 then assumes a 0.1 Ω shunt.
   - The DFRobot SEN0291 board has a 10 mΩ shunt (datasheet).
   - Reported current is therefore 1/10 of the real value (computed). Needs a bench check.
   - The current is used only for local estimates; it isn't sent in the packet.
5. **The cycle is about 19.4 min, not 15 min** (nominal, computed from the source code). The firmware sleeps a fixed 60 s after every wake. One cycle is 16 sleeps, 15 listen wakes of about 9.4 s and one full read of about 65 s. PMS retries alone let a read vary by 30.6–35.1 s.
6. **The radio transmits at about 10 dBm, not 13 dBm.** The Seeed fork maps `setTxPower(13, false)` to register value 0x88, which is 10 dBm. RadioHead 1.147 maps the same call to 13 dBm (datasheet: both library sources and the SX1276 register table).

## 2. Requirements

Each requirement has an ID. "Verify" says how F2–F6 check it. Requirements changed in this revision are marked *(rev 1)*.

### Function and interfaces

| ID | Requirement | Verify |
|---|---|---|
| R-F1 | Keep all current measurements: BME680 (T, RH, p, gas), PMS7003 (PM1, PM2.5, PM10), wind speed (reed anemometer FG-000WIND-004, 2.4 km/h per Hz), battery voltage and current (INA219 at 0x45) | F2 netlist review |
| R-F2 | *(rev 1)* BME680 stays off-board in a radiation shield on the existing < 1 m Cat5e cable, on its own I²C bus (GPIO32/33). The board feeds it from a **switched 3.3 V supply that is off in deep sleep**, so the unknown breakout (regulator, LED) can't load the battery. SDA/SCL get ESD protection at the connector; nothing drives or pulls the bus high while the supply is off | F2 review, F6 measure |
| R-F3 | PMS7003 runs from a 5 V rail (4.5–5.5 V, datasheet) that the firmware switches off completely between readings. The rail must truly disconnect: no path from the battery through the boost | F2 review, F6 measure |
| R-F4 | An unpowered PMS7003 must not be back-powered through its UART or SET lines. Use series resistors on the board, and park TX and SET low with pulls off before the 5 V rail goes off | F6 measure |
| R-F5 | *(rev 1)* Anemometer input with debounce filter and ESD protection; keep GPIO4. In deep sleep no pull-up current may flow, even if the reed switch rests closed | F2 review, F6 measure |
| R-F6 | *(rev 1)* Reserve an ADC1 input with connector for a future wind vane (PRD), with its divider supply switched off in sleep. Add an optional 1-Wire header (DS18B20) with ESD protection | F2 review |
| R-F7 | *(rev 1)* Radio: an SX1276 868 MHz module on SPI, interoperating with the unchanged gateway at 868.0 MHz with RadioHead defaults (BW125, CR4/5, SF7, CRC on, sync word 0x12, 4-byte RadioHead header, broadcast address) and the same 24-byte packet. Firmware sets every air setting explicitly instead of relying on reset defaults. No SPI or blocking RTOS call may run in interrupt context | F5 code review, F6 bench test against the gateway and a deep-sleep soak test |
| R-F8 | External 868 MHz antenna (confirmed, Q11): u.FL on the board, pigtail to an SMA bulkhead on the enclosure, 50 Ω line derived from the real stackup, matching-network footprint, low-capacitance ESD diode | F3 layout review, F6 RSSI test |
| R-F9 | *(rev 1)* USB-C on the board (confirmed, Q14) for programming, logs and charging. It acts as a sink with 5.1 kΩ on CC1 and CC2, plus ESD protection. The USB-UART bridge and every signal it touches are powered from VBUS only. **With USB unplugged the bridge draws no battery current and nothing back-feeds through its UART or auto-reset lines.** Verify in four states: USB absent, attached, suspended, battery absent | F2 review, F6 measure |
| R-F10 | *(rev 1)* Readable charger status on input-only GPIOs, with pull-ups to 3V3 | F2 review |
| R-F11 | *(new)* Wi-Fi only for occasional OTA updates (Q10): keep the ESP32 antenna keep-out clear of cells, metal and cables, and use a flash partition layout with two OTA app slots on the 4 MB flash | F3 layout review, F5 build |

### Power

| ID | Requirement | Verify |
|---|---|---|
| R-P1 | *(rev 1)* Panel input survives a reverse connection and any panel voltage up to the worst-case open-circuit voltage, about 28 V (computed from assumed inputs: Voc 22.4 V +5 % tolerance, −0.35 %/K, panel at −30 °C). **The voltage at the charger IC stays inside its operating range for every panel tolerance and temperature**, including near-Voc operation when the charger is current-limited or done. Any clamp, limiter or OVP is specified with bounded dissipation. A TVS must stay non-conducting at cold Voc. MOSFET gates are protected. No battery current flows back into the panel at night | F2 calculation and review, F6 measure on a cold morning |
| R-P2 | *(rev 1)* MPPT charging from the panel, with the operating point set for Vmp 18.7 V. F2 computes the toleranced range for the chosen charger. For the CN3791 alternative it is 17.9–19.5 V (computed: 1.18–1.23 V reference, ±100 nA bias, 1 % resistors) | F2 calculation, F6 measure |
| R-P3 | *(rev 1)* Charge current about 1.5 A from the panel. F2 computes the toleranced range from the chosen charger's sense threshold. For the CN3791 alternative it is 1.33–1.60 A (computed: 110–130 mV over 0.082 Ω ±1 %). Charge voltage 4.2 V within ±1 %, including the divider if the charger is adjustable | F2 calculation |
| R-P4 | *(rev 1)* **No charging, from the panel or USB, while the cells are below 0 °C or above 45 °C.** This is enforced in hardware, independent of firmware, and **guaranteed including the tolerances** of the NTC, resistors, reference, comparator offset and the NTC-to-cell gradient. The interlock is **off by default**: it allows charging only while it is powered, past start-up, and the NTC reads inside the window. An open or shorted NTC, a brown-out or a slow dawn ramp blocks charging. Hysteresis prevents chatter. **Total trip error ≤ 1 K**, so the nominal trips sit near +1 °C and +44 °C (each extra kelvin costs winter energy, ARCHITECTURE.md § 4.5) | F2 tolerance calculation; F6 test with resistor substitutes (0 °C, 45 °C, open, short), cold spray and a slow supply ramp |
| R-P5 | *(rev 1)* Battery input 3.0–4.2 V from the protection board's P+/C−. Polarised connector, reverse-polarity protection, and a fuse coordinated with the shunt's pulse rating and the connector current rating | F2 review |
| R-P6 | *(rev 1)* 3.3 V rail held at 3.3 V across the whole battery range, with ≥ 500 mA available while the converter input is below 3.0 V after shunt, fuse and FET losses at the 3.0 V pack endpoint. ESP32 requires 3.0–3.6 V and a ≥ 0.5 A supply (datasheet); Wi-Fi peaks reach 379 mA | F2 review, F6 measure |
| R-P7 | *(rev 1)* **Sleep current from the battery ≤ 100 µA** for the whole board in deep sleep with radio and sensors asleep, as a bounded figure (datasheet maxima where published). The inventory in ARCHITECTURE.md § 4.2 gives 52.5 µA typical and 95.8 µA bounded for the board at the battery link (computed). The external protection board adds 3–6 µA upstream of the link. Both figures stay conditional until measured | F6 measure with a µA meter at the battery link |
| R-P8 | A removable link in the battery path, so sleep current can be measured with a meter in series | F3 layout review |
| R-P9 | *(rev 1)* INA219 at 0x45 measures the **net battery current, signed**, with a 0.1 Ω shunt between the battery connector and the node where charger and loads meet. The default library calibration fits. Firmware reports **battery voltage = bus voltage + shunt voltage**, because the bus input sits on the load side. The shunt is Kelvin-routed and rated for 0.21 W continuous plus fault pulses. Power-down in sleep is mandatory | F2 review, F6 compare with a meter while charging and loaded |
| R-P10 | *(rev 1)* **Winter energy.** In the chronological hourly model (PVGIS 2005–2023, 45°, cold gating at the guaranteed interlock trip, carry-over between days and years), the chosen D13 option must give no brown-out in any of the 18 winters 2005/06–2022/23. Otherwise mobric explicitly accepts the brown-out risk quantified for that option | F1 review of [ARCHITECTURE.md § 4](ARCHITECTURE.md#4-power-budget); F6/F7 field data |
| R-P11 | *(new)* USB charging from VBUS (Q3) at ≤ 500 mA, gated by the same temperature interlock as the panel (R-P4) even when there's no panel power. No current flows back into VBUS or the panel input | F2 review, F6 test |

### Environment

| ID | Requirement | Verify |
|---|---|---|
| R-E1 | Operating range inside the enclosure −20 to +50 °C (assumed). PVGIS ERA5 gives a December absolute minimum of −20.2 °C and a typical coldest hour of −10.6 °C (model-derived). Prefer parts rated −40 °C; list every part rated only to −20 °C. The panel itself can reach −30 °C (R-P1) | F2 BOM review |
| R-E2 | Known limits: PMS7003 operates only from −10 °C (datasheet), so the firmware skips PM readings below −10 °C (confirmed, Q12). RFM95W is rated only −20 to +70 °C (datasheet, V1.0), so Ra-01H (−40 °C) is preferred | F5 firmware |
| R-E3 | *(rev 1)* ESD or TVS protection on every line that leaves the enclosure or the board edge: panel, battery, anemometer, BME680 cable, wind vane, 1-Wire, USB, antenna, NTC | F2 review |
| R-E4 | Condensation in the outdoor box: no exposed unprotected high-impedance nodes. Conformal coating is still mobric's call (Q13; the coordinator has explained it and waits for a yes or no) | F3 review |

### Compatibility and firmware

| ID | Requirement | Verify |
|---|---|---|
| R-C1 | Keep current GPIOs where possible. Every change is listed with its firmware impact in [ARCHITECTURE.md § Pin table](ARCHITECTURE.md#3-pin-table) | F1 and F2 review |
| R-C2 | Radio output ≤ 25 mW ERP (14 dBm) in 868.0–868.6 MHz with ≤ 1 % duty cycle (datasheet: ERC/REC 70-03, EN 300 220). *(rev 1)* Firmware keeps today's 10 dBm conducted on PA_BOOST (OutputPower 8). Today's Seeed fork writes PA_CONFIG 0x88; RadioLib's `setOutputPower(10)` writes 0xF8, which selects the same 10 dBm (datasheet: SX1276 RegPaConfig). The 868.0 MHz band-edge question stays open (ARCHITECTURE.md § 7) | F6 measure |
| R-C3 | Firmware is only compiled (`just esp cook station`), never flashed without mobric, per the PKM lock 2026-09-04-T0001 | process |
| R-C4 | The same module family as today: ESP32 (D0WD-V3 class) with 4 MB flash, so the Arduino core and sketch settings stay the same apart from the OTA partition layout (R-F11) | F2 review |
| R-C5 | *(new)* The packet format stays the same. The meaning of the battery voltage field stays "voltage at the protection board output", now computed as bus + shunt voltage (R-P9) | F5 code review |

### Manufacturing and service

| ID | Requirement | Verify |
|---|---|---|
| R-M1 | *(rev 1)* JLCPCB, 2 layers, 1.6 mm FR-4, SMD assembly. Every part has an exact manufacturer part number, an LCSC number, and stock and price with the date seen | F2 BOM |
| R-M2 | Board outline is a parameter, because the enclosure will be new (Q8, D11): outline, mounting holes and connector edge come from a few values in one place | F3 |
| R-M3 | *(rev 1)* Field cables (panel, anemometer, BME680 Cat5e, wind vane) land on **pluggable screw terminal blocks**. Internal leads (battery, NTC, PMS7003) use **locking polarised JST** connectors. Every connector gets a silkscreen label and polarity mark (D14) | F3 review |
| R-M4 | *(rev 1)* Test points on every rail (VBAT, VPANEL, VBUS, 3V3, 5V_PMS) and on ground, both shunt sides, the interlock output, EN/BOOT, UART0, I²C0, I²C1 and the radio SPI/DIO lines | F3 review |
| R-M5 | *(rev 1)* M3 mounting holes. The drill (plated or NPTH) and the copper keep-out around screws and standoffs are specified in F3 | F3 review |
| R-M6 | *(new)* The F2/F3 checklist in [ARCHITECTURE.md § 10](ARCHITECTURE.md#10-f2f3-checklist) is closed item by item before each gate | F2 and F3 gates |

### Out of scope for v1

- BLE, and Wi-Fi beyond occasional OTA sessions (R-F11).
- Changes to the gateway hardware or firmware.
- A custom BME680 sensor board. The existing breakout and cable stay.
- On-board cell protection. The external board stays (Q2, D5.2).
- A graphical schematic. atopile code is the schematic.

## 3. Energy summary

Full details, inputs and sources are in [ARCHITECTURE.md § Power budget](ARCHITECTURE.md#4-power-budget). The hourly model is [calc/winter_model.py](calc/winter_model.py).

| Case | Result |
|---|---|
| Deep sleep, whole board, from the battery | 52.5 µA typical, 95.8 µA bounded; 55.5 / 101.8 µA including the external protection board (computed, not measured) |
| Daily use, required firmware changes only (M1), 1-min listen and 15-min full read | 1.40 Wh nominal, 2.04 Wh pessimistic (computed) |
| Daily use with the optional firmware changes (M2) | 0.70 Wh nominal, 0.87 Wh pessimistic (computed) |
| December mean harvest into the battery, 45° south, charging only between 0 and 45 °C air temperature | 8.0 Wh/day (model-derived) |
| Worst December 14-day mean harvest, same conditions | 0.13 Wh/day, 1–14 Dec 2012 (model-derived) |
| Brown-outs in 18 winters with today's 10 W panel and 10.2 Ah pack, interlock cutoff +1 °C | M1: 6 winters, 90 days in total, longest 27 days. M2: 1 winter, 2 days. M2 with an adaptive schedule: none (model-derived) |

**Verdict: 10 W and 10.2 Ah are enough only under conditions.** This replaces the draft's unconditional "enough". The hourly model shows that the cold-charge block, not the panel, limits the winter. In cold spells it stops charging for weeks while the sun shines, so a bigger panel or a steeper tilt barely helps. In the model the station survives all 18 winters only with one of these:
- M2 firmware plus an adaptive schedule that slows reporting as the battery drains;
- a bigger pack (≥ 24.7 Ah for M1 at a +1 °C cutoff);
- a warmer pack: a heater, or box warming that is shown by measurement.

mobric chooses among these in D13 ([ARCHITECTURE.md § 5](ARCHITECTURE.md#5-decisions)). Snow and site shading remain unmodelled.

## 4. Open questions for mobric

See [ARCHITECTURE.md § 8](ARCHITECTURE.md#8-open-questions-and-answers); the list is kept in one place.
