#pragma once
// Sends keyboard + media keys over USB (wired) and Bluetooth LE at the same time.
#include <NimBLEDevice.h>
#include <NimBLEHIDDevice.h>
#include <USB.h>
#include <USBHIDKeyboard.h>
#include <USBHIDConsumerControl.h>

// modifier bitmask
#define M_CTRL  0x01
#define M_SHIFT 0x02
#define M_ALT   0x04
#define M_GUI   0x08
// HID usage codes used by the macros
#define K_B 0x05
#define K_C 0x06
#define K_E 0x08
#define K_I 0x0C
#define K_K 0x0E
#define K_M 0x10
#define K_N 0x11
#define K_O 0x12
#define K_Q 0x14
#define K_S 0x16
#define K_V 0x19
#define K_W 0x1A
#define K_Z 0x1D
#define K_D 0x07
#define K_ENTER 0x28
#define K_DEL 0x2A      // NOTE: this is BACKSPACE
#define K_FWDDEL 0x4C   // the real Delete key
#define K_SPACE 0x2C
#define K_MINUS 0x2D
#define K_EQUAL 0x2E
#define K_BSLASH 0x31
#define K_COMMA 0x36
#define K_PERIOD 0x37
#define K_SLASH 0x38
#define K_HOME 0x4A
#define K_END 0x4D
#define K_PGUP 0x4B
#define K_PGDN 0x4E
#define K_RIGHT 0x4F
#define K_LEFT 0x50
#define K_DOWN 0x51
#define K_UP 0x52
// consumer usages
#define C_VOL_UP 0xE9
#define C_VOL_DOWN 0xEA
#define C_MUTE 0xE2
#define C_PLAY 0xCD
#define C_NEXT 0xB5
#define C_PREV 0xB6

enum OutMode : uint8_t { OUT_BOTH = 0, OUT_USB = 1, OUT_BLE = 2 };
static OutMode outMode = OUT_BOTH;
static const char* outModeName() { return outMode == OUT_BOTH ? "USB+BLE" : outMode == OUT_USB ? "USB" : "BLE"; }

static USBHIDKeyboard usbKeys;
static USBHIDConsumerControl usbCons;
static NimBLEHIDDevice* bleHid = nullptr;
static NimBLECharacteristic *bleKbd = nullptr, *bleCons = nullptr;
static volatile bool bleConnected = false;
static uint32_t releaseAt = 0;
static bool pendingKey = false, pendingCons = false;

static const uint8_t HID_MAP[] = {
  // Keyboard, report ID 1
  0x05,0x01, 0x09,0x06, 0xA1,0x01, 0x85,0x01,
  0x05,0x07, 0x19,0xE0, 0x29,0xE7, 0x15,0x00, 0x25,0x01, 0x75,0x01, 0x95,0x08, 0x81,0x02,
  0x95,0x01, 0x75,0x08, 0x81,0x01,
  0x95,0x06, 0x75,0x08, 0x15,0x00, 0x25,0x65, 0x05,0x07, 0x19,0x00, 0x29,0x65, 0x81,0x00,
  0xC0,
  // Consumer control, report ID 2
  0x05,0x0C, 0x09,0x01, 0xA1,0x01, 0x85,0x02,
  0x15,0x00, 0x26,0xFF,0x03, 0x19,0x00, 0x2A,0xFF,0x03, 0x75,0x10, 0x95,0x01, 0x81,0x00,
  0xC0
};

class GremBleCb : public NimBLEServerCallbacks {
  void onConnect(NimBLEServer*) { bleConnected = true; }
  void onDisconnect(NimBLEServer*) { bleConnected = false; NimBLEDevice::startAdvertising(); }
};
static GremBleCb bleCb;

static void hidBegin() {
  // ---- USB ----
  usbKeys.begin();
  usbCons.begin();
  USB.productName("G.R.E.M.");
  USB.manufacturerName("Fenil");
  USB.begin();
  // ---- Bluetooth LE ----
  NimBLEDevice::init("G.R.E.M.");
  NimBLEDevice::setSecurityAuth(true, true, true);          // bonding, secure connections
  NimBLEDevice::setSecurityIOCap(BLE_HS_IO_NO_INPUT_OUTPUT); // "Just Works" pairing
  NimBLEServer* server = NimBLEDevice::createServer();
  server->setCallbacks(&bleCb);
  bleHid = new NimBLEHIDDevice(server);
  bleKbd = bleHid->inputReport(1);
  bleCons = bleHid->inputReport(2);
  bleHid->manufacturer()->setValue("Fenil");
  bleHid->pnp(0x02, 0x05AC, 0x820A, 0x0210);
  bleHid->hidInfo(0x00, 0x01);
  bleHid->reportMap((uint8_t*)HID_MAP, sizeof(HID_MAP));
  bleHid->startServices();
  NimBLEAdvertising* adv = server->getAdvertising();
  adv->setAppearance(0x03C1);                                // keyboard
  adv->addServiceUUID(bleHid->hidService()->getUUID());
  adv->start();
}

static void releaseAllNow() {
  if (pendingKey) {
    if (outMode != OUT_BLE) usbKeys.releaseAll();
    if (outMode != OUT_USB && bleConnected) { uint8_t r[8] = {0}; bleKbd->setValue(r, 8); bleKbd->notify(); }
    pendingKey = false;
  }
  if (pendingCons) {
    if (outMode != OUT_BLE) usbCons.release();
    if (outMode != OUT_USB && bleConnected) { uint8_t r[2] = {0, 0}; bleCons->setValue(r, 2); bleCons->notify(); }
    pendingCons = false;
  }
}

// press a key (+modifiers); it is released automatically ~12 ms later by hidService()
static void hidKey(uint8_t mods, uint8_t code) {
  releaseAllNow();
  if (outMode != OUT_BLE) {
    for (int b = 0; b < 4; b++) if (mods & (1 << b)) usbKeys.press(0x80 + b);
    usbKeys.pressRaw(code);
  }
  if (outMode != OUT_USB && bleConnected) {
    uint8_t r[8] = {mods, 0, code, 0, 0, 0, 0, 0};
    bleKbd->setValue(r, 8); bleKbd->notify();
  }
  pendingKey = true; releaseAt = millis() + 12;
}

static void hidConsumer(uint16_t usage) {
  releaseAllNow();
  if (outMode != OUT_BLE) usbCons.press(usage);
  if (outMode != OUT_USB && bleConnected) {
    uint8_t r[2] = {(uint8_t)(usage & 0xFF), (uint8_t)(usage >> 8)};
    bleCons->setValue(r, 2); bleCons->notify();
  }
  pendingCons = true; releaseAt = millis() + 12;
}

// call every loop pass
static void hidService() {
  if ((pendingKey || pendingCons) && (int32_t)(millis() - releaseAt) >= 0) releaseAllNow();
}

static void hidCycleMode() { outMode = (OutMode)((outMode + 1) % 3); }
