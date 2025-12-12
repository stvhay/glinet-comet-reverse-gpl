# Claude Code Permissions Guide

This document explains the command permission structure for Claude Code in this repository and how to work effectively within these boundaries.

## Setup

The permissions are configured in `.claude/settings.local.json` (which is gitignored for local customization). To set up:

```bash
# Copy the template to create your local settings
cp .claude/settings.local.json.template .claude/settings.local.json
```

The template contains optimized permissions for this project. You can customize further for your workflow if needed.

## Overview

The `.claude/settings.local.json` file configures which Bash commands Claude Code can execute autonomously versus which require explicit user approval. This balances automation convenience with security.

## Permission Philosophy

**Auto-approved commands:**
- Development tools used in normal workflow (git, nix, pytest, etc.)
- File system operations (mkdir, cp, mv, rm, etc.)
- Text processing utilities (grep, sed, awk, jq, etc.)
- Project-specific analysis tools (binwalk, dtc, etc.)
- Project scripts in `scripts/` directory
- Temporary file operations in `/tmp/`

**Always require approval:**
- `git push` - Prevents accidental remote changes
- Remote access tools (ssh, scp, rsync, sshpass, sftp) - Security boundary

## Auto-Approved Command Patterns

### Version Control (git)

```bash
# All git commands are auto-approved EXCEPT git push
Bash(git:*)

# Examples that work without permission:
git status
git add file.txt
git commit -m "message"
git diff
git log --oneline
git branch new-feature
git checkout -b feature-branch
git stash
git rebase main
```

**Exception:** `git push` is explicitly blocked and requires user confirmation.

### GitHub CLI (gh)

```bash
# All gh commands are auto-approved
Bash(gh:*)

# Examples:
gh issue list
gh pr create --title "Fix bug" --body "Description"
gh issue comment 123 --body "Update"
gh pr view 456
gh workflow run ci.yml
```

### Nix Package Manager

```bash
# All nix commands are auto-approved
Bash(nix:*)

# Examples:
nix develop
nix build
nix flake check
nix shell nixpkgs#hello
nix run nixpkgs#cowsay -- "Hello"
```

### Python Development

```bash
# All Python tooling is auto-approved
Bash(python:*)
Bash(python3:*)
Bash(python311:*)
Bash(pytest:*)
Bash(ruff:*)
Bash(mypy:*)

# Examples:
python3 script.py
pytest tests/ -v
ruff check scripts/
ruff format scripts/
mypy scripts/
```

### Firmware Analysis Tools

```bash
# All firmware reverse engineering tools are auto-approved
Bash(binwalk:*)
Bash(xxd:*)
Bash(dtc:*)
Bash(strings:*)
Bash(file:*)
Bash(hexdump:*)
Bash(unsquashfs:*)
Bash(dd:*)

# Examples:
binwalk firmware.img
dtc -I dtb -O dts device-tree.dtb
strings binary | grep "version"
xxd -l 512 firmware.img
```

### File Operations

```bash
# All standard file operations are auto-approved
Bash(mkdir:*)
Bash(rm:*)
Bash(mv:*)
Bash(cp:*)
Bash(touch:*)
Bash(ln:*)
Bash(chmod:*)
Bash(ls:*)

# Examples:
mkdir -p output/analysis
rm -rf temp/
mv old.txt new.txt
cp -r src/ backup/
chmod +x script.sh
```

### Text Processing

```bash
# All text processing utilities are auto-approved
Bash(cat:*)
Bash(echo:*)
Bash(grep:*)
Bash(sed:*)
Bash(awk:*)
Bash(head:*)
Bash(tail:*)
Bash(wc:*)
Bash(sort:*)
Bash(uniq:*)
Bash(diff:*)
Bash(tr:*)
Bash(cut:*)
Bash(paste:*)
Bash(jq:*)

# Examples:
grep -r "TODO" scripts/
sed -i 's/old/new/g' file.txt
awk '{print $1}' data.txt
jq '.version' package.json
```

