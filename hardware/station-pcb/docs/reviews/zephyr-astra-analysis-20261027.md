# Zephyr F1 — bounded analysis of interlock filters and panel protection

27 October 2026 · **pcb-analysis-astra** · provider **openai-codex**, model **gpt-6-astra**, session `zephyr-astra-analysis-20261027` (runtime session header verified).

**Analysis only. F1 remains NOT READY. No component, requirement, schematic, phase or purchasing approval is implied.** LT3652, the 35E pack, the zero-degree charging constraint and the 11.3 A surge requirement remain unchanged.

## Executive conclusion

1. **Do not repeat the existing numerical search at higher density.** Two pieces of the filter argument admit short analytic treatments: the continuous slope minimum in the declared NTC interpolation model, and a uniform physical-network tail bound. They do **not** repair the unvalidated integration before the tail.
2. **A small, useful interlock alternative exists:** remove the external cold-feedback resistor RHYS, retain the TLV3012B's internal hysteresis, and re-centre the cold divider to approximately **24.15 kΩ** on its lower leg. This eliminates OUT1 as an independent analog-network source. A conditional design budget gives **0.132 K cold reserve**, **44.619 °C hot ceiling**, and cold-on **3.066 °C**, without relaxing the 0–45 °C or +3.1 °C requirements. These are **static feasibility calculations against explicitly proposed dynamic/thermal budgets**, not a certificate for the changed circuit.
3. **“Use the 3 kW 30 V TVS” is not a solution.** An old ST Rev 5 PDF makes SMC30J30CA look attractive; the newer, retrieved **DS8598 Rev 7** changes the relevant data and gives **40.257 V at 11.3 A and initial Tj=57 °C, before layout overshoot**. SMC30J33CA is worse. SMC30J28CA is the interesting candidate, at **37.346 V**, but has **28 V stand-off below the calculated 28.0476 V cold Voc**, and does not solve switch commutation.
4. **The eFuse needs a complete pin-pair envelope, not only IN-to-ground.** Besides OUT-to-RTN ≥−0.3 V, TI specifies **IN−OUT ≥−60 V** over temperature. A negative-input envelope near −40 V combined with an output capacitor initially near +28 V cannot be certified against that rating. The ±70 V transient entry is restricted to TA=25 °C. This is an additional condition to resolve, not a claimed observed failure.
5. Recommended next owner decision: **a bounded architecture revision using the simpler one-source interlock, and a partitioned surge design with independent LDO protection**. First resolve whether TPS26600 can be retained with documented negative-transient limits/passive protection. If not, explicitly authorize a different protection switch/front end, **not a different charger**. Do not start another cosmetic “fixed” round or F2.

## 1. Scope and evidence

Working directory: `/Users/mikolaj/Documents/MIKO/zephyr-station-pcb/hardware/station-pcb`.

Baseline and final checked HEAD: `fd1c0fef29b1ecaca7e0de6280eb5828806d3b7c`, branch `hardware/station-pcb`.

Read current `docs/STATUS.md`, `REQUIREMENTS.md`, all of `ARCHITECTURE.md`, `reviews/F1-response-r6.md`, all of `reviews/F1-pi-r7.md`, and `F1-pi-r6.md`; inspected the relevant calculation implementation and manufacturer PDFs. The status document predates the r7 disposition: its “waiting for review” wording is not the current gate verdict.

All scratch work, retrieved PDFs, extracted text, images and calculation outputs are under:

`/tmp/pcb-astra-analysis-20261027/`

No paused designer, reviewer or enclosure agent was contacted. No delegation, Reason Network, installation, configuration change, CAD/build, winter-model rerun, hardware test, order or commit occurred.

Evidence categories used below:
- **Published:** explicitly stated manufacturer limit, with its test conditions.
- **Analytic/model:** mathematical implication of the declared circuit/model assumptions.
- **Proposal:** a target or changed topology needing owner approval and independent verification.
- **Unknown:** no sufficient guarantee obtained; not replaced by typical curves or sampled tests.

## 2. Interlock: what can be established simply

### 2.1 Continuous NTC slope — remove finite-difference sampling

For a log-linear table segment, write

`R(T) = Ra exp(b(T−a))`, with `b = ln(Rb/Ra)`.

The divider's normalized slope magnitude is

`m(T) = |b| RS R / (RS + R)^2`.

