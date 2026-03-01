# Contributing with Claude Code

[← Back to README](../README.md)

---

**Claude Code is an AI-powered development environment that can help with reverse engineering, analysis, and documentation.**

This project extensively uses Claude for firmware analysis, GPL compliance research, and documentation. Many of the analysis reports in `docs/analysis/` were created with Claude assistance.

This guide will help you get started using Claude Code to contribute to this project.

## Quick Setup

### 1. Install Claude Code CLI

Follow the installation instructions at [Claude Code](https://docs.anthropic.com/en/docs/build-with-claude/claude-code).

For most users:
```bash
# Install Claude Code globally
npm install -g @anthropics/claude-code
```

Or use the desktop app from [https://claude.ai/download](https://claude.ai/download).

### 2. Clone the Repository

```bash
git clone https://github.com/stvhay/glinet-comet-reverse-gpl.git
cd glinet-comet-reverse-gpl
```

### 3. Enter Development Environment

All commands in this project must run inside the Nix development environment:

```bash
# Option 1: Manual activation
nix develop

# Option 2: Automatic activation (recommended)
direnv allow
```

The Nix environment provides all required tools: `binwalk`, `unsquashfs`, `dtc`, `python3`, `shellcheck`, etc.

### 4. Start Claude

```bash
# From within the project directory
claude
```

Claude will automatically have access to the project files and can run commands in the Nix environment.

---

## What Claude Can Help With

This project uses Claude for:

- **Reverse Engineering Analysis** - Analyzing firmware components, identifying GPL-licensed code
- **Documentation** - Writing clear, comprehensive analysis reports
- **License Compliance Research** - Understanding GPL requirements and obligations
- **Binary Analysis** - Examining firmware structure, extracting components
- **Security Research** - Identifying potential security concerns
- **Script Development** - Writing analysis scripts and automation tools
- **Code Review** - Reviewing changes for correctness and methodology

---

## Useful Prompts

### Getting Started

When you first start Claude in the project directory, try:

```
Read CLAUDE.md and AGENTS.md to understand the project structure and constraints
```

This gives Claude context about legal constraints, git standards, and project methodology.

### Analysis Tasks

**Analyze firmware components:**
```
Analyze the firmware and look for GPL-licensed components we haven't documented yet
```

**Create new analysis reports:**
```
Create a new analysis report for [component] following the style in docs/analysis/
```

**Understand firmware features:**
```
Help me understand how the secure boot process works in this firmware
```

**License compliance research:**
```
Research what source code GL.iNet must provide for the FFmpeg libraries
```

### Documentation Tasks

**Generate documentation:**
```
Create documentation for the kernel module analysis, following the format in docs/analysis/kernel-version.md
```

**Update existing docs:**
```
Update docs/GPL-COMPLIANCE-ANALYSIS.md with the new components we found
```

### Script Development

**Create analysis scripts:**
```
Write a script to extract and analyze device tree blobs from the firmware
```

**Improve existing scripts:**
```
Review scripts/analyze.sh and suggest improvements for error handling
```

### Finding Specific Information

**Search for patterns:**
```
Search the firmware for references to Rockchip OP-TEE secure boot
```

**Identify binaries:**
```
Find all GPL-licensed binaries in the extracted filesystem
```

---

## Tips for Working with Claude

### 1. Point Claude to Context

Claude works best with specific context. Use the `/read` command or prompt Claude to read relevant files:

```
Read docs/analysis/kernel-version.md to understand the documentation style
```

```
Read the files in docs/analysis/ to understand what analysis we've already done
```

### 2. Leverage Existing Analysis

Before starting new analysis, check what's already been done:

- `docs/analysis/` - Completed firmware analysis reports
- `docs/reference/` - Reference documentation on Rockchip, GPL compliance
- `output/` - Raw analysis output (generated, not committed)

**Example prompt:**
```
Review docs/analysis/SUMMARY.md to see what analysis we have. Then suggest what analysis we're missing.
```

### 3. Use Claude's Code Execution

Claude can run commands directly in your development environment:

```
Run ./scripts/analyze.sh and summarize what GPL components it found
```

```
Use binwalk to scan the firmware and explain the partition structure
```

### 4. Ask Claude to Create Issues

When Claude discovers something important:

```
Create a GitHub issue documenting the security vulnerability you found in the boot process
```

Claude can format issues properly and add appropriate labels.

### 5. Follow Project Methodology

This project requires **replicable methodology** - all findings must come from scripts:

**Good prompt:**
```
Write a script to extract the U-Boot version, then document what it finds
```

**Bad prompt:**
```
Manually search for the U-Boot version in the hex dump and document it
```

### 6. Understand Legal Constraints

Before asking Claude to work with firmware:

**Never ask Claude to:**
- Commit binary firmware files (`.bin`, `.img`)
- Commit extracted filesystem contents
- Include proprietary code in the repository

**Always safe to ask Claude to:**
- Write scripts that download/analyze publicly available firmware
- Document what was found
- Reference GPL-licensed source code locations

### 7. Use the Subagents

This project uses model-specific subagents for different tasks:

| Agent | Best For | How to Use |
|-------|----------|------------|
| `code-reviewer` (Opus) | Thorough code review after major changes | `@code-reviewer review my changes to scripts/analyze.sh` |
| `quick-task` (Haiku) | Simple fixes, typos, basic commands | `@quick-task fix the typo in README.md` |
| Default (Sonnet) | Most development tasks | Use normally |

### 8. Commit Workflow

When Claude creates or modifies code:

```
Review the changes, then create a commit following the conventional commit format
```

Claude will:
1. Run `git status` and `git diff` to see changes
2. Create an appropriate commit message
3. Add the Claude Code attribution footer

**Never ask Claude to push** without your explicit permission.

---

## Example Workflows

### Workflow 1: Creating a New Analysis Report

1. **Provide context:**
   ```
   Read docs/analysis/kernel-version.md to see the documentation style we use
   ```

2. **Request analysis:**
   ```
   Analyze the Janus WebRTC Gateway found in the firmware and create a report in docs/analysis/janus-gateway.md
   ```

3. **Review and refine:**
   ```
   Add a section about GPL-3.0 compliance requirements for Janus
   ```

4. **Commit:**
   ```
   Create a commit for this new analysis report
   ```

### Workflow 2: Investigating a New Component

1. **Initial search:**
   ```
   Search the extracted firmware for references to "OP-TEE" or "TrustZone"
   ```

2. **Deep dive:**
   ```
   Based on what you found, analyze how secure boot is implemented and whether it uses GPL-licensed components
   ```

3. **Document:**
   ```
   Create a new document in docs/analysis/ explaining the secure boot chain and any GPL compliance implications
   ```

4. **Create issue:**
   ```
   Create a GitHub issue for tracking the GPL compliance implications of the OP-TEE secure boot implementation
   ```

### Workflow 3: Improving Scripts

1. **Review current implementation:**
   ```
   Read scripts/analyze.sh and identify potential improvements
   ```

2. **Implement improvements:**
   ```
   Add error handling for when the firmware file is not found
   ```

3. **Test:**
   ```
   Run shellcheck on the updated script and fix any issues
   ```

4. **Commit:**
   ```
   Create a commit with these improvements
   ```

---

## Best Practices

### Documentation Style

Follow the existing documentation patterns:

- Use tables for structured data
- Include "Source" or "Evidence" sections showing how findings were obtained
- Link to related analysis reports
- Include GPL compliance implications when relevant
- Use clear headers and navigation links

**Example:**
```markdown
# Component Name

[← Analysis Reports](SUMMARY.md)

---

**One-line summary**

## Overview

[Description of what this component is]

## Version Details

| Property | Value |
|----------|-------|
| Version | X.Y.Z |
| License | GPL-2.0 |

## Evidence

[How this was found - commands used, files analyzed]

## GPL Compliance

[What must be disclosed]

## See Also

- [Related Analysis](related.md)
```

### Script Style

- Bash: Quote all variables, use `shellcheck`
- Python: Type hints for public APIs, follow PEP 8
- Comments: Explain why, not what
- Output JSON with `_source` and `_method` metadata

### Git Commit Style

Use conventional commits:
```
<type>: <description>

<optional body>

Generated with Claude Code

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

Types: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`

---

## Getting Help

### Project Documentation

- `README.md` - Project overview and quick start
- `CLAUDE.md` - Instructions specifically for Claude Code
- `AGENTS.md` - Instructions for all AI coding agents
- `docs/GPL-COMPLIANCE-ANALYSIS.md` - Main compliance analysis
- `docs/analysis/SUMMARY.md` - Index of all analysis reports

### Claude Code Documentation

- [Claude Code Docs](https://docs.anthropic.com/en/docs/build-with-claude/claude-code)
- [Claude API Documentation](https://docs.anthropic.com/)

### Community

- [GitHub Issues](https://github.com/stvhay/glinet-comet-reverse-gpl/issues) - Bug reports and feature requests
- [GL.iNet Forum Discussion](https://forum.gl-inet.com/t/comet-gl-rm1-and-open-source/55955) - Community discussion about GPL compliance

---

## Troubleshooting

### "Command not found" errors

Make sure you're in the Nix development environment:
```bash
nix develop
# or
direnv allow
```

### Claude doesn't have access to files

Ensure Claude is started from within the project directory:
```bash
cd /path/to/glinet-comet-reverse-gpl
claude
```

### Script fails to find firmware

The firmware is downloaded on first run and cached in `downloads/`. If download fails:
```bash
# Manually download
mkdir -p downloads
cd downloads
wget https://fw.gl-inet.com/kvm/rm1/release/glkvm-RM1-1.7.2-1128-1764344791.img
```

### Cannot commit or push

This is by design. Claude should:
- Never push without explicit permission
- Only commit when asked
- Follow the project's git conventions

---

## Contributing Your Work

### Before Creating a Pull Request

1. **Run tests:**
   ```bash
   shellcheck scripts/*.sh
   pytest tests/ -v
   ```

2. **Review changes:**
   ```bash
   git diff
   ```

3. **Ensure methodology is sound:**
   - All findings traceable to scripts
   - No "magic numbers" without documentation
   - Legal constraints followed (no binaries committed)

### Creating Issues

Use the issue templates:
- **Analysis** - New analysis scripts
- **Infrastructure** - Framework/tooling improvements
- **Bug** - Broken scripts or incorrect results
- **Documentation** - Wiki/docs updates
- **Chore** - Maintenance/refactoring

### Pull Requests

When ready, ask Claude to create a PR:
```
Create a pull request with a summary of the changes we made
```

Claude will:
1. Review all commits since branching
2. Create a comprehensive PR summary
3. Include testing checklist
4. Add appropriate labels

---

## Advanced Usage

### Custom Analysis Scripts

Create new analysis scripts in `scripts/`:

```bash
scripts/
├── analyze.sh           # Main analysis orchestrator
├── extract-firmware.sh  # Firmware extraction
├── analyze-*.sh        # Specific analysis scripts
└── render_template.py   # Documentation renderer
```

**Prompt Claude:**
```
Create a new analysis script scripts/analyze-bootloader.sh that extracts and analyzes the U-Boot bootloader
```

### Jinja2 Documentation Templates

The project uses Jinja2 templates for documentation:

```python
# templates/wiki/Example.md.j2
{% set data = analyze('component') %}
Version: {{ data.version | src }}
{{ render_footnotes() }}
```

**Prompt Claude:**
```
Create a Jinja2 template for the kernel analysis report
```

### JSON Output with Source Metadata

Analysis scripts should output JSON with provenance:

```json
{
  "version": "4.19.111",
  "_source": "/path/to/file",
  "_method": "extracted from vermagic string",
  "_command": "strings kernel.ko | grep vermagic"
}
```

**Prompt Claude:**
```
Update the script to output JSON with _source and _method metadata
```

---

## Examples of Claude-Assisted Analysis

Many reports in this repository were created with Claude Code assistance:

- **[Kernel Version Analysis](analysis/kernel-version.md)** - Extracted kernel version from module metadata
- **[GPL Binaries List](analysis/gpl-binaries.md)** - Identified GPL-licensed executables
- **[Boot Process Analysis](analysis/boot-process.md)** - Documented boot chain from device trees
- **[Device Tree Analysis](analysis/device-trees.md)** - Decompiled and analyzed DTBs
- **[GPL Compliance Analysis](GPL-COMPLIANCE-ANALYSIS.md)** - Comprehensive legal analysis

These demonstrate the level of detail and rigor Claude can help achieve when properly directed.

---

## Summary

Claude Code is a powerful tool for reverse engineering and GPL compliance analysis. By following this guide:

1. Set up your environment properly (Nix + Claude)
2. Provide Claude with relevant context from existing docs
3. Use clear, specific prompts
4. Follow project methodology (scripts over manual analysis)
5. Respect legal constraints (no binaries in repo)
6. Create well-documented, reproducible analysis

**Ready to contribute? Start Claude and try:**
```
Read docs/CLAUDE-CODE-GUIDE.md and docs/analysis/SUMMARY.md, then suggest an analysis task I could work on
```

Happy reversing!
