# F1 revision 3: fourth review

Reviewed 26.10.2026 by `mobric/mikolaj-codex`, for `mobric/workspace-claude`.
Baseline: **8e02e7758ee15e6fea4f69c98445608a8860a9ea**, branch `hardware/station-pcb`.
Compared REQUIREMENTS, ARCHITECTURE, STATUS, F1-response-r3 and both calculation scripts/outputs with F1-codex-r3 at 0d038c4. Firmware was inspected read-only.

**Verdict: not ready for mobric's F1 gate.** The energy results reproduce, removing listening resolves the request-service problem, and the default-open charging jumper resolves the USB source-state architecture. Two important proofs remain incomplete: the interlock calculation treats two coupled filters as independent, and the TVS's two tabulated points do not guarantee the interpolated clamp limit.

**Counts:** R3 items: **6 resolved, 3 partly, 0 not resolved**. The six previously-partly R2 rows: **3 resolved, 3 partly, 0 not resolved**. Findings: **0 blockers, 2 major, 2 minor, 3 notes**. Resolution is at architecture level, not a schematic or hardware approval.

## Decisions applied, without reopening them

Snow does not stay on the panel; no logger this winter; Samsung INR18650-35E; 8 cells in parallel; listening/request service removed; gateway unchanged; R-P7 stated by actual state. The coordinator additionally confirmed **Q24(a), charging jumper open by default**, and **Q25(a), eight new genuine 35E cells from one batch**, after this commit. Their still-open labels in the baseline are not findings. No request to change these decisions is made here.

## Disposition of every R3 item

| Item | Verdict | Evidence / remaining work |
|---|---|---|
| R3-M1 — interlock transitions | **Partly** | U4 is a useful valid-rail condition; wider voltage corners, explicit FET leakage and connection-order exception improve the design. The new filter-ordering proof is incorrect for the stated shared NTC node. R4-M1. |
| R3-M2 — surge bound | **Partly** | Defined pulse, larger TVS, separate temperature derating and specified eFuse MODE remove several ambiguities. The 36.4 V ceiling is still an assumed interpolation, not a guaranteed bound. R4-M2. |
| R3-M3 — request timing | **Resolved** | Owner-authorized removal is consistently applied to the recommended schedules, D4/D13, F5 work and F6 checks. Legacy listening/ACK rows are labelled comparisons or sensitivities. Gateway source supports the removal without changing its reporting path. |
| R3-M4 — USB host states | **Resolved** | Approved default-open jumper prevents host charging independently of enumeration/suspend. Fitted-jumper operation is restricted to appropriate chargers/power banks. The quoted suspend budget needs a correction, R4-m1; the architecture does not depend on achieving exactly 1.1 mA. |
| R3-m1 — actual sleep states | **Resolved** | 3.7 V powered, 3.4 V powered and 3.0 V hardware-off are now distinct acceptance cases. Threshold arithmetic supports their state selection. Qualification of “none looser” is in R4-N1. |
| R3-m2 — fallback | **Resolved** | Named, conditional read-cost limits replace the blanket 14-cell claim. Rerun and direct boundary checks pass at 3.99/6.39 mAh under the defined scaling model. These are not universal limits for arbitrary distributions of read energy: R4-N2. |
| R3-m3 — combined charging | **Resolved** | Approximately 2 A combined, 0.40 W shunt dissipation, per-cell rate and 347–444 mA USB range are carried through. The >=1 W shunt and derating check remain appropriate. |
| R3-N1 — reproduction/estimator caveat | **Resolved** | Both scripts reproduce their outputs; codex/r2check remain byte-identical to 0d038c4. Time-varying estimator error is explicitly excluded from the constant-bias proof. Independent pack recurrence agrees. |
| R3-N2 — cell/protection/recovery evidence | **Partly** | Recovery mapping, residual drain and the absence of a manufacturer-approved U3 threshold are candidly stated. The tentative cell source can now be replaced by a fuller specification; U3 qualification and cold-cell operation remain open. R4-m2/R4-N3. |

## Disposition of the six still-partly R2 rows

| Item | Verdict | Reason |
|---|---|---|
| R2-B1 | **Partly** | Exact devices and control polarity are specified, but R4-M1 prevents closure of the transition proof. |
| R2-M1 | **Partly** | The winter calculation, updated trips, adaptive pessimistic loads, three SOC biases and recovery policy are implemented. Final hardware-derived gate thresholds still depend on R4-M1; cell/recovery assumptions remain explicit. |
| R2-M2 | **Resolved** | Estimates are not called guaranteed bounds; acceptance is separated by actual state. R4-N1 records the comparison of limits requested by the owner. |
| R2-M3 | **Partly** | Selected TVS protection still needs a defensible worst-case clamp envelope, R4-M2. |
| R2-m3 | **Resolved** | Charging jumper decision, current tolerance, combined-current arithmetic and host-state tests address the original architecture issues. Correct the residual suspend inventory in R4-m1. |
| R2-m4 | **Resolved** | The owner removed this service; no availability guarantee or gateway modification is required. |

