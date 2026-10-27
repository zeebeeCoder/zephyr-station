#!/usr/bin/env python3
"""Trip points of the charge interlock, with tolerances (F1 revision 6).

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
input through R_F1 with C_F1 to AGND; U2's tap has C_HOT (revision 6). The comparators' own
input capacitance, common-mode and differential, is part of the network. filter_bound() bounds
the error between each comparator's two inputs for any history of VREG whose slope stays between
-R_FALL and +R_RISE, and any history of OUT1, starting from rest: short dips, restarts and
charge left on the capacitors included. Revision 5 searched the tolerance box and doubled the
largest error found; revision 6 (R6-M1) replaces that with an interval envelope over the whole
box and NTC band (Mueller's comparison theorem), so the bound covers every value in the box.
Exact responses at sample points check it (env_check).

Every input is a datasheet value or a labelled assumption. Standard library only; the bound
runs on every CPU and takes about 20 minutes:
  python3 -I interlock_trips.py
"""

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
C_HOT = 100e-12          # U2's IN- (the hot tap) to AGND, C0G (revision 6, R6-M1): it keeps the
                         # comparator's differential capacitance small against that node's own
BAND_K = 0.5             # each trip band is widened by this much, more than either filter bound (K)
ENV_DECADE = 40          # envelope output points a decade in the trip bands (checked at twice this)
ENV_DECADE_BEYOND = 20   # the same beyond the bands, where the margins are large
ENV_T = (1e-13, 50e-3)   # envelope grid, s: every bound has settled to its final value by the end
ENV_H_MIN = 1e-3         # smallest sub-step, as a fraction of a grid step
ENV_BEYOND = {1: (1.0, 1.2, 1.5, 2.5, None),   # NTC pieces beyond the band, as factors of its
              2: (1.0, 0.8, 0.6, 0.3, 0.03)}   # colder end (U1, None = open) or hotter end (U2)
