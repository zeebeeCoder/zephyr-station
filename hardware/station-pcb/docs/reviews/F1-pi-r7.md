# F1 revision 6: seventh review

Reviewed 27.10.2026 by **pcb-review/Pi**.

- Brief: **zephyr-f1-r7-fd1c0fe**.
- Baseline: **fd1c0fef29b1ecaca7e0de6280eb5828806d3b7c**, branch `hardware/station-pcb`.
- Previous review: `F1-pi-r6.md`, committed unchanged in `c54f20d`.
- Scope: revision-6 REQUIREMENTS/ARCHITECTURE/STATUS changes, response-r6, calculation scripts/outputs, outstanding findings and relevant manufacturer sources. Unchanged material was assessed against the preceding review rather than researched afresh.

**Gate recommendation: NOT READY.** R6-M2 is correctly left open and is sufficient to prevent gate approval. Independently, R6-M1 is **partly**, not fixed: the new continuous interval-comparison formulation is substantial progress, but its numerical implementation is not a certified enclosure. The switch-closed surge ceiling also needs an explicit current-slew condition. This review does not approve a part change, an environmental-requirement change or F2 work.

**This round's findings: 0 blockers, 2 major, 1 minor, 2 notes.** These include follow-up defects in the existing arguments; the already acknowledged R6-M2 remains open separately, not counted again as a new finding. **R6 dispositions: 3 resolved, 3 partly, 1 open.** No observed hardware failure is claimed.

## Disposition of every R6 item

| Item | Verdict | What is closed / what remains |
|---|---|---|
| M1 — filter envelope | **Partly** | The arbitrary 2× search factor is gone. Independent coefficient intervals, a lagged-rail decomposition and a bounded-input OUT1 argument are meaningful improvements. Numerical enclosure, integration and tail certification remain missing; R7-M1. |
| M2 — switch commutation/recovery | **Open** | Now explicitly an architecture gap in R-P1, D5 and STATUS, not deferred as a completed proof. Neither the 50.42 V estimate nor the unselected options close it. |
| M3 — thermal premise | **Partly** | Correct Rev 8 source and derating, explicit exponential waveform in the code, Rth/local-heating conditions, and revised arithmetic. Rth ≤120 K/W remains a board requirement, not a manufacturer maximum; the closed-switch ceiling also has R7-M2's missing slew premise. |
| m1 — stale VIN capacitance text | **Resolved** | D5 now consistently requires ≥50 V parts and effective C tied to L/C; obsolete capacitance independence and Rev 4 derating are removed. |
| m2 — blind/residual charge | **Partly** | Fault scope and three-stage budgets are corrected. Test uncertainty is stated but not applied to the acceptance limit; small stage-rounding issue also remains. R7-m1. |
| N1 — energy/reproduction | **Resolved** | Static energy thresholds and winter files are unchanged; conservative model rounding is intact. Independent rerun of scenarios matches. R7-N1. |
| N2 — upper rail/stop conditions | **Resolved at documentation level** | V_TOP=3.4 V including startup is explicitly a condition; the former independence claim is withdrawn. Slew, preload, complete stop and device qualification are not claimed as achieved. R7-N2. |

### Older unresolved rows

- **R5-M1, R4-M1, R3-M1, R2-B1:** remain **partly**, through R7-M1 and the explicit rail/device qualifications.
- **R5-M2, R4-M2, R3-M2, R2-M3:** remain **partly**, through open R6-M2 and the conditional thermal/closed-switch argument.
- **R5-N2:** its disclosure issue is improved; actual rail and complete-stop qualification remains conditional, so the broader row remains **partly**.
- **R4-N3, R3-N2:** remain **partly**. Connection-test improvements do not qualify Samsung's backup-overvoltage limit, the actual −10 °C discharge strategy or recovery voltage-to-SOC mapping.
- **R2-M1:** remains **partly**. The adaptive winter model is internally consistent, but hardware-window closure still depends on the interlock proof.

Previously resolved architecture findings are not reopened merely because F2/F3/F6 qualification remains ahead.

## Major findings

### R7-M1 — The continuous comparison system is not yet a certified numerical bound

**Locations:** `interlock_trips.py:env_coefs`, `rhs_ext`, `_expm_affine`, `envelope`, `_ends`, `kernel_bound`, `slope_per_k`; ARCHITECTURE D5 filters; R-P4; response-r6 M1.

