#!/usr/bin/env python3
"""Trip points of the charge interlock, with tolerances (F1 revision 2).

Circuit (ARCHITECTURE.md D5): a ratiometric NTC divider and three TLV3012B comparators,
all fed from the interlock rail VREG.
  NTC node     VREG - RS - V_T - NTC - AGND. V_T falls as the cells warm.
  U1 (cold)    IN+ = cold tap (RC1 from VREG, RC2 to AGND, RHYS from OUT1), IN- = V_T.
               OUT1 is high (charging allowed) while V_T is below the tap: warm enough.
  U2 (hot)     IN+ = V_T, IN- = hot tap (RH1 from VREG, RH2 to AGND), built-in hysteresis only.
               OUT2 is high while V_T is above the tap: not too hot.
  U3 (cells)   IN+ = LM4041-B (27 k from VREG), IN- = battery connector through R_OV1 / R_OV2,
               whose low side Q8 opens when VREG is off. OUT3 is high while the cells are
               below the trip.
Charging needs OUT1 AND OUT2 AND OUT3 high (series FETs, see D5).

Every input is a datasheet value or a labelled assumption. Standard library only:
  python3 -I interlock_trips.py
"""

import itertools
import math

# NTC: Shiheng MF52A 103F3950, R-T table (attachment I, P477-4B), kOhm (min, nominal, max).
# The table's spread already contains R25 +-1 % and B25/50 +-1 % (datasheet).
NTC_TABLE = {
    -2: (34.368, 35.161, 35.955), -1: (32.750, 33.489, 34.229), 0: (31.356, 32.049, 32.743),
    1: (29.757, 30.399, 31.041), 2: (28.374, 28.972, 29.570), 3: (27.060, 27.617, 28.174),
    4: (25.812, 26.330, 26.849), 5: (24.627, 25.109, 25.591),
    40: (5.258, 5.345, 5.432), 41: (5.046, 5.131, 5.217), 42: (4.843, 4.927, 5.011),
    43: (4.650, 4.733, 4.815), 44: (4.465, 4.546, 4.628), 45: (4.289, 4.368, 4.448),
    46: (4.120, 4.198, 4.277), 47: (3.959, 4.036, 4.113),
}
NTC_DRIFT = 0.005        # +-0.5 % long-term drift allowance (assumed; the datasheet's 1000 h
                         # stress tests allow up to 2 % at 125 C, far beyond this site)
NTC_SELF_HEAT_K = 0.10   # reads warm by at most this much (computed below; 2 mW/K in still air)
GRADIENT_K = 0.5         # NTC versus the coldest or hottest cell (assumed; F6 measures it)

# Resistors: 0.1 % initial plus 25 ppm/K over 25 +- 30 K (assumed part class).
R_TOL = 0.001 + 25e-6 * 30
RHYS_TOL = 0.01
RS, RC1, RC2, RHYS, RH1, RH2 = 12.0, 10.0, 24.3, 3320.0, 10.0, 3.92   # kOhm, 0.1 % E96 values

# TLV3012B (SBOS300C section 6.9, -40 to +125 C): offset +-9 mV, built-in hysteresis 2-8 mV.
VOS_MAX = 0.009
VHYS = (0.002, 0.006, 0.008)
VREG = (3.2, 3.3, 3.4)   # interlock rail; TPS7B6933 regulating (offsets scale with 1/VREG)

# U3: LM4041-B (SNOS641I): 1.225 V +-0.2 % at 25 C, 100 ppm/K maximum average drift, taken over
# the same 25 +- 30 K as the resistors (board temperature while charging is possible, assumed).
# Minimum operating current 65 uA over temperature. TLV3012B's own reference: 1.223-1.260 V.
R_OV1, R_OV2 = 768.0, 301.0   # kOhm, 0.1 % E96 values
R_LM, R_LM_TOL = 27.0, 0.01   # kOhm, LM4041 bias resistor from VREG
LM4041 = (1.225, 0.002, 100e-6 * 30, 0.065)   # nominal V, initial, drift, IRMIN mA
TLV_REF = (1.223, 1.242, 1.260)
# LT3652 float: VFB(FLT) 3.282-3.318 V at 25 C, 3.26-3.34 V over temperature (datasheet p.3),
# with a 0.1 % divider for 4.2 V. BQ25170: 4.2 V +-0.5 % at Tj = 25 C (VREG_ACC).
VFB_FLT = ((3.282, 3.318), (3.26, 3.34))


def r_ntc(t, k):
    """NTC resistance in kOhm at t deg C; k = 0 min, 1 nominal, 2 max (log-linear interpolation)."""
    a = math.floor(t)
    ra, rb = NTC_TABLE[a][k], NTC_TABLE[a + 1][k]
    return math.exp(math.log(ra) + (t - a) * (math.log(rb) - math.log(ra)))


