#!/usr/bin/env python3
"""Trip points of the charge interlock, with tolerances (F1 revision 5).

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

Input filters (revision 4, R4-M1): one capacitor C_T on the NTC node V_T. Each comparator input
that sees V_T is fed from it through R_IN, with no capacitor of its own. U1's tap reaches its
input through R_F1 with C_F1 to AGND; U2's tap has no capacitor. The comparators' own input
capacitance, common-mode and differential, is part of the network. filter_check() solves the
whole network as one coupled RC circuit. For one set of component values it bounds the error
between each comparator's two inputs for any history of VREG whose slope stays between -R_FALL
and +R_RISE, and any history of OUT1 (RHYS's far end), starting from rest: short dips, restarts
and charge left on the capacitors included. Over the component tolerances it searches (revision
5, R5-M1): every vertex of the independent tolerance box, then the NTC across the band, a local
ascent into the interior and random points. A search is not a proof that nothing larger exists,
so the trips carry FILTER_ALLOWANCE times the largest error found.

Every input is a datasheet value or a labelled assumption. Standard library only; the search
runs on every CPU and takes a few minutes:
  python3 -I interlock_trips.py
"""

import heapq
import itertools
import math
import multiprocessing
import random

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
# supply 1.65-5.5 V, quiescent current 3.6 uA maximum, VOH >= V+ - 0.2 V sourcing 5 mA,
# VOL <= 0.2 V sinking 5 mA. OUT1 is RHYS's far end: high is VREG less 0 to TLV_VOH_DROP, low is
# 0 to TLV_VOL (R5-M1). Its load (RHYS, one gate divider) is far below 5 mA, so the drop is
# taken as quasi-static: an offset, not a moving source.
VOS_MAX = 0.009
VHYS = (0.002, 0.006, 0.008)
TLV_VOH_DROP, TLV_VOL = 0.2, 0.2
VREG = (3.2, 3.3, 3.4)   # TPS7B6933 regulating: 3.3 V +-3 % (offsets scale with 1/VREG)

# U4: TPS3840PL30 (SNVSB03E). VIT- = 3.0 V +-1.5 %, hysteresis 75-125 mV for VIT- <= 3.0 V,
# so it releases at 3.17 V at most, below the regulated 3.2 V. Detect delay tP_HL <= 30 us,
# specified for VDD stepping to 10 % below VIT-, into 10 pF. Delay tD from CT: equations 6
# and 7, RCT 350-650 kOhm, CT 1 uF with 0.8-1.2 uF effective at 3.3 V (assumed part class).
# Push-pull output: VOL <= 0.2 V sinking 2 mA; VOH >= 0.8 VDD sourcing 2 mA, for VDD > VIT+.
U4_VIT = (3.0 * 0.985, 3.0 * 1.015)
U4_HYS = (0.075, 0.125)
U4_TPHL_S = 30e-6
U4_VOL, U4_VOH_FRAC = 0.2, 0.8
RCT = (350e3, 650e3)
CT = (0.8e-6, 1.2e-6)
VREG_STATIC = U4_VIT[0]  # lowest VREG while U4 is high and VREG steady

# Gates (R4-M1): each chain FET's gate is driven through R_G from its comparator or U4 and held
# by R_PD to AGND (1 % resistors). C_G_MAX is the largest effective gate capacitance, Miller
# charge included (F2 requirement). VGS_OFF is where the FET leakage limit is specified.
R_G, R_PD, RG_TOL = 100.0, 1000.0, 0.01   # kOhm
C_G_MAX = 100e-12
VGS_OFF = 0.3
N_GATES = 10             # gates driven from VREG, rounded up (Q1, Q2, Q4-Q10)

# VREG's slope. Rise: at most the TPS7B6933's current limit, 500 mA maximum (IOCL, specified
# with OUT shorted; that it holds at every output voltage and during start-up is an assumption
# F2 confirms with TI or F6 measures, R5-N2), into C_VREG_MIN >= 22 uF effective at 3.4 V
# (F2; the TPS7B6933 allows 2.2-100 uF; revision 4 had 10 uF, raised for R5-M1). Fall: the LDO
# doesn't sink, and its input diodes block backflow, so VREG falls no faster than its load over
# C_VREG_MIN. I_VREG_MAX_MA bounds that load, with every gate charging (vreg_load_ma below).
I_LDO_LIMIT_A, C_VREG_MIN, I_VREG_MAX_MA = 0.5, 22e-6, 1.1
R_RISE = I_LDO_LIMIT_A / C_VREG_MIN          # V/s
R_FALL = I_VREG_MAX_MA / 1000 / C_VREG_MIN   # V/s

# Input filters (C0G capacitors +-5 %, filter resistors 1 %).
R_IN, R_F1, RF_TOL = 10.0, 27.0, 0.01    # kOhm
C_T, C_F1, C_TOL = 680e-12, 330e-12, 0.05
C_T_PAR = (0.0, 50e-12)    # also on V_T: ESD diode, NTC cable, board (assumed)
C_CM = (1e-12, 10e-12)     # each comparator input to AGND: 2 pF typical [TL], plus layout (assumed)
C_DM = (0.0, 8e-12)        # between a comparator's inputs: 4 pF typical [TL], doubled (assumed)
C_NODE = (0.5e-12, 5e-12)  # U1's tap node before R_F1 (assumed)
BAND_K = 0.25            # each trip band is widened by this much for the filter error (K)
T_DECADE = 12            # grid points a decade for finding the kernels' sign changes
N_TOP = 64               # worst vertices kept for the NTC refinement and the checks beyond the band
N_NTC = 17               # NTC values across the band for those vertices
N_ASCENT = 8             # local ascents into the interior, from the worst points found
N_RANDOM = 2000          # random interior points (fixed seeds)
FILTER_ALLOWANCE = 2.0   # the trips carry this times the largest error the search finds (R5-M1)