For a fixed segment, `q/(1+q)^2`, with `q=R/RS`, has a single **maximum** at q=1. Its minimum over a closed interval is therefore at an endpoint. Consequently, evaluate both ends of every intersected segment and the resistance/drift/RS extreme ratios; include the one-sided values at integer-temperature boundaries. There is no temperature sampling or root search in this reduction.

The scratch calculation reproduces r7's cold result:

- Cold band: approximately 0.1770–3.6384 °C; minimum **0.009718282777/K**, on the segment beginning at 1 °C, minimum-table column, +0.5% drift, RS=11.979 kΩ.
- Hot band: approximately 40.7669–44.3195 °C; minimum **0.007876692004/K**.

Use outward-rounded lower values, e.g. **0.0097/K and 0.00787/K**, or avoid kelvin conversion altogether by evaluating the forbidden-temperature voltage inequality directly.

**Limit:** this is continuous coverage of the project's **log-linear interpolation model**, not manufacturer certification that an actual NTC follows that interpolant between table entries. The R–T envelope/interpolation premise remains explicit.

### 2.2 The omitted physical RC tail has an elementary bound

For fixed allowed components, the six-node passive network obeys

`C e_dot + G e = 0`

after subtraction of a source step's final equilibrium. Both C and G are symmetric positive definite. With capacitor energy `E = eᵀ C e / 2`,

`E_dot = −eᵀ G e ≤ −2 λ E`, where `λ ≥ λmin(G)/λmax(C)`.

The resistive network has separate 3-node, 2-node and 1-node blocks when the ideal sources are grounded. Its inverse-conductance trace is exactly

`trace(G⁻¹) = 3 R0 + Rin1 + Rin2 + 2 R3 + Rf1 + R5`,

where `R0=RS||NTC`, `R3=RC1||RC2||RHYS`, and `R5=RH1||RH2`.

Using independently worst allowed resistors, including **NTC open**:

- `trace(G⁻¹) ≤ 100569.265 Ω < 110000 Ω`;
- `λmin(G) ≥ 1/trace(G⁻¹)`;
- a capacitance row-sum bound gives `λmax(C) < 800 pF`;
- grounded capacitances give `C ≥ 0.5 pF · I`.

Thus the physical energy norm decays with time constant **<88 µs**, conservatively **<100 µs**. At 50 ms, its amplitude factor is below `exp(−500) < 2⁻⁵⁰⁰`.

For the finite-resistance bands used by r6, NTC ≥about 132 Ω also gives `||G||₂ <0.01 S`. Together with the capacitance bounds, this bounds derivative tails as well as step tails. Unit-step equilibrium coordinates are 0 or 1; applying these norm bounds to the finite sums defining Δ and h′, their integrals and the specified rail slopes permits an intentionally loose **10¹²·2⁻⁵⁰⁰ < 3.1·10⁻¹³⁹** prefactor bound on the residual voltage contribution. Allocating **10⁻¹³⁰ V** is ample in this model.

This is a physical-network tail argument, **not** a proof that the numerical comparison solution or quadrature up to 50 ms was enclosed. It assumes fixed components, reachable source histories and the declared capacitance box. A hard short should be handled by reducing the algebraic circuit, rather than extending the derivative norm through infinite conductance.

### 2.3 What remains genuinely open in the existing computation

R7-M1 stands. Endpoint-only switching checks can miss interior changes; endpoint rectangles are not universal upper quadrature; floating matrix exponentials need roundoff/remainder enclosures. The analytic tail above fixes only one separable piece.

A bounded numerical repair should use:

1. outward-rounded coefficient/state intervals;
2. a whole-step enclosure (validated Taylor/Picard or equivalent), not an endpoint gap correction;
3. integral-state or whole-interval integrand bounds for positive/negative kernel area;
4. the analytic tail and analytic NTC reduction above;
5. the same treatment for W/lag, OUT1 and beyond-band cases.

For example, if an interval proof supplies `|f′|≤M` over a step of width h, `h·max(f_left,f_right) + M h²/2` is a conservative integral allowance. The missing ingredient is the **proved whole-step M**, not denser endpoints. A numerical convergence comparison remains a diagnostic.

**Stop condition:** if this cannot be certified inside an agreed computation budget, report failure to enclose. Do not increase samples and call the result guaranteed.

## 3. NTC heating and rail qualifications matter more than another decimal

