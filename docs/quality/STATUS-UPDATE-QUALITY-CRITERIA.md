# Status Update Quality Criteria

**Purpose:** Define objective quality standards for scratchpad and checkpoint file updates to distinguish meaningful progress tracking from compliance theater.

**Context:** Issue #78 (Epic #77 - Embedded Workflow System)

**Date:** 2025-12-13

---

## Quality Rubric

This rubric applies to **both scratchpad updates and checkpoint files**. Two independent reviewers should arrive at the same score.

### Scoring Scale (1-4)

| Score | Label | Description | Resumption Capability |
|-------|-------|-------------|----------------------|
| **1** | **Minimal** | Satisfies existence check only. States work is happening but provides no context. | Cannot resume work from this update alone. |
| **2** | **Basic** | States WHAT is being done but lacks context for WHY or NEXT. | Can identify current task but unclear how to proceed. |
| **3** | **Good** | Provides WHAT + (WHY or NEXT). Sufficient context to resume work with minor investigation. | Can resume work with brief review of recent changes. |
| **4** | **Excellent** | Provides WHAT + WHY + NEXT + status details. Complete context for immediate resumption. | Can resume work immediately without additional investigation. |

---

## Detailed Scoring Criteria

### Score 1: Minimal (Compliance Theater)

**Characteristics:**
- Generic statements that could apply to any task
- No actionable information
- Optimized to pass staleness checks, not to provide context
- Reader learns nothing beyond "agent is working"

**Examples from Issues #34, #76:**

```markdown
Status: Working on Issue #34
```

```markdown
[2025-12-13 14:23]
WHAT: Making progress on file wrapper issue
```

```markdown
Current: Issue #76
Next: Fixing the problem
```

**Why this fails:**
- "Working on" doesn't specify what action is being taken
- No indication of what's been completed or what remains
- Cannot resume work from this information
- Pure compliance, zero value

---

### Score 2: Basic (What, No Why)

**Characteristics:**
- States specific action being taken
- Missing rationale or next steps
- Partially useful but incomplete for resumption
- Reader knows current task but not broader context

**Examples:**

```markdown
Status: Creating lib/devicetree.py with parser class
```

```markdown
[2025-12-13 14:45]
WHAT: Removing auto_commit parameter from file wrapper
```

```markdown
Current: Writing tests for DeviceTreeParser
Files: test_lib_devicetree.py
```

**Why this is insufficient:**
- Knows WHAT but not WHY this choice was made
- Unclear what the next step should be
- Missing status of related files or dependencies
- Better than Score 1 but still requires investigation to resume

---

### Score 3: Good (What + Why/Next)

**Characteristics:**
- States WHAT is being done
- Provides EITHER rationale (WHY) OR next steps (NEXT)
- Sufficient context to resume with minimal investigation
- Reader understands current state and can infer how to proceed

**Examples:**

```markdown
Status: Created lib/devicetree.py (237 lines, 6 methods)
Next: Writing comprehensive tests, targeting 30+ test cases
Files: scripts/lib/devicetree.py (new)
```

```markdown
[2025-12-13 15:12]
WHAT: Removing auto_commit parameter from wrapped_edit() and wrapped_write()
WHY: Creates QA compliance bypass that defeats enforcement purpose
Files: scripts/lib/file_wrapper.py
```

```markdown
Current: Issue #34 - Device tree parser refactoring
Completed: DeviceTreeParser class with full test coverage (37 tests)
Next: Refactor analyze_device_trees.py to use new parser
Status: All 668 tests passing
```

**Why this works:**
- Specific action with clear rationale OR direction
- Provides resumption context
- Shows what's done and what remains
- Reader can continue work with brief orientation

---

### Score 4: Excellent (Complete Context)

**Characteristics:**
- States WHAT is being done with specifics
- Explains WHY (rationale, problem being solved)
- Indicates NEXT steps clearly
- Includes status details (tests, blockers, files modified)
- Enables immediate work resumption without investigation

**Examples:**

```markdown
Status: Issue #34 - DeviceTreeParser implementation
Completed: Created lib/devicetree.py (237 lines, 6 methods) to consolidate DTS parsing logic duplicated across 3 scripts
WHY: Single source of truth for device tree parsing, reduces 100+ lines of duplication
Next: Write 30+ comprehensive tests covering all extraction methods and edge cases (malformed DTS, missing nodes)
Files modified: scripts/lib/devicetree.py (new)
Tests: Not yet run (will run after test suite complete)
Blockers: None
```

