#!/usr/bin/env bash

# ==============================================================================
# Deploy Script for Claude Deck Pi
# Syncs the Pi package from src/ to Pi Zero over SSH and restarts the daemon.
# ==============================================================================

# Configuration (adjust host/IP if using a static IP like 192.168.7.2)
PI_USER="pi"
PI_HOST="claude-deck.local"
TARGET_DIR="/home/pi/claude-deck-pi"
SERVICE_NAME="claude-deck.service"

# Resolve local source directory relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="${SCRIPT_DIR}/src/claude_deck_pi"

# Verify source folder exists
if [ ! -d "$SOURCE_DIR" ]; then
  echo "❌ Error: Local source directory '${SOURCE_DIR}' not found!"
  exit 1
fi

echo "🚀 Syncing files to ${PI_USER}@${PI_HOST}:${TARGET_DIR}..."

# Sync files using rsync
rsync -avz --delete \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  --exclude='.git' \
  "${SOURCE_DIR}/" "${PI_USER}@${PI_HOST}:${TARGET_DIR}/"

if [ $? -eq 0 ]; then
  echo "✅ Files successfully synced!"
  
  # Restart systemd service over SSH so changes take effect
  echo "🔄 Restarting ${SERVICE_NAME} on Pi Zero..."
  ssh "${PI_USER}@${PI_HOST}" "sudo systemctl restart ${SERVICE_NAME}" 2>/dev/null
  
  if [ $? -eq 0 ]; then
    echo "🎉 Service restarted successfully! Deployment complete."
  else
    echo "⚠️ Sync succeeded, but systemd service restart failed (is ${SERVICE_NAME} installed?)."
  fi
else
  echo "❌ Error: rsync failed. Check your SSH connection to ${PI_USER}@${PI_HOST}."
  exit 1
fi