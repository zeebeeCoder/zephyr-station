# F1 revision 5: sixth review

Reviewed 27.10.2026 by **pcb-review/Pi** (new reviewer, not the author of the historical Codex reviews).

- Brief: **zephyr-f1-r6-119d1e9**.
- Baseline: **119d1e9f930abd69bddfc2dd87af00cb33e610cf**, branch `hardware/station-pcb`; historical r5 committed in `238bad6`.
- Scope: STATUS, REQUIREMENTS, ARCHITECTURE, r5/response-r5, r4's outstanding dispositions, all three calculation scripts and their outputs, cached manufacturer sources and newly retrieved ST Rev 8.

**Recommendation: not ready for the F1 gate.** The larger independent search and the corrected ST arithmetic are useful improvements, and all five recorded stdout bodies reproduce. The missing ST document is now available: pulse-power derating is more favourable than the old curve. However, twice a sampled maximum is not an established safety envelope; the surge argument does not cover switch-generated transients; and the assumed thermal resistance does not establish the claimed starting temperature on this board. These are missing arguments, not demonstrated hardware failures or reasons to reopen the approved LT3652/8-cell decisions.

**Counts:** r5: **3 resolved, 3 partly**. Previously-partly r4/r3/r2 rows: **3 partly in each generation**. Findings: **0 blockers, 3 major, 2 minor, 2 notes**. “Resolved” below means the original architecture finding is addressed, not that hardware is qualified.

## Dispositions

| r5 item | Status | Evidence |
|---|---|---|
| M1, tolerance search | Partly | Independent parameters, OUT1 source and revised rail capacitance implemented; arbitrary 2× multiplier still lacks an upper-bound justification. R6-M1. |
| M2, surge ceiling | Partly | Formula, temperature correction and rounding reproduce; current Rev 8 retrieved. Switching and thermal premises remain open. R6-M2/M3. |
| M3, unsupported Zener | Resolved | Zener and independent 62 V guarantee withdrawn; diode ratings updated. The replacement upstream-dependent protection inherits M2/M3 below and is not independently qualified. |
| m1, impossible connection test | Resolved | Initial voltage is no longer required to fall below float; actual trip and overdrive are distinguished. Reconcile the new transient-charge limits, R6-m2. |
| N1, reproduction/energy | Resolved | Five outputs reproduce, fixed-cadence regression disclosed, new read-cost boundaries checked directly. R6-N1. |
| N2, rail/complete stop | Partly | Complete-stop requirement and initial-condition restrictions are explicit. Actual LDO slew remains assumed, and the new claim that safety does not depend on an upper rail limit is too broad. R6-M1/N2. |

| Previously partly | Status and remaining dependency |
|---|---|
| R4-M1; R3-M1; R2-B1 | Partly: R6-M1/N2; component, drive and complete-stop qualification remain conditional. |
| R4-M2; R3-M2; R2-M3 | Partly: source existence and published clamp formula are settled; R6-M2/M3 prevent closing the protection envelope. |
| R4-N3; R3-N2 | Partly: connection criterion improved; Samsung backstop threshold, actual cold-cell operation and voltage-to-SOC recovery remain explicitly unqualified. This does not demand hardware qualification during F1. |
| R2-M1 | Partly: winter calculations pass for the stated adaptive model, but their hardware window still depends on R6-M1. |

No regression identified in the previously accepted no-listening strategy, default-open USB charging jumper, signed battery-current measurement, bus-plus-shunt voltage, combined-current shunt allocation or actual-state R-P7 limits. This review did not repeat the historical firmware/library source audit.

## Major findings

### R6-M1 — A 2× search result remains an allowance, not the promised bound

**Locations:** `interlock_trips.py:unsafe_error`, `filter_check`, `FILTER_ALLOWANCE`; ARCHITECTURE D5 filters/state table, §9/10; REQUIREMENTS R-P4; response-r5 M1.

The search now really varies all 18 values independently. It evaluates 786432 vertex/NTC combinations per comparator, refines selected vertices over NTC, runs coordinate ascents and samples interiors. The reproduced maxima are **0.45196 mV for U1** and **0.19105 mV for U2**, with the latter including a **0.0115 mV** OUT1 kick. The resulting safety temperatures **+0.0369 / +44.3373 °C** are reproducible *under the allowance and other stated assumptions*.

Nevertheless, multiplying a lower estimate of a supremum by two does not give an upper bound. Neither monotonicity, interval enclosure, a global residual/error estimate nor an independent conservative network inequality establishes that all unsampled parameter/NTC combinations fit inside it. The previous counterexample being only 6% larger and the new random samples being smaller do not supply such a guarantee. R-P4 still says “bounded for any history” and “Guaranteed at the safety corner”; §10 carries the same 2× rule forward as the verification method.

