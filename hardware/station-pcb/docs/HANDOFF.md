# Zephyr PCB — migration handoff (28.10.2026)

## State and authority

Migration was approved by Mikołaj on 28.10.2026; this permits documenting, committing and pushing the handoff, **not resuming engineering work**. Analysis, design, review and enclosure work remain paused until explicit approval.

- Branch: `hardware/station-pcb`; engineering baseline: `fd1c0fef29b1ecaca7e0de6280eb5828806d3b7c` (F1 revision 6).
- **F1 NOT READY** after the final seventh review: 2 major, 1 minor, 2 notes; R6-M2 separately remains open. No F2 approval, no production-ready PCB or enclosure CAD.
- Latest review: [F1-pi-r7.md](reviews/F1-pi-r7.md). SHA256: `0e0e38972f072b7e0c568b0e15148a1fc4d21fdc927d9487e5957dba64c48d67`.
- Independent Astra analysis: [report](reviews/zephyr-astra-analysis-20261027.md), [brief](briefs/zephyr-astra-analysis-20261027.md). Report SHA256: `b96abe0c4f963ee5fc7b1cd284c41653ef9e037dd66041874c789528e67e6d8b`.
- Base requirements and architecture: [REQUIREMENTS.md](REQUIREMENTS.md), [ARCHITECTURE.md](ARCHITECTURE.md); previous response: [F1-response-r6.md](reviews/F1-response-r6.md). Recommendations in them are not automatic approvals.
- Enclosure: [README](../enclosure/README.md), especially “State and next steps (28.10.2026)”; [coordinator review](reviews/enclosure-draft-a-2026-10-27.md). Draft B exists as a specification, not a CAD model or print approval.

## Open work — only after a new brief

- R6-M2: panel-input switching/recovery envelope; owner decision A–D remains pending. Astra's A/B/C analysis is exploratory and does not replace owner approval.
- R7-M1: numerical certification of the interlock envelope; R7-M2: surge di/dt condition; R7-m1: residual-charge uncertainty guardband.
- Astra flags negative/differential eFuse voltages as the first go/no-go for a possible limited variant-B study. No such study has been authorized.
- C_HOT is an unapproved proposal. No approval to change LT3652, battery pack, temperature limits or surge amplitude. Winter rerun only after choosing new thresholds.
- Enclosure awaits F3 board interface and physical measurements (see its README). No manufacturing or flashing authorization.

## Restore on another computer

```sh
git clone --branch hardware/station-pcb https://github.com/zeebeeCoder/zephyr-station.git
cd zephyr-station/hardware/station-pcb
```

A fresh clone is preferable to copying the linked worktree: the old worktree's `.git` points into the original main repository using machine-specific paths. Do not copy that `.git` file into a fresh clone.

There is a separate **private migration archive**, outside Git, under `~/Documents/MIKO/zephyr-migration/` on the source Mac. Transfer its `.tar.gz` and matching `.sha256` file privately (USB/LAN/cloud), not to a public repository. It contains:

- `station-pcb/build/`: ignored research PDFs, source data (including PVGIS series), calculation evidence; about 420 MB uncompressed.
- `scratch/pcb-r6/`, `scratch/pcb-r7/`, `scratch/pcb-astra-analysis-20261027/`: temporary evidence/scripts/PDFs retained before `/tmp` cleanup.
- `coordinator/`: review reports, Astra brief and uploaded enclosure reference material.
- `context/`: Claude memory snapshots, team address book and optional designer inbox history. These may contain private or unrelated context; do not publish them or blindly overwrite configuration on the new machine.
- `git/`: an offline Git bundle of the PCB branch and `main`, plus recorded refs/status. The bundle excludes uncommitted files; the archive is created after the handoff commit.
- `MANIFEST.json`: SHA256 and size of every archived regular file; `RESTORE.md`: archive verification/restoration instructions.

Verify the archive checksum, extract it into a separate directory, then copy `station-pcb/build/` into the fresh clone's `hardware/station-pcb/build/`. Keep scratch/coordinator/context as reference. Old absolute paths in reports are historical; map them to the extracted directories. GitHub alone does not preserve the ignored source data or session context.

## Toolchain / safety

- atopile **0.15.9**, `ato auth login` for part picking; entry point `main.ato:App`, configured in `ato.yaml`.
- **KiCad 9.0.x for editing**. Do not save the board in KiCad 10: atopile 0.15.9 cannot read its upgraded format. KiCad 10 CLI was checked for read-only DRC/export, not layout saves. KiCad 9 installation/save-build check remains pending.
- Python 3.9+; calculation scripts in `docs/calc/` use stdlib. Do not launch expensive runs merely to restore the project. Historical interlock run: 11–17 minutes on 10 cores; future analysis concurrency should be limited to 2–4 unless agreed otherwise.
- Fusion 360 with Astra for future enclosure modeling; Bambu Studio with P2S profile for print checks. Versions not fixed.
- Install/authenticate tools on the destination; credentials are not part of the Git handoff. Do not copy full credential/config directories.
- `pcb-design` and `pcb-caseing`: Claude Code with `cc-intercom`; `pcb-review` and `pcb-analysis-astra`: Pi. Old session IDs, tmux pane numbers and local broker routes are not portable. This document and the reports are the durable handoff, not a promise of live-session restoration.

## Verification scope

This migration checks preservation, hashes, archive contents and Git publication. It does not rerun engineering calculations, certify the design, approve gates or resume paused work.