ENV_POINTS = 64          # validation points per comparator (fixed seeds)
# Upper rail (R6-N2): VREG never above V_TOP, start-up included. The TPS7B6933 regulates to
# 3.4 V at most for 1-150 mA (this load is about 1 mA, so F2 confirms it with TI or enforces it;
# F6 measures start-up). The NTC's self-heating, OUT1's switching excess and the gate drive
# use it.
V_TOP = VREG[2]

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
    """Smallest |d(V_T / VREG) / dT| per kelvin over temps[0]..temps[1] (deg C) widened by
    BAND_K, every 0.1 K, for every NTC corner (table spread and drift) and RS's tolerance. It
    converts the filter bound and the leakage to kelvin (R6-M1)."""
    t0, t1 = min(temps) - BAND_K, max(temps) + BAND_K
    n = int(math.ceil((t1 - t0) / 0.1))

    def one(t, k, d, rs):
        ratio = [r_ntc(x, k) * (1 + d) / (rs + r_ntc(x, k) * (1 + d)) for x in (t - 0.05, t + 0.05)]
        return abs(ratio[1] - ratio[0]) / 0.1
    return min(one(t0 + i * (t1 - t0) / n, k, d, rs) for i in range(n + 1) for k in (0, 1, 2)
               for d in (-NTC_DRIFT, NTC_DRIFT) for rs in (RS * (1 - R_TOL), RS * (1 + R_TOL)))


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
    5 U2 IN- (the hot tap). Every resistor to VREG, OUT1 or AGND is in the diagonal of the
    conductance matrix. Returns the capacitance and conductance matrices."""
    n = 6
    cond = [[0.0] * n for _ in range(n)]
    caps = [[0.0] * n for _ in range(n)]

    def r(i, j, ohm):          # resistor between nodes i and j; j "vreg", "out1" or -1 = AGND
        g = 1 / ohm
        cond[i][i] += g
        if isinstance(j, int) and j >= 0:
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
    for node, key in ((1, "cm1n"), (4, "cm1p"), (2, "cm2p"), (5, "cm2n"), (5, "chot")):
        c(node, -1, p[key])
    c(1, 4, p["dm1"])
    c(2, 5, p["dm2"])
    return caps, cond


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
            ("rh1", RH1 * 1e3 * lo, RH1 * 1e3 * hi), ("rh2", RH2 * 1e3 * lo, RH2 * 1e3 * hi),
            ("chot", C_HOT * cf[0], C_HOT * cf[1]))


BOX = filter_box()
# The U1 point the fifth review exhibited (R5-M1), ohms and farads, with revision 6's C_HOT.
R5_M1_POINT = dict(rs=11979.0, ct=764e-12, ntc=32166.146873431757, rin1=10100.0, rin2=9900.0,
                   cm1n=10e-12, cm1p=10e-12, dm1=8e-12, rc1=10017.5, rc2=24257.475,
                   rhys=3353200.0, rf1=27270.0, cf1=346.5e-12, cnode=0.5e-12, cm2p=10e-12,
                   cm2n=1e-12, dm2=0.0, rh1=9982.5, rh2=4012.965, chot=100e-12)


def point(u, ntc):
    """Values at fractions u of each range (0 low end, 1 high end); ntc in ohms, None = open."""
    p = {name: lo + x * (hi - lo) for (name, lo, hi), x in zip(BOX, u)}
    p["ntc"] = ntc
    return p


def ntc_band(t_lo, t_hi):
    """NTC resistance range (kOhm) over t_lo..t_hi deg C, table spread and drift included."""
    lo = min(r_ntc(t_hi, k) for k in (0, 2)) * (1 - NTC_DRIFT)
    hi = max(r_ntc(t_lo, k) for k in (0, 2)) * (1 + NTC_DRIFT)
    return lo, hi


# Interval envelope (revision 6, R6-M1). Each node's Thevenin source is a fixed fraction of VREG
# (or OUT1): E0 = K0 VREG at V_T (RS and the NTC), E3 = K3L VREG + cO OUT1 at U1's tap node (RC1,
# RC2, RHYS), E5 = K5 VREG at U2's tap (RH1, RH2). x_i^j is node i's response to a unit step of
# E_j from rest. Nodes as in network(). Between each comparator's inputs:
#   U1: IN+ - IN- = (K3 - K0) W1 + Delta1 * dVREG,   W1 = x_1^0 * dVREG,
#       Delta1 = K3 (x_4^3 - x_1^0) + K0 x_4^0 + K5 x_4^5 - K3 x_1^3 - K5 x_1^5,
#   U2: IN+ - IN- = (K0 - K5) W2 + Delta2 * dVREG,   W2 = x_2^0 * dVREG,
#       Delta2 = K5 (x_2^0 - x_5^5) + K3 x_2^3 + K5 x_2^5 - K0 x_5^0 - K3 x_5^3,
# where * is convolution with VREG's slope and K3 is K3H with OUT1 following VREG. W is VREG
# lagged by the input's own filter: the static trips are taken at W, and Delta settles to zero,
# so for any VREG slope history in [-R_FALL, R_RISE] its part is at most
#   R_RISE * integral of max(Delta, 0) + R_FALL * integral of max(-Delta, 0).
# OUT1 at any moment is theta VREG, 0 <= theta <= 1 (high: VREG less its drop; low: VOL). Its
# part of E3 is cO h' * (theta VREG), h = x_a^3 - x_b^3 (a, b the comparator's inputs). Split h'
# into its positive and negative parts: that is at most the OUT1-high kernel (K3 = K3H, in Delta)
# plus cO V_TOP integral of max(-h', 0), which any switching sequence can add (R6-M1). h' is the
# difference of the two inputs' node equations, evaluated over the E3 step's bounds:
#   U1: h' = C4/det1/R_IN1 y1 + C1/det1/R_F1 (x3 - x4),  U2: h' = -C5/det2/R_IN2 y2 + C2/det2 G5 x5.
#
# The node equations, written in V_T (x0), the input currents' coordinates y1 = x1 - x0 and
# y2 = x2 - x0, and nodes 3, 4, 5, are sums of products of coefficients, each a range over the
# box (env_coefs), and differences of states. For each state's upper bound, the largest
# right-hand side with that state at its upper bound and every other state anywhere between its
# bounds gives one equation; likewise each lower bound. By Mueller's comparison theorem this
# 12-state system bounds every trajectory of every set of values in the box (each value varying
# independently, even in time). It is solved exactly for the current choice of extreme
# coefficients and bounds (a linear system: matrix exponential), halving the step wherever the
# choice changes; at ENV_H_MIN of a grid step the choice is kept and the bounds are widened by the
# step times the gap between the kept and the true extreme at the step's end. Integrals take the
# larger of each grid step's two ends; ENV_DECADE points a decade, checked at twice that.
ENV_RUNS = (("E0", None), ("E3", None), ("E5", None))


def env_coefs(g_lo, g_hi):
    """Range of each coefficient over the box, NTC conductance g_lo..g_hi (0 = open). Each is
    monotone in each value it depends on, so its range is at the vertices (env_check tests
    interior points)."""
    r = {name: (lo, hi) for name, lo, hi in BOX}
    r["g"] = (g_lo, g_hi)
    r["c4"] = (r["cf1"][0] + r["cm1p"][0], r["cf1"][1] + r["cm1p"][1])
    r["c5"] = (r["cm2n"][0] + r["chot"][0], r["cm2n"][1] + r["chot"][1])
    return {name: _coef_range(r, fn, names) for name, (fn, names) in ENV_COEFS.items()}


def _coef_range(r, fn, names):
    vals = [fn(*v) for v in itertools.product(*(r[n] for n in names))]
    return min(vals), max(vals)


def _det(c, d, cc):
    """Determinant of two nodes' capacitance matrix: c and cc to AGND, d between them."""
    return c * cc + d * (c + cc)


