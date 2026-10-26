# Station PCB requirements

Status: **F1 revision 2 for review**, 26.10.2026, written by `mobric/pcb-opus-5-5` (listed as `mobric/mikolaj-claude-60` since a restart).
- It revises revision 1 (a22e006) after the Codex re-review in [reviews/F1-codex-r2.md](reviews/F1-codex-r2.md). The item-by-item response is in [reviews/F1-response-r2.md](reviews/F1-response-r2.md). The response to the first review is [reviews/F1-response.md](reviews/F1-response.md).
- It folds in mobric's answers to questions 15–21 and the D5 approval (LT3652), relayed by the coordinator on 25.10.2026.
- Nothing else here is approved until mobric signs off the decisions in [ARCHITECTURE.md](ARCHITECTURE.md).

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
- **computed**: arithmetic from labelled inputs. The formulas are in ARCHITECTURE.md and in [calc/interlock_trips.py](calc/interlock_trips.py).
- **model-derived**: output of a model, either PVGIS or the hourly energy model in [calc/winter_model.py](calc/winter_model.py). It is only as good as its inputs and is not a measurement.

Project sources:

- `MIKO-DATA.md` and photos from mobric, 25.10.2026, kept outside the repo.
- mobric's answers to the F1 questions (Q1–Q14, then 15–21) and the D5 approval, relayed by the coordinator on 25.10.2026. They are listed in [ARCHITECTURE.md § 8](ARCHITECTURE.md#8-open-questions-and-answers).
- `firmware/station/station.ino` and `firmware/gateway/gateway.ino` at commit 82ee40d.
- `docs/prd-tech-design.md`.

Datasheet and dataset links are listed in [ARCHITECTURE.md § Sources](ARCHITECTURE.md#sources).

## 1. Current station (as found)

### Hardware

| Item | Fact | Label |
|---|---|---|
| Panel | SunUP SR10-36M, mono, 36 cells, 10 W ±3 %, Vmp 18.7 V, Imp 0.54 A, Voc 22.4 V, Isc 0.59 A. Temperature coefficients unknown | owner/photo (panel label, IMG_2738) |
| Panel mounting | Tilt 45°, azimuth about 233° (south-west), probably nothing shading it to the south. Snow not answered | owner/photo (Q4, answer 15) |
| Battery | 3 × Samsung 18650 in parallel (1S3P), 3.4 Ah each, 3.7 V nominal, 10 200 mAh, 3.0–4.2 V. Cell model unknown | owner/photo (MIKO-DATA, confirmed in Q1 and answer 19) |
| Protection | External "BMS 1S 10A" board at the cells: two ST 95N3LLH6 MOSFETs and an unmarked protection IC. Cells on B+/B−; charger and load share P+/C−. It stays, but the new board doesn't rely on it (answer 20) | owner/photo (listing screenshot, bms.png; answer 20) |
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

Each requirement has an ID. "Verify" says how F2–F6 check it. Requirements changed in revision 2 are marked *(rev 2)*; *(rev 1)* marks the changes made in revision 1.

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
| R-F10 | *(rev 2)* The firmware infers the charge state from the sign of the INA219's battery current (R-P9). The solar charger's status pins go to test points only. No status pin may be pulled up to a rail that stays powered while the charger's input is not (the LT3652's CHRG and FAULT are rated VIN + 0.5 V) | F2 review |
| R-F11 | *(new)* Wi-Fi only for occasional OTA updates (Q10): keep the ESP32 antenna keep-out clear of cells, metal and cables, and use a flash partition layout with two OTA app slots on the 4 MB flash | F3 layout review, F5 build |

### Power

