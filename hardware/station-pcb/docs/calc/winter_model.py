#!/usr/bin/env python3
"""Hourly winter energy model for the Zephyr station PCB (F1 revision 5).

Input is a PVGIS v5.3 seriescalc JSON: hourly, pvcalculation=1, peakpower=1
(kWp), loss=14. PVGIS's aspect is the azimuth from south (90 = west), so the
panel's compass azimuth of 233 deg is aspect=53. Download one per tilt:

  https://re.jrc.ec.europa.eu/api/v5_3/seriescalc?lat=50.90&lon=15.73&startyear=2005&endyear=2023&angle=45&aspect=53&usehorizon=1&pvcalculation=1&peakpower=1&loss=14&pvtechchoice=crystSi&mountingplace=free&outputformat=json

Usage (standard library only):

  python3 -I winter_model.py codex SERIES_60_SOUTH.json
      Reproduces the first review's daily-netting check (docs/reviews/F1-codex.md, M1).
  python3 -I winter_model.py r2check SERIES_45_SOUTH.json
      Reproduces the re-review's hysteresis sensitivity (docs/reviews/F1-codex-r2.md,
      R2-M1) with the revision-1 loads and policy.
  python3 -I winter_model.py scenarios SERIES_45_SW.json SERIES_70_SW.json SERIES_45_SOUTH.json
      Runs the revision-3 model for ARCHITECTURE.md sections 4.3-4.5 and D13.

Every input below is an assumption or a datasheet value documented in
ARCHITECTURE.md section 4. The results are model outputs, not measurements.
"""

import hashlib
import json
import math
import sys

# Conversion and battery assumptions (ARCHITECTURE.md section 4.1).
PV_LOSS = 0.86          # PVGIS 14 % system loss, removed; the charger efficiency replaces it
ETA_CHG = 0.85          # charger and wiring efficiency (assumed)
V_NOM = 3.7             # battery voltage for mAh <-> Wh (assumed)
V_CHG = 3.8             # mean battery voltage while charging, for current clipping (assumed)
I_CHG = 1.46            # LT3652 charge current; a 68 mOhm sense resistor gives 1.47 A (D5)
USABLE = 0.90 * 0.85    # usable window x cold derating (assumed)
SELF_DIS = 0.02 / 730   # self-discharge per hour as a fraction of stored energy, 2 %/month (assumed)
PM_SKIP_C = -10.0       # PM readings skipped below this air temperature (owner answer Q12)
WIFI_MAH = 1.0          # daily allowance for an occasional Wi-Fi/OTA session (assumed)
K3 = 3.3 / (0.9 * 3.7)  # awake 3.3 V rail mAh -> battery mAh
K5 = 5.0 / (0.9 * 3.7)  # 5 V rail mAh -> battery mAh
CELL_AH = 3.35          # Samsung INR18650-35E, minimum capacity at 0.2C (owner answer 19; Samsung
                        # specification Ver 1.1, July 2015): 10.05 Ah in today's 1S3P


def load_series(path):
    data = json.load(open(path, "rb"))
    rows = []
    for r in data["outputs"]["hourly"]:
        day = r["time"][:8]
        y, m = int(day[:4]), int(day[4:6])
        rows.append((day, r["P"], r["G(i)"], r["T2m"], y if m >= 7 else y - 1))
    return data["inputs"], rows


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def describe(path, inputs):
    fixed = inputs["mounting_system"]["fixed"]
    meteo = inputs["meteo_data"]
    return (f"{fixed['slope']['value']} deg tilt, aspect {fixed['azimuth']['value']} "
            f"({meteo['radiation_db']}/{meteo['meteo_db']}, {meteo['year_min']}-{meteo['year_max']}), "
            f"SHA-256 {sha256(path)}")


# ---------------------------------------------------------------- reviewer check (M1)

def daily_harvest(rows, wp=10.0, t_low=0.0, t_high=45.0):
    """Battery-side Wh per UTC day, charging only while t_low <= T2m <= t_high."""
    days, order = {}, []
    for day, p, _g, t, _s in rows:
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
    print(f"Series: {describe(path, inputs)}")
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


# ---------------------------------------------------------------- revision-1 loads (r2check)

# Battery-side cost per event in mAh and the cadences exactly as in revision 1 (a22e006).
R1_EVENTS = {
    "M2": dict(listen=0.02664 + 8.0 * 1.85 * K3 / 3600, listen_s=8.3, read=1.507, read_s=63.8,
               pms=1.054),
}
R1_CADENCE = {"15min": (96, 1344, True), "lean": (48, 288, True), "survival": (24, 96, False)}
R1_FLOOR_UA = 55.5


