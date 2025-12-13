#!/usr/bin/env bash
# Generate simplified scratchpad.md from cache files
# Focuses on resumption context, integrates with checkpoint files

set -euo pipefail

CACHE_DIR="/tmp/claude-glinet-comet-reversing/.scratchpad-cache"
SCRATCHPAD="/tmp/claude-glinet-comet-reversing/scratchpad.md"
REPO_SCRATCHPAD="/Users/hays/Projects/glinet-comet-reversing/.scratchpad.md"
WORK_DIR=".claude/work"

# Ensure cache directory exists
mkdir -p "$CACHE_DIR"

# Read cache files (with defaults if missing)
LAST_UPDATED=$(cat "$CACHE_DIR/last-updated.txt" 2>/dev/null || date -u "+%Y-%m-%d %H:%M UTC")
CURRENT_WORK=$(cat "$CACHE_DIR/current-work.txt" 2>/dev/null || echo "No active work")

# Try to extract issue number from current work
ISSUE_NUM=$(echo "$CURRENT_WORK" | grep -oE '#[0-9]+' | head -1 | tr -d '#' || echo "")

# Try to read latest checkpoint file if issue number found
LAST_CHECKPOINT="No checkpoints yet"
NEXT_ACTION="Not specified"
STATUS="No status available"

if [ -n "$ISSUE_NUM" ] && [ -d "$WORK_DIR/issue-$ISSUE_NUM" ]; then
    # Find latest checkpoint file
    LATEST_CP=$(find "$WORK_DIR/issue-$ISSUE_NUM" -name "*.txt" -type f 2>/dev/null | sort -V | tail -1 || echo "")

    if [ -n "$LATEST_CP" ] && [ -f "$LATEST_CP" ]; then
        CP_NUM=$(basename "$LATEST_CP" .txt | grep -oE '^[0-9]+')

        # Extract fields from checkpoint file
        CP_WHAT=$(grep "^WHAT:" "$LATEST_CP" | sed 's/^WHAT: //' || echo "")
        CP_NEXT=$(grep "^NEXT:" "$LATEST_CP" | sed 's/^NEXT: //' || echo "")
        CP_STATUS=$(grep "^STATUS:" "$LATEST_CP" | sed 's/^STATUS: //' || echo "")

        if [ -n "$CP_WHAT" ]; then
            LAST_CHECKPOINT="$CP_NUM - $CP_WHAT"
        fi
        if [ -n "$CP_NEXT" ]; then
            NEXT_ACTION="$CP_NEXT"
        fi
        if [ -n "$CP_STATUS" ]; then
            STATUS="$CP_STATUS"
        fi
    fi
fi

# Generate simplified scratchpad content
cat > "$SCRATCHPAD" <<EOF
# Work Status: [GL.iNet Comet Reversing](https://github.com/stvhay/glinet-comet-reverse-gpl)

**Last Updated:** $LAST_UPDATED
**Current Work:** $CURRENT_WORK
**Last Checkpoint:** $LAST_CHECKPOINT
**Next:** $NEXT_ACTION
**Status:** $STATUS
EOF

# Also copy to repo location for commit
cp "$SCRATCHPAD" "$REPO_SCRATCHPAD"

echo "✅ Scratchpad generated: $SCRATCHPAD"
echo "✅ Copied to repo: $REPO_SCRATCHPAD"
