# User Profile Schema Design

**Version**: 1.0
**Created**: 2025-12-12
**Issue**: #65

---

## Purpose

This document defines the schema for user-specific profiles used in the Collaboration Framework. These profiles enable AI agents to understand maintainer expertise, communication preferences, and authority boundaries.

---

## Dual Profile System

### Overview

Each maintainer has **two profile files** serving different audiences:

1. **Agent Reference** (`.claude/agents/<username>.md`)
   - **Audience**: AI agents (Claude Code, subagents)
   - **Purpose**: Collaboration context - when to defer/challenge, communication style
   - **Usage**: Read by main agent for user-specific guidance
   - **Format**: YAML frontmatter + Markdown instructions

2. **QMS Competency Profile** (`docs/quality/maintainers/<username>.md`)
   - **Audience**: Project lead, auditors, QMS reviewers
   - **Purpose**: ISO 9001 competency evidence, development planning
   - **Usage**: Management reviews, competency verification
   - **Format**: Markdown with structured sections

### Why Separate?

- **Separation of concerns**: AI usage guidance vs. ISO 9001 compliance
- **Different audiences**: Technical (agents) vs. administrative (reviewers)
- **Different update cycles**: Ad-hoc (agent) vs. quarterly/annual (QMS)
- **Cleaner organization**: Focused content per file

### Sync Mechanism

- **Quarterly check**: Management Review Section 6.1.1 verifies consistency
- **Update together**: Changes to expertise/communication should update both files
- **Version control**: Git tracks all changes with commit messages explaining rationale

---

## Schema 1: Agent Reference File

### File Location

`.claude/agents/<username>.md`

**Example**: `.claude/agents/stvhay.md`

### YAML Frontmatter

```yaml
---
name: <username>-context
description: Context about user <Full Name> (<username>) for AI agent collaboration. Reference only - not spawnable.
type: user-profile
user: <username>
last_updated: YYYY-MM-DD
---
```

**Field Definitions:**

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `name` | string | Yes | Identifier for this profile | `stvhay-context` |
| `description` | string | Yes | One-line purpose statement | `Context about user Steve Hay (stvhay)...` |
| `type` | string | Yes | Must be `user-profile` | `user-profile` |
| `user` | string | Yes | GitHub username | `stvhay` |
| `last_updated` | date | Yes | ISO 8601 date (YYYY-MM-DD) | `2025-12-12` |

**Notes:**
- `name` should be `<username>-context` to distinguish from role-based agents
- `type: user-profile` distinguishes from spawnable agents (which lack this field)
- `description` should clarify "Reference only - not spawnable"

### Markdown Body Structure

```markdown
# <Full Name> (<username>) - User Profile for AI Collaboration

**Purpose:** [One sentence explaining this document's role]

**IMPORTANT:** This is a reference document, not a spawnable agent. Main agent should read this for context when interacting with <username>.

## Technical Expertise

### Expert Level (Defer to User)
- **<Domain>**: <Evidence of expertise>

**When to defer:**
- [List scenarios where agent should ask user, not tell]

### Advanced Level (Collaborate Actively)
- **<Domain>**: <Evidence of expertise>

**When to collaborate:**
- [List scenarios for active discussion]

### Intermediate Level (Agent-Led with Oversight)
- **<Domain>**: <Evidence of expertise>

**When to challenge (gently):**
- [List scenarios where agent should recommend with explanation]

### Novice Level (Agent Should Lead)
- [Areas not listed above: Assume agent knowledge unless user demonstrates expertise]

## Communication Preferences

### Completed Staff Work Doctrine
**Preference**: [Strong | Moderate | Weak]

[Explain what this means for interaction style]

### Detail Level
- **Planning**: [High | Moderate | Low]
- **Implementation**: [High | Moderate | Low]
- **Routine Tasks**: [High | Moderate | Low]

### Escalation Preferences
**When to ask user:**
- [List decision types requiring user approval]

**When to proceed autonomously:**
- [List routine items agent can handle]

## Authority Boundaries

### User Must Decide
- [List decisions requiring user approval]

### Agent May Decide (with Rationale)
- [List delegated decisions that need justification]

### Agent Must Do Autonomously
- [List routine tasks agent handles without asking]

## Evidence Base (External Sources)

**Evidence Sources**: [List where competency evidence came from]

**Verified Competencies**: See `docs/quality/maintainers/<username>.md` for detailed evidence

## Using This Profile

**Before making recommendations:**
1. Check expertise level for relevant domain
2. Adjust communication style (CSW format)
3. Determine authority level (decide vs. ask)

**During collaboration:**
- Defer on Expert areas (ask, don't tell)
- Collaborate on Advanced areas (propose, discuss)
- Lead on Intermediate areas (recommend, explain)
- Own Novice areas (execute, summarize)

---

**Last Updated**: YYYY-MM-DD
**Review Frequency**: Quarterly (during Management Review)
**Next Review**: YYYY-MM-DD OR XXX AI work-hours
```