### Network Tools

```bash
# Download tools are auto-approved
Bash(curl:*)
Bash(wget:*)

# Examples:
curl -L https://fw.gl-inet.com/firmware.img -o firmware.img
wget https://example.com/file.txt
```

### Shell Utilities

```bash
# Shell execution and utilities are auto-approved
Bash(bash:*)
Bash(sh:*)
Bash(time:*)
Bash(timeout:*)
Bash(find:*)
Bash(xargs:*)

# Examples:
bash -x debug-script.sh
timeout 30 long-running-command
find . -name "*.py" -type f
time pytest tests/
```

### Project Scripts

```bash
# All scripts in the scripts/ directory are auto-approved
Bash(scripts/:*)
Bash(./scripts/:*)
Bash(/Users/hays/Projects/glinet-comet-reversing/scripts/:*)

# Examples:
./scripts/analyze.sh
scripts/analyze-binwalk.py firmware.img
bash -x scripts/render_wiki.sh
```

### Temporary Files

```bash
# All operations in /tmp/ are auto-approved
Bash(/tmp/:*)

# Examples:
echo "test" > /tmp/test.txt
chmod +x /tmp/script.sh
/tmp/test-script.sh
cat /tmp/output.json | jq .
```

## Blocked Commands

These commands ALWAYS require explicit user approval:

```bash
# Remote operations (security boundary)
git push              # Prevents accidental remote changes
ssh user@host         # Remote access
scp file user@host:   # Remote copy
rsync -av local/ remote:/  # Remote sync
sshpass -p pass ssh   # Credential exposure risk
sftp user@host        # Remote file transfer
```

## Best Practices

### For Users

1. **Review the permissions** - Understand what Claude can do autonomously
2. **Grant git push carefully** - Always review commits before approving push
3. **Use /tmp/ for experiments** - Temporary files are auto-approved
4. **Trust project scripts** - Scripts in `scripts/` are part of the codebase

### For Claude Code Agents

1. **Prefer specific tools over Bash** - Use Read/Write/Edit instead of cat/echo
2. **Use parallel operations** - Run independent commands in one message
3. **Chain dependent commands** - Use `&&` for sequential operations
4. **Avoid needless permissions** - Don't use Bash for file operations

### Command Chaining Examples

```bash
# Good: Chain dependent operations
git add . && git commit -m "feat: Add feature" && git status

# Good: Parallel independent commands (use multiple Bash calls)
# Call 1: git status
# Call 2: git diff
# Call 3: pytest tests/

# Bad: Don't use semicolons unless failures are acceptable
git add . ; git commit  # Bad: commit runs even if add fails
```

## How Permissions Work

The permission system uses glob patterns to match Bash commands:

- `Bash(git:*)` - Matches any command starting with "git"
- `Bash(scripts/:*)` - Matches any command starting with "scripts/"
- `Bash(/tmp/:*)` - Matches any command starting with "/tmp/"

### Pattern Matching Rules

1. **Command prefix matching** - `Bash(git:*)` matches `git status`, `git add`, etc.
2. **Path matching** - `Bash(scripts/:*)` matches `scripts/analyze.sh`, etc.
3. **Wildcards** - `:*` means "followed by anything"
4. **Exact matches** - `Bash(git push)` matches only `git push` (no wildcards)

## Updating Permissions

If you find yourself frequently approving the same command pattern:

1. Identify the common prefix (e.g., `newcommand`)
2. Add `Bash(newcommand:*)` to the allow list in `.claude/settings.local.json`
3. Commit the change with a clear explanation

### Template for Adding Permissions

```json
{
  "permissions": {
    "allow": [
      "Bash(your-new-command:*)"
    ]
  }
}
```

## Security Considerations

### Why git push is blocked

