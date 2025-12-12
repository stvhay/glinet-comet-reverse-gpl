# Quality Management System Scope

**Organization:** GL.iNet Comet GPL Compliance Analysis Project
**Version:** 1.1
**Effective Date:** 2025-12-12
**Last Updated:** 2025-12-12
**Review Frequency:** Annually OR 1,820 AI work-hours, whichever comes first

---

## 1. Purpose

This document defines the scope and boundaries of the Quality Management System (QMS) for the GL.iNet Comet (RM1) firmware reverse engineering and GPL compliance analysis project.

---

## 2. Organizational Context

### 2.1 Project Overview

The GL.iNet Comet GPL Compliance Analysis Project is a **black box reverse engineering** effort to identify GPL-licensed components in the GL.iNet Comet (RM1) KVM firmware and facilitate GPL compliance.

**Key Characteristics:**
- **Team Size:** 2-person team (1 human lead + AI agents)
- **Methodology:** Automated analysis scripts with reproducible results
- **Deliverables:** Analysis scripts, findings documentation, wiki pages
- **Stakeholders:**
  - Primary: Project lead (human developer)
  - Secondary: Open source community, GPL enforcement organizations
  - Tertiary: GL.iNet (as firmware vendor subject to analysis)

### 2.2 Relevant Interested Parties

| Party | Interest | Requirements/Expectations |
|-------|----------|--------------------------|
| Project Lead | Accurate GPL compliance findings | Legally defensible methodology, reproducible results |
| Open Source Community | Transparency, verifiability | Open source scripts, documented methodology |
| GPL Enforcement Organizations | Evidence for potential enforcement | Rigorous analysis, clear evidence chain |
| Academic/Research Community | Methodology reference | Documented best practices, reproducible approach |

### 2.3 AI Work-Hour Equivalence Methodology

#### Context: AI Work Compression

Traditional QMS frameworks assume human work patterns (35-40 hour work weeks, calendar-based review schedules). This project uses AI agents that can compress months of human-equivalent work into days.

**Problem:** Calendar-based triggers (quarterly, annually) may be too slow or too fast depending on actual work volume.

**Solution:** **Dual-trigger system** - Reviews trigger on **calendar date OR accumulated work-hours**, whichever comes first.

#### Measuring AI Work-Hours

**Primary Method: Session-Based Tracking**

AI work-hours are measured using **active session time** where AI agents are performing productive work:

**What Counts as Work-Hours:**
- ✅ Active Claude Code sessions (coding, analysis, documentation)
- ✅ Agent task execution time (exploration, planning, code review)
- ✅ Interactive problem-solving sessions
- ✅ Quality management activities (reviews, audits, documentation)

**What Doesn't Count:**
- ❌ User reading/thinking time between sessions
- ❌ CI/CD automated runs (not AI work, machine work)
- ❌ Idle time in open sessions
- ❌ Time waiting for user responses

**Tracking Method:**

Work-hours tracked in management reviews using session logs:

```bash
# Example: Calculate AI work-hours between reviews
# Method 1: Manual session tracking
# During each session, note start/end times in management review

# Method 2: Git-based estimation (fallback)
# Count commits with AI co-authorship, estimate 0.5-2 hours per commit
git log --since="YYYY-MM-DD" --grep="Claude" --oneline | wc -l
```

**Recording:**
- Each management review records accumulated AI work-hours since last review
- Tracked in management review template Section 2: "AI Work-Hours Since Last Review"

#### Conversion Factor: AI Hours to Human Hours

**Conservative 1:1 Ratio**

For QMS trigger purposes, **1 AI hour = 1 human hour** (35-hour work week basis).

**Rationale:**
- **Conservative approach:** Ensures adequate review frequency
- **Task-independent:** Avoids complex per-task calibration
- **Auditable:** Simple to track and verify
- **Adjustable:** Can be refined based on actual experience

**Example Calculations:**

| Review Frequency | Calendar Period | Human Work-Hours | AI Work-Hour Trigger |
|------------------|----------------|------------------|---------------------|
| Quarterly | 13 weeks | 455 hours (13×35) | 455 AI session hours |
| Semi-annually | 26 weeks | 910 hours (26×35) | 910 AI session hours |
| Annually | 52 weeks | 1,820 hours (52×35) | 1,820 AI session hours |

