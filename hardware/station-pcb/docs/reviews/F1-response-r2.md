# F1 re-review response

This is the response by `mobric/pcb-opus-5-5` to [F1-codex-r2.md](F1-codex-r2.md), the Codex re-review of F1 revision 1 at a22e006. It was written on 26.10.2026 and committed together with F1 revision 2 of [REQUIREMENTS.md](../REQUIREMENTS.md) and [ARCHITECTURE.md](../ARCHITECTURE.md).

**Result: 11 fixed, 1 accepted, none disputed.**
- **Fixed:** the revised documents now do what the review asked, or something that meets the same aim. Each row says which.
- **Accepted:** the passed checks and side remarks. Their follow-through is now in the documents.
- **Disputed:** none.

Two fixes end in a question for mobric, because only mobric can make the call:
- the relaxed R-P7 (Q22, from R2-M2);
- whether D13 keeps every gateway request heard (Q23, from R2-m4).

In the "Where" column, § and D numbers refer to ARCHITECTURE.md and R- numbers to REQUIREMENTS.md, both as revised.

## Summary

| Item | Disposition | What changed | Where |
|---|---|---|---|
| **R2-B1** Fail-safe start-up claimed for TLV3012; the guarantee belongs to TLV3012B | **Fixed** | Three TLV3012BIDBVR (push-pull, power-on reset): a cold comparator, a hot comparator, and a new one for battery overvoltage. Outputs are combined by series FETs, never wired together, and every gate has a pull-down. A state-by-state proof covers every source combination, slow ramp and brownout. Both endpoints are recomputed with every tolerance in a committed script | D5, D5.2, § 1, § 7 item 1, § 10; R-P4; [calc/interlock_trips.py](../calc/interlock_trips.py) |
| **R2-M1** The survival result omits the hysteresis and implementation errors | **Fixed** | The model now has a Schmitt gate at the toleranced energy corner, a nightly power-on reset, adaptive pessimistic loads, a ± 15 % charge-estimate error and specified low-energy recovery. `r2check` reproduces the review's table exactly. D13 (a–d) is reissued, and "survives every case" is withdrawn as worded | § 4.3–4.5, D5, D13, § 6 items 10–11; R-P10, REQUIREMENTS § 3; [calc/winter_model.py](../calc/winter_model.py) |
| **R2-M2** 95.8 µA is not a bound and fails R-P7 at 3.0 V | **Fixed** | The column is now a "high-side estimate" and states the basis of each row. Both conversion corners are given. R-P7 is proposed as measured limits with conditions: ≤ 100 µA at 3.7 V and 25 °C, ≤ 150 µA at 3.0 V and +50 °C. mobric's agreement is asked (Q22) | § 4.1, § 4.2, § 7 item 6, § 8; R-P7 |
| **R2-M3** SMBJ28A doesn't establish the LT3652's 40 V limit | **Fixed** | A defined surge, plus a TPS26600 eFuse (OVP 31–34 V, current limit, −60 V reverse) and an SMBJ33CA. Computed bounds: ≤ 55 V at the eFuse and ≤ 36 V at the LT3652's VIN. The TVS stands off above cold Voc. The CN3791 part lapses with the D5 decision | D5, § 1, § 2, § 7 item 2, § 10; R-P1 |
| **R2-M4** CHRG can't be pulled up to the always-on 3V3 | **Fixed** | CHRG and FAULT go to test points only, with no pull-up. Charging is inferred from the INA219's sign, and GPIO39 becomes a spare | § 3, D5, D9, § 10; R-F10, R-M4 |
| **R2-M5** The VBUS ramp to 20 V can damage the CH343P | **Fixed** | The tests are split: panel ramp to 30 V, VBUS only up to 5.5 V. Supported USB sources are defined, and VBUS above 5.5 V is out of scope | § 7 item 1, D3, D5; R-P11 |
| **R2-m1** Pessimistic PMS time and slot counts not in the model | **Fixed** | One explicit timeline gives event durations and slot counts. The pessimistic PMS time is used, and retries and requests are budgeted separately | § 4.3, § 6 item 8; `listen_event`, `read_event`, `day_load` |
| **R2-m2** Termination drop and "1–2 % short" unsupported | **Fixed** | 11–18 mV at the LT3652's C/10 (110–184 mA), with the timer disabled so C/10 is the whole stopping rule. The capacity claim is withdrawn and the effect labelled unknown | D9, D5 |
| **R2-m3** A nominal 500 mA setting isn't a ≤ 500 mA limit | **Fixed** | RISET 750 Ω gives 356–444 mA with the gain tolerance. Total VBUS ≤ 461 mA. Supported sources defined, and a combined-charging test added | D5, D3, § 7 item 4; R-P11 |
| **R2-m4** Adaptive listens don't fit the gateway's 120 s request window | **Fixed** | The model counts the share of requests heard (40 % and 13 %). A 2-min listen variant (a2) hears every request; it's costed and recommended with 8 cells. The trade-off goes to mobric (Q23), with an acceptance test | § 4.3, § 4.5, D13, § 6 item 10, § 7 item 5, § 8 |
| **Longest-run defect** (verification details) | **Fixed** | The longest outage now comes from the 18 complete winters only | § 4.4; `simulate()` |
| **Passed checks and side remarks** | **Accepted** | SHDN and ISET control kept. Translator DIR, input and V3 checks added to § 10. The checklist closes the CHRG domain, USB test voltage, surge waveform and interlock thresholds. CH343 §5.2 correction noted | D3, D5, § 10 |

