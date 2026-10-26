# Station PCB status

Updated 26.10.2026. Maintained by the coordinator, `mobric/workspace-claude` (a Codync bot) from 26.10.2026. Before that it was `mobric/pcb-lead` in Grok Bot, called `mobric/pcb-head` until 25.10.2026. Created in F0 by `mobric/pcb-opus-5-5`.

## Phase

**F1 (requirements and architecture): revision 2 done 26.10.2026, waiting for the coordinator.**
- The documents are [REQUIREMENTS.md](REQUIREMENTS.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
- The Codex review of the draft is [reviews/F1-codex.md](reviews/F1-codex.md): 1 blocker, 6 major, 5 minor, 3 notes. The response to it is [reviews/F1-response.md](reviews/F1-response.md): 12 fixed, 4 accepted, none disputed.
- The Codex re-review of revision 1 is [reviews/F1-codex-r2.md](reviews/F1-codex-r2.md): 9 original items resolved and 7 partly, plus 1 blocker, 5 major and 4 minor new findings.
- The response to the re-review is [reviews/F1-response-r2.md](reviews/F1-response-r2.md): 11 fixed, 1 accepted, none disputed.
- The F1 gate is mobric approving D2–D4 and D6–D14. D1 and D5 are approved.

F0 (workspace setup): done, accepted by the coordinator 25.10.2026.

Sequence: F0 setup → F1 requirements and architecture → F2 atopile schematic → F3 KiCad layout → F4 production files → F5 enclosure and firmware (in parallel from F3) → F6 bring-up. Every phase ends at a gate, and the next one doesn't start without approval.

## Decisions

| # | Topic | State | F1 recommendation (not approved unless the state says so) |
|---|---|---|---|
| D1 | Project location: `zephyr-station/hardware/station-pcb/` on branch `hardware/station-pcb` | approved 25.10.2026 | — |
| D2 | Microcontroller | open | ESP32-WROOM-32E-N4 (PCB antenna, so Wi-Fi OTA stays possible) |
| D3 | Programming and USB | open | USB-C + CH343P powered only from VBUS, isolated from the ESP32 without VBUS, auto-reset. USB sources up to 5.5 V only |
| D4 | Radio | open | Ra-01H (SX1276) on SPI with RadioLib 7.8.1; u.FL to an SMA bulkhead |
| D5 | Charging | **LT3652 approved 25.10.2026** (mobric, relayed by the coordinator) | Revision 2 design around it: TPS26600 eFuse and SMBJ33CA at the panel input; BQ25170 USB charger at 356–444 mA; both chargers gated by three TLV3012B comparators (cold, hot, battery overvoltage). The CN3791 is the rejected alternative |
| D5.2 | Cell protection | answered by mobric (Q2, Q20) | Protection on the board is self-sufficient: U3 overvoltage cut-off, TPS3840 low-battery cut-off, inline fuse at the pack. The pack's own board stays but isn't relied on |
| D6 | 3.3 V rail | open | TPS631000 buck-boost in power-save mode, enabled by the TPS3840 |
| D7 | 5 V rail for the PMS7003 | open | TPS61023 with true disconnect, EN on GPIO13 |
| D8 | BME680 and sensor supply | open | Keep the off-board breakout, fed from a switched sensor supply (GPIO14) |
| D9 | Power measurement | open | One INA219 at 0x45, 0.1 Ω shunt in the battery path; battery voltage = bus + shunt. Its signed current also tells the charge state, because CHRG isn't read |
| D10 | Spare inputs (wind vane, 1-Wire) | open | Wind vane on GPIO36, 1-Wire on GPIO16, both with ESD |
| D11 | Board size and enclosure | open | Parametric outline; new enclosure (Q8) with a compartment for the D13 pack |
| D12 | Manufacturing | open | JLCPCB Standard PCBA, 2 layers. First 5 boards about $280–300 + shipping and VAT (assumed; the new parts aren't priced yet). Quantity deferred (Q9) |
| D13 | Winter energy strategy | open; mobric prefers (b) combined with (a) (Q17) | (a2): M2 firmware with the adaptive schedule and 2-min listens, so every gateway request is heard, plus 8 cells (1S8P, 27.2 Ah). 14 cells if M2's savings fail in F6. The choice is asked in Q23. Fit a DNP heater footprint |
| D14 | Connectors | open | Pluggable screw terminals for field cables, locking JST for internal leads |

Each recommendation's options, reasons, cost and firmware impact are in [ARCHITECTURE.md § 5](ARCHITECTURE.md#5-decisions).

## Open questions for mobric

mobric answered Q1–Q14 and most of Q15–Q21 on 25.10.2026 (relayed by the coordinator). The answers and where they are used are in [ARCHITECTURE.md § 8](ARCHITECTURE.md#8-open-questions-and-answers).

Still open (numbered as there):
- 15: whether snow stays on the panel (the azimuth, about 233°, is answered);
- 16: a temperature logger in today's box for a few weeks this winter;
- 19: a photo of one cell's wrapper, for the cell model;
- 22 (new): the sleep-current target R-P7 as a measured limit with conditions;
- 23 (new): the D13 choice, (a1) or (a2) and 8 or 14 cells.

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
| mobric | Owner. Approves decisions, orders and payment, firmware flashing, changes outside this folder | F1 questions 15, 16, 19, 22 and 23; approving D2–D4 and D6–D14; installing KiCad 9.0.x (R1) |
| `mobric/workspace-claude` (Codync, from 26.10.2026) | Coordinator: briefs, gates, this file. Took over from `mobric/pcb-lead` (Grok Bot) | Revision 2 routed to Codex; questions 15, 16, 19, 22 and 23 with mobric; then the revision 3 brief |
| `mobric/pcb-opus-5-5` (listed as `mobric/mikolaj-claude-60` since a restart) | Designer (Claude Code): atopile code, documents, KiCad, enclosure, firmware branch | F1 revision 2 done; waiting for the Codex review and the revision 3 brief, with no changes to the F1 documents until then |
| `mobric/mikolaj-codex` | Reviewer (Codex): checks against datasheets, writes `docs/reviews/F<n>-codex*.md`, doesn't edit designer files | F1 review (095b876) and re-review (959fe88) done; reviewing revision 2 (0d038c4) into `docs/reviews/F1-codex-r3.md` |

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