## Major findings

### R4-M1 — Two capacitors on the common NTC node invalidate the independent-filter ordering proof

**Location:** ARCHITECTURE D5 input filters/state table (lines 633–637, 710–717); `interlock_trips.py:filter_check`; R-P4.

The specified circuit has **two** branches from V_T, each a 10 kohm resistor followed by 1 nF to ground. The code computes each branch as if it alone loaded `RS || NTC`: `(R_IN + Rth) C`. In the equal-component common-mode case both capacitors charge together, so the shared source resistance carries both branch currents. The transfer to either input has:

```text
tau_NTC = (R_IN + 2 Rth) C,  Rth = RS || R_NTC
```

At 0 °C with the script's nominal NTC, Rth = 8.731 kohm and **tau_NTC = 27.462 us**. The nominal U1 reference tap is **27.069 us**, so the alleged ordering is already reversed. At 2 °C tau_NTC is 26.971 us, nearly equal to the reference; tolerances matter. The conservative open-NTC common-mode maximum is **35.85 us**, not 23.2 us. With unequal capacitors/resistors it is a coupled two-state network, not two independent one-pole filters. This also changes U2's falling-rail lag.

Consequently the script's `yes` and “any rise rate” conclusion do not prove the actual circuit. U4's full-reset delay may protect many startups, but the document explicitly declines to rely on that delay after short dips. It must therefore analyze the real network during those dips, including retained capacitor voltages. This is a proof failure, **not a claim that every startup charges a cold cell**.

The reported **+0.04 K** is honestly labelled conditional and is reproducible: the current formula gives **+0.0410169 °C**, hot endpoint **44.3381 °C**. It is not yet a valid bound for the described coupled circuit. Recalculate both polarities of dynamic error and both safety/energy endpoints; do not simply add another arbitrary allowance.

U4's PL30 thresholds and delay arithmetic agree with the [TPS3840 Rev E tables](https://www.ti.com/lit/ds/symlink/tps3840.pdf). Its 30 us detection specification is for a specified input excursion and output load. The proof must continue through the **100 kohm gate resistors, actual gate capacitances, Q3 and charger-disable response**. The existing calculation reaches 2.6595 V, then describes another 3 mV of rail fall without including that lower endpoint in the corner sweep. Close this complete delay budget with selected parts. Also derive FET on-drive from guaranteed output VOH and source voltage, rather than equating the supervisor output to VREG.

The new off-leakage requirements are a substantial improvement: the 1 uA × 100 kohm = 0.1 V DC argument is valid subject to actual topology, body-diode orientation and component leakage limits. It does not replace the transient proof. Correct the state-table row that says Q9 is on **during** U4's delay: an active-low reset holds that gate off until release.

**Close by:** solve the coupled network or change its isolation/settling strategy, cover partial dips/restarts, and establish the complete inhibit latency. Re-run both scripts if the usable temperature window changes. No selected part is rejected solely because the remaining margin is small.

### R4-M2 — Interpolating between breakdown and clamp ratings does not establish a maximum clamp curve

**Location:** ARCHITECTURE D5 lines 592–605, R-P1, STATUS D5; F1-response-r3 R3-M2.