**Trigger Example:**
- Quarterly review scheduled for April 1, 2026
- If 455 AI work-hours accumulated by March 1, 2026 → trigger review early
- Otherwise, review triggers on April 1 as scheduled

#### Integration with QMS Processes

**Dual-Trigger System:**

All periodic QMS activities use dual triggers:

**Format:**
> "This [activity] shall occur **quarterly** (every 3 months) **OR when 455 cumulative AI work-hours are reached**, whichever comes first."

**Applies to:**
- Management Reviews (Quarterly: 455 hours)
- Internal Audits (Semi-annually: 910 hours)
- Quality Objectives Review (Quarterly: 455 hours)
- Risk Register Review (Quarterly: 455 hours)
- Annual document reviews (Annually: 1,820 hours)

**Reset on Trigger:**
- When review occurs, reset work-hour counter to zero
- Next review: Calendar date OR work-hours from reset point

#### Work-Hour Tracking Procedure

**During Each Management Review:**

1. **Calculate AI Work-Hours:**
   - Review session logs since last management review
   - Sum productive AI session time (hours)
   - Record in management review Section 2

2. **Evaluate Trigger Status:**
   - Compare accumulated hours to threshold
   - Check calendar date to next scheduled review
   - Determine if early review needed

3. **Reset Counter:**
   - After review completes, reset work-hour counter to zero
   - Document reset date in management review

4. **Plan Next Review:**
   - Set calendar date (e.g., +3 months for quarterly)
   - Set work-hour threshold (e.g., 455 hours for quarterly)
   - Document both triggers in management review outputs

**Example Management Review Entry:**

```markdown
## 2. AI Work-Hours Since Last Review

**Period:** 2025-12-12 to 2026-03-15
**Accumulated AI Work-Hours:** 287 hours
**Method:** Session tracking via Claude Code logs

**Trigger Evaluation:**
- Calendar trigger: March 15, 2026 (reached)
- Work-hour trigger: 455 hours (not reached)
- **Triggered by:** Calendar date

**Work-Hour Counter Reset:** 2026-03-15
**Next Review Triggers:**
- Calendar: June 15, 2026 (3 months)
- Work-hours: 455 hours from reset
```

#### Benefits of Dual-Trigger System

**Advantages:**
1. **Responsive to actual work volume:** High-intensity periods trigger earlier reviews
2. **Maintains minimum review frequency:** Calendar trigger ensures reviews don't skip too long
3. **Prevents review overload:** Calendar trigger prevents excessive reviews during slow periods
4. **Auditable:** Clear tracking methodology with objective evidence
5. **Fair comparison:** Enables meaningful comparison to traditional organizations

**Quality Objective:**
> Demonstrate QMS responsiveness to actual work patterns, not just arbitrary calendar dates

---

## 3. QMS Scope

### 3.1 Products and Services Covered

**In Scope:**

1. **Analysis Scripts**
   - Firmware extraction scripts (binwalk, extraction utilities)
   - Binary analysis scripts (strings, file identification, signature detection)
   - GPL component identification scripts
   - Documentation generation scripts (Jinja templates, rendering)
   - Test suites for all analysis scripts

2. **Documentation**
   - Analysis findings (TOML/JSON output files)
   - Wiki pages (Jinja-templated markdown)
   - Methodology documentation (CLAUDE.md, README)
   - Quality management documentation (this QMS)

3. **Supporting Infrastructure**
   - CI/CD pipeline (GitHub Actions)
   - Development environment (nix flake)
   - Version control practices (Git workflows)
   - Issue tracking and planning (GitHub Issues)

**Activities:**
- Requirements analysis (identifying what to analyze in firmware)
- Script development (Python, Bash)
- Testing and validation (pytest, integration tests)
- Documentation generation (Jinja templates → wiki)
- Quality assurance (code review, CI checks)
- Continuous improvement (refactoring, process optimization)

### 3.2 Processes Covered

The QMS applies to:

1. **Analysis Script Development Process**
   - Requirements → Design → Implementation → Testing → Review → Documentation

2. **Documentation Generation Process**
   - Analysis execution → TOML/JSON output → Template rendering → Wiki publication

3. **Quality Assurance Process**
   - Pre-commit checks → CI/CD validation → Code review → Acceptance