def r1_modes():
    """Revision-1 M2 adaptive: hourly Wh and PMS Wh per mode, sleep floor in Wh/h."""
    ev = R1_EVENTS["M2"]
    modes = []
    for cad in ("15min", "lean", "survival"):
        reads, listens, pm = R1_CADENCE[cad]
        read = ev["read"] if pm else ev["read"] - ev["pms"]
        awake_h = (listens * ev["listen_s"] + reads * ev["read_s"]) / 3600
        mah = listens * ev["listen"] + reads * read + R1_FLOOR_UA / 1000 * (24 - awake_h) + WIFI_MAH
        modes.append((mah / 24 * V_NOM / 1000, (reads * ev["pms"] if pm else 0.0) / 24 * V_NOM / 1000))
    floor_wh = R1_FLOOR_UA / 1e6 * V_NOM
    return modes, floor_wh


# ---------------------------------------------------------------- revision-2 loads

# Currents on their own rail in mA, nominal / pessimistic (ARCHITECTURE.md section 4.1).
CPU_MA = {"M1": (45.0, 68.0), "M2": (25.0, 31.0)}   # M1 at 240 MHz, M2 at 80 MHz
RADIO_STBY_MA, RADIO_RX_MA, LIGHT_SLEEP_MA, INA_MA = 1.6, 12.15, 0.8, 0.7
TX_MA_S = 40.0 * 0.0668      # one 28-byte frame at +10 dBm
HEATER_MA_S = 12.0 * 0.15    # BME680 gas heater
PMS_MA = (80.0, 100.0)       # PMS7003 at 5 V
# Timeline in seconds (station.ino at 82ee40d; ARCHITECTURE.md section 4.3).
PMS_S = (31.6, 35.1)         # 0.1 s + 30 s warm-up + reads; retries allow up to 35.1 s
WIND_S = 31.0                # measureWindSpeed()
OTHER_S = {"M1": 2.417, "M2": 1.2}               # boot, BME680, INA219 and TX
LISTEN_S = {"M1": (1.3, 8.1), "M2": (0.3, 8.0)}  # set-up while awake, then the receive window


def listen_event(fw, p):
    """One listen wake: battery mAh and seconds awake."""
    setup, rx = LISTEN_S[fw]
    cpu = CPU_MA[fw][p]
    idle = cpu if fw == "M1" else LIGHT_SLEEP_MA     # M2 light-sleeps while the radio listens
    ma_s = setup * (cpu + RADIO_STBY_MA) + rx * (idle + RADIO_RX_MA)
    return ma_s * K3 / 3600, setup + rx


def read_event(fw, p, pm=True):
    """One full read: battery mAh, seconds awake, and the PMS7003's share in mAh."""
    pms_s = PMS_S[p] if pm else 0.0
    if fw == "M1":      # as today: PMS, then the wind count, radio in standby
        secs = OTHER_S[fw] + pms_s + WIND_S
        rail = CPU_MA[fw][p] + RADIO_STBY_MA + INA_MA
    else:               # M2: radio asleep until TX, wind counted during the PMS warm-up
        secs = OTHER_S[fw] + max(pms_s, WIND_S)
        rail = CPU_MA[fw][p] + INA_MA
    pms = pms_s * PMS_MA[p] * K5 / 3600
    return (secs * rail + HEATER_MA_S + TX_MA_S) * K3 / 3600 + pms, secs, pms


# Schedules on an absolute minute grid: (full-read period, listen period or None) in seconds,
# PM on full reads, Wi-Fi/OTA allowance. Revision 3 has no listen windows (owner answer 23:
# nobody uses the gateway's request button). The listening schedules remain only to compare
# with today's firmware and revision 2; there a full read takes the listen slot it starts in
# and every slot that starts before it ends.
SCHEDULES = {
    "normal": (900, None, True, True),
    "lean": (1800, None, True, True),
    "survival": (3600, None, False, False),
    "normal, 1-min listen": (900, 60, True, True),          # today's listen period
    "lean, 5-min listen": (1800, 300, True, True),           # revision 2
    "survival, 15-min listen": (3600, 900, False, False),    # revision 2
}
GATEWAY_WINDOW_S = 120       # the unchanged gateway repeats a request for 120 s (gateway.ino)
REQUESTS = (2.0, 10.0)       # button requests per day while listening, nominal / pessimistic (assumed)
ACK_S = 2.0                  # receive window after each report for a LoRa ACK (PRD Phase 3; sensitivity)

# Drain on the cells, protection board included (ARCHITECTURE.md section 4.2), in uA.
FLOOR_UA = (55.8, 138.7)     # deep sleep: typical at 3.7 V / high-side estimate at 3.0 V and 70 %
                             # (pessimistic: the converter runs down to 3.05 V at most)
FLOOR_LIMIT_UA = 151.4       # sensitivity: a board at R-P7's limit (b), 132 uA at 3.4 V, leaves 4.9 uA
                             # on the 3.3 V rail; at 3.0 V and 70 % that is 145.4 uA at the link, plus
                             # 6 uA for the protection board