# U3: LM4041-B (SNOS641I): 1.225 V +-0.2 % at 25 C, 100 ppm/K maximum average drift, taken over
# the same 25 +- 30 K as the resistors (board temperature while charging is possible, assumed).
# Minimum operating current 65 uA over temperature. TLV3012B's own reference: 1.223-1.260 V.
R_OV1, R_OV2 = 768.0, 301.0   # kOhm, 0.1 % E96 values
R_LM, R_LM_TOL = 20.0, 0.01   # kOhm, LM4041 bias resistor from VREG
LM4041 = (1.225, 0.002, 100e-6 * 30, 0.065)   # nominal V, initial, drift, IRMIN mA
TLV_REF = (1.223, 1.242, 1.260)
# LT3652 float: VFB(FLT) 3.282-3.318 V at 25 C, 3.26-3.34 V over temperature (datasheet p.3),
# with a 0.1 % divider for 4.2 V. BQ25170: 4.2 V +-0.5 % at Tj = 25 C (VREG_ACC).
VFB_FLT = ((3.282, 3.318), (3.26, 3.34))
# Charger stop, after the chain has opened (estimate only, not part of the trip proof): Q3's
# gate returns to VIN through 100 kOhm from the 12 V Zener clamp; Q3's input capacitance
# <= 1 nF (assumed), and it is off for the leakage argument at |VGS| <= 0.1 V.
C_Q3_MAX, VZ_Q3, VGS_Q3_OFF = 1e-9, 12.0, 0.1
# Highest source rise in a chain: ISET is rated 5.5 V absolute [BQ], so its chain carries at
# most 5.5 V / 750 Ohm through three FETs of <= 5 Ohm below the top one. The solar chain carries
# at most 32 V / 100 kOhm (VIN in its operating range) through three FETs of <= 100 Ohm.
SOURCE_RISE = max(5.5 / 750 * 3 * 5, 32 / 100e3 * 3 * 100)
VGS_RON_SPEC = 1.8       # R_on is specified at this VGS (F2 requirement)


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


def cold_trips(rs, rc1, rc2, rhys, vos, vhys, vreg, k, drift, drop=0.0, vol=0.0):
    """U1 trip temperatures (off while cooling, on while warming). OUT1 high is vreg - drop,
    OUT1 low is vol."""
    g = 1 / rc1 + 1 / rc2 + 1 / rhys
    tap_hi = (1 / rc1 + (1 - drop / vreg) / rhys) / g   # OUT1 high pulls the tap up
    tap_lo = (1 / rc1 + vol / vreg / rhys) / g          # OUT1 low pulls it down
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
        for drop, vol in itertools.product((0.0, TLV_VOH_DROP), (0.0, TLV_VOL)):
            cold.append(cold_trips(rs, RC1 * (1 + s1 * R_TOL), RC2 * (1 + s2 * R_TOL),
                                   RHYS * (1 + s3 * RHYS_TOL), sv * VOS_MAX, vh, vr, k, drift,
                                   drop, vol))
        hot.append(hot_trips(rs, RH1 * (1 + s1 * R_TOL), RH2 * (1 + s2 * R_TOL),
                             sv * VOS_MAX, vh, vr, k, drift))
    return cold, hot


def slope_per_k(temps):
    """Smallest |d(V_T / VREG) / dT| over temps (deg C) for the nominal NTC, per kelvin."""
    def one(t):
        ratio = [r_ntc(x, 1) / (RS + r_ntc(x, 1)) for x in (t - 0.05, t + 0.05)]
        return abs(ratio[1] - ratio[0]) / 0.1
    return min(one(t) for t in temps)


def cholesky(a):
    """Lower-triangular L with L L^T = a (a symmetric, positive definite)."""
    n = len(a)
    low = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = a[i][j] - sum(low[i][k] * low[j][k] for k in range(j))
            low[i][j] = math.sqrt(s) if i == j else s / low[j][j]
    return low


def lower_inverse(low):
    n = len(low)
    inv = [[0.0] * n for _ in range(n)]
    for c in range(n):
        for i in range(n):
            s = (1.0 if i == c else 0.0) - sum(low[i][k] * inv[k][c] for k in range(i))
            inv[i][c] = s / low[i][i]
    return inv


def solve(a, b):
    """x with a x = b (Gaussian elimination with partial pivoting)."""
    n = len(a)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        for r in range(c + 1, n):
            f = m[r][c] / m[c][c]
            for k in range(c, n + 1):
                m[r][k] -= f * m[c][k]
    x = [0.0] * n
    for i in reversed(range(n)):
        x[i] = (m[i][n] - sum(m[i][k] * x[k] for k in range(i + 1, n))) / m[i][i]
    return x


def jacobi(a):
    """Eigenvalues and eigenvectors (columns) of a symmetric matrix, cyclic Jacobi rotations."""
    n = len(a)
    a = [row[:] for row in a]
    v = [[float(i == j) for j in range(n)] for i in range(n)]
    for _ in range(100):
        off = sum(a[i][j] ** 2 for i in range(n) for j in range(n) if i != j)
        if off <= 1e-30 * sum(a[i][i] ** 2 for i in range(n)):
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if a[p][q] == 0.0:
                    continue
                theta = (a[q][q] - a[p][p]) / (2 * a[p][q])
                t = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1))
                c = 1 / math.sqrt(t * t + 1)
                s = t * c
                for k in range(n):
                    a[k][p], a[k][q] = c * a[k][p] - s * a[k][q], s * a[k][p] + c * a[k][q]
                for k in range(n):
                    a[p][k], a[q][k] = c * a[p][k] - s * a[q][k], s * a[p][k] + c * a[q][k]
                for k in range(n):
                    v[k][p], v[k][q] = c * v[k][p] - s * v[k][q], s * v[k][p] + c * v[k][q]
    return [a[i][i] for i in range(n)], v


def modes(caps, cond, srcs):
    """Step responses of an RC network from rest: caps is the capacitance matrix (F), cond the
    conductance matrix (S), and each src the conductances to one source. With C = L L^T the
    system y' = -A y + L^-1 src, A = L^-1 G L^-T, is symmetric. Returns the rates and, for each
    source, (amp, vss): after a unit step of that source alone, node i follows
    vss[i] + sum_k amp[i][k] exp(-rates[k] t)."""
    n = len(caps)
    low = cholesky(caps)
    li = lower_inverse(low)
    a = [[sum(li[i][p] * cond[p][q] * li[j][q] for p in range(n) for q in range(n))
          for j in range(n)] for i in range(n)]
    rates, vec = jacobi(a)
    m = [[sum(li[p][i] * vec[p][k] for p in range(n)) for k in range(n)] for i in range(n)]
    out = []
    for src in srcs:
        vss = solve(cond, src)
        y = [sum(low[p][i] * vss[p] for p in range(n)) for i in range(n)]
        w = [sum(vec[p][k] * y[p] for p in range(n)) for k in range(n)]
        out.append(([[-m[i][k] * w[k] for k in range(n)] for i in range(n)], vss))
    return rates, out