The original items the re-review marked "partly" close through these rows:
- B1 through R2-B1 and R2-M1;
- M1 through R2-M1;
- M3 through R2-M2;
- M4 through R2-M3;
- M5 through R2-m2;
- m1 through R2-m1;
- "Budget notes" through R2-m1 and R2-M1.

## Details

### R2-B1: fixed

- **The finding is confirmed.** Revision 1 said "for example TLV3012 (output driven low below its minimum supply)". That behaviour is the B version's power-on reset (SBOS300C §9.4.5); the plain TLV3012 doesn't have it.
- **Exact part: TLV3012BIDBVR, three of them.**
  - §9.4.5: during the power-on reset the push-pull TLV3012B's output "will be low (sinking)". The reset is active "for up to 1.9 ms after the minimum supply voltage threshold is crossed, or immediately when the supply voltage drops below minimum supply" (1.65 V).
  - §9.4.4: the inputs are fail-safe up to 5.5 V, independent of V+.
  - The open-drain TLV3011B goes high-Z during its reset, so it doesn't qualify.
  - Revision 1's other example, an MCP6542 with an LM4041, is dropped, so its separate supply-good proof isn't needed.
- **Both window comparisons, and their polarity.** Each output is high only for "charging allowed".
  - **U1, cold:** IN+ is a tap of VREG (10.0 kΩ / 24.3 kΩ) with 3.32 MΩ of positive feedback from OUT1. IN− is the NTC node. OUT1 is high when the cells are warm enough.
  - **U2, hot:** IN+ is the NTC node, IN− a tap of VREG (10.0 kΩ / 3.92 kΩ). OUT2 is high when they aren't too hot.
  - **U3, battery overvoltage (new, answer 20):** an LM4041-B against the battery voltage through 768 kΩ / 301 kΩ. The divider's low side opens with the interlock rail, so it draws nothing at night. OUT3 is high when the cells are below the trip.
- **Combining, without wired outputs.**
  - Solar: Q1, Q2 and Q6 in series turn on P-FET Q3, which feeds the LT3652's SHDN divider.
  - USB: Q4, Q5 and Q7 sit in series with the BQ25170's ISET resistor.
- **Pull-downs.**
  - 1 MΩ on every gate.
  - The SHDN divider's lower resistor holds SHDN at 0 V while Q3 is off.
  - An open ISET means no charge current (BQ25170 §7.3.1.1).
- **Proof by state.** D5 has a table of every state and what holds each charger off:
  - no source;
  - VREG between 0 and 1.0 V, then from 1.0 to 1.65 V and 1.9 ms beyond;
  - VREG valid but still ramping;
  - a panel ramp, held off by the TPS26600's UVLO (14.25 V minimum);
  - a panel brownout, and a USB ramp or brownout;
  - both sources together;
  - NTC open or shorted;
  - overvoltage, Q8 open, and an open ISET chain.

  During a slow ramp U1 and U2 compare fractions of VREG and are already valid. U3's start-up errors (an under-biased LM4041, a Q8 not yet on) all read "overvoltage". The one assumption, VGS(th) ≥ 1.0 V minimum, is an F2 selection rule.
