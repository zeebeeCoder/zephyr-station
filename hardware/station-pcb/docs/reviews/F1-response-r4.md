# F1 fourth review response

This is the response by `mobric/pcb-design-2` to [F1-codex-r4.md](F1-codex-r4.md), the Codex fourth review of F1 revision 3 at 8e02e77. The same designer session was earlier called `mobric/pcb-design`, `mobric/mikolaj-claude-60` and `mobric/pcb-opus-5-5`. The review is committed unchanged in 239a130. This response was written on 26.10.2026 and committed together with F1 revision 4 of [REQUIREMENTS.md](../REQUIREMENTS.md) and [ARCHITECTURE.md](../ARCHITECTURE.md), following the coordinator's brief for revision 4.

**Result: 5 fixed, 2 accepted, none disputed.**
- **Fixed:** R4-M1, R4-M2, R4-m1, R4-m2 and R4-N1. The revised documents now do what the review asked, or something that meets the same aim. Each row says which.
- **Accepted:** the notes R4-N2 and R4-N3. Their corrections and qualifications are now in the documents, and what they leave for F2, F5 and F6 is listed there.
- **Disputed:** none.

Revision 4 also folds in mobric's answers Q24 (a) and Q25 (a) and the enclosure plan for D11, all relayed by the coordinator on 26.10.2026. No question for mobric came out of this revision, so none is open. R4-M2's fix rests on one manufacturer formula that F2 confirms in ST's current datasheet; that is a check, not a choice for mobric.

In the "Where" column, § and D numbers refer to ARCHITECTURE.md and R- numbers to REQUIREMENTS.md, both as revised.

## Summary

