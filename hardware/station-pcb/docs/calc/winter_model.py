#!/usr/bin/env python3
"""Hourly winter energy model for the Zephyr station PCB (F1 revision).

Input is a PVGIS v5.3 seriescalc JSON: hourly, pvcalculation=1, peakpower=1
(kWp), loss=14. Download one per tilt (45, 60 or 70):

  https://re.jrc.ec.europa.eu/api/v5_3/seriescalc?lat=50.90&lon=15.73&startyear=2005&endyear=2023&angle=45&aspect=0&usehorizon=1&pvcalculation=1&peakpower=1&loss=14&pvtechchoice=crystSi&mountingplace=free&outputformat=json

Usage (standard library only):

  python3 -I winter_model.py codex SERIES_60.json
      Reproduces the reviewer's daily-netting check (docs/reviews/F1-codex.md, M1).
  python3 -I winter_model.py scenarios SERIES_45.json SERIES_70.json
      Runs the chronological hourly battery model for the option table in
      ARCHITECTURE.md section 4.

Every input below is an assumption or a datasheet value documented in
ARCHITECTURE.md section 4. The results are model outputs, not measurements.
"""

import json
import math
import sys

# Conversion and battery assumptions (ARCHITECTURE.md section 4.1).
PV_LOSS = 0.86          # PVGIS 14 % system loss, removed; the charger efficiency replaces it
ETA_CHG = 0.85          # charger and wiring efficiency (assumed)
V_NOM = 3.7             # battery voltage for mAh <-> Wh (assumed)
V_CHG = 3.8             # mean battery voltage while charging, for current clipping (assumed)
I_CHG = 1.46            # charge current, about 1.5 A for either D5 charger; CN3791 nominal (computed)
USABLE = 0.90 * 0.85    # usable window x cold derating (assumed)
SELF_DIS = 0.02 / 730   # self-discharge per hour as a fraction of stored energy, 2 %/month (assumed)
RESTART = 0.05          # after a brown-out the station restarts at 5 % of usable energy (assumed)
PM_SKIP_C = -10.0       # PM readings skipped below this air temperature (owner answer Q12)
WIFI_MAH = 1.0          # daily allowance for an occasional Wi-Fi/OTA session (assumed)
RETRY_MARGIN = 1.05     # pessimistic profiles: failed reads and on-demand requests (assumed)
FLOOR_TYP_UA = 55.5     # sleep floor incl. protection board, typical (ARCHITECTURE.md section 4.2)
FLOOR_MAX_UA = 101.8    # sleep floor incl. protection board, bounded (ARCHITECTURE.md section 4.2)

# Battery-side cost per event in mAh, from ARCHITECTURE.md section 4.3 (reconstructed
# independently in F1-codex.md), plus the Ra-01H receive current (12.15 mA instead of
# 10.3 mA): 8.1 s or 8 s x 1.85 mA x 3.3 / (0.9 x 3.7).
RX_FIX_M1 = 8.1 * 1.85 * 3.3 / (0.9 * 3.7) / 3600
RX_FIX_M2 = 8.0 * 1.85 * 3.3 / (0.9 * 3.7) / 3600
EVENTS = {
    "M1": dict(listen=0.13998 + RX_FIX_M1, listen_s=9.4, read=1.902, read_s=65.0, pms=1.054),
    "M1p": dict(listen=0.19949 + RX_FIX_M1, listen_s=9.4, read=2.577, read_s=65.0, pms=1.318),
    "M2": dict(listen=0.02664 + RX_FIX_M2, listen_s=8.3, read=1.507, read_s=63.8, pms=1.054),
    "M2p": dict(listen=0.02714 + RX_FIX_M2, listen_s=8.3, read=1.876, read_s=63.8, pms=1.318),
}

# Cadences: (full reads per day, listen wakes per day, PM on full reads).
CADENCE = {
    "15min": (96, 1344, True),       # listen every minute, full read every 15 min
    "now": (74.1, 1111.5, True),     # today's 19.4-min firmware cycle
    "lean": (48, 288, True),         # full read every 30 min, listen every 5 min
    "survival": (24, 96, False),     # hourly read without PM, listen every 15 min
}