OFF_UA = (15.6, 27.3)        # the TPS3840 holds the 3.3 V converter off: typical / high-side
HIB_CHECK_MAH = 0.25 * 25.0 * K3 / 3600   # hourly battery check while hibernating


def day_load(fw, p, sched, ack_s=0.0, read_scale=1.0):
    """Battery mAh per day, PMS mAh per day and the event counts for one schedule.
    ack_s adds a receive window after every report; read_scale multiplies the part of a read's
    cost that isn't the PMS7003."""
    read_p, listen_p, pm, wifi = SCHEDULES[sched]
    r_mah, r_s, pms = read_event(fw, p, pm)
    idle = CPU_MA[fw][p] if fw == "M1" else LIGHT_SLEEP_MA
    r_mah = (r_mah - pms + ack_s * (idle + RADIO_RX_MA) * K3 / 3600) * read_scale + pms
    r_s += ack_s
    reads = 86400 / read_p
    if listen_p is None:
        l_mah, l_s, listens, served = 0.0, 0.0, 0.0, 0.0
    else:
        l_mah, l_s = listen_event(fw, p)
        listens = 86400 / listen_p - reads * math.ceil(r_s / listen_p)
        # A request is heard only if a listen falls inside the gateway's window. Serving it
        # costs one extra full read, which starts after that listen and may cover the next slot.
        served = REQUESTS[p] * min(1.0, GATEWAY_WINDOW_S / listen_p)
        listens -= served * math.floor((LISTEN_S[fw][1] + r_s) / listen_p)
    awake_h = (listens * l_s + (reads + served) * r_s) / 3600
    mah = (listens * l_mah + (reads + served) * r_mah + FLOOR_UA[p] / 1000 * (24 - awake_h)
           + (WIFI_MAH if wifi else 0.0))
    counts = dict(reads=reads, listens=listens, served=served, read=r_mah, read_s=r_s,
                  listen=l_mah, listen_s=l_s)
    return mah, (reads + served) * pms, counts


def now_load():
    """Today's firmware (19.4-min cycle): 15 listens and one full read, 60 s sleep after each."""
    l_mah, l_s = listen_event("M1", 0)
    r_mah, r_s, pms = read_event("M1", 0)
    cycle = 16 * 60 + 15 * l_s + r_s
    reads = 86400 / cycle
    awake_h = reads * (15 * l_s + r_s) / 3600
    mah = reads * (15 * l_mah + r_mah) + FLOOR_UA[0] / 1000 * (24 - awake_h) + WIFI_MAH
    return mah, reads * pms, reads


# Load profiles: (firmware, 0 nominal / 1 pessimistic, schedules from normal to survival,
# receive window after each report in s).
ADAPTIVE = ("normal", "lean", "survival")
PROFILES = {
    "M1 nominal, 1-min listen": ("M1", 0, ("normal, 1-min listen",), 0.0),
    "M1 pessimistic, 1-min listen": ("M1", 1, ("normal, 1-min listen",), 0.0),
    "M1 reads, no listen": ("M1", 0, ("normal",), 0.0),
    "M1 reads, no listen, pessimistic": ("M1", 1, ("normal",), 0.0),
    "M2 nominal": ("M2", 0, ("normal",), 0.0),
    "M2 pessimistic": ("M2", 1, ("normal",), 0.0),
    "M2 adaptive": ("M2", 0, ADAPTIVE, 0.0),
    "M2 adaptive pessimistic": ("M2", 1, ADAPTIVE, 0.0),
    "M2 adaptive, 2 s ACK window": ("M2", 0, ADAPTIVE, ACK_S),
    "M2 adaptive pessimistic, 2 s ACK window": ("M2", 1, ADAPTIVE, ACK_S),
    "M2 adaptive pessimistic, revision-2 listening": (
        "M2", 1, ("normal, 1-min listen", "lean, 5-min listen", "survival, 15-min listen"), 0.0),
}


def r2_modes(profile, read_scale=1.0):
    """Hourly Wh and PMS Wh per mode, plus the hibernation and UVLO-off drains in Wh/h."""
    if profile == "M1 now (19.4-min cycle)":
        mah, pms, _r = now_load()
        modes, p = [(mah / 24 * V_NOM / 1000, pms / 24 * V_NOM / 1000)], 0
    else:
        fw, p, scheds, ack_s = PROFILES[profile]
        modes = []
        for s in scheds:
            mah, pms, _c = day_load(fw, p, s, ack_s, read_scale)
            modes.append((mah / 24 * V_NOM / 1000, pms / 24 * V_NOM / 1000))
    hib_wh = (FLOOR_UA[p] / 1000 + HIB_CHECK_MAH) * V_NOM / 1000
    return modes, hib_wh, OFF_UA[p] / 1e6 * V_NOM


# ---------------------------------------------------------------- policy and interlock