### Section Descriptions

**Technical Expertise (4 levels):**
- **Expert**: Deep domain knowledge, designs frameworks, teaches others → Agent defers
- **Advanced**: Strong working knowledge, handles complex tasks independently → Collaborate
- **Intermediate**: Working knowledge, handles routine tasks independently → Agent leads with oversight
- **Novice**: Learning, needs guidance → Agent should lead

**Communication Preferences:**
- Completed Staff Work: Does user want solutions (Strong) or is it okay to bring problems (Weak)?
- Detail Level: How much explanation at each phase (planning/implementation/routine)?
- Escalation: When should agent ask vs. proceed?

**Authority Boundaries:**
- User Must Decide: Policy, legal, methodology, external communication
- Agent May Decide: Implementation within patterns, refactoring, testing strategies
- Agent Must Do: Formatting, linting, running tests, following procedures

**Evidence Base:**
- High-level summary of evidence sources (GitHub portfolio, resume, interview)
- Link to QMS profile for detailed evidence

**Using This Profile:**
- Practical guidance for AI agents on how to apply the profile
- Decision tree: Expertise level → Communication style → Authority level

---

## Schema 2: QMS Competency Profile

### File Location

`docs/quality/maintainers/<username>.md`

**Example**: `docs/quality/maintainers/stvhay.md`

### Header

```markdown
# Maintainer Competency Profile: <Full Name> (<username>)

**Role**: <Project role>
**Onboarding Date**: YYYY-MM-DD
**Last Reviewed**: YYYY-MM-DD
**Next Review**: YYYY-MM-DD (Annual)

---
```

### Content Structure

```markdown
## Competency Assessment

| Competency Area | Level | Evidence | Verification Method |
|----------------|-------|----------|---------------------|
| <Domain> | <Expert\|Advanced\|Intermediate\|Novice> | <Source of evidence> | <How verified> |

---

## Evidence of Competence

### External Portfolio Analysis

**GitHub Activity** (github.com/<username>):
- [Summary of repositories, languages, contribution patterns]

**Professional Experience**:
- [Summary from resume/CV]

**Education/Certifications**:
- [Relevant credentials]

### Self-Declared Competencies

**Background**:
- [From onboarding interview]

**Experience**:
- [Relevant professional experience]

**Training**:
- [Certifications, courses, self-study]

---

## Competency Gaps and Development Plan

**Identified Gaps**:
- [List any gaps discovered]

**Development Actions**:
- [Planned actions to address gaps]

---

## Communication and Collaboration Preferences

### Completed Staff Work
- **Preference**: [Strong | Moderate | Weak]
- **Application**: [What this means]

### Detail Level
- **Planning**: [Preference]
- **Implementation**: [Preference]
- **Routine**: [Preference]

### Escalation
- [When to ask vs. proceed]

---

## Authority and Decision Rights

### Requires User Approval
- [List]

### Delegated to AI Agents (with Rationale)
- [List]

### Agent Autonomous
- [List]

---

## Review History

| Date | Reviewer | Changes | Reason |
|------|----------|---------|--------|
| YYYY-MM-DD | <Reviewer> | <Summary> | <Trigger> |

---

## Integration with QMS

**Related Documents**:
- `.claude/agents/<username>.md` - AI agent reference version
- `COMPETENCY-MATRIX.md` - Overall competency framework
- `MANAGEMENT-REVIEW-TEMPLATE.md` - Quarterly review process

**Review Triggers**:
- **Scheduled**: Annual (YYYY-MM-DD)
- **Ad-hoc**: Competency gaps identified, role changes, QMS updates

---

**Approved By**: <Approver>
**Date**: YYYY-MM-DD
**Next Review**: YYYY-MM-DD
```

