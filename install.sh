#!/usr/bin/env bash
set -euo pipefail

APP_NAME="baseball-scoreboard"
INSTALL_DIR="/opt/${APP_NAME}"
VENV_DIR="${INSTALL_DIR}/.venv"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
MATRIX_LIB_DIR="/opt/rpi-rgb-led-matrix"
RUN_USER="${SUDO_USER:-$(id -un)}"
RUN_GROUP="$(id -gn "${RUN_USER}")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $EUID -ne 0 ]]; then
  echo "Please run with sudo: sudo ./install.sh"
  exit 1
fi

echo "[1/6] Installing system packages..."
apt-get update
apt-get install -y python3 python3-venv python3-pip python3-dev build-essential git rsync cython3

echo "[2/6] Copying application to ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}"
rsync -a --delete \
  --exclude ".git" \
  --exclude "__pycache__" \
  --exclude ".venv" \
  "${SCRIPT_DIR}/" "${INSTALL_DIR}/"
chown -R "${RUN_USER}:${RUN_GROUP}" "${INSTALL_DIR}"

echo "[3/6] Creating Python virtual environment..."
sudo -u "${RUN_USER}" python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install --upgrade pip wheel setuptools
"${VENV_DIR}/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"

echo "[4/6] Installing rpi-rgb-led-matrix python bindings..."
if [[ ! -d "${MATRIX_LIB_DIR}" ]]; then
  git clone https://github.com/hzeller/rpi-rgb-led-matrix.git "${MATRIX_LIB_DIR}"
else
  git -C "${MATRIX_LIB_DIR}" pull --ff-only
fi
if make -C "${MATRIX_LIB_DIR}/bindings/python" -n build-python >/dev/null 2>&1; then
  make -C "${MATRIX_LIB_DIR}/bindings/python" build-python PYTHON="${VENV_DIR}/bin/python"
  "${VENV_DIR}/bin/pip" install "${MATRIX_LIB_DIR}/bindings/python"
else
  "${VENV_DIR}/bin/pip" install "${MATRIX_LIB_DIR}"
fi

echo "[5/6] Installing systemd service..."
cat > "${SERVICE_FILE}" <<SERVICE
[Unit]
Description=Baseball Scoreboard Controller + LED Matrix Renderer
After=network.target

[Service]
Type=simple
User=${RUN_USER}
Group=${RUN_GROUP}
WorkingDirectory=${INSTALL_DIR}
ExecStart=${VENV_DIR}/bin/python ${INSTALL_DIR}/app.py --host 0.0.0.0 --port 5000
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable "${APP_NAME}.service"

echo "[6/6] Starting service..."
systemctl restart "${APP_NAME}.service"

echo "Installation complete."
echo "Controller URL: http://<pi-ip>:5000"
echo "Service status: sudo systemctl status ${APP_NAME}.service"