- **Both endpoints recomputed for the actual parts** ([calc/interlock_trips.py](../calc/interlock_trips.py), output in [calc/interlock_trips_output.txt](../calc/interlock_trips_output.txt)). Inputs:
  - the MF52A table's spread (R25 ± 1 %, B ± 1 %) and ± 0.5 % drift;
  - 0.1 % resistors at 25 ppm/K over ± 30 K;
  - offset ± 9 mV and hysteresis 2–8 mV (§6.9);
  - VREG ± 3 %;
  - NTC self-heating, computed 0.099 K, allowance 0.1 K;
  - a 0.5 K NTC-to-cell gradient (assumed; F6 measures it).

| Trip | Nominal | Electrical worst case | Safety corner |
|---|---|---|---|
| Cold off | +1.71 °C | +0.75 to +2.69 °C | +0.15 °C (≥ 0) |
| Cold on | +2.11 °C | +1.11 to +3.06 °C | +0.51 °C |
| Hot off | +43.26 °C | +42.16 to +44.36 °C | +44.86 °C (≤ 45) |
| Hot on | +43.04 °C | +41.97 to +44.16 °C | +44.66 °C |

- **Both directions of hysteresis:** cold 0.26–0.48 K, hot 0.07–0.31 K. The overvoltage trip is 4.29–4.43 V, at least 36 mV above the LT3652's highest float (4.25 V over temperature).
- **The SHDN and ISET methods are kept,** as the review advised.
- **One limit is stated, not hidden:** the interlock isn't redundant. A single failed comparator or shorted FET defeats its own condition (D5).

### R2-M1: fixed

- **Thresholds and tolerances** come from the circuit above. The **energy corner**, every tolerance toward less charging, is off below +2.69 °C and on above +3.06 °C.
- **The specified hysteresis changes.** Revision 1 asked for 2–3 K; the review's table shows that a 3 K re-enable separation alone costs an outage winter. Revision 2 keeps the hysteresis no larger than chatter needs: 0.26–0.48 K cold. R-P4 now caps the energy corner at +3.1 °C.
- **Model changes** ([calc/winter_model.py](../calc/winter_model.py)):
  - a Schmitt gate with state;
  - a **nightly reset**: the interlock runs from the panel, so every hour without PV power resets it to off, and charging restarts only above the "on" trip. The review's case of keeping the state overnight is kept as a sensitivity row;
  - adaptive schedules with **pessimistic loads**;
  - a **charge estimate off by −15 %, 0 or +15 %** of usable energy, assumed, with F6 to measure it;
  - **low-energy states:** run, hibernate (below 3 %, resume above 12 %), and off under the TPS3840's UVLO (release at 2 %). The ESP32 boots straight into hibernation;
  - the panel at azimuth 233° (answer 15).
- **`r2check` reproduces the review's table to the last digit,** using revision 1's loads and policy at 45° south:
  - baseline: 44.54 lean days, 22.511 %;
  - +1 / +3 °C: 158.71 / 48.42 days, 6.104 %;
  - +1 / +4 °C: 1 winter, 9.71 days;
  - +2 / +5 °C: 1 winter, 10.75 days.
- **The adaptive policy changes:** lean below 60 % and back above 70 %, survival below 35 % and back above 40 %. These thresholds keep the station out of outages even when the estimate reads 15 % high.
- **D13 (a–d) reissued** at the energy corner with the nightly reset (§ 4.5):
  - **M2 adaptive on today's pack:** no outage hour in any of the 18 winters, at pessimistic loads with the estimate off by up to 15 % in either direction (lowest charge 13 %). With the review's +1 / +4 °C and the state kept overnight: lowest 18 %. The cost is 9–30 lean and 2–8 survival days a winter, hearing 40 % and 13 % of requests in those modes.
  - **(b):** the review is right that revision 1's 24.7 Ah was M1 nominal under the old gate. At the energy corner, M1 nominal needs 55.7 Ah (17 cells) and M1 pessimistic 87.7 Ah (26 cells). mobric asked for 24.7 and 44.3 Ah (answer 17), which is 8 and 14 cells; both are evaluated.
  - **(c)** stays illustrative and isn't rerun.
  - **(d):** M1 nominal on today's pack has 14 of 18 winters with an outage, 314 days, up to 72 days in one go. The restart rule behind those durations is now specified, not just modelled.