### Section Descriptions

**Competency Assessment Table:**
- Structured table for ISO 9001 compliance (Clause 7.2)
- Each competency area mapped to level with evidence and verification
- Evidence must be from external sources (other GitHub repos, resume, interview)

**Evidence of Competence:**
- External Portfolio: GitHub activity outside this AI-assisted project
- Professional Experience: Resume/CV highlights
- Self-Declared: Interview responses, background statements

**Competency Gaps:**
- Identified during onboarding or reviews
- Development plan to address gaps
- Tracked through to closure

**Communication/Authority:**
- Same information as agent reference (keep synchronized)
- Formal documentation for QMS purposes

**Review History:**
- Audit trail of profile changes
- Date, reviewer, summary, and reason for each change

**QMS Integration:**
- Cross-references to related QMS documents
- Review triggers (scheduled and ad-hoc)

---

## Integration with COMPETENCY-MATRIX.md

### Location in Document

Add new section **after** "AI Agent Competencies" section:

```markdown
## Maintainer Profiles

### Purpose

Individual maintainer profiles document:
- Technical competency (expertise domains and levels)
- Communication preferences (Completed Staff Work, detail level, escalation)
- Authority boundaries (approval requirements, delegation, autonomy)
- Evidence base (external GitHub, resume, self-assessment)

### Profile Locations

| Maintainer | Role | Agent Reference | QMS Profile | Status |
|------------|------|-----------------|-------------|--------|
| <username> | <Role> | [.claude/agents/<username>.md](../../.claude/agents/<username>.md) | [maintainers/<username>.md](maintainers/<username>.md) | Active |

### Profile Format

**Dual Profile System**:
1. **Agent Reference** (`.claude/agents/<username>.md`)
   - Purpose: AI agent collaboration context
   - Content: Expertise levels, when to defer/challenge, communication preferences
   - Usage: Read by main agent for user-specific guidance

2. **QMS Profile** (`docs/quality/maintainers/<username>.md`)
   - Purpose: ISO 9001 competency evidence
   - Content: Competency assessment table, evidence, development plan
   - Usage: Management review, competency verification

### Review Process

**Quarterly Review** (Management Review Section 6.1.1):
- Profile accuracy check
- Collaboration effectiveness assessment
- Competency gap identification

**Annual Review** (with Competency Matrix):
- Deep competency assessment
- Evidence refresh (external GitHub, resume updates)
- Development plan update

**Ad-hoc Updates**:
- New expertise demonstrated
- Role changes
- Authority boundary adjustments
- Communication preference changes

### Onboarding

New maintainers follow [ONBOARDING-PROCESS.md](ONBOARDING-PROCESS.md) to create profiles.

**Outcome**: Maintainer ready for AI agent collaboration with documented competency profile.
```

### Integration Points

- **After Section**: AI Agent Competencies (existing)
- **Table Format**: Matches existing competency matrix style
- **Links**: Both agent reference AND QMS profile
- **Cross-Reference**: ONBOARDING-PROCESS.md for creating new profiles

---

## Integration with MANAGEMENT-REVIEW-TEMPLATE.md

### Location in Document

Add new subsection under **Section 6: Resources** as **6.1.1**:

