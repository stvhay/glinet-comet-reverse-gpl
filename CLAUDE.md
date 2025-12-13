# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project

**Black box reverse engineering** of GL.iNet Comet (RM1) KVM to identify GPL-licensed components and facilitate GPL compliance.

**Repository**: https://github.com/stvhay/glinet-comet-reverse-gpl

## Quality Management

This project follows an ISO 9001:2015-aligned quality management system to ensure accuracy, reproducibility, and credibility of analysis results.

**Quality Documentation:**
- [Quality Policy](docs/quality/QUALITY-POLICY.md) - Commitment to evidence-based analysis and continuous improvement
- [QMS Scope](docs/quality/QMS-SCOPE.md) - Boundaries and applicability of quality management system
- [Quality Objectives](docs/quality/QUALITY-OBJECTIVES.md) - Measurable targets for analysis accuracy, test coverage, and continuous improvement
- [Risk Register](docs/quality/RISK-REGISTER.md) - Identified risks and mitigations (legal, technical, operational)
- [Procedures](docs/quality/PROCEDURES.md) - Core operational procedures (P1-P4)

**Key Quality Principles:**
1. **100% Reproducibility** - All findings traceable to automated scripts
2. **≥60% Test Coverage** - Enforced by CI/CD
3. **Zero Linting Errors** - Code quality gates prevent broken code
4. **Evidence-Based** - Every conclusion backed by documented methodology
5. **Continuous Improvement** - Regular refactoring to reduce technical debt

**Core Procedures:**
- **P1: Analysis Script Development** - Creating analysis scripts with black box methodology
- **P2: Documentation Generation** - Rendering Jinja templates from analysis results
- **P3: Quality Assurance** - Running pytest, shellcheck, and CI/CD validation
- **P4: Corrective Action** - Addressing non-conformances and root causes

See [Issue Templates](.github/ISSUE_TEMPLATE/) for quality gates enforced during development.

## Reverse Engineering Methodology

This project follows strict **black box reverse engineering** principles:

### Core Principles

1. **Scripts are the source of truth**: All findings must be derivable from automated analysis scripts
2. **No magic numbers**: Every offset, address, or value must be traced to script output
3. **Replicable methodology**: Anyone running our scripts on the same firmware must arrive at identical conclusions
4. **Documentation describes discoveries**: Write what the scripts found, not what you know from other sources

### In Practice

**Good**: "At offset 0x2000 (found via `binwalk -e firmware.img`), the kernel partition begins..."

**Bad**: "The kernel is at 0x2000" (where did this number come from?)

**Good**: "Script `extract_kernel.sh` identifies kernel magic bytes using pattern matching against known signatures..."

**Bad**: "The kernel is compressed with gzip" (how do we know this?)

### Workflow

1. Write analysis scripts that output findings with justification
2. Document what the scripts discovered and how
3. Never commit findings that cannot be reproduced by running the scripts
4. If you discover something manually, encode that discovery method into a script

## Documentation System

### Jinja Templates with Source Tracking

All documentation is generated from Jinja templates that automatically cite their sources:

**Analysis scripts output JSON with source metadata:**
```json
{
  "kernel_offset": "0x2000",
  "kernel_offset_source": "kernel",
  "kernel_offset_method": "binwalk -e firmware.img | grep 'Kernel'"
}
```

**Templates use `| src` filter for automatic footnotes:**
```jinja
{% set kernel = analyze('kernel') %}
Kernel at {{ kernel.kernel_offset | src }}

{{ render_footnotes() }}
```

**Renders as:**
```markdown
Kernel at 0x2000[^1]

## Sources
[^1]: [scripts/analyze_kernel.sh](../scripts/analyze_kernel.sh) - `binwalk -e firmware.img | grep 'Kernel'`
```

### Results Directory

**`results/`** - Committed analysis data in TOML format
- `results/*.toml` - Cached analysis results with source metadata
- `results/.manifest.toml` - Hash tracking for cache invalidation
- These files prove findings derive from specific firmware + script versions

### Template Rendering Workflow

**1. Run analysis scripts (outputs TOML with source metadata):**
```bash
# Analysis scripts now output TOML (default) or JSON
./scripts/analyze_device_trees.py > results/device-trees.toml
./scripts/analyze_rootfs.py > results/rootfs.toml
./scripts/analyze_uboot.py > results/uboot.toml
./scripts/analyze_boot_process.py > results/boot-process.toml
./scripts/analyze_network_services.py > results/network-services.toml
./scripts/analyze_proprietary_blobs.py > results/proprietary-blobs.toml
./scripts/analyze_secure_boot.py > results/secure-boot.toml
```

**2. Render templates (consumes TOML/JSON):**
```bash
# Render single template
./scripts/render_template.py templates/wiki/Kernel.md.j2 wiki/Kernel.md

# Render all templates
./scripts/render_wiki.sh  # (when available)
```

**3. Template best practices:**
- Always use `| src` filter to auto-generate footnotes
- Templates read from `results/*.toml` via `analyze()` function
- Source metadata (`_source`, `_method`) fields generate citations automatically
- Never hard-code findings in templates - pull from analysis results

