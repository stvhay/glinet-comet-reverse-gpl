# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project

**Black box reverse engineering** of GL.iNet Comet (RM1) KVM to identify GPL-licensed components and facilitate GPL compliance.

**Repository**: https://github.com/stvhay/glinet-comet-reverse-gpl

## Reverse Engineering Methodology

This project follows strict **black box reverse engineering** principles:

1. **Scripts are the source of truth**: All findings must be derivable from automated analysis scripts
2. **No magic numbers**: Every offset, address, or value must be traced to script output
3. **Replicable methodology**: Anyone running our scripts on the same firmware must arrive at identical conclusions
4. **Documentation describes discoveries**: Write what the scripts found, not what you know from other sources

If you discover something manually, encode that discovery method into a script before documenting it.

## Legal Constraints

**Allowed in repo:** Scripts to download/analyze publicly available firmware, methodology documentation, references to GPL source, reproducible analysis results.

**Never commit:** Binary firmware files (*.bin, *.img), extracted filesystem contents, proprietary code/data, findings without documented derivation.

## Firmware

- **URL**: https://fw.gl-inet.com/kvm/rm1/release/glkvm-RM1-1.7.2-1128-1764344791.img
- **Format**: Rockchip RKFW firmware image
- **Device**: GL.iNet Comet (RM1) KVM
- **SoC**: Rockchip RV1126 (armv7)
- **Tools**: `binwalk`, `unsquashfs`, `dtc`, `strings`, `xxd`

### Rockchip SDK Layout

The firmware builds from a standard Rockchip SDK with sibling directories: `buildroot/`, `kernel/`, `u-boot/`, `prebuilts/`, `device/`. Evidence from buildroot-2018:
- Kernel: `BR2_LINUX_KERNEL_CUSTOM_LOCAL_LOCATION="$(TOPDIR)/../kernel"`
- Toolchain: `$(TOPDIR)/../prebuilts/gcc/linux-x86/arm/gcc-arm-8.3-2019.03-x86_64-arm-linux-gnueabihf`
- U-Boot 2017.09 is built separately via its own `make.sh`, not Buildroot's build system

### Relevant Repos

- **kernel-4.19** and **buildroot-2018** — relevant to RM1 (kernel 4.19.111, Buildroot 2018.02-rc3)
- **kernel-6.1** and **buildroot-2024** — for newer products (RM1PE/RM10/RM10RC), NOT the original RM1

## Quality Management

This project follows an ISO 9001:2015-aligned QMS. See [`docs/quality/`](docs/quality/) for policies, procedures (P1-P4), risk register, and quality objectives. Key targets: 100% reproducibility, ≥60% test coverage, zero linting errors.

## Documentation System

All documentation is generated from Jinja templates that consume analysis results (`results/*.toml`) and auto-cite sources via the `| src` filter. See [`docs/design-jinja-documentation.md`](docs/design-jinja-documentation.md) for the complete architecture.

## Development

### Environment

**Setup:** `direnv allow` (loads nix flake automatically)

Nix provides system tools (binwalk, dtc, strings, shellcheck, etc.). Python dependencies are managed by `uv` from `pyproject.toml`:

```bash
uv run pytest                              # Run all tests + quality checks
uv run python3 scripts/analyze_uboot.py    # Run analysis script
uv run ruff check --fix scripts/ tests/    # Fix lint
uv run ruff format scripts/ tests/         # Format
```

### Git Standards

**Atomic commits** with conventional types: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`

```bash
git commit -m "$(cat <<'EOF'
<type>: <description>

<optional body explaining why>

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**Never push without explicit user permission.** Pre-push hook runs pytest automatically.

### Code Quality

- Bash: quote variables, use `shellcheck`
- Python: PEP 8, type hints for public APIs
- Scripts must output their reasoning and trace all values
- `uv run pytest` runs all tests, linting, formatting, shellcheck, and coverage

### Issue Workflow

Create issues before starting non-trivial work. Use templates, label consistently, branch for multi-file changes, PR for review. See [`docs/ISSUE-WORKFLOW.md`](docs/ISSUE-WORKFLOW.md).

### Authorized Commands

Use commands from `.claude/settings.local.json` authorization list. Prefer authorized formulations over alternatives requiring new authorization.

## Subagents

| Agent | Model | Use for |
|-------|-------|---------|
| `code-reviewer` | Opus | Thorough code review after significant changes |
| `quick-task` | Haiku | Typos, simple edits, basic commands |

## Skills

Contributing workflow skills ship with the repo in `.claude/skills/` and are loaded automatically by Claude Code. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow and skill reference.

## Completed Staff Work

Follow the Completed Staff Work doctrine when reporting findings or making recommendations. Present solutions, not problems. See [`standards/COMPLETED-STAFF-WORK.md`](standards/COMPLETED-STAFF-WORK.md).

## Traceability

Every factual claim must trace to a script output. See [`docs/plans/2026-03-01-traceability-enforcement-design.md`](docs/plans/2026-03-01-traceability-enforcement-design.md) for the enforcement design. Use `<!-- cite: results/<file>.toml#<field> -->` in hand-written docs; use `| src` filter in Jinja templates.

## CI/CD

GitHub Actions runs on push to `main` and PRs. Analysis results uploaded as artifacts. Wiki auto-syncs from `docs/` and `wiki/`.