The cached Shiheng approval sheet, **MF52A103F3950(A1), C0, 2026-05-28**, p.3, says thermal dissipation in still air is **approximately 2 mW/°C** (`约2`), and thermal time constant approximately 12 s. It does **not** give a guaranteed minimum dissipation coefficient.

There is also a small arithmetic limitation: r6's approximately 0.099 K calculation uses the **nominal cold trip**, not the maximum over its whole cold band. With RS=11.979 kΩ, VREG=3.4 V and resistance near the band's low end, heating is approximately **0.104 K if δ=2 mW/K**. This is not proof that a forbidden charging state occurs; it shows that the nominal calculation does not establish the universal 0.100 K allowance.

A simpler all-resistance bound is

`P_NTC = V² R/(RS+R)² ≤ V_TOP²/(4 RS_min)`.

Here this is **0.241256 mW**. Therefore:

- a 0.100 K global allowance needs guaranteed effective δ ≥2.413 mW/K;
- a **proposed 0.150 K allowance** needs effective δ ≥**1.609 mW/K** (round requirement upward to 1.61).

The latter is a more useful design target, but the actual mounted sensor must meet it. “Approximately 2” is not a supplier guarantee of ≥1.61. Mounting, coating, contact, cable conduction and transient NTC-to-cell difference need to be included. The **0.5 K gradient must bound the coldest/hottest cell versus the sensor during transients**, not just a steady enclosure measurement.

Unchanged conditions still needed:
- VREG ≤3.4 V including startup, at the actual load;
- global rail-slew/discharge inventory, not only a shorted-output current-limit entry;
- supervisor/gate drive and latency at their actual conditions;
- default-off behavior during brown-out and incomplete timer reset;
- comparator and charger complete-stop behavior.

A positive trip reserve must also cover temperature movement during complete-stop latency. “Not measurably changing in 10 ms” is not a numeric bound. Keep the current-stop and hot-plug residual-charge requirements separate from the analog filter proof.

## 4. A concrete simpler filter candidate — not an implementation

### Proposed topology change

- Remove RHYS from OUT1 to the cold tap.
- Use TLV3012B's existing internal 2–8 mV hysteresis.
- Re-centre the cold lower divider leg to approximately **24.15 kΩ**; retain RS=12 kΩ and the hot DC divider.
- Treat C_HOT as still **unapproved**. The calculations do not authorize fitting it.

The 24.15 kΩ effective value can be realized, for illustration, by `24.3 kΩ || 3.9 MΩ =24.14953 kΩ`. This is not an MPN/BOM choice. Independent resistors with the same fractional tolerance keep the parallel equivalent inside that fractional tolerance.

**Structural benefit:** OUT1 no longer enters the analog RC network through a feedback resistor. Its gate-current effects remain part of VREG's load/slew inventory, but the separate arbitrary-OUT1 impulse-area term disappears. This directly removes the term responsible for most of r6's hot numerical allowance.

### Explicit proposed certificate budget

The following are **targets to prove for the new network**, not inherited r6 results:

| Quantity | Proposed target |
|---|---:|
| W range while charging is possible | 2.4825–3.4004 V |
| Cold unsafe filter error | ≤0.8 mV |
| Hot unsafe filter error | ≤5 mV |
| Self-heating allowance | ≤0.15 K, requiring effective δ ≥1.61 mW/K |
| NTC-to-cell gradient | ≤0.5 K |
| Cold leakage allowance | ≤0.008 K, within the existing 20 nA premise |

Under that contract, the static corner calculation gives:

- minimum electrical cold-off: **0.823027 °C**;
- cold reserve after all tabled allowances: **0.131805 K**;
- hot upper limit: **44.618249 °C**;
- static energy-corner cold off/on: **2.897697 / 3.065494 °C**;
- minimum cold hysteresis in this sweep: approximately **0.058 K**.

Thus the proposal can budget materially more than r6's 0.0145 K without changing the zero-degree limit or cold-on ≤3.1 °C. It is not enough to merely remove RHYS: with the unchanged 24.3 kΩ tap and the more honest 0.15 K heating allowance, this same contract leaves only **0.0122 K**.

**Tradeoffs:** smaller hysteresis needs noise/chatter qualification; cold-off moves warmer even though cold-on improves. The winter model must be rerun after a candidate is selected, because those two changes do not establish monotonic improvement in harvested energy. No winter claim is made for this candidate and no full winter run was performed.