# Nodes 1 and 4 (and 2 and 5) are coupled by the comparator's differential capacitance, so each
# node's slope is a mix of both nodes' currents: the inverse of their capacitance matrix.
ENV_COEFS = {
    "a1g1": (lambda c, d, cc, r: (cc + d) / _det(c, d, cc) / r, ("cm1n", "dm1", "c4", "rin1")),
    "b1g4": (lambda c, d, cc, r: d / _det(c, d, cc) / r, ("cm1n", "dm1", "c4", "rf1")),
    "b1g1": (lambda c, d, cc, r: d / _det(c, d, cc) / r, ("cm1n", "dm1", "c4", "rin1")),
    "c1g4": (lambda c, d, cc, r: (c + d) / _det(c, d, cc) / r, ("cm1n", "dm1", "c4", "rf1")),
    "a2g2": (lambda c, d, cc, r: (cc + d) / _det(c, d, cc) / r, ("cm2p", "dm2", "c5", "rin2")),
    "b2g5": (lambda c, d, cc, r1, r2: d / _det(c, d, cc) * (1 / r1 + 1 / r2),
             ("cm2p", "dm2", "c5", "rh1", "rh2")),
    "b2g2": (lambda c, d, cc, r: d / _det(c, d, cc) / r, ("cm2p", "dm2", "c5", "rin2")),
    "c2g5": (lambda c, d, cc, r1, r2: (c + d) / _det(c, d, cc) * (1 / r1 + 1 / r2),
             ("cm2p", "dm2", "c5", "rh1", "rh2")),
    "iC0": (lambda ct: 1 / ct, ("ct",)),
    "ic3": (lambda cn: 1 / cn, ("cnode",)),
    "gth0": (lambda rs, g: 1 / rs + g, ("rs", "g")),
    "g1": (lambda r: 1 / r, ("rin1",)),
    "g2": (lambda r: 1 / r, ("rin2",)),
    "g4": (lambda r: 1 / r, ("rf1",)),
    "gth3": (lambda r1, r2, rh: 1 / r1 + 1 / r2 + 1 / rh, ("rc1", "rc2", "rhys")),
    "one": (lambda: 1.0, ()),
    "K0": (lambda rs, g: 1 / (1 + rs * g), ("rs", "g")),
    "K3L": (lambda r1, r2, rh: 1 / r1 / (1 / r1 + 1 / r2 + 1 / rh), ("rc1", "rc2", "rhys")),
    "K3H": (lambda r1, r2, rh: (1 / r1 + 1 / rh) / (1 / r1 + 1 / r2 + 1 / rh), ("rc1", "rc2", "rhys")),
    "cO": (lambda r1, r2, rh: 1 / rh / (1 / r1 + 1 / r2 + 1 / rh), ("rc1", "rc2", "rhys")),
    "K5": (lambda r1, r2: r2 / (r1 + r2), ("rh1", "rh2")),
    "e1": (lambda c, d, cc, r: cc / _det(c, d, cc) / r, ("cm1n", "dm1", "c4", "rin1")),
    "e2": (lambda c, d, cc, r: c / _det(c, d, cc) / r, ("cm1n", "dm1", "c4", "rf1")),
    "e3": (lambda c, d, cc, r: cc / _det(c, d, cc) / r, ("cm2p", "dm2", "c5", "rin2")),
    "e4": (lambda c, d, cc, r1, r2: c / _det(c, d, cc) * (1 / r1 + 1 / r2),
           ("cm2p", "dm2", "c5", "rh1", "rh2")),
}

# Right-hand side of each state: groups (sign, factor, terms), each term (sign, coefficient,
# linear form over the states 0-5 and the sources).
_NODE0 = [(+1, "gth0", {"E0": 1, 0: -1}), (+1, "g1", {1: 1}), (+1, "g2", {2: 1})]
ENV_RHS = {
    0: [(+1, "iC0", _NODE0)],
    1: [(+1, "one", [(-1, "a1g1", {1: 1}), (+1, "b1g4", {3: 1, 4: -1})]), (-1, "iC0", _NODE0)],
    2: [(+1, "one", [(-1, "a2g2", {2: 1}), (+1, "b2g5", {"E5": 1, 5: -1})]), (-1, "iC0", _NODE0)],
    3: [(+1, "ic3", [(+1, "gth3", {"E3": 1, 3: -1}), (-1, "g4", {3: 1, 4: -1})])],
    4: [(+1, "one", [(-1, "b1g1", {1: 1}), (+1, "c1g4", {3: 1, 4: -1})])],
    5: [(+1, "one", [(-1, "b2g2", {2: 1}), (+1, "c2g5", {"E5": 1, 5: -1})])],
}
ENV_ORDER = [(False, i) for i in range(6)] + [(True, i) for i in range(6)]


def _form_extreme(i, own_up, form, want_max, z, e):
    """Largest (or smallest) value of a linear form, state i at its own upper (or lower) bound,
    the others anywhere between theirs. Returns it and the bounds used: {(state, upper): coef}."""
    v, used = 0.0, {}
    for k, a in form.items():
        if isinstance(k, str):
            v += a * e[k]
            continue
        up = own_up if k == i else (a > 0) == want_max
        v += a * z[k + 6 if up else k]
        used[(k, up)] = used.get((k, up), 0.0) + a
    return v, used


def rhs_ext(c, i, up, z, e, keep=None):
    """Upper (up) or lower extreme of state i's right-hand side over the box and the other states'
    bounds z (lower 0-5, upper 6-11). keep fixes the choice of extreme coefficients. Returns the
    value, the affine form ({(state, upper): coef}, constant) and the choice."""
    total, row, const, flags = 0.0, {}, 0.0, []
    for gi, (gsign, fname, terms) in enumerate(ENV_RHS[i]):
        want = (gsign > 0) == up             # the inner sum's upper extreme is needed
        parts, s = [], 0.0
        for ti, (tsign, cname, form) in enumerate(terms):
            need_max = (tsign > 0) == want
            v, used = _form_extreme(i, up, form, need_max, z, e)
            pos = v >= 0 if keep is None else keep[gi][0][ti]
            lo_c, hi_c = c[cname]
            coef = tsign * ((hi_c if pos else lo_c) if need_max else (lo_c if pos else hi_c))
            parts.append((pos, coef, used, form))
            s += coef * v
        spos = s >= 0 if keep is None else keep[gi][1]
        lo_f, hi_f = c[fname]
        f = gsign * ((hi_f if spos else lo_f) if want else (lo_f if spos else hi_f))
        flags.append((tuple(p[0] for p in parts), spos))
        for _, coef, used, form in parts:
            for k, a in used.items():
                row[k] = row.get(k, 0.0) + f * coef * a
            const += sum(f * coef * a * e[k] for k, a in form.items() if isinstance(k, str))
        total += f * s
    return total, (row, const), tuple(flags)


