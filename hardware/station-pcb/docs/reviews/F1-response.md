# F1 review response

This is the response by `mobric/pcb-opus-5-5` to [F1-codex.md](F1-codex.md), the Codex review of the F1 draft at 4cd5e93. It was written on 25.10.2026 and committed together with F1 revision 1 of [REQUIREMENTS.md](../REQUIREMENTS.md) and [ARCHITECTURE.md](../ARCHITECTURE.md).

**Result: 12 fixed, 4 accepted, none disputed.**
- **Fixed:** the revised documents now do what the review asked, or something that meets the same aim. Each row says which.
- **Accepted:** a note, a passed check or a side remark. Its follow-through is now in the documents.
- **Disputed:** none.

In the "Where" column, § and D numbers refer to ARCHITECTURE.md and R- numbers to REQUIREMENTS.md, both as revised.

## Summary

| Item | Disposition | What changed | Where |
|---|---|---|---|
| **B1** The reverse-protection FET is not a charge inhibit | **Fixed** | The interlock now gates documented enable inputs (LT3652 SHDN, BQ25170 ISET) instead of a FET in the panel path. It is off by default, toleranced to ≤ 1 K, and powered from the panel or USB | D5, § 1, § 7 item 1; R-P4, R-P11 |
| **M1** The winter verdict fails the temperature model | **Fixed** | New hourly chronological model at 45° over all 18 winters. It reproduces the review's figures exactly. The verdict is now conditional, and mobric chooses among real options in D13 | § 4.4, § 4.5, D13; R-P10, REQUIREMENTS § 3; [calc/winter_model.py](../calc/winter_model.py) |
| **M2** The USB bridge sleep claim | **Fixed** | The whole CH343P runs from VBUS, and its ESP32-side lines are isolated without VBUS. F6 tests four USB states | D3, § 4.1, § 4.2, § 7 item 4; R-F9 |
| **M3** 53 µA is not a bounded floor | **Fixed** | Typical and bounded inventories from the candidate BOM. The unknown breakout moves to a switched rail. Converter current is referred to its input and kept out of the efficiency figure. MODE is specified | § 4.1, § 4.2, § 4.6, D6, D8; R-P6, R-P7 |
| **M4** Cold Voc and the input clamp are not bounded | **Fixed** | Worst-case Voc is about 28 V. The recommended charger is rated 40 V and gets a TVS that stays off at cold Voc. The CN3791 alternative needs a true disconnect and a 26.5 V OVP | D5, § 7 item 2, § 10; R-P1, R-P2 |
| **M5** The INA219 relocation changes the voltage meaning | **Fixed** | Battery voltage = bus + shunt voltage, signed net current. The charge-regulation offset and termination under load are documented and tested | D9, § 6 item 2, § 7 item 3, § 10; R-P9, R-C5 |
| **M6** A private SPI bus doesn't make the ISR safe | **Fixed** | The driver changes to RadioLib 7.8.1, whose interrupt only sets a flag. The build configuration is resolved from source | D4, § 6 item 1, § 7 item 5; R-F7 |
| **m1** Cadence and PMS timing are assumptions | **Fixed** | Timing labelled nominal. Ranges and a 5 % margin go into the pessimistic case. The listen slot inside a full read is skipped. Today's cadence is modelled separately | § 4.1, § 4.3, § 4.5, § 6 item 8 |
| **m2** Ra-01H receive current | **Fixed** | The budget uses the Ra-01H's 12.15 mA | § 4.1, § 4.3, D4 |
| **m3** The LDO cost-down is invalid | **Fixed** | Removed | D6 |
| **m4** Implementation checks need to be traceable | **Fixed** | F2/F3 checklist added. 1-Wire ESD, connectors decided, USB-C CC and ESD in the interface, RF width from the real stackup | § 10, D3, D10, D14; R-E3, R-M3 to R-M6 |
| **m5** Provenance labels overstate what is known | **Fixed** | New labels owner/photo and model-derived. Unsourced measurements are relabelled assumed. Tolerance ranges added. Prices carry exact part numbers and the date seen | REQUIREMENTS labels, § 1, R-P2, R-P3; § 4.1, D5, D12 |
| **N1** Pins pass; hold rule corrected | **Accepted** | CHRG pull-up to 3V3, NSS pull-up, hold wording corrected, pin parking before power-off, strap reset states in the checklist | § 3, D7, § 10 |
| **N2** Air settings and TX power pass | **Accepted** | Every air setting is passed explicitly. Hardware confirmation in F6. The band-edge note stays open | D4, § 7 items 5 and 12; R-F7, R-C2 |
| **N3** Converters pass, with conditions | **Accepted** | The conditions become F6 tests. INA219 power-down is now mandatory in D9 too | D6, D7, D9, § 7 item 9 |
| **Budget notes** (after the reconstruction table) | **Accepted** | INA219 power-down no longer relies on the per-boot flag. Requests and failed reads are budgeted. USB-connected operation is covered by the USB tests | D9, § 4.3, § 6 item 2, § 7 item 4 |