**Progress verified.** The model includes the proposed C_HOT and 19 independent component ranges plus the NTC interval. The transformed node equations retain the differential-capacitance coupling. Coefficient ranges are formed from their dependencies rather than sampled complete networks. The upper/lower right-hand-side construction is a reasonable continuous comparison-system approach; losing correlations makes it more conservative, not less.

The OUT1 treatment now has the requested bounded-input structure. For fixed parameters, with 0 ≤ OUT1 ≤ VREG ≤ V_TOP, subtracting the OUT1-high history leaves a source in [−V_TOP,0]. Its maximum unsafe contribution is bounded by the negative part of the impulse response times V_TOP. This addresses arbitrary switching histories rather than only one isolated step. The decomposition at W, and subtracting the worst input lag from the allowed rail floor, also addresses the common input delay. These are improvements independent of the sample checks.

**The remaining gap is between those continuous statements and the numbers printed as guaranteed bounds:**

1. **Switching of the comparison equations is checked only at sub-step endpoints.** `envelope` advances with one frozen extreme selection and asks whether the endpoint selection changed. It does not exclude a selection changing and changing back inside the step. At minimum step it adds `h * gap_at_endpoint`; there is no bound on the gap throughout the step or its coupled propagation. A small endpoint correction does not establish that the trajectory was enclosed between endpoints or at the final endpoint. More than a million such retained changes per comparator are reported. The printed largest single widening is not a bound on accumulated numerical error.
2. **The matrix exponential is numerical, not exact.** `_expm_affine` uses floating-point scaling, a truncated Taylor series and squaring. No remainder/roundoff enclosure is carried into the state bounds. This need not be a significant practical error, but the claim “solved exactly” does not certify it.
3. **`_ends` is not generally an upper quadrature rule.** It uses the larger endpoint value of each interval. An interior maximum can exceed both endpoints. For example, the actual helper returns zero for endpoints of `t*(1-t)` on [0,1], although the integral is 1/6. This illustrates the missing condition, not a counterexample to this PCB network. Monotonicity or an enclosed interval maximum must be established for the actual integrands. The 40/80-points-per-decade comparison shows convergence evidence, not an error bound or monotonicity proof. `_check_job` uses the same integration rule, so its “exact” integrals are not an independent quadrature certificate.
4. **The tail after 50 ms is omitted without a decay/integral bound.** The reported ~10⁻¹² terminal interval width is not by itself an upper bound on remaining kernel/impulse area. A uniform decay estimate for the physical network could make this negligible; it must actually be supplied and budgeted.
5. **The kelvin conversion still samples a derivative.** I independently evaluated the analytic derivative of each log-linear NTC segment, `abs(d ln R/dT) * RS*R/(RS+R)^2`, at the segment endpoints and resistance corners. For U1 the script returns **0.009731551849/K**, whereas an allowed one-sided segment value at **1 °C**, NTC minimum-table column, +0.5% drift, RS=11.979 kΩ is **0.009718282777/K**. The sampled minimum is **0.1365% too high**, slightly understating the temperature allowance. This does not consume the 0.0145 K cold margin by itself; it is a concrete example of why the claimed continuous minimum should not be a finite-difference sample minimum.

The response candidly admits the widening, quadrature and tail are validated rather than proven. R-P4 and D5 nevertheless present the resulting values as bounds over every allowed history/parameter set. That mismatch leaves the previous major finding open. The 65/64 point checks and passing asserts are useful diagnostics, not replacements for the missing enclosure.

**Reproduction:** U1 **0.5605/0.5478 mV** and U2 **7.4838/7.3471 mV** at 40/80 points per decade; W **2.4825–3.4004 V**; safety corners **+0.0145 / +44.7451 °C**. These are reproduced numerical estimates of the proposed envelope, not independently certified safety margins.

**Close by:** bound integration/selection errors over whole steps, propagate outward numerical error, enclose quadrature and the tail, and use a conservative continuous slope bound (or invert the voltage allowance directly). A simpler conservative analytic bound is equally acceptable; another denser sampling pass alone is not. Apply the certificate to W/lag as well as Δ and OUT1. The beyond-band U2 calculation stops near **132 Ω**, not at zero; retain its documented “nearly shorted” scope and provide a limiting/short argument if claiming all resistances down to a hard short.

**C_HOT disposition:** no technical objection was found to analysing the 100 pF C0G proposal as a candidate; it is correctly present in both the network matrix and interval ranges and does not alter DC trips. However, it is **not accepted as a verified closure of M1**, and reviewer commentary is not owner approval or a BOM instruction. Divergence of an interval enclosure without it is not proof that the old physical network is unstable. No part selection or implementation was performed.