def temp_at(ratio, rs, k, drift, lo, hi):
    """Temperature where V_T / VREG equals ratio, for one NTC corner."""
    for _ in range(60):
        mid = (lo + hi) / 2
        r = r_ntc(mid, k) * (1 + drift)
        if r / (rs + r) > ratio:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def par(a, b):
    return a * b / (a + b)


def cold_trips(rs, rc1, rc2, rhys, vos, vhys, vreg, k, drift):
    """U1 trip temperatures (off while cooling, on while warming)."""
    tap_hi = rc2 / (rc2 + par(rc1, rhys))           # OUT1 high pulls the tap up
    tap_lo = par(rc2, rhys) / (rc1 + par(rc2, rhys))  # OUT1 low pulls it down
    v_off = tap_hi - (vos - vhys / 2) / vreg         # V_T above this turns OUT1 low
    v_on = tap_lo - (vos + vhys / 2) / vreg          # V_T below this turns OUT1 high
    return (temp_at(v_off, rs, k, drift, -2, 5), temp_at(v_on, rs, k, drift, -2, 5))


def hot_trips(rs, rh1, rh2, vos, vhys, vreg, k, drift):
    """U2 trip temperatures (off while heating, on while cooling)."""
    tap = rh2 / (rh1 + rh2)
    v_off = tap + (vos - vhys / 2) / vreg            # V_T below this turns OUT2 low
    v_on = tap + (vos + vhys / 2) / vreg
    return (temp_at(v_off, rs, k, drift, 40, 47), temp_at(v_on, rs, k, drift, 40, 47))


def corners():
    sign = (-1, 1)
    cold, hot = [], []
    for s_rs, s1, s2, s3, sv, vh, vr, k, sd in itertools.product(
            sign, sign, sign, sign, sign, (VHYS[0], VHYS[2]), (VREG[0], VREG[2]), (0, 2), sign):
        rs = RS * (1 + s_rs * R_TOL)
        drift = sd * NTC_DRIFT
        cold.append(cold_trips(rs, RC1 * (1 + s1 * R_TOL), RC2 * (1 + s2 * R_TOL),
                               RHYS * (1 + s3 * RHYS_TOL), sv * VOS_MAX, vh, vr, k, drift))
        hot.append(hot_trips(rs, RH1 * (1 + s1 * R_TOL), RH2 * (1 + s2 * R_TOL),
                             sv * VOS_MAX, vh, vr, k, drift))
    return cold, hot


def ovp_trips(vref_lo, vref_hi, r1, r2):
    """U3 battery voltages over all corners: (off lo, off hi, on lo, on hi, hysteresis lo, hi)."""
    off, on, hys = [], [], []
    for vr, s1, s2, sv, vh in itertools.product(
            (vref_lo, vref_hi), (-1, 1), (-1, 1), (-1, 1), (VHYS[0], VHYS[2])):
        k = r2 * (1 + s2 * R_TOL) / (r1 * (1 + s1 * R_TOL) + r2 * (1 + s2 * R_TOL))
        off.append((vr + sv * VOS_MAX + vh / 2) / k)   # IN- rising past IN+ turns OUT3 low
        on.append((vr + sv * VOS_MAX - vh / 2) / k)
        hys.append(vh / k)
    return min(off), max(off), min(on), max(on), min(hys), max(hys)


def float_range(vfb_lo, vfb_hi):
    """LT3652 float voltage range for a 4.2 V divider of 0.1 % resistors."""
    ratio = 4.2 / 3.3 - 1                            # R_top / R_bottom
    return (vfb_lo * (1 + ratio * (1 - R_TOL) / (1 + R_TOL)),
            vfb_hi * (1 + ratio * (1 + R_TOL) / (1 - R_TOL)))