4. **Risk Management Process**
   - Risk identification → Assessment → Mitigation → Monitoring

5. **Management Review Process**
   - Quarterly performance review → Corrective actions → Continuous improvement

### 3.3 Physical and Organizational Boundaries

**Physical Scope:**
- Development occurs on local workstations (macOS, Linux)
- Repository hosted on GitHub (github.com/stvhay/glinet-comet-reverse-gpl)
- CI/CD runs on GitHub Actions infrastructure
- No physical manufacturing or hardware development

**Organizational Scope:**
- Single project within a personal/research context
- Not part of a larger organizational QMS
- Standalone quality management for this specific analysis effort

**Temporal Scope:**
- Ongoing project (initiated 2024, active development)
- QMS effective from 2025-12-12
- Annual QMS review cycle

---

## 4. QMS Exclusions

The following ISO 9001:2015 requirements are **not applicable** to this project:

### 4.1 Clause 8.2.2 - Determination of Requirements Related to Products and Services

**Rationale:** This project does not have external customers with contractual requirements. The "customer" is the project lead, and requirements are self-determined based on reverse engineering objectives. Analysis is performed on publicly available firmware without customer-supplied specifications.

**Alternative Approach:** Requirements are documented in issue templates and CLAUDE.md as analysis objectives.

### 4.2 Clause 8.2.3 - Review of Requirements Related to Products and Services

**Rationale:** No customer contracts or orders to review. Requirements are internally defined and validated through issue acceptance criteria.

**Alternative Approach:** Issue templates enforce requirements validation before work begins.

### 4.3 Clause 8.3.3 - Design and Development Inputs (partial)

**Rationale:** While we document design inputs for scripts, we do not have statutory/regulatory requirements typical of safety-critical or medical products.

**Alternative Approach:** Black box methodology requirements serve as design inputs. Legal requirements (GPL compliance) are factored into methodology, not product design.

### 4.4 Clause 8.4.1-8.4.3 - Control of Externally Provided Processes, Products and Services

**Rationale:** The project uses standard open-source tools (binwalk, strings, etc.) and development utilities (Git, nix), but these are not "suppliers" in the traditional sense. Firmware analyzed is publicly available, not purchased.

**Alternative Approach:**
- Tool versions controlled via nix flake (cryptographic hashes)
- Firmware provenance documented (download URL, checksums)
- Dependency vulnerability scanning (future enhancement, R9)

### 4.5 Clause 8.5.1(g) - Production and Service Provision - Infrastructure for Customer Property

**Rationale:** No customer-supplied property or infrastructure. Firmware is publicly downloaded.

### 4.6 Clause 8.5.2 - Identification and Traceability (partial)

**Rationale:** While we maintain excellent traceability for analysis findings (source metadata), we do not have serialized products or batch tracking.

**Alternative Approach:** Git commits provide version traceability. Results directory includes firmware hashes and script versions.

### 4.7 Clause 8.5.3 - Property Belonging to Customers or External Providers

**Rationale:** No customer property handled. Firmware is publicly available.

### 4.8 Clause 8.5.5 - Post-Delivery Activities

**Rationale:** Analysis scripts and documentation are published but do not require traditional post-delivery support (warranties, maintenance contracts, recalls).

**Alternative Approach:**
- Scripts maintained in GitHub repository
- Issues tracked for bugs/improvements
- Community can report problems via GitHub Issues

### 4.9 Clause 8.6 - Release of Products and Services (partial)

**Rationale:** While we have quality gates (CI/CD), we do not have customer acceptance or formal release approvals typical of commercial products.

**Alternative Approach:** CI/CD gates serve as release criteria. Merging to main branch = "release" for continuous delivery.

### 4.10 Manufacturing-Specific Requirements

**Not Applicable:**
- Physical product manufacturing
- Production line controls
- Equipment calibration
- Material handling
- Inventory management
- Packaging and labeling
- Shipping and logistics

**Rationale:** This is software/knowledge work with no physical manufacturing.

---

## 5. QMS Boundaries

### 5.1 What is IN Scope

✅ **Development Activities:**
- Writing and maintaining analysis scripts
- Developing test suites
- Creating and updating documentation
- Managing version control
- Operating CI/CD pipeline