For fixed values, the two-source RC matrix and convolution are appropriate. The integral of the pointwise maximum of the high/low slope kernels is conservative for the **continuous slope-driven portion** of the specified source model. Further qualifications matter:

- `unsafe_error` adds the largest excursion of **one OUT1 step** beyond its DC endpoint range. To extend this to *any sequence* of switching, show the impulse-response sign/variation property or an equivalent bounded-input argument. A single-step excursion alone is not that proof. At two independently inspected sample networks the impulse-area check agreed with the single-step treatment; I found no counterexample, but that check is not global coverage.
- VOH/VOL errors enter static corners; the script explicitly treats their drops as quasi-static, not independent moving sources. Preserve that assumption or bound their dynamic contribution.
- Integration is analytic **between detected roots**. Root detection uses a finite 12-points/decade grid; the 600-points/decade comparison at the reported worst points agrees, but does not certify finding every relevant root over the box.
- Initial charge reachable from rest under the modelled source history is included. Arbitrary injected charge, NTC topology changes and independently assigned capacitor voltages are not. The new hot-plug requirement correctly distinguishes these.

**Close by:** derive a conservative envelope over the declared ranges, or provide a justified reduction/validated numerical enclosure and cover OUT1 switching. It need not be a tight optimum. Then regenerate the margins and any changed winter trips. A candidate architecture may carry assumptions, but calling the search honestly a search does not by itself close the previous major proof finding. No cold-charge failure is demonstrated here.

### R6-M2 — The surge proof only budgets the external pulse slope, not switch commutation

**Locations:** ARCHITECTURE D5 surge bound, R-P1; `surge_bound.py:L_TVS`, `DI_DT`, `i_loop`.

The script calculates:

```text
V25 = 45.7 - 0.333*(33 - 11.3) = 38.4739 V
IN at Tstart=51 C, plus 10 nH*1.13 A/us = 39.465515 V
VIN plus 12.3 A*sqrt(5 nH/10 uF)       = 39.740551 V
```

Those numbers correctly round to 39.47/39.75 V. The missing part is showing that their premises hold through the actual switching event.

The **TVS branch current need not follow the external generator's 10 µs rise**. When the eFuse interrupts a forward current, that current commutates into input capacitance/TVS. Its local di/dt can be much faster than 1.13 A/µs even while the imposed surge varies slowly. Thus the 11.3 mV TVS-loop allowance does not establish IN ≤39.47 V during the very opening event the text claims to cover.

TI explicitly describes this in **TPS2660 SLVSDG2G §11.1, p.38**: interruption produces a **positive input spike and negative output spike**, dependent on input/output inductance. Its example energy equation uses the local input capacitance, and it discusses TVS, capacitance and output Schottky protection. §12.1, p.39, also requires placement close to the protected pins. The document's statement that the whole loop energy simply goes into the VIN capacitor on opening is not a substitute for partitioning that interrupted network.

Likewise, limiting capacitance at IN to 1 µF does not prove it contributes only milliamps in all events. The tail calculation is valid on that smooth tail; stored input charge can supply transient forward current during switch transitions/recovery. `I_loop = I_surge + I_panel` needs a circuit/state argument, including initial capacitor voltages and eFuse resistance/control, rather than only the external-source peak sum.

**Close by:** specify the input/output inductance partition, capacitor bounds/initial states and current commutation paths; establish positive and negative pin envelopes for opening and recovery. Either prove passive/damping limits independent of timing, or use guaranteed timing/current bounds. Do not substitute typical fast-trip timing. This can retain the selected parts, but the present scalar calculation alone cannot establish the ceilings. LDO protection now inherits the IN envelope, so this is not just an LT3652 issue.

### R6-M3 — Rev 8 resolves derating, but not the 51 °C thermal premise

**Locations:** ARCHITECTURE D5 starting temperature/pulse rating, §9/10; R-P1; `surge_bound.py:RTH_JA`, `dt_mean`, `tj`.

**Primary-document check succeeded through a supplier mirror.** ST's own endpoints timed out; the LCSC copy identifies itself as **DS0683 Rev 8, May 2022**. Provenance/hash are below. This is not a quote from the retired reviewer.

