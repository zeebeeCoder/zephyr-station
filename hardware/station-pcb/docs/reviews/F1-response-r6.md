# F1 sixth review response

This is the response by `pcb-design` to [F1-pi-r6.md](F1-pi-r6.md), the sixth review, of F1 revision 5 at 119d1e9. It was written by `pcb-review` (Pi). The review is committed unchanged in c54f20d (SHA-256 of the file 4391f7f0a0c3854384d183bc6c8685434825fcdf17b8987948559feadc0d7a55, as the brief gave). This response was written on 27.10.2026 and committed together with F1 revision 6 of [REQUIREMENTS.md](../REQUIREMENTS.md) and [ARCHITECTURE.md](../ARCHITECTURE.md), following the coordinator's brief `zephyr-f1-rev6-r6-119d1e9`. mobric chose option A for the brief: this round of fixes and local commits, with no push.

**Result: 3 fixed, 2 accepted, 1 partly, 1 open; none disputed.**
- **Fixed:** R6-M1, R6-m1 and R6-m2. R6-M1's bound needs one new part, C_HOT (100 pF on the hot comparator's tap). It is proposed here for the review to accept or reject, not approved; if rejected, R6-M1 stays partly open.
- **Accepted:** the notes R6-N1 and R6-N2.
- **Partly:** R6-M3. The thermal envelope, pulse definition and Rev 8 sources are in place. The ceilings they give hold with the switch closed only, and R6-M2 remains.
- **Open:** R6-M2. With R6-M3's envelope, the switch-closed margin to 40 V is 0.03 V. That can't absorb the switch's opening and recovery without timing the TPS26600's datasheet guarantees. Four options went to mobric through the coordinator on 27.10.2026 (§ "Still open"). Nothing is presented as fixed, and no part is changed for it in this revision.
- **Disputed:** none.

In the "Where" column, § and D numbers refer to ARCHITECTURE.md and R- numbers to REQUIREMENTS.md, both as revised.

## Summary