See `docs/design-jinja-documentation.md` for complete architecture.

## Legal Constraints

**Allowed in repo:**
- Scripts to download/analyze publicly available firmware
- Documentation of methodology and findings (derived from scripts)
- References to GPL-licensed source code
- Analysis results that are **reproducible via scripts**

**Never commit:**
- Binary firmware files (*.bin, *.img)
- Extracted filesystem contents
- Proprietary code or data
- "Magic numbers" or findings without documented derivation

## Firmware

- **URL**: https://fw.gl-inet.com/kvm/rm1/release/glkvm-RM1-1.7.2-1128-1764344791.img
- **Format**: Rockchip RKFW firmware image
- **Device**: GL.iNet Comet (RM1) KVM
- **Tools**: `binwalk`, `unsquashfs`, `dtc`, `strings`, `xxd`

## Development

### Environment

ALL commands require nix: `nix develop` or `direnv allow`

### Git Standards

**Atomic commits** with conventional types: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`

```bash
git commit -m "$(cat <<'EOF'
<type>: <description>

<optional body explaining why>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**Never push without explicit user permission.**

### Code Quality

**Quality Standards:**
- Bash: quote variables, use `shellcheck`
- Python: PEP 8, type hints for public APIs
- Comment the why, not the what
- Test scripts before committing
- **Scripts must output their reasoning**: Show what was found and how
- **Trace all values**: Every offset, signature, or identifier must be discoverable from script output

**Quality Checks (MUST pass before commit/push):**

All quality checks are integrated into pytest for simplicity and consistency:

1. **Single command to run all checks:**
   ```bash
   pytest
   ```
   This runs:
   - All unit tests (559+ tests)
   - Code formatting checks (test_code_quality.py)
   - Code linting checks (test_code_quality.py)
   - Shellcheck on bash scripts (test_code_quality.py)
   - Coverage checks

2. **Pre-push hook installed:**
   - Automatically runs `pytest` before `git push`
   - Blocks push if any test or quality check fails
   - Located at `.git/hooks/pre-push`

3. **Quality check helper script:**
   ```bash
   ./scripts/quality-check.sh
   ```
   Wrapper around pytest with friendly output

**IMPORTANT:** Never push code without passing pytest. CI failures after push indicate a process failure.

**Quick fixes:**
```bash
# See specific quality failures
pytest tests/test_code_quality.py -v

# Fix linting issues automatically
ruff check --fix scripts/ tests/

# Format code automatically
ruff format scripts/ tests/

# Run all tests with coverage
pytest
```

### Embedded Workflow (Checkpoint Files)

