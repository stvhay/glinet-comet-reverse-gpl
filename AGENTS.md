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

## Commands

```bash
# Enter development environment (required for all commands)
nix develop

# Run full analysis
./scripts/analyze.sh

# Render documentation templates
python3 scripts/render_template.py templates/wiki/Example.md.j2 wiki/Example.md

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

Analysis scripts output JSON → cached in `results/*.toml` → rendered via Jinja templates

**Template example:**
```jinja
{% set data = analyze('kernel') %}
Offset: {{ data.offset | src }}  {# Auto-generates footnote #}
{{ render_footnotes() }}
```

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
