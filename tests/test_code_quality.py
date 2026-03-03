#!/usr/bin/env python3
"""Code quality tests - linting and formatting checks as pytest tests.

These tests ensure code quality standards are met before commits/pushes.
Running pytest will now validate all code quality checks.
"""

import subprocess
from pathlib import Path
from typing import ClassVar

import pytest


class TestCodeFormatting:
    """Test that code is properly formatted."""

    def test_ruff_format_check(self) -> None:
        """Test that all Python files are formatted with ruff."""
        result = subprocess.run(
            ["ruff", "format", "--check", "scripts/", "tests/"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            pytest.fail(
                f"Code formatting check failed:\n{result.stdout}\nRun: ruff format scripts/ tests/"
            )


class TestCodeLinting:
    """Test that code passes linting checks."""

    def test_ruff_linting(self) -> None:
        """Test that all Python files pass ruff linting."""
        result = subprocess.run(
            ["ruff", "check", "scripts/", "tests/"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            pytest.fail(
                f"Linting check failed:\n{result.stdout}\nRun: ruff check --fix scripts/ tests/"
            )


class TestSkillsWhitelist:
    """Test that .gitignore whitelist tracks exactly the expected skill files."""

    EXPECTED_SKILLS: ClassVar[list[str]] = [
        "brainstorming",
        "code-simplification",
        "dispatching-parallel-agents",
        "executing-plans",
        "finishing-a-development-branch",
        "receiving-code-review",
        "requesting-code-review",
        "subagent-driven-development",
        "systematic-debugging",
        "test-driven-development",
        "using-git-worktrees",
        "verification-before-completion",
        "writing-clearly-and-concisely",
        "writing-plans",
        "writing-skills",
    ]

    def test_tracked_skill_directories(self) -> None:
        """Test that git tracks exactly the expected skill directories."""
        result = subprocess.run(
            ["git", "ls-files", ".claude/skills/"],
            capture_output=True,
            text=True,
            check=True,
        )
        tracked_files = result.stdout.strip().splitlines()

        # Extract unique top-level entries (directories and standalone files)
        tracked_dirs = sorted(
            {
                f.replace(".claude/skills/", "").split("/")[0]
                for f in tracked_files
                if "/" in f.replace(".claude/skills/", "")
            }
        )

        assert tracked_dirs == sorted(self.EXPECTED_SKILLS), (
            f"Tracked skill directories don't match expected.\n"
            f"  Extra: {set(tracked_dirs) - set(self.EXPECTED_SKILLS)}\n"
            f"  Missing: {set(self.EXPECTED_SKILLS) - set(tracked_dirs)}"
        )

    def test_upstream_file_tracked(self) -> None:
        """Test that UPSTREAM-superpowers.md is tracked."""
        result = subprocess.run(
            ["git", "ls-files", ".claude/skills/UPSTREAM-superpowers.md"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == ".claude/skills/UPSTREAM-superpowers.md"

    def test_tracked_file_count(self) -> None:
        """Test that total tracked skill file count matches expectations."""
        result = subprocess.run(
            ["git", "ls-files", ".claude/skills/"],
            capture_output=True,
            text=True,
            check=True,
        )
        tracked_files = result.stdout.strip().splitlines()
        # 15 skill directories with their files + UPSTREAM-superpowers.md
        assert len(tracked_files) >= 40, (
            f"Expected at least 40 tracked skill files, got {len(tracked_files)}"
        )


class TestShellScripts:
    """Test that shell scripts pass shellcheck."""

    def test_shellcheck(self) -> None:
        """Test that all bash scripts pass shellcheck."""
        # Find all .sh files in scripts/
        script_dir = Path(__file__).parent.parent / "scripts"
        shell_scripts = list(script_dir.glob("*.sh"))

        if not shell_scripts:
            pytest.skip("No shell scripts found")

        result = subprocess.run(
            ["shellcheck"] + [str(s) for s in shell_scripts],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            pytest.fail(f"Shellcheck failed:\n{result.stdout}\n{result.stderr}")
