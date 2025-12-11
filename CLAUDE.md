# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project

**Black box reverse engineering** of GL.iNet Comet (RM1) KVM to identify GPL-licensed components and facilitate GPL compliance.

**Repository**: https://github.com/stvhay/glinet-comet-reverse-gpl

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

- Bash: quote variables, use `shellcheck`
- Python: PEP 8, type hints for public APIs
- Comment the why, not the what
- Test scripts before committing
- **Scripts must output their reasoning**: Show what was found and how
- **Trace all values**: Every offset, signature, or identifier must be discoverable from script output

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