**Status:** Experimental (Epic #77) - Under evaluation via pilot Issue #83

The embedded workflow uses checkpoint files to enable work resumption and provide context clarity. Checkpoints serve the agent's own reasoning process first, QA second.

**Purpose:**
- Enable work resumption after session breaks or crashes
- Provide context clarity for the agent's own reasoning
- Generate issue narratives as natural byproduct of clear thinking
- Prevent scratchpad staleness through regular status updates

**Location:** `.claude/work/issue-N/NNN-description.txt`

#### When to Write Checkpoints (Significant Actions)

Write a checkpoint file after:
- ✅ Created/modified a file (scripts, tests, docs)
- ✅ Ran tests and discovered failures or successes
- ✅ Completed a TodoWrite task
- ✅ Discovered important information (grep/glob findings, analysis results)
- ✅ Made a commit
- ✅ Hit a blocker or changed approach
- ✅ **Session start (always)**
- ✅ **Session end (always)**
- ✅ **Issue start (always)**
- ✅ **Issue close (always)**

Do NOT write checkpoints for:
- ❌ Reading files for context
- ❌ Running formatting tools (ruff format)
- ❌ Small edits to fix typos
- ❌ Consecutive commits in same logical unit of work

#### Checkpoint Format

```
[YYYY-MM-DD HH:MM]
WHAT: <What was just accomplished - be specific>
WHY: <Why this action was taken - rationale, problem solved>
NEXT: <What's the next planned action - specific>
STATUS: <Optional: files modified, tests status, blockers>
```

#### Quality Target

Checkpoints are scored using a 1-4 rubric:
- **Score 3-4 (Target):** Includes WHAT + WHY + NEXT with sufficient detail to resume work
- **Score 1-2 (Avoid):** Perfunctory, generic, compliance theater ("Working on issue", "Making progress")

**Reference:** [STATUS-UPDATE-QUALITY-CRITERIA.md](docs/quality/STATUS-UPDATE-QUALITY-CRITERIA.md)

#### Granularity Guidance

- **Target:** 3-8 checkpoints per issue
- **Too few (<3):** Insufficient detail for resumption
- **Too many (>10):** Overhead, likely over-documenting

#### Examples

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

#### Key Principle

**Checkpoints serve YOUR clarity and work resumption.** If they're helpful for you to understand what you were doing and what comes next, they'll be useful for QA. If they're compliance theater, they fail the purpose.

Think of checkpoints as writing a note to your future self who will resume this work after a session break. What would you need to know?

#### Integration with Scratchpad

Checkpoint files complement but don't replace scratchpad updates:
- **Scratchpad:** High-level current state (what issue, what's happening now, what's next)
- **Checkpoints:** Detailed work log (what was done, why, reasoning, next steps)

Both are required. Scratchpad is enforced by P5 procedure (15-minute staleness check). Checkpoints are voluntary but measured for quality.

#### Pushing Scratchpad to Gist

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

#### References

- **Epic #77:** Embedded Workflow System
- **Quality Criteria:** [STATUS-UPDATE-QUALITY-CRITERIA.md](docs/quality/STATUS-UPDATE-QUALITY-CRITERIA.md)
- **Measurement Methodology:** [STATUS-UPDATE-MEASUREMENT-METHODOLOGY.md](docs/quality/STATUS-UPDATE-MEASUREMENT-METHODOLOGY.md)
- **Exit Criteria:** [EMBEDDED-WORKFLOW-EXIT-CRITERIA.md](docs/quality/EMBEDDED-WORKFLOW-EXIT-CRITERIA.md)

**Note:** This section may be moved to separate files (e.g., `.claude/WORKFLOW.md` or `.claude/agents/workflow-guidelines.md`) if CLAUDE.md context becomes too large or if multiple agent modalities require different workflow instructions.

### Settings and Authorized Commands

**Always use authorized commands from settings.local.json when available.**

Claude Code has pre-authorized commands in `.claude/settings.local.json`. When performing tasks:

1. **Check authorized commands first** - Use commands from the Bash tool authorization list shown in your system prompt
2. **Prefer authorized formulations** - Don't use alternative command syntax requiring additional authorization
3. **Work within limits** - Respect the boundaries defined in settings without trying to escape them

**Examples:**

✅ **Use authorized commands:**
- `git status` (if authorized)
- `pytest` (if authorized)
- `ls /tmp/file.txt` (if path authorized)

❌ **Don't use alternatives requiring new authorization:**
- `git --no-pager status` (when simple `git status` is authorized)
- `pytest -v` (when only `pytest` is authorized - use `pytest` and accept default verbosity)
- `/bin/ls /tmp/file.txt` (when `ls` is authorized - use the authorized form)

**Reference:** The authorized command list is shown in your system prompt under "You can use the following tools without requiring user approval". Check this list before using Bash commands.

**Settings location:** `.claude/settings.local.json`

### Issue Templates

Use GitHub issue templates to maintain consistency and enforce methodology:

- **Analysis Task** - New analysis scripts (enforces source metadata, JSON output)
- **Infrastructure** - Framework/tooling improvements
- **Bug Report** - Issues with scripts or framework
- **Documentation** - Template/wiki updates (must trace to script changes)
- **Chore** - Maintenance, dependencies, refactoring

Templates enforce black box principles with required fields and acceptance criteria checklists.

## Subagents

This project uses model-specific subagents in `.claude/agents/`:

| Agent | Model | Use for |
|-------|-------|---------|
| `code-reviewer` | Opus | Thorough code review after significant changes |
| `quick-task` | Haiku | Typos, simple edits, basic commands |

**Delegation guidance:**
- Use `code-reviewer` after writing/modifying significant code
- Use `quick-task` for trivial fixes to save cost
- Handle routine work directly (Sonnet)

## Completed Staff Work

When reporting findings or making recommendations, follow the **Completed Staff Work** doctrine (see `standards/Completed Staff Work.txt`):

### Core Principles

1. **Present solutions, not problems** - The user needs answers, not questions
2. **Work out all details yourself** - Don't ask "what should I do?" - advise what they ought to do
3. **Present finished work** - Ready for approval/disapproval with just a signature
4. **Keep it concise** - No long explanations unless requested
5. **Stake your reputation** - Would you sign off on this work?

### In Practice

**✅ Completed Staff Work:**
- "Here's the complete fix [PR/code ready for review]"
- "Analysis complete. Recommendation: [specific action with rationale]. Ready for approval."
- "Issue identified. Proposed solution: [detailed plan]. Implementation ready in branch X."

**❌ Incomplete Staff Work:**
- "I found a problem, what should we do?"
- "I analyzed this. Here's 10 pages of data. What do you think?"
- "Should we use approach A or B?" (without recommendation)
- "What would you like me to do about this?"

### When to Present

Apply this doctrine when:
- Reporting analysis findings
- Making recommendations or proposals
- Presenting problem reports (include proposed solution)
- Submitting design proposals (complete plans, not partial ideas)
- Delivering any work requiring user approval

### Rough Drafts Are OK

Rough drafts are acceptable if:
- ✅ Complete in substance (all details worked out)
- ✅ Just needs polish (formatting, copies, cleanup)
- ❌ NOT acceptable: Half-baked ideas or shifting decision burden to user

### Final Test

Before presenting work, ask yourself:

> **"If I were the user, would I be willing to sign this and stake my professional reputation on it being right?"**

If the answer is **no**, take it back and work it over - it's not yet completed staff work.

## CI/CD

- GitHub Actions runs on push to `main` and PRs
- Analysis results uploaded as artifacts
- Wiki auto-syncs from `docs/` and `wiki/` on push