# Low-energy policy (ARCHITECTURE.md section 6, D13).
# lean / surv: (enter below, leave above) on the firmware's charge estimate, which is off by
#   soc_bias. The revision-2 values are 45/55 % and 20/25 % raised by the 15 % estimate error,
#   so an estimate that reads 15 % high still enters survival at a true 20 %. That covers the
#   longest stretch without charging (about 60 days at the energy corner) at the pessimistic
#   survival load, 10.1 mAh/day without listening, with today's pack.
# hib_at / restart: hibernate below, resume in the lowest schedule above. These two use the
#   battery voltage near empty, where the curve is steep, so the model applies them to the true
#   charge. release: the TPS3840 (off below 3.05-3.15 V) lets the converter restart above
#   3.23-3.37 V; the ESP32 then boots into hibernation.
R1_POLICY = dict(lean=(0.40, 0.50), surv=(0.15, 0.20), hib_at=None, restart=0.05, release=0.05)
R2_POLICY = dict(lean=(0.60, 0.70), surv=(0.35, 0.40), hib_at=0.03, restart=0.12, release=0.02)
SOC_ERROR = 0.15             # the firmware's charge estimate may be off by this much either way (assumed)

# Interlock trips at the NTC in deg C: (cold off, cold on, hot off, hot on), from
# calc/interlock_trips.py. The energy corner puts every tolerance toward less charging, and is
# rounded that way. Revision 5 adds the comparator's output levels (cold off 2.709 -> 2.723 C).
GATE_NOMINAL = (1.71, 2.11, 42.64, 42.42)
GATE_CORNER = (2.73, 3.09, 41.52, 41.32)
GATE_R1 = (1.0, 1.0, 44.0, 44.0)           # revision 1: stateless +1 / +44 C


def gate(ok, t, powered, trips):
    """Interlock output after one hour. Unpowered means off (TLV3012B power-on reset)."""
    if not powered:
        return False
    cold_off, cold_on, hot_off, hot_on = trips
    if ok:
        return cold_off <= t <= hot_off
    return cold_on <= t <= hot_on


def simulate(rows, modes, hib_wh, off_wh, policy, ah=10.2, wp=10.0, trips=GATE_NOMINAL,
             reset="night", soc_bias=0.0):
    """Chronological hourly battery model. Returns per-season statistics.

    reset: "night" means the panel-powered interlock loses power whenever the panel is
           dark and restarts off; "retain" keeps its state across nights (sensitivity).
    soc_bias: the firmware's charge estimate minus the true charge, as a fraction of the
              usable energy.
    Cell temperature = air temperature T2m (assumed).
    """
    lean_at, lean_off = policy["lean"]
    surv_at, surv_off = policy["surv"]
    hib_at, restart, release = policy["hib_at"], policy["restart"], policy["release"]
    e_max = ah * USABLE * V_NOM
    p_clip = I_CHG * V_CHG
    retain = reset == "retain"
    last = len(modes) - 1
    e, state, mode, ok = e_max, "run", 0, False
    stats = {}
    run, longest, run_start = 0, (0, None), None
    for day, p, _g, t_air, season in rows:
        s = stats.get(season)
        if s is None:
            s = stats[season] = dict(out_h=0, min_soc=1.0, lean_h=0, surv_h=0, hibs=0, trips=0,
                                     restarts=0)
        ok = gate(ok, t_air, retain or p > 0, trips)
        charge = min(p * wp / 1000 / PV_LOSS * ETA_CHG, p_clip) if ok else 0.0
        if state == "run":
            load, pms = modes[mode]
            if t_air < PM_SKIP_C:
                load -= pms
        elif state == "hib":
            load = hib_wh
        else:
            load = off_wh
        e += charge - load - e * SELF_DIS
        if e <= 0.0:
            e = 0.0
            if state != "off":
                s["trips"] += 1
            state = "off"
        elif e > e_max:
            e = e_max
        soc = e / e_max
        if state == "off" and soc >= release:
            state = "hib"
        if state == "hib" and soc >= restart:
            state, mode = "run", last
            s["restarts"] += 1
        elif state == "run":
            if hib_at is not None and soc < hib_at:
                state = "hib"
                s["hibs"] += 1
            elif last:
                est = soc + soc_bias
                if mode == 0 and est < lean_at:
                    mode = 1
                if mode == 1 and est < surv_at:
                    mode = 2
                elif mode == 1 and est > lean_off:
                    mode = 0
                if mode == 2 and est > surv_off:
                    mode = 1
        s["min_soc"] = min(s["min_soc"], soc)
        if state != "run":
            s["out_h"] += 1
            if 2005 <= season <= 2022:
                if run == 0:
                    run_start = day
                run += 1
                if run > longest[0]:
                    longest = (run, run_start)
            continue
        run = 0
        s["lean_h"] += mode == 1
        s["surv_h"] += mode == 2
    full = {k: v for k, v in stats.items() if 2005 <= k <= 2022}
    return full, longest