### R7-M2 — The defined pulse envelope does not establish the assumed maximum di/dt

**Locations:** `surge_bound.py:DI_DT`, `ceilings`; R-P1 waveform; ARCHITECTURE D5 switch-closed ceiling.

Separating switch opening from the closed-switch case is correct. Even the latter still uses **11.3 A / 10 µs = 1.13 A/µs** as though it were a maximum TVS-current slew. The new waveform limits amplitude and tail energy; it does not impose that maximum derivative. In particular, “front time ≤13 µs” is an upper time bound, not a lower rise-time bound, and nominal 10/1000 timing does not bound the peak derivative of a nonlinear front.

Using the designer's own scalar model and unchanged Tj=57 °C, L/C and current assumptions:

| Assumed linear front | IN before rounding | VIN before rounding |
|---|---:|---:|
| 10 µs, as scripted | 39.6917415 V | 39.9667779 V |
| 7 µs | 39.6965844 V | 39.9716207 V |
| 2 µs | 39.7369415 V | 40.0119779 V |

The 7 µs calculation alone rounds VIN to **39.98 V**, not 39.97 V. The 2 µs row is a sensitivity illustrating the missing derivative constraint, **not an assertion that a specified standards-compliant generator or the real PCB produces that voltage**. Both fronts fit the code's stated amplitude/front-upper-limit/exponential-tail envelope; additional admissibility conditions need to be explicit if they are intended to exclude one. Even fixing a nominal front duration does not by itself fix its maximum instantaneous slope.

**Close by:** state and justify the admissible waveform/current-slew envelope at the TVS branch, or derive the loop transient without the `Ipeak/10us` substitution. Recompute consistent rounded ceilings. Do not silently narrow R-P1 or treat a generator's typical waveform as a maximum. The current no-timing/opening gap remains open independently; no alternative TVS or charger research is requested here.

## Minor finding

### R7-m1 — Measurement uncertainty must be included in the residual-charge acceptance rule

**Locations:** R-P4; ARCHITECTURE D5 and §7 item 1; response-r6 m2.

The three stages and the restriction to a voltage-feedback fault **with functioning current regulation** address the substance of the prior finding. The new totals, **0.18 C solar / 0.065 C USB**, comfortably include the stated blind-interval and 20 mC residual allocations under that fault model. The response time allowance is correctly not described as a datasheet maximum.

However, a displayed mean of **1 mA with ±0.5 mA uncertainty** can represent **1.5 mA**. Over 0.1 s that is **0.15 mC**, not ≤0.1 mC. Specify a guard-banded pass criterion, such as measured upper uncertainty limit ≤1 mA, or change the permitted charge with the appropriate approval. Apply the same principle to the ±5% charge measurement and ±2 mV voltage criterion: quote the permitted physical increment separately from instrument uncertainty.

Also round the intermediate gate-stage charge upward: **1.56 A ×129.5 µs =0.20202 mC**, marginally above 0.2 mC; both chargers together at 2.004 A would give **0.25952 mC**. State whether that allocation is per charger or combined. These corrections do not invalidate the rounded 0.18/0.065 C totals, but “≤” acceptance numbers must not be rounded down.

## Notes

### R7-N1 — Reproduction and winter consistency

Executed from `hardware/station-pcb` with stdout, stderr and auxiliary checks under `/tmp/pcb-r7/` only:

```sh
python3 -I docs/calc/interlock_trips.py
python3 -I docs/calc/surge_bound.py
python3 -I docs/calc/winter_model.py scenarios build/f1-revision/pvgis/ser45-az233/series.json build/f1-revision/pvgis/ser70-az233/series.json build/f1-revision/pvgis/ser45/series.json
```

The complete stdout bodies match the recorded sections byte for byte: **5856 / 2116 / 11826 bytes**, respectively. The interlock and scenarios background jobs have recorded exit status **0**, empty stderr; surge also completed successfully. Thus the pass asserts and all quoted results reproduce, without being taken as proof of the envelope.

Full-precision static energy thresholds computed independently from `corners`:

```text
cold off  2.7232084815566573
cold on   3.089393348634056
hot off  41.52483570745201
hot on   41.32510859873162
```

The model correctly retains conservative rounding **2.73 / 3.09 / 41.52 / 41.32 °C**, not the interlock report's nearest-rounded **2.72 / 3.09 / 41.52 / 41.33**. There is no energy-threshold regression. C_HOT affects the dynamic circuit, not its DC dividers. The winter script and recorded output are byte-identical to the previous baseline; its unchanged static-gate modelling assumptions are not expanded into guarantees about arbitrary fast rail histories.

