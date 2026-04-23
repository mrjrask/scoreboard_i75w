# Interstate 75 W Baseball Scoreboard (64x64 HUB75)

This project is rewritten for **Pimoroni Interstate 75 W** (RP2040 + Wi-Fi) driving a **64x64 HUB75 RGB matrix** directly from MicroPython.

## What this version does

- Runs *on-device* (no Raspberry Pi/Linux/systemd required).
- Renders a baseball scoreboard on the HUB75 panel.
- Hosts a lightweight web controller from the Interstate 75 W itself (port `80`) when Wi-Fi is configured.
- Supports:
  - Team names (`TEAM A`, `TEAM B`) up to 10 chars
  - Team scores +/-
  - Inning +/- and Top/Bottom toggle
  - Balls (0-3), Strikes (0-2), Outs (0-2)
  - Optional batting-order tracker per team with configurable lineup size
  - Full reset
  - Automatic state persistence across board resets/reboots, including abrupt power loss after a change

## Files in this repo

- `main.py` – complete scoreboard + renderer + tiny web server for MicroPython
- `secrets.example.py` – Wi-Fi credential template
- `install.sh` – optional helper to deploy files with `mpremote`

## Hardware required

- Pimoroni Interstate 75 W
- 64x64 HUB75 panel
- Suitable 5V power supply for your panel
- USB cable to your computer for flashing/copying files

## Software prerequisites (computer side)

1. Install **Pimoroni MicroPython firmware for Interstate 75 W** (UF2).
2. Install `mpremote` on your computer:

```bash
python3 -m pip install --upgrade mpremote
```

> You can also copy files with Thonny instead of `mpremote`.

## Loading everything onto the device

### Option A: One-command deploy (`install.sh`)

From this repo on your computer:

```bash
chmod +x install.sh
./install.sh
```

This copies `main.py` and `secrets.py` (if present) to the connected Interstate 75 W.

### Option B: Manual deploy with `mpremote`

1. Create Wi-Fi credentials file:

```bash
cp secrets.example.py secrets.py
# Edit secrets.py and set your real SSID/password.
# Optional: set BATTING_ORDER = True/False to show/hide batting-order controls and pixels.
```

2. Copy files:

```bash
mpremote fs cp main.py :main.py
mpremote fs cp secrets.py :secrets.py
```

3. Reboot device:

```bash
mpremote reset
```

### Option C: Thonny

1. Open Thonny and select the MicroPython interpreter for your Interstate 75 W.
2. Open `main.py` and save it to the board as `/main.py`.
3. (Optional, for web control) create and save `/secrets.py` using `secrets.example.py` as template.
4. Reset the board.

## Using it

- After boot, the matrix shows the scoreboard.
- If `secrets.py` is configured and Wi-Fi connects, the device requests DHCP hostname
  `score`, so try:
  - `http://score` (works on networks that publish DHCP hostnames in local DNS)
- If mDNS is available in your MicroPython firmware and client device, you can also try:
  - `http://score.local`
- The serial console now prints exactly which URL variants are available at boot.

## Troubleshooting

- **No web UI:** Ensure `secrets.py` exists and credentials are correct.
- **`score.local` does not resolve:** `.local` requires mDNS support on both the board
  firmware and the phone/computer. If unavailable, use `http://score` (if your router
  resolves DHCP names) or the printed IP address.
- **Panel not updating:** Confirm you flashed Pimoroni Interstate 75 W MicroPython firmware.
- **Dim/flicker:** Verify power supply current capability and HUB75 wiring orientation.
