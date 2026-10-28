# Zephyr station enclosure

3D-printed housings for the outdoor station: the sealed electronics and battery box, the BME680 radiation shield, the PMS7003 hood, and a common mounting foot with adapters for pipe, wall and square post. They are designed for the new custom PCB only.

**Status: draft spec, 27.10.2026, with revisions A and B. Not approved for printing, not committed.**
- Revision A: PMS7003 plug clearance and the BME680 cradle, from mobric's drawing and photo.
- Revision B: the six points from the coordinator's text review of 27.10.2026. That review covered text, consistency and interfaces, not CAD, a slicer, the sources or physical tests. mobric models the parts in Fusion 360 with Astra, mobric's 3D-design agent, from `fusion-spec.md`. The enclosure session (`pcb-caseing`) writes and checks the spec.

| File | What it is |
|---|---|
| `fusion-spec.md` | The spec for Astra: user parameters, features step by step, tolerances, checklist, fasteners |
| `print-and-test.md` | Bambu Lab P2S settings, test coupons in order, hardware list |
| `pcb-interface.md` | Board outline and connector edges proposed to the PCB designer |
| `research/` | The 26.10.2026 research brief and its number check (background) |
| `cad/` | Created by Astra on export: `.f3d`, `.step`, one `.3mf` per part |

## Decisions (mobric, through the coordinator, 27.10.2026)

| # | Decision |
|---|---|
| 1A | Common foot, 4 × M4 on a 50 × 50 square, with adapters for pipe, wall and square post |
| 2A | BME680 Cat5e 1.5–2 m, shield at least 0.5 m from the box (a siting preference; the PCB designer's calc allows the length, F6 measures it, D8 is unchanged) |
| 3A | USB-C only with the lid off; routine updates over Wi-Fi; no outside USB port |
| 4A | Board interface sent to the PCB designer as a proposal for checking; answered 27.10.2026 as a starting point, F3 confirms (`pcb-interface.md`) |
| 5A | Bambu Lab P2S with a hardened nozzle; white ASA outside, PETG-CF only for shaded inner parts |

Design choices made in the spec on top of these (open to mobric's veto):
- The foot puts the threads (M4 heat-set inserts) in the adapter and the bolts in the module. So the adapter goes on the pole first and each module bolts on and comes off from the front.
- The box gets a separate carrier plate that presents the foot. Its back wall is sealed and it prints back-down, so it can't carry the inserts itself.
- One flat adapter serves both a wall and a square post. Only the fixing screws differ.

## What is checked and what isn't

- **Checked against sources** (number check of 26.10.2026; 8 confirmed):
  - the 15 mm antenna keep-out;
  - M3 insert hole and boss sizes;
  - groove, squeeze and fill;
  - Lapp M12 gland range and stack;
  - PMS7003 envelope;
  - the shrinkage method.
- **Corrected and applied:** the 14 corrections, listed in `fusion-spec.md` §10. The one refuted claim (4 shield plates per bed) is fixed in `print-and-test.md`.
- **Looked up 27.10.2026 from retailer and distributor pages:**
  - P2S: 256³ volume, stock 0.4 hardened nozzle, 300 °C nozzle, 110 °C bed;
  - Bambu PETG-CF data sheet ranges;
  - ruthex M4 insert dimensions.
- **PCB designer's answers (27.10.2026):** received, but not agreed, not tested and not in F1 (`pcb-interface.md`). The antenna edge and the module position are working alternatives in the model (`fusion-spec.md` § 4.3a).
- **Not confirmed:**
  - whether the P2S has a chamber heater;
  - the P2S excluded plate areas (check in Bambu Studio);
  - Lapp gland hole sizes (coupon);
  - SMA D-hole (from the bought part);
  - the summer pack peak (the first-summer log decides).
- **New, calc only:**
  - lid 4.5 + skirt;
  - raised roof legs and their screw lengths;
  - carrier and adapter geometry;
  - M4 screw lengths.

  An independent re-check (27.10.2026, arithmetic and clashes, no new sources) found 14 problems; all are fixed. Among them:
  - the lid ribs were hitting the battery retainer;
  - the washer was wider than its counterbore;
  - the vent ran into the land flange;
  - the shield arm couldn't print as described;
  - the PCB insert sat too close to the antenna.

  The lid stiffness still has to pass the simulation in `fusion-spec.md` §6.2 and the lid coupon in `print-and-test.md` §4.

## Before final modelling or printing

From the coordinator's review of 27.10.2026:
- A CAD interference check of every part, tool and wire, including the inserts and screws and the battery-retainer bosses against the pack. The pack-plus-foam bounding box alone doesn't prove those clear.
- The lid stiffness simulation or calc, and the lid coupon. The seal force and the build tolerances stay conditional until then.
- The P2S profile, excluded areas, brims and compensation, and the real filament and nozzle, checked rather than taken from secondary data.
- The PCB interface agreed in F3; real measurements of the sensors, ports, plugs, cables, glands, pigtail and mounting.
- Pack heat: the first summer's log doesn't close it by itself. Neither the ≤ 41 °C model nor the 38 °C trigger proves that the cells are protected.

Each part has its own export gate (`fusion-spec.md` § 9). A missing measurement holds up only the part it belongs to.

## Measurements still needed from mobric

1. **Pole at the new spot:** pipe outer diameter, or the square post's face width, or the wall material.
2. **Cable outer diameters:** the new Cat5e, solar, anemometer. Is the anemometer cable round or flat?
3. **PMS7003:** a photo with a ruler of the inlet/outlet face, plus the adapter board size and the plug with its cable bend. The dimension drawing has arrived; it fixes the envelope and the connector's face, not the ports.
4. **BME680 breakout:** caliper sizes or a top-down photo with a ruler: outline, thickness, hole positions and diameter. The product photo has arrived; it isn't a measurement.
5. **SMA pigtail and antenna:** the exact part (link or drawing); antenna SMA or RP-SMA.
6. **Filament brands** (white ASA, PETG-CF) and the nozzle diameter fitted.
7. Usual maximum snow depth (low priority).

From the PCB designer at F3: the agreed outline, module position and antenna edge. Also the left-edge connectors against the battery divider, which haven't been raised yet.

## State and next steps (28.10.2026)

- **Paused** since 27.10.2026 at mobric's request, through the coordinator. No revisions, research, CAD or tests until mobric resumes the work.
- **This folder is untracked and uncommitted.** A fresh clone won't have it. When moving to another machine, copy `enclosure/` by hand, or commit it once mobric agrees.
- **Inputs kept outside the repo,** in the Codync PCB bot's workspace (`~/.codync/bots/ba2336bd-…/workspace/`):
  - the coordinator's review `reviews/enclosure-draft-a-2026-10-27.md`;
  - mobric's PMS7003 drawing and BME680 photo in `uploads/`;
  - the site photos (never copy them here).
- **Next brief, already asked for by the coordinator:**
  - rewrite the left-edge JST row in `pcb-interface.md` as an item to check jointly at F3;
  - write a short A/B with a recommendation for `SH_ROOF` printing (supports or another form) and for a separate BME cradle part. Implement neither.
- **Tools:** the spec is plain Markdown. Modelling needs Fusion 360 with Astra on mobric's PC (version not fixed yet). The print checks need Bambu Studio with the P2S profile.

## Rules for this folder

- Only enclosure files live here. Don't edit the F1–F3 documents in `../docs/`.
- No commits or pushes without mobric's OK.
- No site photos in the repo.
