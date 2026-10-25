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

Saving the layout in KiCad 10 converts it to a format that atopile 0.15.9 can't read (risk R1 in [docs/STATUS.md](docs/STATUS.md)).
