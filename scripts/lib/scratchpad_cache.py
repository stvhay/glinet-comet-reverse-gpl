#!/usr/bin/env python3
"""Scratchpad cache utilities for fast, atomic updates.

This module provides simple functions to update scratchpad cache files,
which are then rendered into the full scratchpad.md by generate_scratchpad.sh.

Design principles:
- Updates must be trivial (single function call, <100ms)
- Each cache file is single-purpose (atomic updates)
- Simple text format (no JSON parsing overhead)
- Safe for concurrent access (atomic writes)

Usage:
    from lib.scratchpad_cache import update_current_work, update_timestamp

    # Fast update (just 2 function calls)
    update_current_work("Implementing CA #3 - pre-commit hook")
    update_timestamp()
"""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

# Cache directory
CACHE_DIR = Path("/tmp/claude-glinet-comet-reversing/.scratchpad-cache")


def _atomic_write(file_path: Path, content: str) -> None:
    """Write content to file atomically.

    Args:
        file_path: Path to file
        content: Content to write

    Uses temp file + rename for atomic update.
    """
    # Ensure cache directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file
    with tempfile.NamedTemporaryFile(
        mode="w", dir=file_path.parent, delete=False, suffix=".tmp"
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    # Atomic rename
    tmp_path.replace(file_path)


def update_timestamp() -> None:
    """Update last-updated timestamp to current UTC time.

    File: .scratchpad-cache/last-updated.txt
    Format: YYYY-MM-DD HH:MM UTC

    Example:
        update_timestamp()
        # Writes: "2025-12-13 01:00 UTC"
    """
    now = datetime.now(UTC)
    timestamp = now.strftime("%Y-%m-%d %H:%M UTC")
    _atomic_write(CACHE_DIR / "last-updated.txt", timestamp)


def update_current_work(description: str) -> None:
    """Update current work description.

    Args:
        description: Brief description of current work (single line)

    File: .scratchpad-cache/current-work.txt

    Example:
        update_current_work("Implementing CA #3 - pre-commit hook")
    """
    _atomic_write(CACHE_DIR / "current-work.txt", description.strip())


def add_completion(completion: str) -> None:
    """Add completed item to completions list.

    Args:
        completion: Completion entry (markdown format)

    File: .scratchpad-cache/completions.txt (append mode)

    Example:
        add_completion("✅ Issue #31 - BaseScript enhancement (CLOSED)")
    """
    completions_file = CACHE_DIR / "completions.txt"
    completions_file.parent.mkdir(parents=True, exist_ok=True)

    with completions_file.open("a") as f:
        f.write(f"{completion.strip()}\n")


def add_commit(commit_hash: str, commit_msg: str) -> None:
    """Add commit to recent commits list.

    Args:
        commit_hash: Short commit hash (7 chars)
        commit_msg: Commit message

    File: .scratchpad-cache/commits.txt (append mode, keep last 9)

    Example:
        add_commit("abc1234", "feat: Implement CA #3")
    """
    commits_file = CACHE_DIR / "commits.txt"
    commits_file.parent.mkdir(parents=True, exist_ok=True)

    # Read existing commits
    commits = commits_file.read_text().strip().split("\n") if commits_file.exists() else []

    # Add new commit
    commits.append(f"{commit_hash} - {commit_msg}")

    # Keep only last 9
    commits = commits[-9:]

    # Write back
    _atomic_write(commits_file, "\n".join(commits) + "\n")


def set_session_info(start_time: str, description: str) -> None:
    """Set session start information.

    Args:
        start_time: Session start time (UTC)
        description: Session description/goals

    File: .scratchpad-cache/session.txt

    Example:
        set_session_info("2025-12-13 00:00 UTC", "Implementing P5 corrective actions")
    """
    content = f"Start: {start_time}\nDescription: {description}\n"
    _atomic_write(CACHE_DIR / "session.txt", content)


def clear_completions() -> None:
    """Clear completions list (use at session start)."""
    _atomic_write(CACHE_DIR / "completions.txt", "")


def get_cache_dir() -> Path:
    """Get cache directory path.

    Returns:
        Path to cache directory
    """
    return CACHE_DIR


# Convenience function for most common update pattern
def update(work: str) -> None:
    """Update both current work and timestamp (most common pattern).

    Args:
        work: Current work description

    Example:
        update("Implementing CA #3")
        # Equivalent to:
        # update_current_work("Implementing CA #3")
        # update_timestamp()
    """
    update_current_work(work)
    update_timestamp()


if __name__ == "__main__":
    # Example usage
    print("Scratchpad cache example:")
    print(f"Cache directory: {CACHE_DIR}")

    # Fast update example
    update("Testing cache system")
    print(f"Updated: {(CACHE_DIR / 'current-work.txt').read_text().strip()}")
    print(f"Timestamp: {(CACHE_DIR / 'last-updated.txt').read_text().strip()}")
