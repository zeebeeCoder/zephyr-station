# F1 review — Codex

Reviewed 2026-10-25, branch `hardware/station-pcb`, commit `4cd5e934ff61f4c91e47affb728b86471bd6124d`. Scope: REQUIREMENTS.md, ARCHITECTURE.md, STATUS.md, station and gateway firmware, and MIKO-DATA.md. No designer files edited; no commit or firmware flashing.

**Disposition: revise F1 before approval. Counts: 1 blocker, 6 major, 5 minor, 3 notes.** These are architecture findings, not a schematic/layout sign-off. The owner's answers relayed by pcb-head (USB charging/programming, external antenna, new enclosure, possible Wi-Fi, 45° tilt, cold PM skipping) are accepted context, not missing-information findings.

## Blocker

### B1 — The proposed single reverse-protection MOSFET is not a charge-inhibit switch

- **Location:** ARCHITECTURE.md §1 Power path and D5; REQUIREMENTS.md R-P4.
- **Problem:** D5 proposes switching off the same P-FET used for reverse-input protection to remove panel power. In that orientation its body diode still conducts from a positive panel into the charger. Turning its channel off does not enforce the cold-charge prohibition.
- **Evidence:** Visually checked [CN3791 datasheet Figure 3, p.10](https://files.waveshare.com/wiki/Solar-Power-Manager-(D)/CN3791_Datasheet_EN.pdf). M2's orientation blocks battery backflow, not forward panel power. This is a topology error, independent of comparator accuracy.
- **Suggested fix:** Use a separately oriented disconnect plus reverse blocking, or back-to-back FETs with suitable control. Define a default-OFF gate state, brownout/startup behavior, hysteresis and worst-case NTC/reference/resistor/offset tolerances; nominal trips exactly at 0/45°C cannot guarantee those limits. Test open/short NTC and slow dawn ramps. The approved USB charging path must obey the same hardware temperature interlock even without panel power.

## Major

### M1 — The winter survival conclusion fails the document's own temperature model

- **Location:** ARCHITECTURE.md §§4.3–4.4; REQUIREMENTS.md R-P10 and §3.
- **Problem:** Multiplying every day/window by the December-wide 0.634 permitted-charge fraction loses the correlation of sunshine with freezing temperatures. The lowest raw-PV period is not the lowest chargeable-energy period. Mean harvest is correct, but the claimed worst-period margin and unconditional “enough” verdict are not.
- **Evidence:** Independently reprocessed the cached PVGIS hourly data, with the document's exact assumptions: 10 Wp, 60° south, 85% conversion, remove the configured 14% loss, permit charging only for `0 <= T2m <= 45`. Results below. The [PVGIS query](https://re.jrc.ec.europa.eu/api/v5_3/seriescalc?lat=50.90&lon=15.73&startyear=2005&endyear=2023&angle=60&aspect=0&usehorizon=1&pvcalculation=1&peakpower=1&loss=14&pvtechchoice=crystSi&mountingplace=free&outputformat=json) could not be freshly fetched; cached input metadata identifies SARAH3/ERA5, 2005–2023. Cache provenance and reproducible algorithm are below.

| Case | Independently computed battery harvest |
|---|---:|
| December mean | 8.678 Wh/day (agrees) |
| 12–18 Dec 2018 | 0.264 Wh/day, not 1.51 |
| 13–26 Dec 2018 | 1.007 Wh/day, not 1.61 |
| Worst December 7-day window, 14–20 Dec 2007 | 0 Wh/day |
| Worst December 14-day window, 1–14 Dec 2012 | 0.123 Wh/day |

Across the entire cached chronological series, daily cumulative energy deficits reach **40.57 Wh nominal M1** (1 Jan–16 Feb 2010) and **66.00 Wh pessimistic M1** (24 Dec 2005–13 Feb 2006). The assumed usable pack contains only `10.2 × .90 × .85 × 3.7 = 28.87 Wh`. This daily model is optimistic about storage because it allows within-day energy netting. M2 at 0.67/0.81 Wh/day instead gives maximum deficits 16.08/19.44 Wh. These are conditional model results, not measured performance; cell temperature may differ from air and PM skipping changes demand.

- **Suggested fix:** Recompute chronological SOC at the approved 45° tilt with hourly cold gating, charge-current clipping, chosen cell data, PM skipping and Wi-Fi policy. Check all winters and carry SOC across month/year boundaries. Make optimizations, capacity changes or a defensible thermal model necessary conditions of the sizing verdict. Do not assume a larger panel fixes periods when all charging is inhibited.

### M2 — USB bridge sleep claim is not supported by the cited operating condition

- **Location:** ARCHITECTURE.md D3, §§4.1–4.2; REQUIREMENTS.md R-F9/R-P7.
- **Problem:** VIO remains battery-powered. The design simultaneously promises zero battery draw and budgets 2 µA. More significantly, 2 µA is USB **suspend** typical current, not a guarantee for VDD5 absent with connected UART/auto-reset pins.
- **Evidence:** WCH CH343 datasheet, §5.2 and §6.2, locally cached `dl_fork7/ch343ds1.pdf` (11 pages); [manufacturer-authored datasheet mirror](https://archive.decromancer.ca/bitsavers.org/components/wch/_dataSheets/CH343DS1.PDF). ISLP for VIO has 2 µA typical, **50 µA maximum**, without I/O loading/pull-ups. This alone adds about 61 µA battery-side to the stated floor if 50 replaces 2 under the budget's conversion assumptions. Suspend and unplugged are different tests.
- **Suggested fix:** Require a documented power-off/leakage guarantee for the selected variant and all connected signals, or isolate/power the bridge appropriately. Measure USB absent, suspended, attached and battery absent. Reconcile R-F9 with the actual circuit and reserve worst-case current margin.

### M3 — 53 µA is an incomplete conditional estimate, not a pessimistic whole-board floor

- **Location:** ARCHITECTURE.md §§4.1–4.2/D6/D8/D9; REQUIREMENTS.md R-P7.
- **Problem:** The same 53 µA is repeated in the pessimistic column, mixing maxima, typicals and assumptions. The unknown off-board BME680 breakout is represented only by its sensor die. Divider, protection leakage and real pin states are not inventoried. A regulator or LED on that breakout can dominate the entire target.
- **Evidence:** [INA219 §7.5](https://www.ti.com/lit/ds/symlink/ina219.pdf) gives power-down 6 µA typical, 15 µA maximum. [TPS631000 §5.5](https://www.ti.com/lit/ds/symlink/tps631000.pdf) specifies 8 µA at **VOUT**, with a separate VIN current; the budget instead adds 8 µA directly at the battery. [Bosch BME680](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme680-ds001.pdf) specifies the IC, not its unidentified breakout. CH343 is addressed separately in M2.
- **Suggested fix:** Build typical and bounded leakage inventories from the actual BOM and breakout. Include feedback dividers, input bias, ESD/TVS leakage at temperature, status pull-ups and all held inputs. Define whether efficiency includes converter operating current to avoid counting it twice. Label 53 µA a conditional estimate until measured. Specify MODE for power-save operation. At the battery connector's 3.0 V endpoint, shunt/FET losses also mean TPS631000 VIN is below 3.0 V; its headline 2 A condition is not a guaranteed whole-pack endpoint rating, though ample margin likely remains for this load.

### M4 — Cold Voc and input clamp are not yet a bounded protection design

- **Location:** ARCHITECTURE.md D5/§7.1; REQUIREMENTS.md R-P1/R-P2.
- **Problem:** A generic TVS and ≥40 V passives do not protect a lower-rated charger. A TVS that stands off above normal cold Voc may clamp beyond the charger limit. Coefficient and Voc tolerance remain unverified.
- **Evidence:** [CN3791 pp.3–4](https://files.waveshare.com/wiki/Solar-Power-Manager-(D)/CN3791_Datasheet_EN.pdf): 28 V operating, 30 V absolute. Independently, `22.4 × (1 + .003 × (25 − T))` gives 25.424 V at −20°C and 26.096 V at −30°C, before tolerances/transients.
- **Suggested fix:** Specify maximum continuous and transient voltages at the IC, a clamp/OVP implementation and source-current/thermal limits. Include MOSFET VGS protection, reverse panel connection and night backflow. Use a wider-input charger if a toleranced design cannot fit the narrow window. Treat F2 closure as mandatory, not satisfied by the 40 V parts rule.

### M5 — INA219 relocation changes voltage meaning and charge regulation

- **Location:** ARCHITECTURE.md §1/§3/D9; REQUIREMENTS.md R-P9; station.ino `readINA219()`.
- **Problem:** Current calibration can remain compatible, but “none required” hides a voltage/energy semantic change. With IN+ at the battery and IN− at the load/charger junction, `getBusVoltage_V()` reports the junction, not battery terminal voltage. The shunt also lies between the charger regulation node and the pack.
- **Evidence:** [INA219 Figure 13 and §8.5.2](https://www.ti.com/lit/ds/symlink/ina219.pdf) define bus measurement at IN−. At 1.46 A a 0.1 Ω shunt introduces 146 mV and 0.213 W. station.ino uses bus voltage directly for the transmitted battery voltage and percentage and clamps negative current to zero.
- **Suggested fix:** Document the feedback/sense node and verify CC/CV termination with simultaneous load. Recover battery-side voltage as bus plus signed shunt voltage (and account for intervening protection losses). Update percentage/energy semantics: net battery current is not load current during charging. Keep signed current, Kelvin-route the shunt and rate it for continuous and fault power. A0=A1=VS correctly selects 0x45; the default calibration does fit 0.1 Ω.

### M6 — A dedicated SPI bus does not make task-context mutex calls ISR-safe

- **Location:** ARCHITECTURE.md §3/D4/§7.4.
- **Problem:** Deferring the RadioHead/core issue solely to an F6 soak test is too late. Bus exclusivity avoids other peripherals' contention but does not remove calls to non-ISR semaphore APIs from the interrupt path.
- **Evidence:** Cached RadioHead 1.147 `RH_RF95.cpp::handleInterrupt()` calls `spiRead`; `RHSPIDriver.cpp:47–55` enters a transaction. `RHHardwareSPI.cpp::beginTransaction()` calls Arduino SPI. Cached [arduino-esp32 3.3.11 SPI.cpp](https://github.com/espressif/arduino-esp32/blob/3.3.11/libraries/SPI/src/SPI.cpp) and [esp32-hal-spi.c](https://github.com/espressif/arduino-esp32/blob/3.3.11/cores/esp32/esp32-hal-spi.c) use mutex locking, including `xSemaphoreTake(..., portMAX_DELAY)` when HAL locks are enabled. This is a static compatibility concern, not a reproduced hardware crash.
- **Suggested fix:** Resolve the exact build configuration and interrupt strategy before freezing the radio firmware plan. Prefer ISR notification with radio servicing in task context, or a demonstrated supported port. Keep the F6 soak test, but do not present a private SPI bus as the fix.

## Minor

### m1 — Cadence and PMS durations are assumptions, and the proposed schedule needs a policy

- **Location:** ARCHITECTURE.md §§4.1–4.2/§6; REQUIREMENTS.md §3.
- **Problem:** 31.6 s PMS time is a nominal estimate, not an exact result from source; retry timing permits 30.6–35.1 s. A 65 s full read also crosses the next 60 s listen deadline. M1 assumes the corrected cadence while absolute scheduling is called optional.
- **Evidence:** station.ino `readPMS7003()` has 100 ms + 30 s + up to ten 500 ms iterations; `measureWindSpeed()` adds 31 s. `setup()` invokes fifteen listen wakes then a full read, sleeping 60 s after each. Requests can add full reads. The stated 19.4-minute current cycle is a reasonable nominal approximation.
- **Suggested fix:** Label timing as assumed/nominal, budget failed reads and bounded on-demand traffic, and specify skipped/coalesced listen slots during long reads. Separate present-cadence M1 from future scheduled M1.

### m2 — Preferred radio module has a different published receive current

- **Location:** ARCHITECTURE.md §4.1/D4.
- **Problem:** 10.3 mA is taken from the chip/RFM95 literature while Ra-01H is the preferred assembled module.
- **Evidence:** [Ai-Thinker Ra-01H specification v1.0](https://docs.ai-thinker.com/_media/lora/docs/ra-01h_product_specification_en.pdf), locally recovered `dl_fork8/ra01h_ai.pdf`, p.5: 12.15 mA receive. p.6 confirms 803–930 MHz, 2.7–3.6 V, −40 to +85°C, 17×16×3.2 mm. [HopeRF V1.0](https://cdn.sparkfun.com/assets/learn_tutorials/8/0/4/RFM95_96_97_98W.pdf) is a distinct 16×16 mm module.
- **Suggested fix:** Budget by exact module and relevant settings, or label chip current as an unverified estimate. Substituting 12.15 mA adds about 5.54 mAh/day for 1344 × 8.1 s listens. The architecture choice remains plausible; footprints are not interchangeable.

### m3 — LDO cost-down is not valid across the stated battery range

- **Location:** ARCHITECTURE.md D6 option (d).
- **Problem:** The assertion that a sagging 3.3 V LDO stays above the ESP32 minimum is false at a 3.0 V battery endpoint under load. An LDO cannot deliver 3.0 V from 3.0 V after dropout, shunt and protection losses.
- **Evidence:** R-P5 specifies 3.0 V pack minimum; [ESP32-WROOM-32E operating conditions](https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.pdf) require at least 3.0 V at the module. This follows directly from voltage headroom; the chosen buck-boost avoids the issue.
- **Suggested fix:** Remove the unconditional LDO alternative or explicitly raise battery cutoff and recompute usable capacity.

### m4 — Protection and mechanical requirements need traceable D10–D12 implementation checks

- **Location:** ARCHITECTURE.md D3/D4/D8/D10–D12; REQUIREMENTS.md R-E3/R-M3–R-M5.
- **Problem:** Requirements already include ESD, M3 holes and locking JST connectors, so these are not missing requirements. However D10 omits ESD for 1-Wire, and D11/D12 do not carry connector assignments, mounting clearances and test access forward. USB protection and CC wiring are also absent from the architectural interface description.
- **Evidence:** Direct comparison of the cited sections. D4 already correctly calls for 50 Ω, a π footprint and RF ESD; D2 calls for antenna keep-out. These need layout constraints, not just prose.
- **Suggested fix:** Add an F2/F3 checklist covering all external signal/power ports, USB-C CC1/CC2 sink resistors and ESD, battery fuse/connector current rating, correct JST series/pin ordering/mating parts, panel reverse protection and any needed fault-current protection. Specify M3 drill/NPTH choice and screw/standoff copper clearance; test points including grounds, both shunt sides, charge inhibit, EN/BOOT and radio SPI/DIO. Derive RF width from the actual stackup, with continuous ground, stitching and an ESP antenna keep-out clear of cells, metal and cables. Do not copy 1.2–1.4 mm as a verified impedance.

### m5 — Several provenance labels overstate what is known

- **Location:** REQUIREMENTS.md §1; ARCHITECTURE.md §§4.1/4.3/9 and D5/D12.
- **Problem:** Owner statements and listing screenshots are labelled “datasheet”; PMS “measured 25–80 mA (informal)” has no traceable measurement source. PVGIS-derived extrema/fractions are computed model outputs. MPPT's quoted range excludes resistor tolerance and input bias. Historical prices/stocks cannot be reproduced from generic C-number URLs alone.
- **Evidence:** MIKO-DATA.md is owner/photo evidence, not a full cell or protection-IC specification. CN3791 electrical table specifies MPPT 1.18–1.23 V and ±100 nA bias. Nominal `1.205 × (1 + 470/32.4)` is 18.685 V; `0.120/0.082` is 1.463 A. Those nominal values pass, but are not full tolerance analyses.
- **Suggested fix:** Add “owner/photo” and “model-derived” provenance, label unsourced measurements assumed, retain exact part/date evidence and include divider/current-sense tolerances. The known unknown cell/BMS/panel data remain explicitly provisional rather than inferred manufacturer guarantees.

## Notes and passed checks

### N1 — Pin assignment passes, with a correction to the review brief's hold rule

- **Location:** ARCHITECTURE.md §3; station.ino pin definitions and sleep functions.
- **Evidence/result:** No direct pin conflicts found. SPI18/19/23/5, DIO0=35, optional DIO1=34, RESET=17, PMS25/26/27, enable13, wind4, buses21/22 and32/33, vane36, status39 and optional1-Wire16 fit **N4 without PSRAM**. GPIO34–39 are input-only/no internal pulls; no flash GPIO6–11 is used. GPIO12 low at boot is correct for this module. GPIO0/2/5/12/15 strap constraints need reset-state checking in F2. CHRG's pull-up must go to 3V3, and NSS should have a defined deselected reset state. [ESP32 module datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.pdf).
- **Clarification/fix:** The brief's “gpio_hold works on RTC pins only” is too broad: [Espressif GPIO API](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/peripherals/gpio.html) also describes digital output hold with `gpio_deep_sleep_hold_en()`. RTC hold and EXT0/EXT1 wake have different constraints. GPIO27 is suitable in either case. Park TX/SET LOW and remove pulls before power-off; input mode alone is not a complete no-backfeed guarantee.

### N2 — Radio air settings and the proposed TX power mapping pass source inspection

- **Location:** ARCHITECTURE.md D4; REQUIREMENTS.md R-F7/R-C2.
- **Evidence/result:** Cached [Seeed source at f82d4dc](https://github.com/Seeed-Studio/Grove_LoRa_433MHz_and_915MHz_RF/tree/f82d4dc943e8c91fd80ecef5fa5f1a625466ca0d) has modem bytes `72 74 00`; [RadioHead 1.147](https://www.airspayce.com/mikem/arduino/RadioHead/RadioHead-1.147.zip) has `72 74 04`. Both correspond to BW125/CR4/5/SF7, explicit header, CRC and LDRO off; bit 2 changes receiver AGC, not the packet format. Both initialize preamble 8 and use four RadioHead header bytes. Seeed `setTxPower(13,false)` writes PA_CONFIG `0x88`; RadioHead `setTxPower(10,false)` also writes `0x88`, with normal PA_DAC. Nominal conducted output is thus 10 dBm. 28-byte LoRa airtime independently computes to 66.816 ms. At 96 packets/day this is 0.00742% average TX airtime, excluding requests/retries.
- **Suggested follow-through:** Explicitly initialize sync word 0x12 and all air settings instead of relying on reset defaults; confirm packet exchange and actual conducted/ERP power on hardware. Identical register mapping does not prove identical antenna-system output. The 868.0 MHz band-edge compliance note remains unresolved; this review does not certify legal compliance. Gateway radio initialization uses the Seeed defaults and sets 868.0 MHz.

### N3 — Converter choice and arithmetic mostly pass; retain their conditions

- **Location:** ARCHITECTURE.md D6/D7/§4.
- **Evidence/result:** [TPS61023](https://www.ti.com/lit/ds/symlink/tps61023.pdf) explicitly supports true input/output disconnection in shutdown; 0.1 µA is typical, not an all-temperature guarantee. This does not isolate UART/SET. [TPS631000](https://www.ti.com/lit/ds/symlink/tps631000.pdf) supports the required voltage range and advertises 2 A at VIN≥3 V/VOUT=3.3 V. [PMS7003 v2.5](https://download.kamami.pl/p564008-PMS7003%20series%20data%20manua_English_V2.5.pdf) supports 4.5–5.5 V, ≤100 mA active and −10°C minimum operation. The accepted cold-PM policy is appropriate.
- **Suggested follow-through:** Verify inrush, effective capacitance, output discharge/restart, pin parking and low-battery transients on the assembled board. Keep INA power-down and radio sleep mandatory; D9 currently calls the former merely recommended although §6 correctly requires it.

## Independent budget reconstruction

All figures below deliberately use the draft's assumed efficiencies, currents and times, so agreement validates arithmetic rather than those assumptions. Battery conversion factors are `3.3/(0.9×3.7)=0.990991` and `5/(0.9×3.7)=1.501502`.

| Quantity | Independent result | Interpretation |
|---|---:|---|
| Sleep | 52.754 µA | `(19.35×3.3/(.7×3.7)) + 8 + 15 + 5 + .1`; subject to M2/M3 |
| M1 listen nominal/pessimistic | 139.98 / 199.49 µAh | 1.3 s startup at ESP+1.6 mA, 8.1 s at ESP+10.3 mA |
| M1 full nominal/pessimistic | 1.902 / 2.577 mAh | 65.017 s, 31.6 s PMS, brief heater and TX |
| M1 daily nominal/pessimistic | 371.73 / 516.54 mAh | 1344 listens + 96 reads + remaining sleep |
| M1 daily energy | 1.375 / 1.911 Wh | agrees with rounded draft |
| No-harvest M1 autonomy | 20.99 / 15.11 days | conditional usable capacity 7803 mAh |
| M2 listen nominal/pessimistic | 26.64 / 27.14 µAh | 0.3 s awake initialization plus 8 s light-sleep listening |
| M2 full nominal/pessimistic | 1.507 / 1.876 mAh | 63.8 s profile with radio asleep until TX |
| M2 daily energy/autonomy | 181.52–217.61 mAh; .672–.805 Wh; 35.86–42.99 days | independently reconstructed; depends on implementing light sleep/80 MHz |

Neither cycle timing nor a constant 3.7 V conversion is a measured discharge profile. Firmware currently initializes the INA only on full reads; shutdown must not blindly depend on the per-boot `inaInitialized` flag after timer wake. The first full boot must successfully power it down, and later full reads must restore conversion mode. Requests, failure paths and USB-connected operation need separate cases.

## Reproducibility and verification limits

Local source cache used read-only:

`/private/tmp/claude-501/-Users-mikolaj/e0e5aebe-e492-4d7c-bcbf-794da968096b/scratchpad/`

- PVGIS: `pvgis/data/ser60_1k.json`, SHA-256 `66b1548093a9b15f062adb9aed7e78c9c10262daec90899b09f742072edb8b19`. The metadata says 1 kWp, 60° south, 14% system loss; scale P by .01 for this panel. Each record represents an hour. Aggregate `P × .01 × .85/.86` only when `0≤T2m≤45`; otherwise zero. Search all consecutive December windows. For the full-series daily deficit use `D=max(0,D+daily_load−daily_harvest)` and retain the largest D, without resetting at year boundaries. This is fresh reviewer code, not execution of the designer's budget script.
- Radio: `dl_seeed/RH_RF95.cpp`, `dl_rh/rh/RadioHead/` (version macros verified as 1.147), `dl_esp/SPI.cpp` and `dl_esp/esp32-hal-spi.c`. Network retrieval failed for the exact radio sources; cached copies were inspected, not freshly authenticated against remote hashes.
- PDF fallbacks: `dl_cn3791_en/cn3791_waveshare_en.pdf`, `dl_fork7/ch343ds1.pdf`, `dl_fork8/ra01h_ai.pdf`. CN3791 Figure 3 was rendered and visually inspected. Core TI/Espressif/Bosch/Plantower/HopeRF documents were also retrieved via web. The old Ai-Thinker PDF URL now redirects to its documentation home, so the local manufacturer-authored PDF supplied the detailed table.

Not verified: actual cell model/capacity/cold behavior, BMS topology and leakage, panel coefficient/tolerances, 45° hourly harvest, thermal lag, snow/shading, all maximum leakages, actual RF performance, CH343 unplugged behavior, exact connector/NTC/comparator/TVS/FET BOM, impedance, layout, PCBA availability/prices, or regulatory certification. There is no finished schematic/BOM/layout in the reviewed F1 documents to validate those implementations. No hardware tests or firmware compile were performed; the requested artifact is a documentary architecture review.