def _choice(c, z, e):
    return tuple(rhs_ext(c, i, up, z, e)[2] for up, i in ENV_ORDER)


def _linear(c, keep, e):
    """The 12-state linear system for one choice of extremes."""
    a = [[0.0] * 12 for _ in range(12)]
    b = [0.0] * 12
    for idx, (up, i) in enumerate(ENV_ORDER):
        _, (row, const), _ = rhs_ext(c, i, up, [0.0] * 12, e, keep[idx])
        for (k, kup), v in row.items():
            a[idx][k + 6 if kup else k] += v
        b[idx] = const
    return a, b


def _matmul(x, y):
    cols = list(zip(*y))
    return [[sum(p * q for p, q in zip(r, col)) for col in cols] for r in x]


def _expm_affine(a, b, h):
    """exp(a h) and the response to the constant b over h: the exponential of the augmented
    matrix, by scaling, a 20-term Taylor series and squaring."""
    n = len(a)
    m = [[x * h for x in row] + [bi * h] for row, bi in zip(a, b)] + [[0.0] * (n + 1)]
    norm = max(sum(abs(x) for x in row) for row in m)
    s = max(0, int(math.ceil(math.log2(norm))) + 1) if norm > 0.5 else 0
    m = [[x * 2.0 ** -s for x in row] for row in m]
    ex = [[float(i == j) for j in range(n + 1)] for i in range(n + 1)]
    term = [row[:] for row in ex]
    for k in range(1, 20):
        term = [[x / k for x in row] for row in _matmul(term, m)]
        ex = [[p + q for p, q in zip(r, t)] for r, t in zip(ex, term)]
    for _ in range(s):
        ex = _matmul(ex, ex)
    return [row[:n] for row in ex[:n]], [ex[i][n] for i in range(n)]


def envelope(c, src, init, per_decade):
    """Bounds of the six states for a unit step of source src (E0, E3, E5) from rest, or from the
    state init with no source. Returns the grid, the bounds at each grid point (lower 0-5, upper
    6-11), how often a change of choice was kept, and the largest widening that added."""
    e = {"E0": 0.0, "E3": 0.0, "E5": 0.0}
    if init is None:
        e[src] = 1.0
        init = (0.0,) * 6
    t0, t1 = ENV_T
    n = int(round(per_decade * math.log10(t1 / t0)))
    grid = [0.0] + [t0 * (t1 / t0) ** (k / n) for k in range(n + 1)]
    z = [float(x) for x in init] * 2
    out, cache, kept, widened = [z[:]], {}, 0, 0.0
    keep = _choice(c, z, e)
    for k in range(1, len(grid)):
        span = grid[k] - grid[k - 1]
        left = [span]
        while left:
            h = left.pop(0)
            if (keep, h) not in cache:
                cache[(keep, h)] = _expm_affine(*_linear(c, keep, e), h)
            phi, gam = cache[(keep, h)]
            zn = [sum(p * x for p, x in zip(row, z)) + g for row, g in zip(phi, gam)]
            nxt = _choice(c, zn, e)
            if nxt != keep:
                if h > ENV_H_MIN * span:
                    left = [h / 2, h / 2] + left
                    continue
                kept += 1
                for idx, (up, i) in enumerate(ENV_ORDER):
                    gap = rhs_ext(c, i, up, zn, e)[0] - rhs_ext(c, i, up, zn, e, keep[idx])[0]
                    gap = h * max(0.0, gap if up else -gap)
                    zn[idx] += gap if up else -gap
                    widened = max(widened, gap)
                nxt = _choice(c, zn, e)
            z, keep = zn, nxt
        out.append(z[:])
    return grid, out, kept, widened


def _env_job(job):
    key, g_lo, g_hi, src, init, per_decade = job
    return key, envelope(env_coefs(g_lo, g_hi), src, init, per_decade)


def _nodes(z):
    """Node voltage bounds (lower, upper) from the states: x1 = x0 + y1, x2 = x0 + y2."""
    return ([z[0], z[0] + z[1], z[0] + z[2], z[3], z[4], z[5]],
            [z[6], z[6] + z[7], z[6] + z[8], z[9], z[10], z[11]])


def _times(k, f):
    """Range of k * f, k a positive range, f = (lo, hi)."""
    return (k[0] * f[0] if f[0] >= 0 else k[1] * f[0]), (k[1] * f[1] if f[1] >= 0 else k[0] * f[1])


def _ends(grid, vals):
    """Integral of max(v, 0), taking the larger of each grid step's two ends."""
    return sum((t1 - t0) * max(0.0, v0, v1) for t0, t1, v0, v1 in zip(grid, grid[1:], vals, vals[1:]))


