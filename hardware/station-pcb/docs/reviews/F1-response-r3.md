# F1 third review response

This is the response by `mobric/mikolaj-claude-60` (called `mobric/pcb-opus-5-5` until a restart) to [F1-codex-r3.md](F1-codex-r3.md), the Codex third review of F1 revision 2 at 0d038c4. The review is committed unchanged in dacb0ba. This response was written on 26.10.2026 and committed together with F1 revision 3 of [REQUIREMENTS.md](../REQUIREMENTS.md) and [ARCHITECTURE.md](../ARCHITECTURE.md).

**Result: 7 fixed, 2 accepted, none disputed.**
- **Fixed:** R3-M1, R3-M2, R3-M3, R3-M4, R3-m1, R3-m2 and R3-m3. The revised documents now do what the review asked, or something that meets the same aim. Each row says which.
- **Accepted:** the notes R3-N1 and R3-N2. Their caveats are now in the documents.
- **Disputed:** none.

Revision 3 also folds in mobric's answers of 26.10.2026, relayed by the coordinator: 15 (snow doesn't stay on the panel), 16 (no logger this winter), 19 (the cells are Samsung INR18650-35E), 22 (agreed in principle, with any looser limit to be flagged), 23 (nobody uses the listening) and the pack size (8 cells).

Two fixes end in a question for mobric, because only mobric can make the call:
- how USB charging behaves with a computer port (Q24, from R3-M4);
- which cells to buy for the 8-cell pack (Q25, from answer 19 and R3-N2).

In the "Where" column, § and D numbers refer to ARCHITECTURE.md and R- numbers to REQUIREMENTS.md, both as revised.

## Summary

| Item | Disposition | What changed | Where |
|---|---|---|---|
| **R3-M1** The interlock's transition proof goes beyond the conditions the calculation covers | **Fixed** | A TPS3840PL30 (U4) on the interlock rail, in series with both charger chains: no charger runs unless the rail is valid. Trips recomputed down to U4's threshold and while the rail falls. Input filters reordered so a rising rail always reads "do not charge". U3's start-up claim withdrawn and replaced. FET "off" bounded by leakage. The state table now covers fast restart, brown-out, USB dropout, low battery and battery connection order | D5, D5.2, § 4.4, § 7 item 1, § 10; R-P4; [calc/interlock_trips.py](../calc/interlock_trips.py) |
| **R3-M2** The surge bound relies on typical switch timings | **Fixed** | A 5.0SMDJ28CA replaces the SMBJ33CA. The TVS alone holds the TPS26600's input, and so the LT3652's VIN, at ≤ 36.4 V during the defined surge, with pulse derating and the maximum temperature coefficient. MODE and the current-limit tolerance are specified. The interlock LDO's Zener is removed. The leftover SMBJ33A references are gone | D5, § 1, § 2, § 7 item 2, § 10; R-P1 |
| **R3-M3** a2 misses listen slots, and budgets receipt rather than a reply before the timeout | **Fixed, by removal (answer 23)** | Nobody uses the requests, so the station stops listening and the request service goes. Revision 2's "every request heard" is withdrawn. The gateway stays unchanged. All energy results are rerun without listening | § 4.3, § 4.5, D4, D13, § 6, § 7 item 5; REQUIREMENTS "Out of scope" |
| **R3-M4** The USB budget assumes 500 mA before the host grants it | **Fixed (choice asked, Q24)** | A charging jumper in the ISET chain, open by default (recommended). Open, the board fits every host state, about 1.1 mA in suspend. Fitted, it is for chargers and power banks only. Two alternatives are offered | D3, D5, § 7 item 4, § 8; R-F9, R-P11 |
| **R3-m1** At 3.0 V the UVLO is off, so the sleep test measures a different state | **Fixed (with answer 22)** | R-P7 has one limit per real state: powered at 3.7 V, powered at 3.4 V and +50 °C, hardware-off at 3.0 V. None is looser than revision 2's. R-P6's headroom wording now uses 3.05 V | § 4.2, § 7 item 6; R-P6, R-P7 |
| **R3-m2** "14 cells if the M2 savings fail" is too broad | **Fixed** | The fallback is now a measured limit: the largest charge one full read may cost with no outage, for 8 and 14 cells, new and faded, adaptive and fixed. F6 measures that charge | § 4.5, D13, § 7 item 7 |
| **R3-m3** Combined charging is missing from the battery-current arithmetic | **Fixed** | 2.0 A with both chargers, 0.40 W in the shunt, 0.20 C on 3 cells and 0.075 C on 8. USB 347–444 mA with the chain's resistance | D5, D5.2, D9, § 7 item 4; R-P9, R-P11 |
| **R3-N1** Model results reproduce; a separate recurrence supports the energy arithmetic | **Accepted** | Its caveat (constant estimate errors are sensitivity cases) is now in § 4.5's limits, with § 7 item 14 as the check. The `codex` and `r2check` sections still reproduce byte for byte | § 4.5, § 7 item 14 |
| **R3-N2** Protection and recovery stay conditional on cell and implementation data | **Accepted** | The voltage-to-energy mapping stays a stated assumption with an F6 test. U3 is described as a backstop, not a cell-maker limit, now against the 35E's data. The UVLO-off residual drain is stated | § 4.5, D5, D5.2, D13, § 7 item 9, § 9; R-P4 |

