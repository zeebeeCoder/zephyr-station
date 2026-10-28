# PCB ↔ enclosure interface (R-M2): proposal and answer

**Status: proposal, answered, not agreed.** mobric chose to send it to the PCB designer for checking (decision 4A, 27.10.2026). It went to `pcb-design` over the intercom on 27.10.2026, and the designer answered the same day: accepted as a starting point, with notes (below). Nothing here changes F1, F2 or F3. D11 and R-M2 stay parametric, and F3 confirms the outline during placement. Any agreed version goes back to mobric through the coordinator before final modelling.

Status words used here:
- **answer received:** the PCB designer replied on 27.10.2026;
- **agreed:** both designers, and mobric through the coordinator, accept it. Nothing is agreed yet;
- **tested:** measured on hardware. Nothing is tested yet;
- **in F1:** written into the F1 documents. Nothing from this interface is in F1.

## Proposal as sent (27.10.2026)

Frame: seen from the lid, X right, Y up. The PCB's rear face is `standoff_h` = 15 mm off the box's back wall.

| Item | Proposal |
|---|---|
| Outline | 100 × 80 × 1.6 mm |
| Mounting holes | 4 × Ø3.2, 4 mm from each edge (92 × 72 pattern), M3 × 6 nylon screws into heat-set inserts in 15 mm standoffs |
| ESP32-WROOM-32E | on the top edge, antenna up, module centre about 66 mm from the left edge (movable) |
| Antenna keep-out | 15 mm in every direction (Espressif). No metal (screws, inserts) within about 20 mm of the antenna |
| Antenna edge | flush with copper cut away beside and under it, or overhanging the edge by about 6–7 mm. **Designer to choose.** The box drops the PCB by the overhang (`ant_overhang`), so the antenna top stays at the same height |
| Field terminals | panel, anemometer, BME680 Cat5e, wind vane: pluggable 3.5 / 3.81 mm blocks on the **bottom** edge, wire entry downward, screws toward the lid [D14, R-M3]. Cables come up from glands in the box floor |
| Internal JSTs | battery, NTC, PMS, 1-Wire on the **left** edge, facing the battery compartment |
| u.FL | bottom-right corner; the pigtail runs along the floor to the SMA bulkhead (about 100 mm from the ESP32 antenna) |
| USB-C | vertical receptacle, reached from the lid side with the lid off (decision 3A); no outside port |
| Part height | front-side parts ≤ 20 mm |

Questions sent with it:
1. Do 100 × 80 and the 92 × 72 pattern fit F1? If not, what outline? The box can grow by about 20 mm.
2. Antenna flush or overhanging?
3. Can every connector sit on the proposed edge?

Also sent the same day: does a 1.5–2 m Cat5e to the BME680 (decision 2A) fit D8 without an architecture change?

## Answer and status (27.10.2026)

| Item | The PCB designer's answer | Status | In the enclosure spec |
|---|---|---|---|
| Outline 100 × 80, holes 92 × 72 | Fits roughly. The parts take about 4200 of 8000 mm² (about 50 %), but that is an area estimate, not a placement. F3 gives the real answer | answer received; not agreed | proposal values kept (`fusion-spec.md` § 4.3) |
| Box growth ("+20 mm") | Keep the margin in the model | answer received | the model must rebuild with `in_W` and `in_H` up to +20. The box isn't bigger now (§ 4.3a, growth test in § 9) |
| Antenna edge | Leave room in the box for the overhanging antenna (about 6–7 mm past the edge, free space around it). That is the box's worst case and the antenna's best case under Espressif's guidance. Flush vs overhanging belongs to F3 and D2; F1 doesn't decide it | answer received; not agreed | `ant_overhang` working default 6.5, rebuilt at 0 too (§ 4.3a) |
| Module position and metal | At 66 mm the antenna reaches about 75 mm and the top-right hole edge is at about 94.4 mm, so the gap is about 19–20 mm. A nylon screw is fine, but a brass insert in that standoff would sit at the 20 mm limit. Either move the module to about 60 mm (gap about 25 mm) or use a metal-free standoff in that corner | answer received; not agreed | `ant_Xc` working default `pcb_X0 + 60`, rebuilt at + 64 and + 66; metal-free standoff as the + 66 alternative; 3D distances measured in CAD (§ 4.3a, § 9) |
| Connector edges | No objection to the proposed edges. The panel's TVS and TPS26600 sit right at its terminal (F3). u.FL bottom-right is fine with the Ra-01H next to it; the pigtail along the floor is fine, the farther from the ESP32 antenna the better. Vertical USB-C toward the lid is fine, with a no-coating zone (R-E4) | answer received; not agreed | unchanged |
| Battery connector | Both chargers together give up to about 2.0 A (1.56 + 0.44 A), so a JST PH (2 A) is at its limit. F2 will likely pick a JST XH or a 2-pin terminal block, of similar height | answer received; F2 decides | noted in `fusion-spec.md` § 6.3.7 |
| Part height ≤ 20 mm | The tallest parts will be pluggable terminals with their plugs, about 12–18 mm depending on the series. F2 picks a series that fits 20 mm | answer received; F2 decides | `front_max` stays 20 |
| Left-edge JSTs vs the battery divider | Not asked. Only 5 mm separates the compartment divider and the PCB's left edge, so vertical (top-entry) JSTs, side-entry plugs above the shelf, or a moved divider would be needed (`fusion-spec.md` § 6.3.7) | **not raised yet**; raise through the coordinator at F3 | a suggestion, not a requirement on the PCB |
| I²C over 1.5–2 m Cat5e | Works without a buffer: 100 kHz (firmware can drop to 50 kHz), ≤ 250 pF per line (about 190 pF estimated, counting Cat5e at 80 pF/m), 3.3 kΩ pull-ups to SENSOR_3V3 on the board, TVS ≤ 5 pF per line. Each signal in its own pair with GND or 3V3, never SDA with SCL in one pair. A Cat5e of Ø5–6 mm fits the M12 gland | calc received; **not tested** (F6 measures t_r and capacitance on the real cable and breakout); **not in F1** (D8 and R-F2 still say < 1 m until a later F1 revision with mobric's consent) | no enclosure change |