def kernel_bound(comp, c, runs):
    """The bound for one comparator and one coefficient set, from the envelopes of runs (E0, E3
    and E5 steps). Returns the rise and fall parts, the OUT1 switching excess, their total (V),
    the lag of the input from V_T (how far W can fall below and rise above VREG, V) and the
    widest bound at the end."""
    grid = runs["E0"][0]
    xs = {j: [_nodes(z) for z in runs[j][1]] for j in runs}
    k3 = (c["K3L"][0], c["K3H"][1])
    w = 1 if comp == 1 else 2
    d_lo, d_hi, h_lo, lag = [], [], [], ([], [])
    for n in range(len(grid)):
        def x(j, i):
            return xs[j][n][0][i], xs[j][n][1][i]
        if comp == 1:
            terms = [_times(k3, (x("E3", 4)[0] - x("E0", 1)[1], x("E3", 4)[1] - x("E0", 1)[0])),
                     _times(c["K0"], x("E0", 4)), _times(c["K5"], x("E5", 4)),
                     _times(k3, x("E3", 1)), _times(c["K5"], x("E5", 1))]
            sign = (1, 1, 1, -1, -1)
        else:
            terms = [_times(c["K5"], (x("E0", 2)[0] - x("E5", 5)[1], x("E0", 2)[1] - x("E5", 5)[0])),
                     _times(k3, x("E3", 2)), _times(c["K5"], x("E5", 2)),
                     _times(c["K0"], x("E0", 5)), _times(k3, x("E3", 5))]
            sign = (1, 1, 1, -1, -1)
        d_lo.append(sum(t[0] if s > 0 else -t[1] for t, s in zip(terms, sign)))
        d_hi.append(sum(t[1] if s > 0 else -t[0] for t, s in zip(terms, sign)))
        z = runs["E3"][1][n]
        if comp == 1:            # e1 y1 + e2 (x3 - x4)
            h_lo.append(_times(c["e1"], (z[1], z[7]))[0]
                        + _times(c["e2"], (z[3] - z[10], z[9] - z[4]))[0])
        else:                    # -e3 y2 + e4 x5
            h_lo.append(-_times(c["e3"], (z[2], z[8]))[1] + _times(c["e4"], (z[5], z[11]))[0])
        lag[0].append(1 - x("E0", w)[0])
        lag[1].append(x("E0", w)[1] - 1)
    rise = R_RISE * _ends(grid, d_hi)
    fall = R_FALL * _ends(grid, [-v for v in d_lo])
    kick = c["cO"][1] * V_TOP * _ends(grid, [-v for v in h_lo])
    behind, ahead = _ends(grid, lag[0]), _ends(grid, lag[1])
    end = max(max(z[6 + i] - z[i] for i in range(6)) for z in (runs[j][1][-1] for j in runs))
    return dict(rise=rise, fall=fall, kick=kick, total=rise + fall + kick,
                below=R_RISE * behind + R_FALL * ahead, above=R_FALL * behind + R_RISE * ahead,
                end=end, d=(d_lo, d_hi), grid=grid)


def filter_bound(pool, c_band, h_band, f_cold, f_hot, vfl):
    """The filter error bound (V) for each comparator over its trip band (deg C, widened by
    BAND_K), the lagged rail's range, and the margins beyond the band.

    The band's envelopes are solved at ENV_DECADE and twice that, and the larger bound is kept.
    Beyond the band, on the side where the comparator says "do not charge", the NTC range is cut
    into pieces, each with its own envelope: the static distance from the trip at the piece's
    nearest end, at the lagged rail's lowest value for that piece, must exceed the piece's bound.
    The trips themselves use the lagged rail over the band."""
    sets = {}
    for comp, band in ((1, c_band), (2, h_band)):
        r_lo, r_hi = (x * 1e3 for x in ntc_band(band[0] - BAND_K, band[1] + BAND_K))
        sets[(comp, "band")] = (1 / r_hi, 1 / r_lo, (ENV_DECADE, 2 * ENV_DECADE), (r_lo, r_hi))
        cuts = ENV_BEYOND[comp]
        for f0, f1 in zip(cuts, cuts[1:]):
            if comp == 1:            # colder, toward open: NTC r_hi f0 .. r_hi f1
                sets[(comp, f0)] = (0.0 if f1 is None else 1 / (r_hi * f1), 1 / (r_hi * f0),
                                    (ENV_DECADE_BEYOND,), (r_hi * f0, r_hi * f1 if f1 else None))
            else:                    # hotter, toward a short: NTC r_lo f1 .. r_lo f0
                sets[(comp, f0)] = (1 / (r_lo * f0), 1 / (r_lo * f1), (ENV_DECADE_BEYOND,),
                                    (r_lo * f1, r_lo * f0))
    jobs = [((key, pd, run), g_lo, g_hi, run, init, pd)
            for key, (g_lo, g_hi, pds, _) in sets.items() for pd in pds for run, init in ENV_RUNS]
    runs, stats = {}, {}
    for (key, pd, run), res in pool.imap_unordered(_env_job, jobs):
        runs.setdefault((key, pd), {})[run] = res
        old = stats.get(key, (0, 0.0))
        stats[key] = (old[0] + res[2], max(old[1], res[3]))
    out = {}
    for comp, f_tap in ((1, f_cold), (2, f_hot)):
        g_lo, g_hi, pds, ntc = sets[(comp, "band")]
        c = env_coefs(g_lo, g_hi)
        res = {pd: kernel_bound(comp, c, runs[((comp, "band"), pd)]) for pd in pds}
        best = max(res.values(), key=lambda r: r["total"])
        pieces = []
        for key in sets:
            if key[0] == comp and key[1] != "band":
                g0, g1, (pd,), span = sets[key]
                pieces.append((span, env_coefs(g0, g1), kernel_bound(comp, env_coefs(g0, g1),
                                                                     runs[(key, pd)])))
        out[comp] = dict(err=best["total"], best=best, steps=res, band=(ntc[0] / 1e3, ntc[1] / 1e3),
                         pieces=pieces, kept=sum(stats[k][0] for k in stats if k[0] == comp),
                         widened=max(stats[k][1] for k in stats if k[0] == comp), f_tap=f_tap,
                         coefs=c, runs=runs[((comp, "band"), ENV_DECADE)])
    below = max(o["best"]["below"] for o in out.values())
    above = max(o["best"]["above"] for o in out.values())
    w_lo, w_hi = vfl - below, VREG[2] + above
    for comp, o in out.items():
        least = None
        for (n0, n1), _, r in o["pieces"]:
            w_piece = vfl - r["below"]
            if comp == 1:            # nearest end n0, RS highest, the highest cold tap
                dist = (n0 / (RS * 1e3 * (1 + R_TOL) + n0) - o["f_tap"]) * w_piece
            else:                    # nearest end n1, RS lowest, the lowest hot tap
                dist = (o["f_tap"] - n1 / (RS * 1e3 * (1 - R_TOL) + n1)) * w_piece
            margin = dist - VOS_MAX - VHYS[2] / 2 - r["total"]
            least = margin if least is None else min(least, margin)
        o["least"] = least
    return dict(u=out, w=(w_lo, w_hi), lag=(below, above))


