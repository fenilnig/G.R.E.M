// STAGE 3 - USB + Bluetooth keyboard output, CapCut / After Effects profiles (no haptics yet).
// Hold VOLUME dial push 1 s = switch profile. Hold BIG dial push 1 s = USB+BLE / USB only / BLE only.
#include <Arduino.h>
#include "display.h"
#include "inputs.h"
#include "actions.h"

static uint32_t downAt[NUM_ENC] = {};
static void showStatus() {
  snprintf(ui.title, sizeof ui.title, "G.R.E.M.  %s", PROF().name);
  snprintf(ui.status, sizeof ui.status, "%s %s", outModeName(), bleConnected ? "BT:ON" : "BT:--");
}

static void keyEvent(int k, bool pressed) {
  ui.keyDown[k] = pressed;
  if (!pressed) return;
  const Action& a = PROF().keys[k];
  doAction(a);
  snprintf(ui.action, sizeof ui.action, "%s", a.name);
  snprintf(ui.detail, sizeof ui.detail, "key %d", k + 1);
}
static void dialEvent(int d, int dir) {
  ui.dialCount[d] += dir;
  const Action& a = dir > 0 ? PROF().dials[d].cw : PROF().dials[d].ccw;
  doAction(a);
  snprintf(ui.action, sizeof ui.action, "%s", a.name);
  snprintf(ui.detail, sizeof ui.detail, "%s", PROF().dials[d].label);
}
// Dial pushes. Hold small dial 1 (VOLUME) = switch profile. Hold BIG dial = change USB/BT output.
static void dialSwEvent(int d, bool pressed) {
  if (d == 0 || d == 4) {                         // these two support press-and-hold
    if (pressed) { downAt[d] = millis(); return; }  // decide on release
    if (millis() - downAt[d] >= LONG_PRESS_MS) {
      if (d == 0) { curProfile = (curProfile + 1) % 2; snprintf(ui.action, sizeof ui.action, "%s", PROF().name); snprintf(ui.detail, sizeof ui.detail, "profile"); }
      else { hidCycleMode(); snprintf(ui.action, sizeof ui.action, "OUT: %s", outModeName()); ui.detail[0] = 0; }
      return;
    }
  } else if (!pressed) return;
  const Action& a = PROF().dials[d].push;
  doAction(a);
  snprintf(ui.action, sizeof ui.action, "%s", a.name);
  snprintf(ui.detail, sizeof ui.detail, "%s push", PROF().dials[d].label);
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  displayBegin();
  if (!inputsBegin()) snprintf(ui.action, sizeof ui.action, "NO MCP23017");
  hidBegin();
  onKey = keyEvent; onDial = dialEvent; onDialSw = dialSwEvent;
}
void loop() {
  inputsPoll();
  hidService();
  static uint32_t t = 0;
  if (millis() - t > 300) { t = millis(); showStatus(); }
}
