#!/usr/bin/env python3
"""Panel-input surge bound (F1 revision 6: R6-M2 and R6-M3).

The TVS is an SM15T33CA at the TPS26600's IN pin (ARCHITECTURE.md D5). Its maximum clamp at a
current below the rated one follows ST's own formula, DS0683 Rev 8 (May 2022), Table 2 note 3:
    VCL(I) = VCL - RD * (IPP - I),
and note 2 scales VCL with the junction temperature at the start of the pulse:
    VCL(Tj) = VCL(25 C) * (1 + alphaT * (Tj - 25)).
Source: ST DS0683 Rev 8, LCSC copy retrieved by the sixth review (reviews/F1-pi-r6.md), archived
in build/f1-revision/research/power/st_sm15t_rev8_lcsc/ (SHA-256 3d4c7f4c...44). Pulse derating
is Rev 8 Figure 3 and the thermal resistance Rev 8 Figure 12 (revision 5 used the 2007 Rev 4).

Thermal envelope (R6-M3). The defined pulse's current stays below an explicit envelope: I_SURGE
up to T_FRONT, then halving every T_HALF. That bounds its charge and, with the clamp taken at its
rated 45.7 V, its energy. The junction's heating is a passive RC network, so its response to a
unit of energy is a sum of decaying exponentials with positive weights (the driving-point form),
decreasing in time. Just before a pulse, the rise left by all earlier pulses, one every PERIOD_S,
is then at most E / PERIOD_S * Rth(j-a): the average power through the steady thermal resistance.
Rth(j-a) is taken above Figure 12's footprint-only value, with no copper credit, plus T_LOCAL for
neighbouring parts.

Switching envelope (R6-M2): when the TPS26600 opens, the current it carried moves into C_IN and
the TVS loop at IN, and the current in the loop from OUT to the VIN capacitors continues through
the OUT Schottky. Both are bounded below with passive arguments and stated layout requirements;
what they don't cover is printed as open.

Everything is rounded up to 10 mV. Standard library only:
  python3 -I surge_bound.py
"""

import math

# SM15T33CA, 10/1000 us (ST DS0683 Rev 8, Table 2 and notes 2-3).
VBR_MIN = 31.4           # V at 25 C
VCL, IPP, RD = 45.7, 33.0, 0.333     # V, A, ohm
ALPHA_T = 9.8e-4         # per K, maximum
PPP = 1500.0             # W, 10/1000 us, from Tj = 25 C
# Rev 8 Figure 3: 100 % of PPP up to about 115-120 C (graphical reading), about 1250 W at 150 C.
# Taken as 100 % only up to DERATE_KNEE.
DERATE_KNEE = 110.0      # C
# Rev 8 Figure 12 (FR4, 70 um copper): Rth(j-a) about 110-112 K/W on the footprint alone, 80 at
# 0.35 cm2, 65 at 1 cm2, 50 at 2.5 cm2. Taken as RTH_JA with no copper credit (assumed; F3 keeps
# at least ST's recommended footprint, F6 measures).
RTH_JA = 120.0           # K/W
T_LOCAL = 5.0            # K, local heating from neighbouring parts above the board's 50 C (assumed;
                         # F3 keeps the TVS away from the LT3652, its inductor and catch diode)

# The defined surge (REQUIREMENTS.md R-P1, assumed definition): 10/1000 us current pulse of up to
# 11.3 A peak, either polarity, at most once a minute, the board at -30 to +50 C. Waveform envelope
# (assumed definition): front time <= 13 us and time to half value <= 1.2 ms (10/1000 us with
# +30 % / +20 % tolerance); the current stays below I_SURGE up to T_FRONT and below
# I_SURGE * 2^(-(t - T_FRONT) / T_HALF) after.
I_SURGE, PERIOD_S, T_BOARD_MAX, T_BOARD_MIN = 11.3, 60.0, 50.0, -30.0
T_FRONT, T_HALF = 13e-6, 1.2e-3
COLD_VOC = 28.0          # panel's worst-case open-circuit voltage, V (ARCHITECTURE.md D5)

