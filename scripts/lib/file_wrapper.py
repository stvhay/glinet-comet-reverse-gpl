#!/usr/bin/env python3
"""File modification wrapper with cache enforcement and conformance checking.

This module provides wrapped file operations that enforce:
1. Cache update BEFORE modification (P5 compliance)
2. Issue conformance check (work must be tracked)
3. Automatic commit with incremental message
4. Automatic gist push for scratchpad sync

IMPORTANT: After this module is implemented, ALL file modifications must use
these wrappers. Direct file edits are a non-conformance.

Usage:
    from lib.file_wrapper import wrapped_edit, wrapped_write

    # For each file modification (issue_number is REQUIRED)
    wrapped_edit(
        issue_number=71,
        work_description="Fix typo in README",
        file_path="README.md",
        old_string="old text",
        new_string="new text"
    )

    # Wrapper handles: cache update, conformance check, commit, gist push
    # If issue_number is not provided or invalid, ConformanceError is raised
"""

import subprocess
from pathlib import Path

from scripts.lib.scratchpad_cache import CACHE_DIR, update

# Git configuration
REPO_ROOT = Path("/Users/hays/Projects/glinet-comet-reversing")
GIST_UPDATE_SCRIPT = REPO_ROOT / "scripts" / "update-status-gist.py"


class ConformanceError(Exception):
    """Raised when file modification violates conformance rules."""

    pass