| ID | Requirement | Verify |
|---|---|---|
| R-P1 | *(rev 2)* Panel input survives a reverse connection and any panel voltage up to the worst-case open-circuit voltage, about 28 V (computed from assumed inputs: Voc 22.4 V +5 % tolerance, −0.35 %/K, panel at −30 °C). **The charger's VIN stays inside its operating range (≤ 32 V for the LT3652) for every panel tolerance and temperature**, including near-Voc operation when the charger is current-limited or done. **Defined surge:** any pulse the panel TVS clamps within its rating (600 W at 10/1000 µs, ≤ 11.3 A; assumed definition). During it the protection switch's input stays ≤ 55 V (rated 62 V) and the charger's VIN ≤ 36 V (rated 40 V absolute), both computed. The TVS stays non-conducting at cold Voc, and a sustained overvoltage opens the fuse. No battery current flows back into the panel at night | F2 calculation and review; F6 cold-morning Voc, threshold checks and a fast-step overshoot test |
| R-P2 | *(rev 2)* MPPT charging from the panel, with the operating point set for Vmp 18.7 V: the LT3652's VIN_REG with 0.1 % resistors gives 18.3–19.1 V (computed from its 2.65–2.75 V threshold) | F2 calculation, F6 measure |
| R-P3 | *(rev 2)* Charge current about 1.5 A from the panel: 1.38–1.56 A with RSENSE 68 mΩ ±1 % (computed from 95–105 mV). Charge voltage 4.2 V within ±1 % at 25 °C: 4.17–4.23 V with a 0.1 % divider, and 4.15–4.25 V over the chip's temperature range (computed). Termination at C/10, 110–184 mA (computed) | F2 calculation, F6 measure |
| R-P4 | *(rev 2)* **No charging, from the panel or USB, while the cells are below 0 °C or above 45 °C, or above the overvoltage trip.** This is enforced in hardware, independent of firmware.<br>**Guaranteed at the safety corner:** the worst electrical corner (NTC, resistors, comparator offset and hysteresis, supply), plus the NTC's self-heating and the NTC-to-cell gradient, keeps the cold trip ≥ 0 °C and the hot trip ≤ 45 °C.<br>**Off by default:** charging only while the interlock is powered, past its power-on reset, with the NTC reading inside the window and the cells below the overvoltage trip. An unpowered interlock, a brown-out, a slow ramp, or an open or shorted NTC blocks charging, shown state by state (ARCHITECTURE.md D5).<br>**Energy:** the warmest cold "on" trip (energy corner) stays ≤ +3.1 °C, and the hysteresis is no larger than chatter needs.<br>**Battery overvoltage:** both chargers stop above a trip between the highest float and 4.45 V.<br>Single-fault tolerance isn't required | F2 tolerance calculation ([calc/interlock_trips.py](calc/interlock_trips.py) with the chosen parts); F6 test with resistor substitutes (each trip ±0.5 K, open, short), cold spray, slow ramps of the panel (to 30 V) and VBUS (to 5.5 V), brown-outs, and a battery-voltage sweep |
| R-P5 | *(rev 2)* Battery input 3.0–4.2 V from the pack, through the existing protection board's P+/C−. Polarised connector, reverse-polarity protection, a board fuse coordinated with the shunt's pulse rating and the connector current rating, and an inline fuse at the pack for the cable.<br>**The board's own protection is self-sufficient** (answer 20); the pack's board isn't relied on:<br>- overcharge: each charger's float, plus the interlock's overvoltage trip (R-P4);<br>- temperature: R-P4;<br>- overdischarge: the firmware's hibernation, plus a hardware UVLO that holds the 3.3 V converter off below 3.1 V;<br>- short circuit: the two fuses;<br>- reverse polarity | F2 review, F6 test |
| R-P6 | *(rev 2)* 3.3 V rail held at 3.3 V across the battery range above the UVLO (off below 3.1 V, on again at about 3.3 V), with ≥ 500 mA available while the converter input is below 3.0 V after shunt, fuse and FET losses at the 3.0 V pack endpoint. ESP32 requires 3.0–3.6 V and a ≥ 0.5 A supply (datasheet); Wi-Fi peaks reach 379 mA | F2 review, F6 measure |
| R-P7 | *(rev 2)* **Sleep current**, measured at the battery link for the whole board in deep sleep, with radio and sensors asleep, USB unplugged and the panel dark: **≤ 100 µA at 3.7 V and 25 °C, and ≤ 150 µA at 3.0 V and +50 °C** (proposed, Q22). The inventory in ARCHITECTURE.md § 4.2 estimates 52.8 µA typical and 97.4 µA high-side at 3.7 V, and 73.0 / 132.7 µA at 3.0 V (computed). The high-side figures are estimates, not bounds: several parts publish no maximum. The external protection board adds 3–6 µA upstream of the link | F6 measure with a µA meter at the battery link, at 3.0, 3.7 and 4.2 V |
| R-P8 | A removable link in the battery path, so sleep current can be measured with a meter in series | F3 layout review |
| R-P9 | *(rev 2)* INA219 at 0x45 measures the **net battery current, signed**, with a 0.1 Ω shunt between the battery connector and the node where charger and loads meet. The default library calibration fits. Firmware reports **battery voltage = bus voltage + shunt voltage**, because the bus input sits on the load side. The sign also shows whether the battery is charging (R-F10). The shunt is Kelvin-routed and rated for 0.24 W continuous plus fault pulses. Power-down in sleep is mandatory | F2 review, F6 compare with a meter while charging and loaded |
| R-P10 | *(rev 2)* **Winter energy.** The hourly model runs chronologically over PVGIS 2005–2023 at 45° and azimuth 233°, carrying the charge over between days and years. Its conditions are:<br>- the interlock at its **energy corner**, **reset every night** (it restarts off);<br>- pessimistic loads;<br>- the firmware's charge estimate **off by up to 15 %** in either direction.<br>Under those conditions the chosen D13 option gives no outage hour in any of the 18 winters 2005/06–2022/23, and recovers by itself after any low-energy event. Otherwise mobric explicitly accepts the outage risk quantified for that option | F1 review of [ARCHITECTURE.md § 4](ARCHITECTURE.md#4-power-budget); F6/F7 field data |
| R-P11 | *(rev 2)* USB charging from VBUS (Q3) at ≤ 444 mA including the charger's ±10 % gain tolerance, with total VBUS current ≤ 461 mA. It is gated by the same interlock as the panel (R-P4), even when there's no panel power. Supported sources are USB ports, and USB-C sources at default power, within the USB voltage limits. VBUS above 5.5 V isn't supported, because the bridge's VDD5 is rated 6 V absolute. No current flows back into VBUS or the panel input | F2 review, F6 test (VBUS up to 5.5 V only) |