def network(p):
    """The whole input network for one set of values p (ohms, farads; ntc None = open). Nodes:
    0 V_T, 1 U1 IN- (from V_T), 2 U2 IN+ (from V_T), 3 U1's tap node, 4 U1 IN+ (after R_F1),
    5 U2 IN- (the hot tap). Two sources: VREG (through RS, RC1 and RH1) and OUT1 (through
    RHYS). Returns the rates and each source's (amp, vss), as modes() does."""
    n = 6
    cond = [[0.0] * n for _ in range(n)]
    caps = [[0.0] * n for _ in range(n)]
    src = {"vreg": [0.0] * n, "out1": [0.0] * n}

    def r(i, j, ohm):          # resistor between nodes i and j; j a source name, or -1 = AGND
        g = 1 / ohm
        cond[i][i] += g
        if j in src:
            src[j][i] += g
        elif j >= 0:
            cond[j][j] += g
            cond[i][j] -= g
            cond[j][i] -= g

    def c(i, j, farad):        # capacitor between nodes i and j; j -1 = AGND
        caps[i][i] += farad
        if j >= 0:
            caps[j][j] += farad
            caps[i][j] -= farad
            caps[j][i] -= farad

    r(0, "vreg", p["rs"])
    if p["ntc"] is not None:
        r(0, -1, p["ntc"])
    c(0, -1, p["ct"])
    r(0, 1, p["rin1"])
    r(0, 2, p["rin2"])
    r(3, "vreg", p["rc1"])
    r(3, -1, p["rc2"])
    r(3, "out1", p["rhys"])
    c(3, -1, p["cnode"])
    r(3, 4, p["rf1"])
    c(4, -1, p["cf1"])
    r(5, "vreg", p["rh1"])
    r(5, -1, p["rh2"])
    for node, key in ((1, "cm1n"), (4, "cm1p"), (2, "cm2p"), (5, "cm2n")):
        c(node, -1, p[key])
    c(1, 4, p["dm1"])
    c(2, 5, p["dm2"])
    return modes(caps, cond, (src["vreg"], src["out1"]))


def root(fn, t0, f0, t1, f1):
    """A root of fn between t0 and t1, where fn changes sign (Illinois method)."""
    side, t = 0, (t0 + t1) / 2
    for _ in range(60):
        if f1 == f0:
            return t
        t = (t0 * f1 - t1 * f0) / (f1 - f0)
        ft = fn(t)
        if ft == 0.0 or t1 - t0 <= 1e-12 * t1:
            return t
        if ft * f1 > 0:
            t1, f1 = t, ft
            if side == -1:
                f0 /= 2
            side = -1
        else:
            t0, f0 = t, ft
            if side == 1:
                f1 /= 2
            side = 1
    return t


def unsafe_error(p, comp):
    """Worst unsafe error (V) between one comparator's inputs, for one set of values p.

    Each input follows its final value plus the convolution of D(s), its step response less its
    final value, with each source's slope. The error between a comparator's inputs, beyond their
    static difference, is the convolution of Delta = D_a - D_b, where a is the input whose lead
    means "charge": U1's tap (IN+) against V_T (IN-), and V_T (U2's IN+) against U2's tap (IN-).
    OUT1 high follows VREG, so its slope is VREG's; OUT1 low is constant. So at each moment the
    kernel is Delta_H (VREG and OUT1 together) or Delta_L (VREG alone), and with the slope in
    [-R_FALL, R_RISE] the unsafe error, for any history of VREG and of OUT1's state, is at most
        integral over s of max(g(Delta_H(s)), g(Delta_L(s))),
        g(x) = R_RISE * max(x, 0) + R_FALL * max(-x, 0).
    OUT1's own switching step (at most VREG[2]) adds its step response. Within the range between
    the two states' final values, that is the hysteresis already in the static trips; any
    overshoot beyond it is the kick, added here. U2's inputs have no DC path from OUT1, so for
    U2 the whole transient is kick.

    Every kernel is a sum of exponentials, so the integral is exact between the points where a
    kernel, or the choice between them, changes sign. Those are found on a grid of T_DECADE
    points a decade and refined; check_integration() compares a dense trapezoid sum.

    Returns (total, rise part, fall part, kick, OUT1 high alone, OUT1 low alone, mean delay of
    a, mean delay of b); the mean delays (Elmore) are with OUT1 high."""
    rates, ((av, vv), (ao, vo)) = network(p)
    a, b = (4, 1) if comp == 1 else (2, 5)
    n = len(rates)
    dl = [av[a][k] - av[b][k] for k in range(n)]        # OUT1 low: VREG alone
    do = [ao[a][k] - ao[b][k] for k in range(n)]        # OUT1's own step
    dh = [x + y for x, y in zip(dl, do)]                # OUT1 high: both together
    s_inf = vo[a] - vo[b]
    s_top, s_bot = max(0.0, s_inf), min(0.0, s_inf)
    # Sign changes: Delta_H, Delta_L, and the choice between g(Delta_H) and g(Delta_L).
    sums = [dh, dl, do, [R_RISE * x + R_FALL * y for x, y in zip(dh, dl)],
            [R_RISE * y + R_FALL * x for x, y in zip(dh, dl)]]
    slope_o = [-r * c for r, c in zip(rates, do)]       # OUT1 step response's slope

    def value(c, t):
        return sum(ck * math.exp(-r * t) for ck, r in zip(c, rates))

    t_lo, t_hi = 0.01 / max(rates), 40 / min(rates)
    steps = int(math.log10(t_hi / t_lo) * T_DECADE) + 1
    grid = [0.0] + [t_lo * (t_hi / t_lo) ** (i / steps) for i in range(steps + 1)]
    # Sign changes smaller than rounding noise are skipped: they enclose no area.
    noise = [1e-12 * sum(abs(x) for x in c) for c in sums + [slope_o]]
    prev = None
    breaks, turns = [], []
    for t in grid:
        ex = [math.exp(-r * t) for r in rates]
        h = sum(c * x for c, x in zip(dh, ex))
        lo = sum(c * x for c, x in zip(dl, ex))
        cur = (h, lo, h - lo, R_RISE * h + R_FALL * lo, R_RISE * lo + R_FALL * h,
               sum(c * x for c, x in zip(slope_o, ex)))
        if prev is not None:
            for j in range(6):
                if prev[j] * cur[j] < 0 and max(abs(prev[j]), abs(cur[j])) > noise[j]:
                    c = sums[j] if j < 5 else slope_o
                    tr = root(lambda u: value(c, u), t_prev, prev[j], t, cur[j])
                    (breaks if j < 5 else turns).append(tr)
        prev, t_prev = cur, t
    # Exact integrals between the breaks.
    edges = [0.0] + sorted(breaks) + [math.inf]
    ex = [[math.exp(-r * t) if t < math.inf else 0.0 for r in rates] for t in edges]
    tot = [0.0] * 4              # combined rise, combined fall, OUT1 high alone, OUT1 low alone
    for i in range(len(edges) - 1):
        x, y = edges[i], edges[i + 1]
        if x == 0.0:
            mid = y / 2 if y < math.inf else t_lo
        else:
            mid = 2 * x if y == math.inf else math.sqrt(x * y)
        h, lo = value(dh, mid), value(dl, mid)
        wh = R_RISE if h > 0 else -R_FALL
        wl = R_RISE if lo > 0 else -R_FALL
        area = [sum(c * (e0 - e1) / r for c, e0, e1, r in zip(cv, ex[i], ex[i + 1], rates))
                for cv in (dh, dl)]
        ih, il = wh * area[0], wl * area[1]
        if wh * h >= wl * lo:
            tot[0 if h > 0 else 1] += ih
        else:
            tot[0 if lo > 0 else 1] += il
        tot[2] += ih
        tot[3] += il
    kick = 0.0
    for t in turns:
        s = s_inf + value(do, t)
        kick = max(kick, s - s_top, s_bot - s)
    kick *= VREG[2]
    delay = [-sum((av[i][k] + ao[i][k]) / rates[k] for k in range(n)) / (vv[i] + vo[i])
             for i in (a, b)]
    return (tot[0] + tot[1] + kick, tot[0], tot[1], kick, tot[2], tot[3], delay[0], delay[1])


