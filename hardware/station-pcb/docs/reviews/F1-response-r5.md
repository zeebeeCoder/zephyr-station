# F1 fifth review response

This is the response by `pcb-design` to [F1-codex-r5.md](F1-codex-r5.md), the Codex fifth review of F1 revision 4 at a0ae015, written by `mobric/mikolaj-codex`. That reviewer is now retired; the Pi session `pcb-review` reviews from revision 5 on. The designer session was called `mobric/pcb-design-2` on Reason Network until 27.10.2026, and earlier `mobric/pcb-design`, `mobric/mikolaj-claude-60` and `mobric/pcb-opus-5-5`. The review is committed unchanged in 238bad6. This response was written on 27.10.2026 and committed together with F1 revision 5 of [REQUIREMENTS.md](../REQUIREMENTS.md) and [ARCHITECTURE.md](../ARCHITECTURE.md), following the coordinator's brief `zephyr-f1-rev5-r5-a0ae015`.

**Result: 4 fixed, 2 accepted, none disputed.**
- **Fixed:** R5-M1, R5-M2, R5-M3 and R5-m1. R5-M2 leaves one source comparison open: the pulse-derating curve in ST's current datasheet (below).
- **Accepted:** the notes R5-N1 and R5-N2. Revision 5 changes the winter model's energy corner, so the model is rerun as R5-N1 asked. R5-N2's conditions are now stated as requirements or assumptions, each with its F2 or F6 check.
- **Disputed:** none.

No design question for mobric came out of this revision. One practical question goes to the coordinator: how to get ST's DS0683 Rev 8 into the research folder, because it couldn't be downloaded here.

In the "Where" column, § and D numbers refer to ARCHITECTURE.md and R- numbers to REQUIREMENTS.md, both as revised.

## Summary

