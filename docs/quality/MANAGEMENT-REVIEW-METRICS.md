# Management Review Metrics

**Purpose:** Track key quality metrics for quarterly management review per ISO 9001:2015
**Review Frequency:** Quarterly
**Owner:** Project Lead

---

## 6.1 Work-Hour and Session Metrics

### 6.1.1 Session Count and Duration

**Metric:** Number of work sessions and total hours per quarter

**Q4 2025:** [To be calculated in Q1 2026 review]
**Q1 2026:** [To be calculated in Q2 2026 review]

**Data Source:** Git commit timestamps, scratchpad session summaries

---

### 6.1.2 Productivity Indicators

**Metric:** Issues closed per quarter, commits per session

**Q4 2025:** [To be calculated in Q1 2026 review]
**Q1 2026:** [To be calculated in Q2 2026 review]

**Data Source:** GitHub issues, git log

---

### 6.1.3 Scratchpad Currency (P5 Compliance)

**Metric:** Percentage of active work time with scratchpad <15 minutes stale

**Target:** >95%

**Q4 2025:** [To be calculated in Q1 2026 review]
**Q1 2026:** [To be calculated in Q2 2026 review]

**Measurement Method:**
1. Identify all work sessions from git commit activity
2. For each session, extract scratchpad modification timestamps
3. For each commit, check if scratchpad was updated within 15 min prior
4. Formula: `(Commits with fresh scratchpad / Total commits) × 100`

**Alternative Calculation:**
- Analyze scratchpad cache update frequency
- Calculate % of time between updates that is <15 min
- Formula: `(Time periods <15 min / Total active time) × 100`

**Non-Conformances This Quarter:**
- **NCR-2025-12-13-001:** Scratchpad 36 min stale (repeat occurrence)
  - Root cause: Process ambiguity + manual process failure
  - Corrective actions: 5 CAs implemented (blocking hook, cache system, procedure updates)
  - Verification: 30-day monitoring period (Jan 2026)

**Trend Analysis:**
- Q4 2025: Baseline to be established
- Target: Consistent >95% in subsequent quarters
- Improvement actions if <95%: Review CA effectiveness, consider additional automation

**Review Actions:**
- If <95%: Create corrective action issue
- If 95-98%: Monitor for trends
- If >98%: Maintain current processes

**Related Documents:**
- P5 Procedure: PROCEDURES.md Section 5.5
- NCR-2025-12-13-001: Scratchpad staleness non-conformance
- RCA-2025-12-13-scratchpad-staleness.md

---

## 6.2 Quality Metrics

### 6.2.1 Test Coverage

**Metric:** Code coverage percentage

**Target:** ≥60%

**Q4 2025:** [Current: ~65% per pytest-cov]
**Q1 2026:** [To be measured]

**Data Source:** pytest --cov output

---

### 6.2.2 Test Pass Rate

**Metric:** Percentage of pytest runs that pass all tests

**Target:** 100% (all commits must pass)

**Q4 2025:** [To be calculated from CI logs]
**Q1 2026:** [To be calculated]

**Data Source:** Pre-push hook logs, GitHub Actions results

---

### 6.2.3 Linting Compliance

**Metric:** Ruff linting errors per 1000 lines of code

**Target:** 0 errors (enforced by pre-push hook)

**Q4 2025:** 0 (enforced)
**Q1 2026:** 0 (enforced)

**Data Source:** Ruff check output

---

## 6.3 Process Compliance Metrics

### 6.3.1 Non-Conformance Rate

**Metric:** Number of NCRs opened per quarter

**Target:** Decreasing trend

**Q4 2025:** 1 NCR (NCR-2025-12-13-001)
**Q1 2026:** [To be counted]

**Breakdown by Category:**
- Process non-conformance: 1
- Code quality: 0
- Documentation: 0

---

### 6.3.2 Corrective Action Effectiveness

**Metric:** Percentage of CAs that prevent recurrence

**Target:** >90% effectiveness

**Q4 2025:** [To be measured after 30-day verification period]
- NCR-2025-12-13-001: 5 CAs implemented, verification in progress

**Q1 2026:** [To be measured]

**Measurement:** Track if same root cause reappears within 90 days

---

## 6.4 Continuous Improvement Metrics

### 6.4.1 Code Reduction (Refactoring)

**Metric:** Net lines of code removed via refactoring

**Target:** Positive (more removed than added)

**Q4 2025:** +255 lines removed
- Issue #31: -140 lines (scripts) + -115 lines (tests)

**Q1 2026:** [To be calculated]

**Data Source:** Git diff stats for refactoring commits

---

### 6.4.2 Automation Improvements

**Metric:** Number of manual processes automated

**Q4 2025:** 2 automations
- Pre-commit hook (P5 enforcement)
- Post-commit hook (scratchpad auto-update)

**Q1 2026:** [To be counted]

**Data Source:** Git hooks, CI/CD enhancements

---

## Review Process

**Quarterly Management Review includes:**
1. Review all metrics above
2. Identify trends (improving, stable, degrading)
3. Analyze non-conformances and CA effectiveness
4. Create improvement actions for metrics below target
5. Update quality objectives if needed
6. Document review in wiki/management-review/YYYY-QN.md

**Next Review:** Q1 2026 (scheduled for end of Q1)

---

*This document implements CA #4 from NCR-2025-12-13-001. Scratchpad currency metric added to support P5 compliance monitoring.*