## Details

### B1: fixed

- **The finding is confirmed.** The power research re-checked the figure independently: in the Waveshare copy (Figure 3, p.10), M2's body diode conducts from the panel into the charger. The Consonance original has no such figure; its Fig. 3 (p.9) is a snubber.
- **New topology (D5):**
  - The recommended solar charger, the LT3652, has a documented SHDN input with a 1.15–1.25 V threshold. TEMP_OK drives it through a FET-switched divider from VIN, which keeps SHDN ≤ VIN + 0.5 V as the datasheet requires. The divider enables only above about 10 V, so on a slow dawn ramp the interlock, valid from about 4 V, always decides first.
  - The USB charger, a BQ25170, is gated by a 2N7002 in series with its ISET resistor. An open ISET means no charge current (datasheet p.14). Its TS pin gets a fixed 10 kΩ, because an open TS reads as cold.
  - The CN3791 alternative uses back-to-back P-FETs (IRF7342), held off by a 100 kΩ pull-up, with a 12 V gate clamp and a 2N7002 driver.
- **Off by default.** TEMP_OK is window-OK AND supply-good, with a pull-down. The TLV3012 drives its output low while its supply is below the minimum (datasheet § 9.4.5). Every fault blocks charging:
  - interlock unpowered, starting or browning out;
  - an open NTC, which reads too cold;
  - a shorted NTC, which reads too hot.
- **Tolerances.**
  - The window is ratiometric, so supply and reference errors cancel. With 0.1 % resistors the worst-case trip error is about ±0.8 K, computed for a +3 °C design from the Shiheng MF52A tables; F2 recomputes it at +1 °C. With 1 % resistors it would be about ±1.6 K.
  - Because each kelvin costs winter energy (§ 4.5), R-P4 now sets ≤ 1 K total error, nominal trips at +1 / +44 °C and 2–3 K hysteresis. The NTC-to-cell gradient is part of that error.
- **USB without panel power.** A 40 V LDO (TPS7B6933), diode-fed from the panel and from VBUS, powers the interlock whenever a charge source exists.
- **Tests (§ 7 item 1):**
  - resistor substitutes at each trip ±0.5 K, then open and short;
  - cold spray;
  - slow ramps of the panel input and VBUS, 0 → 20 V over minutes;
  - a brown-out of each supply.

### M1: fixed

- **The finding is confirmed**, including the warning about bigger panels.
- **Exact reproduction.** `python3 docs/calc/winter_model.py codex <PVGIS 60° series>` gives the review's figures to the last digit:
  - 8.678 / 0.264 / 1.007 / 0 / 0.123 Wh/day;
  - cumulative deficits of 40.57 / 66.00 Wh.

  The PVGIS file is byte-identical to the review's cache (SHA-256 `66b1548093a9b15f062adb9aed7e78c9c10262daec90899b09f742072edb8b19`). The M2 deficits come out at 16.12 / 19.32 Wh against the review's 16.08 / 19.44, only because the review rounded the loads to 0.67 / 0.81 Wh/day.
- **What the new model does with each suggested element (§ 4.4):**
  - **45° tilt (Q4):** used. The azimuth is assumed south until mobric answers (Q15).
  - **Hourly cold gating:** at the interlock's guaranteed trip, run for 0, +1, +2 and +3 °C.
  - **Charge-current clipping:** 1.46 A × 3.8 V.
  - **Cell data:** still assumed (90 % window, 85 % cold derating, 2 %/month self-discharge), because the cell model is unknown (Q1, Q19).
  - **PM skipping:** below −10 °C air (Q12).
  - **Wi-Fi policy:** 1 mAh/day for occasional OTA sessions (R-F11).
  - **All winters, SOC carried across months and years:** hour by hour from 2005 to 2023, with statistics over the 18 full winters.

  The model works hourly, so it no longer nets energy within a day, which the review noted as optimistic. A brown-out leaves the station off until 5 % has been recovered.
