# AGENTS.md

Instructions for AI coding agents working on this repository.

## Project

**Black box reverse engineering** of GL.iNet Comet (RM1) KVM device to identify GPL-licensed components.

### Critical Methodology

**All findings must be derivable from scripts. No magic numbers. Replicable methodology only.**

- Scripts are the source of truth - document what they discover
- Every offset, address, or value must trace to script output
- Anyone running our scripts must reach identical conclusions
- If you discover something manually, encode it into a script first

## Quality Management

This project uses an ISO 9001:2015-aligned QMS. Follow the documented procedures:

- **P1:** Analysis Script Development - Use issue template, write tests, run quality checks
- **P2:** Documentation Generation - Render Jinja templates from TOML results
- **P3:** Quality Assurance - pytest + shellcheck must pass before commit
- **P4:** Corrective Action - Address failures, document root cause

See [Procedures](docs/quality/PROCEDURES.md) for full workflow details and [Competency Matrix](docs/quality/COMPETENCY-MATRIX.md) for agent-specific requirements.

## Commands

```bash
# Enter development environment (required for all commands)
nix develop

# Run full analysis
./scripts/analyze.sh

# Render documentation templates
python3 scripts/render_template.py templates/wiki/Example.md.j2 wiki/Example.md

# Batch render all wiki templates
./scripts/render_wiki.sh

# Run tests
pytest tests/ -v

# Lint bash scripts
shellcheck scripts/*.sh
```

## Tech Stack

- Nix flakes for reproducible environment
- Bash/Python scripts for analysis
- Python + Jinja2 for documentation templates
- pytest for testing
- GitHub Actions for CI
- GitHub Wiki for documentation

## Code Style

- Bash: Quote variables, use `shellcheck`, follow [Bash Guide](https://mywiki.wooledge.org/FullBashGuide)
- Python: Type hints for public APIs, PEP 8
- Commits: Conventional format (`feat:`, `fix:`, `docs:`, `chore:`)
- Comments: Explain why, not what
- **Scripts must show their work**: Output JSON with `_source` and `_method` metadata

## Documentation

Analysis scripts output TOML/JSON → cached in `results/*.toml` → rendered via Jinja templates

### Template Conventions

**1. Analysis script output format (Python scripts):**
All Python analysis scripts (`analyze_*.py`) output structured data with source metadata:
```toml
# Analysis scripts output TOML by default (use --format json for JSON)
firmware_file = "glkvm-RM1-1.7.2-1128-1764344791.img"
kernel_offset = "0x2000"
kernel_offset_source = "kernel"
kernel_offset_method = "binwalk -e firmware.img | grep 'Kernel'"
```

**2. Template usage with `| src` filter:**
Templates automatically generate citations from `_source` and `_method` fields:
```jinja
{% set data = analyze('kernel') %}
Kernel at {{ data.kernel_offset | src }}  {# Auto-generates footnote #}

{{ render_footnotes() }}
```

**Renders as:**
```markdown
Kernel at 0x2000[^1]

## Sources
[^1]: [scripts/analyze_kernel.py](../scripts/analyze_kernel.py) - `binwalk -e firmware.img | grep 'Kernel'`
```

**3. Best practices:**
- **Never hard-code findings** in templates - always pull from analysis results
- **Every value must have source metadata** - use `_source` and `_method` suffix fields
- **Use `| src` filter** on all data from analysis scripts for automatic citations
- **Cache results** in `results/*.toml` for template consumption
- **Python over Bash** - new analysis scripts should be written in Python with type hints

**4. Template file naming:**
- Place templates in `templates/wiki/` directory
- Use `.md.j2` extension for Jinja markdown templates
- Output to `wiki/` directory with `.md` extension
- Example: `templates/wiki/Kernel.md.j2` → `wiki/Kernel.md`

See `docs/design-jinja-documentation.md` for full architecture.

## Project Structure

```
scripts/          # Analysis scripts
docs/             # Documentation (syncs to wiki)
wiki/             # Wiki-specific pages
.claude/agents/   # Claude Code subagents
output/           # Generated analysis (not committed)
downloads/        # Cached firmware (not committed)
```

## Testing

Run `shellcheck` on all bash scripts before committing:
```bash
shellcheck scripts/*.sh
```

## Boundaries

### Always
- Run commands inside `nix develop`
- Use atomic commits with type prefixes
- Test scripts before committing (pytest, shellcheck)
- Use issue templates when creating issues

### Ask First
- Before pushing to remote
- Before modifying CI workflows
- Before adding new dependencies

### Never
- Commit binary files (*.bin, *.img)
- Commit extracted firmware contents
- Commit proprietary code or data
- Use "magic numbers" without documenting their derivation
- Document findings that cannot be reproduced by running scripts
- Push without explicit permission

## Issue Templates

When creating issues, use the appropriate template (enforces methodology):
- **Analysis** - New analysis scripts
- **Infrastructure** - Framework/tooling
- **Bug** - Broken scripts/incorrect results
- **Documentation** - Wiki/template updates
- **Chore** - Maintenance/refactoring

Templates have required fields and acceptance criteria checklists.
