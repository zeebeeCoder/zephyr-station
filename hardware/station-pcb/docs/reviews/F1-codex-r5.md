# F1 revision 4: fifth review

Reviewed 26.10.2026 by `mobric/mikolaj-codex` for `mobric/workspace-codex-21`.
Baseline: **a0ae015**, branch `hardware/station-pcb`, following review r4 committed as **239a130**. Brief: `zephyr-f1-r5-a0ae015`.

Scope: REQUIREMENTS.md, ARCHITECTURE.md, STATUS.md, F1-response-r4.md, both calculation scripts and recorded outputs; previous unresolved review rows; relevant manufacturer documents. Only this new review file was written in the worktree.

**Verdict: not ready for mobric's F1 gate.** The coupled-network implementation is a substantial improvement and all recorded calculations reproduce. ST really does publish an applicable maximum-clamp calculation, so the missing formula need not wait for F2. However, its temperature correction and the declared input-voltage ceilings are wrong in this revision. The independent Zener ceiling also uses a minimum temperature coefficient as a maximum. The filter search omits independent tolerance combinations and demonstrably understates its claimed maximum. Close these calculation/proof issues before presenting the safety requirements as met.

**Counts:** R4 items: **4 resolved, 3 partly, 0 not resolved**. Previously-partly R3 items: **0 resolved, 3 partly, 0 not resolved**. Previously-partly R2 items: **0 resolved, 3 partly, 0 not resolved**. New findings: **0 blockers, 3 major, 1 minor, 2 notes**. These are architecture-level dispositions, not hardware qualification. No observed hardware failure is claimed.

## Decisions applied

Q24(a), default-open charging jumper for chargers/power banks; Q25(a), eight new genuine Samsung INR18650-35E cells from one batch; and D11, Fusion 360 with Astra and the enclosure agent, are consistently incorporated. The no-listening strategy, unchanged gateway, snow assumption, no logger this winter and chosen 1S8P pack remain intact. None is reopened by this review.

## Disposition of every R4 item

| Item | Verdict | Evidence / remaining work |
|---|---|---|
| R4-M1 — coupled filters and inhibit latency | **Partly** | Six-node RC topology replaces the invalid independent-pole calculation. U4/gate latency and the lower sweep endpoint are now explicit; LM4041 bias is corrected. But the claimed exhaustive tolerance bound is false: valid omitted corners exceed both printed maxima. Complete-stop latency and device qualification remain conditional. R5-M1, R5-N2. |
| R4-M2 — maximum clamp envelope | **Partly** | Manufacturer formula verified in ST DS0683 Rev 8, Table 2, notes 2–3. This closes the source-existence question. Its application does not establish the stated 39.3/39.4 V ceilings, and the restored Zener does not establish its independent ceiling. R5-M2/M3. |
| R4-m1 — suspend inventory | **Resolved** | BQ25170 input bias, LDO IQ and translators are included: 0.16 + 0.20 + 0.60 + 0.74 + 0.025 + 0.008 = 1.733 mA. Charging inventory includes charger bias. Default-open jumper and five-state validation remain explicit. These are estimates/allocations to validate, not complete-board measurements. |
| R4-m2 — cell specification | **Resolved** | Cached manufacturer specification Ver 1.1, 9 July 2015, agrees with the revised 2.65 V cutoff, 1.7 A standard / 2 A maximum charge and 18.55 mm diameter. Batch applicability remains an appropriate F2 check. |
| R4-N1 — R-P7 comparison | **Resolved** | 132 uA at 3.4 V is 448.8 uW, below 450 uW. Original actual-state 100 uA and 35 uA limits remain; rail-headroom assumptions are separately identified. Sensitivity floor is updated to 151.4 uA. |
| R4-N2 — model and firmware qualifications | **Resolved** | All four recorded stdout bodies reproduce. Read-mode scaling qualification and F6 mode measurements are included. Removal of setup's listenForRequest() and accurate gateway wording are present. |
| R4-N3 — cell/protection/recovery qualifications | **Partly** | U3 is explicitly unqualified against a Samsung backup limit; cold discharge and recovery assumptions remain explicit F2 tasks, as requested. Overdrive-dependent connection delay is described correctly. The new connection test has an impossible acceptance criterion, R5-m1. |

## Previously-partly rows

