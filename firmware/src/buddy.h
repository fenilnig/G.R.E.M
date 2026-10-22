#pragma once
// Desk-buddy: animated eyes on the OLED + focus/break timer. No extra hardware.
//  - BUDDY profile (3rd profile): face + timer, keys/dials control the timer.
//  - In CapCut / After Effects profiles the face appears after 45 s with no input (screensaver)
//    and falls asleep after 1 / 3 minutes. Touch anything and it wakes up surprised.
#include <Arduino.h>
#include "display.h"

enum BMood : uint8_t { BM_NORMAL, BM_HAPPY, BM_SURPRISED, BM_SLEEPY, BM_SLEEPING, BM_ALARM };

struct BuddyState {
  BMood forced = BM_NORMAL; uint32_t forcedUntil = 0;
  uint32_t lastInput = 0;
  bool running = false, onBreak = false, showTimer = false;
  uint32_t endAt = 0, leftWhenPaused = 0;
  uint8_t focusMin = 25, breakMin = 5, sessions = 0;
  volatile bool alarmFlag = false;
};
static BuddyState bd;
static bool (*clockFn)(char*, size_t) = nullptr;   // set by companion.h: fills "HH:MM", false if time unknown

static void buddyMood(BMood m, uint32_t ms) { bd.forced = m; bd.forcedUntil = millis() + ms; }
static void buddyPoke() {                      // call on every key / dial event
  uint32_t now = millis();
  if (now - bd.lastInput > 60000UL) buddyMood(BM_SURPRISED, 1200);
  bd.lastInput = now;
}

static uint32_t buddyDurMs() { return (uint32_t)(bd.onBreak ? bd.breakMin : bd.focusMin) * 60000UL; }
static uint32_t buddyLeftMs() {
  if (bd.running) { int32_t l = (int32_t)(bd.endAt - millis()); return l > 0 ? (uint32_t)l : 0; }
  return bd.leftWhenPaused ? bd.leftWhenPaused : buddyDurMs();
}
static void buddyStartPause() {
  if (bd.running) { bd.leftWhenPaused = buddyLeftMs(); bd.running = false; }
  else { bd.endAt = millis() + buddyLeftMs(); bd.running = true; bd.leftWhenPaused = 0; }
}
static void buddyReset() { bd.running = false; bd.leftWhenPaused = 0; }
static void buddySkip()  { bd.onBreak = !bd.onBreak; buddyReset(); }
static void buddyTick() {                      // call every loop pass
  if (bd.running && (int32_t)(millis() - bd.endAt) >= 0) {
    bd.running = false; bd.leftWhenPaused = 0;
    if (!bd.onBreak) bd.sessions++;
    bd.onBreak = !bd.onBreak;
    buddyMood(BM_ALARM, 5000);
    bd.alarmFlag = true;
  }
}
static void buddyAdjustFocus(int dir) { if (!bd.running && !bd.leftWhenPaused) bd.focusMin = constrain((int)bd.focusMin + dir * 5, 5, 90); }
static void buddyAdjustBreak(int dir) { if (!bd.running && !bd.leftWhenPaused) bd.breakMin = constrain((int)bd.breakMin + dir, 1, 30); }
static bool buddyAlarmShowing() { return millis() < bd.forcedUntil && bd.forced == BM_ALARM; }

static void eyeBox(int cx, int cy, int w, int h) {
  if (h < 2) h = 2;
  int r = h / 2 < 8 ? h / 2 : 8;
  u8g2.drawRBox(cx - w / 2, cy - h / 2, w, h, r);
}

