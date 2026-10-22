#pragma once
// OLED user interface. Drawing runs in its own task on core 0 so that slow SPI
// transfers never make the dials/keys miss a click.
#include <U8g2lib.h>
#include "config.h"

static U8G2_SSD1322_NHD_256X64_F_4W_SW_SPI u8g2(U8G2_R0, OLED_CLK, OLED_MOSI, OLED_CS, OLED_DC, OLED_RST);

struct UiState {
  char title[24]   = "G.R.E.M.";
  char action[28]  = "READY";      // big text
  char detail[40]  = "";           // small text under it
  char status[20]  = "";           // top-right (USB/BLE/mode)
  bool keyDown[NUM_KEYS] = {};
  int  dialCount[NUM_ENC] = {};
};
static UiState ui;

static void drawUi() {
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_6x10_tf);
  u8g2.drawStr(0, 8, ui.title);
  u8g2.drawStr(256 - u8g2.getStrWidth(ui.status), 8, ui.status);
  u8g2.drawHLine(0, 11, 256);
  // 3x3 key map (filled square = key held)
  for (int k = 0; k < NUM_KEYS; k++) {
    int x = 4 + (k % 3) * 14, y = 17 + (k / 3) * 15;
    if (ui.keyDown[k]) u8g2.drawBox(x, y, 12, 12); else u8g2.drawFrame(x, y, 12, 12);
  }
  // last action
  u8g2.setFont(u8g2_font_logisoso16_tr);
  u8g2.drawStr(56, 40, ui.action);
  u8g2.setFont(u8g2_font_6x10_tf);
  u8g2.drawStr(56, 55, ui.detail);
  // dial counters on the right
  for (int d = 0; d < NUM_ENC; d++) {
    char b[10]; snprintf(b, sizeof b, "%c%+d", d == 4 ? 'B' : '1' + d, ui.dialCount[d]);
    u8g2.drawStr(205, 21 + d * 10, b);
  }
  u8g2.sendBuffer();
}

static void displayTask(void*) {
  static UiState last;
  memset(&last, 0xFF, sizeof last);                        // force first draw
  for (;;) {
    if (memcmp(&last, &ui, sizeof ui) != 0) { memcpy(&last, &ui, sizeof ui); drawUi(); }  // redraw only on change
    vTaskDelay(pdMS_TO_TICKS(40));
  }
}

static void displayBegin() {
  u8g2.begin();
  u8g2.setContrast(180);
  drawUi();
  xTaskCreatePinnedToCore(displayTask, "oled", 6144, nullptr, 1, nullptr, 0);
}