| Item | Disposition | What changed | Where |
|---|---|---|---|
| **R5-M1** The search doesn't compute an all-tolerance bound | **Fixed** | Each of the 18 filter values now varies independently. The search covers all 262144 vertices at 3 NTC values, the 64 worst vertices at 17 NTC values, 8 local ascents and 2000 random points. The search isn't a proof, so the trips carry **twice the largest error found**. OUT1 is now a second source through RHYS, in either state at every moment, plus its switching kick. OUT1's VOH and VOL enter the static trips. To keep the cold margin with that allowance, VREG's capacitance rises from 10 to **22 µF**. Cold safety corner +0.037 °C, hot +44.337 °C | D5, § 9, § 10; R-P4; [calc/interlock_trips.py](../calc/interlock_trips.py) |
| **R5-M2** ST's formula doesn't give the 39.3 / 39.4 V ceilings | **Fixed** (Rev 8's Figure 1 still to compare) | A new script applies ST's note 3 at 11.3 A and note 2 to VCL, from a junction start of ≤ 51 °C (the board at +50 °C plus self-heating). It adds the TVS loop and rounds up to 10 mV: **IN ≤ 39.47 V**. **VIN ≤ 39.75 V** comes from the loop's real current, 12.3 A, and **√(L / C) ≤ 22.4 mΩ** to the VIN capacitors, which is now an F2/F3 requirement. The claim that the bound doesn't depend on capacitance or current is withdrawn. Pulse derating from Tj 51 °C: the pulse uses 33 % of the derated power | § 1, § 2, D5, § 7 item 2, § 9, § 10; R-P1; [calc/surge_bound.py](../calc/surge_bound.py) |
| **R5-M3** The Zener's independent clamp uses a minimum coefficient as a maximum | **Fixed** | The BZX84C33 is removed. The LDO's input is bounded by the corrected upstream IN, ≤ 39.47 V through its feed diode, inside the TPS7B6933's 40 V operating range. The independent 62 V claim is gone. The VBUS diode is rated ≥ 60 V. The 1 kΩ's pulse energy is ≤ 0.78 mJ with 1 µF | D5, § 10, D12; R-P1 |
| **R5-m1** The battery-connection acceptance criterion is impossible | **Fixed** | F6 first finds the unit's own U3 trip. Healthy chargers are then connected at V_trip + 70 mV and at 4.50 V: they must add no charge (≤ 1 mA). A failed charger (the LT3652 set for a 4.60 V float) may add ≤ 0.16 C before U3 trips within 0.1 s. 4.30 V is no longer a pass/fail point | D5, § 7 item 1; R-P4 |
| **R5-N1** Reproduction and energy | **Accepted** | The energy corner moves from +2.71 to +2.73 °C, and the hot "on" trip from +41.33 to +41.32 °C, so the winter model is rerun. mobric's 8 faded cells on the adaptive schedule still have no outage hour (lowest 27 %) and keep the 3.99 mAh read limit. The fixed-schedule fallback loses margin (details) | § 4.4, § 4.5, D13; R-P10 unchanged |
| **R5-N2** Rail and complete-stop assumptions | **Accepted** | Opening the chains (59.5 µs) is no longer equated with the current stopping. R-P4 now requires each charger below 10 mA within 10 ms, and ≤ 20 mC from both together. Slope limits are 22.7 V/ms rise and 50 V/s fall, with their conditions. The LDO's current limit and its ± 3 % at a 0.74 mA load are labelled as assumptions. The bound's initial conditions are stated, and an NTC hot-plug test is added | D5, § 7 item 1, § 9, § 10; R-P4 |

The rows the review marked "partly" close through these rows:
- R3-M1 and R2-B1 through R5-M1 and R5-N2: the bound is now a declared search with a 2× allowance over independent values, and the rail, slope and stop conditions are explicit;
- R3-M2 and R2-M3 through R5-M2 and R5-M3, except for the comparison of Rev 8's Figure 1, which is still to do;
- R3-N2 through R5-m1;
- R2-M1 through R5-M1 and R5-N1: the trips the winter model uses are recomputed, and the model is rerun.

## Details

### R5-M1: fixed

- **The finding is confirmed.**
  - Revision 4 moved values in groups. RS moved with C_T, U1's four tap resistors moved together, RH1 moved with RH2, and the other comparator's side was either all low or all high.
  - The new script reproduces the review's U1 point. With revision 4's 10 µF, "OUT1 high" alone gives 0.9044 mV; the review got 0.904692 at 60 points a decade and 0.904403 at 600.
  - Revision 4's "every tolerance corner" and its two maxima are withdrawn.
- **Independent values.** Each of the 18 filter values varies on its own within its range:
  - RS and the four divider resistors at ± 0.175 % (0.1 % plus drift);
  - RHYS at ± 1 %;
  - C_T at ± 5 % plus up to 50 pF of ESD diode, cable and board, and C_F1 at ± 5 %;
  - the 10 kΩ and 27.0 kΩ filter resistors at ± 1 %;
  - the comparators' input capacitances, 1–10 pF to AGND and 0–8 pF differential;
  - U1's tap node, 0.5–5 pF.

  The NTC varies across each trip band, ± 0.25 K.
- **The search** (per comparator; [calc/interlock_trips_output.txt](../calc/interlock_trips_output.txt)):
  - all 2¹⁸ = 262144 vertices at the band's two ends and middle: 786432 evaluations;
  - the 64 worst vertices at 17 NTC values across the band;
  - 8 coordinate ascents into the interior from the worst points, NTC included;
  - 2000 random points.

  The worker pool runs it in about 7 minutes on 10 cores.
- **Results.**
  - U1: the largest error found is 0.4520 mV, at a vertex. The ascents and the full band give the same value; the random points reach 0.3779 mV.
  - U2: 0.1911 mV, at a vertex; the random points reach 0.1813 mV.
  - In both cases the worst point is at the band's end.
- **A search, not a proof, so twice what it finds goes into the trips.**
  - Nothing here shows the worst case is at a vertex: the error isn't shown to be monotonic in each value. The review asked that a search be called a search.
  - The safety corner therefore carries 2 × the largest error found: 0.9039 mV = 0.0337 K for U1, 0.3821 mV = 0.0178 K for U2.
  - The factor 2 is a judgment, not a derived bound. The review's counterexample was 6 % above revision 4's maximum, and the random points stay 5–16 % below the vertex maximum. § 9 lists the factor as an assumption.
- **OUT1's states.**
  - RHYS's far end is now a second source. OUT1 high follows VREG; OUT1 low is constant.
  - For any history of VREG and any sequence of OUT1's states, the unsafe error is at most ∫ max(g(Δ_H), g(Δ_L)), with g(x) = 22.7 V/ms × x⁺ + 50 V/s × x⁻. Δ_H and Δ_L are the differential kernels with OUT1 high and low.
  - When OUT1 switches, its step moves U1's tap toward the new state. Inside the hysteresis that reinforces the decision. Any overshoot beyond it is added as a "kick": 0 for U1, 0.0115 mV for U2 at its worst point (through the differential capacitance).
  - OUT1's static levels, VOH ≥ VREG − 0.2 V and VOL ≤ 0.2 V ([TL]), enter the static trips.
- **Integration is exact.**
  - Every kernel is a sum of exponentials, so the integral is exact between the points where a kernel, or the choice between the two kernels, changes sign.
  - Those points are found on a 12-points-a-decade grid and refined (Illinois method).
  - A trapezoid sum at 600 points a decade agrees at both worst points: U1 0.45196 / 0.45196 mV; U2, less its kick, 0.17953 / 0.17953 mV.
- **Why 22 µF.**
  - With revision 4's 10 µF the same search finds 0.995 mV for U1. Twice that takes the cold safety corner to −0.004 °C.
  - The error scales with 1 / C, so VREG's output capacitance rises to ≥ 22 µF effective at 3.4 V, ≤ 100 µF in total. The TPS7B69 is stable from 2.2 to 100 µF ([T7] §7.3.3).
  - The slopes become: rise ≤ 500 mA / 22 µF = 22.7 V/ms; fall ≤ 1.1 mA / 22 µF = 50 V/s.
  - The falling floor rises from 2.653 to **2.6565 V** (3.0 mV of fall during the 59.5 µs latency).
  - Moving the cold trip up instead would have cost charging hours.
- **Recomputed trips.**
  - Safety corner: cold off **+0.0369 °C** (must be ≥ 0), hot off **+44.3373 °C** (must be ≤ 45); revision 4 had +0.038 and +44.339. The margins stay 0.04 K and 0.66 K.
  - OUT1's levels move the cold columns slightly: off +0.75 to +2.70 / +0.72 to +2.72 °C, on +1.09 to +3.06 / +1.07 to +3.09 °C. The hot columns are unchanged.
  - Cold hysteresis is now 0.24–0.53 K.
  - Energy corner unrounded: +2.7232 / +3.0894 / +41.5248 / +41.3251 °C.
- **Beyond the bands,** where the comparator already says "do not charge", the static distance from the trip exceeds the allowed error by ≥ 59 mV (U1) and ≥ 60 mV (U2). That is ≥ 15 and ≥ 321 times the error found.
- **The LM4041's bias** at the new floor is 70.6 µA, above its 65 µA minimum.
- **What the bound still assumes:**
  - the parasitic ranges above;
  - ≥ 22 µF effective on VREG;
  - the LDO's current limit at every output voltage (R5-N2);
  - ≤ 20 nA at V_T;
  - the network as modelled, starting from rest (R5-N2).

  F2 reruns the script with the chosen parts (§ 10).

### R5-M2: fixed (Rev 8's Figure 1 still to compare)

- **The finding is confirmed.**
  - ST's note 2 scales VCL, not only VBR, with temperature. Revision 4 shifted VBR only.
  - Revision 4 also rounded 39.31 V down to 39.3 V.
  - It called the complete bound independent of the capacitance and the current, while its overshoot term used ≥ 4.7 µF and ≤ 2 A.
- **The new bound** is computed by [calc/surge_bound.py](../calc/surge_bound.py) (standard library; output in [calc/surge_bound_output.txt](../calc/surge_bound_output.txt)). Every figure is rounded up to 10 mV.
  - **Clamp at 11.3 A, from Tj 25 °C** ([SM] note 3): 45.7 − 0.333 × (33 − 11.3) = 38.4739 V.
  - **Starting temperature.** One pulse a minute dissipates ≤ 45.7 V × 11.3 A × 1.443 ms = 0.745 J, taking the clamp at its rated maximum for the whole pulse. Through Rth(j-a) 75 K/W that averages +0.93 K. A pulse therefore starts at Tj ≤ 51 °C, not 50 °C.
  - **From Tj 51 °C** (note 2): 38.4739 × (1 + 9.8 × 10⁻⁴ × 26) = 39.4542 V. The review's +50 °C arithmetic gives 39.4165 V; the extra 1 K is the self-heating.
  - **IN ≤ 39.47 V,** adding 10 nH of TVS loop at 1.13 A/µs (11.3 mV). The TPS26600 is rated 62 V and −60 V. This bound needs only the TVS and its loop.
- **VIN ≤ 39.75 V** against the LT3652's 40 V absolute maximum, a margin of 0.25 V.
  - The switch passes current only forward and blocks backflow. So VIN can exceed the highest IN only by the ringing of the loop from IN through the TPS26600 to the VIN capacitors.
  - The energy in that loop bounds the overshoot to I × √(L / C):
    - I ≤ 12.3 A: the defined 11.3 A plus 1.0 A of the panel's own short-circuit current (about 0.6 A at STC, assumed with margin). A capacitor at IN (≤ 1 µF) adds only milliamps on the pulse's tail;
    - L and C are that loop's inductance and the VIN capacitors' effective capacitance at 40 V, over −30 to +50 °C and ageing;
    - the same bound covers the switch opening at any moment (OVP, current limit or a fault), because the loop's current is the same and its energy goes into C.
  - **F2/F3 requirement: √(L / C) ≤ 22.4 mΩ,** for example 5 nH with ≥ 10 µF or 10 nH with ≥ 20 µF. With 5 nH and 10 µF the overshoot is 0.275 V.
  - Revision 4's assumed 10 nH and 4.7 µF would give 40.02 V under this current bound. The review's 39.52 V used revision 4's 2 A.
- **The contradictory statement is gone.** IN's bound depends only on the TVS and its 10 nH. VIN's also depends on the loop's current, L and C. Neither depends on the switch's response time, its current limit or the OVP's delay.
- **Pulse rating from Tj 51 °C** ([SM] revision 4, Figure 1: 100 % up to 25 °C, falling linearly to 50 % at 150 °C):
  - 89.6 % of 1500 W, so 1344 W or 29.6 A;
  - the defined pulse is ≤ 39.47 V × 11.3 A = 446 W (33 %), and 11.3 A (38 %).
- **Cold breakdown** at −30 °C: ≥ 31.4 × (1 − 9.8 × 10⁻⁴ × 55) = 29.71 V, above the cold Voc of 28 V.
- **Negative pulse:** IN ≥ −39.47 V.
- **F6 thresholds** (§ 7 item 2) are now IN ≤ 39.47 V and VIN ≤ 39.75 V, both polarities, cold and from +50 °C.
- **Sources, and what is open.**
  - The review read the SM15T33CA row and notes 2 and 3 in DS0683 Rev 8 (May 2022). The formula, RD and αT used here are those.
  - The review also asked that power derating be confirmed from that source before F1 closes, not left to F2. Here it isn't done yet.
  - On 27.10.2026 every download of Rev 8 from st.com timed out from this machine, the family PDF the review used included, and the browser tools didn't respond.
  - `pcb-review`, the new reviewer session, has no copy and declined to quote one from memory, rightly.
  - The derating curve and Rth(j-a) therefore come from the archived 2007 revision 4. It has the same VBR, VCL, IPP and αT.
  - Comparing Rev 8's Figure 1 is in § 9 and § 10, and the question of how to get the PDF goes to the coordinator. If Rev 8's curve were lower, the pulse's 33 % of the derated power leaves room. The ceilings themselves don't use Figure 1.

### R5-M3: fixed

- **The finding is confirmed** ([DZ], DS18001 Rev 33-2):
  - 27.4 mV/°C sits under "Min" and the maximum is blank;
  - 23.1 V is the reverse-leakage test voltage;
  - ZZT is specified only at 2 mA.

  The 36.3 V and 38.1 V ceilings and the cold lower bound didn't follow.
- **Of the two closures the review offered, revision 5 takes the second.** The LDO's protection comes from the corrected upstream envelope:
  - the BZX84C33 is removed;
  - the feed diode blocks backflow, so the LDO's input can't exceed the highest IN, ≤ 39.47 V during the defined surge;
  - that is inside the TPS7B6933's 40 V operating range, so VREG stays regulated through the surge. 45 V is allowed for 200 ms.
- **The independent 62 V claim is withdrawn.** Beyond the defined surge nothing protects the LDO on its own; a sustained overvoltage makes the TVS conduct and opens the fuse.
- **The ratings follow the retained argument:**
  - the feed diode from IN stays ≥ 100 V (negative pulse);
  - the VBUS feed diode rises from ≥ 40 V to **≥ 60 V**, because revision 4's 40 V relied on the Zener's 38.1 V. With VBUS at 0 V it sees ≤ 39.47 V;
  - the 1 kΩ now only charges the LDO's input capacitor. Its pulse energy is ≤ ½ × C × (39.47 V)², 0.78 mJ with 1 µF, which F2 checks against the resistor's pulse rating.
- **D12:** one unique part fewer.

### R5-m1: fixed

- **The finding is confirmed.** A battery connected above the float can't fall to the float when the charger stops. And 4.30 V lies inside U3's trip band (4.29–4.43 V), so whether it trips there depends on the unit.
- **The blind time.**
  - Connecting the battery while the interlock is powered, U3's input rises with τ ≤ 23.8 ms (100 nF ± 10 % on 216 kΩ).
  - So U3 trips after τ × ln(V / (V − V_trip)): ≤ 0.1 s with ≥ 70 mV of overdrive above the unit's own trip, longer with less.
  - No fixed deadline is claimed.
- **The added charge, separately for each case:**
  - **a healthy charger adds none.** A battery above U3's trip is above both floats (≤ 4.25 V), so neither voltage loop delivers charge current;
  - **a failed charger,** the case U3 backstops, delivers at most its regulated current until U3 trips:
    - ≤ 1.56 A × 0.1 s = 0.16 C (0.04 mAh) from the LT3652;
    - ≤ 0.444 A × 0.1 s = 0.044 C from the BQ25170.

    That is R-P4's permissible transient. It moves the cells' voltage by far less than a millivolt.
- **The F6 test** (§ 7 item 1):
  - first find this unit's V_trip with a lab supply at the battery input, sweeping 4.1 → 4.5 V with both sources present;
  - healthy chargers, connected at V_trip + 70 mV and at 4.50 V (above every unit's trip): U3 trips within τ × ln(V / (V − V_trip)), ≤ 0.1 s. Meanwhile the current into the battery stays ≤ 1 mA and its voltage doesn't rise;
  - a failed charger: the LT3652 with its feedback divider set for a 4.60 V float, connected at 4.50 V. U3 opens the chain within 0.1 s, ≤ 0.16 C is delivered meanwhile, and the chain stays open;
  - 4.30 V is not a pass/fail point;
  - each connection is repeated with the interlock unpowered: the chains stay open until U4 releases.

### R5-N1: accepted

- **The reproduction stands.** The review asked for a winter rerun if corrective hardware changed the trips. They changed:
  - OUT1's VOH drop raises the energy corner's cold "off" trip from +2.709 to +2.723 °C;
  - the model now rounds every trip to 10 mK toward less charging: +2.73 / +3.09 / +41.52 / +41.32 °C (revision 4: +2.71 / +3.09 / +41.52 / +41.33).
- **What the rerun changes** (diff of [calc/winter_model_output.txt](../calc/winter_model_output.txt) against revision 4's):
  - The `codex` and `r2check` bodies are unchanged. So are the December means, the worst windows and the longest stretch without charging, 59.8 days.
  - **mobric's 8 faded cells on the adaptive schedule:**
    - still no outage hour in any case;
    - lowest charge 27 %;
    - lean 4.4–13.4 days and survival ≤ 1.1 days a winter (revision 4: ≤ 13.5 and ≤ 1.0);
    - the read limit stays **3.99 mAh** (3.98 mAh at R-P7's floor limit).
  - **The fallbacks shrink:**
    - 14 faded cells allow 6.14 mAh instead of 6.39 (7.15 instead of 7.80 new; 6.13 instead of 6.38 at the floor limit);
    - without adaptive switching, 1.66 and 2.59 mAh instead of 1.86 and 2.79. M1's pessimistic read, 2.79 mAh, now exceeds even 14 faded cells' fixed-schedule limit.
  - **One verdict changes on the fixed schedule.** M2 pessimistic at a fixed 15 min on 8 faded cells now fails the energy corner: 1 winter, 15 days, and 16–17 days at 70° or due south. Revision 4 passed it with 8 % lowest.
    - D13 already recommends the adaptive schedule, so the recommendation doesn't change, but the fixed schedule is no fallback for 8 cells.
    - The smallest fixed-schedule packs at the energy corner grow by 1–2 cells. For example, M2 pessimistic needs 8 cells new (9 faded) instead of 7 (8), and M1 pessimistic 13 (16) instead of 12 (15).
  - **Today's 3 cells** still have no outage on the adaptive schedule (lowest 14 %), with up to 24 lean and 6 survival days a winter.
  - **Recovery:** more hibernations on the fixed profiles (M2 pessimistic 4 instead of 3). Every one ends in a restart, and the TPS3840-only runs recover 4 of 4 cut-offs.
- R-P10's wording doesn't change. Its conditions still hold for the chosen option.

### R5-N2: accepted

- **Chain opening isn't current stopping.** 59.5 µs is U4 to the chains opening. Q3's ≈ 0.48 ms holds only with ≤ 1 nF (assumed), and neither charger's datasheet bounds its own response.
  - So the complete stop is now a requirement, not a result: **each charger's current into the cells below 10 mA within 10 ms of its chain opening, and ≤ 20 mC from both together meanwhile** (R-P4).
  - F2 checks the datasheets where they say anything; F6 measures it (§ 7 item 1).
- **Rise slope: 22.7 V/ms with 22 µF.**
  - It takes the LDO's ≤ 500 mA current limit as the most it can deliver. [T7] specifies that limit only with OUT shorted to ground, so its holding at every output voltage and during start-up is an assumption.
  - F2 asks TI. F6 measures VREG's rise at start-up and on panel and VBUS steps.
  - Revision 4's "global 50 V/ms" is gone.
- **Fall slope: 50 V/s.** The LDO doesn't sink current and the feed diodes block backflow, so only VREG's own load can pull it down.
  - That load is ≤ 1.1 mA: the dividers, the LM4041, the comparators, U4 and the gate drives at their highest.
  - F2 adds any other path the schematic gets, such as ESD or test-point leakage.
- **The regulated window at the real load.** [T7] specifies ± 3 % for 1–150 mA; the interlock draws 0.74 mA. So 3.2–3.4 V at this load is labelled an assumption. The safety corners don't depend on it:
  - they sit at the lowest VREG;
  - above 3.4 V the offset, hysteresis and output drop are smaller fractions of VREG, so every trip moves toward nominal;
  - only U4's release, and with it the charging hours, needs VREG above VIT+ (≤ 3.17 V).

  F2 asks TI for the accuracy below 1 mA, or adds a preload and reruns the filter search. F6 measures VREG at the real load (D5, § 9, § 10).
- **U4's VOH between VIT− and VIT+** is still taken to scale, as revision 4 said. Lower drive only inhibits charging, and the gate drive computed down to 2.955 V doesn't claim a minimum charging current in that band.
- **Initial conditions.**
  - The bound covers the network as modelled, starting from rest and driven only by VREG and OUT1 within the slopes. Any charge left by an earlier dip or restart is part of such a history, so it is covered.
  - It doesn't cover a change of the network itself: plugging the NTC in or out while powered, a part out of tolerance, or injected charge (ESD).
  - Unplugging reads cold, the safe side. Plugging into hot cells while powered moves V_T down through both taps in about 10 µs, and a chain could close for about that long.
  - **F6 NTC hot-plug test:** any closing must last ≤ 100 µs and deliver ≤ 1 mC (§ 7 item 1).

## Changes beyond the review

- **VREG's output capacitance** is ≥ 22 µF effective at 3.4 V, ≤ 100 µF in total (R5-M1). It sets both slopes and the falling floor, 2.6565 V.
- **VIN capacitors and loop:** √(L / C) ≤ 22.4 mΩ, rated ≥ 50 V; ≤ 1 µF at the TPS26600's IN (R5-M2).
- **The Zener is removed,** and the VBUS feed diode is rated ≥ 60 V (R5-M3).
- **The complete-stop requirement** (10 mA within 10 ms, 20 mC) and the **NTC hot-plug** test (R5-N2).
- **The winter model's energy corner** is now rounded toward less charging rather than to the nearest value. This moves the hot "on" trip from 41.33 to 41.32 °C as well (GATE_CORNER in `winter_model.py`).
- **REQUIREMENTS.md:**
  - R-P1 and R-P4 are marked *(rev 5)*;
  - the header cites this response;
  - the winter verdict rows carry the rerun's figures (3–6 survival days on today's pack; 4–13 lean days and ≤ 1.1 survival days on 8 faded cells).
- **STATUS.md:**
  - the phase;
  - the D5 and D13 rows; D11 names `pcb-caseing` (no content change);
  - the open question on Rev 8;
  - the roles. Reason Network is gone, and the team uses the local intercom. The coordinator is the Codync "PCB" bot on Pi, reached with `intercom bot --to pcb`; then `pcb-design`, `pcb-caseing` and `pcb-review`.
  - Codex's five reviews keep their authorship and commits. The old Reason addresses appear only as history.
- **ARCHITECTURE.md:**
  - the header;
  - § 1 and § 2 (the new ceilings);
  - D5 throughout;
  - § 4.4, § 4.5 and D13 (the rerun);
  - § 7 items 1 and 2;
  - § 8 (no design question; the Rev 8 question to the coordinator);
  - § 9, § 10;
  - D12 (one part fewer);
  - D11 names `pcb-caseing`;
  - Sources: [SM] now cites Rev 8 as read by the review, and the archived revision 4; [DZ] is kept as the source for the removal.
- **Scripts:**
  - **`interlock_trips.py`:**
    - the independent search with a worker pool;
    - OUT1 as a source;
    - exact integration with a trapezoid check;
    - VOH and VOL in the static trips;
    - 22 µF;
    - the 2× allowance;
    - the review's point;
    - an assert that the safety corners hold (cold ≥ 0 °C, hot ≤ 45 °C).
  - **`surge_bound.py`** is new.
  - **`winter_model.py`:** only the revision and GATE_CORNER.

## Still open

- **For the coordinator** (practical, not a design choice): how to get ST's DS0683 Rev 8 into `build/f1-revision/research/power/`, so Figure 1 can be compared before the F1 gate. Options go in the result message.
- **For mobric:** no design question. The F1 gate: approving D2–D4 and D6–D14. Installing KiCad 9.0.x (R1).
- **For F2** (§ 10):
  - Rev 8's Figure 1 against revision 4's, if not done before the gate;
  - the VIN loop, √(L / C) ≤ 22.4 mΩ, with effective capacitance at 40 V;
  - the feed diodes (≥ 100 V from IN, ≥ 60 V from VBUS) and the 1 kΩ's pulse rating;
  - VREG ≥ 22 µF effective;
  - the TPS7B6933's current limit at every output voltage and its accuracy below 1 mA, from TI;
  - the chargers' stop response against R-P4's 10 ms and 20 mC;
  - a rerun of `interlock_trips.py` with the chosen parts;
  - the items carried from revision 4 (chain FETs, U3's abuse limit, the −10 °C limit, the batch, prices).
- **For F3:** the TVS loop (10 nH) and the IN-to-VIN loop.
- **For F6** (§ 7):
  - the rail: dips, restarts, latency, complete stop, rise slope;
  - battery connection, healthy and failed;
  - NTC hot-plug;
  - the defined pulse against 39.47 / 39.75 V;
  - the items carried from revision 4.
- **Not proven:** the filter maximum is a search result carried at twice its value. Monotonicity, or another argument that would make it a bound, isn't shown.

## Where the evidence is

- **Datasheets:** in `hardware/station-pcb/build/f1-revision/research/power/` (gitignored), each in its own directory:
  - ST SM15T, revision 4 (2007), in `st_sm15t_mirror/`. Rev 8 couldn't be downloaded (above);
  - Diodes BZX84 in `bzx84_diodes/`;
  - TI TPS7B69 in `tps7b69_ti/`: ± 3 % at 1–150 mA, current limit 150–500 mA with OUT shorted, output capacitor 2.2–100 µF;
  - the earlier ones as listed in [F1-response-r4.md](F1-response-r4.md).
- **Script hashes (SHA-256):**
  - `interlock_trips.py` 5e00967cd07e1c65d111117bd3f0684d631f01bd16eab762be7dac3f4c375f12;
  - `winter_model.py` 0e5a4e29c5315b1ef28588eec221e3b6d01f6ba7c08e58e2b7d1de090f6c92a2;
  - `surge_bound.py` afa94fe73151edf88c115e9dcc8509f7e79e2e1d9fcff017610122f0d03f9d0c.

  Each output file prints its script's hash.
- **Reproducing the outputs** (from `hardware/station-pcb/`; Python 3.9, standard library only):
  - `python3 -I docs/calc/interlock_trips.py` (about 7 minutes on 10 cores);
  - `python3 -I docs/calc/surge_bound.py`;
  - `python3 -I docs/calc/winter_model.py codex build/f1-revision/pvgis/ser60/series.json`;
  - `python3 -I docs/calc/winter_model.py r2check build/f1-revision/pvgis/ser45/series.json`;
  - `python3 -I docs/calc/winter_model.py scenarios build/f1-revision/pvgis/ser45-az233/series.json build/f1-revision/pvgis/ser70-az233/series.json build/f1-revision/pvgis/ser45/series.json`.
- **Key output lines:**
  - interlock: "Unrounded safety corners: cold off +0.0369 C, hot off +44.3373 C"; U1 "largest error found 0.4520 mV"; U2 "0.1911 mV"; "R5-M1's U1 point … With revision 4's 10 uF … OUT1 high alone is 0.9044 mV";
  - surge: "IN <= 39.47 V", "VIN <= 39.75 V (rated 40 V absolute; margin 0.25 V)", "the defined pulse is <= 446 W (33 %)";
  - winter: the energy-corner row "none (lowest 27 %)" for M2 adaptive pessimistic on 8 faded cells, and the read limit "3.99 mAh".
- **The whole regeneration**, all three scripts, took 6 min 49 s on this Mac (Apple M5, 10 cores).
- **Firmware:** not touched, compiled or flashed.