def main():
    nom_c = cold_trips(RS, RC1, RC2, RHYS, 0.0, VHYS[1], VREG[1], 1, 0.0)
    nom_h = hot_trips(RS, RH1, RH2, 0.0, VHYS[1], VREG[1], 1, 0.0)
    cold, hot = corners()
    c_off = [c[0] for c in cold]
    c_on = [c[1] for c in cold]
    c_hys = [c[1] - c[0] for c in cold]
    h_off = [h[0] for h in hot]
    h_on = [h[1] for h in hot]
    h_hys = [h[0] - h[1] for h in hot]

    # NTC self-heating at the cold trip: P = I^2 R, divided by 2 mW/K (still air, datasheet).
    r1 = r_ntc(nom_c[0], 1)
    i_ma = 3.4 / (RS + r1)
    p_mw = i_ma ** 2 * r1
    print(f"Resistors: RS {RS} k, RC1 {RC1} k, RC2 {RC2} k, RHYS {RHYS / 1000:.2f} M, "
          f"RH1 {RH1} k, RH2 {RH2} k; tolerance +-{R_TOL * 100:.3f} % (RHYS +-{RHYS_TOL * 100:.0f} %)")
    print(f"NTC current at the cold trip: {i_ma * 1000:.0f} uA, {p_mw:.3f} mW -> "
          f"self-heating {p_mw / 2:.3f} K in still air (allowance {NTC_SELF_HEAT_K} K)")
    print()
    print("| Trip | Nominal, deg C | Electrical worst case, deg C | Safety corner, deg C |")
    print("|---|---|---|---|")
    print(f"| Cold off (cooling) | {nom_c[0]:+.2f} | {min(c_off):+.2f} to {max(c_off):+.2f} | "
          f"{min(c_off) - NTC_SELF_HEAT_K - GRADIENT_K:+.2f} (must be >= 0) |")
    print(f"| Cold on (warming) | {nom_c[1]:+.2f} | {min(c_on):+.2f} to {max(c_on):+.2f} | "
          f"{min(c_on) - NTC_SELF_HEAT_K - GRADIENT_K:+.2f} |")
    print(f"| Hot off (heating) | {nom_h[0]:+.2f} | {min(h_off):+.2f} to {max(h_off):+.2f} | "
          f"{max(h_off) + GRADIENT_K:+.2f} (must be <= 45) |")
    print(f"| Hot on (cooling) | {nom_h[1]:+.2f} | {min(h_on):+.2f} to {max(h_on):+.2f} | "
          f"{max(h_on) + GRADIENT_K:+.2f} |")
    print()
    print(f"Cold hysteresis: nominal {nom_c[1] - nom_c[0]:.2f} K, range {min(c_hys):.2f}-{max(c_hys):.2f} K")
    print(f"Hot hysteresis: nominal {nom_h[0] - nom_h[1]:.2f} K, range {min(h_hys):.2f}-{max(h_hys):.2f} K")
    print(f"Energy corner for the winter model: off {max(c_off):+.2f} C, on {max(c_on):+.2f} C")
    print(f"Safety corners include NTC self-heating {NTC_SELF_HEAT_K} K (cold side only) and a "
          f"{GRADIENT_K} K NTC-to-cell gradient (both assumed).")

    v_lm, tol_lm, drift_lm, irmin = LM4041
    lm_lo, lm_hi = v_lm * (1 - tol_lm - drift_lm), v_lm * (1 + tol_lm + drift_lm)
    k_nom = R_OV2 / (R_OV1 + R_OV2)
    ov = ovp_trips(lm_lo, lm_hi, R_OV1, R_OV2)
    i_lm = (VREG[0] - lm_hi) / (R_LM * (1 + R_LM_TOL))
    r1_alt = 750.0                                   # divider re-centred on the internal 1.242 V
    alt = ovp_trips(TLV_REF[0] * (1 - drift_lm), TLV_REF[2] * (1 + drift_lm), r1_alt, R_OV2)
    fl25 = float_range(*VFB_FLT[0])
    flt = float_range(*VFB_FLT[1])
    print()
    print(f"U3 battery overvoltage: LM4041-B {v_lm} V ({lm_lo:.4f}-{lm_hi:.4f} V), divider "
          f"{R_OV1:.0f} k / {R_OV2:.0f} k")
    print(f"  nominal: off above {(v_lm + VHYS[1] / 2) / k_nom:.3f} V, on again below "
          f"{(v_lm - VHYS[1] / 2) / k_nom:.3f} V")
    print(f"  worst case: off above {ov[0]:.3f} to {ov[1]:.3f} V, on again below {ov[2]:.3f} to "
          f"{ov[3]:.3f} V; hysteresis {ov[4] * 1000:.0f}-{ov[5] * 1000:.0f} mV at the battery")
    print(f"  LM4041 current at VREG {VREG[0]} V: {i_lm * 1000:.0f} uA (minimum operating "
          f"{irmin * 1000:.0f} uA)")
    print(f"  with the TLV3012B's own reference instead (divider {r1_alt:.0f} k / {R_OV2:.0f} k): "
          f"off above {alt[0]:.3f} to {alt[1]:.3f} V (not used)")
    print(f"LT3652 float: {fl25[0]:.3f}-{fl25[1]:.3f} V at 25 C, {flt[0]:.3f}-{flt[1]:.3f} V over "
          f"the chip's temperature range; BQ25170: {4.2 * 0.995:.3f}-{4.2 * 1.005:.3f} V at 25 C")
    print(f"Margin from the highest LT3652 float to the lowest U3 trip: "
          f"{(ov[0] - flt[1]) * 1000:.0f} mV")


if __name__ == "__main__":
    main()
