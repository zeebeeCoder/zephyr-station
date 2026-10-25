# F1 re-review — revision 1

Reviewed 2026-10-25 by `mobric/mikolaj-codex` for `mobric/pcb-lead`.

Baseline: `a22e006adac87dbdc0b3d4937bb24c64635bde50`, branch `hardware/station-pcb`. Reviewed REQUIREMENTS.md, ARCHITECTURE.md, STATUS.md, F1-response.md, winter_model.py and its output, against F1-codex.md. Only this review file was written in the worktree; no commit, firmware modification or flashing.

**Verdict: substantial improvement, but not ready to close F1 unconditionally.** Original items: **9 resolved, 7 partly resolved, 0 wholly unresolved**, counting the response's additional “Budget notes” row. New/residual findings below: **1 blocker, 5 major, 4 minor**. “Resolved” means addressed at the architecture level, not bench-qualified hardware.

## Original-item disposition

| Original item | Verdict | Evidence and remaining work |
|---|---|---|
| B1 — reverse FET cannot inhibit charging | **Partly** | The topology error is removed: LT3652 SHDN and BQ25170 ISET are documented control paths; CN alternative uses opposing FETs. But the startup guarantee is attributed to the wrong comparator variant, and the tolerance/hysteresis specification remains incomplete. R2-B1, R2-M1. |
| M1 — winter model | **Partly** | Exact rerun reproduces the committed output; independent baseline confirms adaptive results. Hourly cold gating, clipping, PM skipping and continuous SOC are present. The interlock's specified hysteresis is absent, and it can change the no-outage result. R2-M1. |
| M2 — USB bridge leakage | **Resolved** | D3 makes VIO/VDD5 USB-powered and specifies two partial-power-down translators for UART; four-state testing is explicit. This resolves the architectural battery-fed VIO issue. Verify actual supply ramps, DIR bias, reset-transistor leakage and V3 discharge in F2/F6. |
| M3 — sleep bound | **Partly** | Switched breakout, pin-state inventory, converter VIN/VOUT separation and RF-switch load are real improvements. The claimed bound still uses typical values and fails its own low-battery example. R2-M2. |
| M4 — cold Voc/clamp | **Partly** | LT3652 has adequate continuous-input headroom for the assumed 28.05 V Voc. SMBJ28A is not yet a demonstrated <40 V transient protection design; CN OVP dynamics remain an F2 proof obligation. R2-M3. |
| M5 — INA measurement meaning | **Partly** | Signed current, bus+shunt voltage, Kelvin routing and mandatory power-down are fixed. The residual charge-capacity assertion is unsupported and its termination drop is wrong for the new charger. R2-m2. |
| M6 — SPI in ISR | **Resolved** | RadioLib 7.8.1 attaches the application callback; a flag-only callback and task-context servicing remove the identified call path. Verified in cached version-specific source. Application implementation and soak test remain F5/F6. |
| m1 — cadence/timing assumptions | **Partly** | Timing is labelled nominal and schedule overlap is acknowledged. The actual pessimistic event table still uses nominal PMS duration; cadence counts do not implement the described skipped slots. R2-m1. |
| m2 — Ra-01H RX current | **Resolved** | 12.15 mA is used in the input table and RX_FIX calculations. |
| m3 — invalid LDO alternative | **Resolved** | Removed from D6; low-battery converter headroom is explicitly required. |
| m4 — implementation checklist | **Resolved** | §10 carries forward protection, connectors, 1-Wire ESD, stackup, antenna clearance, M3 holes, test points, ratings and fuse/shunt coordination. D14 gives a reasonable field/internal connector split; exact parts properly remain F2 work. |
| m5 — provenance labels | **Resolved** | Owner/photo, assumed and model-derived are now separated; exact input hashes and dated part identifiers are recorded. This does not validate each new “computed” claim: see R2-m2. |
| N1 — pin/hold checks | **Resolved** | GPIO14 sensor switch introduces no direct conflict. NSS pull-up, CHRG pull-up voltage and digital/RTC hold distinction are explicit. The new LT3652 imposes an additional status-pin supply constraint, R2-M4. |
| N2 — air format/power | **Resolved** | Explicit settings, manual 4-byte RadioHead framing, 28-byte TX and 7-byte RX are specified; source supports the intended air format and 10 dBm mapping. Gateway bench confirmation remains necessary. Adaptive request availability is a separate system-level issue, R2-m4. |
| N3 — converters and conditions | **Resolved** | True-disconnect choice remains valid, low-input margin is acknowledged, INA power-down is mandatory, and transient/inrush/restart tests are included. |
| Budget notes | **Partly** | Per-boot INA state issue is addressed; failed/requested reads get a stated allowance. Actual pessimistic timing and the modeled low-energy restart behavior still need alignment with implementation. R2-m1, R2-M1. |

