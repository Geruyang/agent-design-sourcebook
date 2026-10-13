#!/usr/bin/env bash
# Install or refresh the autonomous research loop launchd jobs.
# This script does not run anything as root. It writes user LaunchAgents and bootstraps them.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
TARGET_DIR="${HOME}/Library/LaunchAgents"
mkdir -p "${TARGET_DIR}"
mkdir -p "${REPO_ROOT}/researcher/reports/logs"

for plist in com.context-engineering.loop-step.plist \
             com.context-engineering.loop-discover.plist \
             com.context-engineering.loop-daily.plist; do
    src="${SCRIPT_DIR}/${plist}"
    dst="${TARGET_DIR}/${plist}"
    sed "s|__REPO_ROOT__|${REPO_ROOT}|g" "${src}" > "${dst}"
    launchctl bootout "gui/$(id -u)" "${dst}" >/dev/null 2>&1 || true
    launchctl bootstrap "gui/$(id -u)" "${dst}"
    launchctl enable "gui/$(id -u)/$(basename "${dst}" .plist)"
done

echo "Installed launchd jobs under ${TARGET_DIR}. Inspect with:"
echo "  launchctl print gui/$(id -u)/com.context-engineering.loop-step"
echo "Logs land in ${REPO_ROOT}/researcher/reports/logs/"