def network_steps(p):
    """Exact node responses at one set of values p to unit steps of E0, E3 and E5 (modes())."""
    caps, cond = network(p)
    g0 = 1 / p["rs"] + (0.0 if p["ntc"] is None else 1 / p["ntc"])
    g3 = 1 / p["rc1"] + 1 / p["rc2"] + 1 / p["rhys"]
    g5 = 1 / p["rh1"] + 1 / p["rh2"]
    srcs = [[g if i == node else 0.0 for i in range(6)] for node, g in ((0, g0), (3, g3), (5, g5))]
    return modes(caps, cond, srcs)


def _check_job(job):
    """Worker: one set of values against the band's envelopes. Returns the largest excursion of an
    exact node response outside its bounds (V, 0 when inside), and the exact rise + fall and OUT1
    excess of that point against the bounds, both with the same integration rule."""
    comp, p, grid, bounds, d_env = job
    rates, resp = network_steps(p)

    def x(j, i, t):
        amp, vss = resp[j]
        return vss[i] + sum(a * math.exp(-r * t) for a, r in zip(amp[i], rates))

    def slope(j, i, t):
        amp, _ = resp[j]
        return sum(-a * r * math.exp(-r * t) for a, r in zip(amp[i], rates))

    out = 0.0
    for n, t in enumerate(grid):
        for j, name in enumerate(("E0", "E3", "E5")):
            lo, hi = bounds[name][n]
            for i in range(6):
                v = x(j, i, t)
                out = max(out, lo[i] - v, v - hi[i])
    k0 = 1 / (1 + p["rs"] * (0.0 if p["ntc"] is None else 1 / p["ntc"]))
    g3 = 1 / p["rc1"] + 1 / p["rc2"] + 1 / p["rhys"]
    k3, co, k5 = (1 / p["rc1"] + 1 / p["rhys"]) / g3, 1 / p["rhys"] / g3, p["rh2"] / (p["rh1"] + p["rh2"])
    d, hd = [], []
    for t in grid:
        if comp == 1:
            d.append(k3 * (x(1, 4, t) - x(0, 1, t)) + k0 * x(0, 4, t) + k5 * x(2, 4, t)
                     - k3 * x(1, 1, t) - k5 * x(2, 1, t))
            hd.append(slope(1, 4, t) - slope(1, 1, t))
        else:
            d.append(k5 * (x(0, 2, t) - x(2, 5, t)) + k3 * x(1, 2, t) + k5 * x(2, 2, t)
                     - k0 * x(0, 5, t) - k3 * x(1, 5, t))
            hd.append(slope(1, 2, t) - slope(1, 5, t))
        lo, hi = d_env[0][len(d) - 1], d_env[1][len(d) - 1]
        out = max(out, lo - d[-1], d[-1] - hi)
    exact = R_RISE * _ends(grid, d) + R_FALL * _ends(grid, [-v for v in d])
    kick = co * V_TOP * _ends(grid, [-v for v in hd])
    return out, exact, kick