def daily_mah(events, cadence, floor_ua, margin=1.0):
    """Battery-side mAh per day for one event set and cadence, and PM mAh per read."""
    ev = EVENTS[events]
    reads, listens, pm = CADENCE[cadence]
    read = ev["read"] if pm else ev["read"] - ev["pms"]
    awake_h = (listens * ev["listen_s"] + reads * ev["read_s"]) / 3600
    mah = listens * ev["listen"] + reads * read + floor_ua / 1000 * (24 - awake_h) + WIFI_MAH
    return mah * margin, (reads * ev["pms"] if pm else 0.0)


# Load profiles: list of (mode name, events, cadence, floor, margin). One mode means a
# fixed schedule; several modes form the adaptive policy, ordered from normal to lean.
PROFILES = {
    "M1 now (19.4-min cycle)": [("normal", "M1", "now", FLOOR_TYP_UA, 1.0)],
    "M1 nominal": [("normal", "M1", "15min", FLOOR_TYP_UA, 1.0)],
    "M1 pessimistic": [("normal", "M1p", "15min", FLOOR_MAX_UA, RETRY_MARGIN)],
    "M2 nominal": [("normal", "M2", "15min", FLOOR_TYP_UA, 1.0)],
    "M2 pessimistic": [("normal", "M2p", "15min", FLOOR_MAX_UA, RETRY_MARGIN)],
    "M2 adaptive": [
        ("normal", "M2", "15min", FLOOR_TYP_UA, 1.0),
        ("lean", "M2", "lean", FLOOR_TYP_UA, 1.0),
        ("survival", "M2", "survival", FLOOR_TYP_UA, 1.0),
    ],
}
# Adaptive thresholds on state of charge: (enter below, leave above) for lean and survival.
LEAN_AT, LEAN_OFF = 0.40, 0.50
SURV_AT, SURV_OFF = 0.15, 0.20


def load_series(path):
    data = json.load(open(path))
    rows = [(r["time"][:8], r["P"], r["G(i)"], r["T2m"]) for r in data["outputs"]["hourly"]]
    return data["inputs"], rows


# ---------------------------------------------------------------- reviewer check

def daily_harvest(rows, wp=10.0, t_low=0.0, t_high=45.0):
    """Battery-side Wh per UTC day, charging only while t_low <= T2m <= t_high."""
    days, order = {}, []
    for day, p, _g, t in rows:
        if day not in days:
            days[day] = 0.0
            order.append(day)
        if t_low <= t <= t_high:
            days[day] += p * wp / 1000 / PV_LOSS * ETA_CHG
    return [(d, days[d]) for d in order]


def december_windows(daily, length):
    """Worst consecutive window of `length` days inside one December."""
    by_year = {}
    for day, h in daily:
        if day[4:6] == "12":
            by_year.setdefault(day[:4], []).append((day, h))
    worst = None
    for days in by_year.values():
        for i in range(len(days) - length + 1):
            mean = sum(h for _d, h in days[i:i + length]) / length
            if worst is None or mean < worst[0]:
                worst = (mean, days[i][0], days[i + length - 1][0])
    return worst


def window_mean(daily, first, last):
    vals = [h for d, h in daily if first <= d <= last]
    return sum(vals) / len(vals)


def max_deficit(daily, load_wh):
    """Largest cumulative deficit D = max(0, D + load - harvest), never reset."""
    d, start, best = 0.0, None, (0.0, None, None)
    for day, h in daily:
        if d == 0.0:
            start = day
        d = max(0.0, d + load_wh - h)
        if d > best[0]:
            best = (d, start, day)
    return best


def cmd_codex(path):
    inputs, rows = load_series(path)
    print(f"Series: {inputs['mounting_system']['fixed']['slope']['value']} deg, "
          f"{inputs['meteo_data']['radiation_db']}/{inputs['meteo_data']['meteo_db']}, "
          f"{inputs['meteo_data']['year_min']}-{inputs['meteo_data']['year_max']}")
    daily = daily_harvest(rows)
    dec = [h for d, h in daily if d[4:6] == "12"]
    print(f"December mean, gated 0-45 C: {sum(dec) / len(dec):.3f} Wh/day")
    print(f"12-18 Dec 2018: {window_mean(daily, '20181212', '20181218'):.3f} Wh/day")
    print(f"13-26 Dec 2018: {window_mean(daily, '20181213', '20181226'):.3f} Wh/day")
    for n in (7, 14):
        mean, a, b = december_windows(daily, n)
        print(f"Worst December {n}-day window: {mean:.3f} Wh/day, {a}-{b}")
    # Daily loads exactly as in the draft and the review.
    for name, mah in (("M1 nominal", 371.73), ("M1 pessimistic", 516.54),
                      ("M2 nominal", 181.52), ("M2 pessimistic", 217.61)):
        d, a, b = max_deficit(daily, mah * V_NOM / 1000)
        print(f"Max cumulative deficit {name} ({mah * V_NOM / 1000:.3f} Wh/day): {d:.2f} Wh, {a}-{b}")