- **p.2 Table 1:** PPP = 1500 W, initial junction temperature equal to ambient, table at 25 °C.
- **p.3 Table 2:** SM15T33A/CA: VBR 31.4/33/34.7 V min/typ/max at 1 mA; IRM maximum **0.2 µA at 25 °C, 1 µA at 85 °C**, at VRM 28.2 V; 10/1000 µs VCL maximum 45.7 V at 33 A; RD 0.333 Ω; αT **maximum** 9.8×10⁻⁴/°C. Notes 2 and 3 confirm the temperature multiplier and lower-current VCL formula used in revision 5.
- The derating plot is **Figure 3, p.4**, not Figure 1. It gives **1500 W at 50 and 51 °C (100%)**, remaining flat to approximately **115–120 °C by graphical reading**, then about 1250 W at 150 °C. The precise knee is not a tabulated tolerance guarantee. The 446 W application pulse is about **30%**, not 33%, of the plotted rating at 51 °C. The archived Rev 4 Figure 1 was correctly read, but is unnecessarily pessimistic here.
- **Figures 11/12, p.5** give thermal impedance and resistance versus time/copper area, for FR4 with **70 µm copper**. The curve approaches roughly **110 °C/W** for small copper area, rather than a universal 75 °C/W. These are graphical characteristic values, not a demonstrated maximum for this two-layer board.

The script's mean heating calculation, **0.745 J/60 s ×75 K/W = 0.931 K**, is correct given those inputs. It does not establish that this board has that thermal resistance, no other local heating and a bounded pre-pulse junction temperature. A periodic passive thermal model can support a pre-pulse bound from average heating, but its waveform, cooling assumptions and board thermal conditions must be stated. “10/1000 µs” alone should not silently become an exact exponential-tail energy bound without defining the waveform/tolerance.

Sensitivity, **not a prediction of this board**: using 110 K/W in the same model gives 1.366 K mean rise; rounding the start to 52 °C yields **IN 39.503219 V, VIN 39.778256 V**, i.e. 39.51/39.78 V rounded up. Thus the published 39.47/39.75 ceilings depend on this assumption, although this example still remains below 40 V. Keeping heating under 1 K in that model requires Rth ≤ approximately 80.5 K/W before other heating allowances.

**Close by:** adopt a defensible thermal envelope with explicit footprint/copper/environment requirements and a stated pulse-energy bound, then consistently recompute the ceilings. The favourable Rev 8 power curve closes the missing-derating-source question; it does not prove a particular junction start or voltage clamp. Do not leave obtaining/comparing Rev 8 as an F2 prerequisite: it has now been done.

## Minor findings

### R6-m1 — The old input-capacitance exemption remains in D5

The **LT3652 settings / Input capacitance** bullet still says it is “no longer part of the surge bound” and specifies only “at least 40 V.” This contradicts the revised surge section and §10, where effective capacitance is essential and parts are rated ≥50 V. Remove the stale exemption and use the revised requirement consistently. Also update the Figure 1 references to Rev 8 Figure 3 and its actual derating evidence.

### R6-m2 — Separate blind-interval charge from complete-stop residual charge and fault scope

The powered-connection test now has a meaningful initial voltage and threshold. At Vbat=4.50 V, Vtrip=4.43 V and τ=23.8 ms:

```text
t_cross = 23.8 ms * ln(4.50/0.07) = 99.0874 ms
1.56 A * t_cross                  = 0.154576 C
```

That is time to **input threshold crossing**, not cessation of charging. Comparator/gate delays and the separately permitted post-opening **20 mC** remain. R-P4 and the test should state whether 0.16/0.044 C are blind-interval budgets only, or totals to current cessation. The stated allowances do not imply a ≤0.16 C total: even 0.154576 C plus the allowed 20 mC exceeds it.

Also scope “a failed charger delivers at most its regulated current” to the selected **voltage-feedback fault with functioning current regulation**; it is not a bound on arbitrary charger failures. The lab-supply/sink test is a suitable way to test that limited scenario. No broad single-fault guarantee is requested. Define measurement tolerance and permitted incremental charge instead of equating ≤1 mA literally with zero added charge or zero voltage rise.

## Notes and verification

### R6-N1 — Reproduction, winter regression and read-cost boundaries

Executed from `hardware/station-pcb`, with stdout/cache only under `/tmp/pcb-r6/`:

```sh
python3 -I docs/calc/interlock_trips.py
python3 -I docs/calc/surge_bound.py
python3 -I docs/calc/winter_model.py codex build/f1-revision/pvgis/ser60/series.json
python3 -I docs/calc/winter_model.py r2check build/f1-revision/pvgis/ser45/series.json
python3 -I docs/calc/winter_model.py scenarios build/f1-revision/pvgis/ser45-az233/series.json build/f1-revision/pvgis/ser70-az233/series.json build/f1-revision/pvgis/ser45/series.json
```

All five complete stdout bodies match their recorded sections: **6114, 858, 678, 548, 11826 bytes**, respectively. Interlock stderr is empty. Script SHA-256 values match response-r5:

