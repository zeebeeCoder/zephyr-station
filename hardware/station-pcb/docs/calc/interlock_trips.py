#!/usr/bin/env python3
"""Trip points of the charge interlock, with tolerances (F1 revision 3).

Circuit (ARCHITECTURE.md D5): a ratiometric NTC divider and three TLV3012B comparators,
all fed from the interlock rail VREG, plus a TPS3840PL30 (U4) that watches VREG itself.
  NTC node     VREG - RS - V_T - NTC - AGND. V_T falls as the cells warm.
  U1 (cold)    IN+ = cold tap (RC1 from VREG, RC2 to AGND, RHYS from OUT1), IN- = V_T.
               OUT1 is high (charging allowed) while V_T is below the tap: warm enough.
  U2 (hot)     IN+ = V_T, IN- = hot tap (RH1 from VREG, RH2 to AGND), built-in hysteresis only.
               OUT2 is high while V_T is above the tap: not too hot.
  U3 (cells)   IN+ = LM4041-B (R_LM from VREG), IN- = battery connector through R_OV1 / R_OV2,
               whose low side Q8 opens when VREG is off. OUT3 is high while the cells are
               below the trip.
  U4 (rail)    RESET is high only while VREG is above its threshold, after a delay set by CT.
Charging needs OUT1 AND OUT2 AND OUT3 AND U4 high (series FETs, see D5).

Input filters: each V_T input sees V_T through R_IN with C_IN to AGND. U1's tap reaches its
input through R_F1 with C_IN to AGND; U2's tap has no capacitor. The time constants are chosen
so that a rising VREG can only make both comparators read "do not charge"; a falling VREG is
limited by the rail's capacitance and load, and its error is computed below.

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
LEAK_A = 20e-9           # leakage from V_T to AGND: ESD diode, capacitors, board (F2 requirement;
                         # it pulls V_T down, so it reads warm: counted on the cold side only)

# Resistors: 0.1 % initial plus 25 ppm/K over 25 +- 30 K (assumed part class).
R_TOL = 0.001 + 25e-6 * 30
RHYS_TOL = 0.01
RS, RC1, RC2, RHYS, RH1, RH2 = 12.0, 10.0, 24.3, 3320.0, 10.0, 4.02   # kOhm, 0.1 % E96 values

# TLV3012B (SBOS300C section 6.9, -40 to +125 C): offset +-9 mV, built-in hysteresis 2-8 mV,
# supply 1.65-5.5 V, quiescent current 3.6 uA maximum.
VOS_MAX = 0.009
VHYS = (0.002, 0.006, 0.008)
VREG = (3.2, 3.3, 3.4)   # TPS7B6933 regulating: 3.3 V +-3 % (offsets scale with 1/VREG)

# U4: TPS3840PL30 (SNVSB03E). VIT- = 3.0 V +-1.5 %, hysteresis 75-125 mV for VIT- <= 3.0 V,
# so it releases at 3.17 V at most, below the regulated 3.2 V. Detect delay tP_HL <= 30 us,
# specified for VDD stepping to 10 % below VIT-. Delay tD from CT: equations 6 and 7,
# RCT 350-650 kOhm, CT 1 uF with 0.8-1.2 uF effective at 3.3 V (assumed part class).
U4_VIT = (3.0 * 0.985, 3.0 * 1.015)
U4_HYS = (0.075, 0.125)
U4_TPHL_S = 30e-6
RCT = (350e3, 650e3)
CT = (0.8e-6, 1.2e-6)
# VREG while charging can be allowed: down to U4's lowest threshold in steady state, and down
# to 10 % below it while VREG falls, before U4 has certainly switched (conservative reading).
VREG_STATIC = U4_VIT[0]
VREG_FALLING = 0.9 * U4_VIT[0]

# Input filters (C0G capacitors, +-5 %; filter resistors 1 %).
R_IN, R_F1, C_IN, C_TOL, RF_TOL = 10.0, 20.0, 1.0e-9, 0.05, 0.01   # kOhm, kOhm, F
C_PIN = 5e-12            # comparator input plus layout, U2's tap (assumed)
# Fastest fall of VREG: its load over its capacitance. Load computed in main() (about
# 0.7 mA), bounded here by 1.0 mA; C_VREG >= 10 uF effective at 3.3 V (F2; the TPS7B6933
# allows 2.2-100 uF).
I_VREG_MAX_MA, C_VREG_MIN = 1.0, 10e-6

# U3: LM4041-B (SNOS641I): 1.225 V +-0.2 % at 25 C, 100 ppm/K maximum average drift, taken over
# the same 25 +- 30 K as the resistors (board temperature while charging is possible, assumed).
# Minimum operating current 65 uA over temperature. TLV3012B's own reference: 1.223-1.260 V.
R_OV1, R_OV2 = 768.0, 301.0   # kOhm, 0.1 % E96 values
R_LM, R_LM_TOL = 24.3, 0.01   # kOhm, LM4041 bias resistor from VREG
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


def corners(vreg_lo, vreg_hi):
    sign = (-1, 1)
    cold, hot = [], []
    for s_rs, s1, s2, s3, sv, vh, vr, k, sd in itertools.product(
            sign, sign, sign, sign, sign, (VHYS[0], VHYS[2]), (vreg_lo, vreg_hi), (0, 2), sign):
        rs = RS * (1 + s_rs * R_TOL)
        drift = sd * NTC_DRIFT
        cold.append(cold_trips(rs, RC1 * (1 + s1 * R_TOL), RC2 * (1 + s2 * R_TOL),
                               RHYS * (1 + s3 * RHYS_TOL), sv * VOS_MAX, vh, vr, k, drift))
        hot.append(hot_trips(rs, RH1 * (1 + s1 * R_TOL), RH2 * (1 + s2 * R_TOL),
                             sv * VOS_MAX, vh, vr, k, drift))
    return cold, hot


def slope_per_k(temps):
    """Smallest |d(V_T / VREG) / dT| over temps (deg C) for the nominal NTC, per kelvin."""
    def one(t):
        ratio = [r_ntc(x, 1) / (RS + r_ntc(x, 1)) for x in (t - 0.05, t + 0.05)]
        return abs(ratio[1] - ratio[0]) / 0.1
    return min(one(t) for t in temps)


def filter_check(c_trip, h_trip):
    """Time constants (s) of every comparator input over component and NTC corners, and the
    worst trip error (K) while VREG falls at its fastest. A rising VREG must leave U1's tap
    slower than its V_T input and U2's tap faster than its V_T input, at every temperature."""
    c_lo, c_hi = C_IN * (1 - C_TOL), C_IN * (1 + C_TOL)
    r_in_lo, r_in_hi = R_IN * (1 - RF_TOL), R_IN * (1 + RF_TOL)
    th_c1 = par(par(RC1, RC2), RHYS)                 # U1's tap, Thevenin
    th_h = par(RH1, RH2)                             # U2's tap, Thevenin
    rs_hi = RS * (1 + R_TOL)
    # V_T's Thevenin resistance RS || NTC is below RS at every temperature.
    tau_t_max_any = (r_in_hi + rs_hi) * 1e3 * c_hi
    tau_tap1_min = (R_F1 * (1 - RF_TOL) + th_c1 * (1 - R_TOL)) * 1e3 * c_lo
    tau_tap1_max = (R_F1 * (1 + RF_TOL) + th_c1 * (1 + R_TOL)) * 1e3 * c_hi
    tau_tap2_max = th_h * (1 + R_TOL) * 1e3 * C_PIN
    # Near each trip: the smallest and largest V_T Thevenin over the NTC spread and drift.
    def th_t(t, k, d):
        return par(RS, r_ntc(t, k) * (1 + d))
    th_c = [th_t(t, k, d) for t in c_trip for k in (0, 2) for d in (-NTC_DRIFT, NTC_DRIFT)]
    th_hh = [th_t(t, k, d) for t in h_trip for k in (0, 2) for d in (-NTC_DRIFT, NTC_DRIFT)]
    tau_t1_min = (r_in_lo + min(th_c) * (1 - R_TOL)) * 1e3 * c_lo
    tau_t2_min_any = r_in_lo * 1e3 * c_lo           # NTC shorted: V_T Thevenin 0
    tau_t2_max = (r_in_hi + max(th_hh) * (1 + R_TOL)) * 1e3 * c_hi
    slew = I_VREG_MAX_MA / 1000 / C_VREG_MIN          # V/s
    ratio_c = RC2 / (RC2 + par(RC1, RHYS))
    ratio_h = RH2 / (RH1 + RH2)
    err_c_v = slew * ratio_c * (tau_tap1_max - tau_t1_min)
    err_h_v = slew * ratio_h * tau_t2_max            # U2's tap lag counted as zero
    vlo = VREG_FALLING
    err_c_k = err_c_v / (vlo * slope_per_k(c_trip))
    err_h_k = err_h_v / (vlo * slope_per_k(h_trip))
    leak_v = LEAK_A * max(th_c) * 1e3
    leak_k = {v: leak_v / (v * slope_per_k(c_trip)) for v in (VREG_STATIC, VREG_FALLING)}
    return dict(tau_t_max_any=tau_t_max_any, tau_tap1_min=tau_tap1_min, tau_tap1_max=tau_tap1_max,
                tau_t1_min=tau_t1_min, tau_t2_min_any=tau_t2_min_any, tau_t2_max=tau_t2_max,
                tau_tap2_max=tau_tap2_max, slew=slew, err_c_v=err_c_v, err_h_v=err_h_v,
                err_c_k=err_c_k, err_h_k=err_h_k, leak_v=leak_v, leak_k=leak_k)


