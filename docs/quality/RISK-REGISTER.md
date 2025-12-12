# Risk Register

**Project:** GL.iNet Comet GPL Compliance Analysis
**Last Updated:** 2025-12-12
**Review Frequency:** Quarterly

## Risk Assessment Matrix

| Likelihood | Impact | Risk Level |
|------------|--------|------------|
| High | High | **Critical** |
| High | Medium | **High** |
| Medium | High | **High** |
| High | Low | **Medium** |
| Medium | Medium | **Medium** |
| Low | High | **Medium** |
| Medium | Low | **Low** |
| Low | Medium | **Low** |
| Low | Low | **Low** |

## Active Risks

### R1: Legal/GPL Compliance Risk
**Category:** Legal
**Likelihood:** Medium
**Impact:** High
**Risk Level:** High

**Description:**
GL.iNet may not have released complete GPL source code for components in the Comet (RM1) firmware, potentially violating GPL licensing obligations.

**Current Mitigations:**
- Black box reverse engineering methodology ensures all findings are independently derived
- Complete traceability system links all findings to automated scripts
- Source metadata documents exact extraction methods
- All analysis scripts are open source and reproducible

**Additional Actions Required:**
- Document methodology in legal-defensible format (covered in Phase 1)
- Consider legal review before public disclosure
- Maintain clear chain of evidence in analysis results

**Owner:** Project Lead
**Review Date:** 2025-03-12

---

### R2: False Positive in Analysis
**Category:** Technical
**Likelihood:** Medium
**Impact:** Medium
**Risk Level:** Medium

**Description:**
Analysis scripts may incorrectly identify proprietary code as GPL-licensed or vice versa, leading to incorrect conclusions.

**Current Mitigations:**
- 619 automated tests with 60%+ coverage requirement enforced by CI
- Code review agent (Opus) performs thorough analysis of significant code changes
- Test-driven development ensures script behavior is verified
- Multiple verification methods (strings, file signatures, etc.)

**Additional Actions Required:**
- Add more integration tests for full analysis pipelines
- Implement peer review for critical findings
- Document confidence levels in findings

**Owner:** Development Team
**Review Date:** 2025-03-12

---

### R3: Dependency Supply Chain Risk
**Category:** Technical
**Likelihood:** Low
**Impact:** Medium
**Risk Level:** Low

**Description:**
Analysis tools (binwalk, strings, etc.) or Python dependencies could have vulnerabilities or unexpected behavior affecting analysis results.

**Current Mitigations:**
- Nix development environment pins all dependencies with cryptographic hashes
- All tools are standard open-source utilities with widespread use
- Reproducible builds via nix flake
- CI runs on trusted GitHub Actions infrastructure

**Additional Actions Required:**
- Document tool versions in results metadata (covered in Phase 3, R9)
- Set up dependency vulnerability scanning
- Periodically verify tool behavior with known test cases

**Owner:** Development Team
**Review Date:** 2025-06-12

---

### R4: Data Loss or Corruption
**Category:** Operational
**Likelihood:** Low
**Impact:** High
**Risk Level:** Medium

**Description:**
Loss of analysis results, scripts, or documentation could require significant rework and delay project completion.

**Current Mitigations:**
- All code and documentation in Git version control
- Repository backed up on GitHub (remote origin)
- Results directory committed to repository
- CI/CD pipeline can regenerate results from scripts

**Additional Actions Required:**
- Implement regular backups of repository
- Document disaster recovery procedures
- Consider additional backup locations

**Owner:** Project Lead
**Review Date:** 2025-06-12

---

### R5: Firmware Download Authenticity
**Category:** Technical
**Likelihood:** Low
**Impact:** High
**Risk Level:** Medium

**Description:**
Downloaded firmware may not be authentic GL.iNet release, leading to analysis of incorrect or tampered files.

**Current Mitigations:**
- Firmware downloaded from official GL.iNet CDN (fw.gl-inet.com)
- Firmware hash/checksum recorded in documentation
- Reproducible download process via scripts

**Additional Actions Required:**
- Verify firmware signature if GL.iNet provides one
- Document chain of custody for firmware files
- Consider checksums in analysis output

**Owner:** Development Team
**Review Date:** 2025-06-12

---

### R6: Insufficient Documentation
**Category:** Quality
**Likelihood:** Medium
**Impact:** Medium
**Risk Level:** Medium

**Description:**
Incomplete or unclear documentation could prevent others from understanding or reproducing analysis, reducing project credibility.

**Current Mitigations:**
- Jinja templates with automatic source citations
- CLAUDE.md documents comprehensive methodology
- All scripts include usage documentation
- Issue templates enforce documentation standards
- Wiki generation from templates

**Additional Actions Required:**
- Complete ISO 9001 documentation (in progress)
- Add more inline comments for complex algorithms
- Create user guide for running analysis

**Owner:** Development Team
**Review Date:** 2025-03-12

---

### R7: Resource/Time Constraints
**Category:** Operational
**Likelihood:** Medium
**Impact:** Low
**Risk Level:** Low

**Description:**
Limited human resources (2-person team) could delay analysis completion or quality improvements.

**Current Mitigations:**
- AI agents handle routine development tasks
- Model-specific agents optimize for cost and capability
- Automated testing reduces manual QA time
- CI/CD automates quality checks
- Efficient workflows documented in CLAUDE.md

**Additional Actions Required:**
- Prioritize critical path items (covered in issue templates)
- Use planning agent for complex work breakdown
- Consider Phase 3 competency management for agent efficiency

**Owner:** Project Lead
**Review Date:** 2025-03-12

---

## Risk Review Process

Risks are reviewed quarterly during Management Review meetings (when implemented in Phase 2, R6).

**Review Checklist:**
- [ ] Review each active risk for status changes
- [ ] Assess effectiveness of mitigations
- [ ] Identify new risks
- [ ] Update likelihood/impact assessments
- [ ] Assign owners and due dates
- [ ] Close resolved risks (moved to Closed Risks section)

## Closed Risks

*(No closed risks yet)*

---

## Risk Escalation Criteria

**Immediate Escalation Required:**
- Any risk becomes Critical (High likelihood + High impact)
- Legal risk becomes actionable (e.g., cease & desist letter)
- Data loss occurs
- Security breach of repository or systems

**Escalation Contact:** Project Lead

---

*This risk register is a living document and should be updated as risks evolve.*
