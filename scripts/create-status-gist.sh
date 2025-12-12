#!/usr/bin/env bash
# scripts/create-status-gist.sh
# One-time setup: Create the Claude Code status gist

set -euo pipefail

SCRATCHPAD="/tmp/claude-glinet-comet-reversing/scratchpad.md"
GIST_ID_FILE="/tmp/claude-glinet-comet-reversing/gist-id.txt"

if [[ ! -f "$SCRATCHPAD" ]]; then
    echo "Error: Scratchpad not found at $SCRATCHPAD"
    exit 1
fi

if [[ -f "$GIST_ID_FILE" ]]; then
    echo "Gist already created! ID: $(cat "$GIST_ID_FILE")"
    echo "URL: https://gist.github.com/$(cat "$GIST_ID_FILE")"
    exit 0
fi

echo "Creating public gist for Claude Code status..."

# Create gist and capture URL
GIST_URL=$(gh gist create "$SCRATCHPAD" \
    --desc "Claude Code Live Status - GL.iNet Comet Reversing" \
    --public \
    --filename "claude-status.md")

# Extract gist ID from URL
GIST_ID=$(basename "$GIST_URL")

# Save gist ID for future updates
echo "$GIST_ID" > "$GIST_ID_FILE"

echo ""
echo "✓ Gist created successfully!"
echo "ID: $GIST_ID"
echo "URL: $GIST_URL"
echo ""
echo "Next steps:"
echo "1. Run: ./scripts/update-status-gist-loop.sh (in separate terminal)"
echo "2. Open: $GIST_URL"
echo "3. Install browser auto-refresh extension, set to 30s"
