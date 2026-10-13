#!/usr/bin/env bash
# Install the long-horizon-prompting skill into a Cursor project's .cursor/skills/
# directory and validate the installed copy with the official Agent Skills validator.
#
# .cursor/ is gitignored in this repo (project-local IDE state), so this script is the
# committed, reproducible record of the install. Run it from the repo root.
#
# Usage: examples/long-horizon-prompt-lab/scripts/install_skill.sh [target_repo_root]
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
TARGET="${1:-$REPO}"

SRC="$REPO/skills/long-horizon-prompting"
DEST="$TARGET/.cursor/skills/long-horizon-prompting"

if [[ ! -f "$SRC/SKILL.md" ]]; then
  echo "ERROR: source skill not found at $SRC" >&2
  exit 1
fi

echo "Installing long-horizon-prompting into $DEST"
mkdir -p "$TARGET/.cursor/skills"
rm -rf "$DEST"
cp -R "$SRC" "$DEST"

echo "Installed files:"
find "$DEST" -type f | sort | sed "s#$TARGET/##"

if command -v agentskills >/dev/null 2>&1; then
  echo "Validating installed copy with the reference Agent Skills CLI..."
  agentskills validate "$DEST"
else
  echo "Note: 'agentskills' CLI not on PATH; skipping reference validation."
  echo "      Install with: python3 -m pip install skills-ref"
fi

echo "Done. Cursor discovers skills under .cursor/skills/ automatically."