# ---------------------------------------------------------------- hourly model

def season_of(day):
    """Winter season label: Jul-Jun, named by the autumn year."""
    y, m = int(day[:4]), int(day[4:6])
    return y if m >= 7 else y - 1


def simulate(rows, profile, wp=10.0, ah=10.2, t_low=0.0, t_high=45.0,
             sun_k=0.0, heater=None):
    """Chronological hourly battery model. Returns per-season statistics.

    sun_k: cell temperature = air + sun_k * G(i), an illustrative box warming term.
    heater: dict(ua=W/K, c=J/K, p_max=W, target=deg C) heats the pack from panel power
            only, before charging; the pack follows a first-order thermal model.
    """
    modes = []
    for name, ev, cad, floor, margin in PROFILES[profile]:
        mah, pms_mah = daily_mah(ev, cad, floor, margin)
        modes.append((name, mah / 24 * V_NOM / 1000, pms_mah / 24 * V_NOM / 1000))
    floor_wh = PROFILES[profile][0][3] / 1e6 * V_NOM    # the profile's own sleep floor
    e_max = ah * USABLE * V_NOM
    p_clip = I_CHG * V_CHG
    e, mode, down = e_max, 0, False
    t_pack = None
    stats = {}
    run, longest = 0, (0, None)
    for day, p, g, t_air in rows:
        s = stats.setdefault(season_of(day), dict(down_h=0, min_soc=1.0, lean_h=0, surv_h=0))
        pv = p * wp / 1000 / PV_LOSS                      # panel power at MPP, W
        if heater:
            if t_pack is None:
                t_pack = t_air
            tau = heater["c"] / heater["ua"]
            a = math.exp(-3600 / tau)
            p_heat = 0.0
            if pv > 0 and t_pack < heater["target"]:
                t_eq_needed = (heater["target"] - t_pack * a) / (1 - a)
                p_need = heater["ua"] * (t_eq_needed - t_air)
                p_heat = max(0.0, min(p_need, heater["p_max"], pv))
            t_start = t_pack
            t_eq = t_air + p_heat / heater["ua"]
            t_pack = t_eq + (t_pack - t_eq) * a
            t_cell = min(t_start, t_pack)
            pv -= p_heat
        else:
            t_cell = t_air + sun_k * g
        charge = min(pv * ETA_CHG, p_clip) if t_low <= t_cell <= t_high else 0.0
        if down:
            load = floor_wh
        else:
            _name, load, pms = modes[mode]
            if t_air < PM_SKIP_C:
                load -= pms
        e += charge - load - e * SELF_DIS
        if e <= 0.0:
            e, down = 0.0, True
        elif e > e_max:
            e = e_max
        soc = e / e_max
        if down and soc >= RESTART:
            down = False
            mode = len(modes) - 1
        if len(modes) > 1 and not down:
            if mode == 0 and soc < LEAN_AT:
                mode = 1
            if mode == 1 and soc < SURV_AT:
                mode = 2
            elif mode == 1 and soc > LEAN_OFF:
                mode = 0
            if mode == 2 and soc > SURV_OFF:
                mode = 1
        if down:
            s["down_h"] += 1
            s["min_soc"] = 0.0
            if run == 0:
                run_start = day
            run += 1
            if run > longest[0]:
                longest = (run, run_start)
        else:
            run = 0
            s["min_soc"] = min(s["min_soc"], soc)
            s["lean_h"] += mode == 1
            s["surv_h"] += mode == 2
    full = {k: v for k, v in stats.items() if 2005 <= k <= 2022}
    return full, longest, modes