def summarize(full, longest):
    seasons = sorted(full)
    out_seasons = [k for k in seasons if full[k]["out_h"]]
    worst = max(seasons, key=lambda k: full[k]["out_h"])
    return dict(
        n_out=len(out_seasons), n=len(seasons),
        out_days=sum(full[k]["out_h"] for k in seasons) / 24,
        worst=(full[worst]["out_h"] / 24, f"{worst}/{(worst + 1) % 100:02d}"),
        longest=(longest[0] / 24, longest[1]),
        low_min_soc=min(full[k]["min_soc"] for k in seasons),
        lean_days=sum(full[k]["lean_h"] for k in seasons) / 24,
        surv_days=sum(full[k]["surv_h"] for k in seasons) / 24,
        hibs=sum(full[k]["hibs"] for k in seasons),
        trips=sum(full[k]["trips"] for k in seasons),
        restarts=sum(full[k]["restarts"] for k in seasons),
    )


def run_case(rows, profile, policy=R2_POLICY, read_scale=1.0, **kw):
    modes, hib_wh, off_wh = r2_modes(profile, read_scale)
    full, longest = simulate(rows, modes, hib_wh, off_wh, policy, **kw)
    return summarize(full, longest)


def worst_case(rows, profile, **kw):
    """Run with the charge estimate off by -SOC_ERROR, 0 and +SOC_ERROR; return all three and
    the one with the most outage hours (then the lowest charge)."""
    if "adaptive" not in profile:      # the estimate only moves the adaptive schedule
        r = run_case(rows, profile, **kw)
        return [r, r, r], r
    runs = [run_case(rows, profile, soc_bias=b, **kw) for b in (-SOC_ERROR, 0.0, SOC_ERROR)]
    return runs, max(runs, key=lambda r: (r["out_days"], -r["low_min_soc"]))


def required_ah(rows, profile, estimate_error=False, **kw):
    """Smallest nominal pack (Ah) with no outage hour in any full season, to 0.1 Ah.
    With estimate_error, an adaptive profile must also pass at +-SOC_ERROR."""
    def fails(ah):
        if estimate_error:
            return worst_case(rows, profile, ah=ah, **kw)[1]["n_out"] > 0
        return run_case(rows, profile, ah=ah, **kw)["n_out"] > 0
    lo, hi = 1.0, 400.0
    if fails(hi):
        return None
    while hi - lo > 0.1:
        mid = (lo + hi) / 2
        if fails(mid):
            lo = mid
        else:
            hi = mid
    return hi


def read_cost_limit(rows, profile, ah, **kw):
    """Largest cost of a full read with PM (mAh, battery side) at which the profile still has no
    outage hour in any full season, with the charge estimate off by up to SOC_ERROR. The part of
    every read that isn't the PMS7003 is scaled alike; the PMS share, floor, Wi-Fi allowance and
    policy stay as they are."""
    fw, p, scheds, ack_s = PROFILES[profile]
    full = day_load(fw, p, scheds[0], ack_s)[2]["read"]
    pms = read_event(fw, p)[2]

    def passes(scale):
        return worst_case(rows, profile, ah=ah, read_scale=scale, **kw)[1]["n_out"] == 0
    lo, hi = 0.0, 1.0
    while passes(hi):
        lo, hi = hi, hi * 2
        if hi > 64:
            return None
    while hi - lo > 0.005:
        mid = (lo + hi) / 2
        if passes(mid):
            lo = mid
        else:
            hi = mid
    return lo * (full - pms) + pms


def cold_hours(rows):
    """Per full season: hours with air below -10 C and below -20 C; and the coldest hour."""
    per = {}
    coldest = (99.0, None)
    for day, _p, _g, t, season in rows:
        if not 2005 <= season <= 2022:
            continue
        c = per.setdefault(season, [0, 0])
        c[0] += t < -10.0
        c[1] += t < -20.0
        if t < coldest[0]:
            coldest = (t, day)
    return per, coldest


def longest_without_charge(rows, trips, reset="night"):
    """Longest run of hours with no charging through the interlock: (days, first day)."""
    ok, run, best, start = False, 0, (0, None), None
    for day, p, _g, t, _s in rows:
        ok = gate(ok, t, reset == "retain" or p > 0, trips)
        if ok and p > 0:
            run = 0
            continue
        if run == 0:
            start = day
        run += 1
        if run > best[0]:
            best = (run, start)
    return best[0] / 24, best[1]


# ---------------------------------------------------------------- re-review check (R2-M1)

