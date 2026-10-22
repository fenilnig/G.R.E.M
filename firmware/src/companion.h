#pragma once
// PC link over USB serial + editable key map saved in flash.
//
// Lines the PC sends (text, one per line):
//   T <epoch_utc> <tz_minutes>      real time          M <title>|<artist>   now playing ("" = nothing)
//   S <cpu> <gpu> <ram> <gpuTemp>   load in %          N <app>|<text>       notification
//   A <capcut|ae|other>             active app         R <text>             render finished
//   K <p> <i> <mods> <code> <cons> <name>              set key i of profile p (0=CapCut,1=AfterFX)
//   D <p> <i> <w> <mods> <code> <cons> <name>          set dial i action w (0=cw,1=ccw,2=push)
//   SAVE (write key map to flash)   RESET (back to defaults)   PING
#include <Arduino.h>
#include <Preferences.h>
#include <time.h>
#include "actions.h"
#include "buddy.h"

// ---------------- editable key map ----------------
static Action RT_KEY[2][9];
static Action RT_DIAL[2][5][3];
struct KeyMapStore { uint32_t magic; Action keys[2][9]; Action dials[2][5][3]; };
static const uint32_t KEYMAP_MAGIC = 0x4752454DUL;   // "GREM"

static void copyDef(Action& a, const ActionDef& d) {
  a.consumer = d.consumer; a.mods = d.mods; a.code = d.code;
  strlcpy(a.name, d.name, sizeof a.name);
}
static void keymapDefaults() {
  for (int p = 0; p < 2; p++) {
    for (int k = 0; k < 9; k++) copyDef(RT_KEY[p][k], PROFILES[p].keys[k]);
    for (int d = 0; d < 5; d++) {
      copyDef(RT_DIAL[p][d][0], PROFILES[p].dials[d].cw);
      copyDef(RT_DIAL[p][d][1], PROFILES[p].dials[d].ccw);
      copyDef(RT_DIAL[p][d][2], PROFILES[p].dials[d].push);
    }
  }
}
static void keymapLoad() {
  keymapDefaults();
  static KeyMapStore st;
  Preferences pr;
  if (!pr.begin("grem", true)) return;
  size_t n = pr.getBytesLength("map");
  if (n == sizeof st) {
    pr.getBytes("map", &st, sizeof st);
    if (st.magic == KEYMAP_MAGIC) { memcpy(RT_KEY, st.keys, sizeof RT_KEY); memcpy(RT_DIAL, st.dials, sizeof RT_DIAL); }
  }
  pr.end();
}
static bool keymapSave() {
  static KeyMapStore st;
  memset(&st, 0, sizeof st);
  st.magic = KEYMAP_MAGIC;
  memcpy(st.keys, RT_KEY, sizeof RT_KEY); memcpy(st.dials, RT_DIAL, sizeof RT_DIAL);
  Preferences pr;
  if (!pr.begin("grem", false)) return false;
  bool ok = pr.putBytes("map", &st, sizeof st) == sizeof st;
  pr.end();
  return ok;
}
static void keymapReset() { Preferences pr; if (pr.begin("grem", false)) { pr.remove("map"); pr.end(); } keymapDefaults(); }

// ---------------- data from the PC ----------------
struct CompState {
  bool timeValid = false; uint32_t epoch = 0, epochAtMs = 0; int tzMin = 330;
  char title[64] = "", artist[40] = "";
  int cpu = -1, gpu = -1, ram = -1, gpuT = -1; uint32_t statsAt = 0;
  char nApp[16] = "", nText[100] = ""; uint32_t nUntil = 0; bool nRender = false;
  uint8_t appHint = 0;                 // 0 other, 1 CapCut, 2 After Effects
  bool appChanged = false;
  uint32_t lastSerial = 0;
  bool linked = false;
  bool nTick = false;                  // main loop buzzes the motor once
};
static CompState comp;

static bool compLocalTm(struct tm* out) {
  if (!comp.timeValid) return false;
  time_t t = (time_t)(comp.epoch + (millis() - comp.epochAtMs) / 1000UL) + (time_t)comp.tzMin * 60;
  gmtime_r(&t, out);
  return true;
}
static bool compClock(char* buf, size_t n) {
  struct tm tmv; if (!compLocalTm(&tmv)) return false;
  snprintf(buf, n, "%02d:%02d", tmv.tm_hour, tmv.tm_min);
  return true;
}