- **"Survives every case" is withdrawn as worded.** The claim is restated with its conditions (§ 4.5, REQUIREMENTS § 3), and R-P10 now names them as the acceptance condition: energy corner, nightly reset, pessimistic loads, ± 15 % estimate, and recovery after any low-energy event.
- **Low-energy recovery is specified (§ 6 item 11, D5.2) and modelled:**
  - hibernation below a voltage threshold, with an hourly battery check;
  - a boot check before any radio, Wi-Fi or PMS start;
  - the brown-out detector on;
  - a TPS3840 that holds the 3.3 V converter off below 3.1 V and releases it at about 3.3 V.

  In the model every hibernation ends in a restart. With the firmware's hibernation removed, the TPS3840 alone recovers the station every time: 22 of 22 cut-offs for M1 nominal.

### R2-M2: fixed (agreement asked)

- **The word "bounded" is dropped.** The third column is a "high-side estimate". Each row states its basis: a datasheet maximum, a typical value with no maximum published, or an allowance. § 4.2 says plainly that the total is not a guaranteed bound.
- **New rows:** the TPS3840 (0.3 / 0.7 µA) and the overvoltage divider's switch (0 / 1 µA). The CHRG path is gone (R2-M4), and the LT3652 VIN-node path is explained through the chip's reverse current.
- **Both corners:**
  - the board at the battery link: 52.8 / 97.4 µA at 3.7 V and 85 %, and 73.0 / 132.7 µA at 3.0 V and 70 %;
  - the cells, with the protection board: 55.8 / 103.4 µA and 76.0 / 138.7 µA.

  The review's 95.73 and 131.03 µA reproduce revision 1's rows; the new rows add up to 1.7 µA.
- **R-P7 now proposes measured acceptance limits with conditions,** for the board at the battery link, USB unplugged and the panel dark:
  - ≤ 100 µA at 3.7 V and 25 °C;
  - ≤ 150 µA at 3.0 V and +50 °C.

  The 17 µA left at 3.0 V has to cover the rise to +50 °C. F2 limits the catch diode to ≤ 10 µA at 4.2 V and 50 °C; the ESP32 has no data. Because this relaxes the old requirement, mobric is asked (Q22).
- **The winter model** uses the 3.0 V high-side figure in every pessimistic case. In survival mode it's a large share of the day: 3.3 of 12.7 mAh.

### R2-M3: fixed