| Item | Disposition | What changed | Where |
|---|---|---|---|
| **R4-M1** Two capacitors on the common NTC node invalidate the independent-filter ordering proof | **Fixed** | New filters: 680 pF on V_T itself, 10 kΩ with no capacitor into each V_T input, 27.0 kΩ and 330 pF on U1's tap, nothing on U2's tap. The script now solves the input network as one coupled circuit and bounds the comparators' input error for any VREG history within its slope limits, so short dips, restarts and retained charge are covered without U4's delay. The inhibit latency runs through U4, the gate resistors and the gate capacitance, and its endpoint, the 2.653 V falling floor, is in the sweep. Q9's state row is corrected. FET requirements now come from guaranteed output levels | D5, § 7 item 1, § 9, § 10; R-P4; [calc/interlock_trips.py](../calc/interlock_trips.py) |
| **R4-M2** Interpolating between breakdown and clamp ratings does not establish a maximum clamp curve | **Fixed** (F2 confirms ST's formula) | ST's SM15T33CA replaces the 5.0SMDJ28CA. ST publishes the maximum clamp at any lower current as VBR max + RD × I, which gives ≤ 39.31 V at 11.3 A from a +50 °C start. With a layout overshoot allowance, the TPS26600's IN stays ≤ 39.3 V and the LT3652's VIN ≤ 39.4 V. "VIN ≤ IN" is replaced by "VIN ≤ the highest IN so far". The LDO's Zener returns, with a bound independent of the TVS. Negative-pulse ratings and cold leakage are stated | § 1, § 2, D5, § 7 item 2, § 10; R-P1 |
| **R4-m1** The open-jumper suspend inventory omits the powered BQ25170 | **Fixed** | Suspend about 1.73 mA with the BQ25170's 0.6 mA IQ_IN, the LDO's 25 µA and the translators' 8 µA; still under 2.5 mA. The VBUS budget when charging includes the charger's own bias: ≤ 462 mA | D3, D5, § 7 item 4; R-F9, R-P11 |
| **R4-m2** Replace tentative 35E ratings with an identified product specification | **Fixed** | Samsung's specification Ver 1.1 replaces the tentative report: 2.65 V cut-off, 1.7 A standard and 2.0 A maximum charge, 18.55 mm diameter. Every figure that used the old data is checked; none of the results moves | § 4.1, § 9, D11, D13, Sources; R-P5, battery row |
| **R4-N1** R-P7's "none looser" has a model-dependent meaning | **Fixed** | R-P7 (b) lowered from 136 to 132 µA, as the coordinator asked: 132 µA × 3.4 V = 448.8 µW, not above 150 µA × 3.0 V = 450 µW. The sleep-floor sensitivity in `winter_model.py` follows | § 4.2, § 7 item 6; R-P7 |
| **R4-N2** Reproduction, independent pack check and conditional read-cost limits | **Accepted** | The read-cost limits are stated as belonging to the model, and F6 measures each read mode. `setup()`'s `listenForRequest()` at station.ino line 807 joins the F5 removal list. "Requests time out" becomes "go unanswered" | § 4.3, § 4.5, D13, § 6 item 1, § 7 item 7; R-P10 |
| **R4-N3** U3 is not yet qualified against a Samsung backup-overcharge limit | **Accepted** | U3 isn't called qualified; F2 asks Samsung or the distributor for an abuse limit, including the float's tolerance. F2 defines how the cells' −10 °C discharge limit is met or the load inhibited. The battery-connection exception is stated as a blind time that depends on overdrive, with the chargers' float as the permissible transient, and F6 tests two overvoltages | D5, D5.2, D13, § 7 item 1, § 9, § 10; R-P4, R-P5 |

The rows the review marked "partly" close through these rows:
- R3-M1 and R2-B1 through R4-M1;
- R3-M2 and R2-M3 through R4-M2;
- R2-M1 through R4-M1. The trips the winter model uses (the energy corner, +2.71 / +3.09 °C) don't change, because the new filters change no resistor ratio. The cell and recovery assumptions stay explicit, as the review asked;
- R3-N2 through R4-m2 (the cell's data) and R4-N3 (U3's qualification and the cold limit, now F2 items).

## Details

### R4-M1: fixed

- **The finding is confirmed.** Both 1 nF capacitors charged through the shared RS ∥ NTC, so revision 3's one-pole time constants for the V_T inputs were wrong. The new script solves revision 3's network as a check and reproduces the review: at 0 °C with the nominal NTC, the V_T inputs' slowest time constant is 27.462 µs against U1's tap's 27.069 µs, so the claimed ordering failed. Revision 3's "any rise rate" conclusion is withdrawn.
- **The new filters** (D5, "Input filters"):
  - one 680 pF C0G (± 5 %) on V_T itself, plus up to 50 pF of ESD diode, NTC cable and board;
  - 10 kΩ, with no capacitor, from V_T into each comparator input that sees it;
  - 27.0 kΩ and 330 pF C0G on U1's tap, after the node where RHYS joins; nothing on U2's tap.
- **The proof no longer rests on an ordering of time constants.** `interlock_trips.py` solves the input network as one coupled RC circuit of six nodes: V_T, both 10 kΩ branches, U1's tap and its filter, and U2's tap. It includes the comparators' input capacitance, 1–10 pF to AGND at each input and 0–8 pF between a comparator's two inputs (TI gives 2 and 4 pF typical; the ranges are assumed), and 0.5–5 pF at U1's tap node.
  - **Method:** C = LLᵀ (Cholesky), then the symmetric matrix L⁻¹GL⁻ᵀ is diagonalised (Jacobi), which gives exact step responses for any capacitances.
  - **Error bound for any history of VREG.** Each input follows the network's step response applied to VREG's slope. The error between a comparator's two inputs, beyond their static difference, is therefore bounded by 50 V/ms × ∫ (the "charge" input leading)⁺ + 110 V/s × ∫ (it lagging)⁺, where 50 V/ms and −110 V/s are VREG's slope limits. That covers slow and fast rises, partial dips, fast restarts and any charge left on the capacitors. It doesn't use U4's delay, which the documents still decline to rely on after a short dip.
  - **Slopes.** VREG rises at most 500 mA (the TPS7B69's maximum current limit) / 10 µF = 50 V/ms. It falls at most 1.1 mA / 10 µF = 110 V/s: the LDO doesn't sink, the input diodes block backflow, and the load is ≤ 1.051 mA with every gate charging (0.738 mA steady). Revision 3 used 1 mA and 100 V/s.
  - **Coverage.** Every tolerance corner (5 % capacitors, 1 % filter resistors, the parasitic ranges: 2560 corners for U1, 640 for U2), plus 300 random interior points, at NTC values across each trip band ± 0.25 K. Beyond each band, where the comparator already says "do not charge", the script checks that the static distance from the trip exceeds the error at every NTC value out to open (U1) or nearly shorted (U2): it does, by ≥ 59 mV.
  - **Results** ([calc/interlock_trips_output.txt](../calc/interlock_trips_output.txt)): U1 ≤ 0.856 mV (0.452 mV rise term, 0.405 mV fall term), 0.032 K at the falling floor; U2 ≤ 0.392 mV, 0.018 K. Mean delays: U1's tap 10.62–12.29 µs against its V_T input's 5.35–7.01 µs; U2's tap ≤ 0.03 µs against its V_T input's 2.09–2.94 µs. So a rise mostly leans both comparators toward "do not charge", but the proof doesn't depend on that.
  - **Checks on the solver:** a single pole and a two-node ladder against their closed forms, the Elmore delay, and the time grid at 60, 200 and 600 points per decade, which agree.
- **The complete inhibit latency** (D5, "Valid rail"). From VREG reaching 2.6595 V, 10 % below U4's lowest threshold, to Q9 and Q10 off:
  - ≤ 30 µs for U4 (tP_HL; the 100 kΩ gate resistor leaves its output nearly unloaded, near the datasheet's 10 pF condition);
  - ≤ 29.5 µs for the gate to fall through 100 kΩ ∥ 1 MΩ from at most 3.09 V to 0.3 V, with U4's output at ≤ 0.2 V and a gate capacitance ≤ 100 pF, Miller charge included (an F2 requirement);
  - VREG falls ≤ 6.5 mV meanwhile, so the comparators decide down to **2.653 V, the falling floor**, and the sweep now includes it. Revision 3 left its last 3 mV out, as the review noted.
  - After that the stop is decided. Q3 turns off within about 0.5 ms (≤ 1 nF, assumed), and each charger stops in its own response time, which F6 measures. That only delays a decided stop by about a millisecond.
- **Recomputed safety corner,** VREG at the falling floor, filter error included: cold off **+0.038 °C** (must be ≥ 0), hot off **+44.339 °C** (must be ≤ 45). Rounded, the table reads +0.04 / +0.42 / +44.34 / +44.10 °C. The first three columns and the energy corner (+2.71 / +3.09 / +41.52 / +41.33 °C) are unchanged, because the filters change no resistor ratio. The hot hysteresis range widens from 0.07–0.37 K to 0.07–0.38 K with the lower floor.
- **The LM4041's feed** drops from 24.3 kΩ to 20.0 kΩ, so U3's reference gets 70.4 µA at the falling floor (65 µA minimum), and 110 µA at 3.4 V. Revision 3 checked it only down to 2.955 V.
- **State table.** The row for U4's delay now says Q9 stays off until the delay ends; revision 3 wrongly said "on". The falling-rail and fast-restart rows now cite the falling floor, the latency and the error bound.
- **Gate drive from guaranteed levels, not from VREG.** The TPS3840 guarantees VOH ≥ 0.8 × VDD and the TLV3012B VOH ≥ V+ − 0.2 V; the 100 kΩ / 1 MΩ divider passes ≥ 0.9074 of that. At U4's threshold, 2.955 V, a gate gets ≥ 2.15 V from U4 (its VOH is specified only above VIT+ and is taken to scale) and ≥ 2.50 V from a comparator. Less a source rise of ≤ 110 mV, every chain FET sees VGS ≥ 2.03 V. So F2's FETs need R_DS(on) specified at VGS 1.8 V (≤ 5 Ω each in the ISET chain, ≤ 100 Ω in the solar chain), gate capacitance ≤ 100 pF, and ≤ 1 µA at VGS ≤ 0.3 V. Revision 3's VGS(th) window goes, because U4 holds Q9 and Q10 at ≤ 0.3 V until it releases. "2N7002" is marked as a placeholder that doesn't meet this.
- **What the bound still assumes:** the parasitic ranges above, ≥ 10 µF effective on VREG, and ≤ 20 nA at V_T. F2 reruns the script with the chosen parts (§ 10).

### R4-M2: fixed (F2 confirms ST's formula)

- **The finding is confirmed.** Two maximum points don't bound the curve between them, and the 5.0SMDJ28CA's datasheet gives no maximum envelope at 11.3 A. Revision 3's 36.4 V was an interpolation. Its "VIN ≤ IN whatever the capacitance" was also wrong while IN falls, and the Zener's removal rested on the same bound.
- **A TVS whose maker publishes the envelope: ST's SM15T33CA** (bidirectional, 1500 W at 10/1000 µs, SMC):
  - stand-off 28.2 V, above the cold Voc of 28.05 V; breakdown 31.4–34.7 V at 1 mA and 25 °C; αT ≤ 9.8 × 10⁻⁴/°C; clamp ≤ 45.7 V at 33 A;
  - ST's note 3 gives the maximum clamping voltage at any other surge level as VCL = RD × IPP + VBR max, with RD = 0.333 Ω, and ST shifts the curve for another starting temperature by ΔVBR = αT × (T − 25 °C) × VBR(25 °C).
- **The bound:** at 11.3 A, 34.7 + 0.333 × 11.3 = 38.46 V from 25 °C. From +50 °C, VBR max rises by 9.8 × 10⁻⁴ × 25 × 34.7 = 0.85 V: **IN ≤ 39.31 V**. The defined 11.3 A is 34 % of the rated 33 A; F2 reads the +50 °C derating.
- **VIN and overshoot.** The switch passes current only forward and blocks backflow, so VIN can't exceed the highest IN reached so far, plus overshoot. Assumed layout (F3): 10 nH of loop at the pulse's 1.13 A/µs adds ≤ 11 mV; if the switch opens while carrying up to 2 A, 10 nH into ≥ 4.7 µF adds ≤ 0.09 V. So **VIN ≤ 39.4 V**, against the LT3652's 40 V absolute maximum. The margin is 0.6 V.
- **The caveat.** I read note 3 and the RD column in ST's current datasheet only through a quoted excerpt; ST's site timed out for every download. The copy archived for this revision is ST's revision 4 of February 2007. It has the same breakdown, clamp and αT figures but no RD column, and RD = (45.7 − 34.7) / 33 = 0.333 Ω reproduces its table point. F2 confirms the row and note 3 in ST's current datasheet (§ 10). If F2 can't, the fallback is a part whose maker publishes such a formula or curve, not a return to interpolation.
- **The LDO's Zener returns,** independent of the TVS: a BZX84C33 after the 1 kΩ in the LDO's feed. Diodes gives VZ ≤ 35.0 V at 2 mA, ZZT ≤ 80 Ω and ≤ 27.4 mV/°C ([DZ]). During the defined surge it carries ≤ 9.6 mA and holds the LDO's input ≤ 36.3 V; even with IN at the TPS26600's own 62 V maximum it carries ≤ 32 mA and holds ≤ 38.1 V, inside the TPS7B69's 40 V. F2 checks its pulse rating for 32 mA over 1 ms. Using ZZT above 2 mA is conservative (assumed).
- **Negative pulse.** IN ≥ −39.3 V, inside the TPS26600's −60 V. The LDO's feed diode from IN is rated ≥ 100 V. The VBUS feed diode is rated ≥ 40 V, above the Zener's ≤ 38.1 V.
- **Cold leakage.** At −30 °C the TVS's breakdown is still ≥ 31.4 × (1 − 9.8 × 10⁻⁴ × 55) = 29.7 V, above the cold Voc, and the Zener's VZ ≥ 29.7 V. Neither conducts strongly in normal use. ST guarantees the stand-off leakage at 25 °C only, so nothing claims a cold leakage figure; whatever either part leaks comes from the panel, not from the battery.
- **F6** applies the defined pulse in both polarities, from a cold board and from +50 °C, and checks IN ≤ 39.3 V, VIN ≤ 39.4 V and the LDO's input ≤ 36.3 V. That validates the layout; it doesn't replace ST's bound.

### R4-m1: fixed

- **The finding is confirmed.** An open ISET stops charging but leaves the BQ25170's input powered, charge enabled at zero current, with IQ_IN ≤ 0.6 mA ([BQ] §6.5). The 80–110 µA TS-shutdown figure doesn't apply.
- **Suspend, jumper open:** ≤ 0.16 mA for the CH343P, ≤ 0.2 mA for its VBUS pull-down, ≤ 0.6 mA for the BQ25170, 0.74 mA for the interlock, ≤ 25 µA for the interlock's LDO and ≤ 8 µA for the translators: **about 1.73 mA**, under the 2.5 mA a suspended device may draw. F6 measures the complete board in all five host states.
- **Charging, jumper fitted:** ≤ 444 mA for the charger, ≤ 0.6 mA of its own bias, ≤ 15 mA for the CH343P and ≤ 2 mA for the interlock and its LDO (0.76 mA computed): **≤ 462 mA** (revision 3: 461 mA).

### R4-m2: fixed

- **The specification is now Samsung's Ver 1.1 of 9 July 2015** ([35E]; BTO and Telit Power copies). It replaces the June 2015 tentative report, which stays cited only for the mean discharge voltage ([35E-T]).
- **The figures that change:** discharge cut-off 2.65 V (was 2.50 V); charge 1.7 A standard, 1.02 A for cycle life, 2.0 A maximum per cell (was ≤ 1.5 A); diameter ≤ 18.55 mm; nominal 3.60 V; storage ≥ 95 % after 20 days at 60 °C. The capacity (3350 mAh minimum), the 4.20 V charge and the 0–45 °C / −10 to +60 °C limits are as before.
- **None of the results moves.** The UVLO cuts off at 3.05–3.15 V, far above 2.65 V. Both chargers together give at most 0.25 A per cell on 8 cells (0.67 A on today's 3), inside even the 1.02 A cycle-life rate. The winter model uses the unchanged 3.35 Ah, and its rerun output differs only in the header, the script's hash and the source note. D11's battery compartment uses the 18.55 mm diameter.
- **F2** checks that the purchased batch matches Ver 1.1 (§ 9).

### R4-N1: fixed

- **R-P7 (b) is now ≤ 132 µA at 3.4 V and +50 °C,** as the coordinator asked: 132 µA × 3.4 V = 448.8 µW, not above revision 2's 150 µA × 3.0 V = 450 µW. Revision 3's 136 µA was 462.4 µW, 2.8 % more, as the review computed.
- R-P7 now says that (b) is no looser in power at the battery terminals either, rather than resting on the 70 % conversion model alone. The high-side estimate, 120.2 µA plus up to 5 µA for the catch diode, leaves 4.9 µA of headroom on the 3.3 V rail under the 70 % conversion model.
- The winter model's sleep-floor sensitivity follows the new limit: 151.4 µA on the cells (was 156.0 µA). Its printed results are unchanged, including the 3.98 mAh read-cost limit.

### R4-N2: accepted

- **The reproduction stands:** the review's reruns matched byte for byte and its independent recurrence agreed. Nothing in the energy model changes in revision 4 apart from the sensitivity above.
- **Read-cost limits belong to the model.** D13, § 4.5, R-P10 and § 7 item 7 now say so: the limits hold with the PMS's contribution fixed and the rest of every read mode scaled alike, under the stated durations, sleep accounting and policy. At the limits the lowest charge comes within 0.05 percentage points of the 3 % hibernation trigger. F6 measures each read mode's cost, not one full read alone.
- **Firmware wording.** § 6 item 1 now removes the `listenForRequest()` call in `setup()` (station.ino line 807) as well as the helpers at 518–555 and the unused `doListenCheck` at 759–785. "Requests now time out" becomes "a button press goes unanswered": the gateway clears it after 120 s (gateway.ino 1779–1783), or earlier when a scheduled frame arrives, because any valid frame clears it.

### R4-N3: accepted

- **U3 isn't qualified against a Samsung limit,** and the documents no longer suggest it is. Ver 1.1 gives no overcharge threshold. F2 asks Samsung or an authorised distributor for an abuse limit, including the normal float's tolerance (D5, § 9, § 10; R-P4).
- **The −10 °C discharge limit isn't yet shown to be met.** Foam and an unfitted heater don't establish the cells' temperature through a long cold spell. F2 defines how the limit is met, or how the load is inhibited below it; the candidates are the DS18B20 on the pack with a firmware rule, the heater footprint, or a documented exception (D13; R-P5).
- **Battery connection while the interlock is powered.** U3 is blind until IN− passes its trip, after τ × ln(V_bat / (V_bat − V_trip)), with τ = 21.6 ms: about 0.1 s for 0.1 V of overdrive and longer for less, so it isn't a deadline. The permissible transient is the chargers' own float, ≤ 4.25 V. F6 connects the battery powered and unpowered at 4.30 V and 4.50 V, records U3's time to trip and checks the cells stay at or below the float meanwhile (§ 7 item 1).
- The recovery voltage-to-charge mapping and the residual off-state drain stay conditional, as revision 3 disclosed.

## Changes beyond the review

- **mobric's answers relayed on 26.10.2026** are written in, as preferences until the F1 gate:
  - **Q24 (a):** USB charging only with the charging jumper fitted, open by default; the alternatives are kept for the record (D3, D5, § 8; R-F9, R-P11, "Out of scope");
  - **Q25 (a):** 8 new, genuine Samsung INR18650-35E from one batch, bought from an authorised seller (D13, § 8; R-P5).
  - § 8 now says no question is open after revision 4.
- **D11, the enclosure:** a 3D-printed enclosure for the new PCB only. mobric models it in Fusion 360 with the 3D agent Astra; `mobric/pcb-caseing` writes the specification, the board interface, the shopping list, the print settings and the STEP/STL review, in `hardware/station-pcb/enclosure/` only; ASA and PETG-CF on an enclosed Bambu Lab printer. This replaces revision 3's ClassCAD plan. ARCHITECTURE.md keeps the board's side of the interface.
- **The interlock's falling slope** is now derived from its load with every gate charging, 1.051 mA, so 110 V/s (revision 3: 1 mA, 100 V/s).
- **D12:** about 2 more unique parts (680 pF and 330 pF instead of 1 nF, 27.0 kΩ, the BZX84C33). The first 5 boards are now about $290–310 plus shipping and VAT (assumed; was $285–305).
- **REQUIREMENTS.md:** R-F9, R-P1, R-P4, R-P5, R-P7, R-P10 and R-P11 marked *(rev 4)*; the battery row from Ver 1.1; the "Out of scope" line on USB charging from a computer.
- **STATUS.md:** the phase, the D3, D5, D11, D12 and D13 rows, the questions (none open), and the roles: the coordinator is now `mobric/workspace-codex-21`, the Codync PCB bot after its restart; the designer is `mobric/pcb-design-2`; `mobric/pcb-caseing` is added for the enclosure.
- **`interlock_trips.py`:** rewritten around the coupled network (Cholesky, Jacobi, step responses, the error bound, the band and beyond-band checks), plus the revision-3 check, the inhibit latency, the falling floor, the gate drive from guaranteed VOH and the LM4041's 20.0 kΩ. It asserts the load bound, an error smaller than the band and a positive beyond-band distance. It runs in about 17 s.
- **`winter_model.py`:** the revision in its docstring, the cell source (Ver 1.1) and `FLOOR_LIMIT_UA` 151.4 µA. No result changes.

## Still open

- **For mobric:** no question. The F1 gate: approving D2–D4 and D6–D14. Installing KiCad 9.0.x (R1).
- **For F2** (§ 10):
  - ST's current datasheet: the SM15T33CA row, note 3's formula and the derating for a +50 °C start;
  - the BZX84C33's pulse rating for ≤ 32 mA over 1 ms; the feed diodes' reverse ratings (≥ 100 V from IN, ≥ 40 V from VBUS);
  - chain FETs: R_DS(on) at VGS 1.8 V (≤ 5 Ω ISET, ≤ 100 Ω solar), gate capacitance ≤ 100 pF, ≤ 1 µA at VGS ≤ 0.3 V, 40 V and 55 °C;
  - the filter parasitics with the chosen parts, ≥ 10 µF effective on VREG, ≤ 20 nA at V_T, and a rerun of `interlock_trips.py`;
  - U3 against an abuse limit from Samsung or the distributor; how the cells' −10 °C discharge limit is met or the load inhibited;
  - the purchased batch against Ver 1.1; the shunt's derating; fuse coordination; exact prices.
- **For F3:** the TVS at the TPS26600's IN pin, and the loop inductance that enters the overshoot allowance.
- **For F5:** the firmware items in § 6, including removing `listenForRequest()` from `setup()`.
- **For F6** (§ 7): rail dips, fast restarts and the inhibit latency; battery connection at 4.30 V and 4.50 V; the defined pulse in both polarities, cold and from +50 °C; the five USB states, suspend about 1.73 mA; sleep in the three R-P7 states, (b) ≤ 132 µA; each read mode's cost against D13's limit; the outer-to-inner cell gradient; the charge estimate; the UVLO ramp.

## Where the evidence is

- **Datasheets:** downloaded to `hardware/station-pcb/build/f1-revision/research/` (gitignored), each in its own directory:
  - ST SM15T, revision 4 (2007), in `power/st_sm15t_mirror/`. ST's own site timed out; the current revision was read only as a quoted excerpt (above);
  - Diodes BZX84 (DS18001) in `power/bzx84_diodes/`;
  - Samsung INR18650-35E Ver 1.1 in `power/samsung_35e_v11_bto/` and `power/samsung_35e_v11_telit/`;
  - the earlier ones as listed in [F1-response-r3.md](F1-response-r3.md).

  Each can be fetched again from the links in ARCHITECTURE.md § Sources.
- **Firmware, read only:** `firmware/station/station.ino` and `firmware/gateway/gateway.ino` at 82ee40d. Nothing was compiled or flashed.
- **PVGIS series:** `build/f1-revision/pvgis/` (gitignored), unchanged. Their SHA-256 values are printed in [calc/winter_model_output.txt](../calc/winter_model_output.txt).
- **Script hashes (SHA-256):** `interlock_trips.py` d86cebffac9d1dc6578ead47758f73b8403d4ab83bb233c4adf418fa89d672f6; `winter_model.py` 0235f8dc2495c511e9f5df3c74b9a797b033b314d26bf16e1c6f81ec37dd1cf2.
- **Reproducing the outputs** (from `hardware/station-pcb/`):
  - `python3 -I docs/calc/interlock_trips.py`;
  - `python3 -I docs/calc/winter_model.py codex build/f1-revision/pvgis/ser60/series.json`;
  - `python3 -I docs/calc/winter_model.py r2check build/f1-revision/pvgis/ser45/series.json`;
  - `python3 -I docs/calc/winter_model.py scenarios build/f1-revision/pvgis/ser45-az233/series.json build/f1-revision/pvgis/ser70-az233/series.json build/f1-revision/pvgis/ser45/series.json`.