The scenario rerun preserves: adaptive pessimistic 8 faded cells, no outage and minimum ~27%; fixed-15-minute pessimistic M2 on the same pack, one outage winter/about 15 days at the energy corner (16–17 days at the other orientations); adaptive read limits **3.99/6.14 mAh**, fixed **1.66/2.59 mAh**. Per-mode scaling, constant SOC biases, cold-cell temperature and recovery qualifications remain unchanged. Codex/r2check modes were not rerun this round; the unchanged script and their prior reproduction were checked by hash/diff rather than claimed as fresh runs.

Hashes match response-r6:

```text
interlock_trips.py        7cb3c40736aa2d081d75c353ed1bef9f4558feca499ed4ed3867fa0f5588a780
surge_bound.py            7d49f033637c74d7917570a69ac1f73d2860868cf0f78cdfce3e68e0eacc30d7
winter_model.py           0e5a4e29c5315b1ef28588eec221e3b6d01f6ba7c08e58e2b7d1de090f6c92a2
winter_model_output.txt   fb7c030815635ff02ae65d479896a3da1815c677e0bcfaf2dcefe837d8d5c42a
```

### R7-N2 — Source/thermal/rail progress and the still-open gate

The archived **ST DS0683 Rev 8 (May 2022)** matches the PDF retrieved during r6:

```text
build/f1-revision/research/power/st_sm15t_rev8_lcsc/sm15t_ds0683_rev8_lcsc.pdf
SHA-256 3d4c7f4c7f31852cf00c9631b55bf65b51582036646e1c8386a098656edb9144
https://datasheet.lcsc.com/datasheet/pdf/90dac3b1fa53d3a9bca01f3963dc7892.pdf?productCode=C81476
```

Table 2/notes 2–3, Figure 3 and Figures 11–12 retain the source findings in r6. Rev 8 supports the favourable pulse-power derating; **120 K/W is a design condition above a characteristic curve, not a guaranteed manufacturer thermal maximum**. The curve's FR4/70 µm copper context must remain attached to its use. Board temperature, neighbouring heat and actual mounting still need qualification.

For the **continuous exponential envelope explicitly written in the script**, charge **19.7098448 mC**, energy **0.9007399 J**, mean heating **1.8014798 K**, and rounded pre-pulse **57 °C** reproduce. Use that equation in the requirements rather than relying only on the potentially ambiguous phrase “halves every 1.2 ms.” The passive periodic-thermal argument is now stated, unlike r5; it remains conditional on that thermal model and waveform. It does not establish the opening/recovery envelope.

The **TPS2660 SLVSDG2G**, §7.1 p.6, confirms **OUT-to-RTN ≥−0.3 V**; §11.1 p.38 and §12.1 p.39 support treating input/output switching spikes separately. Its reverse-input GND rating must not be substituted for the OUT-to-RTN rating. The proposed Schottky is not a qualified clamp without its current/voltage/loop envelope. The new **50.42 V** calculation is an estimate in an acknowledged open model, not an accepted pin/LDO bound or a demonstrated hardware waveform.

The LDO qualifications from **TI TPS7B69xx SLVSDI2**, p.5, remain: the shorted-output current-limit condition does not certify global startup slew, and the regulation accuracy test at 1–150 mA does not directly qualify the ~0.738 mA steady interlock load. Revision 6 now properly makes **VREG ≤3.4 V at startup and thereafter** a condition and retains the consequences of adding preload. W's upper mathematical allowance of 3.4004 V is a lag-coordinate bound, not permission for physical VREG to exceed V_TOP. Complete current stop, actual capacitance, FET drive/leakage and hot-plug behaviour remain qualification requirements, not measured results.

## Handoff and worktree limits

Ready to retain: corrected capacitance wording; source provenance/derating; explicit fault scope and staged charge budgets with the minor acceptance correction; V_TOP/stop assumptions; unchanged conditional winter results. Not ready: a certified all-range interlock numerical bound, an admissible current-slew/closed-switch ceiling, and the already open eFuse opening/recovery/LDO envelope.

Only `docs/reviews/F1-pi-r7.md` is a new deliverable. No designer or enclosure files, commits, branches or remotes were changed. No F2 implementation, BOM substitution, flashing, procurement or research of option C was performed. No automatic next round is initiated; further work requires the coordinator's brief.