A precision-comparator redesign is a fallback, not the first recommendation. For example TI's retrieved TLV902x/903x Rev H has ±2 mV full-temperature offset entries at its stated conditions, but **no internal hysteresis**, only typical switching entries, and its revision history removes POR. It is not a drop-in way to assume all startup/OUT1 problems disappear. Its common-mode/PSRR limits, input leakage and larger supply current would also enter a new budget.

## 5. SMC30J research: exact variant and revision are decisive

### 5.1 Retrieved evidence and the source gap

Real manufacturer-authored PDFs were downloaded and rendered:

- **DS8598 Rev 5, March 2020**, 13 pages, LCSC mirror.
- **DS8598 Rev 7, January 2022**, 13 pages, a different LCSC mirror.

Search indexing indicates **Rev 8, January 2024** exists at ST. Direct ST endpoints failed with HTTP/2 errors/timeouts; the web fetch also failed. **Rev 8 was not retrieved or verified.** No security/network configuration was changed. Part adoption therefore still needs the current authoritative revision.

The older Rev 5 has different VBR columns/RD values. In Rev 7, Table 2 gives RD in **mΩ**, and includes minimum/typical/maximum VBR. Do not read the old typical breakdown as a maximum or mix revisions.

### 5.2 Conditional clamp comparison

Rev 7 Table 2 notes 1–3 support:

`VCL(I,25) = VCL_rated − RD(IPP_rated − I)`

and the stated temperature multipliers for VBR and VCL. The following uses **11.3 A and an assumed initial Tj=57 °C**, with **no inductive/commutation overshoot added**. The SM15T row uses its already archived Rev 8.

| Variant | VRM | VBR min/max at 25 °C | 10/1000 VCL / IPP / RD | VCL at 11.3 A, 57 °C | Cold VBR min at −30 °C |
|---|---:|---:|---:|---:|---:|
| SM15T33CA | 28.2 V | 31.4 / 34.7 V | 45.7 V / 33 A / 0.333 Ω | 39.6804 V | 29.7075 V |
| SMC30J26CA | 26 V | 28.9 / 31.9 V | 42.1 V / 71 A / 0.144 Ω | 34.5431 V | 27.3582 V |
| **SMC30J28CA** | **28 V** | **31.1 / 34.3 V** | **45.4 V / 66 A / 0.168 Ω** | **37.3460 V** | **29.4237 V** |
| SMC30J30CA | 30 V | 33.3 / 36.9 V | 48.4 V / 62 A / 0.185 Ω | **40.2567 V** | 31.4868 V |
| SMC30J33CA | 33 V | 36.7 / 40.5 V | 53.3 V / 56 A / 0.229 Ω | **44.4417 V** | 34.6815 V |

Alpha maxima are 9.7, 9.8, 9.9 and 10.0 ×10⁻⁴/K for the four SMC rows respectively.

**Revision trap:** Rev 5's SMC30J30CA RD=0.215 Ω yields **38.6875 V** in this calculation. Rev 7's RD=0.185 Ω yields **40.2567 V**. The old PDF would lead to the wrong recommendation.

**Naming trap:** SM15T33CA's suffix is not equivalent to SMC30J33CA's stand-off. The 3 kW family's suffix is VRM; matching “33” does not preserve the clamp.

### 5.3 Cold stand-off, power, temperature, package and stock

The stated panel assumptions give `22.4 ×1.05 ×(1+0.0035×55) =28.0476 V`.