```markdown
[2025-12-13 16:30]
WHAT: Removed auto_commit parameter from wrapped_edit() and wrapped_write() in file_wrapper.py
WHY: Parameter created bypass allowing agent to skip gist updates and automatic commits, defeating the QA enforcement system it was meant to support (NCR-2025-12-13-001 related)
NEXT: Update all code using auto_commit=False to handle commits properly, then run full test suite
Files modified: scripts/lib/file_wrapper.py (-15 lines), tests/test_file_wrapper.py (updated)
Tests: 668/668 passing before change, need to rerun
Blockers: None
```

```markdown
Current: Issue #76 - Remove auto_commit bypass
Last checkpoint: 003-removed-parameter.txt - Eliminated auto_commit from wrapper functions
Status:
  - file_wrapper.py refactored (removed parameter, updated docstrings)
  - 2 call sites identified in analyze_*.py scripts need updates
  - Tests passing locally (pytest)
Next: Update analyze_device_trees.py and analyze_boot_process.py to remove auto_commit=False calls
Blockers: None, work proceeding normally
```

**Why this is excellent:**
- Complete picture of current state
- Clear rationale connecting to larger goals (NCR, issue purpose)
- Specific next actions
- Status includes tests, files, blockers
- Anyone (including future agent session) can resume immediately

---

## Minimum Required Fields

Updates **MUST** include these fields to be considered valid (Score ≥2):

### Scratchpad Updates

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| **Current Issue** | Yes | Issue number and title | `Issue #34 - Device tree parser` |
| **Last Action** | Yes | Specific completed action | `Created lib/devicetree.py (237 lines)` |
| **Next Action** | Yes | Specific next step | `Write 30+ comprehensive tests` |
| **Files Modified** | Yes | Changed files with status | `scripts/lib/devicetree.py (new)` |
| **Blockers** | Yes | Current blockers or "None" | `None` or `Waiting on user decision` |
| **Tests Status** | Conditional* | Pass/fail status if tests exist | `668/668 passing` |

*Required if tests exist in the project and changes affect tested code.

**Minimum scratchpad template:**
```markdown
**Current Work:** Issue #N: [title]
**Last Action:** [specific action completed]
**Next:** [specific next action]
**Files:** [modified files with status]
**Tests:** [pass/fail status]
**Blockers:** [blockers or "None"]
```

### Checkpoint Files

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| **Timestamp** | Yes | When checkpoint written | `[2025-12-13 16:45]` |
| **WHAT** | Yes | Specific action completed | `Removed auto_commit parameter` |
| **WHY** | Yes | Rationale or problem solved | `Creates compliance bypass` |
| **NEXT** | Yes | Specific next step | `Update call sites in scripts` |
| **Status** | Recommended | Files, tests, blockers | `file_wrapper.py modified, tests passing` |

**Minimum checkpoint template:**
```
[timestamp]
WHAT: [specific completed action]
WHY: [rationale or problem being solved]
NEXT: [specific next action]
STATUS: [optional: files, tests, blockers]
```

---

## Scoring Guidelines for Reviewers

### How to Score

1. **Read the update in isolation** - Pretend you're resuming work with only this information
2. **Ask:** "Can I continue work from this alone?"
   - **No** → Score 1-2
   - **With brief investigation** → Score 3
   - **Immediately** → Score 4

3. **Check required fields:**
   - Missing WHAT → Score 1
   - Has WHAT, missing WHY and NEXT → Score 2
   - Has WHAT + (WHY or NEXT) → Score 3
   - Has WHAT + WHY + NEXT + status → Score 4

4. **Consider specificity:**
   - Generic ("working on", "making progress") → Score 1
   - Vague ("creating parser", "fixing bug") → Score 2
   - Specific ("created lib/devicetree.py with 6 methods") → Score 3-4

### Inter-Rater Reliability Test

To validate the rubric is actionable, two independent reviewers should score the same update within ±1 point.

**Example test:**
```markdown
Status: Created lib/devicetree.py (237 lines, 6 methods)
Next: Writing comprehensive tests, targeting 30+ test cases
```

**Expected scores:** Both reviewers should score this as **3** (has WHAT + NEXT, missing WHY, no test status).

If reviewers consistently disagree by >1 point, the rubric needs refinement.

---

## Common Failure Patterns

### Pattern 1: "Working on" Syndrome (Score 1)

**Problem:** Generic status that provides no actionable information.

**Example:**
```markdown
Status: Working on Issue #34
```

**Fix:**
```markdown
Status: Created DeviceTreeParser class (237 lines, 6 methods) in lib/devicetree.py
Next: Writing 30+ tests covering extraction methods and edge cases
Files: scripts/lib/devicetree.py (new)
Tests: Not yet run
Blockers: None
```

