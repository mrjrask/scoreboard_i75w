# Raspberry Pi Baseball Scoreboard (64x64 HUB75)

This project runs a baseball scoreboard on a **64x64 HUB75 RGB matrix** (Adafruit RGB Matrix Bonnet on Raspberry Pi 4) and exposes a web controller to update values from your phone.

## Features
- Team names and scores (increment/decrement)
- Inning number (increment/decrement)
- Inning half toggle (Top/Bottom) with arrow indicator
- Balls/Strikes/Outs indicators with cycle behavior:
  - Balls: 0-3
  - Strikes: 0-2
  - Outs: 0-2
- Auto-start at boot via `systemd`

## Quick install on Raspberry Pi

```bash
git clone <your-repo-url> scoreboard
cd scoreboard
chmod +x install.sh uninstall.sh
sudo ./install.sh
```

After install:
- Web controller: `http://<pi-ip>:5000`
- Service name: `baseball-scoreboard.service`

> Tip: if you are tethering from iPhone, connect Pi to tethered network and open the controller using the Pi's IP address on that network.

## Service management

```bash
sudo systemctl status baseball-scoreboard
sudo systemctl restart baseball-scoreboard
sudo journalctl -u baseball-scoreboard -f
```

## Uninstall

```bash
sudo ./uninstall.sh
```

## Notes
- Hardware rendering uses `rpi-rgb-led-matrix` with `--led-gpio-mapping=adafruit-hat`.
- If run on a non-Pi machine, the app still starts and serves the web UI but skips physical panel drawing.