```markdown
### 6.1.1 Maintainer Competency Review

**Current Maintainers:**
- [List: username, role, profile location]

**Profile Accuracy:**
- [ ] Profiles reflect current expertise and responsibilities
- [ ] Evidence up-to-date (recent GitHub activity, resume changes)
- [ ] Communication preferences still accurate

**Collaboration Effectiveness:**
- [ ] AI agents using profiles effectively?
- [ ] Authority boundaries working as expected?
- [ ] Escalation patterns appropriate?
- [ ] Defer/challenge behavior correct?

**Competency Gaps Identified:**
[List any gaps discovered this quarter]

**Profile Updates Needed:**
- [ ] Technical expertise changes (new skills demonstrated)
- [ ] Communication preference changes
- [ ] Authority boundary adjustments
- [ ] Evidence refresh needed

**Actions Required:**
- [ ] Update `.claude/agents/<username>.md` (if changes needed)
- [ ] Update `docs/quality/maintainers/<username>.md` (if changes needed)
- [ ] Schedule competency development (if gaps identified)

**Consistency Check:**
- [ ] Agent reference and QMS profile synchronized
- [ ] Both files updated together (if changes made)

**Next Deep Review**: [Annual competency matrix review date - e.g., 2026-12-12]

---
```

### Integration Points

- **Parent Section**: 6.1 Human Resources (existing)
- **Subsection**: 6.1.1 (new)
- **Frequency**: Quarterly (every 3 months OR 455 AI work-hours)
- **Review Questions**: Actionable (not just "did you review?")
- **Outputs**: Specific actions (update profiles, address gaps)
- **Sync Check**: Ensures dual profiles stay consistent

---

## Competency Level Definitions

Use these standard definitions across both profile types:

| Level | Definition | Characteristics | Agent Behavior |
|-------|-----------|-----------------|----------------|
| **Expert** | Deep domain knowledge, can teach others, designs frameworks | - Creates new approaches<br>- Recognized authority<br>- Handles novel problems<br>- Designs architecture | **Defer**: Ask user, don't tell<br>Listen to user direction |
| **Advanced** | Strong working knowledge, handles complex tasks independently | - Solves complex problems<br>- Needs minimal guidance<br>- Contributes to design<br>- Mentors others | **Collaborate**: Propose solutions, discuss trade-offs<br>User decides final approach |
| **Intermediate** | Working knowledge, handles routine tasks independently | - Solves routine problems<br>- Needs guidance on complex tasks<br>- Follows established patterns<br>- Learning actively | **Lead with oversight**: Recommend approach with explanation<br>User can override |
| **Novice** | Learning, needs guidance and supervision | - Requires instruction<br>- Learning fundamentals<br>- Needs close oversight<br>- Developing skills | **Agent leads**: Execute and explain<br>Teach user as needed |

---

## Example Domains

Common competency domains for this project:

**Technical Domains:**
- Reverse Engineering
- GPL Compliance Law
- Python Development
- Bash Scripting
- Git/Version Control
- Firmware Analysis Tools (binwalk, strings, dtc, etc.)
- Documentation Writing
- Testing and Quality Assurance

**Process Domains:**
- Quality Management (ISO 9001)
- Project Architecture
- AI Agent Orchestration
- Black Box Methodology
- Risk Management

**Note**: Tailor domains to actual maintainer expertise, don't force-fit all domains.

---

## Evidence Requirements

### External Sources Only

For this AI-assisted project, maintainer competency **MUST be evidenced from external sources**:

**Acceptable Evidence:**
1. **Other GitHub repositories** (NOT this glinet-comet-reverse-gpl repo)
   - Commit history
   - Code quality
   - Project complexity
   - Languages used

2. **Resume/CV** (stevenhay.com/cv or provided document)
   - Professional experience
   - Education and certifications
   - Technical skills
   - Project leadership

3. **Self-Assessment Interview**
   - User's own expertise declarations
   - Background and experience
   - Competency self-ratings