| Item | Verdict | Reason |
|---|---|---|
| R3-M1 | **Partly** | R5-M1 and the conditional rail/stop assumptions in R5-N2 prevent calling the whole transition proof closed. |
| R3-M2 | **Partly** | A usable primary source is now available; corrected ceiling and Zener proof still required, R5-M2/M3. |
| R3-N2 | **Partly** | Cell provenance is resolved and F2 qualifications are candid; repair connection acceptance, R5-m1. This does not demand completing hardware qualification in F1. |
| R2-B1 | **Partly** | Interlock topology/polarity and explicit state table are improved, but the numerical all-corners claim is not valid yet. |
| R2-M1 | **Partly** | Winter results and unchanged static energy trips reproduce. Closure still depends on a defensible hardware window and declared qualifications; no new pack-size objection. |
| R2-M3 | **Partly** | Input-protection proof is still incomplete, R5-M2/M3. |

Previously resolved R3 rows M3, M4, m1–m3, N1 and R2 rows M2, m3, m4 remain resolved at architecture level. No regression found in removal of request service, signed current/bus-plus-shunt voltage, combined-current shunt allocation, or USB host-state architecture.

## Major findings

### R5-M1 — The six-node solver is useful, but the claimed all-tolerance bound is not what the search computes

**Locations:** `calc/interlock_trips.py:filter_values`, `side_cases`, `filter_check`; ARCHITECTURE D5 input filters; R-P4.

The matrix construction includes the shared node and differential capacitances. The transformation using C = L Lᵀ and the step-response convolution is appropriate for the stated fixed linear circuit. For a fixed parameter set and the assumed slope limits, integrating the positive and negative parts of the differential response gives a useful conservative error bound.

The parameter coverage is different from the document's claim:

- `rs_ct` forces RS and C_T to move together at the enumerated corners.
- `tap1` forces RC1, RC2, RHYS and RF1 to move together; `tap2` similarly groups RH1/RH2. Opposite resistor errors alter the divider ratio and hence the unsafe rise term.
- The other comparator's side is checked only with all its values low or all high.
- Random interiors are not a replacement for omitted independent boundary combinations, nor is sampling five NTC resistances proof over the continuous band.

A concrete valid omitted corner, evaluated with the **unchanged** `unsafe_error(p, 1)`, gives **0.904692 mV**, above the declared **0.856194 mV**:

```python
p = dict(
    rs=11979.0, ct=764e-12, ntc=32166.146873431757,
    rin1=10100.0, rin2=9900.0,
    cm1n=10e-12, cm1p=10e-12, dm1=8e-12,
    rc1=10017.5, rc2=24257.475, rhys=3353200.0,
    rf1=27270.0, cf1=346.5e-12, cnode=0.5e-12,
    cm2p=10e-12, cm2n=1e-12, dm2=0.0,
    rh1=9982.5, rh2=4012.965)
```

Units are ohms/farads. This is within the script's own allowed ranges. At 200 and 600 time samples per decade it gives 0.904414 and 0.904403 mV: the discrepancy is not time-grid noise. A separate allowed U2 corner gives 0.395123 mV versus 0.391989 mV. Thus “every tolerance corner” and both reported upper bounds are disproved by direct reproduction.

**Impact:** the exhibited extra U1 error corresponds to approximately 0.0018 K using the existing slope conversion, so it alone does **not** consume the 0.038 K cold margin. It demonstrates an incomplete bound, not charging below zero. Do not reject the filter merely for its narrow margin; establish a conservative envelope over independent parameters, or justify reductions with monotonicity/inequalities, and recompute the margin. Describe a numerical search as a search unless its upper-bound property is established. Also cover RHYS's actual output states in the chosen bound instead of silently treating OUT1 as an ideal copy of VREG for every history.

### R5-M2 — ST supports the current-dependent envelope, but the specified 39.3/39.4 V ceilings do not follow

**Locations:** ARCHITECTURE D5 surge bound and source [SM], REQUIREMENTS R-P1, STATUS D5, F1-response-r4 R4-M2.

