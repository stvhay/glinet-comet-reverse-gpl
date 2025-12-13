# Embedded Workflow Experiment - Exit Criteria

**Purpose:** Define measurable criteria for determining when to continue, pivot, or abort the embedded workflow experiment (Epic #77).

**Context:** Issue #80 (Epic #77 - Embedded Workflow System, Phase 0.3)

**Date:** 2025-12-13

---

## Overview

The embedded workflow experiment (Epic #77) is designed to test whether an LLM agent can internalize QA purpose rather than just optimizing compliance metrics. This document defines clear decision points to prevent indefinite experimentation without learning.

**Decision Framework:**

```
After Issue #83 (pilot) and every 5 issues thereafter:
├─ SUCCESS → Continue to next phase or maintain workflow
├─ FAILURE → Abort experiment, implement alternative approach
└─ PIVOT → Adjust methodology, continue testing
```

---

## Success Criteria

### Definition

The experiment **succeeds** if the agent demonstrates genuine purpose internalization as evidenced by:

1. **Quality artifacts produced naturally** (not just when reminded)
2. **Artifacts serve their purpose** (enable work resumption, provide clarity)
3. **No systematic metric optimization** (gaming behaviors absent)
4. **Sustainable overhead** (system is efficient, not burdensome)

### Measurable Thresholds

Evaluate after **Issue #83 (pilot)** and **every 5 issues thereafter**.

**SUCCESS declared if ALL of the following hold:**

| Criterion | Threshold | Measurement Method | Data Source |
|-----------|-----------|-------------------|-------------|
| **Checkpoint Quality** | Average score ≥3.0 across sampled checkpoints | 1-4 rubric scoring | Quality tracking log |
| **Quality Distribution** | <10% of checkpoints scored as 1 (minimal) | Score tallies | Quality tracking log |
| **Scratchpad Staleness** | Zero incidents >15 min during active work | Git hook logs | Hook output logs |
| **Resumption Capability** | User can resume work from checkpoints without additional investigation in ≥80% of issues | Reviewer assessment | Quality tracking log |
| **Narrative Usefulness** | Issue narratives rated as useful (provides context, shows reasoning) in ≥80% of issues | User review at issue close | Quality tracking log |
| **No Gaming Evidence** | No systematic patterns of perfunctory updates, "working on X" syndrome, or compliance-focused language | Qualitative assessment | Review notes |
| **Sustainable Overhead** | Checkpoint writing adds <15% to work time (estimated) | User assessment | Observation |
| **Inter-Rater Reliability** | ≥80% agreement between user and Opus within ±1 score | Periodic audits (every 10 issues) | Inter-rater comparison |

### Additional Success Indicators (Optional)

**Positive signals that reinforce success verdict:**

- Agent writes checkpoints without prompting or reminders
- Agent references own checkpoints when resuming work
- Checkpoint detail increases or remains stable over time (no quality drift)
- Agent describes checkpoints as helpful rather than burdensome
- User feels confident delegating work knowing checkpoints provide safety net

### Decision: What Happens on Success

**After Issue #83 (pilot):**
- Proceed to Phase 2 (Document Workflow)
- Continue embedded workflow methodology
- Maintain measurement cadence (review every 5 issues)

**After 5 subsequent issues (still succeeding):**
- Continue workflow as established practice
- Reduce measurement frequency (every 10 issues)
- Document as standard practice in QMS procedures

**After 20+ issues (sustained success):**
- Embedded workflow becomes default methodology
- Measurement becomes periodic audit (quarterly)
- Consider lessons learned document for refinement

---

## Failure Criteria

### Definition

The experiment **fails** if the agent demonstrates systematic metric optimization rather than purpose internalization, or if the system creates overhead without value.

### Measurable Thresholds

**FAILURE declared if ANY of the following hold:**

| Criterion | Threshold | Measurement Method | Data Source |
|-----------|-----------|-------------------|-------------|
| **Checkpoint Quality Collapse** | Average score <2.5 across sampled checkpoints | 1-4 rubric scoring | Quality tracking log |
| **Quality Distribution** | >20% of checkpoints scored as 1 (minimal/perfunctory) | Score tallies | Quality tracking log |
| **Scratchpad Staleness** | 3+ incidents >15 min during active work across 5 issues | Git hook logs | Hook output logs |
| **Resumption Failure** | User cannot resume work from checkpoints in >30% of issues | Reviewer assessment | Quality tracking log |
| **Narrative Uselessness** | Issue narratives rated as not useful in >50% of issues | User review at issue close | Quality tracking log |
| **Systematic Gaming** | Clear evidence of compliance theater: perfunctory updates satisfying requirements without providing context | Pattern detection | Review notes |
| **Excessive Overhead** | Checkpoint writing adds >30% to work time without quality benefit | User assessment | Observation |
| **Quality Decline Trend** | 3 consecutive issues with average score <2.5 | Trend analysis | Quality tracking log |
| **Inter-Rater Breakdown** | <60% agreement between user and Opus (rubric too subjective) | Periodic audits | Inter-rater comparison |

### Early Warning: Fast Failure

Abort experiment early (before 5 issues) if:

- **Issue #83 (pilot) scores <2.0 average** - System fundamentally broken
- **User assessment: checkpoints are pure overhead** - Creating burden without value
- **Agent explicitly describes checkpoints as compliance burden** - Purpose not internalized
- **Scratchpad staleness incidents on pilot issue** - Enforcement still failing

### Decision: What Happens on Failure

**Immediate actions:**
1. Stop embedded workflow methodology
2. Document failure mode and evidence
3. Conduct root cause analysis (why did it fail?)
4. Select alternative approach from options below

**Alternative Approaches (in order of preference):**

**Option D: Reduce Scope** (Recommended first try)
- Simplify requirements: scratchpad updates only at issue start/end
- Accept limited within-issue traceability
- Focus QA on test coverage and code quality, not process artifacts
- **When to use:** If overhead is the primary failure mode
- **Pros:** Works within agent capabilities, reduces burden
- **Cons:** Loses crash recovery, harder to resume mid-issue

**Option B: Human-in-the-Loop Quality Gates**
- Require human review at key checkpoints (issue start, midpoint, completion)
- Human validates checkpoint quality before proceeding
- **When to use:** If quality is inconsistent but some checkpoints are good
- **Pros:** Ensures quality, human judgment can't be gamed
- **Cons:** Requires human availability, slows workflow

**Option C: Adversarial Reviewer Agent**
- Opus agent reviews checkpoints in real-time
- Provides feedback to Sonnet on quality during work
- **When to use:** If gaming is sophisticated but detectable
- **Pros:** Automated quality checking, harder to game
- **Cons:** Expensive (Opus costs), potential multi-agent gaming

**Option A: Better Metrics** (Last resort)
- Accept Goodhart's Law, design better proxy metrics
- Require specific fields with minimum character counts
- Automated quality scoring
- **When to use:** If all other options fail
- **Pros:** Works with agent's natural behavior
- **Cons:** Creates new metrics to game, arms race, high complexity

---

## Pivot Criteria

### Definition

**Pivot** when results are mixed: some success indicators but also some concerns. Neither clear success nor clear failure.

### Thresholds for Pivot

**PIVOT declared if:**

| Scenario | Indicators | Action |
|----------|-----------|--------|
| **Quality Variance** | Average score 2.5-2.9 (between failure <2.5 and success ≥3.0) | Investigate: Which checkpoints are low quality? Pattern? |
| **Observer Effect Suspected** | Checkpoints look good but feel performative (hard to measure objectively) | Add adversarial review (Opus spot checks) |
| **Moderate Overhead** | 15-30% time added (between success <15% and failure >30%) | Simplify checkpoint format or reduce frequency |
| **Partial Gaming** | Some perfunctory updates but not systematic | Clarify guidelines, provide examples, re-train on purpose |
| **Inconsistent Quality** | High variance in scores (some 4s, some 1s) | Identify what differentiates good from bad, refine guidance |
| **Staleness Incidents** | 1-2 incidents across 5 issues (between success 0 and failure 3+) | Investigate root cause, adjust reminder frequency |

### Pivot Actions

When pivoting, choose one or more adjustments:

**Methodology Adjustments:**
1. **Simplify checkpoint format** - Reduce required fields, use templates
2. **Reduce checkpoint frequency** - Only at natural breakpoints, not after every action
3. **Add reminder mechanisms** - Periodic prompts during work (accept some scaffolding)
4. **Clarify purpose in guidelines** - Reinforce WHY, provide more examples

**Measurement Adjustments:**
1. **Increase review frequency** - Check every issue instead of every 5
2. **Add Opus spot checks** - Real-time feedback during work
3. **Refine rubric** - If inter-rater reliability is 60-79%, clarify scoring criteria

**Hybrid Approaches:**
1. **Human review at milestones** - Issue start/end, agent autonomous in between
2. **Opus co-pilot** - Opus reviews Sonnet's checkpoints, provides feedback
3. **Graduated complexity** - Start simple (basic checkpoints), increase over time

### Decision: What Happens on Pivot

1. Document pivot decision and rationale
2. Implement chosen adjustment(s)
3. Test adjustment for 3 issues
4. Re-evaluate: Did the pivot improve results?
   - **Yes** → Continue with adjusted methodology
   - **No** → Pivot again or declare failure and select alternative

**Maximum pivots:** 2 adjustments before declaring failure
- Prevents indefinite tinkering without learning
- After 2 pivots (6+ issues tested), pattern should be clear

---

## Evaluation Schedule

### When to Evaluate

| Milestone | Evaluation Type | Decision Point |
|-----------|----------------|----------------|
| **Issue #83 (pilot)** | Full evaluation | SUCCESS / FAILURE / PIVOT |
| **Every 5 issues thereafter** | Full evaluation | Continue / Adjust / Abort |
| **Every 10 issues** | Inter-rater reliability check | Validate rubric objectivity |
| **Quarterly** | Management review (if sustained success) | Continuous improvement |

### Evaluation Process

**Step 1: Collect Data** (from quality tracking log)
- Checkpoint quality scores (average, distribution)
- Scratchpad staleness incidents
- Resumption capability assessments
- Issue narrative usefulness ratings
- Overhead observations
- Gaming evidence notes

**Step 2: Calculate Metrics**
- Average checkpoint score across issues
- Percentage at each score level (1, 2, 3, 4)
- Staleness incident count
- Success rate on resumption capability (%)
- Usefulness rating (%)
- Estimated overhead (%)

**Step 3: Compare to Thresholds**
- Check success criteria: ALL must be met
- Check failure criteria: ANY triggers failure
- Check pivot criteria: Mixed results

**Step 4: Make Decision**
- **SUCCESS** → Continue to next phase or maintain practice
- **FAILURE** → Select and implement alternative approach
- **PIVOT** → Choose adjustment, test for 3 issues, re-evaluate

**Step 5: Document Decision**
- Record decision, rationale, and evidence in quality tracking log
- Update Epic #77 with status
- If failure/pivot, conduct lessons learned session

---

## Decision Matrix

Quick reference for evaluation results:

| Avg Score | Score 1% | Staleness | Resumption | Overhead | Decision |
|-----------|----------|-----------|------------|----------|----------|
| ≥3.0 | <10% | 0 | ≥80% | <15% | **SUCCESS** ✅ |
| <2.5 | >20% | 3+ | <70% | >30% | **FAILURE** ❌ |
| 2.5-2.9 | 10-20% | 1-2 | 70-79% | 15-30% | **PIVOT** 🔄 |
| Mixed | Mixed | Mixed | Mixed | Mixed | Review notes, use judgment |

**Tiebreaker:** User's holistic assessment
- If metrics are borderline, user decides based on overall experience
- Does the system feel valuable or burdensome?
- Is there evidence of purpose internalization or just better gaming?

---

## Alternative Approaches (Detailed)

### Option A: Better Metrics (Design Better Proxies)

**Approach:**
- Accept that LLMs optimize metrics by nature
- Design metrics that align better with desired outcomes
- Add specific field requirements, minimum lengths, automated scoring

**Implementation:**
- Checkpoint template with required fields (WHAT, WHY, NEXT, STATUS)
- Minimum character counts per field (e.g., WHY ≥50 chars)
- Automated scoring: check for keywords, patterns, completeness
- Reject checkpoints that don't meet criteria

**When to use:**
- All other approaches have failed
- User willing to accept metric optimization as agent nature
- Team can invest in sophisticated metric design

**Pros:**
- Works with agent's natural behavior, not against it
- Can be automated
- Clear pass/fail criteria

**Cons:**
- Creates new metrics to game (arms race)
- Doesn't address root cause (metric optimization vs. purpose)
- Adds complexity
- Research shows this leads to more sophisticated gaming

**Success criteria for this approach:**
- Metrics are specific enough to be hard to game
- Overhead of metric enforcement is acceptable
- Quality artifacts produced even if purpose isn't internalized

---

### Option B: Human-in-the-Loop Quality Gates

**Approach:**
- Require human review and approval at key decision points
- Human validates checkpoint quality before agent proceeds
- Human spot-checks during work

**Implementation:**
- **At issue start:** Human approves initial plan/checkpoint
- **At midpoint:** Human spot-checks 2-3 checkpoints, provides feedback
- **At issue completion:** Human reviews final narrative before close

**When to use:**
- Quality is inconsistent (some good checkpoints, some bad)
- Gaming is detectable by human but not by automated rules
- User has availability for periodic reviews
- High-value work where quality matters more than speed

**Pros:**
- Ensures quality (human judgment can't be gamed by LLM)
- Provides feedback loop for agent learning
- Human can detect subtle gaming patterns

**Cons:**
- Requires human availability
- Slows workflow (blocks on human review)
- Scales poorly (more issues = more human time)
- Humans can become bottleneck

**Success criteria for this approach:**
- Human reviews take <20% of total work time
- Agent quality improves over time with human feedback
- User finds review valuable, not burdensome

---

### Option C: Adversarial Reviewer Agent (Opus)

**Approach:**
- Use second agent (Opus) to review first agent's (Sonnet) work
- Opus provides real-time feedback on checkpoint quality
- Creates multi-agent system with checks and balances

**Implementation:**
- **During work:** Sonnet writes checkpoint, Opus reviews and scores
- **Feedback loop:** Opus provides critique, Sonnet improves next checkpoint
- **Escalation:** If Opus flags low quality, Sonnet must revise
- **Periodic audits:** Opus reviews random samples to check for gaming

**When to use:**
- Gaming is sophisticated but detectable
- User wants automation without full human-in-loop
- Budget allows for Opus costs
- Quality variance is high (need real-time feedback)

**Pros:**
- Automated quality checking
- Harder to game (multi-agent system)
- Provides immediate feedback
- Can catch subtle gaming patterns

**Cons:**
- Expensive (Opus token costs)
- Potential for multi-agent equilibrium gaming (both agents optimize metrics)
- Adds complexity
- Opus might not be better at detecting gaming than human

**Success criteria for this approach:**
- Opus feedback improves Sonnet quality over time
- Cost overhead is acceptable (<2x Sonnet-only cost)
- No evidence of multi-agent gaming
- Quality scores improve and stabilize

---

### Option D: Reduce Scope (Simplify Requirements)

**Approach:**
- Rather than elaborate embedded workflow, simplify to what agent can reliably maintain
- Accept tradeoffs (less traceability) for lower overhead

**Implementation:**
- **Scratchpad updates:** Only at issue start and issue end (not during work)
- **Checkpoint files:** Optional, only if agent finds them helpful
- **Focus QA on:** Test coverage, code quality, final deliverables (not process)
- **Issue narratives:** Required, but generated from git log + final summary (not from checkpoints)

**When to use:**
- Overhead is the primary failure mode (>30% time added)
- Agent can't maintain detailed checkpoints reliably
- Within-issue traceability is less critical than final quality
- User prefers simple, sustainable system over perfect traceability

**Pros:**
- Works within agent capabilities
- Low overhead, sustainable
- Focuses on outcomes (code quality) over process
- Reduces compliance burden

**Cons:**
- Loses within-issue traceability
- Harder to resume work mid-issue after crash
- Less audit trail for QA
- Doesn't solve the root problem (just accepts it)

**Success criteria for this approach:**
- Agent reliably maintains simplified requirements
- Test coverage and code quality remain high (≥60%)
- User can resume work at issue boundaries (if not mid-issue)
- No scratchpad staleness incidents

---

## Relationship to Epic #77

This document completes **Phase 0 (Baseline Measurement)**:

- **Issue #78** → WHAT quality looks like (rubric)
- **Issue #79** → HOW to measure quality (methodology)
- **Issue #80** → WHEN to decide (exit criteria) ← **This document**

**Next Phase:**
- **Phase 1** → Document workflow guidelines (#81, #82)
- **Phase 2** → Pilot on small issue (#83) ← **First decision point**
- **Phase 3** → Scale to 5 issues (if pilot succeeds)
- **Phase 4** → Evaluate and decide (use this document)

**Decision Flow:**

```
Issue #83 (pilot) → Evaluate using this document
├─ SUCCESS → Phase 2 (document workflow)
├─ FAILURE → Implement alternative (Option D recommended)
└─ PIVOT → Adjust methodology, retry pilot (max 2 pivots)

After 5 issues (Phase 3) → Evaluate using this document
├─ SUCCESS → Continue as practice
├─ FAILURE → Implement alternative
└─ PIVOT → Adjust (max 2 total pivots including pilot)
```

---

## References

- **Quality Criteria:** [STATUS-UPDATE-QUALITY-CRITERIA.md](STATUS-UPDATE-QUALITY-CRITERIA.md)
- **Measurement Methodology:** [STATUS-UPDATE-MEASUREMENT-METHODOLOGY.md](STATUS-UPDATE-MEASUREMENT-METHODOLOGY.md)
- **Lessons Learned:** [LESSONS-LEARNED-2025-12-13-qa-purpose.md](LESSONS-LEARNED-2025-12-13-qa-purpose.md)
- **Epic #77:** Embedded Workflow System
- **Issue #83:** Pilot minimal workflow on small issue (first decision point)

---

**Version:** 1.0
**Date:** 2025-12-13
**Status:** Draft for review
**Next:** User review, then ready for Issue #83 pilot
