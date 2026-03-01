# Embedded Workflow (Checkpoint Files)

**Status:** Experimental (Epic #77) - Under evaluation via pilot Issue #83

The embedded workflow uses checkpoint files to enable work resumption and provide context clarity. Checkpoints serve the agent's own reasoning process first, QA second.

**Purpose:**
- Enable work resumption after session breaks or crashes
- Provide context clarity for the agent's own reasoning
- Generate issue narratives as natural byproduct of clear thinking
- Prevent scratchpad staleness through regular status updates

**Location:** `.claude/work/issue-N/NNN-description.txt`

## When to Write Checkpoints (Significant Actions)

Write a checkpoint file after:
- Created/modified a file (scripts, tests, docs)
- Ran tests and discovered failures or successes
- Completed a TodoWrite task
- Discovered important information (grep/glob findings, analysis results)
- Made a commit
- Hit a blocker or changed approach
- **Session start (always)**
- **Session end (always)**
- **Issue start (always)**
- **Issue close (always)**

Do NOT write checkpoints for:
- Reading files for context
- Running formatting tools (ruff format)
- Small edits to fix typos
- Consecutive commits in same logical unit of work

## Checkpoint Format

```
[YYYY-MM-DD HH:MM]
WHAT: <What was just accomplished - be specific>
WHY: <Why this action was taken - rationale, problem solved>
NEXT: <What's the next planned action - specific>
STATUS: <Optional: files modified, tests status, blockers>
```

## Quality Target

Checkpoints are scored using a 1-4 rubric:
- **Score 3-4 (Target):** Includes WHAT + WHY + NEXT with sufficient detail to resume work
- **Score 1-2 (Avoid):** Perfunctory, generic, compliance theater ("Working on issue", "Making progress")

**Reference:** [STATUS-UPDATE-QUALITY-CRITERIA.md](../docs/quality/STATUS-UPDATE-QUALITY-CRITERIA.md)

## Granularity Guidance

- **Target:** 3-8 checkpoints per issue
- **Too few (<3):** Insufficient detail for resumption
- **Too many (>10):** Overhead, likely over-documenting

## Examples

**Good checkpoint (Score 4):**
```
[2025-12-13 14:30]
WHAT: Created DeviceTreeParser class with 6 methods (parse, find_node, get_property, extract_model, extract_compatible, extract_fit_description)
WHY: Consolidate DTS parsing logic from analyze_device_trees.py to eliminate 100+ lines of duplication across 3 scripts
NEXT: Write comprehensive tests targeting 30+ test cases covering all extraction methods and edge cases (malformed DTS, missing nodes)
STATUS: scripts/lib/devicetree.py created (237 lines), tests not yet run
```

**Bad checkpoint (Score 1 - AVOID):**
```
[2025-12-13 14:30]
WHAT: Working on issue
WHY: Need to finish
NEXT: Continue
```

## Key Principle

**Checkpoints serve YOUR clarity and work resumption.** If they're helpful for you to understand what you were doing and what comes next, they'll be useful for QA. If they're compliance theater, they fail the purpose.

Think of checkpoints as writing a note to your future self who will resume this work after a session break. What would you need to know?

## Integration with Scratchpad

Checkpoint files complement but don't replace scratchpad updates:
- **Scratchpad:** High-level current state (what issue, what's happening now, what's next)
- **Checkpoints:** Detailed work log (what was done, why, reasoning, next steps)

Both are required. Scratchpad is enforced by P5 procedure (15-minute staleness check). Checkpoints are voluntary but measured for quality.

## Pushing Scratchpad to Gist

**Recommended after every checkpoint:**

```bash
.claude/scripts/push-scratchpad-gist.sh
```

This script:
- Pushes current scratchpad state to gist for real-time visibility
- Non-blocking (runs in background, doesn't delay work)
- Race-safe (semaphore prevents concurrent pushes)
- Best-effort (post-commit hook provides guaranteed sync)

If another push is already in progress, the script skips silently.

## References

- **Epic #77:** Embedded Workflow System
- **Quality Criteria:** [STATUS-UPDATE-QUALITY-CRITERIA.md](../docs/quality/STATUS-UPDATE-QUALITY-CRITERIA.md)
- **Measurement Methodology:** [STATUS-UPDATE-MEASUREMENT-METHODOLOGY.md](../docs/quality/STATUS-UPDATE-MEASUREMENT-METHODOLOGY.md)
- **Exit Criteria:** [EMBEDDED-WORKFLOW-EXIT-CRITERIA.md](../docs/quality/EMBEDDED-WORKFLOW-EXIT-CRITERIA.md)
