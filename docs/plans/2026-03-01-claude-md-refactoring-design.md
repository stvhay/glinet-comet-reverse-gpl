# CLAUDE.md Refactoring Design

**Date**: 2026-03-01
**Goal**: Reduce CLAUDE.md from ~465 lines (~17KB) to ~150-170 lines by extracting large sections to standalone files, deduplicating, and organizing MEMORY.md.

## Problem

CLAUDE.md consumes ~17KB of context every conversation turn. ~60% of the content is reference material (checkpoint workflow, staff work doctrine, Jinja template examples) that's only needed occasionally. The auto-memory file references a stale "zig-expert skill" from a different project. Repo-root MEMORY.md is untracked and shows in git status.

## Changes

### New files

1. **`.claude/WORKFLOW.md`** - Embedded Workflow / Checkpoint system (lines 243-357 of current CLAUDE.md). Extracted verbatim; CLAUDE.md gets 2-line reference.

2. **`standards/COMPLETED-STAFF-WORK.md`** - Completed Staff Work doctrine (lines 411-458 of current CLAUDE.md) + tone-in-public-issues guidance (from MEMORY.md). CLAUDE.md gets 2-line reference.

### Modified files

3. **`CLAUDE.md`** (~465 -> ~150-170 lines):
   - Quality Management: condense to 3-line summary + link to `docs/quality/`
   - Documentation System: condense to 5-line summary + link to `docs/design-jinja-documentation.md`
   - Development section: deduplicate (pytest mentioned 4x -> 1x)
   - Embedded Workflow: replace with 2-line reference to `.claude/WORKFLOW.md`
   - Completed Staff Work: replace with 2-line reference to `standards/COMPLETED-STAFF-WORK.md`
   - Settings/Auth Commands: condense to 2 lines
   - Firmware section: add SDK layout + which-repos-matter from MEMORY.md

4. **`MEMORY.md`** (repo root):
   - Remove "Issue Tracking State" section (redundant pointer to scratchpad)
   - Remove SDK layout (moved to CLAUDE.md Firmware section)
   - Remove "Which repos matter" (moved to CLAUDE.md Firmware section)
   - Remove tone guidance (moved to Staff Work file)

5. **`~/.claude/projects/-Users-hays-Projects-glinet-comet-reversing/memory/MEMORY.md`** (auto-memory):
   - Replace zig-expert reference with pointer to repo-root MEMORY.md

6. **`.gitignore`**: Add `MEMORY.md`

## What stays in CLAUDE.md

- Project identity + repo link
- Legal constraints
- Firmware details (enriched with SDK layout + relevant repos)
- Reverse engineering methodology (core principles)
- Development essentials (env setup, git standards, quality checks - deduplicated)
- Brief references to extracted docs
- Issue templates, subagents, CI/CD (already brief)

## Implementation order

1. Create `.claude/WORKFLOW.md` (extract from CLAUDE.md)
2. Create `standards/COMPLETED-STAFF-WORK.md` (extract from CLAUDE.md + MEMORY.md tone section)
3. Rewrite CLAUDE.md (condense, reference, enrich Firmware section)
4. Clean up MEMORY.md (remove moved content)
5. Update auto-memory MEMORY.md (fix zig reference)
6. Add MEMORY.md to .gitignore
