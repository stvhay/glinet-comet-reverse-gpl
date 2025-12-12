#!/usr/bin/env python3
"""Firmware extraction and string parsing utilities.

This module provides reusable functions for extracting and analyzing binary data
from firmware files. All functions handle errors gracefully and return empty results
on failure.
"""

import gzip
import re
import subprocess
from pathlib import Path

# String extraction constants
MIN_STRING_LENGTH = 4  # Minimum length for extracted strings (matching GNU strings default)
ASCII_PRINTABLE_MIN = 32  # Space character
ASCII_PRINTABLE_MAX = 126  # Tilde character


def extract_gzip_at_offset(
    firmware: Path,
    offset: int,
    size: int,
    use_dd: bool = True,
) -> bytes | None:
    """Extract and decompress gzip data at firmware offset.

    Args:
        firmware: Path to firmware file
        offset: Byte offset to start reading (decimal)
        size: Number of bytes to read
        use_dd: If True, use dd|gunzip pipeline (more robust for embedded gzip).
               If False, use Python gzip.decompress (faster but less tolerant).

    Returns:
        Decompressed data as bytes, or None if extraction/decompression fails

    Example:
        >>> data = extract_gzip_at_offset(Path("firmware.img"), 0x8000, 500000)
        >>> if data:
        ...     print(f"Extracted {len(data)} bytes")
    """
    if use_dd:
        # Use dd | gunzip pipeline (matches bash script approach)
        # More robust for handling embedded gzip in binary files
        return _extract_gzip_with_dd(firmware, offset, size)

    # Use Python gzip module (faster but less tolerant of edge cases)
    return _extract_gzip_with_python(firmware, offset, size)