The R2 rows the review marked "partly" close through these rows:
- R2-B1 through R3-M1;
- R2-M1 through R3-M1 (the trips), R3-M3 (no listening, so no service promise) and R3-N2 (the voltage-to-energy mapping stays an explicit assumption);
- R2-M2 through R3-m1 and answer 22;
- R2-M3 through R3-M2;
- R2-m3 through R3-M4 and R3-m3;
- R2-m4 through R3-M3.

## Details

### R3-M1: fixed

- **The finding is confirmed.** Revision 2 said the window was valid at any rail voltage above 1.65 V because the comparison is ratiometric. That holds for the resistor ratios only. The comparators' offset and hysteresis are absolute, and `interlock_trips.py` itself divides them by VREG. Revision 2 also assumed settled inputs and ideal FETs.
- **A valid-rail condition (the review's first option).** A TPS3840PL30, U4, watches VREG. Its push-pull, active-low output drives a fourth FET in each chain: Q9 in the solar chain, Q10 in the ISET chain. No charger runs unless VREG is valid, whatever the comparators do. From the datasheet ([SV]):
  - off below 2.955–3.045 V, within 30 µs (tP_HL, for a step to 10 % below the threshold);
  - on above ≤ 3.17 V, after 0.29–1.05 s (CT 1 µF, internal RCT 350–650 kΩ, equations 6 and 7). Regulated VREG (≥ 3.2 V) is above the highest release, so U4 always releases once VREG regulates;
  - output held ≤ 0.2 V down to VPOR, ≤ 0.3 V. Below that every gate is at most VREG, so at most 0.3 V;
  - its timing holds for VDD slewing at ≤ 100 mV/µs. VREG rises at most 500 mA (the LDO's current limit) / 10 µF = 50 mV/µs.
  - The delay isn't part of the proof. After a short dip CT may be only partly discharged ([SV] §7.3.2), so the proof rests on the filters below.
- **Trips over the real rail.** The script now computes every corner in three VREG bands:
  - regulated, 3.2–3.4 V;
  - static down to U4's lowest threshold, 2.955 V (USB dropout);
  - falling to 2.66 V, 10 % below that threshold, where U4's 30 µs is specified. In those 30 µs VREG falls at most another 3 mV.
- **Filters reordered so a rising rail reads "do not charge".** Revision 2's 100 nF became 10 kΩ and 1 nF C0G on each input that sees V_T. U1's tap gets 20.0 kΩ and 1 nF after the node where RHYS joins; U2's tap has none.
  - U1's tap is slower than its V_T input at any temperature (25.5–28.6 µs against at most 23.2 µs), so OUT1 leans to "too cold".
  - U2's tap is faster than its V_T input (at most 14 ns against at least 9.4 µs), so OUT2 leans to "too hot".
  - This holds for any rise rate: a slow dawn, a USB plug-in, or a restart after a brown-out.
  - A falling rail leans the other way, so that error is bounded and counted. VREG has ≥ 10 µF effective and at most 1 mA of load, so it falls at most 100 V/s. The lag then shifts U1 by at most 0.030 K and U2 by 0.019 K.
- **Recomputed trips** ([calc/interlock_trips_output.txt](../calc/interlock_trips_output.txt)). RH2 moves from 3.92 to 4.02 kΩ, because the lower rail band left only 0.02 K of hot margin.
  - Nominal: +1.71 / +2.11 °C cold, +42.64 / +42.42 °C hot.
  - Safety corner, VREG falling to 2.66 V, with the NTC's self-heating, 20 nA of leakage, the falling-rail error and a 0.5 K gradient: **+0.04 °C and +44.34 °C**.
  - **The margins are now 0.04 K cold and 0.66 K hot.** The cold margin is smaller than revision 2's 0.15 K, because the band now reaches 2.66 V. It holds only with the stated gradient, drift and leakage allowances (R-P4). If F2's parts or F6's gradient come out worse, the cold tap moves up, at the cost of charging hours.
  - Energy corner for the winter model: +2.71 / +3.09 °C and +41.52 / +41.33 °C (revision 2: +2.69 / +3.06 °C, regulated rail only). The model is rerun with it.
- **U3, battery overvoltage.** Revision 2's claim that an under-biased U3 reads "overvoltage" is withdrawn: the review is right that a low reference doesn't force OUT3 low. Instead:
  - U4 keeps both chains open until VREG is valid. The LM4041-B's feed is now 24.3 kΩ, giving 70 µA at 2.955 V, above its 65 µA minimum. So U3's reference is in regulation whenever U4 lets a chain close.
  - At night Q8 is off, so IN− sits at the cell voltage, which reads "overvoltage". At power-up IN− falls to its divided value with τ = 21.6 ms. That is the safe direction.
  - **One exception remains:** connecting the battery while the interlock is powered. IN− then rises from 0 V, and for about 0.1 s U3 can't see an overcharged battery. Only the chargers' own float limits the voltage then. This is stated in D5 and R-P4, and tested (§ 7 item 1).
- **"Off" bounded by leakage, not by a threshold.** F2 requirements:
  - every chain FET leaks ≤ 1 µA at VGS ≤ 0.3 V, VDS 40 V and 55 °C;
  - an open solar chain then holds Q3's VGS at ≤ 0.1 V (1 µA on 100 kΩ). Q3's own ≤ 1 µA into the ≤ 100 kΩ lower SHDN resistor is ≤ 0.1 V, far below SHDN's 1.15 V;
  - an open ISET chain leaks ≤ 1 µA. The BQ25170 publishes no ISET voltage, so F6 measures the charge current with the chain open, with a limit of 1 mA;
  - VGS(th) 1.0–2.0 V, and ≤ 5 Ω at VGS 2.65 V, the drive at U4's lowest threshold. "2N7002" stays a placeholder only.
- **The state table** now has a row for each case the review named: VREG below 0.3 V, below U4's release, during U4's delay, valid, falling, a fast restart, a panel brown-out, USB dropout, USB with the cells too low for the converter, USB plug and unplug, both sources, battery absent, and the battery connected while powered.
- **Bench tests** (§ 7 item 1): dip VREG through U4's threshold slowly and fast, restart within milliseconds, hold it in the dropout band, connect the battery in both orders, and log VREG, U4, OUT1–OUT3, SHDN and the ISET chain throughout.

### R3-M2: fixed

- **The finding is confirmed.** The TPS2660's 250 ns fast-trip and 6 µs OVP delays are typical figures, and the fast-trip ends a peak that is already rising. Revision 2's ≤ 1.98 A ceiling and the 36 V bound that followed from it weren't established.
- **The bound no longer depends on the switch.** A **5.0SMDJ28CA** (Littelfuse, bidirectional, 5 kW at 10/1000 µs, SMC; datasheet [SD]) holds the TPS26600's input:
  - stand-off 28 V at ≤ 5 µA;
  - breakdown 31.1–34.4 V at 1 mA, with a **maximum** temperature coefficient of 0.094 %/°C (the SMBJ's 0.097 %/K was typical, as the review noted);
  - clamp ≤ 45.4 V at 110 A.
  - At −30 °C the breakdown is still ≥ 29.4 V, above the cold Voc of about 28 V.
- **The defined surge** (R-P1, assumed definition): a 10/1000 µs pulse of up to 11.3 A peak, either polarity, at most once a minute, with the board between −30 and +50 °C. The panel cable is under 1 m, on the station's own mast. A direct strike is out of scope.
- **Clamp at that pulse.** The straight line between the datasheet's two points (34.4 V at 1 mA, 45.4 V at 110 A) gives 35.5 V at 11.3 A. That assumes the real curve lies under the line, as a TVS curve does; F2 checks it against Littelfuse's curve. From a +50 °C start, with both points raised by the maximum coefficient (+2.35 %): **≤ 36.4 V**.
- **Derating, treated separately (as asked).** The pulse rating falls to about 83 % at a +50 °C start ([SD] Fig. 3), about 92 A. The defined 11.3 A is 12 % of that. Once a minute is a duty cycle of about 0.002 %, inside the datasheet's 0.01 %.
- **No charge integral is needed.** The switch can't raise its output above its input, so VIN ≤ IN ≤ 36.4 V whatever the switch does and whatever the capacitance. That is below the LT3652's 40 V and the TPS26600's 62 V absolute maxima. For the pulse's 1 ms or so VIN may exceed the LT3652's 32 V operating range, which the absolute maximum allows.
- **MODE and the current limit.** MODE is shorted to RTN: active current limiting with auto-retry ([TP] Table 1). R(ILIM) 12 kΩ ± 1 % gives 0.94–1.06 A. Neither is part of the surge bound.
- **The interlock branch.** The TPS7B6933 is fed from IN, which stays ≤ 36.4 V, inside its 40 V operating range. So revision 2's 36 V Zener, whose tolerance the review questioned, is removed.
- **Rejected:** the SMBJ33CA (its 53.3 V clamp needed the switch's timing) and TI's TVS3300 (unidirectional, 4 A at 10/1000 µs).
- **The SMBJ33A references** in the block diagram and summary are gone. The SMBJ remains only as the rejected part and its source entry.
- **Tests** (§ 7 item 2): the defined pulse in both polarities, IN and VIN ≤ 36.4 V. As the review says, that validates one case; it doesn't replace the datasheet bound. Revision 2's 36 V test source and OVP-delay test are dropped. OVP tests use a current-limited supply, because the TVS may conduct from 31.1 V.

### R3-M3: fixed, by removal (answer 23)

- **The finding is confirmed.** `min(1, 120 / period)` assumed uninterrupted receive slots, while the model itself removed the slot a read occupies. The review's counterexample (a request at −100 s, a timeout at +20 s, the report at +32.8 s) holds.
- **mobric's answer 23: "nobody uses the listening".** Before acting on it, revision 3 checked what the listening serves:
  - **(a) What triggers a request.** Only a person at the gateway: its BOOT button (`handleButton`, firmware/gateway/gateway.ino lines 1645–1658) or `r` / `R` on its serial console (lines 1763–1773). Both call `sendDataRequest` (lines 1572–1582), the only place that sets `requestPending`. Nothing sends a request at start-up, after a missed frame or after a timeout. The gateway sends no ACKs.
  - **(b) What else the station's receiver does.** Nothing. The station receives only in `checkForRequest` and `listenForRequest` (firmware/station/station.ino lines 518–555), which accept nothing but `AA 55 01`. `doListenCheck` (lines 759–785) is never called. There is no configuration or OTA over the radio.
- **So the listen windows go,** and the request service with them. Revision 2's "every request heard" is withdrawn. No service rate is claimed, so no request-phase simulation is needed.
- **The gateway stays unchanged.** A button press times out there after 120 s (lines 1779–1783). It still decodes and uploads every valid frame (lines 1785–1817). F6 checks that the next scheduled frame still arrives after a timed-out request (§ 7 item 5).
- **The PRD's Phase 3 LoRa ACK** (docs/prd-tech-design.md lines 546–552) isn't part of this design, because it needs a gateway change. As a sensitivity the model adds a 2 s receive window after each report: every pack-table entry moves by at most 0.2 days and 1 percentage point.
- **Energy and D13 are recalculated**, as the review asked. Dropping the listening halves M1's consumption at 15-min reads (368 → 185 mAh/day nominal) and lowers M2's pessimistic survival day from 12.7 to 10.1 mAh. Revision 2's (a1) and (a2) become one option, (a). The listening profiles stay only as comparison rows.

### R3-M4: fixed (choice asked, Q24)

- **The finding is confirmed.** A USB 2.0 host allows 100 mA before configuration, up to 500 mA once configured, and 2.5 mA in suspend ([US], cited by the review). A charger gated only by temperature and voltage would draw about 400 mA from attachment and through suspend. The 5.1 kΩ on CC doesn't change that.
- **Recommended, Q24 (a): a charging jumper in the ISET chain, open by default.**
  - Open, USB charging is off. The board draws only the bridge and the interlock: ≤ 0.16 mA for the CH343P in suspend, ≤ 0.2 mA for its VBUS pull-down and 0.72 mA for the interlock, about **1.1 mA in suspend**, under the 2.5 mA allowed. Before configuration it draws ≤ 17 mA, under 100 mA.
  - Fitted, it is for USB chargers and power banks only, never for a computer port.
  - Cost: a 2-pin header and a shunt.
- **Alternatives for mobric:**
  - (b) charge automatically only from a USB-C source that advertises 1.5 A or 3 A on CC: two comparators on the CC voltage against about 0.66 V, about 8–10 more parts. USB-A chargers and A-to-C cables advertise only default power, so they would give data but no charging;
  - (c) no USB charging: remove the BQ25170 and its chain.
- **The CH343P's ACT# can't gate the charger.** Its datasheet says it signals a completed configuration, not what it does in suspend.
- **Tests** (§ 7 item 4): VBUS current with the jumper open in the five R-F9 states (absent, attached but not configured, configured, suspended, battery absent); with it fitted, 347–444 mA from a charger and ≤ 461 mA in total.
- The 750 Ω calculation stays, as the review advised.

### R3-m1: fixed (with answer 22)

- **The finding is confirmed.** At 3.0 V the TPS3840 holds the converter off, so revision 2's 150 µA test measured the hardware-off state.
- **R-P7 now has one limit per real state** (mobric agreed in principle, answer 22):
  - (a) powered deep sleep, 3.7 V, 25 °C: **≤ 100 µA**. Estimate 52.8 µA typical, 97.4 µA high-side;
  - (b) powered deep sleep, 3.4 V, +50 °C: **≤ 136 µA**. 3.4 V is above the UVLO's highest release (3.37 V), so the converter runs whatever the history. Estimate 120.2 µA high-side plus up to 5 µA from a hot catch diode;
  - (c) hardware-off, 3.0 V, +50 °C: **≤ 35 µA**. 3.0 V is below the UVLO's lowest threshold (3.05 V). Estimate 21.3 µA high-side plus the diode's 5 µA.
  - No fixture override is needed in any state.
- **None is looser than revision 2's 100 / 150 µA**, which mobric asked to be told about. (a) is unchanged. (b) leaves 7.8 µA of headroom on the 3.3 V rail, the same as 150 µA at 3.0 V did, and 10.8 µA on the battery side, against 12.3 µA before. 138 µA would have been up to 2 µA looser, so 136 µA is used. (c) is a new state, far below 150 µA.
- **R-P6** now reads "≥ 500 mA available down to 3.05 V at the pack", the UVLO's lowest threshold. The converter's datasheet rates 1.5 A for an input ≥ 2.7 V ([T1] p.1).
- **The winter model** keeps the 3.0 V / 70 % high-side floor, 138.7 µA on the cells, for every pessimistic case. A new sensitivity sets the floor at R-P7 (b)'s limit, 156 µA on the cells: 8 faded cells still reach 48 / 35 / 27 % at the lowest, with no outage.

### R3-m2: fixed

- **The finding is confirmed.** In revision 2, 14 cells didn't cover every failed-M2 case.
- **The fallback is now named by a measurable limit:** the largest charge one full read with PM may cost at the battery, with no outage hour in any of the 18 winters. Conditions: the energy corner, the estimate off by up to 15 %, the pessimistic floor, and the PMS7003's own 1.464 mAh per read, with the rest of every read scaled alike.

| Pack | Adaptive (reads every 15 / 30 / 60 min) | Fixed 15 min |
|---|---|---|
| 8 cells, 26.80 Ah | 4.79 mAh | 2.17 mAh |
| **8 cells, 20 % faded, 21.44 Ah** | **3.99 mAh** | 1.86 mAh |
| 14 cells, 46.90 Ah | 7.80 mAh | 3.33 mAh |
| 14 cells, 20 % faded, 37.52 Ah | 6.39 mAh | 2.79 mAh |

- For comparison, a pessimistic full read costs 1.78 mAh in M2 and 2.79 mAh in M1. With the sleep floor at R-P7 (b)'s limit, the 8- and 14-cell faded limits become 3.98 and 6.38 mAh.
- **So 8 faded cells on the adaptive schedule carry even M1's pessimistic read.** Without the adaptive switching they don't: M1 on fixed 15-min reads needs 12 cells new and 15 faded.
- **The review's 17 and 26 cells** were for M1 with 1-min listening. Without listening (answer 23) the fixed 15-min M1 cases need 7 (9 faded) and 12 (15 faded) cells. The listening rows stay in § 4.5 as comparison rows.
- **The acceptance contingency** is tied to these limits. F6 measures the charge of one full read with PM against 3.99 mAh (§ 7 item 7). If it is higher, 14 cells allow up to 6.39 mAh when faded.

### R3-m3: fixed

- **Both chargers at once:** at most 1.56 A + 0.444 A = **2.0 A** into the cells, before the load is subtracted.
- **Shunt:** 0.40 W continuous, against revision 2's 0.24 W. D9's 2512 part rated ≥ 1 W runs at 40 % of its rating. F2 checks the chosen part's derating curve at the board's +50 °C plus the shunt's own rise (R-E1, R-P9). R-P9 now states 0.40 W.
- **Cell rate:** 0.67 A per cell (0.20 C) on today's 3 cells, 0.25 A per cell (0.075 C) on 8. The 35E allows 1.5 A per cell from 0 to 45 °C ([35E]).
- **USB current with the chain's resistance:** the ISET chain adds at most 20 Ω (four FETs at ≤ 5 Ω), so the range is **347–444 mA**, not the bare resistor's 356–444 mA. F6's acceptance window is 347–444 mA (R-P11).
- **Test:** panel and USB charging together, with the cell current, the shunt's temperature and termination under load (§ 7 item 4).

### R3-N1: accepted

- Thanks for the independent recurrence. It confirms the energy arithmetic for the loads it used (revision 2's a2, with listening). Revision 3's loads have no listening and its trips are new, so its own figures differ: 8 faded cells reach 48 / 35 / 27 %.
- **Its caveat is now in the documents.** § 4.5's list of what the model can't see now includes an estimate error that changes over time. The three constant errors are sensitivity cases, not proof against every error that wanders within ±15 %. F6 compares the estimate with counted charge (§ 7 item 14).
- **Reproduction.** In revision 3, both scripts changed, so their hashes changed (below). The `codex` and `r2check` sections of the output are still byte-identical to those at 0d038c4. The `scenarios` section changes, because the schedules, the trips and the cell capacity changed.

### R3-N2: accepted

- **The voltage-to-energy mapping** (UVLO at 0 / 2 %, hibernation at 3 / 12 %) stays an explicit assumption. It is listed in § 4.5, D13 and § 9, and F6 ramps the battery through the UVLO and checks that the boot check sends the ESP32 back to hibernation (§ 7 item 9).
- **The UVLO isn't a disconnect.** With the converter off, the cells still lose 15.6–27.3 µA plus self-discharge (D5.2, § 4.2).
- **U3 against the 35E (answer 19).** Samsung's specification charges the 35E to 4.20 V and gives no overcharge threshold ([35E]). U3's 4.29–4.43 V is a backstop against a failed charger, not a limit approved by the cell maker. For comparison, the DW01A protection IC trips at 4.25–4.35 V. F2 checks the trip against Samsung's formal specification (R-P4).
- **The cells:** answer 19 names the model; which cells to buy is Q25. No single-fault guarantee is claimed (R-P4).

## Changes beyond the review

- **mobric's answers of 26.10.2026** are folded in (§ 8):
  - **15:** snow doesn't stay on the panel. The model's lack of a snow loss stands, and snow is no longer a D13 condition;
  - **16:** no logger this winter. D13 (c) stays unmodelled; the DNP heater footprint stays, and the board's own DS18B20 logs the pack temperature in its first winter (§ 6 item 13);
  - **19:** the cells are Samsung INR18650-35E;
  - **22:** R-P7 restated by state (R3-m1), none looser;
  - **23:** no listening (R3-M3);
  - **8 cells (1S8P)** as the D13 recommendation, with the 3- and 14-cell rows kept for comparison.
- **mobric's condition on 8 cells:** "If the rerun shows 8 cells failing anywhere at the pessimistic, faded corner, tell me before writing it in."
  - **8 faded cells pass every modelled case on the adaptive schedule,** at pessimistic loads and the energy corner, with the estimate 15 % low, exact or 15 % high. The lowest charge is 27 %, and the review's +1 / +4 °C sensitivity passes too (lowest 18 %). So 8 cells are written in.
  - **On fixed 15-min reads, 8 faded cells still fail some cases**, as in revision 2: M2 pessimistic fails only the +1 / +4 °C sensitivity (31 days in 1 winter), and M1 pessimistic fails every row except revision 1's gate (17–70 days in 1 winter). § 4.5 and D13 say so: the 8 cells rely on the adaptive schedule.
- **The pack table** (D13, § 4.5): M2 adaptive with pessimistic loads, at the energy corner, 35E cells at their 3.35 Ah minimum. Three figures per entry: estimate 15 % low / exact / 15 % high.

| Pack | Outage hours | Lowest charge | Lean days per winter | Survival days per winter |
|---|---|---|---|---|
| 3 cells, 10.05 Ah (today) | none | 43 / 27 / 14 % | 23.9 / 14.8 / 8.9 | 5.4 / 3.7 / 2.9 |
| 3 cells, 20 % faded | none | 41 / 28 / 14 % | 25.9 / 17.4 / 11.3 | 8.4 / 5.5 / 4.3 |
| **8 cells, 26.80 Ah** | none | 50 / 42 / 36 % | 10.4 / 5.0 / 2.5 | 0.1 / 0.0 / 0.0 |
| **8 cells, 20 % faded** | none | 48 / 35 / 27 % | 13.5 / 6.6 / 4.4 | 1.0 / 0.1 / 0.0 |
| 14 cells, 46.90 Ah | none | 64 / 58 / 54 % | 4.9 / 2.4 / 0.0 | 0.0 / 0.0 / 0.0 |
| 14 cells, 20 % faded | none | 59 / 53 / 45 % | 6.4 / 3.4 / 0.1 | 0.0 / 0.0 / 0.0 |

- **The 35E's data** ([35E]) replace revision 2's assumed 3.4 Ah cells: 3350 mAh minimum, 4.20 V at ≤ 1.5 A, 2.50 V cut-off, charge 0–45 °C, discharge −10 to +60 °C. Its mean discharge voltage is 3.62 V, so the model's 3.7 V overstates the energy by about 2 % (§ 9). It gives no self-discharge figure, so the model's 2 %/month stays assumed. The air is below its −10 °C discharge limit for about 152 hours in an average winter (§ 4.4, D13).
- **The pack:** 8 cells as 2 × 4, about 80 × 42 × 68 mm and ≤ 0.40 kg, with a fuse at the pack and new matched cells from one batch (D13, D11).
- **`winter_model.py`:** no listening in the recommended profiles; the new energy corner; 35E capacity; the read-cost limit search (R3-m2); the 2 s ACK sensitivity; the sleep floor at R-P7's limit. A stale comment about the UVLO thresholds is corrected.
- **`interlock_trips.py`:** three VREG bands, the filter time constants, the falling-rail lag and RH2 4.02 kΩ.
- **D12's estimate** grows to about $285–305 for 5 boards (assumed; the new parts aren't priced yet).
- **STATUS.md:** Phase, the D3, D5, D5.2, D12 and D13 rows, the open questions and the "Now" cells.

## Still open

- **For mobric** (ARCHITECTURE.md § 8):
  - **Q24, USB charging and a computer's power rules.** (a) a charging jumper, open by default: no USB charging from a computer, which suits every port, and charging from a charger or power bank with the jumper fitted (recommended); (b) charge automatically, but only from USB-C chargers that announce 1.5 A or more, at about 8–10 more parts; (c) no USB charging at all;
  - **Q25, which cells for the 8-cell pack.** (a) 8 new, genuine Samsung INR18650-35E from one batch, bought from an authorised distributor (recommended); (b) another 18650 model with a datasheet and at least 3.35 Ah, rechecked in F2; (c) today's three cells plus five new ones (not recommended: their age and state are unknown);
  - approving D2–D4 and D6–D14 at the F1 gate, and installing KiCad 9.0.x (R1).
- **For F2:**
  - chain FETs: VGS(th) 1.0–2.0 V, ≤ 5 Ω at VGS 2.65 V, ≤ 1 µA at VGS ≤ 0.3 V, 40 V and 55 °C;
  - ≥ 10 µF effective on VREG; ≤ 20 nA total leakage at V_T;
  - Littelfuse's clamp curve for the 5.0SMDJ28CA at 11.3 A;
  - the shunt's derating curve; fuse coordination with the inline fuse;
  - U3's trip and the 35E's small-current limit below −10 °C against Samsung's formal specification;
  - rerunning `interlock_trips.py` with the chosen parts; exact prices.
- **For F5:** the firmware items in § 6, including the adaptive schedule, the removal of the listen windows, and the boot check after a UVLO restart.
- **For F6:** the rail dips, restart and battery connection order; the defined pulse; the five USB states and combined charging; sleep current in the three R-P7 states; the charge of one full read against 3.99 mAh; the outer-to-inner cell gradient; the charge estimate; the UVLO ramp.

## Where the evidence is

- **Datasheets:** downloaded to `hardware/station-pcb/build/f1-revision/research/` (gitignored), each in its own directory:
  - 5.0SMDJ in `power/smdj5_littelfuse/`; TVS3300 in `power/tvs3300_ti/`;
  - TPS3840 SNVSB03E in `power/tps3840_ti/`; TPS2660x in `power/tps2660_ti/`;
  - Samsung INR18650-35E in `power/samsung_35e/`; BQ25170 in `power/bq25170_ti/`;
  - TLV3012, LM4041 and TPS7B69 in `power/tlv3012_ti/`, `power/lm4041_ti/` and `power/tps7b69_ti/`;
  - TPS631000, CH343 and DW01A in `leak/tps631000-ds/`, `leak/ch343-ds/` and `leak/dw01a-ds/`.

  Each can be fetched again from the links in ARCHITECTURE.md § Sources. The USB-IF guidance [US] is cited by the review and wasn't re-read here.
- **Firmware, read only:** `firmware/gateway/gateway.ino`, `firmware/station/station.ino` and `docs/prd-tech-design.md`, at 82ee40d. Nothing was compiled or flashed.
- **PVGIS series:** `build/f1-revision/pvgis/` (gitignored), unchanged. Their SHA-256 values are printed in [calc/winter_model_output.txt](../calc/winter_model_output.txt).
- **Script hashes (SHA-256):** `winter_model.py` 054c8a9ca0c7c9f6feb99f3a608c06a877125345498e2252c761013e8e9ebb9d; `interlock_trips.py` 59f980f8ab429a2a09fee318da387264c72b40343845e251606fcaf463546365.
- **Reproducing the outputs** (from `hardware/station-pcb/`):
  - `python3 -I docs/calc/interlock_trips.py`;
  - `python3 -I docs/calc/winter_model.py codex build/f1-revision/pvgis/ser60/series.json`;
  - `python3 -I docs/calc/winter_model.py r2check build/f1-revision/pvgis/ser45/series.json`;
  - `python3 -I docs/calc/winter_model.py scenarios build/f1-revision/pvgis/ser45-az233/series.json build/f1-revision/pvgis/ser70-az233/series.json build/f1-revision/pvgis/ser45/series.json`.
