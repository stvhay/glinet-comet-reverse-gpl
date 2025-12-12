#!/usr/bin/env python3
"""
Redact sensitive information from command logs.

Usage:
    ./scripts/redact-command-log.py < input.log > output.log
    cat input.log | ./scripts/redact-command-log.py
"""

import re
import sys

# Redaction patterns: (regex, replacement, optional_flags)
REDACTION_PATTERNS: list[tuple[str, str, int]] = [
    # GitHub tokens (flexible length to handle variations)
    (r"ghp_[a-zA-Z0-9]{34,40}", "[REDACTED:GITHUB_TOKEN]", 0),
    (r"gho_[a-zA-Z0-9]{34,40}", "[REDACTED:GITHUB_OAUTH]", 0),
    (r"ghs_[a-zA-Z0-9]{34,40}", "[REDACTED:GITHUB_SECRET]", 0),
    (r"github_pat_[a-zA-Z0-9_]{80,85}", "[REDACTED:GITHUB_PAT]", 0),
    # AWS keys (before generic patterns)
    (r"AKIA[0-9A-Z]{16}", "[REDACTED:AWS_ACCESS_KEY]", 0),
    (
        r"(?i)aws[_-]?secret[_-]?access[_-]?key['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{40}",
        "[REDACTED:AWS_SECRET_KEY]",
        0,
    ),
    # SSH keys in URLs (before email pattern)
    (r"ssh://[^@]+@", "ssh://[REDACTED]@", 0),
    # HTTP basic auth (before email pattern) - handles passwords with @ symbol
    (r"https?://([^:]+:)([^/]+)(@[^/@\s]+)", r"https://[REDACTED]:[REDACTED]\3", 0),
    # Passwords and secrets (exclude already-redacted values)
    (r"(?i)(password|passwd|pwd|secret)=(?!\[REDACTED)[^\s]+", r"\1=[REDACTED]", 0),
    (r"(?i)(api[_-]?key|apikey|token)=(?!\[REDACTED)[^\s]+", r"\1=[REDACTED]", 0),
    # Private keys
    (
        r"-----BEGIN [A-Z ]+ PRIVATE KEY-----.*?-----END [A-Z ]+ PRIVATE KEY-----",
        "[REDACTED:PRIVATE_KEY]",
        re.DOTALL,
    ),
    # Email addresses (but not in URLs or after redactions)
    (
        r"(?<![:/@])([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b",
        "[REDACTED:EMAIL]",
        0,
    ),
    # Personal paths (home directories)
    (r"/Users/[^/\s]+", "/Users/[REDACTED]", 0),
    (r"/home/[^/\s]+", "/home/[REDACTED]", 0),
]


def redact_line(line: str) -> str:
    """
    Redact sensitive information from a single line.

    Args:
        line: Input line potentially containing sensitive data

    Returns:
        Line with sensitive information redacted
    """
    for pattern, replacement, *flags in REDACTION_PATTERNS:
        if flags:
            line = re.sub(pattern, replacement, line, flags=flags[0])
        else:
            line = re.sub(pattern, replacement, line)
    return line


def main() -> None:
    """Read from stdin, redact, write to stdout."""
    for line in sys.stdin:
        print(redact_line(line), end="")


if __name__ == "__main__":
    main()
