#!/bin/bash
# deploy.sh
# Pull latest from GitHub and optionally restart the add-on.
# Usage:
#   ./deploy.sh              — pull + restart
#   ./deploy.sh --no-restart — pull only

ADDON_SLUG="rtl433_bridge"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "RTL-433 Sensor Bridge — deploy script"
echo "======================================"

# Pull latest from GitHub
echo "Pulling latest from GitHub..."
cd "$SCRIPT_DIR" && git pull origin main

if [ $? -ne 0 ]; then
  echo "ERROR: git pull failed."
  exit 1
fi

echo "Pull complete."

# Restart unless --no-restart is passed
if [ "$1" != "--no-restart" ]; then
  echo "Restarting add-on ${ADDON_SLUG}..."
  ha addons restart "${ADDON_SLUG}"
  echo "Restart triggered."
else
  echo "Skipping restart (--no-restart)."
fi

echo "Done."