✅ **Quality Activities:**
- Code review (human + AI agents)
- Automated testing
- Linting and formatting checks
- Risk management
- Management reviews
- Corrective actions

✅ **Analysis Activities:**
- Firmware extraction and analysis
- GPL component identification
- Documentation generation
- Results validation

### 5.2 What is OUT of Scope

❌ **Not Included:**
- Firmware development or modification (we analyze, not create firmware)
- Hardware manufacturing or testing
- Customer support or SLA commitments
- Commercial sales or contracts
- Legal services (GPL enforcement is separate from analysis)
- Security vulnerability research (focus is GPL compliance, not security)

---

## 6. Applicability Justification

### 6.1 Why ISO 9001:2015?

ISO 9001:2015 is applicable to this project because:

1. **Customer Focus (Clause 5.1.2):** Project lead defines requirements; community expects rigorous analysis
2. **Process Approach (Clause 4.4):** Defined workflows for script development, testing, documentation
3. **Evidence-Based Decision Making (Clause 7.1.5):** All findings must be backed by script output
4. **Continuous Improvement (Clause 10):** Regular refactoring and process optimization
5. **Risk Management (Clause 6.1):** Legal, technical, and operational risks are managed
6. **Competence (Clause 7.2):** AI agent selection based on capability (model competency)

### 6.2 Benefits of QMS

**For this project specifically:**

1. **Legal Defensibility:** Documented methodology supports potential GPL enforcement
2. **Credibility:** ISO-aligned QMS demonstrates rigor to community and stakeholders
3. **Reproducibility:** Structured processes ensure analysis can be independently verified
4. **Risk Awareness:** Systematic risk management for legal/compliance risks
5. **Continuous Improvement:** Framework for regular quality enhancements
6. **Efficiency:** Documented processes reduce rework and errors

---

## 7. QMS Structure

### 7.1 Documented Information

**Tier 1: Policy-Level**
- Quality Policy (QUALITY-POLICY.md)
- QMS Scope (this document)

**Tier 2: Process-Level**
- Quality Objectives (QUALITY-OBJECTIVES.md)
- Risk Register (RISK-REGISTER.md)
- Procedures (PROCEDURES.md) - Phase 2
- Management Review Template (MANAGEMENT-REVIEW-TEMPLATE.md) - Phase 2

**Tier 3: Work Instructions**
- CLAUDE.md (methodology and workflow guidance)
- Issue templates (.github/ISSUE_TEMPLATE/)
- README.md (getting started, tools)

**Tier 4: Records**
- Git commit history (evidence of changes)
- Issue tracker (requirements, bugs, improvements)
- CI/CD logs (test results, quality checks)
- Management review records (when implemented)

### 7.2 Interaction with Other Standards/Systems

This QMS is:
- **Standalone** - Not part of a larger organizational QMS
- **Self-contained** - All requirements defined within project scope
- **Lightweight** - Optimized for 2-person team with AI assistance

Future integration opportunities:
- ISO/IEC 27001 (Information Security) - if project grows
- ISO/IEC 17025 (Testing Laboratories) - if formal accreditation desired

---

## 8. Maintenance and Review

### 8.1 Scope Review Triggers

This QMS Scope shall be reviewed when:

1. **Scheduled:** Annually (next calendar review: 2026-12-12) OR when 1,820 cumulative AI work-hours are reached, whichever comes first
2. **Project Changes:**
   - Significant expansion (e.g., adding commercial services)
   - New stakeholders or interested parties
   - Change in legal/regulatory context
   - Major methodology shifts
3. **QMS Changes:**
   - New processes added or removed
   - Exclusions no longer applicable
   - Boundary changes

### 8.2 Approval and Authorization

**Approved By:** Project Lead
**Date:** 2025-12-12
**Next Review:** 2026-12-12

---

## 9. References

- ISO 9001:2015 - Quality Management Systems - Requirements
- ISO/IEC/IEEE 90003:2018 - Software Engineering - Guidelines for Application of ISO 9001:2015 to Computer Software
- CLAUDE.md - Project methodology and practices
- docs/reports/iso-9001-gap-analysis-2025-12-12.md - Gap analysis report

---

*This document defines the boundaries of our QMS. All personnel (human and AI agents) working on this project shall operate within this scope.*
