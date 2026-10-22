# G.R.E.M. - Grading, Rendering & Editing Machine

A wireless editing macro console for video editors: ESP32-S3, 3.12" SSD1322 OLED, 3x3 MX keys, five haptic dials, USB + Bluetooth HID, 18650 battery, 3D-printed wedge enclosure. Built for CapCut and After Effects.

**Status:** work in progress. CAD checked in software (no part overlaps); firmware written but not yet verified on hardware.

| Folder | What's inside |
|---|---|
| `cad/` | Printable STL/STEP files, full assembly (122 parts), BOM, renders, CadQuery source, print instructions |
| `firmware/` | PlatformIO project (4 test stages + final firmware), pin config |
| `docs/` | Parts list, wiring list, bench-test checklist, 3D blueprint, notes |

Print in PETG, 0.4 mm nozzle, 0.20 mm layers, 4 walls, 30% infill. Print the test tile and knob test pieces first (see `cad/PRINT_INSTRUCTIONS.txt`).