def set_current_issue(issue_number: int, issue_title: str) -> None:
    """Set the current issue being worked on.

    Args:
        issue_number: GitHub issue number
        issue_title: Brief issue title/description

    Creates cache entry that tracks active issue for conformance checking.

    Example:
        set_current_issue(71, "Scratchpad staleness corrective action")
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    issue_file = CACHE_DIR / "current-issue.txt"

    content = f"{issue_number}\n{issue_title}\n"
    issue_file.write_text(content)

    # Update scratchpad to reflect new issue
    update(f"Issue #{issue_number}: {issue_title}")

    print(f"✅ Current issue set: #{issue_number} - {issue_title}")


def get_current_issue() -> tuple[int, str] | None:
    """Get the current issue being worked on.

    Returns:
        (issue_number, issue_title) tuple, or None if no issue set
    """
    issue_file = CACHE_DIR / "current-issue.txt"

    if not issue_file.exists():
        return None

    lines = issue_file.read_text().strip().split("\n")
    EXPECTED_LINE_COUNT = 2  # issue_number and issue_title
    if len(lines) < EXPECTED_LINE_COUNT:
        return None

    try:
        issue_number = int(lines[0])
        issue_title = lines[1]
        return (issue_number, issue_title)
    except (ValueError, IndexError):
        return None


def _check_conformance() -> tuple[int, str]:
    """Check that current work is tracked (conformance requirement).

    Returns:
        (issue_number, issue_title) tuple

    Raises:
        ConformanceError: If no issue is currently tracked
    """
    current_issue = get_current_issue()

    if current_issue is None:
        raise ConformanceError(
            "CONFORMANCE VIOLATION: No current issue set.\n"
            "Before modifying files, you must set the current issue:\n"
            "  set_current_issue(issue_number, issue_title)\n"
            "\n"
            "This ensures all work is tracked and traceable."
        )

    return current_issue


def _regenerate_scratchpad() -> None:
    """Regenerate scratchpad from cache."""
    script = REPO_ROOT / "scripts" / "generate-scratchpad.sh"
    subprocess.run([str(script)], check=True, capture_output=True)


def _push_gist() -> None:
    """Push updated scratchpad to GitHub gist."""
    if not GIST_UPDATE_SCRIPT.exists():
        print("⚠️  Gist update script not found, skipping gist push")
        return

    try:
        subprocess.run([str(GIST_UPDATE_SCRIPT)], check=True, capture_output=True)
        print("✅ Gist updated successfully")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Gist update failed: {e}")
        print("   (Continuing anyway - gist sync is non-critical)")


def _git_commit_and_push(file_path: str, commit_message: str) -> None:
    """Commit file change and push to remote.

    Args:
        file_path: Path to modified file (relative to repo root)
        commit_message: Commit message
    """
    # Add file
    subprocess.run(["git", "add", file_path], cwd=REPO_ROOT, check=True, capture_output=True)

    # Commit with conventional commit format + Claude attribution
    full_message = (
        f"{commit_message}\n\n"
        "🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\n"
        "Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
    )

    subprocess.run(
        ["git", "commit", "-m", full_message], cwd=REPO_ROOT, check=True, capture_output=True
    )

    # Push to remote
    subprocess.run(["git", "push"], cwd=REPO_ROOT, check=True, capture_output=True)

    print(f"✅ Committed and pushed: {commit_message}")


def wrapped_edit(
    issue_number: int,
    work_description: str,
    file_path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
    commit_message: str | None = None,
) -> None:
    """Edit file with cache enforcement, conformance check, and auto-commit.

    Args:
        issue_number: GitHub issue number (REQUIRED - blocks if not provided)
        work_description: Description of work being done (for cache update)
        file_path: Path to file (absolute or relative to repo root)
        old_string: Text to replace
        new_string: Replacement text
        replace_all: Replace all occurrences (default: False)
        commit_message: Commit message (auto-generated if None)

    Raises:
        ConformanceError: If issue_number is not provided or invalid
        ValueError: If issue_number is not a positive integer

    Example:
        wrapped_edit(
            issue_number=71,
            work_description="Fix typo in README",
            file_path="README.md",
            old_string="recieve",
            new_string="receive"
        )
        # Automatically commits and pushes - no bypass allowed
    """
    # 1. Conformance check: issue_number must be provided and valid
    if not isinstance(issue_number, int) or issue_number <= 0:
        raise ConformanceError(
            f"CONFORMANCE VIOLATION: Invalid issue_number={issue_number}\n"
            "All file modifications MUST be associated with a valid GitHub issue.\n"
            "Provide issue_number as a positive integer."
        )

    # 2. Update cache BEFORE modification (P5 enforcement)
    update(f"Issue #{issue_number}: {work_description}")

    # 2. Perform file modification
    file_abs = Path(file_path)
    if not file_abs.is_absolute():
        file_abs = REPO_ROOT / file_path

    if not file_abs.exists():
        raise FileNotFoundError(f"File not found: {file_abs}")

    content = file_abs.read_text()

    if replace_all:
        new_content = content.replace(old_string, new_string)
    else:
        # Single replacement
        if content.count(old_string) == 0:
            raise ValueError(f"old_string not found in file: {old_string[:50]}...")
        if content.count(old_string) > 1:
            raise ValueError(
                f"old_string appears {content.count(old_string)} times. "
                "Use replace_all=True or provide more context."
            )
        new_content = content.replace(old_string, new_string, 1)

    file_abs.write_text(new_content)
    print(f"✅ Modified: {file_path}")

    # 3. Regenerate scratchpad (cache was updated in step 1)
    _regenerate_scratchpad()

    # 4. Auto-commit (ALWAYS - no bypass)
    if commit_message is None:
        # Auto-generate commit message
        file_name = Path(file_path).name
        commit_message = f"edit: {work_description} ({file_name})"

    _git_commit_and_push(str(file_path), commit_message)

    # 5. Push gist
    _push_gist()


def wrapped_write(
    issue_number: int,
    work_description: str,
    file_path: str,
    content: str,
    commit_message: str | None = None,
) -> None:
    """Write file with cache enforcement, conformance check, and auto-commit.

    Args:
        issue_number: GitHub issue number (REQUIRED - blocks if not provided)
        work_description: Description of work being done (for cache update)
        file_path: Path to file (absolute or relative to repo root)
        content: File content to write
        commit_message: Commit message (auto-generated if None)

    Raises:
        ConformanceError: If issue_number is not provided or invalid

    Example:
        wrapped_write(
            issue_number=71,
            work_description="Create new analysis script",
            file_path="scripts/analyze_new.py",
            content="#!/usr/bin/env python3\\n..."
        )
        # Automatically commits and pushes - no bypass allowed
    """
    # 1. Conformance check: issue_number must be provided and valid
    if not isinstance(issue_number, int) or issue_number <= 0:
        raise ConformanceError(
            f"CONFORMANCE VIOLATION: Invalid issue_number={issue_number}\n"
            "All file modifications MUST be associated with a valid GitHub issue.\n"
            "Provide issue_number as a positive integer."
        )

    # 2. Update cache BEFORE modification (P5 enforcement)
    update(f"Issue #{issue_number}: {work_description}")

    # 2. Perform file write
    file_abs = Path(file_path)
    if not file_abs.is_absolute():
        file_abs = REPO_ROOT / file_path

    file_abs.parent.mkdir(parents=True, exist_ok=True)
    file_abs.write_text(content)

    is_new = "Created" if not file_abs.exists() else "Updated"
    print(f"✅ {is_new}: {file_path}")

    # 3. Regenerate scratchpad (cache was updated in step 1)
    _regenerate_scratchpad()

    # 4. Auto-commit (ALWAYS - no bypass)
    if commit_message is None:
        # Auto-generate commit message
        file_name = Path(file_path).name
        action = "feat" if is_new == "Created" else "edit"
        commit_message = f"{action}: {work_description} ({file_name})"

    _git_commit_and_push(str(file_path), commit_message)

    # 5. Push gist
    _push_gist()


def clear_current_issue() -> None:
    """Clear current issue (use at end of issue work)."""
    issue_file = CACHE_DIR / "current-issue.txt"
    if issue_file.exists():
        issue_file.unlink()

    update("No active issue")
    print("✅ Current issue cleared")


if __name__ == "__main__":
    # Example usage
    print("File Wrapper Example:")
    print("=" * 60)

    # Check current issue
    current = get_current_issue()
    if current:
        print(f"Current issue: #{current[0]} - {current[1]}")
    else:
        print("No current issue set")

    print("\nTo use:")
    print("  1. set_current_issue(issue_num, title)")
    print("  2. wrapped_edit(...) or wrapped_write(...)")
    print("  3. Wrapper handles: cache, conformance, commit, gist")
