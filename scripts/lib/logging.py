"""Shared logging utilities for analysis scripts.

This module provides colored logging functions that output to stderr.
"""

import sys

# Color codes for stderr logging
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
NC = "\033[0m"  # No Color


def info(msg: str) -> None:
    """Log info message to stderr."""
    print(f"{GREEN}[INFO]{NC} {msg}", file=sys.stderr)


def warn(msg: str) -> None:
    """Log warning message to stderr."""
    print(f"{YELLOW}[WARN]{NC} {msg}", file=sys.stderr)


def error(msg: str) -> None:
    """Log error message to stderr."""
    print(f"{RED}[ERROR]{NC} {msg}", file=sys.stderr)


def success(msg: str) -> None:
    """Log success message to stderr."""
    print(f"{GREEN}[OK]{NC} {msg}", file=sys.stderr)


def section(msg: str) -> None:
    """Log section header to stderr."""
    print(f"\n{BLUE}=== {msg} ==={NC}", file=sys.stderr)