- SMC30J26CA cannot be credited as non-avalanche at that cold Voc: its calculated minimum cold breakdown is lower.
- SMC30J28CA has **breakdown headroom**, but not a published **28.0476 V cold leakage guarantee**. Rev 7 specifies 0.2 µA at 25 °C and 1 µA at 85 °C at VRM=28 V. Those entries cannot silently become a guarantee above VRM or at −30 °C. Under the manufacturer's VBR temperature formula and monotone I–V behavior, being below the 1 mA breakdown test point supports an engineering sub-1 mA argument; it does not preserve the quoted microamp leakage limit. Get supplier confirmation/accept an explicitly qualified leakage budget, not a rounded-down Voc.
- CA is bidirectional. The A version would forward-conduct on a reversed panel; substitution changes the reverse-connection design.
- Rev 7 Figure 3 gives ample pulse-power headroom at 57 °C (even the more pessimistic branch is >2.5 kW; the application peak is around 0.42 kW for the 28CA). This does not prove temperature or voltage clamp under every waveform.
- Figure 6 makes pulse-duration dependence explicit. The 10/1000 tabulated formula and its applicability to the admitted waveform/tolerances must remain attached; a sampled or arbitrary front/tail envelope is not automatically the manufacturer's test waveform.
- Figures 11/12 are thermal characteristic curves for **FR4 with 70 µm copper**, not a universal guaranteed RθJA. The existing 120 K/W, +5 K local heating and repeated-pulse assumptions must be re-established for any candidate. In particular, input/output capacitor energy and switching dissipation cannot be omitted from the new thermal ledger.
- SMC package: overall terminal span **7.75–8.15 mm**, body E1 **6.60–7.15 mm**, D **5.55–6.25 mm**, height A1 **1.90–2.45 mm**; recommended land pattern overall **8.19 ×3.14 mm** (pp.6–7). Same package class is not automatic footprint/thermal qualification.
- A directly downloaded LCSC product page identifies **SMC30J30CA, C1977363**, with embedded stock **0** and one-piece listed price **$1.9723** on this retrieval. This does not establish JLC assembly availability. No verified LCSC stock/MPN match was obtained for SMC30J28CA. Search snippets about distributor inventory are not procurement evidence.

## 6. Surge: separate the problems instead of spending all margin at VIN

### 6.1 Required circuit/state ledger

The next architecture proof needs an explicit equivalent circuit containing:

- generator/panel impedance, cable inductance and current envelope;
- TVS branch inductance, its capacitance and nonlinear clamp model;
- C_IN **minimum and maximum**, ESR/ESL, and its initial voltage;
- the switch and its permissible conduction/open/recovery states;
- separate OUT-pin capacitance and OUT-to-VIN inductance;
- VIN capacitance bounds and load behavior;
- LDO diode/R/C branch;
- RTN behavior during negative input, and **each relevant differential pin rating**.

Fast-trip threshold/delay and reverse turn-off entries are typical in the inspected TI table. They cannot bound interrupted current. External 11.3 A does not bound current supplied by a charged C_IN on recovery.

For R7-M2, a front-time upper limit is not a derivative limit. Either obtain an admissible current-slew specification at the relevant branch, or include the branch L/C transient explicitly. Do not replace peak di/dt by Ipeak/10 µs without that evidence.

### 6.2 Negative input also challenges IN−OUT

TI SLVSDG2G §7.1, p.6 specifies:

- IN and IN−OUT: −60 to +62 V;
- the 10 ms −70/+70 V entry: **TA=25 °C**;
- OUT relative to RTN: −0.3 to +62 V;
- recommended input falling slew: ≤20 V/µs (§7.3; also §11.1).

An input envelope of −39.70 V with OUT initially near +28.05 V permits a difference near **−67.75 V**. Even SMC30J28CA's conditional −37.35 V envelope plus that output gives approximately **−65.40 V**. Independent bounds alone do not prove these combinations occur, but the architecture has not excluded the precharged-output state, so it cannot certify the −60 V differential limit.

A series reverse-blocking diode before the eFuse is one possible remedy to analyse: it stops the negative cable source pulling IN down while local capacitance holds it. Its reverse rating, leakage, displacement/recovery charge, pin slew and normal voltage loss must be bounded. It does **not** fix positive-opening OUT undershoot.

### 6.3 Useful passive inequalities — with their initial states attached

For an isolated output commutation model consisting of local C_OUT, downstream C_VIN, connecting L and nonnegative R, with no external current/load during the interval:

`Ceq = C_OUT C_VIN/(C_OUT+C_VIN)`

`Vbar = (C_OUT Vout0 + C_VIN Vvin0)/(C_OUT+C_VIN)`

`A = sqrt((Vout0−Vvin0)^2 + L I0^2/Ceq)`.

Dissipation cannot increase the differential-mode energy, so

`Vout ≥ Vbar − C_VIN/(C_OUT+C_VIN) · A`,

`Vvin ≤ Vbar + C_OUT/(C_OUT+C_VIN) · A`.

This is a timing-independent way to design/check a **partitioned** local capacitor network. It is not valid with an unmodelled source/load, and it does not supply I0 or the initial capacitor voltages. In particular, a charged-output case that passes does not cover recovery from a discharged output. C_OUT alone cannot be declared a universal cure for −0.3 V.