static void drawBuddy() {
  uint32_t now = millis();
  BMood m = BM_NORMAL;
  if (now < bd.forcedUntil) m = bd.forced;
  else {
    uint32_t idle = now - bd.lastInput;
    if (idle > 180000UL) m = BM_SLEEPING; else if (idle > 60000UL) m = BM_SLEEPY;
  }
  if (bd.running && (m == BM_SLEEPY || m == BM_SLEEPING)) m = BM_NORMAL;   // stays awake while timing

  static uint32_t nextBlink = 0, blinkStart = 0, nextLook = 0;
  static float lx = 0, ly = 0, tx = 0, ty = 0;
  if (now > nextBlink) { blinkStart = now; nextBlink = now + 2000 + random(3500); }
  if (now > nextLook)  { tx = random(-12, 13); ty = random(-5, 6); nextLook = now + 2500 + random(3500); }
  lx += (tx - lx) * 0.25f; ly += (ty - ly) * 0.25f;
  int blinkH = 34; uint32_t bt = now - blinkStart;
  if (bt < 160) { float k = fabsf((float)bt - 80.0f) / 80.0f; blinkH = 4 + (int)(30 * k); }

  u8g2.clearBuffer();
  u8g2.setDrawColor(1);
  const int LX = 88, RX = 168, CY = 24;
  switch (m) {
    case BM_NORMAL:
      eyeBox(LX + (int)lx, CY + (int)ly, 38, blinkH);
      eyeBox(RX + (int)lx, CY + (int)ly, 38, blinkH);
      break;
    case BM_HAPPY:                               // ^ ^ eyes
      for (int t = -1; t <= 1; t++) {
        u8g2.drawLine(LX - 18, CY + 10 + t, LX, CY - 10 + t); u8g2.drawLine(LX, CY - 10 + t, LX + 18, CY + 10 + t);
        u8g2.drawLine(RX - 18, CY + 10 + t, RX, CY - 10 + t); u8g2.drawLine(RX, CY - 10 + t, RX + 18, CY + 10 + t);
      }
      break;
    case BM_SURPRISED:
      eyeBox(LX, CY, 44, 40); eyeBox(RX, CY, 44, 40);
      u8g2.setDrawColor(0); u8g2.drawDisc(LX, CY, 7); u8g2.drawDisc(RX, CY, 7); u8g2.setDrawColor(1);
      break;
    case BM_SLEEPY:
      eyeBox(LX, CY + 8, 38, 14); eyeBox(RX, CY + 8, 38, 14);
      break;
    case BM_SLEEPING: {
      u8g2.drawBox(LX - 18, CY + 10, 36, 4); u8g2.drawBox(RX - 18, CY + 10, 36, 4);
      u8g2.setFont(u8g2_font_helvB10_tr);
      int z = (now / 500) % 3; u8g2.drawStr(205 + z * 8, 24 - z * 7, "z");
      break; }
    case BM_ALARM: {
      int sh = ((now / 100) & 1) ? 3 : -3;
      eyeBox(LX + sh, CY, 40, 36); eyeBox(RX + sh, CY, 40, 36);
      break; }
  }
  if (bd.showTimer) {
    uint32_t s = buddyLeftMs() / 1000;
    const char* lab = bd.running ? (bd.onBreak ? "BREAK" : "FOCUS") : (bd.leftWhenPaused ? "PAUSED" : (bd.onBreak ? "BREAK?" : "READY"));
    char b[32];
    snprintf(b, sizeof b, "%s %02lu:%02lu", lab, (unsigned long)(s / 60), (unsigned long)(s % 60));
    u8g2.setFont(u8g2_font_helvB10_tr);
    u8g2.drawStr(4, 62, b);
    snprintf(b, sizeof b, "#%u", bd.sessions);
    u8g2.drawStr(256 - u8g2.getStrWidth(b) - 4, 62, b);
  } else if (clockFn) {
    char c[8];
    if (clockFn(c, sizeof c)) { u8g2.setFont(u8g2_font_helvB10_tr); u8g2.drawStr(256 - u8g2.getStrWidth(c) - 4, 62, c); }
  }
}
static void buddyBegin() { bd.lastInput = millis(); buddyDrawFn = drawBuddy; }

// Keys in BUDDY profile:  1 start/pause  2 reset  3 skip focus<->break  4 pet  5 sleep  6 startle
static void buddyKey(int k) {
  switch (k) {
    case 0: buddyStartPause(); break;
    case 1: buddyReset(); break;
    case 2: buddySkip(); break;
    case 3: buddyMood(BM_HAPPY, 2500); break;
    case 4: bd.lastInput = millis() - 190000UL; bd.forcedUntil = 0; break;   // go to sleep
    case 5: buddyMood(BM_SURPRISED, 1500); break;
    default: buddyMood(BM_HAPPY, 1500); break;
  }
}