### Environment

| ID | Requirement | Verify |
|---|---|---|
| R-E1 | Operating range inside the enclosure −20 to +50 °C (assumed). PVGIS ERA5 gives a December absolute minimum of −20.2 °C and a typical coldest hour of −10.6 °C (model-derived). Prefer parts rated −40 °C; list every part rated only to −20 °C. The panel itself can reach −30 °C (R-P1) | F2 BOM review |
| R-E2 | Known limits: PMS7003 operates only from −10 °C (datasheet), so the firmware skips PM readings below −10 °C (confirmed, Q12). RFM95W is rated only −20 to +70 °C (datasheet, V1.0), so Ra-01H (−40 °C) is preferred | F5 firmware |
| R-E3 | *(rev 1)* ESD or TVS protection on every line that leaves the enclosure or the board edge: panel, battery, anemometer, BME680 cable, wind vane, 1-Wire, USB, antenna, NTC | F2 review |
| R-E4 | *(rev 2)* Condensation in the outdoor box: conformal coating, yes (answer 21), with keep-outs for connectors, test points, the u.FL and the USB-C receptacle. No exposed unprotected high-impedance nodes | F3 review |

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
| R-M4 | *(rev 2)* Test points on every rail (VBAT, VPANEL, VBUS, 3V3, 5V_PMS, VREG) and on ground, both shunt sides, the interlock outputs (OUT1–OUT3, SHDN, the ISET chain), the LT3652's CHRG and FAULT, EN/BOOT, UART0, I²C0, I²C1 and the radio SPI/DIO lines | F3 review |
| R-M5 | *(rev 1)* M3 mounting holes. The drill (plated or NPTH) and the copper keep-out around screws and standoffs are specified in F3 | F3 review |
| R-M6 | *(new)* The F2/F3 checklist in [ARCHITECTURE.md § 10](ARCHITECTURE.md#10-f2f3-checklist) is closed item by item before each gate | F2 and F3 gates |

### Out of scope for v1

- BLE, and Wi-Fi beyond occasional OTA sessions (R-F11).
- Changes to the gateway hardware or firmware.
- A custom BME680 sensor board. The existing breakout and cable stay.
- *(rev 2)* Cell balancing and a redundant second protection IC. The board's own protection is self-sufficient (R-P5, D5.2). The pack's existing 1S board stays but isn't relied on (answer 20).
- *(rev 2)* A direct lightning strike on the mast; R-P1 covers the defined surge only.
- *(rev 2)* USB sources above 5.5 V (R-P11).
- A graphical schematic. atopile code is the schematic.

## 3. Energy summary

Full details, inputs and sources are in [ARCHITECTURE.md § Power budget](ARCHITECTURE.md#4-power-budget). The hourly model is [calc/winter_model.py](calc/winter_model.py). Every figure below is computed or model-derived, not measured.

| Case | Result |
|---|---|
| Deep sleep, whole board at the battery link | 52.8 µA typical and 97.4 µA high-side estimate at 3.7 V; 73.0 / 132.7 µA at 3.0 V. With the external protection board: 55.8 / 103.4 µA and 76.0 / 138.7 µA (computed) |
| Daily use, required firmware changes only (M1), 1-min listen and 15-min full read | 368 mAh = 1.36 Wh nominal, 552 mAh = 2.04 Wh pessimistic (computed) |
| Daily use with the optional firmware changes (M2) | 170 mAh = 0.63 Wh nominal, 235 mAh = 0.87 Wh pessimistic (computed) |
| December mean harvest into the battery, 45°, azimuth 233° | 9.18 Wh/day without a temperature limit; 4.31 Wh/day at the interlock's nominal trips, 3.41 Wh/day at its energy corner (model-derived) |
| Longest stretch without any charging | 55.0 days from 25 Dec 2009 at the nominal trips, 59.8 days at the energy corner (model-derived) |
| Outages in 18 winters with today's 10 W panel and 10.2 Ah pack, energy corner | M1 nominal: 14 winters, 314 days, longest 72 days. M2 nominal: 2 winters, 57 days. M2 adaptive (D13 a1) with pessimistic loads and the estimate off by up to 15 %: none, lowest charge 13 % (model-derived) |
| D13 recommendation: (a2) with 8 cells, 27.2 Ah | No outage hour in any winter, with pessimistic loads, the estimate off by up to 15 % and 20 % fade. 2–15 lean days and under 2 survival days a winter, and every gateway request heard (model-derived) |

**Verdict: the winter needs both the firmware savings and margin.** Revision 1's claim that M2 with an adaptive schedule "survives every case" is withdrawn as worded (R2-M1).
- **Today's 10 W panel and 10.2 Ah pack** survive every modelled winter only with M2 and the adaptive schedule. That holds with the interlock's tolerances, the nightly reset and a 15 % estimate error included.
- **The cost is 9–30 lean and 2–8 survival days a winter.** In those modes the station hears only part of the gateway's requests.
- **mobric prefers the firmware combined with a bigger pack** (answer 17). With 8 cells and 2-min listens, every request is heard and every modelled case survives.
- **The cold-charge block, not the panel, limits the winter.** A bigger panel or a steeper tilt barely helps.

mobric chooses in D13 ([ARCHITECTURE.md § 5](ARCHITECTURE.md#5-decisions)). Snow and site shading remain unmodelled.

## 4. Open questions for mobric

See [ARCHITECTURE.md § 8](ARCHITECTURE.md#8-open-questions-and-answers); the list is kept in one place.
