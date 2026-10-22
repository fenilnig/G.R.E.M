// STAGE 1 - OLED + the 9 keys.  Goal: OLED lights up, pressing a key fills its square.
// Also scans the I2C bus so you can check the MCP23017 (0x20) and DRV2605L (0x5A) are seen.
#include <Arduino.h>
#include "display.h"
#include "inputs.h"

static void keyEvent(int k, bool pressed) {
  ui.keyDown[k] = pressed;
  if (pressed) {
    snprintf(ui.action, sizeof ui.action, "KEY %d", k + 1);
    snprintf(ui.detail, sizeof ui.detail, "pressed");
  }
  Serial.printf("key %d %s\n", k, pressed ? "DOWN" : "up");
}
static void dialSwEvent(int d, bool pressed) {
  Serial.printf("dial-switch %d %s\n", d, pressed ? "DOWN" : "up");
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.println("\nG.R.E.M. stage 1");
  displayBegin();
  snprintf(ui.title, sizeof ui.title, "G.R.E.M.  stage 1");
  bool ok = inputsBegin();
  Serial.printf("MCP23017 at 0x%02X: %s\n", MCP_ADDR, ok ? "FOUND" : "NOT FOUND (check I2C wiring/power)");
  if (!ok) snprintf(ui.action, sizeof ui.action, "NO MCP23017");
  Serial.println("I2C scan:");
  for (uint8_t a = 1; a < 127; a++) { Wire.beginTransmission(a); if (!Wire.endTransmission()) Serial.printf("  device at 0x%02X\n", a); }
  onKey = keyEvent;
  onDialSw = dialSwEvent;
}
void loop() { inputsPoll(); }
