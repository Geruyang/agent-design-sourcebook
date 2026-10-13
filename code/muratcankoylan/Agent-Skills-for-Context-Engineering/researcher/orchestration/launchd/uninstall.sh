#!/usr/bin/env bash
# Remove the autonomous research loop launchd jobs.
set -euo pipefail

TARGET_DIR="${HOME}/Library/LaunchAgents"
for label in com.context-engineering.loop-step com.context-engineering.loop-discover com.context-engineering.loop-daily; do
    dst="${TARGET_DIR}/${label}.plist"
    launchctl bootout "gui/$(id -u)" "${dst}" >/dev/null 2>&1 || true
    rm -f "${dst}"
done

echo "Removed launchd jobs from ${TARGET_DIR}."
