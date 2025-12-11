# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project

Reverse engineering GL.iNet Comet (RM1) KVM to identify GPL-licensed components and facilitate GPL compliance.

**Repository**: https://github.com/stvhay/glinet-comet-reverse-gpl

## Legal Constraints

**Allowed in repo:**
- Scripts to download/analyze publicly available firmware
- Documentation of methodology
- References to GPL-licensed source code

**Never commit:**
- Binary firmware files (*.bin, *.img)
- Extracted filesystem contents
- Proprietary code or data

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
