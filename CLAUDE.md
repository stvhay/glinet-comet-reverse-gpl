# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project

**Black box reverse engineering** of GL.iNet Comet (RM1) KVM to identify GPL-licensed components and facilitate GPL compliance.

**Repository**: https://github.com/stvhay/glinet-comet-reverse-gpl

## Quality Management

This project follows an ISO 9001:2015-aligned quality management system to ensure accuracy, reproducibility, and credibility of analysis results.

**Quality Documentation:**
- [Quality Objectives](docs/quality/QUALITY-OBJECTIVES.md) - Measurable targets for analysis accuracy, test coverage, and continuous improvement
- [Risk Register](docs/quality/RISK-REGISTER.md) - Identified risks and mitigations (legal, technical, operational)
- ISO 9001 Gap Analysis: `docs/reports/iso-9001-gap-analysis-2025-12-12.md`

**Key Quality Principles:**
1. **100% Reproducibility** - All findings traceable to automated scripts
2. **≥60% Test Coverage** - Enforced by CI/CD
3. **Zero Linting Errors** - Code quality gates prevent broken code
4. **Evidence-Based** - Every conclusion backed by documented methodology
5. **Continuous Improvement** - Regular refactoring to reduce technical debt

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

## CI/CD

- GitHub Actions runs on push to `main` and PRs
- Analysis results uploaded as artifacts
- Wiki auto-syncs from `docs/` and `wiki/` on push