def summarize(full, longest):
    seasons = sorted(full)
    out_seasons = [k for k in seasons if full[k]["down_h"]]
    down_days = sum(full[k]["down_h"] for k in seasons) / 24
    worst = max(seasons, key=lambda k: full[k]["down_h"])
    mins = sorted(full[k]["min_soc"] for k in seasons)
    surv_days = sum(full[k]["surv_h"] for k in seasons) / 24
    lean_days = sum(full[k]["lean_h"] for k in seasons) / 24
    return dict(
        n_out=len(out_seasons), n=len(seasons), down_days=down_days,
        worst=(full[worst]["down_h"] / 24, f"{worst}/{(worst + 1) % 100:02d}"),
        longest=(longest[0] / 24, longest[1]),
        median_min_soc=mins[len(mins) // 2], low_min_soc=mins[0],
        lean_days=lean_days, surv_days=surv_days,
    )


def required_ah(rows, profile, **kw):
    """Smallest nominal pack (Ah) with no brown-out in any full season, to 0.1 Ah."""
    lo, hi = 1.0, 400.0
    full, _l, _m = simulate(rows, profile, ah=hi, **kw)
    if any(v["down_h"] for v in full.values()):
        return None
    while hi - lo > 0.1:
        mid = (lo + hi) / 2
        full, _l, _m = simulate(rows, profile, ah=mid, **kw)
        if any(v["down_h"] for v in full.values()):
            lo = mid
        else:
            hi = mid
    return hi


def fmt_row(label, profile, r):
    worst_d, worst_s = r["worst"]
    long_d, long_start = r["longest"]
    worst = f"{worst_d:.0f} ({worst_s})" if worst_d else "-"
    longest = f"{long_d:.0f} d from {long_start[:4]}-{long_start[4:6]}-{long_start[6:]}" if long_d else "-"
    modes = f"{r['lean_days']:.0f} / {r['surv_days']:.0f}" if profile == "M2 adaptive" else "-"
    return (f"| {label} | {profile} | {r['n_out']}/{r['n']} | {r['down_days']:.0f} | "
            f"{worst} | {longest} | {r['low_min_soc'] * 100:.0f} % | {modes} |")


def fmt_cell(r):
    if not r["n_out"]:
        return f"none (lowest {r['low_min_soc'] * 100:.0f} %)"
    return f"{r['n_out']}/18, {r['down_days']:.0f} d (longest {r['longest'][0]:.0f} d)"


HEATER = dict(ua=0.05, c=200.0, p_max=2.0, target=5.0)
MATRIX_PROFILES = ("M1 nominal", "M1 pessimistic", "M2 nominal", "M2 adaptive")


def december_table(rows):
    """December harvest statistics into the battery for the harvest table."""
    print("| December case, 45 deg south | No temperature limit, Wh/day | Charging 0-45 C, Wh/day | Charging +1 to +44 C, Wh/day |")
    print("|---|---|---|---|")
    series = [daily_harvest(rows, t_low=-99.0, t_high=99.0), daily_harvest(rows),
              daily_harvest(rows, t_low=1.0, t_high=44.0)]
    decs = [sorted(h for d, h in s if d[4:6] == "12") for s in series]
    stats = [
        ("Mean", lambda v, s: sum(v) / len(v)),
        ("Median day", lambda v, s: v[len(v) // 2]),
        ("10th-percentile day", lambda v, s: v[len(v) // 10]),
        ("Worst 7-day window", lambda v, s: december_windows(s, 7)[0]),
        ("Worst 14-day window", lambda v, s: december_windows(s, 14)[0]),
    ]
    for name, fn in stats:
        cells = [f"{fn(v, s):.2f}" for v, s in zip(decs, series)]
        print(f"| {name} | " + " | ".join(cells) + " |")
    for s, label in zip(series, ("ungated", "0-45 C", "+1-44 C")):
        for n in (7, 14):
            mean, a, b = december_windows(s, n)
            print(f"  worst {n}-day, {label}: {mean:.3f} Wh/day, {a}-{b}")


def cmd_scenarios(path45, path70=None):
    _i, rows45 = load_series(path45)
    rows70 = load_series(path70)[1] if path70 else None
    december_table(rows45)
    print("Daily loads (battery side):")
    for prof, modes in PROFILES.items():
        for name, ev, cad, floor, margin in modes:
            mah, pms = daily_mah(ev, cad, floor, margin)
            print(f"  {prof:24s} {name:9s} {mah:7.1f} mAh = {mah * V_NOM / 1000:.3f} Wh/day (PM {pms:.1f} mAh)")
    daily = daily_harvest(rows45)
    dec = [h for d, h in daily if d[4:6] == "12"]
    dec_ungated = [h for d, h in daily_harvest(rows45, t_low=-99) if d[4:6] == "12"]
    print(f"45 deg December mean into battery: {sum(dec) / len(dec):.3f} Wh/day gated, "
          f"{sum(dec_ungated) / len(dec_ungated):.3f} Wh/day if charging were allowed at any temperature")
    for n in (7, 14):
        mean, a, b = december_windows(daily, n)
        print(f"45 deg worst December {n}-day window, gated: {mean:.3f} Wh/day, {a}-{b}")
    for name, mah in (("M1 nominal", 371.73), ("M2 nominal", 181.52)):
        d, a, b = max_deficit(daily, mah * V_NOM / 1000)
        print(f"45 deg daily-netting max deficit {name}: {d:.2f} Wh, {a}-{b}")

    g1 = dict(t_low=1.0, t_high=44.0)
    cases = [
        ("Lower cutoff 0 C at the cells (exact, no tolerance)", rows45, {}),
        ("Lower cutoff +1 C (interlock error <= 1 K)", rows45, g1),
        ("Lower cutoff +2 C (interlock error <= 2 K)", rows45, dict(t_low=2.0, t_high=43.0)),
        ("Lower cutoff +3 C (interlock error <= 3 K)", rows45, dict(t_low=3.0, t_high=42.0)),
        ("Pack x2 (20.4 Ah), cutoff +1 C", rows45, dict(g1, ah=20.4)),
        ("Pack x3 (30.6 Ah), cutoff +1 C", rows45, dict(g1, ah=30.6)),
        ("Panel 20 W, cutoff +1 C", rows45, dict(g1, wp=20.0)),
    ]
    if rows70:
        cases.append(("Tilt 70 deg, cutoff +1 C", rows70, g1))
    cases += [
        ("Sun-warmed box, cells +1 K per 100 W/m2 (illustrative), cutoff +1 C", rows45,
         dict(g1, sun_k=0.01)),
        ("Panel-powered pack heater (illustrative), cutoff +1 C", rows45, dict(g1, heater=HEATER)),
        ("Cells chargeable down to -20 C (e.g. LTO)", rows45, dict(t_low=-20.0)),
    ]
    results = []
    for label, rows, kw in cases:
        for prof in MATRIX_PROFILES:
            full, longest, _m = simulate(rows, prof, **kw)
            results.append((label, prof, summarize(full, longest)))
    print()
    print("| Case | Load profile | Seasons with brown-out | Brown-out days, 18 seasons | Worst season, days | Longest brown-out | Lowest charge | Lean / survival days |")
    print("|---|---|---|---|---|---|---|---|")
    for label, prof, r in results:
        print(fmt_row(label, prof, r))
    print()
    print("| Case (10 W, 45 deg, 10.2 Ah unless stated) | " + " | ".join(MATRIX_PROFILES) + " |")
    print("|---" * (len(MATRIX_PROFILES) + 1) + "|")
    for label, _rows, _kw in cases:
        cells = [fmt_cell(r) for lab, _p, r in results if lab == label]
        print(f"| {label} | " + " | ".join(cells) + " |")
    print()
    print("Smallest nominal pack with no brown-out in 2005/06-2022/23 (10 W, 45 deg):")
    for gate in (0.0, 1.0, 3.0):
        for prof in ("M1 now (19.4-min cycle)", "M1 nominal", "M1 pessimistic", "M2 nominal",
                     "M2 pessimistic", "M2 adaptive"):
            need = required_ah(rows45, prof, t_low=gate, t_high=45.0 - gate)
            print(f"  gate {gate:+.0f} C  {prof:24s} " + (f"{need:.1f} Ah" if need else "> 400 Ah"))


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "codex":
        cmd_codex(sys.argv[2])
    elif len(sys.argv) >= 3 and sys.argv[1] == "scenarios":
        cmd_scenarios(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        sys.exit(__doc__)
