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

# Create enhanced status with timestamp
TIMESTAMP=$(date '+%Y-%m-%d %I:%M:%S %p %Z')
TEMP_FILE=$(mktemp)

cat > "$TEMP_FILE" <<EOF
# GL.iNet Comet Reversing - Live Work Log

**Repository:** https://github.com/stvhay/glinet-comet-reverse-gpl
**Last Updated:** $TIMESTAMP
**Project:** GL.iNet Comet GPL Compliance Analysis
**Auto-refresh:** Use browser extension for updates every 30s

---

EOF

# Append scratchpad content (skip first line - the header)
tail -n +2 "$SCRATCHPAD" >> "$TEMP_FILE"

# Add footer
cat >> "$TEMP_FILE" <<EOF

---

**Live URL:** https://gist.github.com/$GIST_ID
**Auto-updated:** This gist updates automatically every 30 seconds during active Claude sessions

_Generated from: \`/tmp/claude-glinet-comet-reversing/scratchpad.md\`_
EOF

# Update the gist (use scratchpad.md filename to match creation)
gh gist edit "$GIST_ID" "$TEMP_FILE" --filename "scratchpad.md" > /dev/null

rm "$TEMP_FILE"

echo "✓ Updated: https://gist.github.com/$GIST_ID"
