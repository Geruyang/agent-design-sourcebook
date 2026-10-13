#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
LOG_DIR="${REPO_ROOT}/researcher/reports/logs"
mkdir -p "${LOG_DIR}"
cd "${REPO_ROOT}"
# --allow-fetch enables stdlib HTTP retrieval (no paid APIs). Remove it to make
# the daemon do bookkeeping only and require humans to retrieve sources.
# loop_step exits 78 when there is no work; that is normal and must not stop
# the status refresh that follows.
python3 researcher/scripts/loop_step.py --allow-fetch --json >> "${LOG_DIR}/loop_step.log" 2>&1 || true
python3 researcher/scripts/loop_status.py --json >> "${LOG_DIR}/loop_status.log" 2>&1
