# Claude Code Live Status - GitHub Gist

Real-time status page showing Claude's current work progress via GitHub Gist.

## Quick Start

### 1. Create the Status Gist (One-Time)

```bash
./scripts/create-status-gist.sh
```

This creates a public gist and saves the ID to `/tmp/claude-glinet-comet-reversing/gist-id.txt`.

You'll get a URL like: `https://gist.github.com/stvhay/abc123...`

### 2. Start Auto-Updates (During Claude Sessions)

In a separate terminal:

```bash
./scripts/update-status-gist-loop.sh
```

This updates the gist every 30 seconds while Claude is working.

### 3. Enable Browser Auto-Refresh

**Chrome/Edge:**
1. Install: [Auto Refresh](https://chrome.google.com/webstore/detail/auto-refresh/ifooldnmmcmlbdennkpdnlnbgbmfalko)
2. Open your gist URL
3. Set refresh interval: 30 seconds

**Firefox:**
1. Install: [Auto Refresh](https://addons.mozilla.org/en-US/firefox/addon/auto-refresh/)
2. Open your gist URL
3. Set refresh interval: 30 seconds

## How It Works

```
┌─────────────────────────┐
│ Claude Code Session     │
│ Updates scratchpad      │
│ /tmp/claude-*/          │
│ scratchpad.md           │
└───────────┬─────────────┘
            │ Reads every 30s
            ▼
┌─────────────────────────┐
│ update-status-gist.sh   │
│ - Adds timestamp        │
│ - Adds header/footer    │
│ - Calls: gh gist edit   │
└───────────┬─────────────┘
            │ GitHub API
            ▼
┌─────────────────────────┐
│ GitHub Gist             │
│ (claude-status.md)      │◄──── Browser auto-refresh
│ Public, instantly       │      (30 seconds)
│ updated                 │
└─────────────────────────┘
```

## Files & Components

### Scratchpad
- **Location:** `/tmp/claude-glinet-comet-reversing/scratchpad.md`
- **Updated by:** Claude Code during sessions
- **Contains:** Task list, progress, current work

### Scripts

**create-status-gist.sh** - One-time setup
- Creates public gist with scratchpad content
- Saves gist ID to `/tmp/claude-glinet-comet-reversing/gist-id.txt`

**update-status-gist.sh** - Single update
- Reads scratchpad
- Enhances with timestamp, header, footer
- Updates gist via `gh gist edit`

**update-status-gist-loop.sh** - Auto-update
- Runs update script every 30 seconds
- Displays status in terminal
- Press Ctrl+C to stop

### Gist ID File
- **Location:** `/tmp/claude-glinet-comet-reversing/gist-id.txt`
- **Contains:** GitHub gist ID (e.g., `abc123def456...`)
- **Purpose:** Persistence across update cycles

## Manual Updates

Update anytime without the loop:

```bash
./scripts/update-status-gist.sh
```

## Viewing the Status

Your gist URL (from create script output):
```
https://gist.github.com/stvhay/YOUR_GIST_ID
```

Or find all your gists:
```bash
gh gist list
```

## Stopping Auto-Updates

If running the loop script, press **Ctrl+C** in that terminal.

Or kill the process:
```bash
pkill -f update-status-gist-loop
```

## Troubleshooting

**"Gist not created yet" error:**
```bash
# Run the create script first
./scripts/create-status-gist.sh
```

**"Scratchpad not found" error:**
- Claude creates it during active sessions
- Only exists at: `/tmp/claude-glinet-comet-reversing/scratchpad.md`
- Start a Claude Code session to create it

**"gh: command not found":**
```bash
# Install GitHub CLI
brew install gh  # macOS
# OR
nix profile install nixpkgs#gh  # Nix
```

**Authentication issues:**
```bash
# Login to GitHub CLI
gh auth login
```

## Integration with Wiki

You can link to the gist from your wiki:

```markdown
[📊 Live Claude Status](https://gist.github.com/stvhay/YOUR_GIST_ID)
```

Or embed it (if wiki allows iframes):
```markdown
<script src="https://gist.github.com/stvhay/YOUR_GIST_ID.js"></script>
```

## Benefits

✅ **No authentication hassles** - Uses `gh` CLI (already authenticated)
✅ **Instant updates** - GitHub API is fast
✅ **No git repo needed** - Pure API-driven
✅ **Public & shareable** - Anyone can view status
✅ **Crash recovery** - Scratchpad survives crashes
✅ **Clean URLs** - Readable gist.github.com links

## Example Output

```markdown
# Claude Code Live Status

**Last Updated:** 2025-12-12 12:45:30 PM EST

## Progress Status (Epic #51)
- ✅ Issue #52 - Date typo fix (CLOSED)
- ✅ Issue #54 - Work-hour triggers (CLOSED)
- ⏳ Issue #55 - Baseline management review (NEXT)
```

---

**Pro tip:** Keep the gist URL bookmarked for quick access during long Claude sessions!