- **The verdict is now conditional** (REQUIREMENTS § 3, R-P10). No brown-out in any of the 18 winters needs one of three things: M2 firmware with an adaptive schedule, a bigger pack, or a warmer pack.
- **Options for mobric (D13, from § 4.5):**

  | Option | Result at a +1 °C cutoff, 18 winters (model-derived) |
  |---|---|
  | (a) M2 firmware plus an adaptive schedule | No brown-out on today's pack. About 2.5 days a winter in lean mode |
  | (b) Bigger pack | 24.7 Ah for M1 nominal, 44.3 Ah for M1 pessimistic |
  | (c) Warmer pack (heater or solar-gain enclosure) | Strongest lever in the illustrative runs, but it needs measured temperatures first (Q16) |
  | (d) Accept brown-outs | M1 nominal: 6 winters, 90 days, longest 27 days |
  | (e) Cells chargeable below 0 °C (e.g. LTO) | No brown-out, but charger, converter and pack all change |
  | (f) Bigger panel or steeper tilt | Doesn't help. A 20 W panel still gives M1 6 winters and 64 days |

  I recommend (a) now. In parallel, measure for (c) and fit a DNP heater footprint.

### M2: fixed

- **The finding is confirmed.** 2 µA is the CH343's suspend current, with a 50 µA maximum, and suspend isn't the same as unplugged.
- **New circuit (D3):**
  - The CH343P takes VDD5 from VBUS and VIO from its own V3 output, the datasheet's all-USB-powered configuration.
  - While VBUS is absent, two SN74LVC1T45 translators isolate TXD and RXD. With either supply at 0 V both ports go high-Z, which also covers the battery-absent case.
  - The auto-reset transistors only leak, because their base-emitter voltage is 0.
  - Series resistors alone weren't enough: the CH343P's pins are rated only to VIO + 0.5 V, and it promises no back-flow only while VIO is powered.
- **Result:** the CH343P itself draws nothing from the battery with USB unplugged. The bounded inventory reserves 8 µA for the translators (datasheet supply and Ioff maxima).
- **R-F9** now states VBUS-only power and no back-feed. It is verified in four states: USB absent, attached, suspended, battery absent (§ 7 item 4).

### M3: fixed

- **The finding is confirmed.**
- **Two inventories (§ 4.2):** 52.5 µA typical and 95.8 µA bounded for the board at the battery link, or 55.5 / 101.8 µA on the cells including the protection board. They go line by line with labels, at 25 °C, and include:
  - the TPS631000 feedback divider and the LT3652 float divider;
  - input leakage of the INA219 and of the LT3652's VIN node;
  - ESD/TVS and board leakage, as an allowance;
  - pull-ups, the interlock and held pins, which are zero by design. § 4.2 lists them with the traps that would break that, such as a resting-closed reed switch or a low NRESET.

  Where leakage rises with temperature, as in the catch Schottky, the inventory says so and F2 picks the part.
- **Lines the draft missed:**
  - the Ra-01H's internal RF switch, 9 / 20 µA;
  - the LT3652's catch Schottky, about 5 µA at 25 °C;
  - an allowance for the LT3652's VIN node at night.
- **The unknown BME680 breakout.** It no longer sits on the battery in sleep: SENSOR_3V3 is switched off by a TPS22917 (D8). The breakout survey shows why: left on, five common breakouts would draw about 1–240 µA, because their regulators sit in dropout at 3.3 V.
- **TPS631000 current is split by pin.**
  - 0.15 µA (6.1 µA maximum) is drawn at VIN, directly from the battery.
  - 8 µA is drawn at VOUT, a 3.3 V load converted like the rest of the rail.
  - The 5.5 µA feedback divider is listed separately.
  - The 85 % sleep-load efficiency covers switching losses only, so nothing is counted twice (§ 4.1).
- **MODE:** tied to GND for automatic power-save operation; the pin must not float.
- **INA219:** power-down is 6 µA typical in the typical inventory and 15 µA maximum in the bounded one.
- **Both figures stay conditional until measured** (R-P7, F6 § 7 item 6).
- **The 3.0 V endpoint note** is adopted in § 4.6 and R-P6.

### M4: fixed

- **The finding is confirmed.**
- **The bound (R-P1).** Voc 22.4 V +5 % tolerance, −0.35 %/K, panel at −30 °C gives about 28 V (computed from assumed inputs). The review's 26.1 V at −30 °C used −0.30 %/K without tolerance.
- **Why the CN3791 doesn't fit.** It is rated 28 V operating and 30 V absolute. A current-limited or finished charger lets the panel float to near Voc, up to about 27.4 V.
- **Why no TVS can protect a 30 V part.** An SMBJ24A breaks down at about 25.3 V at −30 °C, so it conducts at cold Voc; it also clamps at 38.9 V.
- **Recommendation: LT3652** (32 V operating, 40 V absolute):
  - An SMBJ28A still stands off at −30 °C, with breakdown at about 29.5 V, and clamps below 40 V for moderate surges.
  - A 60 V Schottky blocks a reversed panel and night backflow.
