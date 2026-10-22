// STAGE 5 = FINAL FIRMWARE: everything + desk-buddy (animated face, focus timer, screensaver).
// Hold VOLUME dial push 1 s = switch profile. Hold BIG dial push 1 s = USB+BLE / USB only / BLE only.
#include <Arduino.h>
#include "display.h"
#include "inputs.h"
#include "actions.h"
#include "haptics.h"
#include "buddy.h"

static uint32_t downAt[NUM_ENC] = {};
static const char* profName() { return curProfile == 2 ? "BUDDY" : PROF().name; }
static void showStatus() {
  snprintf(ui.title, sizeof ui.title, "G.R.E.M.  %s", profName());
  snprintf(ui.status, sizeof ui.status, "%s %s", outModeName(), bleConnected ? "BT:ON" : "BT:--");
}

static void keyEvent(int k, bool pressed) {
  ui.keyDown[k] = pressed;
  if (!pressed) return;
  buddyPoke();
  if (curProfile == 2) { buddyKey(k); hapticKey(); return; }
  const Action& a = PROF().keys[k];
  doAction(a);
  hapticKey();
  snprintf(ui.action, sizeof ui.action, "%s", a.name);
  snprintf(ui.detail, sizeof ui.detail, "key %d", k + 1);
}
static void dialEvent(int d, int dir) {
  ui.dialCount[d] += dir;
  buddyPoke();
  if (curProfile == 2 && d != 0) {               // BUDDY: small dial 2 = focus minutes, 3 = break minutes
    if (d == 1) buddyAdjustFocus(dir); else if (d == 2) buddyAdjustBreak(dir);
    hapticDial(); return;
  }
  const Action& a = dir > 0 ? PROF().dials[d].cw : PROF().dials[d].ccw;
  doAction(a);
  hapticDial();
  snprintf(ui.action, sizeof ui.action, "%s", a.name);
  snprintf(ui.detail, sizeof ui.detail, "%s", PROF().dials[d].label);
}
// Dial pushes. Hold small dial 1 (VOLUME) = switch profile. Hold BIG dial = change USB/BT output.
static void dialSwEvent(int d, bool pressed) {
  if (pressed) buddyPoke();
  if (curProfile == 2 && d == 4 && pressed) { downAt[4] = millis(); buddyStartPause(); hapticKey(); return; }   // BUDDY: big dial push = start/pause
  if (d == 0 || d == 4) {                         // these two support press-and-hold
    if (pressed) { downAt[d] = millis(); return; }  // decide on release
    if (millis() - downAt[d] >= LONG_PRESS_MS) {
      if (d == 0) { curProfile = (curProfile + 1) % 3; snprintf(ui.action, sizeof ui.action, "%s", profName()); snprintf(ui.detail, sizeof ui.detail, "profile"); }
      else { hidCycleMode(); snprintf(ui.action, sizeof ui.action, "OUT: %s", outModeName()); ui.detail[0] = 0; } hapticMode();
      return;
    }
  } else if (!pressed) return;
  if (curProfile == 2) return;                    // BUDDY: other pushes do nothing
  const Action& a = PROF().dials[d].push;
  doAction(a);
  hapticKey();
  snprintf(ui.action, sizeof ui.action, "%s", a.name);
  snprintf(ui.detail, sizeof ui.detail, "%s push", PROF().dials[d].label);
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  displayBegin();
  if (!inputsBegin()) snprintf(ui.action, sizeof ui.action, "NO MCP23017");
  hidBegin();
  buddyBegin();
  if (!hapticsBegin()) Serial.println("DRV2605L not found - continuing without haptics");
  onKey = keyEvent; onDial = dialEvent; onDialSw = dialSwEvent;
}
void loop() {
  inputsPoll();
  hidService();
  buddyTick();
  if (bd.alarmFlag) { bd.alarmFlag = false; hapticAlarm(); }
  bd.showTimer = bd.running || curProfile == 2;
  uiBuddyView = (curProfile == 2) || buddyAlarmShowing() || (millis() - bd.lastInput > 45000UL);
  static uint32_t t = 0;
  if (millis() - t > 300) { t = millis(); showStatus(); }
}
