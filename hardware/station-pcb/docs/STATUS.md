# Station PCB status

Updated 25.10.2026. Maintained by the coordinator, `mobric/pcb-head`; created in F0 by `mobric/pcb-opus-5-5`.

## Phase

**F1 (requirements and architecture): draft done 25.10.2026, waiting for review.** The documents are [REQUIREMENTS.md](REQUIREMENTS.md) and [ARCHITECTURE.md](ARCHITECTURE.md). The coordinator routes the review to Codex. The F1 gate is mobric approving D2–D12.

F0 (workspace setup): done, accepted by the coordinator 25.10.2026.

Sequence: F0 setup → F1 requirements and architecture → F2 atopile schematic → F3 KiCad layout → F4 production files → F5 enclosure and firmware (in parallel from F3) → F6 bring-up. Every phase ends at a gate, and the next one doesn't start without approval.

## Decisions

| # | Topic | State | F1 recommendation (not approved) |
|---|---|---|---|
| D1 | Project location: `zephyr-station/hardware/station-pcb/` on branch `hardware/station-pcb` | approved 25.10.2026 | — |
| D2 | Microcontroller | open | ESP32-WROOM-32E-N4 |
| D3 | Programming interface | open | USB-C + CH343P powered from USB, auto-reset |
| D4 | Radio | open | SX1276 on SPI: Ra-01H first, RFM95W alternative; u.FL to an SMA bulkhead |
| D5 | Solar charging | open | CN3791 on board, MPPT 18.69 V, 1.46 A, NTC window inhibit (0–45 °C) |
| D5.2 | Cell protection placement | open | Keep the external protection board at the cells |
| D6 | 3.3 V rail | open | TPS631000 buck-boost |
| D7 | 5 V rail for the PMS7003 | open | TPS61023 with true disconnect, EN on GPIO13 |
| D8 | BME680 placement | open | Keep the off-board breakout on the Cat5e cable |
| D9 | Power measurement | open | One INA219 at 0x45, 0.1 Ω shunt in the battery path |
| D10 | Spare inputs (wind vane, 1-Wire) | open | Wind vane on GPIO36, 1-Wire on GPIO16 |
| D11 | Board size and enclosure | open (mobric undecided) | Parametric outline |
| D12 | Manufacturing | open | JLCPCB Standard PCBA, 2 layers, 5 boards (about $195 + shipping) |

Each recommendation's options, reasons, cost and firmware impact are in [ARCHITECTURE.md § 5](ARCHITECTURE.md#5-decisions-d1d12).

## Open questions for mobric

Answered 25.10.2026 (in REQUIREMENTS.md § 1):
- Panel: SunUP SR10-36M, 10 W.
- Battery: 1S3P with an external protection board.
- Cables: all < 1 m.
- Gateway: about 20 m away.
- Budget: none set.

Still open: the enclosure (D11) and the board quantity.

The new questions from F1 (14 of them) are in [ARCHITECTURE.md § 8](ARCHITECTURE.md#8-open-questions-for-mobric). The most important are:
- whether the battery is wired in series or parallel;
- shading and tilt at the panel;
- today's sleep current and the CN3791 divider, measured with a multimeter;
- the connector on the BME680 cable.

## Risks

Risks found in F1 (cold Voc against the CN3791 limits, the cold-charge inhibit, the radio driver on core 3.3.11, and others) are listed in [ARCHITECTURE.md § 7](ARCHITECTURE.md#7-risks-and-bench-tests-f6).

- **R1. atopile 0.15.9 can't read layouts saved by KiCad 10.** Found 25.10.2026 on a scratch copy: after `kicad-cli pcb upgrade` moved the file from format 20241229 to 20260206, `ato build` failed at "Loading PCB" with `UnexpectedType in kicad.pcb.Layer field 'tenting'`. KiCad can't save in the older format.
  - **Decided 25.10.2026 by mobric (relayed by pcb-head): option (a).** This layout is edited in KiCad 9.0.x, installed next to KiCad 10. mobric installs it himself (it needs sudo).
  - KiCad 9 path: TBD until the install.
  - Until mobric confirms the install, nobody saves `layouts/default/default.kicad_pcb` in KiCad 10. Viewing it is fine.
  - `kicad-cli` 10 is safe on this board. DRC, render, and exports of gerbers, drill, positions and STEP left a KiCad 9 board byte-identical (checked 25.10.2026). They do create a `.kicad_prl` next to it, which git ignores.
  - After the install: record the KiCad 9 path here, and check one KiCad 9 save followed by `ato build` on a scratch copy.

## Who works on what

| Who | Role | Now |
|---|---|---|
| mobric | Owner. Approves decisions, orders and payment, firmware flashing, changes outside this folder | F1 open questions; installing KiCad 9.0.x (R1); then approving D2–D12 |
| `mobric/pcb-head` | Coordinator: briefs, gates, this file | Routing the F1 review |
| `mobric/pcb-opus-5-5` | Designer (Claude Code): atopile code, documents, KiCad, enclosure, firmware branch | F1 draft done; waiting for review comments |
| `mobric/mikolaj-codex` | Reviewer (Codex): checks against datasheets, writes `docs/reviews/F<n>-codex.md`, doesn't edit designer files | F1 review, once the coordinator routes it |

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