def cmd_r2check(path):
    inputs, rows = load_series(path)
    print(f"Series: {describe(path, inputs)}")
    print("Revision-1 M2 adaptive loads and policy; only the interlock changes.")
    print("| Cold disable / re-enable | Outage seasons | Outage days | Lean / survival days | Minimum SOC |")
    print("|---|---:|---:|---|---:|")
    modes, floor_wh = r1_modes()
    cases = [("Baseline stateless +1 C", GATE_R1, "retain"),
             ("+1 / +3 C", (1.0, 3.0, 43.0, 40.0), "retain"),
             ("+1 / +4 C", (1.0, 4.0, 43.0, 40.0), "retain"),
             ("+2 / +5 C", (2.0, 5.0, 43.0, 40.0), "retain")]
    for label, trips, reset in cases:
        full, longest = simulate(rows, modes, floor_wh, floor_wh, R1_POLICY, trips=trips, reset=reset)
        r = summarize(full, longest)
        print(f"| {label} | {r['n_out']} | {r['out_days']:.2f} | {r['lean_days']:.2f} / "
              f"{r['surv_days']:.2f} | {r['low_min_soc'] * 100:.3f} % |")


# ---------------------------------------------------------------- revision-2 scenarios

def gated_daily(rows, trips, reset="night", wp=10.0):
    """Battery-side Wh per UTC day through the interlock state machine (no battery limit)."""
    days, order, ok = {}, [], False
    for day, p, _g, t, _s in rows:
        if day not in days:
            days[day] = 0.0
            order.append(day)
        ok = gate(ok, t, reset == "retain" or p > 0, trips)
        if ok:
            days[day] += p * wp / 1000 / PV_LOSS * ETA_CHG
    return [(d, days[d]) for d in order]


def december_table(rows, label):
    print(f"| December, {label} | No temperature limit | Interlock nominal, reset at night | "
          f"Interlock energy corner, reset at night |")
    print("|---|---|---|---|")
    series = [gated_daily(rows, (-99.0, -99.0, 99.0, 99.0)), gated_daily(rows, GATE_NOMINAL),
              gated_daily(rows, GATE_CORNER)]
    decs = [sorted(h for d, h in s if d[4:6] == "12") for s in series]
    stats = [
        ("Mean, Wh/day", lambda v, s: f"{sum(v) / len(v):.2f}"),
        ("Median day, Wh", lambda v, s: f"{v[len(v) // 2]:.2f}"),
        ("Worst 7-day window, Wh/day", lambda v, s: "{:.2f} ({}-{})".format(*december_windows(s, 7))),
        ("Worst 14-day window, Wh/day", lambda v, s: "{:.2f} ({}-{})".format(*december_windows(s, 14))),
    ]
    for name, fn in stats:
        print(f"| {name} | " + " | ".join(fn(v, s) for v, s in zip(decs, series)) + " |")


def fmt_cell(r, modes=False):
    if not r["n_out"]:
        text = f"none (lowest {r['low_min_soc'] * 100:.0f} %)"
    else:
        text = f"{r['n_out']}/18, {r['out_days']:.0f} d (longest {r['longest'][0]:.0f} d)"
    if modes:
        text += f"; lean {r['lean_days']:.0f} d, survival {r['surv_days']:.0f} d"
    return text


def fmt_ah(need):
    if need is None:
        return "> 400 Ah"
    return f"{need:.1f} Ah = {math.ceil(need / CELL_AH)} cells ({math.ceil(need / (CELL_AH * 0.8))})"


def per_winter(r):
    return f"{r['lean_days'] / r['n']:.1f} / {r['surv_days'] / r['n']:.1f}"


def fmt_mah(mah):
    return "> 64 x the event cost" if mah is None else f"{mah:.2f} mAh"