def check_integration(p, comp, per_decade=600):
    """The total of unsafe_error() by a dense trapezoid sum over 10 ps to 1 ms instead."""
    rates, ((av, vv), (ao, vo)) = network(p)
    a, b = (4, 1) if comp == 1 else (2, 5)
    n = len(rates)
    dl = [av[a][k] - av[b][k] for k in range(n)]
    dh = [dl[k] + ao[a][k] - ao[b][k] for k in range(n)]
    total, prev, t_prev = 0.0, None, 0.0
    for t in [0.0] + [10 ** (-11 + i / per_decade) for i in range(8 * per_decade + 1)]:
        ex = [math.exp(-r * t) for r in rates]
        g = []
        for c in (dh, dl):
            x = sum(ck * e for ck, e in zip(c, ex))
            g.append(R_RISE * x if x > 0 else -R_FALL * x)
        if prev is not None:
            total += (t - t_prev) * (max(g) + prev) / 2
        prev, t_prev = max(g), t
    return total


def filter_box():
    """Each filter value's range (ohms, farads). Every value varies independently (R5-M1)."""
    lo, hi = 1 - R_TOL, 1 + R_TOL
    rf, cf = (1 - RF_TOL, 1 + RF_TOL), (1 - C_TOL, 1 + C_TOL)
    return (("rs", RS * 1e3 * lo, RS * 1e3 * hi),
            ("ct", C_T * cf[0] + C_T_PAR[0], C_T * cf[1] + C_T_PAR[1]),
            ("rin1", R_IN * 1e3 * rf[0], R_IN * 1e3 * rf[1]),
            ("rin2", R_IN * 1e3 * rf[0], R_IN * 1e3 * rf[1]),
            ("cm1n",) + C_CM, ("cm1p",) + C_CM, ("dm1",) + C_DM,
            ("rc1", RC1 * 1e3 * lo, RC1 * 1e3 * hi), ("rc2", RC2 * 1e3 * lo, RC2 * 1e3 * hi),
            ("rhys", RHYS * 1e3 * (1 - RHYS_TOL), RHYS * 1e3 * (1 + RHYS_TOL)),
            ("rf1", R_F1 * 1e3 * rf[0], R_F1 * 1e3 * rf[1]), ("cf1", C_F1 * cf[0], C_F1 * cf[1]),
            ("cnode",) + C_NODE, ("cm2p",) + C_CM, ("cm2n",) + C_CM, ("dm2",) + C_DM,
            ("rh1", RH1 * 1e3 * lo, RH1 * 1e3 * hi), ("rh2", RH2 * 1e3 * lo, RH2 * 1e3 * hi))


BOX = filter_box()
# The U1 point the fifth review exhibited (R5-M1), ohms and farads.
R5_M1_POINT = dict(rs=11979.0, ct=764e-12, ntc=32166.146873431757, rin1=10100.0, rin2=9900.0,
                   cm1n=10e-12, cm1p=10e-12, dm1=8e-12, rc1=10017.5, rc2=24257.475,
                   rhys=3353200.0, rf1=27270.0, cf1=346.5e-12, cnode=0.5e-12, cm2p=10e-12,
                   cm2n=1e-12, dm2=0.0, rh1=9982.5, rh2=4012.965)


def point(u, ntc):
    """Values at fractions u of each range (0 low end, 1 high end); ntc in ohms, None = open."""
    p = {name: lo + x * (hi - lo) for (name, lo, hi), x in zip(BOX, u)}
    p["ntc"] = ntc
    return p


def vertex(bits):
    return [bits >> j & 1 for j in range(len(BOX))]


def ntc_at(f, r_lo, r_hi):
    return r_lo * (r_hi / r_lo) ** f


def _vertex_job(job):
    """Worker: the N_TOP worst vertices of one block at one NTC value, and the mean delays."""
    comp, ntc, start, stop = job
    top, lead, lag = [], [], []
    for bits in range(start, stop):
        e = unsafe_error(point(vertex(bits), ntc), comp)
        top.append((e[0], bits))
        lead.append(e[6])
        lag.append(e[7])
    return heapq.nlargest(N_TOP, top), (min(lead), max(lead)), (min(lag), max(lag))


def _point_job(job):
    comp, u, ntc = job
    return unsafe_error(point(u, ntc), comp)


def _ascent_job(job):
    """Worker: coordinate ascent from u (and the NTC at fraction f of the band), first over a
    grid of eighths of each range, then in halving steps around the best point."""
    comp, u, f, r_lo, r_hi = job
    x = list(u) + [f]

    def ev(y):
        return unsafe_error(point(y[:-1], ntc_at(y[-1], r_lo, r_hi)), comp)[0]

    best, grid_done = ev(x), False
    for step in [None] * 4 + [1 / 16, 1 / 32, 1 / 64, 1 / 128]:
        if step is None and grid_done:
            continue
        improved = False
        for j in range(len(x)):
            values = [i / 8 for i in range(9)] if step is None else \
                [min(1.0, max(0.0, x[j] + s)) for s in (-step, step)]
            for v in values:
                y = x[:]
                y[j] = v
                e = ev(y)
                if e > best * (1 + 1e-9):
                    best, x, improved = e, y, True
        grid_done = step is None and not improved
    return best, x