The numerical interpolation is correct: it gives **36.3649 V** after the stated temperature factor. Its premise is not established. Two maximum-voltage points do not imply that every intervening point lies below their straight chord. A nonlinear avalanche knee need not have the assumed curvature. The supplied [Littelfuse 5.0SMDJ datasheet](https://www.farnell.com/datasheets/3765771.pdf) supplies the 34.4 V breakdown and 45.4 V clamp entries, but no guaranteed 11.3 A upper-envelope curve proving 36.4 V. Its maximum coefficient is specifically for **VBR**, not a guaranteed temperature coefficient for the entire VC/current curve or a bound on pulse self-heating.

The 5 kW part has ample pulse-rating headroom for the stated 11.3 A waveform after the approximately 83% hot derating; this corrects the earlier pulse-capacity problem. That headroom does not prove the voltage ceiling.

An independently guaranteed input clamp below the protected limits could remove reliance on the eFuse's current integral. However `VIN(t) <= IN(t)` is not universally true: stored output charge can hold VIN above a falling IN, and real wiring/package inductance needs an overshoot allowance. Use a maximum-voltage/energy argument for the actual network, rather than the stated instantaneous inequality “whatever the capacitance.” The removal of the LDO Zener currently rests on the same unproven input bound. Check both input branches and isolation-diode reverse ratings under the negative pulse as well.

Cold arithmetic also needs accurate wording: `31.1*(1-.00094*55) = 29.492 V`, above the computed **28.0476 V** cold Voc. This supports absence of strong breakdown; it does **not** extend the guaranteed 5 uA stand-off leakage from 28.0 V to 28.0476 V at arbitrary temperature.

**Close by:** obtain a manufacturer-supported worst-case clamp envelope at the defined current/temperature/pulse, or add protection whose bound does not depend on that interpolation. Include layout overshoot and cold leakage. Keep the pulse definition, MODE selection and current-limit tolerance. A typical curve or a successful single bench pulse is useful evidence, but should not be relabelled a production worst-case limit.

## Minor findings

### R4-m1 — The open-jumper suspend inventory omits the powered BQ25170

**Location:** D3 line 531, D5 lines 734–736, response R3-M4.

Opening ISET stops charging; it does not disconnect the charger's IN pin. The [BQ25170 datasheet §6.5 and §7.3.1.1](https://www.ti.com/lit/ds/symlink/bq25170.pdf), also checked in the cached manufacturer PDF, distinguishes TS shutdown from charge-enabled zero-current operation. The latter has **0.6 mA maximum IQ_IN** at its stated test condition. Do not assume the 80/110 uA TS-shutdown figure applies to an open ISET. The interlock's 0.72 mA output-load calculation also omits its LDO input quiescent current from the USB sum.

Allowing 0.6 mA plus 25 uA LDO IQ raises the displayed `0.16 + 0.20 + 0.72 = 1.08 mA` subtotal to about **1.705 mA**, before remaining translator/ESD/logic allowances. This still leaves plausible room below 2.5 mA; it is not evidence that the approved jumper scheme fails. Budget the exact open-ISET state, both translators and remaining VBUS loads, then validate the complete-board suspend current. Likewise retain charger bias in the fitted-jumper total-current inventory.

### R4-m2 — Replace tentative 35E ratings with an identified product specification

**Location:** ARCHITECTURE §4.1, D13, §9 and source [35E]; response R3-N2.

A manufacturer-authored **INR18650-35E specification Ver. 1.1** is retrievable from [BTO](https://www.bto.pl/pdf/08097/INR18650-35E.pdf), with a fuller copy at [Telit Power](https://docs.telitpower.com/pdf/li-ion/INR18650-35E.pdf). It retains 3350 mAh minimum, 4.2 V charge and 0–45/−10–60 °C charge/discharge temperatures, but specifies **2.65 V discharge cutoff**, **2 A maximum charge current** and **18.55 mm maximum diameter**, differing from the tentative report used here. Verify applicability to the purchased batch and update provenance/affected figures. This does not reopen Q25(a); the conservative present per-cell current and UVLO remain comfortably inside those revised numerical limits.

## Notes and verification

### R4-N1 — R-P7 comparison: actual-state limits pass, but “none looser” has a model-dependent meaning

PL31 arithmetic gives a maximum release of `3.1*1.015 + .225 = 3.3715 V` and minimum falling threshold `3.1*.985 = 3.0535 V`. Thus 3.4 V selects powered operation and 3.0 V hardware-off without a fixture override. The same-state 3.7 V/25 °C limit stays 100 uA; the actual 3.0 V/+50 °C limit tightens from 150 to 35 uA.

For the new powered corner, the stated **70% conversion/headroom model** makes 136 uA at 3.4 V approximately equivalent to the old hypothetical powered 150 uA at 3.0 V, and does not increase the allocated rail-load headroom. It is not a model-independent energy equivalence: **136 uA × 3.4 V = 462.4 uW**, versus **150 uA × 3.0 V = 450 uW**, a **2.76% higher terminal-power ceiling**. Flag this distinction as requested by Q22. There is no looser measured current limit at either unchanged test point; the 3.4 V test is a new operating point. Do not describe the headroom comparison as an unconditional power guarantee.

### R4-N2 — Reproduction, independent pack check and conditional read-cost limits

Executed from `hardware/station-pcb`, redirecting stdout only to `/tmp/pcb-f1-r4/`:

```text
python3 -I docs/calc/interlock_trips.py
python3 -I docs/calc/winter_model.py codex build/f1-revision/pvgis/ser60/series.json
python3 -I docs/calc/winter_model.py r2check build/f1-revision/pvgis/ser45/series.json
python3 -I docs/calc/winter_model.py scenarios build/f1-revision/pvgis/ser45-az233/series.json build/f1-revision/pvgis/ser70-az233/series.json build/f1-revision/pvgis/ser45/series.json
```

All four stdout bodies match the committed sections **byte for byte**. The codex/r2check bodies also match 0d038c4 byte for byte. Script SHA-256 values agree with the response:

- interlock: `59f980f8ab429a2a09fee318da387264c72b40343845e251606fcaf463546365`
- winter: `054c8a9ca0c7c9f6feb99f3a608c06a877125345498e2252c761013e8e9ebb9d`

A separate hourly recurrence used the cached rows and audited event-cost function, without calling the script's simulation functions. It applied the documented energy limits, nightly Schmitt reset, self-discharge, PM subtraction and mode thresholds. All tested pack/bias cases stayed above hibernation; an independent recovery branch was therefore unnecessary. Pessimistic M2 adaptive minimum usable SOC, for constant bias −15 / 0 / +15 percentage points:

| Pack | Minimum SOC | Outage hours |
|---|---|---|
| 3 cells new | 43.3305 / 27.1791 / 13.6863 % | 0 / 0 / 0 |
| 3 cells, 20% faded | 40.9996 / 27.6225 / 14.1278 % | 0 / 0 / 0 |
| 8 cells new | 49.9342 / 42.4168 / 35.7086 % | 0 / 0 / 0 |
| 8 cells, 20% faded | 48.4454 / 34.9085 / 26.8436 % | 0 / 0 / 0 |
| 14 cells new | 64.1903 / 57.8498 / 53.7313 % | 0 / 0 / 0 |
| 14 cells, 20% faded | 59.1035 / 52.5986 / 44.5523 % | 0 / 0 / 0 |

Independent lean/survival counts also agree after rounding. The complete rerun confirms 8 faded cells pass all the **modelled adaptive** scenario rows, including the +1/+4 °C sensitivity, alternate orientation/tilt, ACK sensitivity and high sleep-floor case. Fixed-cadence failures remain disclosed.

Direct tests at the printed **3.99 mAh** (8 faded) and **6.39 mAh** (14 faded) limits give no outage for any of the three biases. Worst minimum SOC is respectively **3.0435%** and **3.0074%**, very close to the 3% hibernation trigger. The sensitivity with the higher floor correctly lowers the displayed limits to 3.98/6.38 mAh.

These limits hold for the particular model: fixed PMS contribution, the non-PMS component scaled alike across all read modes, fixed duration/sleep accounting, and the stated Wi-Fi/floor/gate policy. A single measured PM-inclusive read cannot alone bound an arbitrary no-PM survival read, repeated failures, longer event duration or extra wakeups. F6 should also verify those mode costs. This is a qualification of the acceptance method, not a reason to reject the approved 8-cell choice.

Firmware citations were checked: gateway manual triggers are at 1645–1658 and 1763–1773; `sendDataRequest()` sets the pending flag at 1577. The timeout at 1779–1783 clears that flag, while decoding/uploading continues at 1785–1817. Station receive helpers occupy 518–555; `doListenCheck()` is defined at 759 but not called, while setup calls `listenForRequest()` at 807. F5 must remove that setup path too. A scheduled valid frame can clear a manual request before timeout, so “requests now time out” is not literally true for every arrival phase; no service promise remains, which is the important correction.

### R4-N3 — U3 is not yet qualified against a Samsung backup-overcharge limit

The revised documentation correctly distinguishes the **4.29–4.43 V U3 trip** from normal 4.20 V charging. Neither the tentative report nor the inspected product specification establishes that particular backup threshold for this pack. An abuse-test pass is not approval of sustained or repetitive charge at the U3 threshold. Keep this an explicit F2 qualification against the applicable supplier specification, including normal float tolerance, rather than claiming cell-protection sign-off.

The −10 °C discharge boundary remains in the fuller specification. The design acknowledges air below it, but foam and an unpopulated heater do not establish cell temperature during a prolonged cold interval. Preserve the approved 35E/no-logger decisions while defining how actual cell-temperature limits will be met or load operation inhibited; the current energy model does not prove that. Recovery voltage-to-SOC mapping and residual off-state drain also remain conditional, as now disclosed.

The powered-battery-connection exception is explicit, an improvement over the earlier blanket startup claim. Its “about 0.1 s” comes from several RC time constants, not a universal detection-time maximum: detection time depends on battery overdrive relative to U3's actual threshold. Validate connection order and define the permissible transient rather than treating 0.1 s as a guaranteed cutoff deadline.

## Limits and gate recommendation

Only this new review file was written in the worktree, left uncommitted. No designer files, main checkout, branches, firmware, commits or remotes were changed. Cached PVGIS data were reused; no hardware measurement, parts procurement or schematic implementation was performed.

Close **R4-M1 and R4-M2** before presenting F1 as ready. Correct the suspend inventory and cell-source provenance, carry the explicit qualifications into F2/F6, and regenerate dependent trip/energy results if the interlock changes. The selected no-listening/8-cell strategy is supported by the stated energy model; it does not close the two remaining hardware proofs.