Pushing to remote requires explicit user approval because:
- It permanently modifies the remote repository
- It can affect other collaborators
- It should be reviewed and deliberate
- User maintains control over when changes go public

### Why remote access is blocked

SSH/SCP/RSYNC require approval because:
- They access external systems
- They may transmit credentials
- They create security audit trails
- User should be aware of all remote operations

### Safe patterns

These patterns are considered safe for auto-approval:
- Local file system operations
- Read-only network operations (curl, wget)
- Development tools that don't modify remote state
- Temporary file operations
- Project-specific scripts (reviewed in the repository)

## Optimization History

### Previous State (108 rules)

The original settings.local.json had 108 individual rules including:
- Separate rules for each git subcommand (add, commit, status, etc.)
- Duplicate path variations (./scripts/, scripts/, absolute paths)
- One-off temporary file permissions
- Verbose issue update heredocs embedded in permissions

### Optimized State (57 rules)

Reduced to 57 rules by:
- Consolidating `git add`, `git commit`, etc. → `Bash(git:*)`
- Merging all Python variants → `Bash(python:*)`, `Bash(python3:*)`, etc.
- Using path prefixes → `Bash(scripts/:*)`, `Bash(/tmp/:*)`
- Removing one-off temporary commands
- Eliminating redundant specific cases covered by wildcards

### Benefits

- **47% fewer rules** (108 → 57)
- **Easier to understand** - Clear categories vs. scattered specifics
- **More maintainable** - Add tool categories, not individual commands
- **Better coverage** - Wildcards catch new commands automatically
- **Clearer intent** - Categories express purpose, not history

## Common Workflows

### Making a commit

```bash
# All auto-approved (except push)
git status
git add .
git commit -m "feat: Add feature"
git log --oneline -1

# Requires approval
git push  # User must explicitly approve
```

### Running analysis

```bash
# All auto-approved
./scripts/analyze.sh
binwalk firmware.img
dtc -I dtb -O dts device.dtb
jq . output.json
```

### Testing changes

```bash
# All auto-approved
pytest tests/ -v
ruff check scripts/
shellcheck scripts/*.sh
nix flake check
```

### Creating a PR

```bash
# Auto-approved
git checkout -b feature-branch
git add .
git commit -m "feat: Add feature"

# Requires approval
git push -u origin feature-branch

# Auto-approved
gh pr create --title "Add feature" --body "Description"
```

## Troubleshooting

### "Permission required" for approved command

If Claude asks permission for a command that should be auto-approved:

1. Check the exact command - wildcards match prefixes, not substrings
2. Verify the pattern in `.claude/settings.local.json`
3. Ensure the command starts with the allowed prefix
4. Consider if the command needs a more specific pattern

### Adding a new tool

To add a new development tool (e.g., `rg` for ripgrep):

```json
{
  "permissions": {
    "allow": [
      "Bash(rg:*)"
    ]
  }
}
```

Then commit the change:

```bash
git add .claude/settings.local.json
git commit -m "chore: Add rg (ripgrep) to auto-approved commands"
```

## FAQ

**Q: Why not approve everything?**
A: Security boundaries prevent accidental damage (git push, ssh, etc.)

**Q: Can I customize for my fork?**
A: Yes! `.claude/settings.local.json` is checked in, so customize it for your workflow

**Q: What if I need git push autonomy?**
A: Remove `Bash(git push:*)` from the block list (not recommended for shared repos)

**Q: Why are there multiple script path patterns?**
A: Covers variations: `scripts/`, `./scripts/`, absolute paths - ensures commands work from any invocation style

**Q: Can patterns overlap?**
A: Yes. More specific patterns can override general ones in the allow/block lists

**Q: What about commands not listed?**
A: Unlisted commands require explicit approval on first use

## Related Documentation

- `.claude/settings.local.json` - The actual permission configuration
- `CLAUDE.md` - Project-specific Claude Code guidance
- `AGENTS.md` - Subagent delegation patterns