def ntc_band(t_lo, t_hi):
    """NTC resistance range (kOhm) over t_lo..t_hi deg C, table spread and drift included."""
    lo = min(r_ntc(t_hi, k) for k in (0, 2)) * (1 - NTC_DRIFT)
    hi = max(r_ntc(t_lo, k) for k in (0, 2)) * (1 + NTC_DRIFT)
    return lo, hi


def filter_check(pool, c_band, h_band, f_cold, f_hot, vfl):
    """Largest error found between each comparator's inputs while VREG moves, in volts.

    unsafe_error() bounds the error for one set of values. The values are then searched, each
    independently over its own range (R5-M1):
      1. every vertex of the 18-value box (2^18) at the NTC values of the band's two ends and
         its middle;
      2. the N_TOP worst vertices at N_NTC NTC values across the band;
      3. N_ASCENT local ascents into the interior, NTC included, from the worst points so far;
      4. N_RANDOM random points of the box and band (fixed seeds).
    This is a search: it doesn't prove that nothing larger exists. So the trips carry
    FILTER_ALLOWANCE times the largest error found (err); main() checks that the shift stays
    inside BAND_K.

    The band is each trip band (c_band, h_band, deg C) widened by BAND_K. Beyond it, on the side
    where the comparator says "do not charge", the static distance from its trip must exceed
    the allowed error: checked in 5 % steps of NTC resistance over a factor of 3, and at open
    (U1) or nearly shorted (U2), for the N_TOP worst vertices; at the last of these, every
    vertex."""
    n_box = 2 ** len(BOX)
    blocks = 64
    size = n_box // blocks
    out = {}
    for comp, band, f_tap in ((1, c_band, f_cold), (2, h_band, f_hot)):
        r_lo, r_hi = (x * 1e3 for x in ntc_band(band[0] - BAND_K, band[1] + BAND_K))
        # 1. Every vertex at three NTC values.
        jobs = [(comp, ntc_at(f, r_lo, r_hi), i * size, (i + 1) * size)
                for f in (0.0, 0.5, 1.0) for i in range(blocks)]
        worst, lead, lag = {}, [], []
        for (top, ld, lg), job in zip(pool.map(_vertex_job, jobs), jobs):
            lead += ld
            lag += lg
            for e, bits in top:
                if e > worst.get(bits, (0.0,))[0]:
                    worst[bits] = (e, job[1])
        top = heapq.nlargest(N_TOP, ((e, bits) for bits, (e, _) in worst.items()))
        vertex_max = top[0][0]
        # 2. The worst vertices across the band.
        fr = [i / (N_NTC - 1) for i in range(N_NTC)]
        cand = [(bits, f) for _, bits in top for f in fr]
        res = pool.map(_point_job, [(comp, vertex(bits), ntc_at(f, r_lo, r_hi)) for bits, f in cand], 16)
        found = [(e[0], bits, f) for e, (bits, f) in zip(res, cand)]
        ntc_max = max(found)[0]
        # 3. Local ascents from the worst distinct vertices.
        starts, seen = [], set()
        for e, bits, f in sorted(found, reverse=True):
            if bits not in seen:
                seen.add(bits)
                starts.append((comp, vertex(bits), f, r_lo, r_hi))
            if len(starts) == N_ASCENT:
                break
        ascents = pool.map(_ascent_job, starts, 1)
        ascent_max, ascent_x = max(ascents)
        # 4. Random points.
        jobs = []
        for i in range(N_RANDOM):
            rng = random.Random(i)
            u = [rng.random() for _ in BOX]
            jobs.append((comp, u, ntc_at(rng.random(), r_lo, r_hi)))
        random_max = max(e[0] for e in pool.map(_point_job, jobs, 50))
        best = max(vertex_max, ntc_max, ascent_max, random_max)
        detail = _point_job((comp, ascent_x[:-1], ntc_at(ascent_x[-1], r_lo, r_hi)))
        err = FILTER_ALLOWANCE * best

        # Beyond the band: static distance from the trip, at the falling floor, against the
        # allowed error.
        outside = [r_hi * 1.05 ** k for k in range(1, 24)] + [None] if comp == 1 else \
            [r_lo * 0.95 ** k for k in range(1, 24)] + [r_lo * 0.1, r_lo * 0.03]
        jobs = [(comp, vertex(bits), ntc) for ntc in outside for _, bits in top]
        errs = [e[0] for e in pool.map(_point_job, jobs, 16)]
        far = [(comp, outside[-1], i * size, (i + 1) * size) for i in range(blocks)]
        far_max = max(t[0][0][0] for t in pool.map(_vertex_job, far))
        least, ratio = None, None
        for i, ntc in enumerate(outside):
            e = max(errs[i * len(top):(i + 1) * len(top)])
            if i == len(outside) - 1:
                e = max(e, far_max)
            if comp == 1:
                f_t = 1.0 if ntc is None else ntc / (RS * 1e3 * (1 + R_TOL) + ntc)
                dist = (f_t - f_tap) * vfl
            else:
                f_t = ntc / (RS * 1e3 * (1 - R_TOL) + ntc)
                dist = (f_tap - f_t) * vfl
            dist -= VOS_MAX + VHYS[2] / 2
            margin = dist - FILTER_ALLOWANCE * e
            least = margin if least is None else min(least, margin)
            ratio = dist / e if ratio is None else min(ratio, dist / e)
        out[comp] = dict(err=err, best=best, vertex=vertex_max, ntc=ntc_max, ascent=ascent_max,
                         random=random_max, detail=detail, x=ascent_x, n=3 * n_box,
                         band=(r_lo / 1e3, r_hi / 1e3), lead=(min(lead), max(lead)),
                         lag=(min(lag), max(lag)), least=least, ratio=ratio, far=far_max)
    return out