| Item | Disposition | What changed | Where |
|---|---|---|---|
| **R6-M1** A 2× search result remains an allowance, not the promised bound | **Fixed**, with C_HOT proposed | The search and its factor 2 are gone. An interval envelope of the whole network over the whole box (19 independent values, the NTC over the band ± 0.5 K), by Müller's comparison theorem, bounds the error. OUT1's switching is bounded for any sequence through ∫(h′)⁻. The static trips are taken at the inputs' lagged rail, from 2.4825 V. Bounds: U1 0.561 mV, U2 7.48 mV. Safety corners **+0.0145 °C** and **+44.745 °C**. Exact responses at 64 points each check them, and nothing rests on those points. **It needs C_HOT, 100 pF C0G on U2's tap, proposed for the review to accept** | D5, § 9, § 10; R-P4; [calc/interlock_trips.py](../calc/interlock_trips.py) |
| **R6-M2** The surge proof only budgets the external pulse slope, not switch commutation | **Open** (options to mobric) | The switch-closed bound and the opening are now separate. `surge_bound.py` prints the opening as open, with no timing credited. Up to 12.3 A moving into C_IN and the TVS loop gives an estimated IN ≤ 50.42 V: inside the TPS26600's 62 V, but above the LDO's 45 V. OUT would sit at the Schottky's −VF at up to 12.3 A, against its −0.3 V rating. Recovery has 0.03 V of VIN margin left. Revision 5's claim that the bound covers any opening is withdrawn. Options A–D are with mobric | § 1, § 2, D5, § 8, § 9, § 10; R-P1; [calc/surge_bound.py](../calc/surge_bound.py) |
| **R6-M3** Rev 8 resolves derating, but not the 51 °C thermal premise | **Partly** | Rev 8 is archived (SHA-256 matches the review) and replaces revision 4. The pulse now has an explicit waveform envelope (assumed definition): ≤ 11.3 A for 13 µs, then halving at least every 1.2 ms. That gives ≤ 19.71 mC and ≤ 0.90 J. Pre-pulse heating uses a periodic passive-network argument: average power through Rth(j-a). Rth is taken as 120 K/W, above Figure 12's footprint-only 110–112 K/W with no copper credit, plus 5 K local. So Tj ≤ 57 °C. Switch closed: **IN ≤ 39.70 V**, **VIN ≤ 39.97 V** (margin 0.03 V). Derating is from Rev 8 Figure 3: the pulse uses 30 % | D5, § 9, § 10; R-P1; [calc/surge_bound.py](../calc/surge_bound.py) |
| **R6-m1** The old input-capacitance exemption remains in D5 | **Fixed** | The bullet now requires parts rated ≥ 50 V, with the effective capacitance the surge bound uses. "No longer part of the surge bound" is gone. The Figure 1 references now cite Rev 8 Figure 3 | D5 (LT3652 settings), § 9, § 10 |
| **R6-m2** Separate blind-interval charge from residual charge and fault scope | **Fixed** | Three separate parts. Blind interval to the trip crossing: ≤ 0.155 C from the LT3652, ≤ 0.044 C from the BQ25170 (99.1 ms at 70 mV). Trip to chain open: ≤ 0.2 mC. Complete stop: ≤ 20 mC. In all: ≤ 0.18 C and ≤ 0.065 C. "Failed charger" is scoped to a voltage-feedback fault with working current regulation. The healthy-charger test gets a measurement tolerance: ≤ 1 mA mean, measured to ± 0.5 mA, so ≤ 0.1 mC; the voltage rises by no more than ± 2 mV | D5, § 7 item 1; R-P4 |
| **R6-N1** Reproduction, winter regression and read-cost boundaries | **Accepted** | Nothing to rerun: revision 6 doesn't move the energy corner (+2.72 / +3.09 °C, +41.52 / +41.33 °C), and `winter_model.py` and its output are unchanged. The fixed-15-minute outage disclosure and the adaptive model's conditions stay in § 4.4 and D13. `surge_bound.py` reproduces its recorded output byte for byte | § 4.4, D13 unchanged |
| **R6-N2** Rail and stop qualifications must remain conditions | **Accepted** | Revision 5's "the safety corners don't depend on the upper rail" is withdrawn. VREG ≤ V_TOP = 3.4 V, start-up included, is now an explicit condition: F2 asks TI or enforces it, and F6 measures it. The terms that use it are listed: NTC self-heating as VREG² (0.099 K at 3.4 V, about 0.137 K at 4.0 V), OUT1's switching excess in the filter bound, the gates' starting voltage, and the load and falling slope. A preload is not assumed, because it would need the falling slope, floor, filter bound and USB budget rerun. The 22.7 V/ms, 50 V/s, current-limit and complete-stop items stay conditions; none is described as met | D5, § 9, § 10; R-P4 |

The rows the review marked "partly" in earlier generations:
- R4-M1, R3-M1 and R2-B1 through R6-M1 and R6-N2: the filter error is now a bound over the whole declared box, not a search. The rail, slope, upper-rail and complete-stop conditions stay conditions.
- R4-M2, R3-M2 and R2-M3: still partly. R6-M3 states the thermal and pulse premises; R6-M2 is open.
- R4-N3 and R3-N2 through R6-m2. The Samsung backstop threshold, cold-cell operation and voltage-to-SOC recovery remain unqualified, as before.
- R2-M1 through R6-M1: the winter model's trips don't change (R6-N1).

## Details

### R6-M1: fixed

**What the review asked.** Revision 5 multiplied the largest error a search found by two. That is a lower estimate of a supremum times a factor, not an upper bound. Derive a conservative envelope over the declared ranges, or a justified reduction or validated numerical enclosure; cover any sequence of OUT1's switching, not one step; keep VOH and VOL quasi-static or bound them; then regenerate the margins and any changed winter trips.

**What revision 6 does.** The search, its vertices, ascents, random points and the factor 2 are gone from `interlock_trips.py`. In their place is `filter_bound()`, an interval envelope of the whole coupled network over the whole box.

1. **Sources and the decomposition.** Each node's Thevenin source is a fixed fraction of VREG or OUT1: E0 = K0·VREG at V_T, E3 = K3L·VREG + cO·OUT1 at U1's tap node, E5 = K5·VREG at U2's tap. The difference between a comparator's inputs splits into two parts:
   - a static part, (K3 − K0)·W for U1 or (K0 − K5)·W for U2, where W is VREG lagged by the input's own filter;
   - a dynamic part, Δ convolved with VREG's slope. Δ is a combination of the nodes' unit-step responses and settles to zero.

   The static trips are taken at W, over its whole range. The dynamic part is at most R_RISE·∫Δ⁺ + R_FALL·∫Δ⁻ for any VREG history whose slope stays between −50 V/s and +22.7 V/ms. That covers dips, restarts and charge left on the capacitors, as in revision 5, without relying on U4's delay.