```text
interlock 5e00967cd07e1c65d111117bd3f0684d631f01bd16eab762be7dac3f4c375f12
surge     afa94fe73151edf88c115e9dcc8509f7e79e2e1d9fcff017610122f0d03f9d0c
winter    0e5a4e29c5315b1ef28588eec221e3b6d01f6ba7c08e58e2b7d1de090f6c92a2
```

The winter code diff changes only revision commentary and the energy-corner trips to **2.73/3.09/41.52/41.32 °C**. The full model was read and rerun; its simulation recurrence was not independently reimplemented this round.

- **8 faded cells, pessimistic adaptive:** all three constant SOC-bias cases pass; minimum rounds to 27%, lean 4.4–13.4 days/winter, survival up to 1.1.
- **8 faded cells, fixed 15-minute M2 pessimistic:** energy-corner failure is real in the rerun: one outage winter, about 15 days; alternate orientation/tilt about 16–17. Revision 5 correctly withdraws this fallback. Adaptive control is essential to the recommendation.
- Additional direct calls at the **printed** adaptive limits, with the documented common non-PMS scaling, give zero outage hours at every bias. Minimum SOC for −15/0/+15 percentage-point bias:
  - 8 faded, **3.99 mAh**: **28.3295 / 16.1928 / 3.0435%**;
  - 14 faded, **6.14 mAh**: **26.6165 / 14.5961 / 3.0475%**.
- Fixed-profile limits reproduce at **1.66/2.59 mAh** for 8/14 faded cells. These are model-specific, not universal per-read acceptance numbers. Mode costs, duration, repeated failures and recovery voltage mapping still need qualification. Constant biases are not a proof against arbitrary time-varying estimator errors.

### R6-N2 — Rail and stop qualifications must remain conditions, not disappear in prose

The cached **TI TPS7B69xx SLVSDI2 (April 2016)**, electrical characteristics p.5, supports the response's qualification: the 500 mA limit is specified with OUT shorted, and the ±3% regulation entry applies at **1–150 mA**, not the actual **0.738 mA** steady interlock load. The calculation's 22.7 V/ms rise and 50 V/s fall therefore remain conditional on a global current limit, effective 22 µF capacitance and the full discharge-path inventory. The 1.051 mA gate-charging load and 59.5 µs chain-opening arithmetic reproduce; neither proves complete current cessation.

The sentence that safety “doesn't depend” on the upper regulated window because normalized offsets shrink above 3.4 V is incomplete. **NTC self-heating scales approximately as VREG²**, while its 0.1 K allowance was computed at 3.4 V. OUT1 kick amplitude, gate initial voltage and load/falling slope also use the upper rail. For illustration, the nominal 0.099 K self-heating at 3.4 V becomes about 0.137 K at 4.0 V; this is not a prediction of LDO overshoot, but disproves the claimed general independence. Retain an explicit upper-rail/startup envelope or recalculate those terms. A preload requires rerunning fall/USB budgets, not just asserting regulation.

F2 confirmation from TI or a design that enforces the required rail envelope, chosen-FET qualification, and F6 full-stop/hot-plug/thermal measurements remain valid future tasks. They must not be described as already satisfied. U3 supplier approval and the actual −10 °C cell-discharge strategy also remain open as already disclosed.

## Source provenance and limits

New manufacturer-authored ST source, retrieved 27.10.2026 from LCSC:

```text
https://datasheet.lcsc.com/datasheet/pdf/90dac3b1fa53d3a9bca01f3963dc7892.pdf?productCode=C81476
/tmp/pcb-r6/st-lcsc.pdf
SHA-256 3d4c7f4c7f31852cf00c9631b55bf65b51582036646e1c8386a098656edb9144
```

Text and rendered pages 1–5: `/tmp/pcb-r6/st-new.txt`, `/tmp/pcb-r6/st-new-pages/`. Table 2 and Figures 3/11/12 were visually inspected, not inferred from search snippets. ST-hosted `sm15t15a.pdf` failed through fetch and bounded curl attempts; `sm15t39ca.pdf` also timed out. TME/Avnet attempts returned HTML, not source PDFs. No configuration was changed to bypass those failures.

Also inspected the cached ST Rev 4, TI TPS7B69xx and TPS2660 PDFs. TI source URLs: `https://www.ti.com/lit/ds/symlink/tps7b69.pdf`, `https://www.ti.com/lit/ds/symlink/tps2660.pdf`. The new ST mirror resolves source availability; no owner intervention to retrieve it is needed.

Only this review is a new deliverable. No designer/enclosure files, firmware, branches, commits or remotes were changed; no schematic/layout build, flash, procurement or hardware testing was performed. Close R6-M1–M3 at calculation/architecture level, reconcile the two minor items and preserve the explicitly conditional F2/F3/F6 checks before presenting F1 as ready.