def rev3_check():
    """Revision 3's filters solved as one network at 0 C, nominal NTC (R4-M1): two 10 kOhm /
    1 nF branches on V_T, and U1's tap through 20 kOhm into 1 nF. Returns the slowest time
    constants (s) of the V_T inputs and of the tap."""
    tiny = 1e-15                                      # V_T and the tap node had no capacitor
    cond = [[0.0] * 3 for _ in range(3)]
    rth_ntc = r_ntc(0, 1) * 1e3
    g_s, g_n, g_i = 1 / (RS * 1e3), 1 / rth_ntc, 1 / (R_IN * 1e3)
    cond[0][0] = g_s + g_n + 2 * g_i
    for k in (1, 2):
        cond[k][k] = g_i
        cond[0][k] = cond[k][0] = -g_i
    caps = [[tiny, 0, 0], [0, 1e-9, 0], [0, 0, 1e-9]]
    rates, _ = modes(caps, cond, [[g_s, 0, 0]])
    th = par(par(RC1, RC2), RHYS) * 1e3
    tap = (20e3 + th) * 1e-9
    return 1 / min(rates), tap


def inhibit_latency():
    """From VREG reaching 10 % below U4's lowest threshold to Q9 / Q10 off: U4's tP_HL, then the
    gate falling through R_G || R_PD from its highest level to VGS_OFF, U4's output at VOL."""
    k_hi = R_PD * (1 + RG_TOL) / (R_PD * (1 + RG_TOL) + R_G * (1 - RG_TOL))
    r_par = par(R_G * (1 + RG_TOL), R_PD * (1 + RG_TOL)) * 1e3
    v_start, v_end = VREG[2] * k_hi, U4_VOL * k_hi
    t_gate = r_par * C_G_MAX * math.log((v_start - v_end) / (VGS_OFF - v_end))
    return U4_TPHL_S, t_gate


def v_floor():
    """Lowest VREG at which a chain can still be closed: 10 % below U4's lowest threshold, less
    the fastest fall during the inhibit latency."""
    tp, tg = inhibit_latency()
    return 0.9 * U4_VIT[0] - R_FALL * (tp + tg)