**Primary-source verification completed:** [ST DS0683 Rev 8, May 2022](https://www.st.com/resource/en/datasheet/sm15t15a.pdf), Table 2 on page 3, contains the SM15T33A/CA row and RD = 0.333 ohm for 10/1000 us. Note 3 uses `VCL - RD*(IPP - Iapplication)`; note 2 scales **VCL**, not only VBR, with temperature. The family PDF includes the selected 33CA despite the URL's 15A filename. Direct 33CA/30CA downloads timed out, but this ST-hosted family PDF opened successfully. The generic `sm15t.pdf` link in the project returned 404.

Using the published entries and +50 C correction:

```text
V25 = 45.7 - 0.333*(33 - 11.3) = 38.4739 V
V50 = V25*(1 + 0.00098*25)     = 39.41651055 V
IN  = V50 + 0.0113             = 39.42781055 V
VIN = IN + 2*sqrt(10e-9/4.7e-6)= 39.52006367 V
```

The last two lines use the designer's own inductance/current/capacitance allowances. Even V50 alone exceeds 39.4 V. The alternative VBR-based intercept differs slightly because RD is rounded; adding a temperature shift only to VBR misses another approximately 0.09 V. Rounding 39.31 down to a hard 39.3 V ceiling was already invalid before these corrections.

**This calculation still leaves about 0.48 V below 40 V** under those assumptions; it does not demonstrate that SM15T33CA must be replaced. Update the requirement, architecture, status and F6 thresholds with consistently rounded-up bounds and the actual source. Confirm temperature/pulse applicability and power derating using this source before F1 closure, rather than leave the central safety justification to F2. Do not equate survival at a rated pulse with an independently tighter voltage guarantee.

The revised stored-charge argument is directionally correct for a passive feed, but its overshoot allowance explicitly depends on >=4.7 uF and <=2 A at opening. Therefore remove the contradictory statement that the **complete** bound is independent of capacitance/current limit. Tie those assumptions to an actual current bound, effective capacitance, loop inductance and switching event; a typical eFuse response time is not a substitute. Cold breakdown arithmetic and negative-pulse diode ratings are improvements and need no reopening of the approved charger choice.

### R5-M3 — BZX84C33's claimed independent clamp uses a minimum coefficient as a maximum

**Locations:** ARCHITECTURE D5 interlock rail, R-P1's 36.3/38.1 V limits, response R4-M2.

The cached [Diodes DS18001 Rev 33-2](https://www.diodes.com/assets/Datasheets/ds18001.pdf), page 2, was extracted and visually inspected. For BZX84C33, **27.4 mV/C is under Min; Max is a dash**. It is not a maximum. The 23.1 figure used in the cold calculation is the reverse-leakage test voltage VR, not a temperature coefficient. The 80-ohm entry is impedance at the specified 2 mA/1 kHz test point; this table does not guarantee an integrated upper envelope up to 32 mA.

Consequently neither the +50 C 36.3/38.1 V ceiling nor the quoted cold lower bound follows from this source. The prose labels extension of ZZT as assumed, but R-P1 still claims a computed TVS-independent guarantee. The source also supplies no demonstrated 32 mA, 1 ms thermal bound in the current analysis. A 1 ms characteristic tail is not automatically a rectangular pulse with that duration and no remaining energy.

**Close by:** use a manufacturer-supported maximum voltage/current/temperature/pulse envelope for the selected clamp, or explicitly derive LDO protection from the corrected upstream envelope and remove the unsupported independent-62 V claim. This is about the claimed guarantee, not evidence that the diode fails in the defined pulse. Keep diode reverse-voltage and resistor pulse-energy checks consistent with whichever protection argument is retained.

## Minor finding

### R5-m1 — The new powered-battery-connection acceptance criterion is impossible as written

**Locations:** ARCHITECTURE §7 item 1, D5 U3 settling/state table, R-P4; response R4-N3.

The proposed test connects a battery at 4.30 V or 4.50 V, then requires the cells to remain at or below the chargers' <=4.25 V float during the blind interval. They already exceed that voltage at connection; a charger shutting off does not pull them down to its float. Furthermore 4.30 V is below some valid U3 thresholds (up to 4.43 V), so a trip at 4.30 V is not required of every unit.

Specify the initial voltage, actual threshold/overdrive, permitted **additional charge current/charge** during the interval, and expected result separately. A 4.50 V test exceeds the full trip range; a 4.30 V test probes the tolerance band. Distinguish a healthy charger's refusal to add charge from the failed-charger case U3 is intended to backstop. The overdrive-dependent RC expression is otherwise an improvement; no fixed 0.1 s guarantee should return.

## Notes and verification

### R5-N1 — Reproduction, energy and accepted corrections

Executed from `hardware/station-pcb`, with stdout redirected only to `/tmp/pcb-f1-r5/`:

```text
python3 -I docs/calc/interlock_trips.py
python3 -I docs/calc/winter_model.py codex build/f1-revision/pvgis/ser60/series.json
python3 -I docs/calc/winter_model.py r2check build/f1-revision/pvgis/ser45/series.json
python3 -I docs/calc/winter_model.py scenarios build/f1-revision/pvgis/ser45-az233/series.json build/f1-revision/pvgis/ser70-az233/series.json build/f1-revision/pvgis/ser45/series.json
```

All four stdout bodies match their committed sections byte for byte (4526, 678, 548 and 11800 bytes respectively). Script SHA-256 values match the response:

- interlock: `d86cebffac9d1dc6578ead47758f73b8403d4ab83bb233c4adf418fa89d672f6`
- winter: `0235f8dc2495c511e9f5df3c74b9a797b033b314d26bf16e1c6f81ec37dd1cf2`

The winter code diff changes only provenance and the sensitivity floor, 156.0 to 151.4 uA. The codex/r2check bodies are unchanged from revision 3. The scenarios body differs only in that printed floor; all rounded result rows remain identical. The 3/8/14-cell tables, new/faded and -15/0/+15 percentage-point biases, reproduce; 8 faded cells pass all modelled adaptive cases. The read-cost limits remain 3.99/6.39 mAh and 3.98/6.38 mAh at the higher floor, conditional on the stated common scaling of read modes. This round audited the diff and reran the model; it did not repeat r4's separate hourly recurrence. The corrected longest-run implementation is unchanged.

The interlock reproduces cold +0.0380 C and hot +44.3386 C, but reproduction is not validation of the omitted parameter combinations. Static energy trips remain +2.71/+3.09 and +41.52/+41.33 C. If corrective hardware changes those, rerun the winter scenarios.

R-P7 now satisfies the requested terminal-power comparison. The USB suspend subtotal and charger-bias correction are present. F6 must validate whole-board currents including the host conditions and tolerances. The formal [Samsung Ver 1.1](https://docs.telitpower.com/pdf/li-ion/INR18650-35E.pdf) was checked in the cached manufacturer PDF; the revised provenance and operating limits agree. U3 supplier qualification, real cell temperature below -10 C, gradient/drift, and voltage-to-SOC recovery remain explicit limitations, not achieved qualifications.

### R5-N2 — Rail and complete-stop assumptions must remain visible

U4's threshold/delay arithmetic, 29.5 us gate discharge and 2.653 V endpoint are internally consistent with the declared resistor/capacitance assumptions. Reducing the LM4041 feed to 20 kohm gives the stated 70.4 uA at that endpoint. The delay state now correctly holds Q9 off. The output-level-based FET selection is more useful than a threshold-voltage placeholder.

The 59.5 us number is **U4-to-chain opening**, not a maximum time until charge current stops. Q3's approximately 479 us is conditional on its assumed capacitance; charger response is still unbounded here. Keep a requirement for the complete current-stop response and permissible residual charge rather than treating “about a millisecond” as a proven maximum.

The [TPS3840 Rev E](https://www.ti.com/lit/ds/symlink/tps3840.pdf) VOH condition is above VIT+; scaling it into the hysteresis band remains explicitly assumed. Lower drive generally inhibits charging, but any minimum charging-current/energy claim in that band must respect the qualification. The 30 us detection figure also retains its specified excursion/load conditions.

The cached TPS7B6933 data specifies the 500 mA limit with OUT shorted to ground and output accuracy for a stated load range; steady interlock load here is only about 0.74 mA. Support the claimed global +50 V/ms slope and regulated upper rail for the actual loading/startup conditions, or label them as qualification assumptions rather than universal datasheet guarantees. The falling-slope calculation must include all discharge paths and effective capacitance. The six-node convolution is conditional on those slope bounds and its fixed circuit parameters; it cannot by itself qualify the regulator or arbitrary independent initial conditions.

## Gate recommendation and worktree limits

Close R5-M1–M3 at the calculation/architecture level, correct R5-m1, and carry the explicitly conditional device/layout/thermal checks into F2/F3/F6. ST source verification itself is now done and must not remain an unresolved prerequisite deferred to F2. The corrected TVS arithmetic appears compatible with the LT3652 absolute limit under the stated allowances; no replacement charger, pack or owner decision is requested.

Review file left uncommitted. No designer files, firmware, main checkout, branches, commits or remotes changed. No hardware, schematic/layout validation, flashing, or procurement was performed.
