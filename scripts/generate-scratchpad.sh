#!/usr/bin/env bash
# Generate scratchpad.md from cache files
# This script reads simple cache files and renders the full scratchpad

set -euo pipefail

CACHE_DIR="/tmp/claude-glinet-comet-reversing/.scratchpad-cache"
SCRATCHPAD="/tmp/claude-glinet-comet-reversing/scratchpad.md"
REPO_SCRATCHPAD="/Users/hays/Projects/glinet-comet-reversing/.scratchpad.md"

# Ensure cache directory exists
mkdir -p "$CACHE_DIR"

# Read cache files (with defaults if missing)
LAST_UPDATED=$(cat "$CACHE_DIR/last-updated.txt" 2>/dev/null || date -u "+%Y-%m-%d %H:%M UTC")
CURRENT_WORK=$(cat "$CACHE_DIR/current-work.txt" 2>/dev/null || echo "No active work")

# Read completions (multi-line)
COMPLETIONS=""
if [ -f "$CACHE_DIR/completions.txt" ]; then
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        COMPLETIONS="${COMPLETIONS}- ${line}\n"
    done < "$CACHE_DIR/completions.txt"
fi

# Read recent commits (multi-line)
COMMITS=""
if [ -f "$CACHE_DIR/commits.txt" ]; then
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        COMMITS="${COMMITS}- ${line}\n"
    done < "$CACHE_DIR/commits.txt"
fi

# Generate scratchpad content
cat > "$SCRATCHPAD" <<EOF
# Work Status: [GL.iNet Comet Reversing](https://github.com/stvhay/glinet-comet-reverse-gpl)

**Last Updated:** $LAST_UPDATED
**Current Work:** $CURRENT_WORK

## Recent Completions (This Session)

${COMPLETIONS:+### Completions
$COMPLETIONS}
### Issues Closed
- ✅ [#71](https://github.com/stvhay/glinet-comet-reverse-gpl/issues/71) - Scratchpad staleness corrective action (CLOSED)
- ✅ [#60](https://github.com/stvhay/glinet-comet-reverse-gpl/issues/60) - Add status link to README (CLOSED)
- ✅ [#63](https://github.com/stvhay/glinet-comet-reverse-gpl/issues/63) - Simplify settings.local.json permissions (CLOSED)
- ✅ [#59](https://github.com/stvhay/glinet-comet-reverse-gpl/issues/59) - QMS wiki page (CLOSED)
- ✅ [#58](https://github.com/stvhay/glinet-comet-reverse-gpl/issues/58) - Command audit trail CI integration (CLOSED)
- ✅ [#49](https://github.com/stvhay/glinet-comet-reverse-gpl/issues/49) - Convert ASCII diagrams to Mermaid (CLOSED)

### Epic Completed
- ✅ **Epic #64** - Collaboration Framework (CLOSED)
  - All 6 child issues completed (#65, #66, #67, #68, #69, #70)
  - Dual profile system implemented (agent + QMS)
  - Maintainer onboarding process documented
  - Integration with Management Review complete

## Open Work

### Issue #31 - BaseScript Enhancement (COMPLETE)
**Status:** ✅ All 8 scripts refactored, all 647 tests passing
**Result:** Eliminated ~160 lines of duplicated boilerplate
**Commits:**
- ✅ Commit 089462a: Added 11 helper methods to base classes (+348 lines to lib/)
- ✅ Commit ae1ac6c: Refactored analyze_binwalk.py, analyze_device_trees.py
- ✅ Commit f069050: Refactored analyze_uboot.py, analyze_rootfs.py
- ✅ Commit d944188: Refactored remaining 4 scripts + fixed all tests
**Lines saved:**
- analyze_binwalk.py: -8 lines
- analyze_device_trees.py: -15 lines
- analyze_uboot.py: -17 lines
- analyze_rootfs.py: -20 lines
- analyze_proprietary_blobs.py: -18 lines
- analyze_network_services.py: -17 lines
- analyze_secure_boot.py: -24 lines
- analyze_boot_process.py: -21 lines
**Total:** -140 lines (scripts) + 115 saved (tests) = 255 lines cleaner
**Next:** Close issue #31, continue Epic #30

### Epic #30 - Codebase Refactoring 2025 ⭐
**Status:** IN PROGRESS (Issue #31 started)
**Child Issues:** 13 issues (#31-#43)
**Phases:**
- Phase 1: Core Infrastructure (#31-#33) - Extract base classes, create lib modules
- Phase 2: Specialized Utilities (#34-#35) - Device tree parser, offset manager
- Phase 3: Code Quality (#36-#38) - Error handling, type hints, complexity reduction
- Phase 4: Test Improvements (#39-#41) - Integration tests, fixtures, edge cases
- Phase 5: Documentation (#42-#43) - Architecture diagrams, cleanup

### Other Open Issues
- [#50](https://github.com/stvhay/glinet-comet-reverse-gpl/issues/50) - Docker/container access for agents
- [#44](https://github.com/stvhay/glinet-comet-reverse-gpl/issues/44) - Community Standards
- [#21](https://github.com/stvhay/glinet-comet-reverse-gpl/issues/21) - Jinja template documentation system
- [#18-20](https://github.com/stvhay/glinet-comet-reverse-gpl/issues/18) - Hardware verification issues

## Recent Commits (Last 9)

${COMMITS:+$COMMITS}
## Session Summary

**Work completed:** 6 issues + 1 epic (Epic #64 + issues #49, #58, #59, #60, #63, #71)
**Commits:** 7 commits pushed to main
**Tests:** All 647 tests passing
**Corrective Action:** Issue #71 COMPLETE - scratchpad staleness addressed with P5 procedure + agent profile update
**Starting:** Epic #30 (Refactoring) per user request

EOF

# Also copy to repo location for commit
cp "$SCRATCHPAD" "$REPO_SCRATCHPAD"

echo "✅ Scratchpad generated: $SCRATCHPAD"
echo "✅ Copied to repo: $REPO_SCRATCHPAD"