def cmd_scenarios(path_sw45, path_sw70, path_s45):
    global FLOOR_UA
    inp45, sw45 = load_series(path_sw45)
    inp70, sw70 = load_series(path_sw70)
    inps, s45 = load_series(path_s45)
    print("Inputs:")
    for path, inp in ((path_sw45, inp45), (path_sw70, inp70), (path_s45, inps)):
        print(f"  {path.split('/')[-2]}: {describe(path, inp)}")
    print()

    print("Event timeline (battery side):")
    for fw in ("M1", "M2"):
        for p, tag in ((0, "nominal"), (1, "pessimistic")):
            l_mah, l_s = listen_event(fw, p)
            r_mah, r_s, pms = read_event(fw, p)
            s_mah, s_s, _x = read_event(fw, p, pm=False)
            print(f"  {fw} {tag:11s} listen {l_s:4.1f} s {l_mah * 1000:6.1f} uAh | full read {r_s:5.1f} s "
                  f"{r_mah:.3f} mAh (PMS {pms:.3f}) | read without PM {s_s:4.1f} s {s_mah:.3f} mAh")
    ack = ACK_S * (LIGHT_SLEEP_MA + RADIO_RX_MA) * K3 / 3600
    print(f"  M2 receive window after a report, {ACK_S:.0f} s (sensitivity): {ack * 1000:.1f} uAh")
    print()
    print("| Profile | Schedule | Full reads / day | Listens / day | Requests served / day | mAh / day | Wh / day |")
    print("|---|---|---|---|---|---|---|")
    for prof, (fw, p, scheds, ack_s) in PROFILES.items():
        for s in scheds:
            mah, _pms, c = day_load(fw, p, s, ack_s)
            print(f"| {prof} | {s} | {c['reads']:.0f} | {c['listens']:.0f} | {c['served']:.1f} | {mah:.1f} | "
                  f"{mah * V_NOM / 1000:.3f} |")
    mah, _pms, reads = now_load()
    print(f"| M1 now (19.4-min cycle) | today | {reads:.1f} | {reads * 15:.0f} | 0 | {mah:.1f} | "
          f"{mah * V_NOM / 1000:.3f} |")
    for p, tag in ((0, "typical"), (1, "pessimistic")):
        print(f"  Hibernation {tag}: {(FLOOR_UA[p] / 1000 + HIB_CHECK_MAH) * 24:.2f} mAh/day; "
              f"UVLO off: {OFF_UA[p] * 24 / 1000:.2f} mAh/day")
    print()

    december_table(sw45, "45 deg, azimuth 233 deg")
    print()
    december_table(s45, "45 deg south (revision-1 assumption)")
    print()
    for label, trips, reset in (("interlock nominal, reset at night", GATE_NOMINAL, "night"),
                                ("energy corner, reset at night", GATE_CORNER, "night"),
                                ("revision-1 gate +1 / +44 C, stateless", GATE_R1, "retain")):
        days, first = longest_without_charge(sw45, trips, reset)
        print(f"Longest stretch without charging, 45 deg, azimuth 233 deg, {label}: {days:.1f} d from {first}")
    per, coldest = cold_hours(sw45)
    b10 = {k: v[0] for k, v in per.items()}
    b20 = {k: v[1] for k, v in per.items()}
    w10, w20 = max(b10, key=b10.get), max(b20, key=b20.get)
    print(f"Air temperature (PVGIS T2m), 2005/06-2022/23: below -10 C {sum(b10.values()) / len(per):.0f} h per "
          f"winter on average, at most {b10[w10]} h ({w10}/{(w10 + 1) % 100:02d}); below -20 C "
          f"{sum(b20.values()) / len(per):.1f} h, at most {b20[w20]} h ({w20}/{(w20 + 1) % 100:02d}); coldest "
          f"hour {coldest[0]:.1f} C on {coldest[1]}")
    print()

    corner = dict(trips=GATE_CORNER)
    ah8f = 8 * CELL_AH * 0.8
    cases = [
        ("Revision-1 gate: stateless +1 / +44 C", sw45, dict(trips=GATE_R1, reset="retain")),
        ("Interlock nominal (+1.7 off / +2.1 on), reset at night", sw45, {}),
        ("Interlock energy corner (+2.7 / +3.1), reset at night", sw45, corner),
        ("Review sensitivity +1 / +4 C, state kept overnight", sw45,
         dict(trips=(1.0, 4.0, 43.0, 40.0), reset="retain")),
        ("Energy corner, tilt 70 deg", sw70, corner),
        ("Energy corner, panel due south", s45, corner),
    ]
    cols = ("M2 adaptive", "M2 adaptive pessimistic", "M2 adaptive pessimistic, 2 s ACK window",
            "M2 pessimistic", "M1 reads, no listen, pessimistic")
    print("Adaptive profiles: the worst of a charge estimate 15 % low, exact and 15 % high.")
    print(f"| Case (10 W, 45 deg, azimuth 233 deg, 8 cells 20 % faded = {ah8f:.2f} Ah) | " + " | ".join(cols) + " |")
    print("|---" * (len(cols) + 1) + "|")
    for label, rows, kw in cases:
        cells = [fmt_cell(worst_case(rows, prof, ah=ah8f, **kw)[1]) for prof in cols]
        print(f"| {label} | " + " | ".join(cells) + " |")
    print()

    print("Smallest nominal pack with no outage hour in 2005/06-2022/23 (10 W, 45 deg, azimuth 233 deg),")
    print(f"as Ah and as {CELL_AH} Ah cells in parallel, new (and with 20 % capacity fade):")
    print("| Load profile | Interlock nominal | Energy corner | Energy corner, charge estimate off by up to 15 % |")
    print("|---|---|---|---|")
    for prof in ("M1 now (19.4-min cycle)",) + tuple(PROFILES):
        cells = [fmt_ah(required_ah(sw45, prof)), fmt_ah(required_ah(sw45, prof, **corner))]
        if "adaptive" in prof:
            cells.append(fmt_ah(required_ah(sw45, prof, estimate_error=True, **corner)))
        else:
            cells.append("as energy corner (no estimate used)")
        print(f"| {prof} | " + " | ".join(cells) + " |")
    print()

    packs = [(3, 1.0), (3, 0.8), (8, 1.0), (8, 0.8), (14, 1.0), (14, 0.8)]
    print("Pack options at the energy corner (10 W, 45 deg, azimuth 233 deg), each with the charge estimate")
    print("15 % low / exact / 15 % high. Outage days are totals over the 18 winters; lean and survival days")
    print("are per winter.")
    print("| Profile | Pack | Outage days | Lowest charge | Lean d per winter | Survival d per winter |")
    print("|---|---|---|---|---|---|")
    for prof in ("M2 adaptive pessimistic", "M2 adaptive pessimistic, 2 s ACK window", "M2 adaptive"):
        for n, health in packs:
            ah = n * CELL_AH * health
            label = f"{n} cells, {ah:.2f} Ah" + (" (20 % faded)" if health < 1 else "")
            runs, _worst = worst_case(sw45, prof, ah=ah, **corner)
            out = " / ".join(f"{r['out_days']:.0f}" for r in runs)
            socs = " / ".join(f"{r['low_min_soc'] * 100:.0f} %" for r in runs)
            lean = " / ".join(f"{r['lean_days'] / r['n']:.1f}" for r in runs)
            surv = " / ".join(f"{r['surv_days'] / r['n']:.1f}" for r in runs)
            print(f"| {prof} | {label} | {out} | {socs} | {lean} | {surv} |")
    print()

    print("Largest full-read cost (battery side, with PM) that still leaves no outage hour: energy corner,")
    print("charge estimate off by up to 15 %, pessimistic floor and PMS7003 (1.464 mAh per read), the rest of")
    print("every read scaled alike. For comparison, a pessimistic full read costs 1.782 mAh in M2 and 2.791 mAh")
    print("in M1.")
    print("| Pack | Adaptive 15 / 30 / 60 min, no listen | Fixed 15 min, no listen |")
    print("|---|---|---|")
    for n, health in ((8, 1.0), (8, 0.8), (14, 1.0), (14, 0.8)):
        ah = n * CELL_AH * health
        label = f"{n} cells, {ah:.2f} Ah" + (" (20 % faded)" if health < 1 else "")
        a = read_cost_limit(sw45, "M2 adaptive pessimistic", ah, **corner)
        f = read_cost_limit(sw45, "M2 pessimistic", ah, **corner)
        print(f"| {label} | {fmt_mah(a)} | {fmt_mah(f)} |")
    print()

    print(f"Sleep floor at R-P7's limit (b): {FLOOR_LIMIT_UA} uA on the cells instead of {FLOOR_UA[1]} uA.")
    print("M2 adaptive pessimistic at the energy corner, charge estimate 15 % low / exact / 15 % high.")
    print("| Pack | Outage days | Lowest charge | Largest full-read cost, adaptive |")
    print("|---|---|---|---|")
    saved = FLOOR_UA
    FLOOR_UA = (FLOOR_UA[0], FLOOR_LIMIT_UA)
    try:
        for n in (8, 14):
            ah = n * CELL_AH * 0.8
            runs, _worst = worst_case(sw45, "M2 adaptive pessimistic", ah=ah, **corner)
            out = " / ".join(f"{r['out_days']:.0f}" for r in runs)
            socs = " / ".join(f"{r['low_min_soc'] * 100:.0f} %" for r in runs)
            a = read_cost_limit(sw45, "M2 adaptive pessimistic", ah, **corner)
            print(f"| {n} cells, {ah:.2f} Ah (20 % faded) | {out} | {socs} | {fmt_mah(a)} |")
    finally:
        FLOOR_UA = saved
    print()

    ah3 = 3 * CELL_AH
    print(f"Low-energy recovery at the energy corner, today's pack ({ah3:.2f} Ah): hibernation entries, restarts")
    print("into the lowest schedule, UVLO cut-offs (TPS3840) and the longest outage, over 18 winters.")
    print("| Load profile | Hibernations | Restarts | UVLO cut-offs | Longest outage |")
    print("|---|---|---|---|---|")
    no_hib = dict(R2_POLICY, hib_at=None)
    rows = [(prof, prof, {}) for prof in ("M1 now (19.4-min cycle)", "M1 nominal, 1-min listen",
                                          "M1 reads, no listen", "M1 reads, no listen, pessimistic",
                                          "M2 nominal", "M2 pessimistic", "M2 adaptive",
                                          "M2 adaptive pessimistic")]
    rows += [(f"{prof}, firmware never hibernates (TPS3840 only)", prof, dict(policy=no_hib))
             for prof in ("M1 reads, no listen", "M2 pessimistic")]
    for label, prof, kw in rows:
        _runs, r = worst_case(sw45, prof, ah=ah3, **dict(corner, **kw))
        longest = f"{r['longest'][0]:.1f} d from {r['longest'][1]}" if r["longest"][1] else "none"
        print(f"| {label} | {r['hibs']} | {r['restarts']} | {r['trips']} | {longest} |")

if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "codex":
        cmd_codex(sys.argv[2])
    elif len(sys.argv) >= 3 and sys.argv[1] == "r2check":
        cmd_r2check(sys.argv[2])
    elif len(sys.argv) >= 5 and sys.argv[1] == "scenarios":
        cmd_scenarios(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        sys.exit(__doc__)
