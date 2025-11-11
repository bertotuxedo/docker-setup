#!/usr/bin/env bash

set -euo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  if ! command -v sudo >/dev/null 2>&1; then
    echo "[ERROR] This script must be run as root or with sudo available." >&2
    exit 1
  fi
  SUDO="sudo"
else
  SUDO=""
fi

export DEBIAN_FRONTEND=noninteractive

echo "[INFO] Updating package index..."
$SUDO apt-get update -y

echo "[INFO] Installing prerequisites..."
$SUDO apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  gnupg \
  lsb-release

echo "[INFO] Setting up Docker GPG key..."
$SUDO install -m 0755 -d /etc/apt/keyrings
$SUDO curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
$SUDO chmod a+r /etc/apt/keyrings/docker.asc

echo "[INFO] Configuring Docker repository..."
ARCHITECTURE=$(dpkg --print-architecture)
RELEASE_CODENAME=$(lsb_release -cs)
REPO_ENTRY="deb [arch=${ARCHITECTURE} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian ${RELEASE_CODENAME} stable"

if [[ ! -f /etc/apt/sources.list.d/docker.list ]] || ! grep -Fxq "$REPO_ENTRY" /etc/apt/sources.list.d/docker.list; then
  echo "$REPO_ENTRY" | $SUDO tee /etc/apt/sources.list.d/docker.list >/dev/null
else
  echo "[INFO] Docker repository already configured."
fi

echo "[INFO] Refreshing package index with Docker repo..."
$SUDO apt-get update -y

echo "[INFO] Installing Docker Engine and related components..."
$SUDO apt-get install -y --no-install-recommends \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin \
  docker-compose-plugin

if command -v systemctl >/dev/null 2>&1; then
  echo "[INFO] Enabling and starting Docker service..."
  $SUDO systemctl enable docker >/dev/null 2>&1 || true
  $SUDO systemctl start docker >/dev/null 2>&1 || true
fi

CURRENT_USER=${SUDO_USER:-${USER:-}}
if [[ -n "$CURRENT_USER" && "$CURRENT_USER" != "root" ]]; then
  echo "[INFO] Adding user '$CURRENT_USER' to the docker group..."
  $SUDO usermod -aG docker "$CURRENT_USER"
  echo "[INFO] Log out and log back in for group changes to take effect."
fi

echo "[SUCCESS] Docker installation completed."
