#!/usr/bin/env bash
# Push scratchpad to gist (non-blocking, race-safe)
#
# Usage: .claude/scripts/push-scratchpad-gist.sh
#
# Non-blocking background push with semaphore lock to prevent race conditions.
# Skips silently if another push is already in progress.

set -euo pipefail

gist_id="165f51b518db358f3515610af94e01fb"

scratchpad_file="/tmp/claude-glinet-comet-reversing/scratchpad.md"
semaphore="/tmp/$(basename "$(git rev-parse --show-toplevel)").scratchpad-semaphore"

if mkdir "$semaphore" 2>/dev/null; then
      (gh gist edit "$gist_id" "$scratchpad_file" -f scratchpad.md; rmdir "$semaphore") &
fi
