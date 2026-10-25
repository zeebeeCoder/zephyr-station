# Station PCB status

Updated 25.10.2026. Maintained by the coordinator, `mobric/pcb-head`; created in F0 by `mobric/pcb-opus-5-5`.

## Phase

**F0 (workspace setup): done 25.10.2026, waiting for the coordinator's check.**

F1 (requirements and architecture) starts with the coordinator's brief, once mobric has sent the missing data below.

Sequence: F0 setup → F1 requirements and architecture → F2 atopile schematic → F3 KiCad layout → F4 production files → F5 enclosure and firmware (in parallel from F3) → F6 bring-up. Every phase ends at a gate, and the next one doesn't start without approval.

## Decisions

| # | Topic | State |
|---|---|---|
| D1 | Project location: `zephyr-station/hardware/station-pcb/` on branch `hardware/station-pcb` | approved 25.10.2026 |
| D2 | Microcontroller | open |
| D3 | Programming interface | open |
| D4 | Radio | open |
| D5 | Solar charging | open |
| D6 | 3.3 V rail | open |
| D7 | 5 V rail for the PMS7003 | open |
| D8 | BME680 placement | open |
| D9 | Power measurement | open |
| D10 | Spare inputs (wind vane, 1-Wire) | open |
| D11 | Board size and enclosure | open |
| D12 | Manufacturing | open |

F1 presents D2–D12 with recommendations, cost and firmware impact for mobric to approve.

## Open questions for mobric

1. Solar panel: Voc/Vmp and wattage.
2. Battery pack (10 200 mAh): cell count, its own BMS or not, connector.
3. Cable lengths to the anemometer, the BME680 and the panel.
4. Enclosure: an existing one (dimensions) or designed from scratch.
5. Budget and number of boards.
6. Distance from the station to the gateway (affects the antenna).

## Risks

- **R1. atopile 0.15.9 can't read layouts saved by KiCad 10** (checked 25.10.2026 on a scratch copy). After `kicad-cli pcb upgrade` moved the file from format 20241229 to 20260206, `ato build` failed at "Loading PCB" with `UnexpectedType in kicad.pcb.Layer field 'tenting'`. KiCad can't save in the older format, so once the layout is saved in KiCad 10, atopile can no longer update it. Needs a decision before F3.

## Who works on what

| Who | Role | Now |
|---|---|---|
| mobric | Owner. Approves decisions, orders and payment, firmware flashing, changes outside this folder | Answering the open questions |
| `mobric/pcb-head` | Coordinator: briefs, gates, this file | Checking F0, then the F1 brief |
| `mobric/pcb-opus-5-5` | Designer (Claude Code): atopile code, documents, KiCad, enclosure, firmware branch | F0 done, waiting for the F1 brief |
| `mobric/mikolaj-codex` | Reviewer (Codex): checks against datasheets, writes `docs/reviews/F<n>-codex.md`, doesn't edit designer files | Waiting for the F1 draft |

The handoff session `mobric/projektowanie-custom-pcb-z-ai` delivered the project context on 25.10.2026 and does no further work.

## Ground rules

- Work happens only in `hardware/station-pcb/`, on branch `hardware/station-pcb` (worktree `~/Documents/MIKO/zephyr-station-pcb`). The rest of zephyr-station is shared, so changes outside this folder need mobric's approval.
- No push without approval.
- Firmware is compile-only (`just esp cook station`). Flashing is locked until PKM task 2026-09-04-T0001 is closed and needs mobric's consent.

## Tooling (checked 25.10.2026)

- atopile 0.15.9, signed in (part picking needs it). It's the last classic CLI, in maintenance mode only; the successor is app.atopile.io (0.16+).
- Every `ato` command warns "Could not find KiCad plugin path" and "Couldn't enable plugin api". atopile 0.15.9 only knows KiCad 9.0 paths (`KICAD_VERSION = "9.0"` in `faebryk/libs/kicad/paths.py`) and this Mac has KiCad 10.0.7, so the atopile KiCad plugin isn't installed. Builds aren't affected.
- `kicad-cli` 10.0.7 isn't on PATH: `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`.
- `ato create project` runs `git init` unless its target is a repository root. Inside this monorepo, generate the project elsewhere and copy it in (F0 did this).
- The template `.gitignore` ignores `*.csv`, `*.xml` and `lib/`. Adjust it before committing JLC BOM/CPL files or a local library folder.