def vreg_load_ma(vreg):
    """Steady VREG load in mA at vreg: dividers at their highest current, LM4041, comparators,
    U4, ten gate pull-downs (all gates high)."""
    r_ntc_min = 2.0                                  # NTC at about +66 C, a hot board (assumed)
    i = vreg / (RS * (1 - R_TOL) + r_ntc_min)
    i += vreg / ((RC1 + RC2) * (1 - R_TOL)) + vreg / ((RH1 + RH2) * (1 - R_TOL))
    i += (vreg - LM4041[0] * (1 - LM4041[1] - LM4041[2])) / (R_LM * (1 - R_LM_TOL))
    i += 3 * 0.0036 + 0.0007 + 10 * vreg / 1100.0
    return i


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
    bands = (("regulated", VREG[0]), ("U4 static", VREG_STATIC), ("U4 falling", VREG_FALLING))
    res = {}
    for name, lo in bands:
        cold, hot = corners(lo, VREG[2])
        res[name] = dict(c_off=[c[0] for c in cold], c_on=[c[1] for c in cold],
                         c_hys=[c[1] - c[0] for c in cold], h_off=[h[0] for h in hot],
                         h_on=[h[1] for h in hot], h_hys=[h[0] - h[1] for h in hot])
    reg = res["regulated"]
    st = res["U4 static"]
    fall = res["U4 falling"]
    flt = filter_check((min(fall["c_off"]), max(fall["c_on"])), (min(fall["h_on"]), max(fall["h_off"])))

    # NTC self-heating at the cold trip: P = I^2 R, divided by 2 mW/K (still air, datasheet).
    r1 = r_ntc(nom_c[0], 1)
    i_ma = 3.4 / (RS + r1)
    p_mw = i_ma ** 2 * r1
    print(f"Resistors: RS {RS} k, RC1 {RC1} k, RC2 {RC2} k, RHYS {RHYS / 1000:.2f} M, "
          f"RH1 {RH1} k, RH2 {RH2} k; tolerance +-{R_TOL * 100:.3f} % (RHYS +-{RHYS_TOL * 100:.0f} %)")
    print(f"NTC current at the cold trip: {i_ma * 1000:.0f} uA, {p_mw:.3f} mW -> "
          f"self-heating {p_mw / 2:.3f} K in still air (allowance {NTC_SELF_HEAT_K} K)")
    print()
    print(f"VREG bands: regulated {VREG[0]}-{VREG[2]} V; U4 static {VREG_STATIC:.3f}-{VREG[2]} V "
          f"(lowest VIT-); U4 falling {VREG_FALLING:.3f}-{VREG[2]} V (10 % below the lowest VIT-)")
    print()
    print("| Trip | Nominal, deg C | Electrical worst case, VREG regulated | VREG down to U4's threshold "
          "| Safety corner, VREG falling to 10 % below it, plus the falling-rail error |")
    print("|---|---|---|---|---|")
    sc_c = NTC_SELF_HEAT_K + GRADIENT_K + flt["leak_k"][VREG_FALLING]
    sc_s = NTC_SELF_HEAT_K + GRADIENT_K + flt["leak_k"][VREG_STATIC]
    print(f"| Cold off (cooling) | {nom_c[0]:+.2f} | {min(reg['c_off']):+.2f} to {max(reg['c_off']):+.2f} | "
          f"{min(st['c_off']):+.2f} to {max(st['c_off']):+.2f} | "
          f"{min(fall['c_off']) - sc_c - flt['err_c_k']:+.2f} (must be >= 0) |")
    print(f"| Cold on (warming) | {nom_c[1]:+.2f} | {min(reg['c_on']):+.2f} to {max(reg['c_on']):+.2f} | "
          f"{min(st['c_on']):+.2f} to {max(st['c_on']):+.2f} | "
          f"{min(fall['c_on']) - sc_c - flt['err_c_k']:+.2f} |")
    print(f"| Hot off (heating) | {nom_h[0]:+.2f} | {min(reg['h_off']):+.2f} to {max(reg['h_off']):+.2f} | "
          f"{min(st['h_off']):+.2f} to {max(st['h_off']):+.2f} | "
          f"{max(fall['h_off']) + GRADIENT_K + flt['err_h_k']:+.2f} (must be <= 45) |")
    print(f"| Hot on (cooling) | {nom_h[1]:+.2f} | {min(reg['h_on']):+.2f} to {max(reg['h_on']):+.2f} | "
          f"{min(st['h_on']):+.2f} to {max(st['h_on']):+.2f} | "
          f"{max(fall['h_on']) + GRADIENT_K + flt['err_h_k']:+.2f} |")
    print()
    print(f"Safety corners at VREG {VREG_STATIC:.3f} V without the falling-rail error: cold off "
          f"{min(st['c_off']) - sc_s:+.2f} C, hot off {max(st['h_off']) + GRADIENT_K:+.2f} C")
    print(f"Cold hysteresis: nominal {nom_c[1] - nom_c[0]:.2f} K, range {min(fall['c_hys']):.2f}-"
          f"{max(fall['c_hys']):.2f} K")
    print(f"Hot hysteresis: nominal {nom_h[0] - nom_h[1]:.2f} K, range {min(fall['h_hys']):.2f}-"
          f"{max(fall['h_hys']):.2f} K")
    print(f"Energy corner for the winter model (VREG down to U4's threshold): off "
          f"{max(st['c_off']):+.2f} C, on {max(st['c_on']):+.2f} C; hot off {min(st['h_off']):+.2f} C, "
          f"on {min(st['h_on']):+.2f} C")
    print(f"Safety corners include NTC self-heating {NTC_SELF_HEAT_K} K and {LEAK_A * 1e9:.0f} nA of leakage "
          f"at V_T ({flt['leak_v'] * 1000:.2f} mV, {flt['leak_k'][VREG_FALLING]:.3f} K), both on the cold side "
          f"only, and a {GRADIENT_K} K NTC-to-cell gradient (all assumed).")

    print()
    print(f"Input filters: R_IN {R_IN} k and C_IN {C_IN * 1e9:.0f} nF on each V_T input, R_F1 {R_F1} k and "
          f"C_IN on U1's tap, no capacitor on U2's tap (C0G +-{C_TOL * 100:.0f} %, resistors "
          f"+-{RF_TOL * 100:.0f} %)")
    print(f"  U1: tap {flt['tau_tap1_min'] * 1e6:.1f}-{flt['tau_tap1_max'] * 1e6:.1f} us, slower than its "
          f"V_T input at any temperature ({flt['tau_t_max_any'] * 1e6:.1f} us at most): "
          f"{'yes' if flt['tau_tap1_min'] > flt['tau_t_max_any'] else 'NO'}")
    print(f"  U2: tap {flt['tau_tap2_max'] * 1e9:.0f} ns at most, faster than its V_T input at any "
          f"temperature ({flt['tau_t2_min_any'] * 1e6:.1f} us at least): "
          f"{'yes' if flt['tau_tap2_max'] < flt['tau_t2_min_any'] else 'NO'}")
    print(f"  So a rising VREG can only make OUT1 and OUT2 read 'do not charge'.")
    print(f"  Fastest VREG fall: {I_VREG_MAX_MA} mA / {C_VREG_MIN * 1e6:.0f} uF = {flt['slew']:.0f} V/s "
          f"(computed load {vreg_load_ma(VREG[2]):.2f} mA at {VREG[2]} V, {vreg_load_ma(VREG_STATIC):.2f} mA "
          f"at {VREG_STATIC:.3f} V)")
    print(f"  Error while it falls: U1 {flt['err_c_v'] * 1000:.2f} mV = {flt['err_c_k']:.3f} K, U2 "
          f"{flt['err_h_v'] * 1000:.2f} mV = {flt['err_h_k']:.3f} K at {VREG_FALLING:.3f} V (included above)")
    fall_s = (VREG[0] - VREG_FALLING) / flt["slew"]
    print(f"  VREG takes at least {fall_s * 1000:.1f} ms to fall from {VREG[0]} V to {VREG_FALLING:.3f} V; "
          f"in U4's {U4_TPHL_S * 1e6:.0f} us detect delay it falls at most "
          f"{flt['slew'] * U4_TPHL_S * 1000:.1f} mV")

    td_min = -math.log(0.36) * RCT[0] * CT[0]
    td_max = -math.log(0.26) * RCT[1] * CT[1] + 50e-6
    print()
    print(f"U4 TPS3840PL30: off below {U4_VIT[0]:.3f}-{U4_VIT[1]:.3f} V, on above "
          f"{U4_VIT[0] + U4_HYS[0]:.3f}-{U4_VIT[1] + U4_HYS[1]:.3f} V (regulated VREG >= {VREG[0]} V); "
          f"delay after a full reset {td_min:.2f}-{td_max:.2f} s with CT {CT[0] * 1e6:.1f}-"
          f"{CT[1] * 1e6:.1f} uF")

    v_lm, tol_lm, drift_lm, irmin = LM4041
    lm_lo, lm_hi = v_lm * (1 - tol_lm - drift_lm), v_lm * (1 + tol_lm + drift_lm)
    k_nom = R_OV2 / (R_OV1 + R_OV2)
    ov = ovp_trips(lm_lo, lm_hi, R_OV1, R_OV2)
    i_lm = (VREG_STATIC - lm_hi) / (R_LM * (1 + R_LM_TOL))
    i_lm_max = (VREG[2] - lm_lo) / (R_LM * (1 - R_LM_TOL))
    r1_alt = 750.0                                   # divider re-centred on the internal 1.242 V
    alt = ovp_trips(TLV_REF[0] * (1 - drift_lm), TLV_REF[2] * (1 + drift_lm), r1_alt, R_OV2)
    fl25 = float_range(*VFB_FLT[0])
    flt_t = float_range(*VFB_FLT[1])
    print()
    print(f"U3 battery overvoltage: LM4041-B {v_lm} V ({lm_lo:.4f}-{lm_hi:.4f} V), divider "
          f"{R_OV1:.0f} k / {R_OV2:.0f} k")
    print(f"  nominal: off above {(v_lm + VHYS[1] / 2) / k_nom:.3f} V, on again below "
          f"{(v_lm - VHYS[1] / 2) / k_nom:.3f} V")
    print(f"  worst case: off above {ov[0]:.3f} to {ov[1]:.3f} V, on again below {ov[2]:.3f} to "
          f"{ov[3]:.3f} V; hysteresis {ov[4] * 1000:.0f}-{ov[5] * 1000:.0f} mV at the battery")
    print(f"  LM4041 current through {R_LM} k: {i_lm * 1000:.0f} uA at VREG {VREG_STATIC:.3f} V (minimum "
          f"operating {irmin * 1000:.0f} uA), {i_lm_max * 1000:.0f} uA at {VREG[2]} V")
    print(f"  with the TLV3012B's own reference instead (divider {r1_alt:.0f} k / {R_OV2:.0f} k): "
          f"off above {alt[0]:.3f} to {alt[1]:.3f} V (not used)")
    print(f"LT3652 float: {fl25[0]:.3f}-{fl25[1]:.3f} V at 25 C, {flt_t[0]:.3f}-{flt_t[1]:.3f} V over "
          f"the chip's temperature range; BQ25170: {4.2 * 0.995:.3f}-{4.2 * 1.005:.3f} V at 25 C")
    print(f"Margin from the highest LT3652 float to the lowest U3 trip: "
          f"{(ov[0] - flt_t[1]) * 1000:.0f} mV")


if __name__ == "__main__":
    main()
