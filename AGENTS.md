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

# Lint bash scripts
shellcheck scripts/*.sh
```

## Tech Stack

- Nix flakes for reproducible environment
- Bash scripts for analysis
- GitHub Actions for CI
- GitHub Wiki for documentation

## Code Style

- Bash: Quote variables, use `shellcheck`, follow [Bash Guide](https://mywiki.wooledge.org/FullBashGuide)
- Commits: Conventional format (`feat:`, `fix:`, `docs:`, `chore:`)
- Comments: Explain why, not what
- **Scripts must show their work**: Output reasoning and trace all discovered values

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
- Test scripts before committing

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
