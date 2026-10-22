# G.R.E.M. bench-test checklist (do in this order, tick each before the next)
Do all of this on the desk, OUTSIDE the case, with loose wires or a breadboard. Only assemble into the case after everything passes.

## A. Parts arrive - check (10 min)
- [ ] Count everything against GREM_parts_list.csv.
- [ ] Measure the MCP23017 breakout (length x width, mm) and send me the numbers.
- [ ] Look at a KY-040 shaft: round or with a flat (D-shaped)? Length above the nut? Send me a photo.
- [ ] Rocker switch: measure body depth behind the panel.

## B. ESP32 alone (USB only, no battery)
- [ ] Install VS Code + PlatformIO. Plug in ESP32 over USB.
- [ ] Upload firmware stage 1 (pio run -e stage1 -t upload). Success = it compiles and uploads. Send me any error text.

## C. Power chain, ESP32 DISCONNECTED
- [ ] Battery -> TP4056 -> rocker -> XL6009 input. Switch on.
- [ ] Multimeter on XL6009 output; turn trimmer to exactly 5.0 V (stop if it ever reads above 5.3 V). Switch off.
- [ ] Charge test: switch OFF, plug USB-C into TP4056; red LED = charging, blue/green = full.
- [ ] Only then connect XL6009 5V/GND to ESP32 5V/GND. Switch on: ESP32 should boot with no USB attached.

## D. Peripherals one at a time (stage firmware 1 -> 4)
- [ ] OLED: shows the screen (stage 1). Blank = interface jumpers on the display board.
- [ ] MCP23017: serial monitor says FOUND and the I2C scan lists 0x20.
- [ ] Each key: press all 9, correct square fills.
- [ ] Each dial (stage 2): clockwise goes up; push registers.
- [ ] USB + Bluetooth (stage 3): shortcuts reach CapCut / After Effects; pairs as "G.R.E.M.".
- [ ] Haptics (stage 4): scan lists 0x5A; click on every key; motor on 3V3 (never 5V).

## E. Soak test before closing the case
- [ ] Run 30 minutes on battery: nothing hot (XL6009, TP4056, ESP32 should be warm at most).
- [ ] Battery voltage afterwards still above 3.6 V.
