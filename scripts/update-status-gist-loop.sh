#!/usr/bin/env bash
# scripts/update-status-gist-loop.sh
# Continuously update status gist every 30 seconds

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPDATE_SCRIPT="$SCRIPT_DIR/update-status-gist.sh"
GIST_ID_FILE="/tmp/claude-glinet-comet-reversing/gist-id.txt"

if [[ ! -f "$GIST_ID_FILE" ]]; then
    echo "Error: Gist not created yet"
    echo "Run: ./scripts/create-status-gist.sh"
    exit 1
fi

GIST_ID=$(cat "$GIST_ID_FILE")

echo "Starting gist auto-updater..."
echo "URL: https://gist.github.com/$GIST_ID"
echo "Updates every 30 seconds"
echo "Press Ctrl+C to stop"
echo ""

while true; do
    TIMESTAMP=$(date '+%H:%M:%S')

    if "$UPDATE_SCRIPT"; then
        echo "[$TIMESTAMP] ✓ Updated"
    else
        echo "[$TIMESTAMP] ✗ Update failed (will retry)"
    fi

    sleep 30
done