def vreg_load_ma(vreg, gates_charging=False):
    """VREG load in mA at vreg: dividers at their highest current, LM4041, comparators, U4,
    and the gates: held by R_G + R_PD, or (gates_charging) each drawing vreg / R_G, the most
    it can while charging from 0 V."""
    r_ntc_min = 2.0                                  # NTC at about +66 C, a hot board (assumed)
    i = vreg / (RS * (1 - R_TOL) + r_ntc_min)
    i += vreg / ((RC1 + RC2) * (1 - R_TOL)) + vreg / ((RH1 + RH2) * (1 - R_TOL))
    i += (vreg - LM4041[0] * (1 - LM4041[1] - LM4041[2])) / (R_LM * (1 - R_LM_TOL))
    i += 3 * 0.0036 + 0.0007
    if gates_charging:
        i += N_GATES * vreg / (R_G * (1 - RG_TOL))
    else:
        i += N_GATES * vreg / ((R_G + R_PD) * (1 - RG_TOL))
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
    vfl = v_floor()
    nom_c = cold_trips(RS, RC1, RC2, RHYS, 0.0, VHYS[1], VREG[1], 1, 0.0)
    nom_h = hot_trips(RS, RH1, RH2, 0.0, VHYS[1], VREG[1], 1, 0.0)
    bands = (("regulated", VREG[0]), ("U4 static", VREG_STATIC), ("floor", vfl))
    res = {}
    for name, lo in bands:
        cold, hot = corners(lo, VREG[2])
        res[name] = dict(c_off=[c[0] for c in cold], c_on=[c[1] for c in cold],
                         c_hys=[c[1] - c[0] for c in cold], h_off=[h[0] for h in hot],
                         h_on=[h[1] for h in hot], h_hys=[h[0] - h[1] for h in hot])
    reg = res["regulated"]
    st = res["U4 static"]
    fall = res["floor"]
    c_trip = (min(fall["c_off"]), max(fall["c_on"]))
    h_trip = (min(fall["h_on"]), max(fall["h_off"]))

    # The fraction of VREG at each comparator's inputs near its trip, highest corner.
    f_cold = RC2 * (1 + R_TOL) / (RC2 * (1 + R_TOL) + par(RC1 * (1 - R_TOL), RHYS * (1 - RHYS_TOL)))
    f_hot = RH2 * (1 + R_TOL) / (RH2 * (1 + R_TOL) + RH1 * (1 - R_TOL))
    with multiprocessing.Pool() as pool:
        flt = filter_check(pool, c_trip, h_trip, f_cold, f_hot, vfl)
    err_c_k = flt[1]["err"] / (vfl * slope_per_k(c_trip))
    err_h_k = flt[2]["err"] / (vfl * slope_per_k(h_trip))
    th_c = [par(RS, r_ntc(t, k) * (1 + d)) for t in c_trip for k in (0, 2)
            for d in (-NTC_DRIFT, NTC_DRIFT)]
    leak_v = LEAK_A * max(th_c) * 1e3
    leak_k = {v: leak_v / (v * slope_per_k(c_trip)) for v in (VREG_STATIC, vfl)}

    # NTC self-heating at the cold trip: P = I^2 R, divided by 2 mW/K (still air, datasheet).
    r1 = r_ntc(nom_c[0], 1)
    i_ma = 3.4 / (RS + r1)
    p_mw = i_ma ** 2 * r1
    print(f"Resistors: RS {RS} k, RC1 {RC1} k, RC2 {RC2} k, RHYS {RHYS / 1000:.2f} M, "
          f"RH1 {RH1} k, RH2 {RH2} k; tolerance +-{R_TOL * 100:.3f} % (RHYS +-{RHYS_TOL * 100:.0f} %)")
    print(f"NTC current at the cold trip: {i_ma * 1000:.0f} uA, {p_mw:.3f} mW -> "
          f"self-heating {p_mw / 2:.3f} K in still air (allowance {NTC_SELF_HEAT_K} K)")
    print()
    tp, tg = inhibit_latency()
    print(f"VREG bands: regulated {VREG[0]}-{VREG[2]} V; U4 static {VREG_STATIC:.3f}-{VREG[2]} V "
          f"(lowest VIT-); falling floor {vfl:.4f}-{VREG[2]} V")
    print(f"  Floor: 10 % below the lowest VIT- ({0.9 * U4_VIT[0]:.4f} V), less {R_FALL:.0f} V/s for "
          f"U4's {tp * 1e6:.0f} us detect delay and {tg * 1e6:.1f} us for Q9 / Q10's gate to fall "
          f"to {VGS_OFF} V")
    print()
    print("| Trip | Nominal, deg C | Electrical worst case, VREG regulated | VREG down to U4's threshold "
          "| Safety corner, VREG at the falling floor, plus the filter error |")
    print("|---|---|---|---|---|")
    sc_c = NTC_SELF_HEAT_K + GRADIENT_K + leak_k[vfl]
    sc_s = NTC_SELF_HEAT_K + GRADIENT_K + leak_k[VREG_STATIC]
    print(f"| Cold off (cooling) | {nom_c[0]:+.2f} | {min(reg['c_off']):+.2f} to {max(reg['c_off']):+.2f} | "
          f"{min(st['c_off']):+.2f} to {max(st['c_off']):+.2f} | "
          f"{min(fall['c_off']) - sc_c - err_c_k:+.2f} (must be >= 0) |")
    print(f"| Cold on (warming) | {nom_c[1]:+.2f} | {min(reg['c_on']):+.2f} to {max(reg['c_on']):+.2f} | "
          f"{min(st['c_on']):+.2f} to {max(st['c_on']):+.2f} | "
          f"{min(fall['c_on']) - sc_c - err_c_k:+.2f} |")
    print(f"| Hot off (heating) | {nom_h[0]:+.2f} | {min(reg['h_off']):+.2f} to {max(reg['h_off']):+.2f} | "
          f"{min(st['h_off']):+.2f} to {max(st['h_off']):+.2f} | "
          f"{max(fall['h_off']) + GRADIENT_K + err_h_k:+.2f} (must be <= 45) |")
    print(f"| Hot on (cooling) | {nom_h[1]:+.2f} | {min(reg['h_on']):+.2f} to {max(reg['h_on']):+.2f} | "
          f"{min(st['h_on']):+.2f} to {max(st['h_on']):+.2f} | "
          f"{max(fall['h_on']) + GRADIENT_K + err_h_k:+.2f} |")
    print()
    print(f"Unrounded safety corners: cold off {min(fall['c_off']) - sc_c - err_c_k:+.4f} C, hot off "
          f"{max(fall['h_off']) + GRADIENT_K + err_h_k:+.4f} C")
    print(f"Safety corners at VREG {VREG_STATIC:.3f} V without the filter error: cold off "
          f"{min(st['c_off']) - sc_s:+.2f} C, hot off {max(st['h_off']) + GRADIENT_K:+.2f} C")
    print(f"Cold hysteresis: nominal {nom_c[1] - nom_c[0]:.2f} K, range {min(fall['c_hys']):.2f}-"
          f"{max(fall['c_hys']):.2f} K")
    print(f"Hot hysteresis: nominal {nom_h[0] - nom_h[1]:.2f} K, range {min(fall['h_hys']):.2f}-"
          f"{max(fall['h_hys']):.2f} K")
    print(f"Energy corner for the winter model (VREG down to U4's threshold): off "
          f"{max(st['c_off']):+.2f} C, on {max(st['c_on']):+.2f} C; hot off {min(st['h_off']):+.2f} C, "
          f"on {min(st['h_on']):+.2f} C")
    print(f"Safety corners include NTC self-heating {NTC_SELF_HEAT_K} K and {LEAK_A * 1e9:.0f} nA of leakage "
          f"at V_T ({leak_v * 1000:.2f} mV, {leak_k[vfl]:.3f} K), both on the cold side "
          f"only, and a {GRADIENT_K} K NTC-to-cell gradient (all assumed).")

    print()
    print(f"Input filters: C_T {C_T * 1e12:.0f} pF on V_T (plus {C_T_PAR[1] * 1e12:.0f} pF at most of "
          f"ESD diode, cable and board); R_IN {R_IN} k into each comparator input, no capacitor; "
          f"R_F1 {R_F1} k and C_F1 {C_F1 * 1e12:.0f} pF on U1's tap; none on U2's tap (C0G "
          f"+-{C_TOL * 100:.0f} %, resistors +-{RF_TOL * 100:.0f} %)")
    print(f"  Comparator inputs: {C_CM[0] * 1e12:.0f}-{C_CM[1] * 1e12:.0f} pF to AGND each, "
          f"{C_DM[0] * 1e12:.0f}-{C_DM[1] * 1e12:.0f} pF between the two; U1's tap node "
          f"{C_NODE[0] * 1e12:.1f}-{C_NODE[1] * 1e12:.0f} pF (assumed)")
    print(f"  VREG slope: rise <= {I_LDO_LIMIT_A * 1000:.0f} mA / {C_VREG_MIN * 1e6:.0f} uF = "
          f"{R_RISE / 1000:.1f} V/ms; fall <= {I_VREG_MAX_MA} mA / {C_VREG_MIN * 1e6:.0f} uF = "
          f"{R_FALL:.0f} V/s (load {vreg_load_ma(VREG[2], True):.3f} mA at {VREG[2]} V with every gate "
          f"charging, {vreg_load_ma(VREG[2]):.3f} mA steady)")
    print(f"  Solved as one coupled network, for any VREG history inside those slopes and either "
          f"OUT1 state at every moment (RHYS to VREG or to AGND), plus OUT1's switching kick")
    for comp, name, k, lead, lag in ((1, "U1", err_c_k, "IN+ (tap)", "IN- (V_T)"),
                                     (2, "U2", err_h_k, "IN+ (V_T)", "IN- (tap)")):
        f = flt[comp]
        w = f["detail"]
        print(f"  {name}: NTC {f['band'][0]:.2f}-{f['band'][1]:.2f} k (trip band +-{BAND_K} K). Searched, "
              f"every value independent: all {2 ** len(BOX)} vertices at 3 NTC values ({f['n']}), the "
              f"{N_TOP} worst at {N_NTC} NTC values, {N_ASCENT} local ascents, {N_RANDOM} random points")
        print(f"    largest error found {f['best'] * 1000:.4f} mV: vertices {f['vertex'] * 1000:.4f}, "
              f"across the band {f['ntc'] * 1000:.4f}, ascents {f['ascent'] * 1000:.4f}, random "
              f"{f['random'] * 1000:.4f} mV")
        print(f"    at the ascents' best point: rise term {w[1] * 1000:.4f}, fall term {w[2] * 1000:.4f}, "
              f"kick {w[3] * 1000:.4f} mV; OUT1 high alone {w[4] * 1000:.4f}, OUT1 low alone "
              f"{w[5] * 1000:.4f} mV")
        ends = [(n, x) for (n, _, _), x in zip(BOX, f["x"])]
        print(f"    there: high end {', '.join(n for n, x in ends if x == 1) or '-'}; low end "
              f"{', '.join(n for n, x in ends if x == 0) or '-'}; inside "
              f"{', '.join(f'{n} {x:.3f}' for n, x in ends if 0 < x < 1) or '-'}; NTC at "
              f"{f['x'][-1]:.3f} of the band")
        print(f"    in the trips: {FILTER_ALLOWANCE:.0f} x {f['best'] * 1000:.4f} = {f['err'] * 1000:.4f} mV "
              f"= {k:.4f} K at {vfl:.3f} V. Mean delays {lead} {f['lead'][0] * 1e6:.3f}-"
              f"{f['lead'][1] * 1e6:.3f} us, {lag} {f['lag'][0] * 1e6:.3f}-{f['lag'][1] * 1e6:.3f} us")
        print(f"    Beyond the band, toward {'open' if comp == 1 else 'short'}: static distance exceeds "
              f"the allowed error by >= {f['least'] * 1000:.0f} mV, and is >= {f['ratio']:.0f} times the "
              f"error found (every vertex at the far end: {f['far'] * 1000:.3f} mV)")
        print(f"    Integration check at that point: exact {w[0] * 1000:.5f} mV less kick "
              f"{(w[0] - w[3]) * 1000:.5f} mV, trapezoid at 600 points a decade "
              f"{check_integration(point(f['x'][:-1], ntc_at(f['x'][-1], *[x * 1e3 for x in f['band']])), comp) * 1000:.5f} mV")
    e = unsafe_error(R5_M1_POINT, 1)
    print(f"  R5-M1's U1 point (ntc {R5_M1_POINT['ntc']:.0f} ohm): OUT1 high alone {e[4] * 1000:.4f} mV, "
          f"either state {e[0] * 1000:.4f} mV. With revision 4's 10 uF (both slopes x "
          f"{C_VREG_MIN / 10e-6:.1f}; no kick here) OUT1 high alone is {e[4] * C_VREG_MIN / 10e-6 * 1000:.4f} mV: "
          f"the review got 0.904692 at 60 points a decade, 0.904403 at 600")
    old_t, old_tap = rev3_check()
    print(f"  Check, revision 3 solved as one network at 0 C (nominal NTC): V_T inputs' slowest time "
          f"constant {old_t * 1e6:.3f} us against U1's tap {old_tap * 1e6:.3f} us, so its ordering "
          f"claim failed (R4-M1)")

    td_min = -math.log(0.36) * RCT[0] * CT[0]
    td_max = -math.log(0.26) * RCT[1] * CT[1] + 50e-6
    k_lo = R_PD * (1 - RG_TOL) / (R_PD * (1 - RG_TOL) + R_G * (1 + RG_TOL))
    t_q3 = 100e3 * C_Q3_MAX * math.log(VZ_Q3 / VGS_Q3_OFF)
    print()
    print(f"U4 TPS3840PL30: off below {U4_VIT[0]:.3f}-{U4_VIT[1]:.3f} V, on above "
          f"{U4_VIT[0] + U4_HYS[0]:.3f}-{U4_VIT[1] + U4_HYS[1]:.3f} V (regulated VREG >= {VREG[0]} V); "
          f"delay after a full reset {td_min:.2f}-{td_max:.2f} s with CT {CT[0] * 1e6:.1f}-"
          f"{CT[1] * 1e6:.1f} uF")
    print(f"  Inhibit latency: {tp * 1e6:.0f} us detect + {tg * 1e6:.1f} us gate ({R_G:.0f} k || "
          f"{R_PD:.0f} k, {C_G_MAX * 1e12:.0f} pF at most) = {(tp + tg) * 1e6:.1f} us, VREG falling at "
          f"most {R_FALL * (tp + tg) * 1000:.1f} mV meanwhile")
    print(f"  Then, not part of the trip proof: Q3 off (|VGS| <= {VGS_Q3_OFF} V) within "
          f"{t_q3 * 1e6:.0f} us with <= {C_Q3_MAX * 1e9:.0f} nF, plus each charger's own response")
    print(f"Gate drive through {R_G:.0f} k / {R_PD:.0f} k (factor >= {k_lo:.4f}), from guaranteed VOH:")
    for name, v in (("regulated VREG", VREG[0]), ("VREG at U4's threshold", VREG_STATIC)):
        print(f"  {name} {v} V: U4 >= {U4_VOH_FRAC * v * k_lo:.3f} V, comparators >= "
              f"{(v - TLV_VOH_DROP) * k_lo:.3f} V; less a source rise of <= {SOURCE_RISE * 1000:.0f} mV, "
              f"the weakest VGS is {U4_VOH_FRAC * v * k_lo - SOURCE_RISE:.3f} V (R_on specified at "
              f"{VGS_RON_SPEC} V)")
    print("  (U4's VOH is specified for VDD above VIT+; at VREG 2.955 V it is taken to scale the same way)")

    v_lm, tol_lm, drift_lm, irmin = LM4041
    lm_lo, lm_hi = v_lm * (1 - tol_lm - drift_lm), v_lm * (1 + tol_lm + drift_lm)
    k_nom = R_OV2 / (R_OV1 + R_OV2)
    ov = ovp_trips(lm_lo, lm_hi, R_OV1, R_OV2)
    i_lm = (vfl - lm_hi) / (R_LM * (1 + R_LM_TOL))
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
    print(f"  LM4041 current through {R_LM} k: {i_lm * 1000:.1f} uA at the falling floor {vfl:.3f} V "
          f"(minimum operating {irmin * 1000:.0f} uA), {i_lm_max * 1000:.0f} uA at {VREG[2]} V")
    print(f"  with the TLV3012B's own reference instead (divider {r1_alt:.0f} k / {R_OV2:.0f} k): "
          f"off above {alt[0]:.3f} to {alt[1]:.3f} V (not used)")
    print(f"LT3652 float: {fl25[0]:.3f}-{fl25[1]:.3f} V at 25 C, {flt_t[0]:.3f}-{flt_t[1]:.3f} V over "
          f"the chip's temperature range; BQ25170: {4.2 * 0.995:.3f}-{4.2 * 1.005:.3f} V at 25 C")
    print(f"Margin from the highest LT3652 float to the lowest U3 trip: "
          f"{(ov[0] - flt_t[1]) * 1000:.0f} mV")
    assert vreg_load_ma(VREG[2], True) <= I_VREG_MAX_MA
    assert max(err_c_k, err_h_k) < BAND_K and flt[1]["least"] > 0 and flt[2]["least"] > 0
    assert min(fall["c_off"]) - sc_c - err_c_k >= 0 and max(fall["h_off"]) + GRADIENT_K + err_h_k <= 45


if __name__ == "__main__":
    main()