- **The CN3791 alternative, if chosen:**
  - back-to-back IRF7342s, opened by an OVP comparator above 26.1–26.9 V;
  - gate clamp 12 V against a ±20 V rating;
  - D1 fitted against the night drain path.

  Below about −15 °C a worst-case panel trips the OVP while charging. That lockout is safe.
- **F2 closure is mandatory:** § 10, Calculations, "panel voltage bound (R-P1)".

### M5: fixed

- **The finding is confirmed.**
- **Sense node (D9):** IN+ at the battery connector, IN− at VBAT, where the chargers and loads meet.
- **Voltage:** battery voltage = bus voltage + signed shunt voltage. That is the protection board's output, which keeps the packet field's meaning (R-C5). The protection FETs' drop, about 15 mV at 1.46 A (assumed), stays outside the measurement.
- **Current:** net battery current, with discharge positive. During charging it is not the load current. The firmware stops clamping negative current.
- **Charge regulation:**
  - The cell sees 4.2 V minus I × 0.1 Ω: 146 mV at 1.46 A, and about 23 mV near termination. Charging therefore ends about 1–2 % short of full.
  - F6 checks CC/CV and termination with a load present (§ 7 item 3).
- **Shunt:** a 2512 rated ≥ 1 W and for pulses, Kelvin-routed, with the battery fuse coordinated to its pulse limit (§ 10).

### M6: fixed

- **The finding is confirmed from source.** On core 3.3.11, RadioHead 1.147 takes two FreeRTOS mutexes per register access from inside its DIO0 interrupt. ESP-IDF 5.5.5 doesn't assert on this: it works while the bus is uncontended and corrupts scheduler state when it isn't.
- **Fix (D4):** RadioLib 7.8.1. Its interrupt only sets a flag, and the loop services the radio. Every air setting is passed explicitly. The F6 soak test stays at ≥ 5000 cycles.
- **Rejected:**
  - RadioHead with DIO0 polled through a subclass: it depends on a protected internal and still takes the mutexes with interrupts masked.
  - `CONFIG_DISABLE_HAL_LOCKS`: it applies to the whole core.
- **Today's firmware isn't affected.** The Seeed fork already services its module from the loop, so moving to RadioHead 1.147 on SPI would have been a regression.

Evidence, in the upstream sources downloaded for this revision. I re-read the lines marked ✓; the rest come from the radio research and I didn't re-read them.

| Claim | Upstream file and lines |
|---|---|
| RadioHead's interrupt handler reads registers over SPI ✓ | RadioHead 1.147 `RH_RF95.cpp:158, 166` |
| Every register access opens an SPI transaction ✓ | `RHSPIDriver.cpp:51, 110–112`; `RHHardwareSPI.cpp:495–498` |
| `SPIClass::beginTransaction` takes a mutex with `portMAX_DELAY` ✓ | arduino-esp32 3.3.11 `libraries/SPI/src/SPI.cpp:28–31, 199–200` |
| `spiTransaction` also takes the bus mutex ✓ | `cores/esp32/esp32-hal-spi.c:188–190, 1277` |
| HAL locks are compiled into the prebuilt core ✓ | esp32 libs 3.3.11 `sdkconfig:467`: `# CONFIG_DISABLE_HAL_LOCKS is not set` |
| Semaphore take has no interrupt-context assert ✓ | ESP-IDF v5.5.5 FreeRTOS `queue.c:1697–1718` |
| RadioLib attaches the user's function as a plain interrupt, with no library code in it | RadioLib 7.8.1 `SX127x.cpp:387–389, 409–411`; `hal/Arduino/ArduinoHal.cpp:45–49` |
| RadioLib's defaults differ (434 MHz, SF9, CR 4/7), so every value is passed ✓ | `SX1276.h:52` |
| RadioLib sets a 60 mA current limit by default ✓ | `SX127x.cpp:57` |
| `setOutputPower(10)` on PA_BOOST writes 0xF8 ✓ | `SX1278.cpp:375–379`; `SX1278.h:35` |
| Today's fork services the radio from the loop | Seeed fork f82d4dc `RH_RF95.cpp:127–134` |

