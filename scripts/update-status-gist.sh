#!/usr/bin/env bash
# scripts/update-status-gist.sh
# Update Claude Code status gist

set -euo pipefail

SCRATCHPAD="/tmp/claude-glinet-comet-reversing/scratchpad.md"
GIST_ID_FILE="/tmp/claude-glinet-comet-reversing/gist-id.txt"

if [[ ! -f "$SCRATCHPAD" ]]; then
    echo "Error: Scratchpad not found at $SCRATCHPAD"
    exit 1
fi

if [[ ! -f "$GIST_ID_FILE" ]]; then
    echo "Error: Gist not created yet. Run ./scripts/create-status-gist.sh first"
    exit 1
fi

GIST_ID=$(cat "$GIST_ID_FILE")

# Update timestamp in scratchpad and add minimal footer
TIMESTAMP=$(date '+%Y-%m-%d %I:%M:%S %p %Z')
TEMP_FILE=$(mktemp)

# Copy scratchpad with updated timestamp
sed "s/^\*\*Last Updated:\*\* .*/**Last Updated:** $TIMESTAMP/" "$SCRATCHPAD" > "$TEMP_FILE"

# Add minimal footer with gist URL
cat >> "$TEMP_FILE" <<EOF

---
_Live URL: https://gist.github.com/${GIST_ID}_
EOF

# Update the gist (use scratchpad.md filename to match creation)
gh gist edit "$GIST_ID" "$TEMP_FILE" --filename "scratchpad.md" > /dev/null

rm "$TEMP_FILE"

echo "✓ Updated: https://gist.github.com/$GIST_ID"
