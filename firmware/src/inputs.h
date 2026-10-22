#pragma once
// Reads the 14 switches (through the MCP23017) and the 5 quadrature encoders.
#include <Wire.h>
#include <Adafruit_MCP23X17.h>
#include "config.h"

typedef void (*KeyCb)(int idx, bool pressed);   // idx 0-8
typedef void (*DialCb)(int idx, int dir);       // dir +1 / -1
typedef void (*DialSwCb)(int idx, bool pressed);// idx 0-4

static Adafruit_MCP23X17 mcp;
static KeyCb onKey = nullptr;
static DialCb onDial = nullptr;
static DialSwCb onDialSw = nullptr;

// ---- full-step quadrature table (one count per physical click) ----
#define R_START 0x0
#define R_CW_FINAL 0x1
#define R_CW_BEGIN 0x2
#define R_CW_NEXT 0x3
#define R_CCW_BEGIN 0x4
#define R_CCW_FINAL 0x5
#define R_CCW_NEXT 0x6
#define DIR_CW 0x10
#define DIR_CCW 0x20
static const uint8_t ttable[7][4] = {
  {R_START,    R_CW_BEGIN,  R_CCW_BEGIN, R_START},
  {R_CW_NEXT,  R_START,     R_CW_FINAL,  R_START | DIR_CW},
  {R_CW_NEXT,  R_CW_BEGIN,  R_START,     R_START},
  {R_CW_NEXT,  R_CW_BEGIN,  R_CW_FINAL,  R_START},
  {R_CCW_NEXT, R_START,     R_CCW_BEGIN, R_START},
  {R_CCW_NEXT, R_CCW_FINAL, R_START,     R_START | DIR_CCW},
  {R_CCW_NEXT, R_CCW_FINAL, R_CCW_BEGIN, R_START},
};
static uint8_t encState[NUM_ENC];

static bool swStable[NUM_INPUTS];     // true = pressed
static bool swRaw[NUM_INPUTS];
static uint32_t swChangedAt[NUM_INPUTS];

// returns false if the MCP23017 was not found on the I2C bus
static bool inputsBegin() {
  Wire.begin(I2C_SDA, I2C_SCL, 400000);
  bool ok = mcp.begin_I2C(MCP_ADDR, &Wire);
  if (ok) for (int p = 0; p < 16; p++) mcp.pinMode(p, INPUT_PULLUP);
  for (int i = 0; i < NUM_ENC; i++) {
    pinMode(ENC_PINS[i].a, INPUT_PULLUP);
    pinMode(ENC_PINS[i].b, INPUT_PULLUP);
    encState[i] = R_START;
  }
  return ok;
}

static int inputPin(int n) { return n < NUM_KEYS ? MCP_KEY_PIN[n] : MCP_ENC_SW_PIN[n - NUM_KEYS]; }

// call as often as possible (every loop pass)
static void inputsPoll() {
  uint32_t now = millis();
  // ---- encoders: plain GPIO, fast ----
  for (int i = 0; i < NUM_ENC; i++) {
    uint8_t pinstate = (digitalRead(ENC_PINS[i].b) << 1) | digitalRead(ENC_PINS[i].a);
    encState[i] = ttable[encState[i] & 0x0f][pinstate];
    uint8_t d = encState[i] & 0x30;
    if (d && onDial) {
      int dir = (d == DIR_CW) ? 1 : -1;
      if (ENC_REVERSE) dir = -dir;
      onDial(i, dir);
    }
  }
  // ---- switches: one I2C read for all 16 ----
  uint16_t bits = mcp.readGPIOAB();
  for (int n = 0; n < NUM_INPUTS; n++) {
    bool pressed = !((bits >> inputPin(n)) & 1);   // pull-ups: LOW = pressed
    if (pressed != swRaw[n]) { swRaw[n] = pressed; swChangedAt[n] = now; }
    if (swRaw[n] != swStable[n] && now - swChangedAt[n] >= DEBOUNCE_MS) {
      swStable[n] = swRaw[n];
      if (n < NUM_KEYS) { if (onKey) onKey(n, swStable[n]); }
      else if (onDialSw) onDialSw(n - NUM_KEYS, swStable[n]);
    }
  }
}