# Layout and parts (F2/F3 requirements, assumed values).
L_TVS = 10e-9            # H, the TVS's own loop at IN
DI_DT = I_SURGE / 10e-6  # A/s, the pulse's rise
I_PANEL = 1.0            # A, the panel's short-circuit current with margin (about 0.6 A at STC)
L_LOOP = 5e-9            # H, IN pin to the first VIN capacitors, through the TPS26600
C_VIN = 10e-6            # F, effective at 40 V over -30 to +50 C and ageing
C_IN = 1e-6              # F, ceramic at the IN pin, effective at 40 V (F2: rated >= 50 V)
LT3652_ABS, TPS26600_ABS, TPS26600_NEG, LDO_OPER, LDO_200MS = 40.0, 62.0, -60.0, 40.0, 45.0
TPS26600_OUT_MIN = -0.3  # V, OUT to RTN absolute minimum ([TP] 7.1)


def up(v):
    """Round up to 10 mV."""
    return math.ceil(v * 100 - 1e-9) / 100


def ceilings(i_surge, rth, t_local):
    """Charge, energy, mean rise, starting Tj, clamp at Tj, IN and VIN for one set of premises."""
    charge = i_surge * (T_FRONT + T_HALF / math.log(2))
    energy = VCL * charge
    dt_mean = energy / PERIOD_S * rth
    tj = math.ceil(T_BOARD_MAX + t_local + dt_mean)
    v25 = VCL - RD * (IPP - i_surge)
    v_hot = v25 * (1 + ALPHA_T * (tj - 25))
    v_in = v_hot + L_TVS * i_surge / 10e-6
    v_vin = v_in + (i_surge + I_PANEL) * math.sqrt(L_LOOP / C_VIN)
    return charge, energy, dt_mean, tj, v25, v_hot, v_in, v_vin