2. **The lagged rail W replaces "VREG at the floor".** W can be up to 174.0 mV below VREG and 0.39 mV above it at the steepest slopes (the integral of the V_T input's step-response envelope). So the static corners are taken at W from 2.4825 V (the falling floor less that lag) to 3.4004 V.
3. **The envelope (Müller's comparison theorem).** The six node equations are written in V_T, the two input currents' coordinates and the three tap nodes. Each coefficient is a range over the box: 19 values, each independent, plus the NTC over the trip band widened by 0.5 K on each side, with the table's spread and drift. The script asserts that each trip, moved by its bound, stays inside that band.
   - Each coefficient's partial derivative with respect to each value has a fixed sign, so its range is at the box's vertices. For example, ∂/∂d of d / (c·c′ + d·(c + c′)) is c·c′ / det² ≥ 0. `env_check` also tests random interior points.
   - Each state's upper bound follows the largest right-hand side with that state at its upper bound and every other state anywhere within its bounds; likewise the lower bounds. By Müller's theorem these 12 equations bound every trajectory of every parameter set in the box, even a parameter varying in time.
   - The bound system is linear for a fixed choice of extremes. It is solved exactly with a matrix exponential, with the step halved wherever the choice changes, down to 1/1000 of a grid step. Where the choice still changes, the bounds are widened by the step times the gap between the kept and the true extreme. That happened about 1.1 million times per comparator, adding at most 1.1e-9 of a unit step each time.
   - Δ is formed from the three runs' envelopes (E0, E3 and E5 steps) by interval arithmetic. The runs are treated as independent, which loses correlation but is conservative.
4. **OUT1, any switching sequence.** OUT1 at any moment is θ·VREG with 0 ≤ θ ≤ 1. Its part of the input difference is cO·(h′ ∗ OUT1), with h the E3 step response between the inputs. Split h′ into its positive and negative parts. The positive part is at most the OUT1-high kernel, already in Δ with K3 = K3H. The negative part adds at most cO·V_TOP·∫(h′)⁻, for any sequence of states and any level between 0 and VREG. h′ is evaluated by interval arithmetic from the E3 envelopes. This replaces revision 5's single-step "kick". It uses VREG ≤ V_TOP = 3.4 V (R6-N2). VOH's and VOL's drops stay quasi-static in the static trips, as revision 5 stated, and are within the 0 ≤ θ ≤ 1 range of the dynamic part.
5. **Integration.** On a grid from 0.1 ps to 50 ms at 40 points a decade, each step's integral takes the larger of its two ends. The band is solved again at 80 points a decade, and the larger total is kept: U1 0.5605 / 0.5478 mV, U2 7.4838 / 7.3471 mV. At 50 ms the widest bound is 1e-12 of a unit step, so nothing is left to integrate.
6. **Beyond the band**, toward open (U1) and toward a short (U2), the NTC range is cut into four pieces, each with its own envelope at 20 points a decade. At each piece's nearest end, with the lagged rail at its lowest for that piece, the static distance from the trip exceeds the piece's bound, the offset and half the hysteresis by ≥ 38 mV (U1) and 26 mV (U2).

**A design change was needed: C_HOT.** Revision 5's U2 tap had only the comparator's 1–10 pF to AGND and 0–8 pF to the other input. With that, the tap's fastest mode is many times faster than the rest of the network, and the interval system diverges: the bounds grow without limit, although every fixed network is stable. 100 pF C0G (± 5 %) at U2's IN− keeps the differential capacitance small against the node's own, and the envelope closes. **C_HOT is proposed for the review to accept or reject. It isn't an approved change.** If it's rejected, R6-M1 stays partly open. The network is solved as one, so the envelope diverges for both comparators.

**Results.**

| | U1 (cold) | U2 (hot) |
|---|---|---|
| Rise / fall / OUT1 switching, mV | 0.160 / 0.310 / 0.091 | 0.937 / 0.047 / 6.500 |
| Bound, mV (K at W_lo) | **0.561** (0.023 K) | **7.48** (0.383 K) |
| Revision 5 (2 × the search), mV | 0.904 | 0.382 |
| Beyond the band, least margin, mV | 38 | 26 |

Safety corners: **cold off +0.0145 °C (≥ 0), hot off +44.745 °C (≤ 45)**, both with the lagged rail at 2.4825 V. Revision 5 had +0.037 and +44.34 °C. The margins, 0.01 K cold and 0.25 K hot, are smaller than revision 5's, because these are bounds and not search results. Two conservative terms take most of them. The lagged rail costs 0.032 K cold and 0.043 K hot. U2's OUT1 term costs 0.33 K; at the check points its exact value is ≤ 0.0126 mV, under 0.001 K. The envelope's coupling from U1's tap through V_T makes that term so loose. Either term can be tightened if F2's parts need margin; neither is needed for these corners.

**Validation, not part of the bound.** `env_check` takes 64 fixed-seed points of the box and band per comparator, plus the review's R5-M1 point for U1. For each it computes the exact network (eigen-decomposition) and checks three things:
- every node's exact step response lies inside the envelopes; the largest excursion is 3.2e-12, against a tolerance of 1e-9;
- the exact rise + fall integral is ≤ the bound: U1 0.241 against 0.470 mV, U2 0.186 against 0.984 mV;
- the exact OUT1 excess (the integral of h′'s negative part) is ≤ the bound's: U1 0 against 0.091 mV, U2 0.0126 against 6.500 mV.

The script asserts all three.

**Assumptions the bound still rests on** (they're conditions, not results):
- The network as modelled: the parasitic ranges (≤ 50 pF on V_T, 1–10 pF and 0–8 pF at the comparators, 0.5–5 pF at U1's tap node), the tolerances, C_HOT fitted, and a start from rest driven only by VREG and OUT1. It doesn't cover NTC hot-plug, parts outside tolerance or injected charge (R5-N2, unchanged).
- VREG's slopes (≥ 22 µF effective, the LDO's current limit, the load) and VREG ≤ V_TOP (R6-N2).
- Numerically, three things are validated rather than proven. Where the bounds are widened, the widening uses the gap at the sub-step's end. Those sub-steps are under 1/1000 of a grid step, and the exact responses stay inside the envelopes. Between grid points the integrand is taken at the larger end of each 6 % step, which holds if it is monotone within the step; the 80-points-a-decade solve checks this. Nothing is integrated beyond 50 ms, where the bounds have converged to 1e-12 of a unit step.

### R6-M2: open

**What the review asked.** Specify the inductance partition, capacitor bounds and initial states, and the current paths. Give positive and negative pin envelopes for opening and recovery. Prove passive limits independent of timing, or use guaranteed timing or current bounds, not typical fast-trip timing.

**What revision 6 does.**
- `surge_bound.py` separates the switch-closed bound (R6-M3, below) from the switch opening. It prints the opening's three parts and says which are open.
- **IN at opening.** No switch timing is credited, so the switch may carry the whole loop current, 12.3 A, when it opens. That current moves into C_IN (1 µF effective at the IN pin, assumed) and the 10 nH TVS loop. The energy of that network about the TVS's new operating point can't grow, because the TVS is monotone. That gives IN ≤ 50.42 V, an estimate under those layout values. It is inside the TPS26600's 62 V, but above the TPS7B6933's 45 V for 200 ms, so the LDO relies on its 1 kΩ and input capacitor, which isn't shown.
- **OUT at opening.** The loop current continues through the OUT Schottky into C_VIN. OUT then sits at the Schottky's −VF at up to 12.3 A, about −0.5 V, against the TPS26600's −0.3 V OUT rating ([TP] § 7.1). That holds unless the interrupted current is bounded.
- **Recovery.** C_IN's stored charge can feed the loop when the switch recovers. VIN has 0.03 V of switch-closed margin left for it.
- Revision 5's sentence that the bound covers any opening is withdrawn (D5).

**Why it isn't closed.** A passive bound independent of timing needs margin that isn't there: 0.03 V at VIN, and none at OUT for an unbounded interrupted current. A bound from timing needs the TPS26600's fast-trip timing or current, which its datasheet gives as typical only.

**Options sent to mobric** (through the coordinator, 27.10.2026, recommendation A for this round):
- **A.** Keep the parts. State the switching conditions as F2/F3 requirements: copper under the TVS for Rth ≤ 80 K/W, C_IN at the IN pin, a TVS loop ≤ 10 nH, an OUT Schottky, and a guaranteed interruption current or time from TI. The VIN margin becomes about 0.14 V.
- **B.** Change the defined surge in R-P1, for example to 8 A. The VIN margin becomes about 1.24 V. This is a change of an assumed environmental definition, which only mobric can make.
- **C.** Research a 3 kW TVS in the same SMC package (ST SMC30J family). It would need its datasheet, downloaded with approval, and a check of VCL, RD and VBR above the cold Voc. It doesn't by itself bound OUT or the LDO.
- **D.** A different charger or two-stage protection. A larger change, not recommended.

**The coordinator's reply.** A is not a closure of R6-M2 and must not move a known gap to F2 labelled as fixed. B weakens a requirement and needs mobric's explicit decision. C is research, not an accepted change. R6-M2 stays open until there is evidence; no part changes and no assumptions committed as approved. This revision follows that. When it was committed, mobric hadn't chosen among A–D, and C hadn't been started (coordinator, 27.10.2026).

### R6-M3: partly

**Sources.** ST DS0683 Rev 8 (May 2022) is archived at `build/f1-revision/research/power/st_sm15t_rev8_lcsc/sm15t_ds0683_rev8_lcsc.pdf` (gitignored). It is the copy the sixth review retrieved from LCSC (`https://datasheet.lcsc.com/datasheet/pdf/90dac3b1fa53d3a9bca01f3963dc7892.pdf?productCode=C81476`); its SHA-256, 3d4c7f4c7f31852cf00c9631b55bf65b51582036646e1c8386a098656edb9144, matches the review's. Revision 4 of 2007 is no longer used.

**Pulse definition** (assumed, R-P1). 10/1000 µs with tolerances: the current stays ≤ 11.3 A up to 13 µs and then halves at least every 1.2 ms. So the charge is ≤ 11.3 A × (13 µs + 1.2 ms / ln 2) = 19.71 mC. With the clamp taken at its rated 45.7 V for the whole pulse, the energy is ≤ 0.90 J. "10/1000 µs" alone is no longer read as an exact exponential.

**Starting temperature.**
- The junction's heating is a passive RC network. Its response to a unit of energy is a sum of decaying exponentials with positive weights, so it decreases in time.
- So just before a pulse, the rise left by all earlier pulses, one a minute, is at most the average power through the steady thermal resistance: 0.90 J / 60 s × 120 K/W = 1.80 K.
- Rth(j-a) is taken as 120 K/W, above Figure 12's footprint-only 110–112 K/W, with no copper credit. Figures 11 and 12 are characteristic curves for FR4 with 70 µm copper, not maxima for this board, so F3 keeps at least ST's footprint and F6 measures.
- 5 K is added for neighbouring parts above the board's +50 °C (assumed; F3 keeps the TVS away from the LT3652, its inductor and catch diode).
- So Tj ≤ 57 °C, against revision 5's 51 °C.

**Ceilings, switch closed.**
- VCL at 11.3 A: 38.4739 V from 25 °C, 39.6804 V from 57 °C.
- IN ≤ 39.70 V with the 10 nH TVS loop at 1.13 A/µs.
- VIN ≤ 39.97 V with 12.3 A × √(5 nH / 10 µF). The margin to 40 V is 0.03 V, against revision 5's 0.25 V.
- The review's own sensitivity (110 K/W, 52 °C) is inside this envelope.

**Derating.** Rev 8 Figure 3 is flat at 100 % to about 115–120 °C by reading. The script takes 100 % only up to 110 °C. From 57 °C the defined pulse is ≤ 449 W, 30 % of 1500 W, and 11.3 A, 34 % of 33 A.

**Why partly.** The envelope is explicit, but the ceilings it gives hold only with the switch closed (R6-M2). F3's copper and placement, and F6's measurement, are requirements, not results.

### R6-m1: fixed

- D5's LT3652 input-capacitance bullet no longer says it is "no longer part of the surge bound".
- It now requires parts rated ≥ 50 V, with the effective capacitance the bound uses: ≥ 10 µF within ≤ 5 nH, or ≥ 20 µF with 10 nH. This is consistent with § 9 and § 10.
- The Figure 1 references now cite Rev 8 Figure 3 and its actual curve.

### R6-m2: fixed

**Blind interval, residual and fault scope** (D5, R-P4). At 4.50 V against a 4.43 V trip, with τ ≤ 23.8 ms:

```text
t_cross = 23.8 ms × ln(4.50 / 0.07)  = 99.09 ms   (to U3's input crossing its trip)
LT3652:   1.56 A × 99.09 ms          = 0.1546 C
BQ25170:  0.444 A × 99.09 ms         = 0.0440 C
U3 to chain open: TLV3012 response (no published maximum; 100 µs allowed, F2)
                  + Q6's gate to 0.3 V (≤ 29.5 µs)   ≤ 0.13 ms → ≤ 0.2 mC
complete stop after the chain opens (R-P4 requirement)     ≤ 20 mC
total to the current stopping:  LT3652 ≤ 0.18 C, BQ25170 ≤ 0.065 C
```

- The three parts are now named separately in D5, R-P4 and § 7 item 1. The old 0.16 C was the blind interval only, rounded up.
- **Fault scope.** "A failed charger" now means a voltage-feedback fault, the float set too high, with its current regulation still working. Nothing bounds arbitrary charger failures, and no single-fault guarantee is claimed. The lab test (the LT3652 set for a 4.60 V float) tests exactly that case.
- **Measurement tolerance.** The healthy-charger test passes at a mean current ≤ 1 mA over the blind interval, measured to ± 0.5 mA, so ≤ 0.1 mC added. The voltage may rise by no more than the voltmeter's ± 2 mV. The failed-charger test measures charge to ± 5 %. "No charge" and "no rise" are no longer literal zeros.

### R6-N1: accepted

**What the review noted.** All five recorded outputs reproduced, byte for byte, at the response-r5 SHAs. The winter model's fixed-15-minute fallback fails the energy corner on 8 faded cells (one outage winter, about 15 days; 16–17 days at the other orientations), so adaptive control is essential. The read-cost limits (3.99 and 6.14 mAh adaptive, 1.66 and 2.59 mAh fixed) belong to the model, not to every read. Constant SOC biases aren't a proof against an estimator error that varies in time.

**What revision 6 does.**
- **No winter rerun is needed, and none was done.** The winter model takes the interlock's energy corner, the static column "VREG down to U4's threshold". Revision 6 doesn't change it:
  - The filter bound and the lagged rail enter only the safety corners. `interlock_trips_output.txt` prints the same energy corner as revision 5: off +2.72 °C, on +3.09 °C; hot off +41.52 °C, on +41.33 °C.
  - `winter_model.py` (SHA-256 0e5a4e29…92a2) and `winter_model_output.txt` (fb7c0308…d5c42a) are unchanged.
- **The disclosures stay as they were.** § 4.4 and D13 still say three things:
  - fixed 15-minute reads fail the energy corner on 8 faded cells, which is why revision 5 withdrew that fallback;
  - the recommendation depends on the adaptive schedule;
  - the named limits hold for the model's mode costs, durations and policies only (R4-N2). F6 measures each read mode, and the three constant biases are sensitivity cases, not proof against an error that wanders (R3-N1).
- **Reproduction.**
  - `surge_bound.py` was rerun for this response; its stdout matches `surge_bound_output.txt` byte for byte.
  - `interlock_trips_output.txt` is the stdout of the committed script, whose SHA is in its header.
  - The commands and SHAs are under "Where the evidence is".

### R6-N2: accepted

- **Upper rail.** D5's "Regulated or not" bullet withdraws revision 5's claim and states VREG ≤ V_TOP = 3.4 V, start-up included, as a condition. `interlock_trips.py` names it `V_TOP`.
- **What uses it:**
  - the NTC's self-heating, which scales as VREG²: 0.099 K at 3.4 V, printed against the 0.1 K allowance, about 0.137 K at 4.0 V;
  - OUT1's switching excess in the filter bound, proportional to V_TOP;
  - the gates' starting voltage in the inhibit latency;
  - VREG's load at 3.4 V, which sets the 50 V/s fall.
- F2 confirms with TI that the TPS7B6933 stays ≤ 3.4 V at 0.74–1.05 mA and during start-up, or the design enforces it. F6 measures VREG at the real load and its start-up overshoot.
- **No preload is assumed.** It would change the falling slope, the floor, the filter bound and the USB budget, so it would need all of them rerun.
- **Still conditions, not met:** the LDO's current limit at every output voltage (22.7 V/ms), the effective 22 µF, the discharge-path inventory (50 V/s), the chargers' complete stop, FET qualification, and F6's full-stop, hot-plug and thermal measurements. § 9 and § 10 list them as open.

## Changes beyond the review

- **The static trips are taken at the lagged rail.** The new split puts the inputs' common lag behind VREG into W, where revision 5's kernels carried it implicitly. At the steepest rise the lag is up to 174.0 mV, which costs 0.032 K cold and 0.043 K hot against the falling floor itself. The full lag comes only on a fast rise, and the floor only on a slow fall, so this is pessimistic. It is kept because it needs no assumption about U4. A rail window from U4's rising threshold could recover most of it if F2's parts need margin.
- **U2's distance beyond the band now uses the lowest hot tap.** Revision 5 took the highest tap for both comparators. That is right for U1, but for U2 it overstated the distance by 3.8 mV at the falling floor (the dividers' ± 0.175 %). The check now uses the lowest hot tap, the rail's lowest value for each piece, and each piece's own envelope: ≥ 26 mV (U2) and ≥ 38 mV (U1), where revision 5 had ≥ 59 mV for the search allowance.
- **A conservative conversion to kelvin.** Revision 5 converted the filter error and the leakage at the nominal NTC's slope at the band's two ends. Now each takes the smallest slope of any NTC corner (table spread, drift, RS's tolerance), every 0.1 K across the band. That adds 2–4 % to both in kelvin; the leakage is now 0.007 K, not 0.006 K.
- **The bands are widened by 0.5 K, not 0.25 K.** The script asserts that each trip, moved by its bound, stays inside the band it was computed over. U2's 0.38 K didn't fit in 0.25 K.
- **Run time.** `interlock_trips.py` now takes 11–17 minutes here, against revision 5's few minutes. The final run took 679 s wall clock and 3706 s CPU on 10 processes; the docstring says about 20 minutes.
- **Bookkeeping.** C_HOT adds about one unique part to D12's assembly cost, if accepted. The D5 heading lists the R6 items. The STATUS D5 row now has the revision 6 numbers.

## Still open

- **For mobric** (through the coordinator): R6-M2's options A–D (above). Until mobric decides, R6-M2 stays open and no part changes for it. The F1 gate: approving D2–D4 and D6–D14. Installing KiCad 9.0.x (R1).
- **For F2** (§ 10):
  - C_HOT, the hot tap's 100 pF C0G (R6-M1): first the review's decision on it, then the part; and the interlock filter parts' capacitance ranges;
  - VREG ≤ 3.4 V at the real load and at start-up, the current limit and the 22 µF (R6-N2);
  - the TLV3012's response time, with 100 µs allowed (R6-m2);
  - the chargers' stop response against R-P4's 10 ms and 20 mC;
  - a rerun of `interlock_trips.py` with the chosen parts;
  - the items carried from revision 5.
- **For F3:** the TVS loop (10 nH), its copper and its distance from hot parts; the IN-to-VIN loop.
- **For F6** (§ 7): the rail, including VREG's start-up overshoot; battery connection with the stated tolerances; NTC hot-plug; the defined pulse with the switch closed, and IN, OUT and the LDO input recorded while the switch opens and recovers (limits open); the items carried from revision 5.
- **Not covered by the filter bound** (unchanged from revision 5): a change of the network itself (NTC hot-plug while powered, a part outside its tolerance, charge injected by ESD).

## Where the evidence is

All commands were run from `hardware/station-pcb` on 27.10.2026, with Python 3.9 from Xcode and the standard library only. Every number is computed, not measured.

| Command | Result |
|---|---|
| `python3 -I docs/calc/interlock_trips.py` | exit 0, stderr empty, 679 s wall clock (3706 s CPU, 10 processes); stdout recorded unchanged below the header of [calc/interlock_trips_output.txt](../calc/interlock_trips_output.txt) |
| `python3 -I docs/calc/surge_bound.py` | exit 0, stderr empty; stdout identical, byte for byte, to the body of [calc/surge_bound_output.txt](../calc/surge_bound_output.txt) |
| `winter_model.py` | not rerun: the script, its inputs and the energy corner it uses are unchanged (R6-N1) |

SHA-256:

| File | SHA-256 |
|---|---|
| `docs/calc/interlock_trips.py` (revision 6) | 7cb3c40736aa2d081d75c353ed1bef9f4558feca499ed4ed3867fa0f5588a780 |
| `docs/calc/interlock_trips_output.txt` | 2a66cb2664fdc6ba806f715dcfa12ac6fa10af5dc47f2ba1aafce66dd4259e2d |
| `docs/calc/surge_bound.py` (revision 6) | 7d49f033637c74d7917570a69ac1f73d2860868cf0f78cdfce3e68e0eacc30d7 |
| `docs/calc/surge_bound_output.txt` | 489490959386dc740e918d11cb3f5f6dc55824a4077d3bd8f899944c905f66c8 |
| `docs/calc/winter_model.py` (unchanged) | 0e5a4e29c5315b1ef28588eec221e3b6d01f6ba7c08e58e2b7d1de090f6c92a2 |
| `docs/calc/winter_model_output.txt` (unchanged) | fb7c030815635ff02ae65d479896a3da1815c677e0bcfaf2dcefe837d8d5c42a |
| ST DS0683 Rev 8, `build/f1-revision/research/power/st_sm15t_rev8_lcsc/sm15t_ds0683_rev8_lcsc.pdf` (gitignored) | 3d4c7f4c7f31852cf00c9631b55bf65b51582036646e1c8386a098656edb9144 |
| `docs/reviews/F1-pi-r6.md` (unchanged) | 4391f7f0a0c3854384d183bc6c8685434825fcdf17b8987948559feadc0d7a55 |

Revision 5's `interlock_trips.py` was 5e00967c…5f12, and `surge_bound.py` was afa94fe7…9d0c.

Key lines of `interlock_trips_output.txt`:

```text
  Lagged rail at the comparator inputs: W 2.4825-3.4004 V (the floor less 174.0 mV, the top plus 0.39 mV: the inputs' lag behind VREG at the steepest slopes)
Unrounded safety corners: cold off +0.0145 C, hot off +44.7451 C
Energy corner for the winter model (VREG down to U4's threshold): off +2.72 C, on +3.09 C; hot off +41.52 C, on +41.33 C
  U1: NTC 26.125-32.597 k (trip band +-0.5 K): rise 0.1599, fall 0.3099, OUT1 switching 0.09066 mV; bound 0.5605 mV = 0.0232 K at 2.483 V
    at 40 / 80 points a decade: 0.5605 / 0.5478 mV (the larger kept); changes of choice kept 1097164, widening <= 4.0e-10; widest bound at 50 ms 9.7e-13
    Beyond the band, toward open: the static distance from the trip exceeds the bound by >= 38 mV
    Validation, not part of the bound (65 points, fixed seeds, R5-M1 point included): exact responses outside the envelopes by <= 3.2e-12; exact rise + fall <= 0.2411 mV against 0.4698; OUT1 excess <= 0.00000 mV against 0.09066
  U2: NTC 4.386-5.293 k (trip band +-0.5 K): rise 0.9368, fall 0.0473, OUT1 switching 6.49979 mV; bound 7.4838 mV = 0.3827 K at 2.483 V
    at 40 / 80 points a decade: 7.4838 / 7.3471 mV (the larger kept); changes of choice kept 1107348, widening <= 1.1e-09; widest bound at 50 ms 7.8e-13
    Beyond the band, toward short: the static distance from the trip exceeds the bound by >= 26 mV
    Validation, not part of the bound (64 points, fixed seeds): exact responses outside the envelopes by <= 1.1e-12; exact rise + fall <= 0.1859 mV against 0.9840; OUT1 excess <= 0.01255 mV against 6.49979
```

The surge numbers under R6-M2 and R6-M3 above come from `surge_bound_output.txt`. Revision 6 is committed locally on `hardware/station-pcb`, in the commit that adds this file. It isn't pushed.
