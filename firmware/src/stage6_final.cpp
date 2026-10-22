// STAGE 6 = FINAL FIRMWARE
//  Macro console (CapCut / After Effects, editable key map) + desk buddy + PC link (clock, now playing,
//  notifications, CPU/GPU load, auto profile, render-finished reaction).
// Hold VOLUME dial push 1 s = next profile: CAPCUT -> AFTER EFFECTS -> BUDDY -> DASH.
// Hold BIG dial push 1 s    = USB+BLE / USB only / BLE only.
#include <Arduino.h>
#include "display.h"
#include "inputs.h"
#include "actions.h"
#include "haptics.h"
#include "buddy.h"
#include "companion.h"

static const int NUM_PROFILES = 4;                 // 0 CapCut, 1 After Effects, 2 Buddy, 3 Dash
static const char* PROFILE_NAMES[NUM_PROFILES] = {"CAPCUT", "AFTER EFFECTS", "BUDDY", "DASH"};
static uint32_t downAt[NUM_ENC] = {};
static bool isMacro() { return curProfile < 2; }

static void showStatus() {
  snprintf(ui.title, sizeof ui.title, "G.R.E.M.  %s", PROFILE_NAMES[curProfile]);
  if (millis() < comp.nUntil) snprintf(ui.status, sizeof ui.status, "! %.17s", comp.nText);   // notification in the top bar
  else snprintf(ui.status, sizeof ui.status, "%s %s%s", outModeName(), bleConnected ? "BT" : "--", comp.linked ? " PC" : "");
}

static void keyEvent(int k, bool pressed) {
  ui.keyDown[k] = pressed;
  if (!pressed) return;
  buddyPoke();
  if (!isMacro()) { if (curProfile == 2) buddyKey(k); hapticKey(); return; }
  const Action& a = RT_KEY[curProfile][k];
  doAction(a);
  hapticKey();
  snprintf(ui.action, sizeof ui.action, "%s", a.name);
  snprintf(ui.detail, sizeof ui.detail, "key %d", k + 1);
}
static void dialEvent(int d, int dir) {
  ui.dialCount[d] += dir;
  buddyPoke();
  if (!isMacro() && d != 0) {                      // BUDDY: small dial 2 = focus minutes, 3 = break minutes
    if (curProfile == 2) { if (d == 1) buddyAdjustFocus(dir); else if (d == 2) buddyAdjustBreak(dir); }
    hapticDial(); return;
  }
  const int p = isMacro() ? curProfile : 0;        // volume dial works in every profile (CapCut table)
  const Action& a = RT_DIAL[p][d][dir > 0 ? 0 : 1];
  doAction(a);
  hapticDial();
  snprintf(ui.action, sizeof ui.action, "%s", a.name);
  snprintf(ui.detail, sizeof ui.detail, "%s", PROFILES[p].dials[d].label);
}
static void dialSwEvent(int d, bool pressed) {
  if (pressed) buddyPoke();
  if (curProfile == 2 && d == 4 && pressed) { downAt[4] = millis(); buddyStartPause(); hapticKey(); return; }
  if (d == 0 || d == 4) {                           // these two support press-and-hold
    if (pressed) { downAt[d] = millis(); return; }
    if (millis() - downAt[d] >= LONG_PRESS_MS) {
      if (d == 0) { curProfile = (curProfile + 1) % NUM_PROFILES; snprintf(ui.action, sizeof ui.action, "%s", PROFILE_NAMES[curProfile]); snprintf(ui.detail, sizeof ui.detail, "profile"); }
      else { hidCycleMode(); snprintf(ui.action, sizeof ui.action, "OUT: %s", outModeName()); ui.detail[0] = 0; }
      hapticMode();
      return;
    }
  } else if (!pressed) return;
  if (!isMacro()) { if (d == 0) hidConsumer(C_MUTE); return; }
  const Action& a = RT_DIAL[curProfile][d][2];
  doAction(a);
  hapticKey();
  snprintf(ui.action, sizeof ui.action, "%s", a.name);
  snprintf(ui.detail, sizeof ui.detail, "%s push", PROFILES[curProfile].dials[d].label);
}

static void routedDraw() { drawRouter(curProfile, millis() - bd.lastInput); }

void setup() {
  Serial.begin(115200);
  delay(1500);
  keymapLoad();
  displayBegin();
  if (!inputsBegin()) snprintf(ui.action, sizeof ui.action, "NO MCP23017");
  hidBegin();
  buddyBegin();
  buddyDrawFn = routedDraw;
  clockFn = compClock;
  if (!hapticsBegin()) Serial.println("DRV2605L not found - continuing without haptics");
  onKey = keyEvent; onDial = dialEvent; onDialSw = dialSwEvent;
}

void loop() {
  inputsPoll();
  hidService();
  compPoll();
  buddyTick();
  if (bd.alarmFlag) { bd.alarmFlag = false; hapticAlarm(); }
  if (comp.nTick) { comp.nTick = false; hapticDial(); }
  if (comp.appChanged) {                            // auto profile: follow the app the PC says is in front
    comp.appChanged = false;
    if (isMacro() && comp.appHint) {
      int want = comp.appHint == 1 ? 0 : 1;
      if (want != curProfile) { curProfile = want; snprintf(ui.action, sizeof ui.action, "AUTO: %s", PROFILE_NAMES[curProfile]); ui.detail[0] = 0; hapticMode(); }
    }
  }
  bd.showTimer = bd.running || curProfile == 2;
  uint32_t idle = millis() - bd.lastInput;
  bool notif = millis() < comp.nUntil;
  uiBuddyView = !isMacro() || buddyAlarmShowing() || idle > 45000UL || (notif && comp.nRender);
  static uint32_t t = 0;
  if (millis() - t > 300) { t = millis(); showStatus(); }
}