### Minor items: fixed

- **m1.**
  - § 4.1 labels the timing nominal. PMS time is 31.6 s nominal and 35.1 s in the pessimistic case (from the retry range 30.6–35.1 s).
  - Failed reads and on-demand requests add 5 % in the pessimistic cases.
  - F5 skips the listen slot that falls inside a 65 s full read (§ 6 item 8).
  - "M1, today's 19.4-min cycle" is modelled separately from the scheduled M1 (§ 4.5).
- **m2.** Ra-01H receive at 12.15 mA (datasheet p.5) in every case, +5.5 mAh/day.
- **m3.** The LDO option is removed from D6.
- **m4.**
  - § 10 is the F2/F3 checklist, item by item: ports, board, calculations, BOM. R-M6 makes it a gate.
  - D10 adds 1-Wire ESD, and D14 decides the connectors.
  - D3 adds the USB-C CC resistors and ESD, and R-M4 extends the test points.
  - The RF width comes from the JLC stackup and is never copied from the draft.
- **m5.**
  - REQUIREMENTS defines **owner/photo** and **model-derived**.
  - MIKO-DATA facts are relabelled owner/photo. The PMS current is relabelled assumed. PVGIS extremes are model-derived.
  - R-P2 and R-P3 carry tolerance ranges: 17.9–19.5 V and 1.33–1.60 A for the CN3791 alternative.
  - Every price names the exact part and LCSC number with the date seen, 25.10.2026.

### Notes and side remarks: accepted

- **N1.**
  - CHRG's pull-up goes to 3V3, and NSS gets a pull-up so the radio stays deselected through reset (§ 3).
  - The hold wording is corrected: digital GPIOs can also hold through `gpio_deep_sleep_hold_en()`.
  - Before power-off, TX and SET are parked low with pulls off (D7, R-F4).
  - Strap reset states are an F2 checklist item.
- **N2.**
  - `begin(868.0, 125.0, 7, 5, 0x12, 10, 8, 0)`, `forceLDRO(false)` and `setCurrentLimit(100)` set every air setting explicitly.
  - F6 confirms the exchange, register dumps and conducted power on hardware.
  - The 868.0 MHz band-edge note stays open and flagged (§ 7 item 12). This revision doesn't claim compliance either.
- **N3.**
  - Inrush, effective capacitance, output discharge and restart, pin parking and low-battery transients are F6 tests (§ 7 item 9).
  - D9 now calls INA219 power-down mandatory, matching § 6.
  - The TPS61023's 0.1 µA is labelled typical, with the bounded value in the bounded inventory.
- **Budget notes.**
  - The firmware powers the INA219 down after every full read, including the first boot, and doesn't rely on the per-boot `inaInitialized` flag (D9, § 6 item 2).
  - Requests and failure paths are in the 5 % margin.
  - USB-connected operation draws from VBUS, which also charges the pack, so it isn't a battery budget case. The four USB states are measured in F6.

## Changes beyond the review

- mobric's answers Q1–Q14 are folded in. They are listed with where they're used in ARCHITECTURE.md § 8.
- New decisions:
  - D13, the winter energy strategy;
  - D14, connectors (Q7 left the choice to me).
- New requirements:
  - R-F11, Wi-Fi only for OTA;
  - R-P11, USB charging;
  - R-C5, the packet's meaning;
  - R-M6, the checklist gate.
- The energy model is committed as [calc/winter_model.py](../calc/winter_model.py), standard library only, with its output in [calc/winter_model_output.txt](../calc/winter_model_output.txt).

## Still open

- **For mobric** (ARCHITECTURE.md § 8, questions 15–21):
  - panel azimuth and snow;
  - a temperature logger in today's box this winter;
  - the D13 and D5 choices;
  - the cell model and protection IC;
  - conformal coating.
- **For F2:** the toleranced trip points at +1 / +44 °C, the R-P1 voltage bound with the chosen parts, the charger's toleranced settings, and the sleep inventory against the real BOM.
- **For F6:** every figure labelled assumed or model-derived that a measurement can replace, starting with the sleep current, the ESP32 awake current and M2's light-sleep listening.

## Where the evidence is

- **Datasheets and upstream sources:** downloaded to `hardware/station-pcb/build/f1-revision/research/` (gitignored). Each one can be fetched again from the links in ARCHITECTURE.md § Sources.
- **PVGIS series:** `build/f1-revision/pvgis/` (gitignored). They come from the query in ARCHITECTURE.md § Sources with `angle` set to 45, 60 or 70.
