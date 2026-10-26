# F1 revision 2: third review

Reviewed 26.10.2026 by `mobric/mikolaj-codex`, for coordinator `mobric/workspace-claude`.
Baseline: **0d038c4411b89da9e40a7ca63fd250bd06e65f84**, branch `hardware/station-pcb`.
Scope: REQUIREMENTS, ARCHITECTURE, STATUS, F1-response-r2, both calculation scripts and their outputs, compared with F1-codex-r2. Gateway source was read only to check the request contract.

**Verdict: not ready for F1 approval yet.** There is substantial progress: the comparator variant is corrected, both calculations reproduce exactly, and the proposed 8-cell energy result survives a separate recurrence check. Four architecture issues remain: interlock transition proof, surge bounds, gateway request timing, and USB source-state handling. Q22 and Q23 remain owner decisions, not approvals inferred by this review.

**Counts:** 12 R2 response rows reviewed: **6 resolved, 6 partly, 0 not resolved**. Findings below: **0 blockers, 4 major, 3 minor, 2 notes**. “Resolved” means resolved at the requirements/architecture stage; it does not approve a future schematic or replace F6 testing.

## Disposition of every R2 item

| R2 item | Verdict | Evidence and remaining work |
|---|---|---|
| R2-B1 — comparator/startup | **Partly** | Exact TLV3012B, output polarity, series-FET AND, pull resistors and steady-state corner calculation are now specified. The state table still assumes valid thresholds throughout an unregulated rail transition and ideal instantaneous inputs. See R3-M1. |
| R2-M1 — winter model and recovery | **Partly** | Schmitt thresholds, nightly reset, pessimistic adaptive loads, three SOC biases, UVLO/hibernation policy and updated azimuth are implemented. Both scripts reproduce. The energy result is conditional on those inputs; the chosen a2 service promise needs R3-M3, and thresholds must follow closure of R3-M1. Voltage-to-energy recovery mapping remains an explicit F5/F6 assumption. |
| R2-M2 — sleep bound/R-P7 | **Partly** | “High-side estimate” and the two conversion corners correctly replace the false guaranteed bound. Q22 explicitly requests approval of the relaxation. Approval is still pending, and the 3.0 V test conflicts with the new UVLO operating state: R3-m1. |
| R2-M3 — surge protection | **Partly** | SMBJ33CA has useful stand-off margin; TPS26600 adds isolation/OVP. CN3791 is no longer the selected design. The claimed dynamic bound still does not follow from the supplied specifications: R3-M2. |
| R2-M4 — CHRG power domain | **Resolved** | CHRG/FAULT have no on-board pull-up, only test points; the bench pull-up is to VIN. GPIO39 is spare and signed INA current supplies charge indication. |
| R2-M5 — dangerous VBUS test | **Resolved** | Panel and USB tests are separated; assembled-board VBUS is limited to 5.5 V. Higher-voltage USB sources are explicitly unsupported. |
| R2-m1 — PMS time/slot arithmetic | **Resolved** | 35.1 s pessimistic PMS duration is actually used; read/listen costs and skipped slots are derived in code; discretionary requests have a separate allowance. Request success probabilities still need R3-M3, rather than undoing this timing fix. |
| R2-m2 — termination/drop/capacity | **Resolved** | TIMER-to-ground C/10 selection is explicit, 110–184 mA gives approximately 11–18 mV, and unsupported capacity-loss percentage is withdrawn. These examples are conditional on net shunt current; system load and simultaneous chargers remain bench cases. |
| R2-m3 — USB current margin and source states | **Partly** | 750 ohm ±1% correctly yields 356.44–444.44 mA before extra series resistance. Bridge/interlock consumption is budgeted and combined charging is tested. Host configuration/suspend behavior is still missing: R3-M4. |
| R2-m4 — gateway availability | **Partly** | a1's reduced service is disclosed and Q23 asks the owner to choose. a2's “every request heard” claim is not established by a 120 s nominal listen period: R3-M3. |
| Longest-run defect | **Resolved** | `simulate()` now counts longest outage only inside the same complete 2005/06–2022/23 interval as the season totals. Rerun output agrees. |
| Passed checks and side remarks | **Resolved** | SHDN/ISET methods retained; translator DIR, floating-input and unpowered-V3 checks added; CHRG/test-voltage/surge/interlock checklist entries present. CH343 §5.2 correction acknowledged. RadioLib 7.8.1 flag-only ISR and air-format provisions remain unchanged; no new radio approval is implied. |

## Major findings

### R3-M1 — The interlock's transition proof exceeds the calculation's valid conditions

