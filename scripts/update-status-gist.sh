#!/usr/bin/env bash
# scripts/update-status-gist.sh
# Update Claude Code status gist

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GIST_ID_FILE="/tmp/claude-glinet-comet-reversing/gist-id.txt"

if [[ ! -f "$GIST_ID_FILE" ]]; then
    echo "Error: Gist not created yet. Run ./scripts/create-status-gist.sh first"
    exit 1
fi

GIST_ID=$(cat "$GIST_ID_FILE")

# Render gist content using Jinja template
TEMP_FILE=$(mktemp)
"$SCRIPT_DIR/render-gist.py" > "$TEMP_FILE"

# Update the gist
gh gist edit "$GIST_ID" "$TEMP_FILE" --filename "scratchpad.md" > /dev/null

rm "$TEMP_FILE"

echo "✓ Updated: https://gist.github.com/$GIST_ID"
