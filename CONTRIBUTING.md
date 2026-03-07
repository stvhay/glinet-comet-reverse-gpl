# Contributing to GL.iNet Comet GPL Compliance Analysis

This project uses [Claude Code](https://docs.anthropic.com/en/docs/claude-code) with plugins from `github:stvhay/my-claude-plugins` to maintain contribution quality. It uses black box reverse engineering to identify GPL-licensed components in firmware.

## Quick Start

1. Clone the repo and run `direnv allow` (requires [Nix](https://nixos.org/download.html))
2. Run `uv run pytest` to verify the environment (647+ tests)
3. Install Claude Code plugins from `github:stvhay/my-claude-plugins` (see [CLAUDE.md](CLAUDE.md#plugins) for the list)

## Workflow

Every change — feature, fix, refactor, docs, or skill — follows this process:

### 1. File a GitHub issue

File a GitHub issue describing the problem and proposed solution. Use the appropriate template:

- **[Analysis Task](.github/ISSUE_TEMPLATE/analysis.yml)** — New analysis scripts
- **[Bug Report](.github/ISSUE_TEMPLATE/bug.yml)** — Issues with scripts or framework
- **[Documentation](.github/ISSUE_TEMPLATE/documentation.yml)** — Template/wiki updates
- **[Infrastructure](.github/ISSUE_TEMPLATE/infrastructure.yml)** — Tooling improvements
- **[Chore](.github/ISSUE_TEMPLATE/chore.yml)** — Maintenance, dependencies, refactoring

Small fixes can reference an existing issue. [Completed Staff Work](standards/Completed%20Staff%20Work.txt) format preferred.

### 2. Create a branch

Use `/using-git-worktrees` to create an isolated worktree for your work, or create a branch manually.

### 3. Brainstorm the design

Run `/brainstorming` to explore the problem space before writing code. This skill asks clarifying questions, considers alternatives, and produces a design you can review before committing to an approach.

### 4. Write an implementation plan

Run `/writing-plans` to produce a structured plan in `docs/plans/` (a local working directory, not committed). The plan breaks the work into 2-3 self-contained tasks with exact file paths, code, and test commands. Paste the plan into your PR body when you open it.

### 5. Execute the plan

Run `/executing-plans` to implement the plan with checkpoints between tasks.

### 6. Verify before claiming done

`/verification-before-completion` triggers automatically before any completion claim. It requires running verification commands and confirming output — no "it should work" allowed.

### 7. Self-review

Run `/requesting-code-review` to dispatch a code review subagent that checks your work against the plan and project standards.

### 8. Finalize

`/finishing-a-development-branch` triggers automatically when work is complete. It guides you through merge prep, PR creation, or cleanup.

### 9. Open a pull request

Use the PR template. Include:
- Reference to the GitHub issue
- The implementation plan (paste into the collapsible details block)
- Atomic commits — one logical change per commit

---

## Plugin Reference

Workflow skills are provided by plugins from `github:stvhay/my-claude-plugins`. See [CLAUDE.md](CLAUDE.md#plugins) for the full list. Key skills used in the workflow above:

| Skill | Plugin | When to use |
|---|---|---|
| `brainstorming` | `dev-workflow-toolkit` | Before creative work — features, components, behavior changes |
| `writing-plans` | `dev-workflow-toolkit` | When you have requirements and need an implementation plan |
| `executing-plans` | `dev-workflow-toolkit` | To execute a written plan with checkpoints |
| `verification-before-completion` | `dev-workflow-toolkit` | Before any success or completion claim (auto-triggered) |
| `code-simplification` | `dev-workflow-toolkit` | After verification passes, as a pipeline step (auto-triggered) |
| `finishing-a-development-branch` | `dev-workflow-toolkit` | When implementation is complete and tests pass (auto-triggered) |
| `requesting-code-review` | `dev-workflow-toolkit` | Before submitting a PR, to self-review |
| `systematic-debugging` | `dev-workflow-toolkit` | When encountering bugs or test failures |
| `test-driven-development` | `dev-workflow-toolkit` | Before writing implementation code |
| `using-git-worktrees` | `dev-workflow-toolkit` | To create an isolated worktree for feature work |
| `writing-clearly-and-concisely` | `writing-toolkit` | Final editing pass on prose (docs, commit messages) |
| `skill-creator` | `skill-creator` | When creating or modifying skills |

---

## Black Box Methodology

**Core Principle**: All findings must be derivable from automated scripts.

### Good Contribution Example

```python
# Script outputs source metadata
result = {
    "kernel_version": "5.10.110",
    "kernel_version_source": "kernel",
    "kernel_version_method": "strings kernel.img | grep 'Linux version'"
}
```

**Why good?** The finding ("5.10.110") is traceable to a specific command that anyone can reproduce.

### Bad Contribution Example

```python
# Where did this come from?
result = {"kernel_version": "5.10.110"}
```

**Why bad?** No indication of how this was discovered. Not reproducible.

**Why This Matters:** Legal defensibility requires that every claim is traceable to a documented method. See [CLAUDE.md#reverse-engineering-methodology](CLAUDE.md#reverse-engineering-methodology) for complete methodology.

---

## Types of Contributions

1. **Analysis Scripts** — New firmware analysis capabilities
2. **Bug Fixes** — Fix incorrect analysis or broken scripts
3. **Documentation** — Improve clarity or add examples
4. **Infrastructure** — CI/CD, tooling, quality improvements
5. **Tests** — Expand test coverage or add edge cases

---

## Issue Templates

We use structured issue templates to maintain quality. Each enforces our black box methodology and quality standards.

### Analysis Task

**When to use**: Adding new analysis capabilities (e.g., identify Bluetooth drivers, extract firmware signatures)

**Required fields:**
- **Purpose**: What GPL component to identify
- **Methodology**: How will you extract this information? (binwalk, strings, etc.)
- **Expected outputs**: TOML format with `_source` and `_method` metadata
- **Source metadata compliance**: Every value must include how it was discovered

### Bug Report

**When to use**: Scripts producing incorrect results, analysis failures, broken functionality

**Required fields:**
- **Reproduction steps**: Exact commands to reproduce the issue
- **Expected vs. actual behavior**: What should happen vs. what does happen
- **Root cause analysis**: Initial hypothesis about why this occurs
- **Proposed fix**: How you think this should be fixed

### Documentation

**When to use**: Improving templates, wiki pages, or documentation

**Required fields:**
- **Traceability**: What script changes necessitate this documentation update?
- **Motivation**: Why is this documentation needed?
- **Proposed changes**: What specifically will you add/change?

**Note**: Documentation follows code. Scripts are the source of truth, documentation explains them.

### Infrastructure

**When to use**: Improving CI/CD, tooling, build process, quality checks

**Required fields:**
- **Problem statement**: What current limitation or issue exists?
- **Proposed solution**: How will you address it?
- **Testing approach**: How will you validate the improvement?

### Chore

**When to use**: Refactoring, dependency updates, code cleanup, maintenance

**Required fields:**
- **Scope**: What will be changed?
- **Impact assessment**: What might break? What are the risks?
- **Rollback plan**: If something goes wrong, how do we revert?

---

## Code Quality Standards

### Python

```python
# PEP 8 style (enforced by ruff format)
def analyze_component(firmware_path: str) -> dict[str, str]:
    """
    Analyze firmware component.

    Args:
        firmware_path: Path to firmware file

    Returns:
        Analysis results with source metadata
    """
    result = {
        "component": "kernel",
        "component_source": "firmware",
        "component_method": "binwalk -e firmware.img"
    }
    return result
```

**Best practices:**
- Type hints for public APIs
- Docstrings for all functions
- Comment the "why," not the "what"
- Source metadata for all findings

### Bash

```bash
#!/usr/bin/env bash
# Description: Extract kernel version from firmware

set -euo pipefail  # Exit on error, undefined vars, pipe failures

firmware_path="${1:?Usage: $0 <firmware_path>}"

# shellcheck disable=SC2034
kernel_version=$(strings "$firmware_path" | grep -m1 "Linux version" | awk '{print $3}')

echo "kernel_version=$kernel_version"
echo "kernel_version_method=strings firmware | grep 'Linux version'"
```

**Best practices:**
- Quote all variables
- Use `shellcheck` (enforced by CI)
- Include usage examples in comments
- Fail fast (set -euo pipefail)

### Tests

```python
def test_extract_kernel_version():
    """Test kernel version extraction from firmware."""
    # Arrange
    firmware_path = "tests/fixtures/test_firmware.img"

    # Act
    result = extract_kernel_version(firmware_path)

    # Assert
    assert result["kernel_version"] == "5.10.110"
    assert "_source" in result["kernel_version"]
    assert "_method" in result["kernel_version"]
```

**Best practices:**
- Use pytest with clear test names
- Test both success and error paths
- Aim for ≥60% coverage (enforced)
- Include edge cases

### Commits

**Atomic commits** with conventional types: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`

```bash
git commit -m "feat: Add Bluetooth driver version extraction

- Extract version from /usr/bin/bluetoothd strings output
- Add source metadata (_source, _method)
- Add tests with 80% coverage

Closes #123"
```

---

## Project-Specific Guidelines

- **Dependencies.** If you add a dependency, update `flake.nix` (Nix) and test commands in `README.md`.
- **Documentation.** If your change affects analysis output, update the relevant Jinja templates and TOML results. Documentation follows code — scripts are the source of truth.
- **Analysis results.** All new TOML fields must include `_source` and `_method` metadata.

---

## Quality Management System (QMS)

This project follows an **ISO 9001-aligned Quality Management System**. Key principles:

- **100% Reproducibility** — All findings traceable to scripts
- **≥60% Test Coverage** — Automated validation
- **Evidence-Based Documentation** — Jinja templates auto-cite sources
- **Continuous Improvement** — Regular refactoring to reduce technical debt

### For Contributors

Follow the procedures in [docs/quality/PROCEDURES.md](docs/quality/PROCEDURES.md):

- **P1: Analysis Script Development** — How to develop and validate analysis scripts
- **P2: Documentation Generation** — How to update templates and wiki pages
- **P3: Quality Assurance** — Quality gates and validation process

These procedures integrate with GitHub Issues, CI/CD, and pytest.

### For Maintainers

Full QMS documentation in [docs/quality/](docs/quality/):
- Quality Policy, Objectives, Procedures
- Risk Register, Competency Matrix
- Management Review, Internal Audit schedules
- Onboarding Process

---

## Path to Maintainership

**External Contributor → Maintainer**

### Step 1: Contribute Quality Work

- Submit several successful PRs
- Demonstrate understanding of black box methodology
- Show commitment to quality standards

### Step 2: Express Interest

- Open an issue: "Interest in becoming a maintainer"
- Explain your motivation and relevant expertise

### Step 3: Complete Onboarding

- Follow [docs/quality/ONBOARDING-PROCESS.md](docs/quality/ONBOARDING-PROCESS.md)
- Provide evidence of expertise (GitHub portfolio, resume/CV)
- Self-assessment interview
- Competency mapping

### Step 4: Profile Creation

- **Agent reference profile** — AI collaboration context (`.claude/agents/<username>.md`)
- **QMS competency profile** — ISO 9001 evidence (`docs/quality/maintainers/<username>.md`)
- Integration with quarterly/annual reviews

### Maintainer Benefits

- Direct commit access (after review)
- Issue triage and labeling
- Pull request approval authority
- AI agent collaboration context (personalized workflow)
- Participate in QMS management reviews

---

## Legal and Licensing

### Important Restrictions

**Do NOT commit:**
- Binary firmware files (`*.bin`, `*.img`)
- Extracted filesystem contents
- Proprietary code or data
- Files that could contain secrets (.env, credentials.json)

**Only commit:**
- Scripts to download/analyze publicly available firmware
- Documentation of methodology and findings (derived from scripts)
- References to GPL-licensed source code
- Analysis results that are **reproducible via scripts**

### License

**AGPL-3.0 with Military Use Restrictions**

This project is licensed under the GNU Affero General Public License v3.0 with additional restrictions prohibiting military, weapons, and paramilitary use.

- [LICENSE.md](LICENSE.md) — Full AGPL-3.0 text
- [LICENSE.ADDENDUM.md](LICENSE.ADDENDUM.md) — Additional restrictions
- [RELICENSING.md](RELICENSING.md) — Relicensing notice (from GPL-2.0)

**Non-OSI Compliant**: The additional restrictions make this license non-compliant with the Open Source Definition. This is intentional.

By contributing, you agree that your contributions will be licensed under the same terms.

---

## Community Standards

### We Value

- **Rigor**: Quality over speed
- **Transparency**: Methodology is fully documented
- **Reproducibility**: Everything must be automated and traceable
- **Collaboration**: Respectful, constructive feedback
- **Evidence**: All claims backed by documented methods

### We Do NOT Tolerate

- Harassment or discrimination
- Uncommitted binary files (breaks legal guidelines)
- Undocumented "magic numbers" (breaks black box methodology)
- Bypassing quality gates (tests, linting, coverage)
- Unsubstantiated claims (must provide evidence/methodology)

### Code of Conduct

This project adheres to professional standards:

- **Be respectful**: Critique code, not people
- **Be constructive**: Suggest improvements, don't just criticize
- **Be collaborative**: We're all working toward the same goal
- **Be evidence-based**: Support claims with data and methodology
- **Be transparent**: Share your reasoning and process

---

## FAQ

### Do I need to be an expert in reverse engineering?

No. We welcome contributors at all skill levels. If you can write Python, analyze binary files, or improve documentation, you can contribute. The QMS and issue templates guide you through the process.

### What if I find something manually (not via script)?

Encode your discovery method into a script:
1. You manually discover kernel version at offset 0x2000
2. Write a script: `binwalk -e firmware.img | grep "Kernel"` to find it automatically
3. Submit the script that outputs the finding with source metadata

### How long does PR review take?

Typically 1--3 days for small PRs, up to a week for large changes. Complex changes may require multiple review rounds.

### Can I contribute if I work for GL.iNet?

Yes. This project welcomes all contributors. However, be aware that findings may be used to demonstrate GPL compliance obligations.

### Why so many templates and procedures?

GPL compliance analysis has legal implications. Our QMS ensures every finding is defensible, reproducible, and accurately documented. This rigor protects both the project and contributors.

---

## Getting Help

- **Questions**: Open a [GitHub Discussion](https://github.com/stvhay/glinet-comet-reverse-gpl/discussions)
- **Bugs**: Use [Bug Report template](.github/ISSUE_TEMPLATE/bug.yml)
- **Feature Ideas**: Open an issue with your proposal ([Completed Staff Work](standards/Completed%20Staff%20Work.txt) format appreciated)

---

## Additional Resources

- **[CLAUDE.md](CLAUDE.md)** — Full project methodology and black box principles
- **[README.md](README.md)** — Project overview and key findings
- **[docs/quality/](docs/quality/)** — Complete QMS documentation
- **[Wiki](https://github.com/stvhay/glinet-comet-reverse-gpl/wiki)** — Detailed analysis reports
