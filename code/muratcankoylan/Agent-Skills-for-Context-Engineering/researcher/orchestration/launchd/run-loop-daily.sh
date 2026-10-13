#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
LOG_DIR="${REPO_ROOT}/researcher/reports/logs"
mkdir -p "${LOG_DIR}"
cd "${REPO_ROOT}"
python3 researcher/scripts/loop_daily.py --json >> "${LOG_DIR}/loop_daily.log" 2>&1
python3 researcher/scripts/loop_status.py --json >> "${LOG_DIR}/loop_status.log" 2>&1