- **Surge definition (assumed):** any pulse the panel TVS clamps within its 600 W, 10/1000 µs rating, up to 11.3 A.
  - That fixes the waveform and the current, whatever the source impedance. The panel cable is under 1 m.
  - Temperatures: the clamp is taken at up to +50 °C (R-E1), the breakdown at down to −30 °C (the panel's cold limit, R-P1).
  - A direct lightning strike is out of scope (REQUIREMENTS, out of scope).
- **Limiting and OVP added: a TPS26600** (SLVSDG2G). It replaces the 60 V Schottky:
  - factory UVLO 14.25–15.75 V and OVP 31–34 V, disable delay 6 µs typical;
  - current limit 0.95–1.05 A, fast trip ≤ 1.98 A within 250 ns;
  - 62 V absolute maximum (70 V for 10 ms), −60 V reverse.
- **Bounds (computed):**
  - **At the eFuse's input:** the SMBJ33CA clamps at 53.3 V at 11.3 A, or 54.6 V at +50 °C. Wiring inductance adds little for this waveform: 20 nH × 11.3 A / 10 µs ≈ 0.02 V. That gives ≤ 55 V against 62 V.
  - **At the LT3652's VIN:** until the eFuse opens at ≤ 34 V, OUT can rise only as fast as ≤ 1.98 A charges ≥ 10 µF effective. With a 10 µs disable (assumed; 6 µs typical, no maximum published), VIN stays ≤ 36 V against 40 V. The margin holds for delays up to 30 µs. F6 measures the delay and the overshoot.
- **Off-state leakage at cold Voc.** The SMBJ33CA stands off 33 V at ≤ 1 µA, above the cold Voc of about 28 V. Its breakdown at −30 °C is still ≥ 34.7 V.
- **Normal operation stays inside the 32 V operating range.** The OVP never acts in normal use: cold Voc is below its lowest release (28.5 V) and its lowest trip (31 V).
- **The CN3791 alternative's OVP dynamics lapse.** D5 = LT3652 was approved on 25.10.2026, and the CN3791 is kept only as a rejected-alternative note.

### R2-M4: fixed

- CHRG and FAULT go to test points only, with no pull-up on the board, so no rail can drive them and no leakage path remains. Revision 1's pull-up to 3V3 would have exceeded their VIN + 0.5 V rating every night, with VIN at 0 V.
- F6 probes them with a pull-up to the LT3652's own VIN.
- The firmware infers charging from the INA219's signed current (D9, § 6 item 2). GPIO39 is a spare input (§ 3).
- R-F10 is rewritten as a power-domain rule, and § 10 checks it.

### R2-M5: fixed

- § 7 item 1 now ramps the panel input to 30 V and VBUS only to 5.5 V. The full-board VBUS ramp to 20 V is withdrawn.
- D3 and R-P11 state the limit: the CH343P's VDD5 is rated 6 V absolute, and the board has no overvoltage protection for it. USB sources above 5.5 V are out of scope. The charger's own high-voltage behaviour isn't tested on the assembled board.

### R2-m1: fixed

- **One explicit timeline** (`listen_event`, `read_event`, `day_load`) gives every duration and count (§ 4.3).
- **The pessimistic PMS time of 35.1 s** is now in the pessimistic events: M1 68.5 s and 2.79 mAh, M2 36.3 s and 1.78 mAh. The PMS share rises from 1.05 to 1.46 mAh per read.
- **Slots follow an absolute minute grid.** A full read takes every slot it overlaps: a 65 s M1 read costs two slots (1246 listens a day), and a 32.8 s M2 read costs one (1344).
- **Retries and requests are separated.** Retries sit inside the 35.1 s. Gateway requests are budgeted at 2 a day nominal and 10 pessimistic, each costing an extra full read. Revision 1's 5 % margin is gone.

### R2-m2: fixed

- With the timer disabled (TIMER to ground), C/10 is the whole stopping rule. VSENSE 7.5–12.5 mV over 68 mΩ is 110–184 mA, which is 11–18 mV across the 0.1 Ω shunt: about 15 mV, as the review says.
- The "1–2 % short of a full charge" claim is withdrawn. The capacity effect is labelled unknown until the cell model is known (Q19) or F6 measures it.
- The CC/CV and termination bench test stays (§ 7 item 3).

### R2-m3: fixed

- RISET 750 Ω (1 %) with K_ISET 270–330 AΩ gives 356–444 mA.
- Total VBUS: ≤ 444 mA charger, ≤ 15 mA CH343P and ≤ 2 mA interlock, so ≤ 461 mA. The board presents 5.1 kΩ Rd and never asks for more than default power.
- Supported sources are defined (D5, R-P11).
- § 7 item 4 adds panel and USB charging at the same time, and termination under system load.

### R2-m4: fixed

- **The model counts the share of requests heard.** The unchanged gateway resends every 2 s for 120 s (gateway.ino lines 106 and 132), so a request is heard only if a listen window falls inside those 120 s: min(1, 120 s / listen period). That is 40 % in lean (5 min) and 13 % in survival (15 min).
- **(a2) listens every 2 min** in lean and survival, so it hears every request. It costs 87 instead of 73 mAh/day in lean and 29 instead of 9 in survival (nominal).
  - On today's pack it has one outage winter at pessimistic loads.
  - On 8 cells it has none, in every case modelled.
- **The trade-off is explicit in D13 and goes to mobric (Q23):** (a1) or (a2), 8 or 14 cells. § 7 item 5 adds an acceptance test: a request heard within 120 s at each listen period.
- No gateway change is proposed.

### Longest-run defect: fixed

`simulate()` now reports the longest outage from the 18 complete winters only. Every longest outage in the output starts inside 2005/06–2022/23 (§ 4.5, recovery table).

### Passed checks and side remarks: accepted

- **LT3652 SHDN and BQ25170 ISET** stay the control paths.
- **SN74LVC1T45:** § 10 now asks for fixed DIR levels, no floating inputs, and the V3 rail's behaviour while unpowered.
- **The F2/F3 checklist** now closes the items the review listed:
  - the CHRG power domain (§ 10, R-F10);
  - the safe USB test voltage (§ 7 items 1 and 4);
  - the surge waveform and bounds (§ 10, R-P1);
  - the interlock thresholds and the proof by state (§ 10).
- **RadioLib 7.8.1:** no change needed. The register dumps stay in F6.
- **CH343 §5.2 correction:** noted. D3's all-VBUS topology stands.

## Changes beyond the review

- **D5 = LT3652, approved by mobric on 25.10.2026** (relayed by the coordinator). The CN3791 becomes a rejected-alternative note, and D5 is designed around the LT3652.
- **mobric's answers 15–21 are folded in** (§ 8):
  - azimuth about 233°, so the model is rerun at `aspect=53`;
  - Samsung 18650 cells, 3.4 Ah each;
  - the protection IC is unmarked, so the on-board protection becomes self-sufficient (D5.2, R-P5): the U3 overvoltage cut-off, the TPS3840 UVLO, and an inline fuse at the pack;
  - conformal coating, yes (R-E4, § 10);
  - for D13, (b) combined with (a), sized for 24.7 and 44.3 Ah: 8 and 14 cells, with dimensions, mass and compartment.
- **New questions:** Q22 (R-P7) and Q23 (the D13 choice). Questions 15 (snow), 16 (logger) and 19 (a photo of a cell wrapper) stay open.
- **New committed calculation:** [calc/interlock_trips.py](../calc/interlock_trips.py) and its output.
- **The winter model gains:**
  - the `r2check` command, which reproduces the review;
  - the 2-min listen schedules;
  - the pack tables in 3.4 Ah cells;
  - the recovery table.
- **D12's cost estimate** grows to about $280–300 for 5 boards (assumed, unpriced new parts).

## Still open

- **For mobric** (ARCHITECTURE.md § 8): questions 15, 16, 19, 22 and 23, and approving D2–D4 and D6–D14 at the F1 gate.
- **For F2:**
  - FETs meeting VGS(th) ≥ 1.0 V minimum with on-resistance specified at VGS ≤ 2.9 V;
  - rerunning `interlock_trips.py` with the chosen parts;
  - ≥ 10 µF effective at 35 V on VIN;
  - the catch Schottky's leakage;
  - fuse coordination with the inline fuse;
  - exact prices.
- **For F6:**
  - the OVP delay and VIN overshoot;
  - the NTC-to-cell gradient, outer against inner cell;
  - chatter on a slow ramp, and the U3 voltage sweep;
  - sleep current at 3.0, 3.7 and 4.2 V;
  - the charge estimate's error;
  - M2's light-sleep listening current.

## Where the evidence is

- **Datasheets and upstream sources:** downloaded to `hardware/station-pcb/build/f1-revision/research/` (gitignored):
  - TLV3012 SBOS300C in `power/tlv3012_ti/`;
  - TPS2660x SLVSDG2G in `power/tps2660_ti/`;
  - TPS3840 SNVSB03E in `power/tps3840_ti/`;
  - LM4041-N SNOS641I in `power/lm4041_ti/`;
  - TPS7B69 in `power/tps7b69_ti/`;
  - the SMBJ table in `power/smbj_littelfuse/`;
  - the LT3652 copies in `power/lt3652_lcsc/` and `leak/lt3652-ds-lcsc/`.

  Each can be fetched again from the links in ARCHITECTURE.md § Sources.
- **PVGIS series:** `build/f1-revision/pvgis/` (gitignored), from the query in ARCHITECTURE.md § Sources. Their SHA-256 values are printed in [calc/winter_model_output.txt](../calc/winter_model_output.txt).
- **Reproducing the outputs** (from `hardware/station-pcb/`):
  - `python3 -I docs/calc/interlock_trips.py`;
  - `python3 -I docs/calc/winter_model.py r2check build/f1-revision/pvgis/ser45/series.json`;
  - the `codex` and `scenarios` commands as listed at the top of each section of the output file.
