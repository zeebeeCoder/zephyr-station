# Station PCB status

Updated 26.10.2026. Maintained by the coordinator, the Codync PCB bot: `mobric/workspace-codex-21` (a Codex agent) since its restart on 26.10.2026, `mobric/workspace-claude` before that from 26.10.2026. Before that it was `mobric/pcb-lead` in Grok Bot, called `mobric/pcb-head` until 25.10.2026. Created in F0 by `mobric/pcb-opus-5-5`.

## Phase

**F1 (requirements and architecture): revision 4 done 26.10.2026, waiting for the coordinator.**
- The documents are [REQUIREMENTS.md](REQUIREMENTS.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
- The Codex review of the draft is [reviews/F1-codex.md](reviews/F1-codex.md): 1 blocker, 6 major, 5 minor, 3 notes. The response to it is [reviews/F1-response.md](reviews/F1-response.md): 12 fixed, 4 accepted, none disputed.
- The Codex re-review of revision 1 is [reviews/F1-codex-r2.md](reviews/F1-codex-r2.md): 9 original items resolved and 7 partly, plus 1 blocker, 5 major and 4 minor new findings.
- The response to the re-review is [reviews/F1-response-r2.md](reviews/F1-response-r2.md): 11 fixed, 1 accepted, none disputed.
- The Codex third review, of revision 2, is [reviews/F1-codex-r3.md](reviews/F1-codex-r3.md): of the 12 revision-2 response rows, 6 resolved and 6 partly; new findings 0 blockers, 4 major, 3 minor and 2 notes.
- The response to it is [reviews/F1-response-r3.md](reviews/F1-response-r3.md): 7 fixed, 2 accepted, none disputed. Revision 3 also folds in mobric's answers of 26.10.2026 (15, 16, 19, 22, 23 and 8 cells).
- The Codex fourth review, of revision 3, is [reviews/F1-codex-r4.md](reviews/F1-codex-r4.md) (239a130): of the 9 revision-3 response rows, 6 resolved and 3 partly; of the six still-partly R2 rows, 3 resolved and 3 partly; new findings 0 blockers, 2 major, 2 minor and 3 notes.
- The response to it is [reviews/F1-response-r4.md](reviews/F1-response-r4.md): 5 fixed, 2 accepted, none disputed. Revision 4 also folds in mobric's answers Q24 (a) and Q25 (a), and the enclosure plan (D11), all relayed by the coordinator on 26.10.2026. No question for mobric is open.
- The F1 gate is mobric approving D2–D4 and D6–D14. D1 and D5 are approved.

F0 (workspace setup): done, accepted by the coordinator 25.10.2026.

Sequence: F0 setup → F1 requirements and architecture → F2 atopile schematic → F3 KiCad layout → F4 production files → F5 enclosure and firmware (in parallel from F3) → F6 bring-up. Every phase ends at a gate, and the next one doesn't start without approval.

## Decisions

| # | Topic | State | F1 recommendation (not approved unless the state says so) |
|---|---|---|---|
| D1 | Project location: `zephyr-station/hardware/station-pcb/` on branch `hardware/station-pcb` | approved 25.10.2026 | — |
| D2 | Microcontroller | open | ESP32-WROOM-32E-N4 (PCB antenna, so Wi-Fi OTA stays possible) |
| D3 | Programming and USB | open | USB-C + CH343P powered only from VBUS, isolated from the ESP32 without VBUS, auto-reset. USB sources up to 5.5 V only. USB charging only with a charging jumper fitted, open by default (mobric's answer Q24 a) |
| D4 | Radio | open | Ra-01H (SX1276) on SPI with RadioLib 7.8.1; u.FL to an SMA bulkhead |
| D5 | Charging | **LT3652 approved 25.10.2026** (mobric, relayed by the coordinator) | Revision 4 design around it: an SM15T33CA TVS and a TPS26600 eFuse at the panel input, which hold the eFuse's input ≤ 39.3 V and the charger's VIN ≤ 39.4 V during the defined surge, from ST's published clamp formula (F2 confirms it in ST's current datasheet); a Zener-clamped feed for the interlock's LDO; a BQ25170 USB charger at 347–444 mA behind the charging jumper; both chargers gated by three TLV3012B comparators (cold, hot, battery overvoltage) and a TPS3840 that requires a valid interlock rail, with the comparators' input filters bounded as one coupled network. The CN3791 is the rejected alternative |
| D5.2 | Cell protection | answered by mobric (Q2, Q20) | Protection on the board is self-sufficient: U3 overvoltage cut-off (4.29–4.43 V), TPS3840 low-battery cut-off (3.05–3.15 V), inline fuse at the pack. The pack's own board stays but isn't relied on |
| D6 | 3.3 V rail | open | TPS631000 buck-boost in power-save mode, enabled by the TPS3840 |
| D7 | 5 V rail for the PMS7003 | open | TPS61023 with true disconnect, EN on GPIO13 |
| D8 | BME680 and sensor supply | open | Keep the off-board breakout, fed from a switched sensor supply (GPIO14) |
| D9 | Power measurement | open | One INA219 at 0x45, 0.1 Ω shunt in the battery path; battery voltage = bus + shunt. Its signed current also tells the charge state, because CHRG isn't read |
| D10 | Spare inputs (wind vane, 1-Wire) | open | Wind vane on GPIO36, 1-Wire on GPIO16, both with ESD |
| D11 | Board size and enclosure | open | Parametric outline; new 3D-printed enclosure (Q8) with a compartment for the D13 pack, for the new PCB only. mobric models it in Fusion 360 with the 3D agent Astra; `mobric/pcb-caseing` writes its specification, board interface, shopping list, print settings and STEP/STL review. ASA and PETG-CF on an enclosed Bambu Lab printer. Preferences until the gate |
| D12 | Manufacturing | open | JLCPCB Standard PCBA, 2 layers. First 5 boards about $290–310 + shipping and VAT (assumed; the new parts aren't priced yet). Quantity deferred (Q9) |
| D13 | Winter energy strategy | open; mobric prefers (b) combined with (a) (Q17) and chose 8 cells (26.10.2026) | (a): M2 firmware with the adaptive schedule and no listening, plus 8 new Samsung INR18650-35E cells (1S8P, 26.8 Ah). No outage in 18 modelled winters with 20 % fade, as long as one full read costs ≤ 3.99 mAh under the model's scaling of read costs; 14 cells allow 6.39 mAh. The cells: 8 new, genuine 35E from one batch (mobric's answer Q25 a). Keep a DNP heater footprint; F2 defines how the cells' −10 °C discharge limit is met |
| D14 | Connectors | open | Pluggable screw terminals for field cables, locking JST for internal leads |

Each recommendation's options, reasons, cost and firmware impact are in [ARCHITECTURE.md § 5](ARCHITECTURE.md#5-decisions).

## Open questions for mobric

mobric answered Q1–Q14 and most of Q15–Q21 on 25.10.2026, and 15, 16, 19, 22–25 plus the pack size on 26.10.2026 (relayed by the coordinator). The answers and where they are used are in [ARCHITECTURE.md § 8](ARCHITECTURE.md#8-open-questions-and-answers).

No question is open after revision 4:
- 24: USB charging stays off unless a charging jumper is fitted, open by default (a);
- 25: 8 new, genuine Samsung INR18650-35E from one batch (a).

What remains for mobric is the F1 gate: approving D2–D4 and D6–D14.

## Risks

Risks found in F1 and its reviews (surges at the charger input, the cold-charge interlock, the radio interrupt on core 3.3.11, winter outages, and others) are listed in [ARCHITECTURE.md § 7](ARCHITECTURE.md#7-risks-and-bench-tests-f6). The winter options are in [ARCHITECTURE.md § 4.5](ARCHITECTURE.md#45-options-for-getting-through-the-winter) and D13.

- **R1. atopile 0.15.9 can't read layouts saved by KiCad 10.** Found 25.10.2026 on a scratch copy: after `kicad-cli pcb upgrade` moved the file from format 20241229 to 20260206, `ato build` failed at "Loading PCB" with `UnexpectedType in kicad.pcb.Layer field 'tenting'`. KiCad can't save in the older format.
  - **Decided 25.10.2026 by mobric (relayed by the coordinator): option (a).** This layout is edited in KiCad 9.0.x, installed next to KiCad 10. mobric installs it (it needs sudo).
  - KiCad 9 path: TBD until the install.
  - Until mobric confirms the install, nobody saves `layouts/default/default.kicad_pcb` in KiCad 10. Viewing it is fine.
  - `kicad-cli` 10 is safe on this board. DRC, render, and exports of gerbers, drill, positions and STEP left a KiCad 9 board byte-identical (checked 25.10.2026). They do create a `.kicad_prl` next to it, which git ignores.
  - After the install: record the KiCad 9 path here, and check one KiCad 9 save followed by `ato build` on a scratch copy.

## Who works on what

| Who | Role | Now |
|---|---|---|
| mobric | Owner. Approves decisions, orders and payment, firmware flashing, changes outside this folder | Approving D2–D4 and D6–D14 at the F1 gate; installing KiCad 9.0.x (R1); the enclosure model in Fusion 360 with Astra (D11) |
| `mobric/workspace-codex-21` (the Codync PCB bot, a Codex agent since its restart on 26.10.2026; `mobric/workspace-claude` before it) | Coordinator: briefs, gates, this file. Took over from `mobric/pcb-lead` (Grok Bot) | Routing revision 4 to Codex |
| `mobric/pcb-design-2` (earlier `mobric/pcb-design`, `mobric/mikolaj-claude-60` and `mobric/pcb-opus-5-5`; the same session renamed) | Designer (Claude Code): atopile code, documents, KiCad, firmware branch | F1 revision 4 done 26.10.2026; waiting for the Codex review of it, with no changes to the F1 documents until then |
| `mobric/mikolaj-codex` | Reviewer (Codex): checks against datasheets, writes `docs/reviews/F<n>-codex*.md`, doesn't edit designer files | F1 review (095b876), re-review (959fe88), third review (dacb0ba) and fourth review (239a130) done; next, revision 4 when the coordinator routes it |
| `mobric/pcb-caseing` | Enclosure (Claude Code): specification, board interface, shopping list, print settings and STEP/STL review for the enclosure mobric models in Fusion 360 (D11). Writes only in `hardware/station-pcb/enclosure/` | Enclosure specification (D11) |

The handoff session `mobric/projektowanie-custom-pcb-z-ai` delivered the project context on 25.10.2026 and does no further work.

## Ground rules

- Work happens only in `hardware/station-pcb/`, on branch `hardware/station-pcb` (worktree `~/Documents/MIKO/zephyr-station-pcb`). The rest of zephyr-station is shared, so changes outside this folder need mobric's approval.
- No push without approval.
- Firmware is compile-only (`just esp cook station`). Flashing is locked until PKM task 2026-09-04-T0001 is closed and needs mobric's consent.

## Tooling (checked 25.10.2026)

- atopile 0.15.9, signed in (part picking needs it). It's the last classic CLI, in maintenance mode only; the successor is app.atopile.io (0.16+).
- Every `ato` command warns "Could not find KiCad plugin path" and "Couldn't enable plugin api". atopile 0.15.9 only knows KiCad 9.0 paths (`KICAD_VERSION = "9.0"` in `faebryk/libs/kicad/paths.py`) and this Mac has KiCad 10.0.7, so the atopile KiCad plugin isn't installed. Builds aren't affected.
- KiCad 10.0.7: `kicad-cli` isn't on PATH (`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`). KiCad 9.0.x, used to edit this layout: path TBD (R1).
- `ato create project` runs `git init` unless its target is a repository root. Inside this monorepo, generate the project elsewhere and copy it in (F0 did this).
- The template `.gitignore` ignores `*.csv`, `*.xml` and `lib/`. Adjust it before committing JLC BOM/CPL files or a local library folder.