### Pattern 2: Missing Context (Score 2)

**Problem:** States action but no rationale or next steps.

**Example:**
```markdown
[2025-12-13 14:45]
WHAT: Removing auto_commit parameter
```

**Fix:**
```markdown
[2025-12-13 14:45]
WHAT: Removing auto_commit parameter from wrapped_edit() and wrapped_write()
WHY: Creates bypass that defeats QA enforcement (Issue #76)
NEXT: Update call sites in analyze_*.py scripts, then run full test suite
STATUS: file_wrapper.py modified, tests pending
```

### Pattern 3: Vague Next Steps (Score 2-3)

**Problem:** Next action is unclear or generic.

**Example:**
```markdown
Next: Continue working on tests
```

**Fix:**
```markdown
Next: Write 30+ tests for DeviceTreeParser covering:
  - All 6 extraction methods
  - Edge cases: malformed DTS, missing nodes
  - Real DTS files from firmware
```

### Pattern 4: Missing Status (Score 3 vs 4)

**Problem:** Has WHAT/WHY/NEXT but unclear on current state.

**Example:**
```markdown
WHAT: Created lib/devicetree.py
WHY: Consolidate DTS parsing logic
NEXT: Write comprehensive tests
```

**Fix:**
```markdown
WHAT: Created lib/devicetree.py (237 lines, 6 methods)
WHY: Consolidate DTS parsing logic duplicated across 3 scripts
NEXT: Write 30+ comprehensive tests
FILES: scripts/lib/devicetree.py (new)
TESTS: Not yet run (will run after test suite complete)
BLOCKERS: None
```

---

## Application Guidelines

### When to Update

**Scratchpad:**
- At issue start (establish baseline)
- After significant actions (file creation, major edits, test runs)
- Before/after tool calls that modify files
- Before commits
- When stopping work (session end)

**Checkpoint files:**
- After completing discrete subtasks
- Before/after significant decisions
- When hitting blockers or needing to investigate
- At natural stopping points
- When switching between tasks

### Frequency vs. Quality Trade-off

**Bad approach:** Frequent updates with minimal content (Score 1-2)
- Updates every 5 minutes saying "Working on X"
- Satisfies staleness check but provides no value
- Compliance theater

**Good approach:** Less frequent updates with complete content (Score 3-4)
- Updates after meaningful progress (file created, tests written, blocker hit)
- Each update provides resumption context
- Quality over compliance frequency

**Principle:** Better to have 3 excellent updates (Score 4) in an hour than 12 minimal updates (Score 1) in the same time.

---

## Validation and Continuous Improvement

### Periodic Review

Every 10 issues, conduct quality audit:
1. Randomly sample 5 scratchpad updates and 5 checkpoint files
2. Two reviewers independently score each sample
3. Calculate inter-rater reliability (agreement within ±1 point)
4. Calculate average score across samples

**Target metrics:**
- Inter-rater agreement: ≥80%
- Average score: ≥3.0
- No Score 1 updates in sample

### Failure Indicators

If audit reveals:
- **Average score <2.5:** Agent is not internalizing purpose, reverting to compliance theater
- **Inter-rater agreement <60%:** Rubric is too subjective, needs refinement
- **>20% Score 1 updates:** Enforcement mechanism failing, agent bypassing intent

**Action:** Trigger corrective action process (P4) and reassess approach.

---

## Relationship to Embedded Workflow (Epic #77)

This rubric supports the embedded workflow experiment by:

1. **Defining "quality"** - Rubric makes quality measurable and objective
2. **Enabling measurement** - Can track whether agent improves over time (Phase 0.2)
3. **Informing guidelines** - Checkpoint file guidelines (Issue #81) will incorporate this rubric
4. **Validating internalization** - Declining scores indicate metric optimization, not purpose understanding

**Exit criteria for Epic #77:** If quality scores trend downward over time despite guidelines, the embedded workflow is failing and alternative approaches (human-in-loop, reduced scope) should be considered.

---

## References

- **Lessons Learned:** [LESSONS-LEARNED-2025-12-13-qa-purpose.md](LESSONS-LEARNED-2025-12-13-qa-purpose.md)
- **Epic #77:** Embedded Workflow System
- **Issue #34:** DeviceTreeParser implementation (example of bad/good updates)
- **Issue #76:** Remove auto_commit bypass (example of minimal updates)
- **NCR-2025-12-13-001:** Scratchpad staleness non-conformance

---

**Version:** 1.0
**Date:** 2025-12-13
**Status:** Draft for review
**Next:** User review, then inform Issues #79 (measurement methodology) and #81 (checkpoint guidelines)