An OUT Schottky must satisfy

`VF_max(I,T) + local inductive excursion ≤0.3 V`

for the entire interrupted-current envelope, or the device maker must supply an applicable transient exception. A typical −0.5 V waveform is not compliant with the inspected rating. No qualifying Schottky/current envelope was established here.

Adding a damping/limiting resistor is practical but not free: at 0.54 A, **0.47/1.0/2.2 Ω** dissipate **0.137/0.292/0.642 W** and lose **0.254/0.540/1.188 V**. It must sit in the actual capacitor-discharge path. Do not credit the panel current limit for a local capacitor discharge. Include the resulting MPPT/input-voltage and winter-energy effect.

### 6.4 Independent LDO protection is an inexpensive simplification

The LDO branch carries milliamps, unlike the main surge path. It should not depend on a 30 mV charger margin or an unbounded opening spike.

**Candidate:** keep its series resistor and feed diode, and add a separately specified low-current shunt clamp plus local capacitor. Use a real manufacturer maximum, not the rejected Zener's incomplete temperature coefficient.

As a deliberately oversized existence example, **SMC30J22CA** has full-rated VCL=35.5 V at 85 A, alpha max 9.6×10⁻⁴/K. At a **proposed** 75 °C initial-junction ceiling, the scaled full-rated clamp is **37.204 V**, leaving 2.796 V to the LDO's 40 V operating limit without using an optimistic lower-current RD interpolation. With upstream voltage bounded to 62 V and 1 kΩ ±1%, branch current is at most **62/990 =62.63 mA**, before any benefit from the clamp voltage or diode drop.

This is a candidate design direction, **not a qualified clamp**: verify the current/pulse regime, low-current monotonic envelope, local inductance/capacitance, continuous conduction at normal panel Voc, pulse thermal energy, source voltage bound and current datasheet revision. A smaller appropriate TVS may be sufficient. Its normal conduction costs panel power, not battery sleep current; USB operation must remain unaffected.

A bare RC filter is also analysable, but only with an established excursion duration/area and initial voltage. For a source bounded by M over duration t, ignoring load gives `vC(t) ≤ M−(M−vC0) exp(−t/RC)`. Without a duration/volt-second bound, “1 kΩ and a capacitor” does not prove protection; diode-held charge and repeated events must be included.

**Target ≤40 V, not just ≤45 V:** the interlock's regulated-rail argument depends on operation during the event. Surviving the LDO's short-duration absolute maximum alone does not establish its output behavior.

### 6.5 Why a two-stage main clamp is an option, not a ready answer

A primary TVS, series impedance and secondary clamp near VIN can isolate C_IN recovery energy and reserve real charger-voltage margin. A lower-voltage secondary TVS can be used after reverse blocking. However, the secondary branch's maximum current must come from the complete capacitor/source state ledger, not 11.3 A alone. Neither stage automatically fixes the eFuse OUT negative rating or IN−OUT on a negative pulse.

If those pin limits cannot be met passively with qualified parts, a protection controller/switch with documented suitable negative-transient tolerance or guaranteed limiting/timing is the cleaner larger change. No such replacement was selected or approved in this analysis. There is no need to reopen the LT3652 merely because the present eFuse proof is missing.

## 7. Options A/B/C and recommendation

**These labels are new report options, not the historical A–D.** Historical “leave it to F2” and “reduce the surge to 8 A” remain unapproved and are not offered as closure.

| Option | Interlock | Surge | Tradeoff / stop condition |
|---|---|---|---|
| **A — preserve topology, obtain a real certificate** | Keep current circuit; analytic slope/tail plus validated finite-time enclosure; qualify heating and rail | Keep selected parts only if TI supplies applicable guarantees or a complete passive pin-envelope proof succeeds | Least part churn, highest proof fragility; original cold/VIN margins are tiny. Stop if guarantees/enclosure are unavailable, not at another passing sample set |
| **B — small structural simplification (recommended direction)** | Remove RHYS, re-centre cold divider near 24.15 kΩ; prove the stated one-source filter/thermal contract | Independent LDO clamp; analyse SMC30J28CA, reverse-input isolation, local OUT/VIN capacitance and damping as separate blocks | Reduces the interlock proof and separates the LDO. Still conditional on current TVS source, cold leakage and a valid TPS26600 pin envelope; not an approved BOM or gate pass |
| **C — replace the protection/interlock building blocks where guarantees are missing** | Precision comparator/rail architecture with explicit startup and noise qualification | Different protection switch/controller or a fully specified two-stage front end, retaining LT3652 and 11.3 A | More engineering/BOM change, but can avoid forcing a −0.3 V pin into an unqualified Schottky commutation case. Exact parts and proof required before adoption |