def _extract_gzip_with_dd(firmware: Path, offset: int, size: int) -> bytes | None:
    """Extract gzip data using dd | gunzip pipeline."""
    try:
        dd_cmd = [
            "dd",
            f"if={firmware}",
            "bs=1",
            f"skip={offset}",
            f"count={size}",
        ]

        gunzip_cmd = ["gunzip"]

        # Run dd | gunzip pipeline
        dd_proc = subprocess.Popen(
            dd_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        gunzip_proc = subprocess.Popen(
            gunzip_cmd,
            stdin=dd_proc.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        # Close dd's stdout to allow it to receive SIGPIPE if gunzip exits
        if dd_proc.stdout:
            dd_proc.stdout.close()

        # Get decompressed output
        decompressed_data, _ = gunzip_proc.communicate()

        # Wait for both processes
        dd_proc.wait()

        return decompressed_data if decompressed_data else None

    except Exception:
        return None


def _extract_gzip_with_python(firmware: Path, offset: int, size: int) -> bytes | None:
    """Extract gzip data using Python gzip module."""
    try:
        # Read compressed data
        with firmware.open("rb") as f:
            f.seek(offset)
            compressed_data = f.read(size)

        # Return None if no data to decompress
        if not compressed_data:
            return None

        # Decompress
        decompressed = gzip.decompress(compressed_data)
        return decompressed if decompressed else None

    except (OSError, gzip.BadGzipFile):
        return None


def extract_strings(
    data: bytes,
    min_length: int = MIN_STRING_LENGTH,
) -> list[str]:
    """Extract printable strings from binary data.

    Args:
        data: Binary data to extract strings from
        min_length: Minimum string length to include (default: 4)

    Returns:
        List of extracted strings (ASCII only)

    Example:
        >>> data = b"Hello\\x00\\x01\\x02World\\x00"
        >>> extract_strings(data)
        ['Hello', 'World']
    """
    if not data:
        return []

    strings = []
    current = []

    for byte in data:
        if ASCII_PRINTABLE_MIN <= byte <= ASCII_PRINTABLE_MAX:
            current.append(chr(byte))
        else:
            if len(current) >= min_length:
                strings.append("".join(current))
            current = []

    # Don't forget the last string
    if len(current) >= min_length:
        strings.append("".join(current))

    return strings


def filter_strings(
    strings: list[str],
    keywords: list[str] | None = None,
    regex: str | None = None,
    regex_patterns: list[str] | None = None,
    case_sensitive: bool = False,
) -> list[str]:
    """Filter strings by keywords or regex patterns.

    Args:
        strings: List of strings to filter
        keywords: List of keywords to search for (OR logic)
        regex: Single regex pattern to match
        regex_patterns: List of regex patterns to match (OR logic)
        case_sensitive: Whether to perform case-sensitive matching

    Returns:
        Sorted unique list of matching strings

    Example:
        >>> strings = ["version 1.0", "copyright 2025", "hello world"]
        >>> filter_strings(strings, keywords=["version", "copyright"])
        ['copyright 2025', 'version 1.0']
    """
    if not strings:
        return []

    matches = set()

    # Filter by keywords
    if keywords:
        for s in strings:
            s_compare = s if case_sensitive else s.lower()
            for keyword in keywords:
                kw_compare = keyword if case_sensitive else keyword.lower()
                if kw_compare in s_compare:
                    matches.add(s)
                    break

    # Filter by single regex
    if regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(regex, flags)
        matches.update(s for s in strings if pattern.search(s))

    # Filter by multiple regex patterns
    if regex_patterns:
        flags = 0 if case_sensitive else re.IGNORECASE
        # Combine patterns with OR
        combined_pattern = "|".join(f"({p})" for p in regex_patterns)
        pattern = re.compile(combined_pattern, flags)
        matches.update(s for s in strings if pattern.search(s))

    return sorted(matches)


def extract_firmware_component(
    firmware: Path,
    offset: int,
    size: int,
    keywords: list[str] | None = None,
    regex_patterns: list[str] | None = None,
    use_dd: bool = True,
) -> list[str]:
    """High-level: extract gzipped component and filter strings.

    Combines extract_gzip_at_offset, extract_strings, and filter_strings
    into a single convenient function.

    Args:
        firmware: Path to firmware file
        offset: Byte offset to start reading
        size: Number of bytes to read
        keywords: Optional list of keywords to filter for
        regex_patterns: Optional list of regex patterns to filter for
        use_dd: Whether to use dd|gunzip pipeline (default: True)

    Returns:
        List of filtered strings from decompressed data

    Example:
        >>> strings = extract_firmware_component(
        ...     Path("firmware.img"),
        ...     0x8000,
        ...     500000,
        ...     keywords=["U-Boot", "version"]
        ... )
    """
    # Extract and decompress
    data = extract_gzip_at_offset(firmware, offset, size, use_dd=use_dd)
    if not data:
        return []

    # Extract strings
    all_strings = extract_strings(data)

    # Filter if keywords or patterns provided
    if keywords or regex_patterns:
        return filter_strings(all_strings, keywords=keywords, regex_patterns=regex_patterns)

    return all_strings


def extract_strings_from_file(
    file_path: Path, pattern: str | None = None, min_length: int = MIN_STRING_LENGTH
) -> list[str]:
    """Extract printable strings from a binary file using `strings` command.

    Uses the external `strings` command (more efficient for large files than
    Python-based extract_strings). Optionally filters results with grep.

    Args:
        file_path: Path to binary file
        pattern: Optional grep pattern to filter strings
        min_length: Minimum string length (default: 4, matches `strings` default)

    Returns:
        List of extracted strings (one per line)

    Raises:
        FileNotFoundError: If strings or grep command not found
        RuntimeError: If strings command fails

    Example:
        >>> # Extract all strings
        >>> strings = extract_strings_from_file(Path("firmware.bin"))

        >>> # Extract strings matching pattern
        >>> version_strings = extract_strings_from_file(
        ...     Path("uboot.bin"),
        ...     pattern="U-Boot"
        ... )
    """
    try:
        # Build command
        if pattern:
            # strings <file> | grep <pattern>
            strings_proc = subprocess.Popen(
                ["strings", f"-n{min_length}", str(file_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            grep_proc = subprocess.Popen(
                ["grep", pattern],
                stdin=strings_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            strings_proc.stdout.close()  # type: ignore
            output, _ = grep_proc.communicate()
        else:
            # strings <file>
            result = subprocess.run(
                ["strings", f"-n{min_length}", str(file_path)],
                capture_output=True,
                text=True,
                check=True,
            )
            output = result.stdout

        # Split by newlines and filter empty lines
        return [line.strip() for line in output.split("\n") if line.strip()]

    except FileNotFoundError as e:
        # Handle missing commands
        if "strings" in str(e):
            raise FileNotFoundError(
                "strings command not found. Please run within 'nix develop' shell"
            ) from e
        if "grep" in str(e):
            raise FileNotFoundError(
                "grep command not found. Please run within 'nix develop' shell"
            ) from e
        raise

    except subprocess.CalledProcessError as e:
        # strings command failed
        raise RuntimeError(f"Failed to extract strings from {file_path}: {e}") from e
