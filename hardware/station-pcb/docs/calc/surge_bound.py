#!/usr/bin/env python3
"""Panel-input surge bound (F1 revision 5, R5-M2 and R5-M3).

The TVS is an SM15T33CA at the TPS26600's IN pin (ARCHITECTURE.md D5). Its maximum clamp at a
current below the rated one follows ST's own formula, DS0683 Rev 8, Table 2 note 3:
    VCL(I) = VCL - RD * (IPP - I),
and note 2 scales VCL with the junction temperature at the start of the pulse:
    VCL(Tj) = VCL(25 C) * (1 + alphaT * (Tj - 25)).
The fifth review read both notes and the SM15T33CA row in Rev 8 (reviews/F1-codex-r5.md, R5-M2).
The copy archived here is ST's 2007 revision 4 (build/f1-revision/research/power/), which has the
same VBR, VCL, IPP and alphaT, and the pulse-derating curve (Figure 1) used below.

Everything is rounded up to 10 mV. Standard library only:
  python3 -I surge_bound.py
"""

import math

# SM15T33CA, 10/1000 us (ST DS0683 Rev 8 Table 2, as quoted in review r5; Rev 4 Table 3).
VBR_MIN = 31.4           # V at 25 C
VCL, IPP, RD = 45.7, 33.0, 0.333     # V, A, ohm
ALPHA_T = 9.8e-4         # per K, maximum
PPP = 1500.0             # W, 10/1000 us, from Tj = 25 C
RTH_JA = 75.0            # K/W, junction to ambient on the recommended pad (Rev 4)
# Rev 4 Figure 1: peak pulse power is 100 % up to Tj = 25 C, then falls linearly to 50 % at 150 C.
DERATE_AT_150 = 0.5

# The defined surge (REQUIREMENTS.md R-P1, assumed definition): 10/1000 us current pulse of up to
# 11.3 A peak, either polarity, at most once a minute, the board at -30 to +50 C.
I_SURGE, PERIOD_S, T_BOARD_MAX, T_BOARD_MIN = 11.3, 60.0, 50.0, -30.0
TAIL_S = 1000e-6 / math.log(2)      # charge of a 10/1000 us pulse is about I_peak * this
COLD_VOC = 28.0          # panel's worst-case open-circuit voltage, V (ARCHITECTURE.md D5)

# Layout and parts (F2/F3 requirements, assumed values).
L_TVS = 10e-9            # H, the TVS's own loop at IN
DI_DT = I_SURGE / 10e-6  # A/s, the pulse's rise
I_PANEL = 1.0            # A, the panel's short-circuit current with margin (about 0.6 A at STC)
L_LOOP = 5e-9            # H, IN pin to the first VIN capacitors, through the TPS26600
C_VIN = 10e-6            # F, effective at 40 V over -30 to +50 C and ageing
LT3652_ABS, TPS26600_ABS, TPS26600_NEG, LDO_OPER, LDO_200MS = 40.0, 62.0, -60.0, 40.0, 45.0


def up(v):
    """Round up to 10 mV."""
    return math.ceil(v * 100 - 1e-9) / 100


def main():
    v25 = VCL - RD * (IPP - I_SURGE)
    # Self-heating between pulses: the mean power of one pulse a minute through RTH_JA, with the
    # clamp taken at its rated maximum VCL for the whole pulse.
    energy = VCL * I_SURGE * TAIL_S
    dt_mean = energy / PERIOD_S * RTH_JA
    tj = T_BOARD_MAX + math.ceil(dt_mean)
    v_hot = v25 * (1 + ALPHA_T * (tj - 25))
    v_in = v_hot + L_TVS * DI_DT
    i_loop = I_SURGE + I_PANEL
    over = i_loop * math.sqrt(L_LOOP / C_VIN)
    v_vin = v_in + over
    derate = 1 - (1 - DERATE_AT_150) * (tj - 25) / 125
    vbr_cold = VBR_MIN * (1 - ALPHA_T * (25 - T_BOARD_MIN))

    print(f"SM15T33CA at {I_SURGE} A (ST note 3): {VCL} - {RD} x ({IPP} - {I_SURGE}) = {v25:.4f} V from Tj 25 C")
    print(f"Self-heating: <= {energy:.3f} J a pulse, once in {PERIOD_S:.0f} s, through {RTH_JA:.0f} K/W: "
          f"+{dt_mean:.2f} K mean, so Tj starts at <= {tj:.0f} C")
    print(f"From Tj {tj:.0f} C (ST note 2): x (1 + {ALPHA_T} x {tj - 25:.0f}) = {v_hot:.4f} V")
    print(f"TPS26600 IN: + {L_TVS * 1e9:.0f} nH x {DI_DT / 1e6:.2f} A/us = {v_in:.4f} V -> IN <= {up(v_in):.2f} V "
          f"(either polarity; rated {TPS26600_ABS:.0f} V, {TPS26600_NEG:.0f} V)")
    print(f"LT3652 VIN: + {i_loop:.1f} A x sqrt({L_LOOP * 1e9:.0f} nH / {C_VIN * 1e6:.0f} uF) = +{over:.4f} V "
          f"-> VIN <= {up(v_vin):.2f} V (rated {LT3652_ABS:.0f} V absolute; margin {LT3652_ABS - up(v_vin):.2f} V)")
    print(f"  sqrt(L/C) <= {math.sqrt(L_LOOP / C_VIN) * 1e3:.1f} mOhm, e.g. {L_LOOP * 1e9:.0f} nH with "
          f"{C_VIN * 1e6:.0f} uF or 10 nH with {10e-9 / (L_LOOP / C_VIN) * 1e6:.0f} uF")
    print(f"TPS7B6933 input (through its diode and 1 kOhm, no Zener credited): <= {up(v_in):.2f} V "
          f"(operating <= {LDO_OPER:.0f} V, {LDO_200MS:.0f} V for 200 ms)")
    print(f"Pulse rating from Tj {tj:.0f} C (Rev 4 Figure 1): {derate * 100:.1f} % of {PPP:.0f} W = "
          f"{derate * PPP:.0f} W, {derate * IPP:.1f} A; the defined pulse is <= {up(v_in) * I_SURGE:.0f} W "
          f"({up(v_in) * I_SURGE / (derate * PPP) * 100:.0f} %), {I_SURGE} A ({I_SURGE / (derate * IPP) * 100:.0f} %)")
    print(f"Cold breakdown at {T_BOARD_MIN:.0f} C: >= {VBR_MIN} x (1 - {ALPHA_T} x {25 - T_BOARD_MIN:.0f}) = "
          f"{vbr_cold:.2f} V, above the cold Voc {COLD_VOC:.0f} V")
    assert up(v_vin) < LT3652_ABS and up(v_in) < LDO_OPER and vbr_cold > COLD_VOC


if __name__ == "__main__":
    main()