**Location:** ARCHITECTURE D5, especially lines 610–679; `interlock_trips.py` VREG and `cold_trips`; R-P4.

The script proves steady-state corners only for **VREG = 3.2–3.4 V**. The state table then declares the window valid at every voltage above 1.65 V because the comparison is ratiometric. Resistor ratios cancel supply scale; absolute comparator offset and hysteresis do not. The script itself divides these terms by VREG.

As a numerical sensitivity, rerunning the same corner enumeration at lower VREG gives the following cold-off safety endpoints, retaining its 0.6 K total allowance:

| VREG | Minimum cold-off cell temperature |
|---|---:|
| 3.2 V | +0.155 °C |
| 2.5 V | +0.048 °C |
| 2.0 V | −0.074 °C |
| 1.65 V | −0.204 °C |

This is **not a claim that the assembled charger necessarily operates at those corners**. It shows why the stated ratiometric argument is insufficient. The design must prove that charging cannot remain enabled there. U3 is not a specified supply-good detector: a reference voltage below nominal may still exceed the divided voltage of a low battery, so “under-biased” does not universally mean OUT3 low. Nor does a functioning U3 wait for all other inputs to settle.

The temperature inputs have 10 kohm/100 nF filters; U3 has a different 100 nF/high-resistance time constant. These states survive brownouts differently. The current script contains no capacitor or ramp state. Include fast restart, partial brownout and battery connection order as well as a slow ramp. A FET threshold is specified at a finite drain current; VGS below that threshold is not by itself a zero-current guarantee for the high-impedance solar enable path.

