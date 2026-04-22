#!/usr/bin/env bash
set -euo pipefail

APP_NAME="baseball-scoreboard"
INSTALL_DIR="/opt/${APP_NAME}"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"

if [[ $EUID -ne 0 ]]; then
  echo "Please run with sudo: sudo ./uninstall.sh"
  exit 1
fi

echo "Stopping and disabling service if present..."
if systemctl list-unit-files | grep -q "^${APP_NAME}.service"; then
  systemctl stop "${APP_NAME}.service" || true
  systemctl disable "${APP_NAME}.service" || true
fi

if [[ -f "${SERVICE_FILE}" ]]; then
  rm -f "${SERVICE_FILE}"
fi

systemctl daemon-reload

if [[ -d "${INSTALL_DIR}" ]]; then
  rm -rf "${INSTALL_DIR}"
  echo "Removed ${INSTALL_DIR}"
fi

echo "Uninstall complete."
echo "Note: /opt/rpi-rgb-led-matrix was left in place intentionally."
