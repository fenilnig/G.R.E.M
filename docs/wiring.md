# G.R.E.M. wiring list (matches firmware/config.h)

Rule of thumb: every GND goes to ONE common ground. Everything except the ESP32's 5V pin runs on 3V3.

## 1. Power chain (do this first, with the ESP32 NOT connected)
1. 18650 (protected) -> TP4056: cell + to B+, cell - to B-.
2. TP4056 OUT+ -> rocker switch -> XL6009 IN+. TP4056 OUT- -> XL6009 IN-.
3. Connect a multimeter to XL6009 OUT+/OUT-. Switch on. Turn the trimmer until it reads exactly 5.0 V. Switch off.
4. XL6009 OUT+ -> ESP32 5V pin. XL6009 OUT- -> ESP32 GND.
5. Charging: switch the rocker OFF while charging over the TP4056 USB-C (no power-path protection).
Never connect the ESP32 to the XL6009 before step 3. Never plug USB into the ESP32 and run it from the boost at the same time while testing unless you know the 5V pins are isolated - use one or the other.

## 2. 3V3 rail (ESP32 3V3 pin feeds all of this)
ESP32 3V3 -> OLED VCC, MCP23017 VCC, DRV2605L VIN, all five KY-040 "+" pins.
ESP32 GND -> OLED GND, MCP23017 GND, DRV2605L GND, all five KY-040 GND, one side of every key switch.

## 3. OLED (SSD1322, 4-wire SPI)
| OLED pin | ESP32 GPIO |
|---|---|
| CS | 10 |
| DIN / MOSI / D1 | 11 |
| CLK / SCK / D0 | 12 |
| DC / A0 | 13 |
| RES / RST | 14 |
| VCC / GND | 3V3 / GND |
Set the board's interface jumpers/resistors for 4-wire SPI before powering (see the seller's page).

## 4. I2C bus (shared)
| Signal | ESP32 GPIO | Goes to |
|---|---|---|
| SDA | 8 | MCP23017 SDA, DRV2605L SDA |
| SCL | 9 | MCP23017 SCL, DRV2605L SCL |
MCP23017: A0, A1, A2 -> GND (address 0x20). RESET -> 3V3 (never leave it floating). INT -> GPIO 21 (optional, firmware doesn't need it).
DRV2605L: address is fixed 0x5A. If the board has an EN pin, tie it to 3V3. Coin motor wires -> OUT+ / OUT- (either order). IN/TRIG not used.

## 5. Keys (one wire from each switch to the MCP23017, the other wire to GND; no diodes)
Layout seen from the front:   K1 K2 K3 (rear, next to OLED) / K4 K5 K6 / K7 K8 K9 (front)
| Key | MCP23017 pin | Key | MCP23017 pin |
|---|---|---|---|
| K1 | GPA0 | K6 | GPA5 |
| K2 | GPA1 | K7 | GPA6 |
| K3 | GPA2 | K8 | GPA7 |
| K4 | GPA3 | K9 | GPB0 |
| K5 | GPA4 | | |

## 6. Dials (KY-040: GND, +, SW, DT, CLK)
| Dial | CLK -> ESP32 | DT -> ESP32 | SW -> MCP23017 |
|---|---|---|---|
| Small 1 (volume), leftmost | GPIO 4 | GPIO 5 | GPB1 |
| Small 2 (zoom) | GPIO 6 | GPIO 7 | GPB2 |
| Small 3 | GPIO 15 | GPIO 16 | GPB3 |
| Small 4 | GPIO 17 | GPIO 18 | GPB4 |
| BIG dial | GPIO 1 | GPIO 2 | GPB5 |
KY-040 "+" -> 3V3 (NOT 5V). If a dial turns the wrong way, swap in software (ENC_REVERSE) or swap CLK/DT.

## 7. Don't use these ESP32 pins
GPIO 19/20 (USB), 35/36/37 (internal memory on the N16R8), 0/3/45/46 (boot straps).

## 8. Check before first power-up
- Multimeter continuity: battery + never touches GND; 3V3 never touches GND; 5V never touches 3V3.
- Power up on USB only first (battery disconnected) and run firmware stage 1.
