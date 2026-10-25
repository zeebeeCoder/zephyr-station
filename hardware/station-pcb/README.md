# Zephyr station PCB

Custom PCB for the Zephyr outdoor weather station. It replaces the current prototype, an ESP32 dev kit with sensor and radio modules on wires. The schematic is written in [atopile](https://atopile.io) and compiles to a KiCad layout.

Phase, decisions and open questions are in [docs/STATUS.md](docs/STATUS.md).

## Build

```sh
cd hardware/station-pcb
ato build
```

This needs atopile 0.15.9, signed in with `ato auth login` (part picking uses the atopile service). Outputs land in `build/`, which git ignores.

- `main.ato`: the top-level module `App`, the entry of the `default` build in `ato.yaml`.
- `layouts/default/default.kicad_pcb`: the board, which `ato build` creates and updates.

## KiCad

Edit the layout in KiCad 9.0.x, installed next to KiCad 10 (install path: TBD until mobric installs it). KiCad 10 saves boards in a newer format that atopile 0.15.9 can't read, and KiCad can't save back to the old one (risk R1 in [docs/STATUS.md](docs/STATUS.md)). Open the board from KiCad 9 itself rather than by double-clicking it in Finder, which may launch KiCad 10.

Until mobric confirms the KiCad 9 install, don't save `layouts/default/default.kicad_pcb` in KiCad 10. Viewing it is fine, and so is `kicad-cli` 10 for DRC, renders and exports, which leave the file unchanged.
