#!/usr/bin/env python3
"""Code quality tests - linting and formatting checks as pytest tests.

These tests ensure code quality standards are met before commits/pushes.
Running pytest will now validate all code quality checks.
"""

import subprocess
from pathlib import Path

import pytest


class TestCodeFormatting:
    """Test that code is properly formatted."""

    def test_ruff_format_check(self):
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

    def test_ruff_linting(self):
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


class TestShellScripts:
    """Test that shell scripts pass shellcheck."""

    def test_shellcheck(self):
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
