#pragma once
// DRV2605L + coin motor (ERM). Uses the built-in ERM effect library 1.
#include <Wire.h>
#include <Adafruit_DRV2605.h>

static Adafruit_DRV2605 drv;
static bool hapticsOk = false;

static bool hapticsBegin() {          // call AFTER Wire.begin()
  hapticsOk = drv.begin(&Wire);
  if (!hapticsOk) return false;
  drv.selectLibrary(1);               // 1 = ERM (coin motor)
  drv.useERM();
  drv.setMode(DRV2605_MODE_INTTRIG);
  return true;
}
static void hapticPlay(uint8_t effect) {   // see DRV2605 effect list (1..123)
  if (!hapticsOk) return;
  drv.setWaveform(0, effect);
  drv.setWaveform(1, 0);
  drv.go();
}
static void hapticKey()   { hapticPlay(1);  }   // strong click
static void hapticDial()  { hapticPlay(24); }   // sharp tick (light)
static void hapticMode()  { hapticPlay(10); }   // double click
static void hapticAlarm() {            // three strong buzzes with pauses (timer finished)
  if (!hapticsOk) return;
  drv.setWaveform(0, 14); drv.setWaveform(1, 0x80 | 20);
  drv.setWaveform(2, 14); drv.setWaveform(3, 0x80 | 20);
  drv.setWaveform(4, 14); drv.setWaveform(5, 0);
  drv.go();
}