def env_check(pool, flt, n_points=ENV_POINTS):
    """Validation, not part of the bound: exact responses at sample points of the band (fixed
    seeds: random vertices, random interior points, and R5-M1's point for U1) must stay inside the
    envelopes, and their own rise + fall must stay below the bound. Also checks each coefficient
    at random interior points against its range. Returns, per comparator, the largest excursion
    outside the envelopes (V), and the largest exact error and OUT1 excess found."""
    res = {}
    for comp, o in flt["u"].items():
        r_lo, r_hi = (x * 1e3 for x in o["band"])
        best = o["steps"][ENV_DECADE]
        runs = o["runs"]
        bounds = {j: [_nodes(z) for z in runs[j][1]] for j in ("E0", "E3", "E5")}
        pts = []
        for i in range(n_points):
            rng = random.Random(1000 * comp + i)
            u = [float(rng.random() < 0.5) for _ in BOX] if i % 2 else [rng.random() for _ in BOX]
            pts.append(point(u, r_lo * (r_hi / r_lo) ** rng.random()))
        if comp == 1:
            pts.append(dict(R5_M1_POINT))
        jobs = [(comp, p, best["grid"], bounds, best["d"]) for p in pts]
        got = pool.map(_check_job, jobs, 4)
        for i in range(200):
            rng = random.Random(i)
            p = {name: lo + rng.random() * (hi - lo) for name, lo, hi in BOX}
            g = 1 / (r_lo * (r_hi / r_lo) ** rng.random())
            vals = dict(p, g=g, c4=p["cf1"] + p["cm1p"], c5=p["cm2n"] + p["chot"])
            for name, (fn, names) in ENV_COEFS.items():
                v = fn(*(vals[n] for n in names))
                lo, hi = o["coefs"][name]
                assert lo * (1 - 1e-12) <= v <= hi * (1 + 1e-12), name
        res[comp] = (max(g[0] for g in got), max(g[1] for g in got), max(g[2] for g in got), len(pts))
    return res


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

    # The fraction of VREG at each tap closest to "charge": U1's highest, U2's lowest.
    f_cold = RC2 * (1 + R_TOL) / (RC2 * (1 + R_TOL) + par(RC1 * (1 - R_TOL), RHYS * (1 - RHYS_TOL)))
    f_hot = RH2 * (1 - R_TOL) / (RH2 * (1 - R_TOL) + RH1 * (1 + R_TOL))
    with multiprocessing.Pool() as pool:
        flt = filter_bound(pool, c_trip, h_trip, f_cold, f_hot, vfl)
        chk = env_check(pool, flt)
    # The static trips at the lagged rail W (R6-M1): the falling floor less the inputs' lag.
    w_lo, w_hi = flt["w"]
    cold, hot = corners(w_lo, w_hi)
    lagd = dict(c_off=[c[0] for c in cold], c_on=[c[1] for c in cold], h_off=[h[0] for h in hot],
                h_on=[h[1] for h in hot])
    err_c_k = flt["u"][1]["err"] / (w_lo * slope_per_k(c_trip))
    err_h_k = flt["u"][2]["err"] / (w_lo * slope_per_k(h_trip))
    th_c = [par(RS, r_ntc(t, k) * (1 + d)) for t in c_trip for k in (0, 2)
            for d in (-NTC_DRIFT, NTC_DRIFT)]
    leak_v = LEAK_A * max(th_c) * 1e3
    leak_k = {v: leak_v / (v * slope_per_k(c_trip)) for v in (VREG_STATIC, w_lo)}
    sc_c = NTC_SELF_HEAT_K + GRADIENT_K + leak_k[w_lo]
    sc_s = NTC_SELF_HEAT_K + GRADIENT_K + leak_k[VREG_STATIC]
    safe_c = min(lagd["c_off"]) - sc_c - err_c_k
    safe_h = max(lagd["h_off"]) + GRADIENT_K + err_h_k

    # NTC self-heating at the cold trip: P = I^2 R at V_TOP, divided by 2 mW/K (still air,
    # datasheet). It scales as VREG squared (R6-N2).
    r1 = r_ntc(nom_c[0], 1)
    i_ma = V_TOP / (RS + r1)
    p_mw = i_ma ** 2 * r1
    print(f"Resistors: RS {RS} k, RC1 {RC1} k, RC2 {RC2} k, RHYS {RHYS / 1000:.2f} M, "
          f"RH1 {RH1} k, RH2 {RH2} k; tolerance +-{R_TOL * 100:.3f} % (RHYS +-{RHYS_TOL * 100:.0f} %)")
    print(f"NTC current at the cold trip, VREG {V_TOP} V: {i_ma * 1000:.0f} uA, {p_mw:.3f} mW -> "
          f"self-heating {p_mw / 2:.3f} K in still air (allowance {NTC_SELF_HEAT_K} K)")
    print()
    tp, tg = inhibit_latency()
    print(f"VREG bands: regulated {VREG[0]}-{VREG[2]} V; U4 static {VREG_STATIC:.3f}-{VREG[2]} V "
          f"(lowest VIT-); falling floor {vfl:.4f}-{VREG[2]} V; never above V_TOP {V_TOP} V (R6-N2)")
    print(f"  Floor: 10 % below the lowest VIT- ({0.9 * U4_VIT[0]:.4f} V), less {R_FALL:.0f} V/s for "
          f"U4's {tp * 1e6:.0f} us detect delay and {tg * 1e6:.1f} us for Q9 / Q10's gate to fall "
          f"to {VGS_OFF} V")
    print(f"  Lagged rail at the comparator inputs: W {w_lo:.4f}-{w_hi:.4f} V (the floor less "
          f"{flt['lag'][0] * 1000:.1f} mV, the top plus {flt['lag'][1] * 1000:.2f} mV: the inputs' lag "
          f"behind VREG at the steepest slopes)")
    print()
    print("| Trip | Nominal, deg C | Electrical worst case, VREG regulated | VREG down to U4's threshold "
          "| Safety corner: lagged rail at the falling floor, plus the filter bound |")
    print("|---|---|---|---|---|")
    print(f"| Cold off (cooling) | {nom_c[0]:+.2f} | {min(reg['c_off']):+.2f} to {max(reg['c_off']):+.2f} | "
          f"{min(st['c_off']):+.2f} to {max(st['c_off']):+.2f} | {safe_c:+.2f} (must be >= 0) |")
    print(f"| Cold on (warming) | {nom_c[1]:+.2f} | {min(reg['c_on']):+.2f} to {max(reg['c_on']):+.2f} | "
          f"{min(st['c_on']):+.2f} to {max(st['c_on']):+.2f} | "
          f"{min(lagd['c_on']) - sc_c - err_c_k:+.2f} |")
    print(f"| Hot off (heating) | {nom_h[0]:+.2f} | {min(reg['h_off']):+.2f} to {max(reg['h_off']):+.2f} | "
          f"{min(st['h_off']):+.2f} to {max(st['h_off']):+.2f} | {safe_h:+.2f} (must be <= 45) |")
    print(f"| Hot on (cooling) | {nom_h[1]:+.2f} | {min(reg['h_on']):+.2f} to {max(reg['h_on']):+.2f} | "
          f"{min(st['h_on']):+.2f} to {max(st['h_on']):+.2f} | "
          f"{max(lagd['h_on']) + GRADIENT_K + err_h_k:+.2f} |")
    print()
    print(f"Unrounded safety corners: cold off {safe_c:+.4f} C, hot off {safe_h:+.4f} C")
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
          f"at V_T ({leak_v * 1000:.2f} mV, {leak_k[w_lo]:.3f} K), both on the cold side "
          f"only, and a {GRADIENT_K} K NTC-to-cell gradient (all assumed).")

    print()
    print(f"Input filters: C_T {C_T * 1e12:.0f} pF on V_T (plus {C_T_PAR[1] * 1e12:.0f} pF at most of "
          f"ESD diode, cable and board); R_IN {R_IN} k into each comparator input, no capacitor; "
          f"R_F1 {R_F1} k and C_F1 {C_F1 * 1e12:.0f} pF on U1's tap; C_HOT {C_HOT * 1e12:.0f} pF on "
          f"U2's tap (C0G +-{C_TOL * 100:.0f} %, resistors +-{RF_TOL * 100:.0f} %)")
    print(f"  Comparator inputs: {C_CM[0] * 1e12:.0f}-{C_CM[1] * 1e12:.0f} pF to AGND each, "
          f"{C_DM[0] * 1e12:.0f}-{C_DM[1] * 1e12:.0f} pF between the two; U1's tap node "
          f"{C_NODE[0] * 1e12:.1f}-{C_NODE[1] * 1e12:.0f} pF (assumed)")
    print(f"  VREG slope: rise <= {I_LDO_LIMIT_A * 1000:.0f} mA / {C_VREG_MIN * 1e6:.0f} uF = "
          f"{R_RISE / 1000:.1f} V/ms; fall <= {I_VREG_MAX_MA} mA / {C_VREG_MIN * 1e6:.0f} uF = "
          f"{R_FALL:.0f} V/s (load {vreg_load_ma(VREG[2], True):.3f} mA at {VREG[2]} V with every gate "
          f"charging, {vreg_load_ma(VREG[2]):.3f} mA steady)")
    print(f"  Bound (R6-M1): interval envelope of the whole network over the box ({len(BOX)} values, each "
          f"independent) and the NTC, by Mueller's comparison theorem; for any VREG history inside "
          f"those slopes, either OUT1 state and any OUT1 switching sequence (OUT1 <= V_TOP)")
    for comp, name, k in ((1, "U1", err_c_k), (2, "U2", err_h_k)):
        o = flt["u"][comp]
        b = o["best"]
        out, exact, kick, n = chk[comp]
        print(f"  {name}: NTC {o['band'][0]:.3f}-{o['band'][1]:.3f} k (trip band +-{BAND_K} K): rise "
              f"{b['rise'] * 1000:.4f}, fall {b['fall'] * 1000:.4f}, OUT1 switching {b['kick'] * 1000:.5f} mV; "
              f"bound {o['err'] * 1000:.4f} mV = {k:.4f} K at {w_lo:.3f} V")
        decades = " / ".join(str(pd) for pd in sorted(o["steps"]))
        totals = " / ".join(f"{o['steps'][pd]['total'] * 1000:.4f}" for pd in sorted(o["steps"]))
        print(f"    at {decades} points a decade: {totals} mV (the larger kept); changes of choice kept {o['kept']}, widening <= {o['widened']:.1e}; "
              f"widest bound at {ENV_T[1] * 1000:.0f} ms {b['end']:.1e}")
        for (n0, n1), _, r in o["pieces"]:
            far = "open" if n1 is None else f"{n1 / 1000:.2f} k"
            print(f"    beyond the band, NTC {n0 / 1000:.2f} k to {far}: bound {r['total'] * 1000:.4f} mV")
        print(f"    Beyond the band, toward {'open' if comp == 1 else 'short'}: the static distance from the "
              f"trip exceeds the bound by >= {o['least'] * 1000:.0f} mV")
        print(f"    Validation, not part of the bound ({n} points, fixed seeds"
              f"{', R5-M1 point included' if comp == 1 else ''}): exact responses outside the envelopes "
              f"by <= {out:.1e}; exact rise + fall <= {exact * 1000:.4f} mV against "
              f"{(b['rise'] + b['fall']) * 1000:.4f}; OUT1 excess <= {kick * 1000:.5f} mV against "
              f"{b['kick'] * 1000:.5f}")
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
    for comp in (1, 2):
        b = flt["u"][comp]["best"]
        out, exact, kick, _ = chk[comp]
        assert flt["u"][comp]["least"] > 0 and out <= 1e-9
        assert exact <= b["rise"] + b["fall"] and kick <= b["kick"]
    assert min(lagd["c_off"]) - err_c_k >= c_trip[0] - BAND_K and max(lagd["c_on"]) + err_c_k <= c_trip[1] + BAND_K
    assert min(lagd["h_on"]) - err_h_k >= h_trip[0] - BAND_K and max(lagd["h_off"]) + err_h_k <= h_trip[1] + BAND_K
    assert safe_c >= 0 and safe_h <= 45


if __name__ == "__main__":
    main()