def main():
    charge, energy, dt_mean, tj, v25, v_hot, v_in, v_vin = ceilings(I_SURGE, RTH_JA, T_LOCAL)
    i_loop = I_SURGE + I_PANEL
    over = i_loop * math.sqrt(L_LOOP / C_VIN)
    vbr_cold = VBR_MIN * (1 - ALPHA_T * (25 - T_BOARD_MIN))

    print(f"SM15T33CA at {I_SURGE} A (ST Rev 8 note 3): {VCL} - {RD} x ({IPP} - {I_SURGE}) = {v25:.4f} V from Tj 25 C")
    print(f"Pulse envelope: <= {I_SURGE} A to {T_FRONT * 1e6:.0f} us, then halving every {T_HALF * 1e3:.1f} ms: "
          f"charge <= {charge * 1000:.2f} mC, energy <= {VCL} V x charge = {energy:.3f} J")
    print(f"Pre-pulse heating (periodic, passive network): <= {energy:.3f} J / {PERIOD_S:.0f} s x "
          f"{RTH_JA:.0f} K/W = {dt_mean:.2f} K; plus {T_LOCAL:.0f} K local on a {T_BOARD_MAX:.0f} C board, "
          f"so Tj starts at <= {tj:.0f} C")
    print(f"From Tj {tj:.0f} C (ST note 2): x (1 + {ALPHA_T} x {tj - 25:.0f}) = {v_hot:.4f} V")
    print(f"TPS26600 IN, switch closed: + {L_TVS * 1e9:.0f} nH x {DI_DT / 1e6:.2f} A/us = {v_in:.4f} V -> "
          f"IN <= {up(v_in):.2f} V (either polarity; rated {TPS26600_ABS:.0f} V, {TPS26600_NEG:.0f} V)")
    print(f"LT3652 VIN: + {i_loop:.1f} A x sqrt({L_LOOP * 1e9:.0f} nH / {C_VIN * 1e6:.0f} uF) = +{over:.4f} V "
          f"-> VIN <= {up(v_vin):.2f} V (rated {LT3652_ABS:.0f} V absolute; margin {LT3652_ABS - up(v_vin):.2f} V)")
    print(f"  sqrt(L/C) <= {math.sqrt(L_LOOP / C_VIN) * 1e3:.1f} mOhm, e.g. {L_LOOP * 1e9:.0f} nH with "
          f"{C_VIN * 1e6:.0f} uF or 10 nH with {10e-9 / (L_LOOP / C_VIN) * 1e6:.0f} uF")
    print(f"  valid while IN stays <= {up(v_in):.2f} V with the switch closed and the loop current is "
          f"<= {i_loop:.1f} A when VIN reaches it (energy 1/2 C (VIN - IN max)^2 + 1/2 L i^2 can't grow)")
    print(f"TPS7B6933 input (through its diode and 1 kOhm, no Zener credited): <= {up(v_in):.2f} V "
          f"(operating <= {LDO_OPER:.0f} V, {LDO_200MS:.0f} V for 200 ms)")
    p_pulse = up(v_in) * I_SURGE
    print(f"Pulse rating from Tj {tj:.0f} C (Rev 8 Figure 3: 100 % up to >= {DERATE_KNEE:.0f} C): {PPP:.0f} W, "
          f"{IPP:.0f} A; the defined pulse is <= {p_pulse:.0f} W ({p_pulse / PPP * 100:.0f} %), "
          f"{I_SURGE} A ({I_SURGE / IPP * 100:.0f} %)")
    print(f"Cold breakdown at {T_BOARD_MIN:.0f} C: >= {VBR_MIN} x (1 - {ALPHA_T} x {25 - T_BOARD_MIN:.0f}) = "
          f"{vbr_cold:.2f} V, above the cold Voc {COLD_VOC:.0f} V")

    # Switching (R6-M2). Without the TPS26600's timing (typical only), the switch may carry the
    # whole input current when it opens.
    print()
    print("Switch opening (R6-M2), no switch timing credited:")
    di = i_loop
    v_eq = (VCL - RD * (IPP - di)) * (1 + ALPHA_T * (tj - 25))
    z_in = math.sqrt(L_TVS / C_IN)
    # Energy of C_IN and the TVS loop about the TVS's new operating point can't grow (the TVS is
    # monotone), and the loop starts at most (v_eq - cold breakdown) below it with di to take up.
    v_spike = v_eq + math.hypot(v_eq - vbr_cold, di * z_in)
    print(f"  IN: up to {di:.1f} A moves into C_IN {C_IN * 1e6:.0f} uF || TVS loop {L_TVS * 1e9:.0f} nH "
          f"(sqrt(L/C) = {z_in * 1000:.0f} mOhm): IN <= {up(v_spike):.2f} V, inside the TPS26600's "
          f"{TPS26600_ABS:.0f} V; above the LDO's {LDO_200MS:.0f} V only through its 1 kOhm and input capacitor")
    print(f"  OUT: the loop current continues through the OUT Schottky into C_VIN (VIN term above). "
          f"OUT then sits at -VF of that Schottky at up to {di:.1f} A, against the TPS26600's "
          f"{TPS26600_OUT_MIN} V OUT rating: open unless the interrupted current is bounded")
    print(f"  VIN margin left for recovery and C_IN's stored charge feeding the loop: "
          f"{LT3652_ABS - up(v_vin):.2f} V")
    print()
    print("Sensitivity (same model):")
    for name, args in (("this envelope", (I_SURGE, RTH_JA, T_LOCAL)),
                       ("Rth 80 K/W (copper, F3), 2 K local", (I_SURGE, 80.0, 2.0)),
                       ("defined surge 10 A", (10.0, RTH_JA, T_LOCAL)),
                       ("defined surge 8 A", (8.0, RTH_JA, T_LOCAL))):
        r = ceilings(*args)
        print(f"  {name}: Tj <= {r[3]:.0f} C, IN <= {up(r[6]):.2f} V, VIN <= {up(r[7]):.2f} V "
              f"(margin {LT3652_ABS - up(r[7]):.2f} V)")
    assert v_hot < VCL and tj < DERATE_KNEE
    assert up(v_vin) < LT3652_ABS and up(v_in) < LDO_OPER and vbr_cold > COLD_VOC
    assert up(v_spike) < TPS26600_ABS


if __name__ == "__main__":
    main()
