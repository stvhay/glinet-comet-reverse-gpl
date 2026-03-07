# Contributing with Claude Code

This guide covers how to use [Claude Code](https://github.com/anthropics/claude-code) to contribute to this project. It assumes you're an experienced developer familiar with CLI tooling and git.

For general contribution guidelines, see [CONTRIBUTING.md](../CONTRIBUTING.md).

## Quick Setup

```bash
# 1. Install Claude Code
# See https://github.com/anthropics/claude-code#installation

# 2. Clone the repo
git clone https://github.com/stvhay/glinet-comet-reverse-gpl.git
cd glinet-comet-reverse-gpl

# 3. Enter the dev environment (Nix provides all system tools)
direnv allow

# 4. Start Claude
claude
```

No manual context loading is needed -- Claude reads `CLAUDE.md` automatically on every session.

## How Claude Knows This Project

The project is pre-configured for Claude Code through several mechanisms:

**CLAUDE.md** loads automatically at session start. It contains the black-box reverse engineering methodology, legal constraints (no binaries in repo), firmware details, development commands, git commit conventions, and quality standards. You don't need to brief Claude on any of this.

**`results/*.toml`** files contain structured analysis outputs from every script. These are more useful as context than prose descriptions -- point Claude at a specific TOML file when working on related analysis or documentation.

**Traceability enforcement** is built into the instructions. Claude is directed to trace every finding to a script output and follow the project's reproducibility requirements. If Claude suggests committing binaries or undocumented findings, the CLAUDE.md constraints should prevent it, but stay aware of these rules yourself.

## Subagents and Skills

**Subagents** handle specialized tasks without polluting your main conversation context:

| Agent | Model | Use for |
|-------|-------|---------|
| `code-reviewer` | Opus | Thorough review after significant changes |
| `quick-task` | Haiku | Typos, simple renames, basic commands |

Claude selects these automatically based on CLAUDE.md guidance, but you can also request them directly (e.g., "use the code-reviewer agent to review this change").

**Skills** are provided by plugins from `github:stvhay/my-claude-plugins`. Invoke them with `/skill-name` (e.g., `/brainstorming`, `/systematic-debugging`). See [CLAUDE.md](CLAUDE.md#plugins) for the full plugin list.
