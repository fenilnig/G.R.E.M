#pragma once
// What every key and dial DOES. Two profiles: CapCut and After Effects.
// Hold the volume dial (small dial 1) push for 1 second to switch profile.
// To change a shortcut: edit the table below. Names (last item) are what the OLED shows.
// IMPORTANT: check each shortcut against the app's own shortcut list (CapCut: keyboard icon /
// Shortcuts; After Effects: Edit > Keyboard Shortcuts) - versions differ.
#include "hid_out.h"

struct ActionDef { bool consumer; uint8_t mods; uint16_t code; const char* name; };      // default table
struct Action    { bool consumer; uint8_t mods; uint16_t code; char name[18]; };            // editable copy (stored in flash)
struct DialDef { const char* label; ActionDef cw, ccw, push; };
struct Profile { const char* name; ActionDef keys[9]; DialDef dials[5]; };

// key layout:  0 1 2 / 3 4 5 / 6 7 8
static const Profile PROFILES[2] = {
 { "CAPCUT",
   { {false,M_CTRL,K_Z,"UNDO"}, {false,M_CTRL|M_SHIFT,K_Z,"REDO"}, {false,0,K_FWDDEL,"DELETE"},
     {false,M_CTRL,K_B,"SPLIT"}, {false,0,K_Q,"TRIM START"}, {false,0,K_W,"TRIM END"},
     {false,M_CTRL,K_C,"COPY"}, {false,M_CTRL,K_V,"PASTE"}, {false,M_CTRL,K_E,"EXPORT"} },
   { {"VOLUME",  {true,0,C_VOL_UP,"VOL +"},        {true,0,C_VOL_DOWN,"VOL -"},     {true,0,C_MUTE,"MUTE"}},
     {"ZOOM",    {false,M_CTRL,K_EQUAL,"ZOOM IN"}, {false,M_CTRL,K_MINUS,"ZOOM OUT"},{false,0,K_HOME,"GO START"}},
     {"EDIT PT", {false,0,K_DOWN,"NEXT CLIP"},     {false,0,K_UP,"PREV CLIP"},      {false,0,K_END,"GO END"}},
     {"NUDGE",   {false,M_SHIFT,K_RIGHT,"+SHIFT >"},{false,M_SHIFT,K_LEFT,"< SHIFT"},{false,0,K_ENTER,"ENTER"}},
     {"SCRUB",   {false,0,K_RIGHT,"FRAME >"},      {false,0,K_LEFT,"< FRAME"},      {false,0,K_SPACE,"PLAY/PAUSE"}} } },
 { "AFTER EFFECTS",
   { {false,M_CTRL,K_Z,"UNDO"}, {false,M_CTRL|M_SHIFT,K_Z,"REDO"}, {false,0,K_FWDDEL,"DELETE"},
     {false,M_CTRL|M_SHIFT,K_D,"SPLIT LAYER"}, {false,0,K_B,"WORK AREA IN"}, {false,0,K_N,"WORK AREA OUT"},
     {false,M_CTRL|M_SHIFT,K_C,"PRECOMPOSE"}, {false,M_CTRL,K_S,"SAVE"}, {false,M_CTRL,K_M,"RENDER QUEUE"} },
   { {"VOLUME",  {true,0,C_VOL_UP,"VOL +"},        {true,0,C_VOL_DOWN,"VOL -"},     {true,0,C_MUTE,"MUTE"}},
     {"ZOOM",    {false,0,K_PERIOD,"ZOOM IN"},     {false,0,K_COMMA,"ZOOM OUT"},    {false,M_SHIFT,K_SLASH,"FIT VIEW"}},
     {"LAYER",   {false,M_CTRL,K_DOWN,"NEXT LAYER"},{false,M_CTRL,K_UP,"PREV LAYER"},{false,0,K_HOME,"GO START"}},
     {"10 FRAMES",{false,M_SHIFT,K_PGDN,"+10 FRAMES"},{false,M_SHIFT,K_PGUP,"-10 FRAMES"},{false,0,K_END,"GO END"}},
     {"SCRUB",   {false,0,K_PGDN,"FRAME >"},       {false,0,K_PGUP,"< FRAME"},      {false,0,K_SPACE,"PLAY/PAUSE"}} } },
};
static uint8_t curProfile = 0;
static const Profile& PROF() { return PROFILES[curProfile]; }

static void doAction(const ActionDef& a) {
  if (a.consumer) hidConsumer(a.code); else hidKey(a.mods, (uint8_t)a.code);
}
static void doAction(const Action& a) {
  if (a.consumer) hidConsumer(a.code); else hidKey(a.mods, (uint8_t)a.code);
}
