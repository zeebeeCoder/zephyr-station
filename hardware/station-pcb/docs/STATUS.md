# Station PCB status

Updated 25.10.2026. Maintained by the coordinator, `mobric/pcb-lead` (called `mobric/pcb-head` until 25.10.2026); created in F0 by `mobric/pcb-opus-5-5`.

## Phase

**F1 (requirements and architecture): revision 1 done 25.10.2026, waiting for the coordinator.**
- The documents are [REQUIREMENTS.md](REQUIREMENTS.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
- The Codex review of the draft is [reviews/F1-codex.md](reviews/F1-codex.md): 1 blocker, 6 major, 5 minor, 3 notes.
- The item-by-item response is [reviews/F1-response.md](reviews/F1-response.md): 12 fixed, 4 accepted, none disputed.
- The F1 gate is mobric approving D2–D14.

F0 (workspace setup): done, accepted by the coordinator 25.10.2026.

Sequence: F0 setup → F1 requirements and architecture → F2 atopile schematic → F3 KiCad layout → F4 production files → F5 enclosure and firmware (in parallel from F3) → F6 bring-up. Every phase ends at a gate, and the next one doesn't start without approval.

## Decisions

| # | Topic | State | F1 recommendation (not approved) |
|---|---|---|---|
| D1 | Project location: `zephyr-station/hardware/station-pcb/` on branch `hardware/station-pcb` | approved 25.10.2026 | — |
| D2 | Microcontroller | open | ESP32-WROOM-32E-N4 (PCB antenna, so Wi-Fi OTA stays possible) |
| D3 | Programming and USB | open | USB-C + CH343P powered only from VBUS, isolated from the ESP32 without VBUS, auto-reset |
| D4 | Radio | open | Ra-01H (SX1276) on SPI with RadioLib 7.8.1; u.FL to an SMA bulkhead |
| D5 | Charging | open | LT3652 solar charger and BQ25170 USB charger, both gated by a fail-safe NTC interlock (+1 / +44 °C). Cheaper alternative: CN3791 with a back-to-back FET disconnect and OVP |
| D5.2 | Cell protection placement | answered by mobric (Q2) | Keep the external protection board at the cells |
| D6 | 3.3 V rail | open | TPS631000 buck-boost in power-save mode |
| D7 | 5 V rail for the PMS7003 | open | TPS61023 with true disconnect, EN on GPIO13 |
| D8 | BME680 and sensor supply | open | Keep the off-board breakout, fed from a switched sensor supply (GPIO14) |
| D9 | Power measurement | open | One INA219 at 0x45, 0.1 Ω shunt in the battery path; battery voltage = bus + shunt |
| D10 | Spare inputs (wind vane, 1-Wire) | open | Wind vane on GPIO36, 1-Wire on GPIO16, both with ESD |
| D11 | Board size and enclosure | open | Parametric outline; new enclosure (Q8) |
| D12 | Manufacturing | open | JLCPCB Standard PCBA, 2 layers. First 5 boards about $250 + shipping and VAT (about $215 with the D5 alternative). Quantity deferred (Q9) |
| D13 | Winter energy strategy (new) | open | M2 firmware plus an adaptive schedule on today's panel and pack; log the box temperature this winter; fit a DNP heater footprint |
| D14 | Connectors (new) | open | Pluggable screw terminals for field cables, locking JST for internal leads |

Each recommendation's options, reasons, cost and firmware impact are in [ARCHITECTURE.md § 5](ARCHITECTURE.md#5-decisions).

## Open questions for mobric

mobric answered Q1–Q14 on 25.10.2026 (relayed by the coordinator). The answers and where they are used are in [ARCHITECTURE.md § 8](ARCHITECTURE.md#8-open-questions-and-answers).

Still open (questions 15–21 there):
- panel azimuth, and whether snow stays on the panel;
- a temperature logger in today's box for a few weeks this winter;
- the D13 winter strategy and the D5 charger;
- the cell model and the protection IC marking;
- conformal coating (Q13).

## Risks

Risks found in F1 and its review (cold Voc at the charger, the cold-charge interlock, the radio interrupt on core 3.3.11, winter brown-outs, and others) are listed in [ARCHITECTURE.md § 7](ARCHITECTURE.md#7-risks-and-bench-tests-f6). The winter brown-out options are in [ARCHITECTURE.md § 4.5](ARCHITECTURE.md#45-options-for-getting-through-the-winter).

- **R1. atopile 0.15.9 can't read layouts saved by KiCad 10.** Found 25.10.2026 on a scratch copy: after `kicad-cli pcb upgrade` moved the file from format 20241229 to 20260206, `ato build` failed at "Loading PCB" with `UnexpectedType in kicad.pcb.Layer field 'tenting'`. KiCad can't save in the older format.
  - **Decided 25.10.2026 by mobric (relayed by the coordinator): option (a).** This layout is edited in KiCad 9.0.x, installed next to KiCad 10. mobric installs it (it needs sudo).
  - KiCad 9 path: TBD until the install.
  - Until mobric confirms the install, nobody saves `layouts/default/default.kicad_pcb` in KiCad 10. Viewing it is fine.
  - `kicad-cli` 10 is safe on this board. DRC, render, and exports of gerbers, drill, positions and STEP left a KiCad 9 board byte-identical (checked 25.10.2026). They do create a `.kicad_prl` next to it, which git ignores.
  - After the install: record the KiCad 9 path here, and check one KiCad 9 save followed by `ato build` on a scratch copy.

## Who works on what

| Who | Role | Now |
|---|---|---|
| mobric | Owner. Approves decisions, orders and payment, firmware flashing, changes outside this folder | F1 questions 15–21; approving D2–D14; installing KiCad 9.0.x (R1) |
| `mobric/pcb-lead` | Coordinator: briefs, gates, this file | F1 revision 1 |
| `mobric/pcb-opus-5-5` | Designer (Claude Code): atopile code, documents, KiCad, enclosure, firmware branch | F1 revision 1 done; waiting for the coordinator |
| `mobric/mikolaj-codex` | Reviewer (Codex): checks against datasheets, writes `docs/reviews/F<n>-codex.md`, doesn't edit designer files | F1 review done (095b876); re-review if the coordinator routes it |

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