**Recommendation:** authorize B as a **bounded next design-analysis brief**, with the eFuse negative/differential envelope as the first surge go/no-go question. If that cannot be supported by published/supplier data or a complete passive proof, stop and ask for C. Do not commit a provisional SMC30J substitution and then try to make the numbers fit.

Owner approval would be required for RHYS/divider changes, C_HOT, any TVS/diode/resistor/capacitor changes, a new protection switch, and any changed energy assumptions. No approval is needed merely to retain the existing “not ready” disposition. Nothing here asks to weaken the charging-temperature or surge requirement, change the pack, or replace LT3652.

## 8. Small r7 measurement corrections

Document physical limits separately from instrument uncertainty:

- Healthy-charger current: pass only if **measured mean + upper uncertainty ≤1 mA**. With ±0.5 mA uncertainty, an indicated 0.5 mA is the largest uncomplicated passing indication, not 1 mA.
- Charge: require **measured Q + upper uncertainty ≤Q_limit**. If the uncertainty really is ±5% of reading, indicated limits are ≤0.17143 C for a physical 0.18 C and ≤0.06190 C for 0.065 C. Include offset/time-base terms if present.
- Voltage: define a permitted physical increment first, then guard-band it; ±2 mV instrument uncertainty is not itself a permitted physical rise.
- Gate stage: 1.56 A×129.5 µs = **0.20202 mC**, combined 2.004 A gives **0.259518 mC**. Round upward and say per-charger versus combined. Existing rounded total charge budgets are not invalidated by that small correction.

No project document was edited.

## 9. Reproduction and source manifest

### Calculations

Scripts and outputs in the scratch directory:

- `analysis.py` → `analysis-output.txt`: Decimal TVS arithmetic; analytic segment-endpoint slope evaluation; cold voltage headroom; RC-tail constants; NTC heating; measurement guards.
- `candidate-static.py` → `candidate-static.txt`: explicitly unapproved RHYS/divider static variants and proposed error budgets. Loads the baseline functions using `runpy` without executing their main program.
- `baseline-surge.txt`: fresh baseline surge stdout, **2116 bytes**, found byte-for-byte as the complete recorded stdout body. This reproduces the baseline arithmetic, not its missing proof.
- `calculation-hashes.txt`, `status-before.txt`, `head-before.txt`, `lcsc-availability.txt`, retrieved PDFs/text/rendered pages.

Commands:

```sh
python3 -I -B /tmp/pcb-astra-analysis-20261027/analysis.py
python3 -I -B /tmp/pcb-astra-analysis-20261027/candidate-static.py
python3 -I -B docs/calc/surge_bound.py
```

These ran successfully. No multi-process filter search or winter simulation was run. The scripts' decimal/float values are arithmetic evidence; the report identifies separately which inequalities supply all-range coverage.

PDF extraction/rendering used the already installed PDF skill interpreter and `scripts/read_pdf.py`, with outputs only in scratch. Relevant table columns, notes and thermal/power plots were visually inspected.

### Manufacturer sources

**ST SMC30J DS8598 Rev 7**, primary basis for candidate numbers:

- URL: `https://datasheet.lcsc.com/datasheet/pdf/6f55dd2200aa89e2c7a9b89e94f5b2c2.pdf?productCode=C5456170`
- Local: `smc30j-new.pdf`
- SHA-256: `cc1a4a76aad467473faddd2d008074a1cd9fa611f623ccc2f75e9bd9eabe0a57`
- pp.2–3 ratings and Table 2/notes; pp.4–5 curves; pp.6–7 package; p.10 ordering; p.12 revision history.

**ST SMC30J DS8598 Rev 5**, retained to demonstrate the revision trap, not for adoption:

- URL: `https://datasheet.lcsc.com/datasheet/pdf/314776ddfacc07fec3d115652cc86ca3.pdf?productCode=C1976218`
- Local: `smc30j-lcsc.pdf`
- SHA-256: `e16750bc0aa9528c800485550ee9dff5482c7494e59c8784ec0a3446fb168913`