## Blocker

### R2-B1 — Fail-safe startup is claimed for TLV3012, but the guarantee belongs to TLV3012B

**Location:** ARCHITECTURE.md D5 Interlock; F1-response.md B1; REQUIREMENTS.md R-P4.

The text selects “for example TLV3012 (output driven low below its minimum supply)” and uses that as evidence that TEMP_OK is fail-safe. [TI TLV301x datasheet Rev C, §§9.4 and 9.4.5](https://www.ti.com/lit/ds/symlink/tlv3012.pdf) explicitly adds POR to the **B variants**; the defined low output applies to **TLV3012B**. Plain TLV3012 does not inherit it. The alternative MCP6542/LM4041 also needs a separately demonstrated supply-good implementation. Naming an AND with supply-good without defining the supervisor does not prove the behavior.

The old body-diode error is fixed, but a charge-safety guarantee cannot be closed using the wrong part's specification. **Fix:** select an exact POR-capable comparator/supervisor and define both window comparisons, output polarity/combining and enable pull-downs. Prove every source combination, slow ramp and brownout. Do not wire push-pull comparator outputs together. Retain the documented SHDN/ISET methods; they are appropriate. Recalculate both temperature endpoints, NTC tolerance, offset, thermal gradient and both directions of hysteresis for the actual parts.

## Major

### R2-M1 — D13's survival result omits the specified interlock hysteresis and implementation errors

**Location:** ARCHITECTURE.md §§4.4–4.5, D5, D13, §6.10; winter_model.py `simulate()` and `PROFILES`.

The model uses a stateless `t_low <= t_cell <= t_high` test. D5 requires 2–3 K hysteresis. A cold cutoff at +1°C with a 3 K restart separation resumes charging at +4°C, not immediately above +1°C. The distinction is particularly important on short, cold sunny days. Nominal +1°C with ±1 K error also does not mean the conservative energy cutoff is +1°C: one tolerance corner cuts off at +2°C. Both threshold directions must still satisfy the 0/45°C safety envelope.

**Independent numerical evidence:** a separate implementation reproduces the baseline adaptive result: no outage, **44.542 lean days**, no survival days, **22.511%** minimum SOC over 18 complete seasons. Keeping the same PV data, loads and all other assumptions but adding a cold Schmitt state yields:

| Cold disable / re-enable | Outage seasons | Outage days | Lean / survival days | Minimum SOC |
|---|---:|---:|---:|---:|
| Baseline stateless +1°C | 0 | 0 | 44.54 / 0 | 22.51% |
| +1 / +3°C | 0 | 0 | 158.71 / 48.42 | 6.10% |
| +1 / +4°C | 1 | 9.71 | 190.54 / 76.67 | 0% |
| +2 / +5°C | 1 | 10.75 | 282.08 / 96.88 | 0% |

These are **sensitivity cases, not predictions of an unspecified final circuit**. They retain the gate state across hours, start inhibited, disable above 43°C and re-enable below 40°C. A panel-powered interlock's real nightly reset state must also be modeled. The +1/+4 case alone demonstrates that the currently permitted hysteresis can invalidate the claimed result even without extra load or SOC-estimator error.

Two further implementation assumptions are not yet represented: the model knows exact stored energy, whereas D13 uses an uncalibrated cold-cell resting-voltage estimate; and the model turns the station off after depletion until 5% energy recovers, whereas no corresponding UVLO/restart/backoff mechanism is specified. A resetting MCU can repeatedly start a full read instead. The adaptive case also uses nominal M2 loads only; the pessimistic cases do not test adaptive scheduling.

**Fix:** define off/on thresholds and their worst-case tolerances, model hysteresis and source power cycling, add adaptive pessimistic loads and SOC-estimation error, and specify low-energy recovery. Reissue D13(a–d) numbers from that circuit/policy. D13(b)'s 24.7 Ah is M1 nominal under the original gate, not a general guarantee; D13(c) is correctly labelled illustrative; D13(d)'s outage duration remains conditional on the modeled restart rule. Do not approve the existing “survives every case” conclusion as the hardware acceptance condition.

### R2-M2 — “95.8 µA bounded” still is not a bound and does not meet R-P7 across the battery range

**Location:** REQUIREMENTS.md R-P7 and §3; ARCHITECTURE.md §§4.1–4.2, §7.6; F1-response.md M3.

§4.2 now explicitly admits “bounded” uses typicals where maxima are absent and “isn't a guaranteed bound,” then says it meets the ≤100 µA bounded target. These statements conflict. ESP32, converter VOUT current, LT3652 bias and catch-diode leakage remain typical/estimated; other entries are allowances. All inventory values are at 25°C, despite the outdoor operating range. The 85% switching-only efficiency is assumed.

Independent summation gives approximately **95.73 µA** at 3.7 V/85%, consistent with the displayed rounded result. At the document's own 3.0 V/70% case it becomes **131.03 µA**. That is an admitted counterexample to the unqualified R-P7 requirement. The updated inventory is useful, but “fixed” overstates closure.

**Fix:** call this a conditional high-side estimate, separate guaranteed maxima from measured acceptance limits, define voltage/temperature/source conditions for R-P7, and obtain owner agreement if the requirement is relaxed. Otherwise select parts/values that meet it and validate corners. Preserve the board-versus-cell distinction and include actual isolation, status and diode paths. No amount of arithmetic turns an unpublished maximum into a guaranteed bound.

### R2-M3 — SMBJ28A does not by itself establish the promised LT3652 transient limit

**Location:** ARCHITECTURE.md §2/D5/§10; REQUIREMENTS.md R-P1.

The revised continuous-voltage calculation is correct: `22.4 × 1.05 × (1 + .0035 × 55) = 28.0476 V`, within LT3652's 32 V operating input range. But “clamps below 40 V for moderate surges” is undefined. [Littelfuse SMBJ table](https://www.littelfuse.com/~/media/electronics/datasheets/tvs_diodes/littelfuse_tvs_diode_smbj_datasheet.pdf.pdf), locally verified, gives SMBJ28A **28 V stand-off, 31.1–34.4 V breakdown and 45.4 V clamp at 13.3 A**. The last value exceeds the LT3652's 40 V absolute maximum. Even continuous Voc is slightly above nominal TVS stand-off; cold breakdown arithmetic is not a stand-off/leakage guarantee.

This does not prove SMBJ28A is unusable for the current-limited panel. It proves the present transient-survival claim is not established. **Fix:** define the surge waveform, source impedance/current and temperature; bound maximum clamp voltage at the protected pin, including wiring inductance. Qualify off-state leakage at maximum cold Voc. Add limiting/OVP or choose a higher-rated charger if needed. The CN3791 alternative's 26.1–26.9 V static OVP also needs response-time/overshoot and restart/hysteresis analysis; a DC trip number alone is insufficient.

### R2-M4 — LT3652 CHRG cannot unconditionally be pulled to an always-on 3.3 V rail

**Location:** ARCHITECTURE.md §3 charger-status row, §4.2 zero-current assumptions, D5; REQUIREMENTS.md R-F10.

The inherited CHRG-to-3V3 connection needs requalification for the new charger. [LT3652 absolute ratings, p.2, and CHRG description, p.7](https://www.analog.com/media/en/technical-documentation/data-sheets/3652fe.pdf) limit CHRG relative to **VIN** (absolute ceiling VIN+0.5 V); the pin description permits pulling it up as high as VIN. A floating/unpowered night-time VIN is not guaranteed to remain high enough for the always-on 3.3 V pull-up, especially at low battery or during startup/disconnection. “Open collector” does not mean independent-of-supply voltage tolerance.

**Fix:** prove the permitted CHRG voltage for every powered/unpowered state, or use isolation/level shifting and a source-domain pull-up. Account for leakage. No claim of actual damage is made without a schematic, but the proposed direct connection cannot be accepted from the present evidence.

### R2-M5 — The prescribed VBUS ramp to 20 V can damage the USB bridge

**Location:** ARCHITECTURE.md §7.1; F1-response.md B1 test list.

The test says to ramp **both panel input and VBUS from 0 to 20 V**. CH343P VDD5 is directly supplied by VBUS. [WCH CH343 datasheet §6.1](https://archive.decromancer.ca/bitsavers.org/components/wch/_dataSheets/CH343DS1.PDF) rates VDD5 to **6 V absolute maximum**. BQ25170's higher input tolerance/OVP does not protect the parallel CH343 branch.

**Fix:** split the procedures. Test the assembled USB input only within its specified 5 V operating envelope, using current limiting. Test higher-voltage behavior only on a suitably isolated interlock/charger fixture or after adding appropriately rated protection for every VBUS load. Do not follow the existing full-board 20 V USB procedure.

## Minor

### R2-m1 — The actual event model still does not include the claimed pessimistic PMS time or slot counts

**Location:** ARCHITECTURE.md §§4.1/4.3; winter_model.py `EVENTS`, `CADENCE`, `daily_mah()`; F1-response.md m1.

35.1 s is listed as the pessimistic PMS duration, but M1p/M2p reuse the old 31.6 s event totals and keep full-read duration 65/63.8 s. Extending PMS by 3.5 s alone adds **14.0 mAh/day** at 100 mA/5 V/90% efficiency for 96 reads, before the longer CPU-on time. The global 5% allowance may cover some of it, but then cannot also be presented as an independent request/failure allowance.

The scheduled normal cadence retains 1344 listens/day despite skipping the next minute during each >60 s full read; a strict minute grid would normally lose another 96 slots. Lean/survival similarly count full listen rates plus reads without defining whether those slots overlap. These are mostly conservative listen-count errors, not proof of energy starvation.

**Fix:** derive event durations and counts from one explicit timeline; distinguish retry energy from discretionary request margin and carry those numbers into the seasonal model.

### R2-m2 — Charging termination drop and “1–2% short” are not supported

**Location:** ARCHITECTURE.md D9 Effect on charging; F1-response.md M5.

With the recommended LT3652 at 1.5 A and C/10 termination, the nominal charge-current threshold is **0.15 A**, giving **15 mV** across 0.1 Ω, not 23 mV. The latter resembles the former CN3791's 16% threshold. If timer termination is selected, a single current threshold is not the full stopping rule. [LT3652 termination description](https://www.analog.com/media/en/technical-documentation/data-sheets/3652fe.pdf).

A voltage offset cannot be converted to a universal 1–2% capacity loss without cell/taper/temperature/load data. **Fix:** correct the charger-specific example, label capacity impact unknown, and retain the CC/CV/termination bench test. The bus+shunt and signed-current fixes themselves pass.

### R2-m3 — Nominal 500 mA USB charging does not establish a ≤500 mA input/charge limit

**Location:** REQUIREMENTS.md R-P11; ARCHITECTURE.md D3/D5.

[BQ25170](https://www.ti.com/lit/ds/symlink/bq25170.pdf) specifies ±10% charge-current accuracy, before external resistor tolerance. A nominal 500 mA setting can exceed the requirement's ≤500 mA charge limit. USB input also supplies CH343P and the interlock; it is not just battery charge current.

**Fix:** set ISET with tolerance margin and budget total VBUS consumption. Define behavior for the supported USB host/source states instead of assuming the nominal charger setting is the input limit. Test simultaneous panel/USB charging and termination under system load as part of F2/F6.

### R2-m4 — Adaptive listen periods no longer fit the unchanged gateway's request window

**Location:** ARCHITECTURE.md D4 Exchange, D13, §6.10; current gateway request timeout.

The unchanged gateway retries for 120 s, while lean listens every 300 s and survival every 900 s. Requests initiated just after a listen can time out before the next listen. This is a deterministic availability trade-off, beyond simply less frequent scheduled reporting.

**Fix:** explicitly include reduced on-demand availability in the owner's D13(a) decision and acceptance tests, or select an energy-budgeted cadence that preserves the request contract. A longer gateway retry would require separately authorized gateway changes, presently out of scope.

## Verification details and passed checks

### Model rerun and independent check

Executed the committed standard-library script read-only, writing stdout to `/tmp/pcb-f1-r2/rerun.txt`:

```text
python3 -I hardware/station-pcb/docs/calc/winter_model.py scenarios \
  hardware/station-pcb/build/f1-revision/pvgis/ser45/series.json \
  hardware/station-pcb/build/f1-revision/pvgis/ser70/series.json
```

The scenario output matches the corresponding committed output **byte for byte**, including the capacity search. All three cached input SHA-256 values match the manifest:

| Tilt | SHA-256 |
|---|---|
| 45° | `f562649f1b8aeba8fafad2ba230702f55eaac3ba422070619459137a5dfe9bb4` |
| 60° | `66b1548093a9b15f062adb9aed7e78c9c10262daec90899b09f742072edb8b19` |
| 70° | `788b403ed940ba836b5a913cb355a9ed3dc184118a6c93a62a87fbb984a225a9` |

Independent implementation used the documented event costs to recompute hourly normal/lean/survival loads, charged `min(P × .01/.86 × .85, 1.46×3.8)` when temperature permitted, subtracted PM energy below −10°C, applied `E×.02/730` self-discharge, capped energy at `10.2×.90×.85×3.7`, and applied the documented 40/50%, 15/20% mode thresholds and 5% restart rule. Counts include only July-2005 through June-2023; energy is continuous over the whole input. The Schmitt sensitivity modifies only the temperature gate as specified in R2-M1. Temporary reviewer implementation: `/tmp/pcb-f1-r2/independent.py` (baseline and +2/+5 case; other thresholds were parameterized in memory).

A smaller reporting defect: `simulate()` filters per-season statistics to complete seasons but returns `longest` from the whole series, including partial 2004/05 and 2023/24. The committed 0°C M1 row's longest outage starts **2005-03-07**, outside the stated 18-season statistics. Filter longest-run reporting consistently; this does not invalidate the reproduced baseline adaptive result.

### Parts, radio and checklist

- LT3652 SHDN is a documented disable input; its proposed ~10 V enable threshold clears its specified 4.2 V-output startup headroom. BQ25170 §7.3.1.1 explicitly monitors ISET continuously and permits open ISET with no charge current. The two control strategies are supported; their surrounding safety logic needs R2-B1 closure.
- SN74LVC1T45 documents high impedance with either supply at ground. Specify fixed DIR levels, non-floating inputs and the actual unpowered V3 behavior; this is now an implementation verification rather than the old architecture error.
- RadioLib source checked in `hardware/station-pcb/build/f1-revision/research/radio/radiolib-7.8.1/src/RadioLib-7.8.1/`: `SX1276.h/.cpp`, `SX1278.cpp`, `SX127x.cpp`, `Module.h`. The 3-argument Module constructor is valid; DIO1 defaults to NC. `setDio0Action()` attaches the supplied callback without mandatory SPI processing. `begin()` enables CRC, sets the stated RF parameters and supports gain 0; normal PA_BOOST output-power setting writes 0xF8 for 10 dBm. `forceLDRO(false)` and current-limit setting are appropriate. Explicit-header/CRC/IQ settings should still be verified in register dumps. [Upstream 7.8.1 source](https://raw.githubusercontent.com/jgromes/RadioLib/7.8.1/src/modules/SX127x/SX127x.cpp).
- F2/F3 checklist is materially improved and D14 is reasonable. Add closure for the new CHRG power-domain constraint, safe USB test voltage, protection waveform and all interlock transition thresholds. Neither checklist presence nor this review is a finished schematic/layout approval.
- Reviewer correction to the earlier report: CH343 §5.2 does describe VDD5/V3 at zero while VIO remains supplied, with conditions on I/O loading. My earlier statement that unplugged behavior was not described was too broad. The original 2 µA-as-bound/zero-current contradiction still warranted correction; the new isolated topology addresses it.

## Remaining verification limits

No final schematic, exact safety comparator/NTC network, surge specification, complete BOM, firmware implementation or hardware measurements are available for sign-off. PVGIS input files were hash-checked locally, not re-downloaded. Radio source was checked in the cached 7.8.1 package and against the retrievable upstream SX127x source; not every archive file was independently authenticated. SMBJ numbers were checked in the cached manufacturer table `/private/tmp/pwrres/work_parts/text/smbj_littelfuse.txt`; the old manufacturer PDF URL now redirects. No fresh stock/pricing or legal-compliance certification was attempted. Thermal cases, cell model, cold usable capacity, SOC estimation, snow and shading remain assumptions as the revision correctly states.

Before the next F1 gate: correct the comparator variant/startup proof, define and model the real hysteresis, qualify the input clamp and CHRG interface, reconcile R-P7, and remove the unsafe USB test instruction. Then regenerate the energy decision table and response dispositions.
