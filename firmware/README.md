# G.R.E.M. firmware (ESP32-S3 N16R8)

NOT yet compiled or run on real hardware (the build servers were unreachable from where it was written).
Expect a few small fixes the first time you build. Do the stages in order and fix each before moving on.

## One-time setup (Windows)
1. Install **VS Code**, then its extension **PlatformIO IDE**. Open the `grem_fw` folder in VS Code.
   PlatformIO downloads the ESP32 toolchain and libraries by itself (needs internet, takes a few minutes).
2. Plug the ESP32-S3 into the PC with USB (use the port marked USB, not UART, if there are two).
3. If upload fails: hold **BOOT**, tap **RST**, release BOOT, upload again.

## The stages (run each, test, then go to the next)
| Stage | Command (PlatformIO terminal)      | What you should see |
|-------|-------------------------------------|---------------------|
| 1     | `pio run -e stage1 -t upload`       | OLED shows the UI; pressing a key fills its square. `pio device monitor` prints "MCP23017 ... FOUND" and the I2C scan (0x20 = MCP23017, 0x5A = DRV2605L). |
| 2     | `pio run -e stage2 -t upload`       | Turning a dial changes its counter (right side of OLED). Clockwise must go up - if not, set `ENC_REVERSE` true in `config.h`. |
| 3     | `pio run -e stage3 -t upload`       | Keys send CapCut or After Effects shortcuts (open the app to test). Pair "G.R.E.M." in Bluetooth settings too. Hold the VOLUME dial push 1 s = switch CapCut / After Effects. Hold the BIG dial push 1 s = switch USB+BT / USB / BT. |
| 4     | `pio run -e stage4 -t upload`       | Same as 3 plus haptic clicks. |
| 5     | `pio run -e grem -t upload`         | FINAL: stage 4 + desk buddy (see below). |

## If something doesn't work
- **"MCP23017 NOT FOUND"**: check SDA=GPIO8, SCL=GPIO9, 3V3, GND, and the A0/A1/A2 address pins on the breakout (all low = 0x20).
- **OLED blank**: most 3.12" SSD1322 boards need the interface-select jumpers/resistors set for 4-wire SPI (see the seller's page). Also check the 5 pins in `config.h`.
- **Key N does the wrong thing / wrong key lights**: wiring order differs from `MCP_KEY_PIN` in `config.h` - just edit that table.
- **Changing what keys do**: edit `src/actions.h` only. Two profiles: CapCut and After Effects. Check every shortcut against the app's own shortcut list (versions differ), especially CapCut's Up/Down arrow (previous/next clip) and Shift+arrow.
- **Haptics weak/none**: stage-4 log says "DRV2605L not found" -> check address 0x5A and 3V3; make sure the coin motor is on the DRV2605L OUT pins.

## Pin assumptions you must match when wiring (edit config.h if you choose otherwise)
- OLED: CS 10, MOSI/DIN 11, CLK 12, DC 13, RST 14.
- I2C: SDA 8, SCL 9 (MCP23017 0x20, DRV2605L 0x5A).
- Dials A/B: small 1 = 4/5, small 2 = 6/7, small 3 = 15/16, small 4 = 17/18, BIG = 1/2.
- MCP23017: keys 1-9 on pins GPA0..GPA7 + GPB0; dial push-switches on GPB1..GPB5 (small 1-4 then BIG).

## Desk buddy (stage 5, no extra hardware)
- Hold the VOLUME dial push 1 s to cycle profiles: CapCut -> After Effects -> BUDDY.
- In CapCut / After Effects the OLED shows an animated face after 45 s with no input; it gets sleepy at 1 min, sleeps at 3 min, and wakes up surprised when you touch anything.
- BUDDY profile = face + focus timer. Keys: 1 start/pause, 2 reset, 3 skip focus<->break, 4 pet (happy), 5 sleep, 6 startle. Small dial 2 = focus minutes (5-90), small dial 3 = break minutes (1-30). Big dial push = start/pause.
- When a timer finishes the eyes shake and the motor buzzes three times; it then switches focus <-> break and waits for you to start the next one.
- The buddy has no real-time clock (nothing in the hardware to keep time), so no clock face yet.