static char* tok(char*& s) {
  while (*s == ' ') s++;
  if (!*s) return nullptr;
  char* t = s;
  while (*s && *s != ' ') s++;
  if (*s) *s++ = 0;
  return t;
}
static void asciiOnly(char* s) { for (; *s; s++) if ((uint8_t)*s < 32 || (uint8_t)*s > 126) *s = '?'; }

static void compLine(char* line) {
  comp.lastSerial = millis();
  char* s = line;
  char* cmd = tok(s);
  if (!cmd) return;
  if (!strcmp(cmd, "PING")) { Serial.println("PONG G.R.E.M."); return; }
  if (!strcmp(cmd, "T")) {
    char* a = tok(s); char* b = tok(s);
    if (a) { comp.epoch = strtoul(a, nullptr, 10); comp.epochAtMs = millis(); comp.timeValid = true; }
    if (b) comp.tzMin = atoi(b);
  } else if (!strcmp(cmd, "M")) {
    while (*s == ' ') s++;
    char* bar = strchr(s, '|');
    if (bar) { *bar = 0; strlcpy(comp.title, s, sizeof comp.title); strlcpy(comp.artist, bar + 1, sizeof comp.artist); }
    else { strlcpy(comp.title, s, sizeof comp.title); comp.artist[0] = 0; }
    asciiOnly(comp.title); asciiOnly(comp.artist);
  } else if (!strcmp(cmd, "S")) {
    char* a = tok(s); char* b = tok(s); char* c = tok(s); char* d = tok(s);
    comp.cpu = a ? atoi(a) : -1; comp.gpu = b ? atoi(b) : -1; comp.ram = c ? atoi(c) : -1; comp.gpuT = d ? atoi(d) : -1;
    comp.statsAt = millis();
  } else if (!strcmp(cmd, "N")) {
    while (*s == ' ') s++;
    char* bar = strchr(s, '|');
    if (bar) { *bar = 0; strlcpy(comp.nApp, s, sizeof comp.nApp); strlcpy(comp.nText, bar + 1, sizeof comp.nText); }
    else { strlcpy(comp.nApp, "NOTICE", sizeof comp.nApp); strlcpy(comp.nText, s, sizeof comp.nText); }
    asciiOnly(comp.nApp); asciiOnly(comp.nText);
    comp.nUntil = millis() + 6000; comp.nRender = false; comp.nTick = true;
  } else if (!strcmp(cmd, "R")) {
    while (*s == ' ') s++;
    strlcpy(comp.nApp, "RENDER DONE", sizeof comp.nApp);
    strlcpy(comp.nText, *s ? s : "Your render has finished", sizeof comp.nText);
    asciiOnly(comp.nText);
    comp.nUntil = millis() + 9000; comp.nRender = true;
    buddyMood(BM_HAPPY, 9000); bd.alarmFlag = true;
  } else if (!strcmp(cmd, "A")) {
    char* a = tok(s);
    uint8_t h = (a && !strcmp(a, "capcut")) ? 1 : (a && !strcmp(a, "ae")) ? 2 : 0;
    if (h != comp.appHint) { comp.appHint = h; comp.appChanged = true; }
  } else if (!strcmp(cmd, "K") || !strcmp(cmd, "D")) {
    bool isDial = cmd[0] == 'D';
    char* p = tok(s); char* i = tok(s); char* w = isDial ? tok(s) : (char*)"0";
    char* m = tok(s); char* c = tok(s); char* k = tok(s);
    if (!p || !i || !w || !m || !c || !k) { Serial.println("ERR args"); return; }
    while (*s == ' ') s++;
    int pi = atoi(p), ii = atoi(i), wi = atoi(w);
    Action* a = nullptr;
    if (pi >= 0 && pi < 2) {
      if (!isDial && ii >= 0 && ii < 9) a = &RT_KEY[pi][ii];
      if (isDial && ii >= 0 && ii < 5 && wi >= 0 && wi < 3) a = &RT_DIAL[pi][ii][wi];
    }
    if (!a) { Serial.println("ERR range"); return; }
    a->mods = (uint8_t)atoi(m); a->code = (uint16_t)atoi(c); a->consumer = atoi(k) != 0;
    strlcpy(a->name, s, sizeof a->name);
    asciiOnly(a->name);
    Serial.println("OK");
  } else if (!strcmp(cmd, "SAVE")) {
    Serial.println(keymapSave() ? "OK saved" : "ERR save");
  } else if (!strcmp(cmd, "RESET")) {
    keymapReset(); Serial.println("OK reset");
  }
}

