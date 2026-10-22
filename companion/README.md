# G.R.E.M. companion (Windows, Python)

Run it while the console is plugged in by USB. It talks to the console over the USB serial port.
(Not available over Bluetooth-only; with Bluetooth the console still works as a keyboard, just without these extras.)

## Start
1. Install Python 3.10+ from python.org (tick "Add python to PATH").
2. Double-click `start_grem_companion.bat` (installs `pyserial`, `psutil`, `winsdk`, then starts).
3. Open http://localhost:8765 for the key-map editor.

## What it does
- **Clock / date** on the DASH profile and on the sleeping buddy face.
- **Now playing** (anything that shows in Windows' media overlay: Spotify, YouTube in Chrome/Brave, etc.) - DASH profile.
- **CPU / GPU / RAM load + GPU temperature** (GPU via `nvidia-smi`, NVIDIA only) - DASH profile.
- **Auto profile:** when CapCut or After Effects comes to the front, the console switches to that profile. Edit the `app_map` in `grem_config.json` to add other exe names.
- **Render-finished reaction:** the buddy cheers and the motor buzzes. Two triggers: `aerender.exe` ending, and a heuristic (CPU/GPU high for 45 s while an editing app is open, then idle for 8 s). The heuristic CAN be wrong (e.g. a long preview or a game). Turn it off in the web page.
- **Key-map editor:** change any key/dial action, press "Send to console". Saved in the console's flash.
- **Notifications (EXPERIMENTAL):** Windows only lets packaged apps read other apps' notifications, so Discord/WhatsApp toasts may NOT come through. The web page shows the status. The "Send notification" test button always works. If it stays denied, tell me and I'll look at another route (e.g. a Discord bot or a Chrome extension).

## Files
`grem_companion.py` (everything), `grem_config.json` (created on first save), `requirements.txt`, `start_grem_companion.bat`.

## Safety
The web page only answers on localhost. Nothing is sent over the internet.