The [TLV3012B datasheet, §§6.9 and 9.4.5](https://www.ti.com/lit/ds/symlink/tlv3012.pdf) supports the B variant and low POR output; it does not make external networks settled at POR release. Likewise, the [LM4041-N operating-current specification](https://www.ti.com/lit/ds/symlink/lm4041-n.pdf) does not specify an external supply-good function.

**Close by:** either enforce a valid-rail/settling condition or demonstrate the existing topology over its actual rail/input/FET states, including low-battery USB operation. Bound gate leakage and delays with selected parts. Recalculate trip safety and energy corners if values change. Keep the very small +0.15/0.14 K residual margins conditional on the stated thermal-gradient, drift and leakage assumptions.

### R3-M2 — Fast-trip detection is not a hard instantaneous current ceiling

**Location:** ARCHITECTURE D5 lines 580–602, §7.2, §10; R-P1; response R2-M3.

The proof uses `I <= 1.98 A` throughout the transient and hence `dV/dt <= 0.2 V/us`. But a fast-trip threshold is crossed **before** the switch responds. [TPS2660 Rev G, §§7.5–7.6 and 9.3.5.2](https://www.ti.com/lit/ds/symlink/tps2660.pdf) gives a typical threshold expression and **250 ns typical**, not a guaranteed maximum delay or peak-current clamp. Its explanation explicitly describes terminating an already-rising peak. The 6 us OVP delay is also typical. Thus the chosen 10 us delay and 1.98 A ceiling do not establish a worst-case 36 V output. Specify MODE and include current-limit resistor tolerance as well.

The missing proof is the charge delivered to the protected capacitor: `delta V = integral(Icap dt) / Ceff`, including the initial overshoot before current regulation/turn-off. A 36 V test source cannot establish survival of the defined pulse clamped near 55 V. This does not show TPS26600 is unsuitable; it shows the claimed bound is not yet demonstrated.

The [Littelfuse SMBJ datasheet](https://www.littelfuse.com/~/media/electronics/datasheets/tvs_diodes/littelfuse_tvs_diode_smbj_datasheet.pdf.pdf) also needs more careful treatment. Its 0.097 %/K entry is a **typical breakdown-voltage coefficient**, not a guaranteed clamping-voltage temperature bound. Figure 3 derates peak pulse power/current with initial junction temperature. Applying the full 11.3 A/600 W rating at +50 °C while only increasing the clamp voltage omits that derating. Keep the helpful 33 V stand-off choice, but qualify the hot pulse amplitude and maximum clamp independently. The 36 V Zener protecting the interlock LDO likewise needs its actual tolerance and dynamic clamp at the calculated current checked in F2.

**Close by:** define source pulse, impedance/current, repetition and temperature; establish maximum charge/overshoot using defensible bounds or additional limiting; qualify TVS derating and the interlock branch. Treat a bench result as validation of a defined case, not a replacement for an unpublished worst-case specification. Correct the remaining SMBJ33A references in the block diagram/summary to the intended bidirectional SMBJ33CA.

### R3-M3 — a2 misses listen slots and budgets receipt, not response before timeout

**Location:** ARCHITECTURE §§4.3, 4.5, D13, §6.8–10, Q23; `winter_model.py:day_load`; gateway lines 1566–1592 and 1776–1802.

`min(1, 120 / listen_period)` assumes uninterrupted periodic receive opportunities. The same model explicitly removes a listen when a full read occupies its slot. In a2, a read at t=0 replaces that listen; adjacent receive windows are around t=−120 and +120 seconds, a gap of roughly four minutes. The radio is asleep during the read.

Concrete nominal M2 example: the previous receive window ends around **−111.7 s**; a gateway request starts at **−100 s** and times out at **+20 s**. The scheduled full read at t=0 transmits only around **+32.8 s**, and the next receive window begins around **+120.3 s**. Neither the scheduled report nor a requested reply meets the timeout. This remains a counterexample even though any valid scheduled report can clear the gateway's pending request.

Separately, hearing a request near the end of its 120 s retry interval leaves too little time for a new 32.8–36.3 s full read. The gateway timeout is for a **response**, not an acknowledgement of receipt. On-demand measurements can also overlap subsequent receive slots. The 40%/13% a1 values are approximations under idealized phase assumptions, not exact end-to-end service rates.

**Close by:** specify and simulate actual RX/read/TX intervals and request arrival phases, including scheduled reports, retries, mode transitions and turnaround time. Preserve the unchanged gateway. Either reserve enough receive/response opportunities or have Q23 explicitly accept quantified timeouts. Recalculate event energy and D13 pack results if the schedule changes; do not offer “all requests” as the reason to select a2 yet.

### R3-M4 — The USB budget still assumes 500 mA before the host grants it

**Location:** ARCHITECTURE D3/D5 and §7.4; R-P11; response R2-m3.

The resistor arithmetic is corrected, but “a USB 2.0 port ... supplies 500 mA” does not establish permission in every supported source state. A charger enabled by temperature/voltage alone can draw roughly 400 mA immediately after attachment, before CH343 configuration, and can continue during host suspend. Passive CC Rd resistors do not resolve the USB 2.0 configuration/suspend contract.

[USB-IF interoperability test guidance §2.2](https://www.usb.org/sites/default/files/3.2%20Interoperability%20Testing%20v0.99%20w%20USB%20Type-C.pdf) distinguishes 100 mA unconfigured, up to 500 mA configured for full-/high-speed devices, and 2.5 mA suspended. The [USB-IF compliance guidance](https://compliance.usb.org/index.asp?UpdateFile=Electrical) also requires consistency with the device's declared current demand. Merely testing CH343 leakage in suspend does not gate the parallel charger.

**Close by:** define charge behavior for attached/unconfigured/configured/suspended host states and qualifying charging sources, including descriptors/detection or an explicit source/mode restriction. Add the needed charger enable/current selection and total-current test. Retain the 750 ohm calculation; the USB power-state issue is separate from its correct tolerance margin.

## Minor findings

### R3-m1 — At 3.0 V the new UVLO turns the converter off, so the proposed deep-sleep test tests another state

**Location:** R-P6/R-P7, ARCHITECTURE §§4.2, 7.6, D5.2/D6.

TPS3840PL31 disables the converter below about 3.1 V. A whole-board test at 3.0 V therefore measures the UVLO-off state, not the 132.7 uA powered deep-sleep inventory calculated at 70% conversion efficiency. Specify separate acceptance limits for powered deep sleep above the worst-case UVLO threshold and hardware-off drain below it. If 3.0 V is a forced-on characterization, label the fixture override explicitly. Also reconcile R-P6's 3.0 V operating-headroom wording. Q22 should approve the actual states being tested. [TPS3840 datasheet](https://www.ti.com/lit/ds/symlink/tps3840.pdf).

### R3-m2 — “14 cells if M2 savings fail” is too broad for the computed fallback

**Location:** D13 recommendation/conditions, Q23, STATUS D13.

The output itself says 14 cells support today's nominal M1 cycle only when new; at 20% fade that case has an outage winter. Fixed 15-minute M1 nominal requires 17 new cells, and pessimistic M1 requires 26. Thus 14 cells are not a general fallback for failed M2 assumptions. Name the measured load/cadence for which the fallback passes, rerun that case with aging, and tie the acceptance contingency to those limits. The tables are useful and do not need to be discarded.

### R3-m3 — Combined charging is absent from the maximum battery-current arithmetic

**Location:** D5.2 charge-rate paragraph, D9 shunt dissipation, R-P9; §7.4 already requires simultaneous charging.

Both chargers may run together. Their stated maxima sum to about **2.004 A**, before subtracting load: **0.402 W** in 0.1 ohm, rather than 0.24 W; about 0.20 C on the existing 10.2 Ah pack rather than 0.15 C. D9 already selects a >=1 W shunt, so this is not evidence of an undersized selected resistor. Correct the requirement, dissipation/temperature budget and cell-rate assertion, include resistor/thermal derating, and verify the combined case. Series ISET-FET resistance can also lower the minimum USB current below the quoted bare-resistor 356 mA; state the test tolerance accordingly.

## Notes

### R3-N1 — Model results reproduce; a separate recurrence supports the 8/14-cell energy arithmetic

Executed from `hardware/station-pcb`, with output redirected outside the worktree to `/tmp/pcb-f1-r3/`:

```text
python3 -I docs/calc/interlock_trips.py
python3 -I docs/calc/winter_model.py codex build/f1-revision/pvgis/ser60/series.json
python3 -I docs/calc/winter_model.py r2check build/f1-revision/pvgis/ser45/series.json
python3 -I docs/calc/winter_model.py scenarios build/f1-revision/pvgis/ser45-az233/series.json build/f1-revision/pvgis/ser70-az233/series.json build/f1-revision/pvgis/ser45/series.json
```

**All four stdout bodies match the corresponding committed output sections byte for byte.** Script hashes match their manifests:

| Input | SHA-256 |
|---|---|
| interlock_trips.py | `3e6af8c2d9ac64c41ae414eed5840a33a3d8f333d909d8f9fc4e32d1f2bd2e42` |
| winter_model.py | `3af55752fc50d38c54f70487fcf175945eee3105b985b2bf237772a260362481` |
| PVGIS 45°, azimuth 233° | `f063b7df87bea004dde5a584718e141ba5f0c944085cf856e4cf246033a4bbcb` |
| PVGIS 70°, azimuth 233° | `bdb51b57cf608933cd00af7ce0f7ef84f9f62865b077f6d638b20108ff826919` |

A separately written hourly recurrence used the cached 45°/233° rows and the script's audited event-cost function, but did not call its `simulate`, `run_case` or `worst_case`. It applied `min(P*.01/.86*.85, 1.46*3.8)` charging, the 2.69/3.06 and 42.16/41.97 Schmitt gate reset when P=0, self-discharge, the documented SOC transitions, and PM subtraction below −10°C. It counted July 2005–June 2023 after continuous carry-in. All the following pessimistic a2 runs remain above the 3% hibernation threshold; no recovery branch was needed in this independent check.

| Pack | Minimum usable SOC: bias −15 / 0 / +15 percentage points |
|---|---|
| 8 cells new | 44.540 / 33.151 / 21.898 % |
| 8 cells, 20% faded | 40.038 / 28.573 / 16.818 % |
| 14 cells new | 56.274 / 49.887 / 43.586 % |
| 14 cells, 20% faded | 49.724 / 42.594 / 36.315 % |

This verifies the energy recurrence for the stated loads, not the request-availability assertion or real battery SOC accuracy. The three constant SOC biases are sensitivity cases; they are not a proof against every time-varying estimator error bounded by ±15 percentage points.

### R3-N2 — Self-sufficient protection and recovery remain conditional on cell and implementation data

The explicit TPS3840 cutoff and pre-radio boot check improve the recovery architecture. Mapping 3.1/3.3 V to 0/2% usable energy and voltage hibernation to 3/12% is still assumed; the scripts do not simulate voltage rebound, pulse sag or reset-loop energy. Validate those mappings against the selected cell, temperatures, supervisor tolerances and actual boot behavior. Switching off the converter leaves the documented residual battery drain; it is not a complete pack disconnect.

Similarly, the computed U3 4.29–4.43 V trip demonstrates compliance with the newly written 4.45 V requirement, not a cell-manufacturer-approved backup protection threshold. Q19 and the exact new-cell choice must close that requirement before hardware sign-off. No independent single-fault guarantee is claimed or requested here; R-P4 explicitly excludes it.

## Limits and gate recommendation

No designer file was edited, no branch switched, no firmware compiled/flashed, and no commit or push made. This review is left uncommitted. PVGIS files were checked locally, not downloaded anew. Datasheet checks used TI manufacturer documents and the cached manufacturer SMBJ/BQ25170 texts; radio's previously reviewed implementation was unchanged. No stock/pricing or hardware measurements were performed.

Close R3-M1–M4 and reconcile Q22/Q23 before presenting F1 as ready for approval. Carry the minor corrections into the response and regenerate energy results if the interlock or listen policy changes. F2 still selects exact FETs, protection values, capacitor derating and leakage limits; F6 validates the documented thermal gradient, source transients, sleep states, SOC estimator and service timing.