**ST SM15T DS0683 Rev 8**, baseline, cached reviewer source hash rechecked:

- URL: `https://datasheet.lcsc.com/datasheet/pdf/90dac3b1fa53d3a9bca01f3963dc7892.pdf?productCode=C81476`
- Cache: `/tmp/pcb-r6/st-lcsc.pdf`
- SHA-256: `3d4c7f4c7f31852cf00c9631b55bf65b51582036646e1c8386a098656edb9144`.

**TI TPS2660 SLVSDG2G**, cached manufacturer PDF:

- URL: `https://www.ti.com/lit/ds/symlink/tps2660.pdf`
- Repository cache: `build/f1-revision/research/power/tps2660_ti/tps2660.pdf`
- SHA-256: `b781cbce51984715771bde540df2b36404b4fae4b41e27166c84c19b6598e1de`
- §7.1/7.3, pp.6–9 ratings/characteristics/timing; §11.1/12.1, pp.38–39 transients/layout.

**Shiheng MF52A103F3950(A1) C0 approval sheet**, cached manufacturer PDF:

- Cache: `build/f1-revision/research/power/ntc_mf52_shiheng/MF52A103F3950_lcsc_copy.pdf`
- SHA-256: `9a27be6a3fc770e4d9969bd9a2f4aebdc2eca09114d781c852cbf9ba68fc3baa`
- p.3 electrical/thermal characteristics; R–T tables later in document. Original exact supplier download URL was not reconstructed; this is explicitly a cached source.

**TI TPS7B69 SLVSDI2**, baseline LDO source:

- URL: `https://www.ti.com/lit/ds/symlink/tps7b69.pdf`
- Cache SHA-256: `209a5c9b66a11e9cb488a4cbb4b807df1dfddf6d598e422cf8079f10b1cd9929`
- Regulation/current-limit qualifications are retained from the inspected baseline/reviewer evidence; no broader startup guarantee was obtained.

**TI TLV902x/903x SNOSDA3H, November 2025**, fallback comparator caution only:

- URL: `https://www.ti.com/lit/ds/symlink/tlv9022.pdf`
- Local: `tlv9022.pdf`
- SHA-256: `874c1d4f5ec1c1b4bf6c714d3fe8623d57ad6bff18b83930e3894061a0701c8a`
- pp.11–12 electrical/switching conditions, §6.4.5 no internal hysteresis, revision history POR removal.

**Failed/current-source attempts:** ST `smc30j36a.pdf`, `smc30j16ca.pdf`, ST China `smc30j10a.pdf`, and web fetch of ST `smc30j58a.pdf`. None supplied a verified Rev 8 PDF. The gap remains; no search snippet was used as a replacement electrical specification.

## 10. Independent-review checklist and final boundary

An independent reviewer should check:

1. The segment-endpoint minimum argument, interpolation premise, and outward rounding.
2. The RC inverse-trace identity, capacitance spectral bounds and physical tail estimate; do not mistake it for certification of the finite-time solver.
3. Whether the mounted NTC has a defensible minimum dissipation and transient gradient bound.
4. The proposed one-source topology, full static corners, new W/kernel certificate, open/hard-short/hot-plug states, noise and complete-stop margin.
5. The selected/current ST revision and exact variant, cold leakage/stand-off, admitted pulse waveform and thermal/energy ledger.
6. All eFuse pin pairs, especially **OUT−RTN and IN−OUT**, at opening, negative surge and recovery, with capacitor initial states and no typical timing credit.
7. The LDO branch independently to its operating limit, and the changed source/USB/rail budgets.
8. Winter-energy rerun only once changed trips/losses are selected; no transfer of the old no-outage result by assertion.

**Final repository check:** HEAD remains `fd1c0fef29b1ecaca7e0de6280eb5828806d3b7c`; branch remains `hardware/station-pcb`; tracked and staged diffs are empty. Status remains exactly:

```text
?? docs/reviews/F1-pi-r7.md
?? enclosure/
```

Those pre-existing untracked paths were not modified/staged/removed. No repository writes were made. Deliverables are this report and authorized scratch files only. **No closure of R7-M1, R7-M2 or R6-M2 is claimed. Stop here pending a new owner/coordinator brief.**
