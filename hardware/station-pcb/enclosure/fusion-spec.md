# Zephyr enclosure: Fusion 360 spec for Astra

**Status: draft, 27.10.2026.** Written by the enclosure session (`pcb-caseing`) for mobric's Fusion 360 agent Astra. Concept decisions 1A–5A are mobric's (relayed by the coordinator on 27.10.2026). Dimensions still need the design check and the measurements marked **TBD**. The PCB designer answered on the board interface and the BME680 cable on 27.10.2026. Both answers are a starting point, not agreed geometry (§ 4.3a, `pcb-interface.md`). The coordinator reviewed the text on 27.10.2026; that review didn't check CAD, a slicer or the sources. Nothing here is approved for printing yet.

Revision A (27.10.2026, at mobric's request), from mobric's PMS7003 drawing and BME680 product photo:
- the PMS hood keeps room for the plug on the sensor's big face (`pms_plug_clr`, § 6.10);
- the shield cradle is sized from `brd_*` (about 18 × 16), with an M2 nylon-screw option (§ 6.9).

Revision B (27.10.2026), after the coordinator's text review of draft A:
- the PCB designer's answers are in. What was answered stays apart from what is agreed, tested or written into F1 (§ 2, 4.3a, 8, 11);
- the antenna edge and the module position are working alternatives, checked as 3D bodies in CAD (§ 4.3, 4.3a, 5, 9);
- one rule for `hole_add`, with a table of modelled hole sizes (§ 3.2, 4.1);
- every part names its bed face, supports and bridges, to confirm in CAD and the slicer (`print-and-test.md` § 3). The flat adapter now prints front face down;
- the radio test is split into LoRa and Wi-Fi (`print-and-test.md` § 4.8);
- export gates per part. The shield cap and the PMS parts wait for their own measurements, without holding up the rest of the text (§ 9).

Read with:
- `print-and-test.md`: P2S print settings, test coupons, hardware list.
- `pcb-interface.md`: the board outline proposed to the PCB designer, the answer, and the status of each item.
- `research/`: the research brief and number check behind the values ([n] = brief §8 source n).

---

## 1. Labels

Every number carries a label:
- **ds**: datasheet, standard or maker's guide.
- **meas**: a third-party measurement.
- **calc**: computed here or in the number check.
- **assumed**: engineering judgement; change it if you have a reason.
- **decided**: mobric's decision; don't change without asking.
- **proposal**: waits for the PCB designer.
- **TBD**: a measurement or part choice still missing. Model it as a parameter with the default shown.
- **coupon**: confirm on a test print before the real part (`print-and-test.md` §4).
- **(secondary)**: the finding behind the number was not read at its source.

---

## 2. System

Four modules, all white ASA outside (decision 5A):

| Module | What it is | Mounts with |
|---|---|---|
| **A. Box** | Sealed electronics and battery box with lid, battery compartment and roof cap | Box carrier → standard foot → adapter |
| **B. PMS7003 hood** | Open-bottom hood under the box floor | 2 × M3 into the box's floor ribs |
| **C. Radiation shield** | 7-plate stack for the BME680 breakout | Shield arm → standard foot → adapter |
| **D. Standard foot and adapters** | One bolt pattern, 4 × M4 on a 50 × 50 square (decision 1A), and two adapters: pipe (V-saddle with hose clamps) and flat (wall or square post) | — |

Decisions that shape the CAD:
- **1A** common foot, 4 × M4 on 50 × 50, adapters for pipe, wall and square post.
- **2A** BME680 Cat5e 1.5–2 m, shield at least 0.5 m from the box. The shield is therefore a separate module on its own arm, never hung under the box.
  - The PCB designer's calc (27.10.2026): 1.5–2 m works without a buffer at 100 kHz, with ≤ 250 pF per line, 3.3 kΩ pull-ups on the board and TVS ≤ 5 pF.
  - That is a calc, not a test of the real cable and breakout; F6 measures them.
  - D8 in the F1 documents still says < 1 m. It changes only in a later F1 revision, with mobric's consent.
- **3A** USB-C only with the lid off. There is no USB opening in the box.
- **5A** Bambu Lab P2S with a hardened nozzle. White ASA outside, PETG-CF only for shaded inner parts.

**How the foot works.** The adapter holds the threads (4 × M4 heat-set inserts). The module has 4 clearance holes, and the bolts go in from the module side. So the adapter goes on the pipe or wall first, with full access, and every module bolts on and comes off from the front. The box has a sealed back wall and prints back-down, so it can't carry the foot itself. A separate **box carrier** takes the box's 4 corner tabs and presents the foot.

---

## 3. Frames and global rules

### 3.1 Frames
- Units: mm, degrees.
- **Box frame** (box, lid, roof, carrier, battery parts, PMS hood):
  - Origin at the inner bottom-left-back corner of the box, seen from the lid.
  - **X** runs left to right, from the battery end (X = 0) to the PCB end (X = `in_W`).
  - **Y** runs up.
  - **Z** runs from the inner face of the back wall toward the lid. The box opening (sealing land) is at Z = `in_D`.
- **Adapter frame**: origin at the centre of the foot pattern on the module contact face. Z points away from the module (toward the pipe or wall), and Y points up.
- **Shield frame**: origin on the shield axis at the top face of the arm flange, Z up.

### 3.2 Global rules
- **Holes:** every diameter in § 4 is the value Astra models. Never add anything on top of it.
  - A hole that must fit a bought part (an insert, the SMA bulkhead) is written as nominal + `hole_add` (0.1, meas [30]), so the add is already inside the parameter.
  - Clearance holes for screws, rods and fixings are modelled as given, with no add.
  - The Gore vent hole is modelled at nominal (§ 6.5). The gland holes are modelled at the value the coupon picks.
  - In Bambu Studio leave "X-Y hole compensation" at 0 (secondary [48][49]), so nothing is compensated twice.
  - The hole table in § 4.1 lists every hole.
- **Growth:** positions in § 6 are written as numbers for the default box (inside 210 × 130 × 70). Tie every position on the PCB end and the top to `in_W` and `in_H` (for example the right-hand ears at `in_W + ear_off`), so the growth test in § 9 rebuilds.
- **Fits between printed parts:** `fit_xy` = 0.25 per side in XY and `fit_z` = 0.4 in Z (ds [47]). Print mating parts in the same filament and orientation (ds [47]).
- **Cold:**
  - No snap-fits for structure or sealing; screws only.
  - Load-bearing inner corners R ≥ `r_load`. Nothing that flexes under 2 mm thick.
  - ASA notched impact falls from 17 to 4.0 kJ/m² between 23 °C and −30 °C (ds [44]).
- **Loads:**
  - Keep load paths in the print's XY plane.
  - Bosses standing up in Z get `r_root` root fillets and gussets.
  - Printed ASA is 43.8 MPa in XY and 32 MPa in Z (ds [35]).
- **Surfaces:**
  - Smooth outer faces. No text, logos or grooves on any upward-facing outside face (meas [80], secondary).
  - Markings go on side faces or inside.
- **Antenna:** no metal, cell, cable or carbon-filled part inside the ESP32 antenna keep-out body (§ 5).
- **Heat-set inserts:**
  - Blind holes only.
  - No insert hole may break through a sealed wall of the box.

---

## 4. User parameters

Create these as Fusion user parameters with these exact names. Values are defaults; the status column says how firm each one is.

### 4.1 Global

| Name | Value | Status | Note |
|---|---|---|---|
| `hole_add` | 0.1 | meas [30] | used only inside `ins3_D`, `ins4_D`, `sma_D` and `sma_flat`; never added again |
| `fit_xy` | 0.25 | ds [47] | per side |
| `fit_z` | 0.4 | ds [47] | |
| `clr_M3` | 3.4 | assumed | M3 clearance hole, modelled as is, no `hole_add` |
| `clr_M4` | 4.6 | assumed | M4 clearance hole, modelled as is, no `hole_add` |
| `cb_M4_D` | 10 | calc | counterbore for a DIN 912 M4 head (Ø7.0) **with** its DIN 125 washer (Ø9) + 1 |
| `r_load` | 1.0 | assumed | minimum inner fillet, load-bearing |
| `r_root` | 1.5 | assumed | boss and gusset root fillet |

**Hole table.** "Modelled" is what Astra draws. The coupon steps are modelled values too (`print-and-test.md` § 4.3).

| Hole | Parameter | Nominal | `hole_add` | Modelled | Coupon steps |
|---|---|---|---|---|---|
| M3 insert | `ins3_D` | 4.0 (ruthex) | included | 4.1 | 4.0 / 4.1 / 4.2 |
| M4 insert | `ins4_D` | 5.6 (ruthex) | included | 5.7 | 5.6 / 5.7 / 5.8 |
| SMA D-hole | `sma_D` / `sma_flat` | from the bought part (WE default 6.5 / 5.85) | included | 6.6 / 5.95 | the bought part |
| M2 clearance (cradle option b) | `brd_hole_D` | — | none | 2.4 | 2.4, only if option (b) is used |
| M3 clearance | `clr_M3` | — | none | 3.4 | 3.4 |
| M4 clearance | `clr_M4` | — | none | 4.6 | 4.6 |
| M4 shield rods | `rod_hole` | — | none | 4.6 | as the M4 clearance |
| 5 mm fixing screws | `fix_D` | — | none | 5.3 | — |
| M12 / M16 gland | `gl12_D` / `gl16_D` | — | none; the coupon picks the modelled value | 12.3 / 16.3 | 12.2 / 12.3 / 12.4; 16.3 |
| Gore vent | `vent_D` | 12.2 (ds [55]) | none | 12.2 | 12.2 |
| Shield cap drains | `drain_D` | — | none, not a fit | 5 | — |
| PCB holes | `pcb_hole_D` | made by the board maker | — | in `REF` only, never printed | — |

Pockets and fits between printed parts use `fit_xy` / `fit_z`, `pms_clr` or `brd_clr`, never `hole_add`.

### 4.2 Box, lid, inserts

| Name | Value | Status | Note |
|---|---|---|---|
| `in_W` | 210 | calc / assumed | inside X |
| `in_H` | 130 | calc / assumed | inside Y |
| `in_D` | 70 | calc / assumed | inside Z, back wall to land |
| `wall` | 2.4 | meas [14], ds [13] | all box walls, fully solid |
| `corner_R` | 4 | calc | inner vertical corners |
| `land` | 10 | assumed | sealing land width from the inner face |
| `land_flat` | 0.3 | assumed | land flatness |
| `groove_off` | 5 | ds [17][18] | groove centreline from the inner face |
| `groove_w` | 4.0 | ds [17][18] | |
| `groove_d` | 2.2 | ds [17][18] | 0.8 squeeze = 27 %, 80 % fill (calc, confirmed by the number check) |
| `groove_R` | 9 | ds [20] | centreline corner radius, 3 × cord |
| `cord` | 3.0 | ds [17][21] | solid EPDM, 70 Shore A |
| `ear_off` | 12 | calc | lid screw centres from the inner face |
| `ear_D` | 8 | ds [27] | screw ear boss |
| `lid_t` | 4.5 | calc (check #2) | was 3.2; the lid must not bow between screws |
| `skirt_h` | 6 | calc (check #2) | perimeter stiffening skirt on the lid |
| `skirt_t` | 2.4 | assumed | |
| `skirt_gap` | 0.5 | assumed | skirt to ears and land |
| `lip_t` | 1.6 | assumed | locating lip on the lid |
| `lip_h` | 4 | assumed | |
| `ins3_D` | `4.0 + hole_add` (4.1) | ds [27] + `hole_add` | M3 × 5.7 insert hole (ruthex: hole 4.0, OD 4.6, L 5.7, wall ≥ 1.6) |
| `ins3_L` | 6.7 | ds [27][31] | blind, straight, no chamfer |
| `ins3_L_rib` | 7.5 | calc | roof inserts in the top ribs only: the roof screws reach 6.45 deep, so 6.7 left only 0.25 spare. 7.5 still leaves 0.5 of rib plus the 2.4 wall below the hole |
| `boss3_D` | 8 | ds [27] | wall (8 − 4.1) / 2 = 1.95 ≥ 1.6 |
| `rib_w` | 10 | assumed | outer ribs |
| `rib_h` | 8 | assumed | rib height proud of the wall |
| `tab_W` | 14 | assumed | corner tab X |
| `tab_H` | 20 | assumed | corner tab Y |
| `tab_T` | 11 | assumed | corner tab Z |

### 4.3 PCB envelope (proposal, see `pcb-interface.md`)

| Name | Value | Status | Note |
|---|---|---|---|
| `pcb_W` | 100 | proposal | |
| `pcb_H` | 80 | proposal | |
| `pcb_t` | 1.6 | proposal | |
| `pcb_hole_in` | 4 | proposal | hole centres from the edges, 92 × 72 pattern |
| `pcb_hole_D` | 3.2 | proposal | |
| `standoff_h` | 15 | assumed | back wall to the PCB rear face |
| `standoff_D` | 8 | assumed | |
| `pcb_X0` | 108 | assumed | PCB left edge in the box frame |
| `ant_overhang` | 6.5 | **working alternative**, not agreed (§ 4.3a) | 0 = antenna flush, copper cut away beside and under it; 6–7 = overhanging the top edge. 6.5 is the box's worst case |
| `pcb_Y0` | `35 - ant_overhang` | calc (check #14) | keeps the antenna top at Y 115 in both cases (28.5 at the working default) |
| `ant_Xc` | `pcb_X0 + 60` | **working alternative**, not agreed (§ 4.3a) | antenna centre X; the PCB designer places the module in F3 |
| `ant_W` | 18 | ds (module 18 × 25.5 × 3.1) | antenna zone width |
| `ant_H` | 7 | assumed | antenna zone height |
| `ant_T` | 3.1 | ds | module height above the PCB |
| `keepout` | 15 | ds [1] | Espressif: at least 15 mm in every direction |
| `front_max` | 20 | assumed | tallest part on the PCB front. The PCB designer expects pluggable terminals with their plugs at about 12–18 |

### 4.3a Antenna and board: working alternatives (not agreed)

The PCB designer answered on 27.10.2026 (`pcb-interface.md`). That answer is a starting point, not agreed geometry: the outline, the module position and the antenna edge are settled in F3, then go to mobric through the coordinator. Until then the model carries every alternative below and must rebuild at each one (§ 9). The working defaults only pick one case to model first. Neither designer has agreed to them.

| Parameter | Working default | Alternatives to rebuild | Status and source |
|---|---|---|---|
| `ant_overhang` | 6.5 | 0 (flush) | The PCB designer: leave room for the overhanging antenna (about 6–7 past the edge, free space around it). It is the worst case for the box. The choice belongs to F3 and D2. At 6.5 the PCB's bottom edge drops to Y 28.5, leaving 28.5 under it for the wires to the glands (35 at 0). |
| `ant_Xc` | `pcb_X0 + 60` | `pcb_X0 + 64`, `pcb_X0 + 66` | + 66 was the first proposal and + 64 the draft's own fix. The PCB designer suggests about + 60, or a metal-free standoff in the top-right corner. 3D text calc of the top-right insert's brass to the antenna zone: 24.8 / 20.8 / 18.8. |
| Top-right standoff | M3 insert (as the other three) | metal-free standoff, method **TBD** | Needed only at + 66 (18.8 is under 20). |
| Box growth (the "+20 mm" margin) | inside 210 × 130 × 70 | `in_W` up to 230, `in_H` up to 150 | The enclosure session offered it, and the PCB designer asked to keep it in the model. It means the model must rebuild if F3's outline is larger. The box isn't bigger now. |

The distances in this spec are 3D text calcs. The CAD measures them between solid bodies (§ 5, § 9), and its numbers replace these.

### 4.4 Battery compartment

| Name | Value | Status | Note |
|---|---|---|---|
| `comp_W` | 101 | calc (check #20) | was 100; zero slack before |
| `comp_H` | 89 | calc (check #20) | |
| `comp_D` | 63 | calc (check #20) | |
| `foam` | 10 | calc model (secondary) | closed-cell XPS or PE, no thicker |
| `divider_t` | 2 | assumed | |
| `retainer_t` | 2 | assumed | |

### 4.5 Roof cap

| Name | Value | Status | Note |
|---|---|---|---|
| `roof_X0` | -14.4 | calc | 12 past each end wall's outer face |
| `roof_W` | 238.8 | calc | the lid (247.8) sticks out 4.5 past each roof end; the seal line (X −5 to 215) stays covered |
| `roof_Z0` | -5 | calc | |
| `roof_D` | 104.5 | calc | 25 past the lid face (lid face at Z 74.5) |
| `roof_t` | 3.0 | assumed | |
| `roof_fall` | 10 | assumed | degrees, falling toward the lid |
| `leg_D` | 10 | assumed | |
| `leg_front_h` | 25 | calc | at Z 40; raised 5 over the brief to clear the lid skirt |
| `leg_back_h` | 30 | calc | at Z 12 |
| `roof_rib_max` | 5 | calc (check #6) | underside rib height |
| `roof_rib_endZ` | 46 | calc (check #6) | underside ribs end at Z ≤ 46 |

### 4.6 Entries

| Name | Value | Status | Note |
|---|---|---|---|
| `gl12_D` | 12.3 | **TBD, coupon** (check #10 unsupported) | Lapp gives no hole size; coupon 12.2 / 12.3 / 12.4 |
| `gl16_D` | 16.3 | **TBD, coupon** | only if the Cat5e is thicker than 7 mm |
| `sma_D` | `6.5 + hole_add` (6.6) | **TBD** (check #11) | replace 6.5 with the drawing of the pigtail actually bought; the default is the WE part |
| `sma_flat` | `5.85 + hole_add` (5.95) | **TBD** (check #11) | WE 5.85, as above |
| `vent_D` | 12.2 | ds [55] | nominal; **no** `hole_add` (12.3 is at Gore's limit) |
| `vent_flat` | 20 | ds [55] | flat area diameter around the vent |

### 4.7 Standard foot, adapters, carrier, shield arm

| Name | Value | Status | Note |
|---|---|---|---|
| `foot_p` | 50 | decided (1A) | bolt square |
| `foot_pad` | 64 | assumed | minimum pad size on both sides |
| `ins4_D` | `5.6 + hole_add` (5.7) | ds + `hole_add` | ruthex M4 × 8.1: hole 5.6, OD 6.3, L 8.1, wall ≥ 2.1 (3DJake table; columns read as in the M3 row) |
| `ins4_L` | 9.1 | calc | insert length + 1 |
| `boss4_D` | 12 | calc | ≥ 5.7 + 2 × 2.1 = 9.9 |
| `mod_bear` | 8 | calc | module pad thickness under the bolt head; sets M4 × 16 everywhere |
| `blk_W` | 64 | calc | pipe adapter block X |
| `blk_H` | 100 | calc | pipe adapter block Y |
| `blk_D` | 42 | calc | pipe adapter block Z |
| `v_angle` | 90 | assumed (secondary [65]) | V-saddle angle |
| `v_mouth` | 56 | calc | V width at the mouth |
| `pipe_min` | 25 | assumed | |
| `pipe_max` | 60 | calc | 90° V with a 56 mouth: contact at r/√2 ≤ 21.2 |
| `band_w` | 14 | assumed | slot for a 12 mm hose-clamp band |
| `band_t` | 3 | assumed | |
| `band_Y` | 40 | calc | band slot centres at Y ± 40 |
| `flat_W` | 70 | assumed | flat adapter |
| `flat_H` | 130 | assumed | |
| `flat_t` | 12 | calc | 9.1 insert depth + 2.9 behind |
| `fix_D` | 5.3 | assumed | for 5 mm wood or plug screws |
| `fix_csk` | 10.5 | assumed | 90° countersink |
| `fix_px` | 30 | assumed | fixing screw pattern X |
| `fix_py` | 110 | assumed | fixing screw pattern Y |
| `car_t` | 6 | assumed | carrier plate |
| `car_gap` | 10 | assumed (secondary) | air gap from the box back to the carrier |
| `car_pad_t` | 14 | calc | carrier foot pad |
| `spacer_D` | 12 | assumed | carrier spacer bosses |
| `arm_L` | 160 | assumed | pad face to shield axis |
| `arm_w` | 20 | assumed | |
| `arm_h` | 25 | assumed | |
| `arm_pad_t` | 12 | calc | |
| `spoke_w` | 14 | assumed | |
| `spoke_t` | 6 | assumed | |

### 4.8 Radiation shield

| Name | Value | Status | Note |
|---|---|---|---|
| `n_plates` | 7 | ds [69][70] | identical plates, one STL |
| `D_outer` | 120 | ds [69][70]; meas [71][72] | |
| `D_inner` | 72 | ds [69][70]; meas [71][72] | |
| `pitch` | 20 | ds [69]; meas [71] | allowed 18–25 |
| `plate_t` | 2.4 | ds [75][76] | solid |
| `slope` | 40 | calc | cone down and outward; drop 20.1 = one pitch |
| `drip_h` | 4 | assumed (secondary) | vertical skirt at the outer lip |
| `sh_roof_D` | 130 | secondary [73]; assumed | |
| `sh_roof_t` | 3.2 | assumed | |
| `sh_roof_slope` | 25 | assumed | |
| `BC` | 96 | secondary [72] | rod bolt circle, 3 rods at 120° |
| `rod_hole` | 4.6 | assumed | M4 rods |
| `boss_D` | 10 | calc | built-in spacer bosses at r = 48 |
| `boss_h` | 16.9 | calc | = pitch − plate_t / cos(slope) |
| `cap_D` | 120 | secondary | bottom cap |
| `cap_fall` | 10 | assumed | cap top falls outward |
| `cap_gland_r` | 20 | assumed | M12 gland position |
| `drain_D` | 5 | assumed | 4 drains |
| `drain_r` | 54 | assumed | |
| `brd_W` | 18 | **TBD** (caliper) | BME680 breakout. About 18 × 16 from the caption of mobric's product photo (27.10.2026, a CJMCU-680 type), not measured |
| `brd_H` | 16 | **TBD** (caliper) | |
| `brd_t` | 1.6 | **TBD** (caliper) | board thickness |
| `brd_clr` | 0.3 | assumed | per side in the fork pocket |
| `brd_hole_D` | 2.4 | assumed | clearance in the cradle bosses for M2 nylon screws, modelled as is. The board has 2 mounting holes; their size isn't measured, and M2 is assumed from the photo (**TBD**) |
| `brd_hole_dx` | 10 | **TBD**, placeholder | X offset between the 2 holes. In the photo they sit diagonally (one top-right, one mid-left) |
| `brd_hole_dy` | 6 | **TBD**, placeholder | Y offset between the 2 holes |
| `cradle_W` | `brd_W + 2 * brd_clr` | calc | fork pocket |
| `cradle_H` | `brd_H + 2 * brd_clr` | calc | |
| `cradle_t` | `brd_t + 2 * brd_clr` | calc | board slot |

### 4.9 PMS7003 hood

| Name | Value | Status | Note |
|---|---|---|---|
| `pms_L` | 48 | ds [102] | sensor envelope |
| `pms_W` | 37 | ds [102] | |
| `pms_T` | 12 | ds [102] | |
| `pms_clr` | 0.3 | assumed | pocket 48.6 × 37.6 × 12.6 |
| `port_gap` | 10 | meas [106] | port face above the mesh plane |
| `pms_plug_clr` | 12 | assumed, **TBD** | free depth in front of the 37 × 48 face at the 10-pin connector, for the plug and the cable bend. Set from the real plug and cable |
| `hood_skirt` | 15 | assumed (meas [110] scaled) | skirt below the mesh |
| `hood_ear_t` | 4 | calc (check #5) | with M3 × 10: 10 − 4 − 0.5 = 5.5 mm engagement |
| `mesh_ap` | 0.5 | ds [107] | 40-mesh 304 woven, 57 % open |

---

## 5. Reference bodies (model first, never print)

Put them in a component `REF` and run an interference check against every printed body at the end.

1. **PCB envelope:** `pcb_W` × `pcb_H` × `pcb_t` at X `pcb_X0`, Y `pcb_Y0`, rear face at Z = `standoff_h`. Front parts zone: the same outline, `front_max` deep in front of the PCB.
2. **Antenna zone:**
   - X `ant_Xc ± ant_W/2`, Y 108–115, Z from the PCB front face (16.6) to `+ ant_T`.
   - If `ant_overhang` > 0, the zone still ends at Y 115 because `pcb_Y0` drops.
3. **Antenna keep-out:**
   - A solid 3D body: the antenna zone grown by `keepout` in every direction.
   - X `ant_Xc ± (ant_W/2 + keepout)` (144–192 at the working default), Y 93–130, Z 1.6–34.7.
   - Only the PCB itself (copper cut away under the antenna, the PCB designer's job), the nylon screws and solid ASA walls may touch it.
4. **Battery pack:** 80 × 42 × 68 (cells vertical, 68 along Y), centred in the compartment inside the foam [P1 D13].
5. **Gland wrench circles:** Ø24 for M12 and Ø28 for M16, on the floor, both faces.
6. **Test pipes:** Ø25 and Ø60 in the pipe adapter V, to check contact and band path.
7. **Metal bodies:**
   - Every insert as a cylinder of its OD × length, every screw, nut and washer, the SMA bulkhead, and the cell pack, each at its real position.
   - Measure the 3D minimum distance from each one to the antenna zone in CAD (§ 9). The text calcs don't count as this check.

---

## 6. Modules, feature by feature

### 6.1 Box shell (component `BOX`)

1. **Shell.**
   - Inside block `in_W` × `in_H` × `in_D`, inner vertical corners `corner_R`.
   - Walls, floor, top and back all `wall` thick, fully solid.
   - Outside: 214.8 × 134.8, depth `in_D + wall` = 72.4.
2. **Sealing land** at Z = `in_D`:
   - Flat, `land` wide from the inner face (7.6 outboard of the wall). Land outline 230 × 150.
   - Supported by a flange 5 thick at its outer edge with a 45° chamfer back to the wall (occupies Z 57–70 outside). It prints without supports.
3. **Groove** in the land:
   - Centreline `groove_off` from the inner face, `groove_w` × `groove_d`, centreline corner radius `groove_R`.
   - Centreline length about 705 (cord length, calc).
   - No seam, label or feature on the land or the rim.
4. **Lid screw ears:**
   - 14 bosses Ø`ear_D`, flush with the land, 45° taper underneath (Z 46–70 outside).
   - Centres `ear_off` from the inner face, a 234 × 154 rectangle:
     - long sides (Y = −12 and Y = 142) at X = −12, 46.5, 105, 163.5, 222;
     - short sides (X = −12 and X = 222) at Y = −12, 39.3, 90.7, 142.
   - Insert hole Ø`ins3_D` × `ins3_L`, blind.
   - Pitch is 58.5 on the long sides; see § 6.2 for the stiffness check.
5. **Corner tabs** (box-to-carrier fixing):
   - 4 tabs, `tab_W` × `tab_H` × `tab_T`, in the back-wall plane (Z −2.4 to 8.6), on the outside of the two end walls.
   - Centres at X = −9 and 219, Y = 10 and 120.
   - Ø`clr_M4` through-hole along Z. Gusset each tab to its end wall.
   - The tabs lie on the bed when the box prints.
6. **Top ribs** (roof):
   - 2 ribs `rib_w` wide, `rib_h` proud, at X = 12 and 200, running Z −2.4 to 45. They stand vertical in print.
   - M3 inserts from the top at Z = 12 and Z = 40, hole Ø`ins3_D` × `ins3_L_rib`.
7. **Floor ribs** (PMS hood):
   - 2 ribs at X = 8 and 97, same size, running Z −2.4 to 45.
   - M3 inserts from below at Z = 22.
8. **PCB standoffs:**
   - 4 × Ø`standoff_D` × `standoff_h` on the back wall's inner face at the PCB hole centres: (`pcb_X0 + pcb_hole_in`, `pcb_Y0 + pcb_hole_in`) and the other three corners of the 92 × 72 pattern.
   - Each has an M3 insert hole Ø`ins3_D` × `ins3_L` and two 3 mm ribs to the back wall.
   - **M3 × 6 nylon screws** (assumed).
   - The top-right insert's brass (Ø4.6) must stay ≥ 20 from the antenna zone, measured in 3D in CAD.
   - 3D text calc: 24.8 at `pcb_X0 + 60`, 20.8 at + 64, 18.8 at + 66. At + 66 that corner needs the metal-free standoff instead (§ 4.3a).
9. **Battery compartment walls:** see § 6.3.
10. **Floor entries and vent:** see § 6.5.
11. **Desiccant:** nothing in the box; the clip is on the lid (§ 6.2).

### 6.2 Lid (component `LID`)

1. **Plate:**
   - `lid_t` thick.
   - Outline is the box's ear outline grown by `skirt_gap + skirt_t`: about 247.8 × 167.8.
   - Corners concentric with the corner ears: skirt inner R = `ear_D/2 + skirt_gap`.
2. **Perimeter skirt:**
   - `skirt_t` thick, `skirt_h` deep, hanging from the plate toward the box, all round.
   - Clears the ears and the land by `skirt_gap`.
   - It stiffens the lid edge between screws (check #2) and is also the drip edge.
3. **Locating lip:**
   - `lip_t` thick, `lip_h` tall, running inside the box opening with `fit_xy` per side.
   - It must stay inside the groove line, never on the cord.
4. **Screw holes:**
   - 14 × Ø`clr_M3` at the ear positions.
   - **M3 × 10** ISO 7380 A2 (calc: 10 − 4.5 − 0.5 washer = 5.0 engagement, hole 6.7).
   - Hand driver, ≤ 0.5 Nm (assumed; M3 stripped PETG at about 1 Nm, meas [32]).
5. **Inner ribs:**
   - Two ribs 5 deep along X at Y 45 and 85, over X 106–204 only (assumed).
   - Over the battery compartment they would reach the retainer face (Z 65) and its screw heads.
   - They must clear the PCB front zone (Z ≤ 36.6). The lid's inner face is at Z 70.
6. **Desiccant clip seat:**
   - X 10–60, Y 95–125 on the inner face.
   - 2 bosses Ø8, 3.5 proud, with M3 inserts (6.7 deep in 8.0). A 6.7 hole doesn't fit the 4.5 lid alone.
   - Keep ≥ 5 clear of the parts above the battery shelf (fuse holder, protection board; **TBD**).
7. **Stiffness check (required):**
   - A 70 Shore A cord at 27 % squeeze pushes back with about 1.5–3.5 N/mm (calc, check #2).
   - Run a Fusion static simulation, or a hand calc, of one long-side span (58.5 between screws) under 3.5 N/mm.
   - **Pass: the lid opens ≤ 0.25 mm between screws.**
   - If it fails, in this order:
     - (a) deepen the skirt to 8–10;
     - (b) add screws so that no span is over about 40: long sides 7 (pitch 39) and short sides 5 (pitch 38.5), 20 screws in all;
     - (c) specify a softer cord (50–60 Shore A solid, or EPDM sponge) and re-check the squeeze.

### 6.3 Battery compartment and retainer (`BOX`, `RETAINER`)

1. **Compartment:**
   - Inside X 0–`comp_W`, Y 0–`comp_H`, Z 0–`comp_D` (101 × 89 × 63).
   - The walls are the box's left wall, floor and back wall, plus:
     - a divider `divider_t` (X 101–103, Y 0–91);
     - a shelf `divider_t` (Y 89–91, X 0–103).
   - Both print as vertical walls.
2. **Lead slot:** 20 × 6 through the shelf at X 81–101.
3. **NTC / DS18B20 slot:** 3 wide, cut later into the foam, not printed.
4. **Retainer plate** (`RETAINER`):
   - `retainer_t` thick at Z 63–65, over X 0–101, Y 0–89.
   - Fixed with 2 × **M3 × 8 ISO 7380** A2, no washer (check #5; 8 − 2 = 6.0 engagement, 0.7 spare).
   - The screws go into inserts in Ø8 bosses at Y 44.5, both inside the plate's outline:
     - one at X 7, joined to the left wall by a rib. It keeps the head clear of the lid's locating lip, which runs at X ≤ 1.85.
     - one at X 97, on the divider's inner face.
   - The heads end at Z 66.65, 3.3 under the lid's inner face.
   - Notch the foam around the bosses. The pack ends at X 90.5.
5. **Above the shelf** (Y 91–130, X 0–103): space for the inline fuse holder and the 1S protection board, outside the foam [P1 D13] (secondary).
6. **Check:** pack plus 2 × `foam` = 100 × 62 × 88 fits 101 × 63 × 89 with 1 mm slack per axis (calc). This compares bounding boxes only. The CAD interference check against the retainer bosses and the foam notches decides (§ 9).
7. **PCB clearance:**
   - Only 5 mm separates the divider (X 101–103, up to Y 91) and the PCB's left edge (X 108).
   - Vertical (top-entry) JSTs on the left edge would avoid the clash. Side-entry plugs need about 10 mm and fit only above the shelf (Y > 91).
   - This is a suggestion, not a requirement on the PCB. It hasn't been raised with the PCB designer yet. It goes through the coordinator at F3, and either the board or the box layout may change (§ 4.3a, `pcb-interface.md`).
   - The battery connector will likely be a JST XH or a 2-pin terminal block rather than a PH, because both chargers together give up to about 2.0 A (the PCB designer; F2 decides). It is about as tall as a PH.

### 6.4 Roof cap (`ROOF`)

1. **Plate:**
   - `roof_t` thick, X `roof_X0` to `roof_X0 + roof_W` (−14.4 to 224.4), Z `roof_Z0` to `roof_Z0 + roof_D` (−5 to 99.5).
   - Falls `roof_fall` toward the lid.
2. **Legs:**
   - 4 × Ø`leg_D` on the top ribs (X 12 and 200).
   - Front pair at Z 40, `leg_front_h` tall; back pair at Z 12, `leg_back_h` tall.
   - Heights are from the rib top to the plate underside.
3. **Screws:**
   - Front **M3 × 35**, back **M3 × 40**, A2, with washers.
   - calc: washer 0.5 + plate 3.05 + leg; 6.45 engagement in a 7.5 hole (`ins3_L_rib`).
   - This replaces the brief's M3 × 35 everywhere, which bottomed out at the front (check #4).
4. **Underside ribs** (if any): ≤ `roof_rib_max` tall and ending at Z ≤ `roof_rib_endZ` (check #6).
5. **Clearance check:**
   - Underside above the top wall: about 26.8 at the lid face.
   - Over the lid skirt top (16.5 above the top wall): about 10.3. Over the ears (13.6): about 13.2.
   - Keep at least 8 everywhere and open on all four sides.
6. **Antenna:**
   - The nearest roof metal is the back insert and its screw tip, at X 200, Z 12. It is about 29 from the antenna zone at `pcb_X0 + 60`, 26 at + 64 and 25 at + 66 (3D text calc), so ≥ 20 in every case. CAD measures it (§ 9).
   - The zone doesn't move with `ant_overhang`, because `pcb_Y0` compensates.
7. **Print:**
   - Top face down: the whole flat top face lies on the bed.
   - The legs and their screw holes then lean 10° from vertical. No supports or bridges are expected; confirm in the slicer (`print-and-test.md` § 3).
8. **Optional SE side shade** (only if the first summer log passes 38 °C; that is a trigger for the shade, not proof that the cells are protected):
   - White ASA, 2.0, standing 15 off the battery-end wall, open at top and bottom.
   - Fixed on 3–4 Ø8 standoffs (assumed, secondary). Leave M3 insert bosses for it on the battery-end wall now (assumed).

### 6.5 Floor entries, vent, antenna (`BOX`)

**Floor entries**, positions (X, Z) on the floor, all entries pointing down:

| Entry | Part | Hole | (X, Z) |
|---|---|---|---|
| PMS lead | Lapp SKINTOP ST-M M12x1.5 black, 53111200 | `gl12_D` | (118, 15) |
| Solar, 2-wire | ST-M M12 | `gl12_D` | (143, 15) |
| Anemometer, 2-wire | ST-M M12 | `gl12_D` | (168, 15) |
| BME680 Cat5e (1.5–2 m) | ST-M M12; M16 (53111210) only if the cable OD > 7 | `gl12_D` / `gl16_D` | **(195, 15)** |
| Wind vane (later) | ST-M M12 with a blanking plug | `gl12_D` | (130, 45) |
| 868 MHz antenna | SMA(f) bulkhead with O-ring | D-hole `sma_D` / `sma_flat` | (193, 45) |

- **Cat5e gland position** moved from X 193 to 195 (check #8). With an M16 there, its Ø28 wrench circle would otherwise overlap the anemometer gland's Ø24.
- **Glands:**
  - M12 clamps 3.5–7, M16 clamps 4–10 (ds [53], check #7/#8). The black version is the UV-rated one.
  - Each gland gets an inner SKINDICHT SM-M locknut and a 1 mm EPDM sealing washer outside (check #9: the stack fits the 8 mm thread).
- **Round cables only:**
  - A gland seals only on a round jacketed cable (check #21).
  - The PMS lead is a round 4-core cable (OD 3.5–7) with JSTs inside at both ends, never the ribbon.
  - If the anemometer cable is flat (RJ11 style), it gets its own grommet: **TBD** when its type is known.
- **SMA:**
  - The D-hole comes from the drawing of the pigtail actually bought (check #11). The 2.4 floor is within every maximum panel thickness found.
  - The pigtail (u.FL to SMA(f), 1.37 mm, 150–250) runs along the floor and never above Y = 60.

**Vent:**
- Gore PolyVent Standard M12x1.5, black, PMF100320, with counter nut M10510-009 (ds [55]).
- On the PCB-end wall (X = `in_W`) at **Y 20, Z 47**. The Ø20 flat (Z 37–57) stays clear of the land flange, whose chamfer meets the wall at Z 57.4. The inside nut stays clear of the PCB front zone (Z ≤ 36.6).
- Hole `vent_D`, flat area Ø`vent_flat`, wrench 16, torque 0.7 Nm (check #12).

**Drainage and condensation:**
- No drain or weep hole.
- A 10 g indicating silica-gel sachet in the lid clip, replaced each autumn.
- The PCB is conformal-coated [P1 R-E4].

**USB-C:** no opening (decision 3A). A vertical receptacle on the PCB is reached with the lid off.

**Antenna wall:** solid white ASA `wall`, no infill, no metal, no PETG-CF.

### 6.6 Box carrier (`CARRIER`)

The carrier hangs the box and presents the standard foot. It prints flat, back face down.

1. **Plate:**
   - `car_t` thick, back face at Z = −2.4 − `car_gap` − `car_t` = −18.4.
   - Two bars 20 tall at Y 0–20 and Y 110–130, running X −16 to 226.
   - A spine `foot_pad` wide (X 73–137) joins them over the full height.
   - Fillets `r_root` at the joints.
2. **Spacer bosses:**
   - 4 × Ø`spacer_D` × `car_gap` on the box side at the tab centres (X −9 / 219, Y 10 / 120).
   - Each has an M4 insert hole Ø`ins4_D` × `ins4_L` from the box side.
   - **Box to carrier: 4 × M4 × 20 DIN 912 A2 with washers**, from the tab front (calc: 20 − 0.8 − 11 = 8.2 engagement, 0.9 spare).
   - **Access:**
     - The land flange (out to X −10 / 220, Z 57.4–70) sits above the bolt axes, so a straight key can't reach them.
     - Hang the box with the lid off. Use a 3 mm ball-end hex key, or the short arm of an L-key (48 free above the head).
3. **Foot pad:**
   - `foot_pad` × `foot_pad` at X 73–137, Y 33–97 (centre X 105, Y 65), `car_pad_t` thick (2 mm short of the box back).
   - 4 × Ø`clr_M4` at the foot pattern (X 80 / 130, Y 40 / 90).
   - Counterbores Ø`cb_M4_D` from the box side, leaving `mod_bear` = 8 under the head.
4. **Order of assembly:** adapter on the pipe or wall → carrier onto the adapter (4 × M4 × 16 from the box side) → box onto the carrier (4 × M4 × 20 from the front).
5. **Marking:** "UP" on the carrier's top edge face.

### 6.7 Standard foot and adapters (`ADAPTER_PIPE`, `ADAPTER_FLAT`)

**The standard (all modules and adapters):**
- 4 × M4 on a `foot_p` × `foot_p` square, centred on a flat pad of at least `foot_pad` × `foot_pad`.
- **Adapter side:** 4 × M4 heat-set inserts (ruthex M4 × 8.1 class), hole Ø`ins4_D` × `ins4_L`, blind, wall ≥ 2.1. Contact face flat within 0.2 (assumed).
- **Module side:** 4 × Ø`clr_M4` through holes with Ø`cb_M4_D` counterbores, `mod_bear` = 8 of material under the head.
- **Bolts:**
  - **M4 × 16 DIN 912 A2 + DIN 125 washer** everywhere.
  - calc: 16 − 8 − 0.8 = 7.2 engagement; the tip stops 1.9 short of the hole bottom.
- **Torque:** ≤ 1.2 Nm (assumed). Confirm on the coupon that the insert does not spin.
- The pattern allows 4 orientations. Each module marks "UP" on a side face.

**Pipe adapter (`ADAPTER_PIPE`)**, for vertical pipes Ø`pipe_min`–`pipe_max`:
1. Block `blk_W` × `blk_H` × `blk_D`, adapter frame (Z from the module face toward the pipe).
2. **Inserts:** 4 × M4 on the module face at (±25, ±25).
3. **V-saddle:**
   - `v_angle` V along Y, mouth `v_mouth` wide at Z = `blk_D`, apex at Z 14.
   - Apex relief 1.5 wide × 1 deep.
4. **Band tunnels:**
   - Two `band_w` × `band_t` slots running through the block along X, centred at Y ±`band_Y`, at Z 6–9.
   - They clear the inserts (Y ±25 ± 3.15) and stay 4 below the apex relief (Z 13).
5. **Band path:**
   - The outer vertical edges from the tunnel exits to the mouth are rounded R5.
   - The band runs: through the tunnel → along the side faces → around the pipe.
6. **Hose clamps:**
   - 2 all-stainless worm-drive clamps, 12 mm band (A2 / W4 or W5).
   - Size each clamp from the band path measured in CAD. For a 33.7 pipe expect about a 60–80 mm clamp range (calc, rough).
   - The worm housing sits beside the pipe, never inside the V.
7. Prints with the module face down. The V and tunnels need no supports if the tunnel roofs are ≤ 14 wide (bridge).

**Flat adapter (`ADAPTER_FLAT`)**, for a wall (with plugs) or a square post (with wood screws):
1. Plate `flat_W` × `flat_H` × `flat_t`.
2. **Inserts:** 4 × M4 from the front (module) face at (±25, ±25), 2.9 of material behind.
3. **Fixing holes:**
   - 4 × Ø`fix_D` at (±`fix_px`/2, ±`fix_py`/2) = (±15, ±55), 90° countersunk Ø`fix_csk` from the front.
   - Heads end flush or below the front face, because the box carrier's bars cover them.
   - The 30 × 110 pattern fits a post face ≥ 45 wide (assumed). Change `fix_px` and `fix_py` for the real post (**TBD**).
4. **Back face:** 4 pads Ø14 × 2 around the fixing holes, so water drains behind the plate (assumed).
5. **Print:**
   - Front (module) face down. With the back face down only the 4 pads would touch the bed, and the plate would hang 2 above it.
   - The insert holes and the countersinks then open at the bed. The insert-hole ends bridge Ø5.7, and the countersinks rise at 45°. No supports. Confirm in the slicer (`print-and-test.md` § 3).

### 6.8 Shield arm (`SHIELD_ARM`)

1. **Root pad:**
   - `foot_pad` × `foot_pad` × `arm_pad_t`.
   - 4 × Ø`clr_M4` with Ø`cb_M4_D` counterbores from the arm side, `mod_bear` = 8 under the head.
2. **Arm:**
   - `arm_w` wide × `arm_h` tall, horizontal, centred on the pad in X.
   - **Its bottom face is flush with the pad's bottom edge**, so the arm, flange and pad all print on the bed. It runs to the shield axis at `arm_L` from the pad face.
   - One gusset above the arm at the root, clear of the counterbores, `r_root` fillets. No gusset below.
3. **Flange:**
   - 3 spokes `spoke_w` × `spoke_t` at the arm end; one spoke in line with the arm.
   - Rod holes Ø`rod_hole` at r = `BC`/2 = 48, with M4 hex nut pockets underneath.
   - Keep r ≤ 30 open for the cap gland and the cable. Keep the spokes clear of the cap drains (r = 54, between spokes).
4. **Cable:** 3 cable-tie slots under the arm (assumed). The Cat5e runs under the arm with a drip loop before the cap gland.
5. **Print:**
   - In mounted orientation: arm and flange on the bed, pad standing.
   - Overall length about 227 (12 + 160 + 55), which fits the 256 bed without a brim along the length (calc; check in the slicer).
6. **Loads:**
   - Stack about 0.35 kg; wind about 17 N in a 30 m/s gust (calc, Cd 1.2 assumed).
   - Pad bending stress about 3 MPa (calc), far under 32 MPa in Z.

### 6.9 Radiation shield stack (`SH_PLATE`, `SH_ROOF`, `SH_CAP`)

1. **Plate** (one body, printed 7 ×):
   - Annulus `D_outer` / `D_inner`, `plate_t` solid.
   - Cone sloping `slope` down and outward over a radial width of 24.
   - Vertical drip skirt `drip_h` at the outer lip.
   - 3 built-in bosses Ø`boss_D` × `boss_h` at r = 48 with Ø`rod_hole`.
   - The clear gap is 16.9 vertical and 12.9 perpendicular to the plates (calc).
   - **Correct claim (check #17):** there is no direct line of sight from above or from the horizontal. Rays rising at about 40° (parallel to the cones, for example light reflected off snow) still reach the centre.
   - Plate index embossed only on the inside face of a boss.
2. **Roof:**
   - Ø`sh_roof_D`, `sh_roof_t` solid, slopes `sh_roof_slope` outward, smooth top.
   - 3 recessed pockets for M4 wing nuts.
   - **Print (open):** rim down, the underside of the shell is 65° from vertical. That likely needs supports under it, or a different form (for example a filled underside). It is an open choice for mobric through the coordinator; confirm in the slicer (`print-and-test.md` § 3).
3. **Bottom cap:**
   - Solid Ø`cap_D` dish, top falls `cap_fall` outward.
   - Lapp M12 gland at r = `cap_gland_r` for the Cat5e.
   - 4 × Ø`drain_D` at r = `drain_r`.
   - Rod holes on `BC`.
4. **Sensor cradle:**
   - A stem rises from the cap centre and holds the board, which is small: about `brd_W` × `brd_H` (**TBD**).
   - Both options below are working models built on placeholders: the size comes from a product photo, and M2 is assumed. Don't make a final cradle from them. `SH_CAP` stays behind its export gate until `brd_*` are measured (§ 9).
   - Model both and keep (b) suppressed until `brd_hole_dx` and `brd_hole_dy` are measured:
     - (a) a fork pocket `cradle_W` × `cradle_H` × `cradle_t` gripping 2 edges;
     - (b) 2 bosses on the stem, offset by `brd_hole_dx` / `brd_hole_dy`, with 2 × M2 × 6 **nylon** screws and nylon nuts through the board's mounting holes (bosses Ø`brd_hole_D`). No metal next to the sensor. The bosses stick out sideways from the upright stem, so give each a 45° chamfer underneath.
   - The BME680 sits on a tab sticking out of the board. Point the tab away from the stem and the cable entry, into free air. Nothing touches the tab.
   - Board vertical, about 90 above the cap (plate 4–5 level), ≥ 40 below the roof underside, ≥ 15 from every plate.
   - Chip face toward the pole.
   - The 6 pads (VCC, GND, SCL, SDA, SDO, CS) face down toward the cap gland, so the Cat5e reaches them without a loop. How the cable is terminated is **TBD**; today it is soldered (Q6).
5. **Rods:**
   - 3 × M4 A2 threaded rod. Length = flange underside to roof pocket floor + 25, measured in CAD (about 205).
   - Nuts under the flange; wing nuts on the roof (opens without tools).
6. **Inside the shield:**
   - Only the breakout: no extender, regulator board or connector PCB (an extender read about 1.5 °C high, meas [72]).
   - Power LED removed or blacked out.
   - No hot glue, silicone or rubber inside; siloxane-free coating only, or mask the BME680 (ds [82]).
7. No fan, no mesh on the louvres.

### 6.10 PMS7003 hood (`PMS_HOOD`, `PMS_CRADLE`, `MESH_RING`)

The hood is a separate component with its own export gate (§ 9): the port positions, the adapter board and the plug clearance must be measured first. Model it parametrically now, but don't export it for the field.

1. **Body:**
   - Outside 75 (X) × 35 (Z) at X 15–90, Z 5–40, walls 2.4.
   - The top plate sits 8 below the floor (on the floor-rib bottoms).
   - Total height about 90 (calc).
2. **Ears:**
   - One at each end, reaching the floor ribs at X 8 and 97, `hood_ear_t` thick, Ø`clr_M3` hole.
   - **M3 × 10** A2 into the rib inserts at Z 22 (check #5).
3. **Sensor:**
   - Pocket `pms_L + 2·pms_clr` × `pms_W + 2·pms_clr` × `pms_T + 2·pms_clr`.
   - On edge, port face down, `port_gap` above the mesh plane.
   - **10-pin connector:** mobric's dimension drawing (27.10.2026) puts it on the big 37 × 48 face, near one corner (PIN1 at the top right of that face), not on an edge.
     - Keep `pms_plug_clr` of free depth in front of that face around the connector, for the plug and the cable bend.
     - The cradle rails and foam pads must stay off that area.
     - The cable runs up to the adapter board slot (item 11).
   - **Fit check:** inside depth (Z) is 35 − 2 × 2.4 = 30.2. Pocket 12.6 + `pms_plug_clr` 12 + about 2 for rails and pads = 26.6, which fits (calc).
     - If the real plug needs more than about 15, widen the body in Z.
     - If the ports turn out to be on another face, re-check the orientation.
4. **Port face:**
   - A parametric plate. Inlet and outlet positions from the real sensor: **TBD (measure)**.
   - The dimension drawing shows openings on a 37 × 12 face and on a 12 × 48 face but doesn't label them. Don't take positions from it.
5. **Divider:**
   - A 2 mm rib from the port face to the mesh plane, sealed to the sensor with 2–3 mm closed-cell EPDM tape.
6. **Inlet and outlet:**
   - Inlet: open bottom on the inlet side, ≥ 25 across, channel ≤ 20 long, area ≥ 2 × the port.
   - Outlet: ducted 90° to a slot in the hood's battery-end wall, ≥ 20 from the inlet, behind its own mesh (ds [100]; assumed).
7. **Mesh:**
   - 40-mesh 304 woven, removable, in a 1 mm groove or a printed `MESH_RING`.
   - Open area ≥ 4 × the port area.
8. **Skirt and drainage:**
   - Skirt ≥ `hood_skirt` below the mesh, with a 3 mm downturned drip lip.
   - Every inner horizontal face falls ≥ 5° toward the open bottom. Never sealed.
9. **Cleaning:** ≥ 10 free under the port face with the mesh out.
10. **Cradle:**
    - Clip cradle on 2 rails with 1–2 mm foam pads; no screws through the sensor.
    - PETG-CF allowed (shaded).
11. **Adapter board and lead:**
    - Slot about 30 × 25 × 8 above the sensor: **TBD (measure the board)**.
    - The round 4-core lead leaves through a notch with an EPDM or TPU grommet at the top of the hood's PCB-end wall (X ≈ 90).
    - It makes a low point before rising into the floor gland at (118, 15).

### 6.11 Small parts

| Part | Material | Rule |
|---|---|---|
| Desiccant clip | PETG-CF or ASA | on the lid, ≥ 15 from the antenna keep-out (X 10–60 is ≈ 84 away at the working default) |
| Cable clamps | PETG-CF or ASA | inside the box only, below Y 60 |
| Strain-relief sleeves, pads | TPU 95A | never as a seal |

---

## 7. Tolerances and fits (summary)

| Joint | Rule | Status |
|---|---|---|
| Holes | modelled values from the § 4.1 hole table; `hole_add` only inside the insert and SMA holes; slicer hole compensation 0 | meas [30] |
| Gore vent hole | 12.2 nominal, no + 0.1 | ds [55] |
| Printed part to printed part | 0.25 per side XY, 0.4 in Z | ds [47] |
| Lid lip in opening | 0.25 per side | ds [47] |
| Lid skirt to ears and land | 0.5 | assumed |
| M3 insert | Ø4.1 × 6.7 blind, boss Ø8 | ds [27] |
| M4 insert | Ø5.7 × 9.1 blind, boss ≥ Ø10 (12 used) | ds (3DJake table) |
| Clearance | M2 2.4, M3 3.4, M4 4.6, modelled as is | assumed |
| Land flatness | ≤ 0.3 | assumed |
| Foot pad flatness | ≤ 0.2 | assumed |
| PMS pocket | + 0.3 per side | assumed |
| Gland holes | 12.3 / 16.3 default, set from the coupon | coupon |
| SMA D-hole | from the bought part's drawing | TBD |

---

## 8. Siting rules (not CAD, for the assembly sketch)

The final layout waits for the site measurements (§ 11). These rules hold for any pole or wall:

1. **Shield:**
   - Sensor at 1.25–2.0 m (WMO band, ds [89][90]), on the N side, clear sky, no wall, fence or paving within a few metres to the N.
   - ≥ 0.5 m from the box (2A).
   - Never directly under the box (drip, check #18) or directly above it (warm plume).
   - ≥ 0.3 m from the PMS outlet.
   - If the usual snow depth is over 0.9 m, raise it to snow depth + 0.6 m (ds [90]).
2. **Box:**
   - On the N or NE side of the pole, entries down, drip loops 100–150 mm with the low point ≥ 50 below each gland (ds [92]).
   - Battery end toward the SE if possible (assumed).
   - **Don't count on the panel's shade:** at the brief's heights the panel shadow falls below the box (check #19). The SE side shade stays the fallback.
3. **PMS inlet** ≥ 1.5 m above the ground, in shade (assumed; the PurpleAir guide says ≥ 1.8 m, secondary).
4. **Panel** SR10-36M: azimuth 233°, tilt 45°, unshaded.
5. **Anemometer** at the highest point, ≥ 2.5 m or above nearby obstacles (assumed).
6. **Cables:**
   - Cat5e ≤ 2 m (2A). The PCB designer's calc allows it (§ 2); F6 measures it on the real cable.
   - Each I²C signal goes in its own pair with GND or 3V3, never SDA with SCL in one pair (the PCB designer).
   - Anemometer cable: length **TBD**.
   - All cables tied every 0.3 m with UV-stabilised ties.

---

## 9. Checklist for Astra

Every box stays unticked until Astra's model exists. The text calcs in this spec don't tick any of them.

Before export:
- [ ] All user parameters exist with these names; no hard-coded dimension where a parameter exists.
- [ ] Rebuild at `ant_overhang` = 6.5 and 0, and at `ant_Xc` = `pcb_X0` + 60, + 64 and + 66 (§ 4.3a). At each one the model rebuilds and the keep-out body clears every printed and metal body except the PCB.
- [ ] At each of those alternatives, measure in CAD the 3D minimum distance from every metal body (§ 5.7) to the antenna zone and record it in `cad/NOTES.md`. Pass: ≥ 20, or the metal-free standoff at + 66.
- [ ] Growth test: set `in_W` 230 and `in_H` 150. The model rebuilds without broken features. Set them back.
- [ ] Interference check of every printed body against `REF` (antenna keep-out, PCB envelope and front zone, battery pack, wrench circles, metal bodies): no hits, except the PCB inside its own keep-out. Include the tools (hex keys, gland wrenches), the wiring, the inserts and screws, and the battery-retainer bosses against the real pack. The pack-plus-foam box alone doesn't prove those clear.
- [ ] No insert hole breaks into a sealed wall of the box.
- [ ] Lid stiffness check (§ 6.2.7) done and recorded: opening ≤ 0.25 mm, or the fallback taken.
- [ ] Roof clearance ≥ 8 over the lid skirt and ears, open on all four sides.
- [ ] Pipe adapter: Ø25 and Ø60 test pipes touch both V faces; the band path clears everything.
- [ ] Every part fits a 256 × 256 bed in one piece with its brim, away from any excluded area of the P2S profile (`print-and-test.md` § 1).
- [ ] Each part sits on the bed face named in `print-and-test.md` § 3, with only the supports and bridges listed there. Confirm in the slicer. `SH_ROOF` stays open until mobric chooses (§ 6.9.2).
- [ ] No text or grooves on upward outside faces; "UP" marks on side faces.
- [ ] Every screw length matches § 12 (the stack is measured in CAD, ≥ 0.5 mm short of each hole bottom).

Export to `hardware/station-pcb/enclosure/cad/` (create it; don't commit, mobric decides):
- `zephyr-enclosure.f3d`: the Fusion archive.
- `zephyr-enclosure.step`: the assembly.
- One `.3mf` (or `.stl`) per printed part, named after the component (`BOX.3mf`, `LID.3mf`, and so on).
- A short `cad/NOTES.md`: Fusion version, final parameter values that differ from § 4, check results.

**Export gates.** Each part waits only for its own inputs, so the rest of the model can go ahead. A gate says when a part could be ready for the field. Printing it or buying parts for it still needs mobric's OK.

| Part | Its gate opens when | Today |
|---|---|---|
| `SH_CAP` (with the cradle) | `brd_*` measured; cradle option (a) or (b) chosen | closed |
| `PMS_HOOD`, `PMS_CRADLE`, `MESH_RING` | port positions, adapter board, plug and cable bend (`pms_plug_clr`) measured | closed |
| `BOX`, `LID`, `ROOF`, `RETAINER`, `CARRIER` | PCB outline, module position and antenna edge agreed in F3; gland and SMA holes from the coupon and the bought parts; lid check passed | closed |
| `ADAPTER_PIPE`, `ADAPTER_FLAT` | pipe OD or post width known | closed |
| `SH_ROOF` | print choice made (§ 6.9.2) | closed |
| `SHIELD_ARM`, `SH_PLATE` | the checks above pass on the model | closed until the model exists |

---

## 10. Corrections applied from the number check (`research/2026-10-26-check.json`)

| # | Was (brief) | Now | Where |
|---|---|---|---|
| 2 | lid 3.2, closure assumed rigid | lid 4.5 + 6 mm perimeter skirt + required stiffness check, fallbacks | § 6.2 |
| 4 | roof screws M3 × 35 all round | front M3 × 35, back M3 × 40 (legs raised 5 for the skirt) | § 6.4 |
| 5 | M3 × 12 for retainer and hood | retainer M3 × 8, hood ears 4 thick with M3 × 10 | § 6.3, 6.10 |
| 6 | roof gap "≥ 20 everywhere" | real gap computed, underside ribs ≤ 5 and end at Z ≤ 46 | § 6.4 |
| 8 | M16 clamps 4.5–10, Cat5e gland at X 193 | M16 clamps 4–10, Cat5e gland at X 195 | § 6.5 |
| 10 | gland holes 12.3 / 16.3 as fact | parameters, set from the coupon | § 4.6 |
| 11 | SMA D-hole 6.6 / 5.95 as fact | parameters from the bought part | § 4.6 |
| 12 | vent hole + 0.1 rule | 12.2 nominal, 0.7 Nm, wrench 16 | § 6.5 |
| 14 | antenna "flush or overhang", distances 31 / 40 | `ant_overhang` parameter moves the PCB so the antenna stays put; roof insert about 26, tab bolt about 38 | § 4.3, 5, 6.4 |
| 15 | 4 shield plates per print | 3 per print only with a 3 mm brim, otherwise 2 | `print-and-test.md` |
| 17 | "no straight line of sight" | corrected wording | § 6.9 |
| 18 | shield on a 160 arm under the box | shield is its own module, ≥ 0.5 m from the box, never under it | § 2, 8 |
| 19 | panel shades the box | not counted on | § 8 |
| 20 | compartment 100 × 88 × 62 (zero slack) | 101 × 89 × 63 | § 6.3 |
| 21 | PMS ribbon through the gland | round 4-core lead; flat cables get a grommet | § 6.5, 6.10 |
| 24 | bracket bolts M4 × 35 | bracket replaced by the carrier; tab bolts M4 × 20 into inserts | § 6.6 |

Still unsupported: the gland hole size (coupon) and the summer pack peak ≤ 41 °C (the model assumed paint-white absorptance and did not include the layout). The DS18B20 log in the first summer decides on the side shade. Neither the ≤ 41 °C model nor the 38 °C trigger proves that the cells are protected; field tests have to show it.

---

## 11. TBD: what is still needed

| Item | Blocks | From |
|---|---|---|
| Board outline, module position, antenna edge. Answer received 27.10.2026 as a starting point (§ 4.3a); not agreed | PCB envelope, `pcb_Y0`, `ant_Xc`; the box gate | PCB designer in F3, then mobric through the coordinator |
| Left-edge connectors vs the battery divider (§ 6.3.7); battery connector series (XH or 2-pin block) | PCB-side layout near X 103–108 | raise with the PCB designer at F3; F2 picks the series |
| I²C at 1.5–2 m. Calc received 27.10.2026 (§ 2); not measured on the real cable and breakout; D8 unchanged | nothing in the enclosure (the M12 gland fits a 5–6 mm Cat5e) | F6 measures it; the D8 text changes in a later F1 revision, with mobric's consent |
| `SH_ROOF` printing: supports under the shell, or a different form | `SH_ROOF` gate | mobric, through the coordinator |
| Pole: pipe OD, or post face width, or wall material | adapter choice, `fix_px` / `fix_py` | mobric |
| Cable ODs: new Cat5e, solar, anemometer (round or flat?) | gland size, grommet | mobric |
| PMS7003 inlet and outlet positions and sizes, plug height and cable bend (`pms_plug_clr`), adapter board size. The 48 × 37 × 12 envelope and the connector's face are known from the drawing | PMS port face, board slot, hood depth | mobric (photo with a ruler of the port face; the adapter board with its plug) |
| BME680 breakout: exact outline (about 18 × 16 from a product photo, not measured), thickness, hole pitch and diameter (M2 assumed), cable termination | shield cradle (`brd_*`), the `SH_CAP` gate | mobric (caliper, or a top-down photo with a ruler) |
| SMA pigtail actually bought (drawing), antenna SMA or RP-SMA | `sma_D`, `sma_flat` | mobric |
| ASA and PETG-CF brands; nozzle diameter fitted | print profiles, shrinkage | mobric |
| Usual maximum snow depth | shield height | mobric (low priority) |

---

## 12. Fastener summary

| Joint | Fastener | Into |
|---|---|---|
| Lid | 14 × M3 × 10 ISO 7380 A2 + washer | M3 inserts in the ears |
| Roof front / back | 2 × M3 × 35 / 2 × M3 × 40 A2 + washer | M3 inserts in the top ribs |
| Battery retainer | 2 × M3 × 8 ISO 7380 A2, no washer | M3 inserts |
| Desiccant clip | 2 × M3 × 6 A2 (or as the clip needs) | M3 inserts in the lid bosses |
| PCB | 4 × M3 × 6 nylon | M3 inserts in the standoffs |
| BME680 board (cradle option b) | 2 × M2 × 6 nylon + nylon nuts | holes in the cradle bosses |
| PMS hood | 2 × M3 × 10 A2 + washer | M3 inserts in the floor ribs |
| Box → carrier | 4 × M4 × 20 DIN 912 A2 + washer | M4 inserts in the carrier spacers |
| Module → adapter (carrier or shield arm) | 4 × M4 × 16 DIN 912 A2 + washer | M4 inserts in the adapter |
| Adapter → wall or post | 4 × 5 mm A2 countersunk screws (+ plugs on a wall) | — |
| Pipe adapter → pipe | 2 × stainless hose clamps, 12 mm band | — |
| Shield stack | 3 × M4 A2 rod, nuts, washers, wing nuts | flange nut pockets |
