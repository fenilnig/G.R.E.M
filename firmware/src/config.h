#pragma once
#include <Arduino.h>
// ======================= G.R.E.M. pin + behaviour configuration =======================
// Change ONLY this file if your wiring differs.

// ---- OLED (SSD1322 256x64, 4-wire SPI, bit-banged so the pins can be anything) ----
#define OLED_CS    10
#define OLED_MOSI  11   // "SDA"/"DIN" on the OLED
#define OLED_CLK   12   // "SCL"/"CLK" on the OLED
#define OLED_DC    13
#define OLED_RST   14

// ---- I2C bus (MCP23017 @0x20, DRV2605L @0x5A) ----
#define I2C_SDA    8
#define I2C_SCL    9
#define MCP_ADDR   0x20

// ---- Rotary encoders (A,B pins). Index 0-3 = small dials left->right, 4 = big dial ----
struct EncPins { uint8_t a, b; };
constexpr EncPins ENC_PINS[5] = { {4,5}, {6,7}, {15,16}, {17,18}, {1,2} };
constexpr int NUM_ENC = 5;
// If a dial counts the wrong way round, flip this to true (flips ALL dials).
constexpr bool ENC_REVERSE = false;

// ---- MCP23017 pin numbers: GPA0..GPA7 = 0..7, GPB0..GPB7 = 8..15 ----
// 9 keys on MCP pins 0..8, key numbering:  0 1 2   (rear row, next to OLED)
//                                         3 4 5
//                                         6 7 8   (front row)
// 5 dial push-switches on MCP pins 9..13 (same order as the dials).
constexpr int NUM_KEYS = 9;
constexpr int MCP_KEY_PIN[NUM_KEYS] = {0,1,2,3,4,5,6,7,8};
constexpr int MCP_ENC_SW_PIN[NUM_ENC] = {9,10,11,12,13};
constexpr int NUM_INPUTS = NUM_KEYS + NUM_ENC;   // 14 switches total

constexpr uint16_t DEBOUNCE_MS = 8;
constexpr uint16_t LONG_PRESS_MS = 1000;   // hold big-dial push to change output mode