**Unacceptable Evidence:**
- This repository's commit history (AI-assisted work)
- This repository's code (authored with Claude Code)
- This repository's documentation (co-created with AI)

**Why?** Cannot verify maintainer competency based on work where AI was the primary contributor.

---

## Update Workflow

### When to Update Profiles

**Quarterly** (Management Review Section 6.1.1):
- Check for accuracy
- Identify new expertise demonstrated externally
- Update communication/authority if changed

**Annual** (Competency Matrix review):
- Full evidence refresh (GitHub, resume)
- Deep competency reassessment
- Development plan review

**Ad-hoc**:
- Role changes (e.g., contributor → maintainer)
- Major new expertise (e.g., learns Rust, completes certification)
- Authority boundary needs adjustment
- Communication preferences change

### How to Update

1. **Identify change needed** (quarterly review, ad-hoc trigger)
2. **Update BOTH profiles**:
   - `.claude/agents/<username>.md` - Update relevant section
   - `docs/quality/maintainers/<username>.md` - Update corresponding section + review history table
3. **Commit together** with message explaining change:
   ```
   chore: Update stvhay profile - new expertise in X

   - Added X to Advanced competencies (evidence: github.com/stvhay/project-x)
   - Updated communication preferences (now prefers CSW for all interactions)
   - Both agent reference and QMS profile updated

   Trigger: Quarterly Management Review 2025-12-12
   ```
4. **Verify sync** in next Management Review

---

## Validation Checklist

Use this checklist when creating or reviewing profiles:

### Agent Reference File (`.claude/agents/<username>.md`)

- [ ] YAML frontmatter complete (name, description, type, user, last_updated)
- [ ] `type: user-profile` set (distinguishes from spawnable agents)
- [ ] Description clarifies "Reference only - not spawnable"
- [ ] Technical expertise organized by 4 levels (Expert/Advanced/Intermediate/Novice)
- [ ] Each level includes "when to defer/collaborate/challenge/lead" guidance
- [ ] Communication preferences documented (CSW, detail level, escalation)
- [ ] Authority boundaries clear (must decide, may decide, autonomous)
- [ ] Evidence base summarized with link to QMS profile
- [ ] "Using This Profile" section provides practical agent guidance

### QMS Competency Profile (`docs/quality/maintainers/<username>.md`)

- [ ] Header complete (role, onboarding date, last reviewed, next review)
- [ ] Competency assessment table with all domains, levels, evidence, verification
- [ ] Evidence from EXTERNAL sources only (other GitHub, resume, interview)
- [ ] Self-declared competencies documented
- [ ] Competency gaps and development plan present
- [ ] Communication/authority sections match agent reference
- [ ] Review history table started (initial entry)
- [ ] QMS integration section with cross-references
- [ ] Approved by and next review date set

### Consistency Between Files

- [ ] Expertise levels identical in both files
- [ ] Communication preferences identical
- [ ] Authority boundaries identical
- [ ] Evidence sources consistent (external focus)
- [ ] Last updated dates within same day

### Integration

- [ ] COMPETENCY-MATRIX.md updated (maintainer profiles table)
- [ ] MANAGEMENT-REVIEW-TEMPLATE.md Section 6.1.1 ready to review this profile
- [ ] Profile files in version control (committed)

---

## Summary

This schema provides:

1. **Dual profiles** for different audiences (AI agents vs. QMS reviewers)
2. **Standard structure** for all maintainer profiles
3. **Evidence-based** competency assessment (external sources only)
4. **Clear integration** with existing QMS (Competency Matrix, Management Review)
5. **Expertise-weighted collaboration** (defer on Expert, collaborate on Advanced, etc.)
6. **Quarterly sync mechanism** (Management Review Section 6.1.1)

**Next Steps:**
- Use this schema in Issue #66 (ONBOARDING-PROCESS.md)
- Validate schema in Issue #67 (stvhay onboarding)
- Update as needed based on validation findings