static void compPoll() {
  static char rx[200]; static size_t rxn = 0;
  while (Serial.available()) {
    int c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') { rx[rxn] = 0; if (rxn) compLine(rx); rxn = 0; }
    else if (rxn < sizeof rx - 1) rx[rxn++] = (char)c;
  }
  comp.linked = comp.lastSerial && (millis() - comp.lastSerial < 8000);
}

// ---------------- screens ----------------
static void drawBar(int x, int y, int w, int pct) {
  u8g2.drawFrame(x, y, w, 8);
  if (pct > 0) u8g2.drawBox(x + 1, y + 1, ((w - 2) * (pct > 100 ? 100 : pct)) / 100, 6);
}
static void marquee(int y, const char* txt) {
  int len = strlen(txt) * 6;
  if (len <= 250) { u8g2.drawStr(3, y, txt); return; }
  int gap = 40, off = (millis() / 80) % (len + gap);
  u8g2.drawStr(3 - off, y, txt);
  u8g2.drawStr(3 - off + len + gap, y, txt);
}

static void drawDash() {
  u8g2.clearBuffer(); u8g2.setDrawColor(1);
  static const char* DAYS[7] = {"SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"};
  struct tm tmv;
  if (compLocalTm(&tmv)) {
    char b[16]; snprintf(b, sizeof b, "%02d:%02d", tmv.tm_hour, tmv.tm_min);
    u8g2.setFont(u8g2_font_logisoso20_tr); u8g2.drawStr(2, 24, b);
    u8g2.setFont(u8g2_font_6x10_tf);
    snprintf(b, sizeof b, "%s %02d", DAYS[tmv.tm_wday], tmv.tm_mday); u8g2.drawStr(4, 38, b);
  } else {
    u8g2.setFont(u8g2_font_6x10_tf);
    u8g2.drawStr(4, 14, comp.linked ? "SYNCING TIME" : "WAITING FOR PC");
    char b[20]; uint32_t s = millis() / 1000; snprintf(b, sizeof b, "UP %02lu:%02lu", (unsigned long)(s / 3600), (unsigned long)((s / 60) % 60));
    u8g2.drawStr(4, 30, b);
  }
  u8g2.setFont(u8g2_font_6x10_tf);
  bool fresh = comp.statsAt && (millis() - comp.statsAt < 5000);
  const char* lab[3] = {"CPU", "GPU", "RAM"};
  int val[3] = {comp.cpu, comp.gpu, comp.ram};
  for (int i = 0; i < 3; i++) {
    int y = 10 + i * 13; char b[12];
    u8g2.drawStr(96, y + 8, lab[i]);
    drawBar(120, y, 80, fresh && val[i] >= 0 ? val[i] : 0);
    if (fresh && val[i] >= 0) snprintf(b, sizeof b, "%d%%", val[i]); else snprintf(b, sizeof b, "--");
    u8g2.drawStr(206, y + 8, b);
  }
  if (fresh && comp.gpuT > 0) { char b[10]; snprintf(b, sizeof b, "%dC", comp.gpuT); u8g2.drawStr(256 - u8g2.getStrWidth(b) - 2, 21, b); }
  u8g2.drawHLine(0, 44, 256);
  char line[120];
  if (comp.title[0]) snprintf(line, sizeof line, "> %s%s%s", comp.title, comp.artist[0] ? " - " : "", comp.artist);
  else snprintf(line, sizeof line, "nothing playing");
  marquee(58, line);
}

static void drawNotif() {
  u8g2.clearBuffer(); u8g2.setDrawColor(1);
  u8g2.drawFrame(0, 0, 256, 64);
  u8g2.setFont(u8g2_font_6x10_tf);
  u8g2.drawStr(5, 11, comp.nApp);
  u8g2.drawHLine(0, 14, 256);
  size_t n = strlen(comp.nText);
  for (int row = 0; row < 3; row++) {          // 3 lines x 40 chars
    char seg[42]; size_t st = row * 40;
    if (st >= n) break;
    strlcpy(seg, comp.nText + st, sizeof seg); seg[40] = 0;
    u8g2.drawStr(5, 27 + row * 12, seg);
  }
}

// chooses what to draw whenever the "buddy view" is active
static void drawRouter(int profile, uint32_t idleMs) {
  if (millis() < comp.nUntil && (profile >= 2 || comp.nRender || idleMs > 45000UL)) drawNotif();
  else if (profile == 3) drawDash();
  else drawBuddy();
}
