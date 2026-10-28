# Zephyr enclosure: printing, tests and hardware

**Status: draft, 27.10.2026.** These are starting values. Replace each filament value with the data sheet of the brand mobric actually uses once it is known (**TBD**). Labels as in `fusion-spec.md` §1.

Revision B (27.10.2026): every part names its bed face, supports and bridges (§ 3), and the radio test is split into LoRa and Wi-Fi (§ 4.8). This file gives instructions only. It is not consent to print, buy, flash or run a hardware test.

---

## 1. Printer: Bambu Lab P2S (decided, 5A)

| Fact | Value | Status |
|---|---|---|
| Build volume | 256 × 256 × 256 | Bambu Lab P2S FAQ (via search) and retailer listings; the official wiki page was not reachable (HTTP 402) |
| Stock nozzle | 0.4 hardened steel; 0.2 / 0.6 / 0.8 also offered | retailer listings (secondary). mobric confirms a hardened nozzle; **its diameter is not assumed** |
| Nozzle max | 300 °C | retailer listings (secondary) |
| Bed max | 110 °C | retailer listings (secondary) |
| Plate | textured PEI (one listing says flexible steel) | retailer listings (secondary) |
| Enclosure | yes, closed | listings; mobric |
| Active chamber heater | **not confirmed**: one retailer says "50 °C chamber", nothing official found | TBD |
| Excluded areas on the plate | **not confirmed for the P2S**. The P1S profile excludes 18 × 28 at the front left (check #15) | **TBD: load the P2S profile in Bambu Studio and look** |
| AMS | not assumed | TBD |

Everything below assumes a **0.4 mm nozzle**. With another diameter, re-derive line widths and wall-loop counts, so that the 2.4 mm box walls stay pure perimeters.

---

## 2. Filaments

Brands are **TBD**. Start from the Bambu Studio system profile for the brand, then apply the changes below.

**White ASA** (all outside parts):
- **Nozzle:** 260 °C (ds [36]: 260 ± 10).
- **Bed:** 100 °C on textured PEI (assumed, inside the 75–110 °C range of ds [35][36][76]; the P2S bed max is 110).
- **Part fan:** 0–20 %; up to 50 % only on bridges and overhangs (ds [36]).
- **Chamber:** door and top closed. Warm up for 10 min with the bed at 100 °C before the print (assumed; there is no confirmed chamber heater).
- **Drying:** 70 °C for 7 h (ds [35], Polymaker; check the brand's sheet).
- **Brim:** 3 mm on parts longer than 150 mm and on the round shield plates. The sources suggest 5 mm for the plates (ds [36][76]), but with a 5 mm brim even 3 plates no longer fit a bed (§ 3).
- **Room:** ventilate it, because ASA releases styrene (ds [37]).

**PETG-CF** (shaded inner parts only, ≥ 15 mm from the antenna keep-out), values from the Bambu PETG-CF data sheet V2 (via a distributor mirror, secondary):
- **Nozzle:** 240–270 °C, hardened.
- **Bed:** 65–75 °C with glue, on a textured PEI, engineering or high-temperature plate.
- **Speed:** < 200 mm/s.
- **Drying:** 65 °C for 8 h; store below 20 % RH.
- **Chamber:** two versions of the sheet give 35–50 °C and 25–45 °C. Use the brand profile as is.
- **Heat:** HDT about 74 °C (secondary [43]), so only below about 55 °C, in shade (assumed).
- If the brand isn't Bambu, use that brand's sheet instead.

**Not for field parts:**
- PLA: HDT 58–60 °C (ds [40]). Jigs and test fits only.
- TPU 95A: pads and sleeves only, never as a seal (ds [24]: 60–70 % compression set at 55–70 °C).

---

## 3. Print table

| Part | Qty | Material | Layer | Walls / infill | Footprint with brim | Notes |
|---|---|---|---|---|---|---|
| `BOX` | 1 | ASA white | 0.16–0.20 | watertight (below) | 248 × 168 | iron the land; seam at X 0 / Y 130 |
| `LID` | 1 | ASA white | 0.20 | watertight, 100 % | 248 × 168 without brim | brim ≤ 2 mm or none; iron the sealing face |
| `RETAINER` | 1 | ASA or PETG-CF | 0.20 | 4 loops, 100 % | 101 × 89 | |
| `ROOF` | 1 | ASA white | 0.20 | 4 loops, 100 % | about 245 × 112 | |
| `CARRIER` | 1 | ASA white | 0.20 | 6 loops, 40 % gyroid | 242 × 130 + mouse ears R ≤ 7 | carries the box; no full brim (242 wide) |
| `ADAPTER_PIPE` | per pole | ASA white | 0.20 | 6 loops, 50 % gyroid | 64 × 100 | |
| `ADAPTER_FLAT` | per wall or post | ASA white | 0.20 | 6 loops, 50 % gyroid | 70 × 130 | |
| `SHIELD_ARM` | 1 | ASA white | 0.20 | 6 loops, 50 % gyroid | about 233 × 116 with a 3 mm brim | length in XY (ds [35]) |
| `SH_PLATE` | 7 | ASA white | 0.20 | solid | Ø126 each with a 3 mm brim | **3 per plate only in a tight triangle** (needs a 247.7 mm square; check in the slicer), else 2 per plate: 2 + 2 + 2 + 1 (check #15) |
| `SH_ROOF` | 1 | ASA white | 0.20 | solid | Ø140 | print choice open (below) |
| `SH_CAP` | 1 | ASA white | 0.20 | solid | Ø130 | |
| `PMS_HOOD` | 1 | ASA white | 0.20 | 6 loops, 5 top / 5 bottom, 20–25 % gyroid | about 100 × 40 (with the ears) | |
| `PMS_CRADLE`, `MESH_RING` | 1 + 2 | PETG-CF or ASA | 0.20 | 4 loops, 30 % | small | shaded |
| Desiccant clip, cable clamps | small | PETG-CF or ASA | 0.20 | 4 loops | small | ≥ 15 from the antenna keep-out |
| Pads, sleeves | small | TPU 95A | 0.20 | — | small | never a seal |

**Bed face, supports and bridges.** This comes from the text, not from a model. Confirm each row in the CAD model and the slicer (§ 4.1) before calling a part printable.

| Part | On the bed | Supports | Bridges and steep faces to check |
|---|---|---|---|
| `BOX` | back wall and the 4 corner tabs; opening up | none | land flange and ear tapers at 45°; round holes in the walls (glands, vent, rib inserts) print sideways, so check the top of each |
| `LID` | outer face | none | none; skirt, lip, ribs and bosses rise from the plate |
| `RETAINER` | either flat face | none | none |
| `ROOF` | the whole flat top face | none | the legs and their screw holes lean 10° from vertical |
| `CARRIER` | back face | none | none; bosses and counterbores open upward |
| `ADAPTER_PIPE` | module face | none | band-tunnel roofs bridge 14; insert-hole ends bridge Ø5.7; V faces at 45° |
| `ADAPTER_FLAT` | **front (module) face**. With the back face down only the 4 pads (Ø14 × 2) would touch | none | insert-hole ends bridge Ø5.7; countersinks at the bed rise at 45° |
| `SHIELD_ARM` | arm, flange and the pad's lower edge; pad standing | none | counterbores in the standing pad print sideways; cable-tie slots bridge |
| `SH_PLATE` | drip skirt (rim) | none | cone underside 50° from vertical, unsupported. The first-plate test decides (§ 4.10) |
| `SH_ROOF` | rim | **likely needed**: the shell's underside is 65° from vertical | open choice for mobric: supports under the shell, or a different form (`fusion-spec.md` § 6.9.2) |
| `SH_CAP` | flat bottom; stem up | none | cradle option (b): bosses stick out of the stem, each with a 45° chamfer underneath |
| `PMS_HOOD` | closed top | none intended | overhangs ≤ 45°; the inner geometry isn't drawn yet |
| `PMS_CRADLE`, `MESH_RING`, small parts | flat | none | none |

**Watertight settings** for `BOX` and `LID` (ds [12]; meas [13][14]; counts assumed):
- 6 wall loops at about 0.42 mm, so the 2.4 mm walls have no sparse infill.
- Flow + 5 % over the calibrated value (or 0.44 mm line width). Nozzle 265–270 °C.
- Layers 0.16–0.20 mm; 6 top and 6 bottom layers.
- 100 % infill in the thick zones: land, ears, ribs, tabs, standoffs.
- If the wall coupon leaks, raise the infill/wall overlap to 25–35 %.
- Seams aligned or painted on the outer vertical edge at X 0, Y 130. Never in the groove or at an entry (meas [13]; ds [12]).

**Bed placement:** keep every part, with its brim, clear of the P2S excluded areas (§ 1). The box and lid are about 248 × 168, which fits with room to spare in Y.

---

## 4. Calibration and tests, in order

1. **Bed fit.**
   - Load every part into Bambu Studio with the P2S profile and brims. Check `BOX`, `LID`, `ROOF`, `CARRIER`, `SHIELD_ARM` and 3 `SH_PLATE` against the plate and the excluded areas.
   - For each part, confirm the bed face, the supports and the bridges in § 3. Record any difference in `cad/NOTES.md`.
2. **Shrinkage.**
   - Print a 150 mm L-bar flat in the same white ASA and measure it after 24 h.
   - Set the filament's "Shrinkage (XY)" to measured / designed × 100 (expect about 99.3–99.6 %, secondary [50]).
   - Don't scale the CAD (check #16, confirmed).
3. **Hole and insert coupon,** printed both flat and in a vertical wall. All sizes are modelled diameters (the hole table in `fusion-spec.md` § 4.1), with slicer hole compensation at 0:
   - M3 insert holes at 4.0 / 4.1 / 4.2;
   - M4 insert holes at 5.6 / 5.7 / 5.8;
   - gland holes at 12.2 / 12.3 / 12.4 and 16.3;
   - the SMA D-hole from the bought pigtail's drawing;
   - the vent hole at 12.2;
   - clearance holes at 3.4 / 4.6, and 2.4 only if cradle option (b) is used.

   Install the inserts at 260–265 °C: melt about 90 % of the way in, then press flush with a flat tool and hold (ds [31]; temperature inferred). Check each for pull-out and spin. Thread a real gland, vent and SMA into their holes.
4. **Foot coupon.**
   - Print a 70 × 70 adapter pad with 4 M4 inserts and a 70 × 70 module pad with counterbored holes.
   - Bolt them with 4 × M4 × 16 + washers at 1.2 Nm. Pass: no insert spins, the faces close flat.
   - Repeat after a night at −20 °C.
5. **Lid section coupon** (check #2):
   - A 75 mm straight piece of box rim with 2 ears 58.5 apart, the groove and the cord, plus the matching lid section with skirt.
   - Screw it down. Measure the gap between lid and land at mid-span with a feeler gauge. Pass: ≤ 0.25 mm and the cord visibly compressed.
6. **Wall coupon.** A 50 × 50 × 50 cup with the box settings, filled with water (or soapy water) overnight (ds [12]).
7. **Box hose and freeze test.**
   - Dry tissue inside, lid screwed down, box hung as mounted with cable stubs in the glands.
   - Spray every face, the lid seam and each gland from about 3 m for 3 min. Freeze at −20 °C overnight, thaw, spray again.
   - Pass: the tissue stays dry. This is an IPX5-like check, not a certification (secondary [64]).
8. **Radio, two separate tests.** Each one runs only under the consents that already cover flashing, OTA and hardware tests; this instruction is not one of them.
   - **LoRa 868 MHz** (SX1276, external antenna on the SMA bulkhead): read the RSSI and SNR of the station's packets at the master node, which is the LoRa gateway. Compare the board in the closed printed box with open air, the box on the real pole, with the same antenna, position and radio settings.
   - **Wi-Fi 2.4 GHz** (the ESP32's PCB antenna inside the box): read the Wi-Fi RSSI at the access point, or the ESP32's own reading of the access point, using the same side for both runs. Compare the closed box with open air.
   - **OTA:** confirm a Wi-Fi OTA update goes through the closed box, but only once OTA itself is allowed.
9. **PMS hood.** Measure the ports, set the port-face plate, print, and run the smoke test: match smoke 5 cm below the mesh must raise the reading within about 10 s (ds [102]); smoke at the outlet should raise it much less.
10. **Shield.**
    - One plate first: check warp, overhang quality and boss height.
    - Then the stack: compare the reading against a reference thermometer at night with wind above 2 m/s (ds [93]).
    - After the first hard rime, check that the gaps stay open.
11. **First summer:** log the pack temperature (DS18B20). If it passes 38 °C, fit the side shade. 38 °C is the trigger for the shade, not proof that the cells are protected.
12. **First winter:** log the pack against the air, and the outer-to-inner cell gradient [P1 D13].

---

## 5. Hardware list

No prices were sourced. The figures are rough 2026 hobby-shop estimates (assumed).

| Item | Size or part number | Qty | Use | Rough price |
|---|---|---|---|---|
| Solid EPDM cord | 3.0 mm, 70 Shore A (alt. 50–60 Shore A if the lid check fails) | 1–2 m | lid seal | €3–8 |
| Cable gland | Lapp SKINTOP ST-M M12x1.5 black, 53111200 (ds [53]) | 6 | 5 in the floor, 1 in the shield cap | €10–18 |
| Cable gland (optional) | Lapp ST-M M16x1.5 black, 53111210 | 1 | Cat5e if its OD > 7 | €2–4 |
| Locknuts | Lapp SKINDICHT SM-M M12 / M16 (ds [54]) | 6–7 | inside the glands | €3–6 |
| Blanking plug | M12x1.5 | 1 | spare vane gland | €1 |
| Gland sealing washers | Lapp ring or 1 mm EPDM | 6 | outside each gland | €2–5 |
| Pressure vent | Gore PolyVent Standard M12x1.5 PMF100320 + nut M10510-009 (ds [55]) | 1 | box breathing | €5–12 |
| SMA pigtail | u.FL to SMA(f) bulkhead with O-ring, 1.37 mm, 150–250 mm (Taoglas CAB.01052 class, ds [61]) | 1 | 868 MHz; **keep its drawing for `sma_D`** | €3–10 |
| M3 inserts | ruthex or CNC Kitchen M3 × 5.7, OD 4.6 (ds [27][28]) | 32 (+ spares) | lid 14, PCB 4, retainer 2, roof 4, hood 2, clip 2, side shade 4 | €10–15 / 100 |
| M4 inserts | ruthex M4 × 8.1, OD 6.3 | 12 (+ spares) | carrier spacers 4, each adapter 4 | €8–12 / 50 |
| Lid screws | M3 × 10 ISO 7380 A2 + washers | 14 (+ 2) | lid | €4–6 |
| Roof screws | M3 × 35 and M3 × 40 A2 + washers | 2 + 2 | roof | €2 |
| Short screws | M3 × 8 ISO 7380 A2 (no washer); M3 × 10 A2 + 2 washers; M3 × 6 A2 | 2 + 2 + 2 | retainer; PMS hood; desiccant clip | €1–2 |
| Nylon screws | M3 × 6 | 4 | PCB | €1 |
| Nylon screws and nuts | M2 × 6 + M2 nuts | 2 + 2 | BME680 board, only for cradle option (b) | €1 |
| Box to carrier | M4 × 20 DIN 912 A2 + DIN 125 washers | 4 + 4 | box | €2 |
| Foot bolts | M4 × 16 DIN 912 A2 + DIN 125 washers | 4 per module | carrier, shield arm | €2–3 |
| Fixing screws | 5 mm A2 countersunk wood screws (+ 6–8 mm plugs for a wall), length **TBD** | 4 per flat adapter | wall or post | €2–4 |
| Hose clamps | all-stainless worm drive, 12 mm band, range from the CAD band path (about 60–80 mm for a 33.7 pipe) | 2 per pipe adapter | pipe | €4–10 |
| Threaded rod | M4 A2, 1 m | 1 | 3 shield rods of about 205 | €3–5 |
| Rod fittings | M4 A2 nuts, washers, wing nuts | 6 + 6 + 3 | shield | €2–4 |
| Foam | 10 mm closed-cell XPS (ds [11]) or closed-cell PE | 1 small sheet | battery compartment | €3–8 |
| Foam tape | 2–3 mm closed-cell EPDM | 1 roll | PMS divider seal | €3–6 |
| Silica gel | 10 g indicating sachets | 10 | yearly swap | €5–8 |
| Mesh | 40-mesh 304 woven, 0.50 mm aperture (ds [107]) | 100 × 100 mm | PMS inlet and outlet | €3–8 |
| PMS lead | round jacketed 4-core, OD 3.5–7 (e.g. LiYY 4 × 0.14, about 4.5 mm) | 0.5 m | hood to box (check #21) | €2 |
| Cable ties | UV-stabilised | 20 | every 0.3 m | €3 |
| Masking tape | silicone-free (check the adhesive) | 1 | BME680 during coating (ds [82]) | €3–5 |

**Stainless grade:**
- A2 (304) for screws, nuts and washers.
- A4 (316) for the hardware outside if the pole is within road-salt splash (secondary [51][52]).
- No zinc-plated steel.
