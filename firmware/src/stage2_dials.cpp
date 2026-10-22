// STAGE 2 - adds the 5 dials. Turn a dial: its counter on the OLED goes up (clockwise) / down.
// Push a dial: logged. If a dial counts backwards set ENC_REVERSE in config.h.
#include <Arduino.h>
#include "display.h"
#include "inputs.h"

static void keyEvent(int k, bool pressed) {
  ui.keyDown[k] = pressed;
  if (pressed) snprintf(ui.action, sizeof ui.action, "KEY %d", k + 1);
}
static void dialEvent(int d, int dir) {
  ui.dialCount[d] += dir;
  if (d == 4) snprintf(ui.action, sizeof ui.action, "DIAL BIG");
  else snprintf(ui.action, sizeof ui.action, "DIAL %d", d + 1);
  snprintf(ui.detail, sizeof ui.detail, dir > 0 ? "clockwise" : "counter-clockwise");
  Serial.printf("dial %d %s (total %d)\n", d, dir > 0 ? "CW" : "CCW", ui.dialCount[d]);
}
static void dialSwEvent(int d, bool pressed) {
  if (pressed) { snprintf(ui.action, sizeof ui.action, "PUSH %d", d + 1); snprintf(ui.detail, sizeof ui.detail, "dial switch"); }
  Serial.printf("dial-switch %d %s\n", d, pressed ? "DOWN" : "up");
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  displayBegin();
  snprintf(ui.title, sizeof ui.title, "G.R.E.M.  stage 2");
  if (!inputsBegin()) snprintf(ui.action, sizeof ui.action, "NO MCP23017");
  onKey = keyEvent; onDial = dialEvent; onDialSw = dialSwEvent;
}
void loop() { inputsPoll(); }
