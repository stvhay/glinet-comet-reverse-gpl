#!/usr/bin/env python3
"""Generic file and directory finding utilities for firmware analysis.

This module provides reusable functions for finding files in extracted firmware
filesystems. All functions follow consistent patterns and handle edge cases.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Literal, TypeVar

T = TypeVar("T")


def find_files(
    rootfs: Path,
    patterns: list[str],
    exclude_patterns: list[str] | None = None,
    file_type: Literal["file", "dir", "any"] = "any",
    first_match_only: bool = False,
) -> list[Path]:
    """Find files or directories matching glob patterns.

    Args:
        rootfs: Root filesystem path to search in
        patterns: List of glob patterns (e.g., ["*.so*", "lib*.a"])
        exclude_patterns: Optional list of patterns to exclude (e.g., ["*.pyc"])
        file_type: Type of filesystem entry to find ("file", "dir", or "any")
        first_match_only: If True, return only first match per pattern

    Returns:
        List of Path objects matching criteria (deduplicated)

    Example:
        >>> find_files(rootfs, ["*.so*"], exclude_patterns=["*.pyc"])
        [Path("/lib/libc.so.6"), Path("/usr/lib/libssl.so.1.1")]
    """
    found_paths: set[Path] = set()
    exclude_set = set(exclude_patterns) if exclude_patterns else set()

    for pattern in patterns:
        for path in rootfs.rglob(pattern):
            # Check type filter
            if file_type == "file" and not path.is_file():
                continue
            if file_type == "dir" and not path.is_dir():
                continue

            # Check exclusions
            if any(path.match(excl) for excl in exclude_set):
                continue

            # Skip if already found (for deduplication)
            if path in found_paths:
                continue

            found_paths.add(path)

            # If first match only, stop after finding one for this pattern
            if first_match_only:
                break

    return sorted(found_paths)


def find_and_create(
    rootfs: Path,
    patterns: list[str],
    creator_func: Callable[[Path, Path], T],
    exclude_patterns: list[str] | None = None,
    file_type: Literal["file", "dir", "any"] = "any",
    first_match_only: bool = False,
) -> list[T]:
    """Find files and create objects from them using a creator function.

    This is a higher-order function that combines file finding with object creation.

    Args:
        rootfs: Root filesystem path to search in
        patterns: List of glob patterns to search for
        creator_func: Function that takes (rootfs, path) and returns object T
        exclude_patterns: Optional list of patterns to exclude
        file_type: Type of filesystem entry to find
        first_match_only: If True, return only first match per pattern

    Returns:
        List of objects of type T created from found paths

    Example:
        >>> def make_lib_info(rootfs: Path, path: Path) -> LibraryInfo:
        ...     return LibraryInfo(name=path.name, path=str(path.relative_to(rootfs)))
        >>> find_and_create(rootfs, ["*.so*"], make_lib_info)
        [LibraryInfo(name="libc.so.6", path="/lib/libc.so.6")]
    """
    paths = find_files(
        rootfs,
        patterns,
        exclude_patterns=exclude_patterns,
        file_type=file_type,
        first_match_only=first_match_only,
    )

    objects = []
    for path in paths:
        try:
            obj = creator_func(rootfs, path)
            objects.append(obj)
        except Exception:
            # Skip files that fail to process
            continue

    return objects


def find_by_names(
    rootfs: Path,
    names: dict[str, str],
    file_type: Literal["file", "dir", "any"] = "file",
) -> dict[str, Path | None]:
    """Find multiple files/directories by exact name, returning first match for each.

    Args:
        rootfs: Root filesystem path to search in
        names: Dict mapping name to description (e.g., {"nginx": "Nginx server"})
        file_type: Type of filesystem entry to find

    Returns:
        Dict mapping name to found Path (or None if not found)

    Example:
        >>> find_by_names(rootfs, {"nginx": "Nginx server", "sshd": "SSH daemon"})
        {"nginx": Path("/usr/sbin/nginx"), "sshd": Path("/usr/sbin/sshd")}
    """
    results: dict[str, Path | None] = {}

    for name in names:
        # Try exact match first
        found = find_files(
            rootfs,
            [name],
            file_type=file_type,
            first_match_only=True,  # type: ignore[arg-type]
        )
        if found:
            results[name] = found[0]
        else:
            # Try with wildcard
            found = find_files(
                rootfs,
                [f"{name}*"],
                file_type=file_type,
                first_match_only=True,  # type: ignore[arg-type]
            )
            results[name] = found[0] if found else None

    return results


def find_elf_binaries(
    rootfs: Path,
    names: list[str],
    directories: list[str] | None = None,
) -> list[Path]:
    """Find ELF binaries by name in common binary directories.

    Args:
        rootfs: Root filesystem path to search in
        names: List of binary names to search for (e.g., ["nginx", "sshd"])
        directories: Optional list of directories to search (defaults to standard paths)

    Returns:
        List of found binary paths

    Example:
        >>> find_elf_binaries(rootfs, ["nginx", "sshd"])
        [Path("/usr/sbin/nginx"), Path("/usr/sbin/sshd")]
    """
    if directories is None:
        directories = [
            "bin",
            "sbin",
            "usr/bin",
            "usr/sbin",
            "usr/local/bin",
            "usr/local/sbin",
        ]

    found_binaries = []

    for name in names:
        for directory in directories:
            dir_path = rootfs / directory
            if not dir_path.exists():
                continue

            # Check exact name
            binary_path = dir_path / name
            if binary_path.is_file():
                found_binaries.append(binary_path)
                break

            # Check with wildcards in that directory
            matches = list(dir_path.glob(f"{name}*"))
            if matches:
                # Take first match that's a file
                for match in matches:
                    if match.is_file():
                        found_binaries.append(match)
                        break

    return found_binaries


def find_libraries(
    rootfs: Path,
    patterns: list[str],
    lib_dirs: list[str] | None = None,
) -> list[Path]:
    """Find shared libraries (.so files) matching patterns.

    Args:
        rootfs: Root filesystem path to search in
        patterns: List of library patterns (e.g., ["libssl*", "libcrypto*"])
        lib_dirs: Optional list of library directories to search (defaults to standard)

    Returns:
        List of found library paths (deduplicated)

    Example:
        >>> find_libraries(rootfs, ["libssl*", "libcrypto*"])
        [Path("/lib/libssl.so.1.1"), Path("/lib/libcrypto.so.1.1")]
    """
    if lib_dirs is None:
        lib_dirs = [
            "lib",
            "usr/lib",
            "lib64",
            "usr/lib64",
            "lib/aarch64-linux-gnu",
            "usr/lib/aarch64-linux-gnu",
        ]

    found_libs: set[Path] = set()

    for pattern in patterns:
        for lib_dir in lib_dirs:
            dir_path = rootfs / lib_dir
            if not dir_path.exists():
                continue

            # Find all .so files matching pattern in this directory and subdirs
            for lib_file in dir_path.rglob(f"{pattern}*.so*"):
                if lib_file.is_file() and ".so" in lib_file.name:
                    found_libs.add(lib_file)

    return sorted(found_libs)


def get_relative_path(rootfs: Path, path: Path) -> str:
    """Get path relative to rootfs with leading slash.

    Args:
        rootfs: Root filesystem path
        path: Absolute path to make relative

    Returns:
        Relative path with leading slash (e.g., "/lib/libc.so.6")

    Example:
        >>> get_relative_path(Path("/tmp/rootfs"), Path("/tmp/rootfs/lib/libc.so.6"))
        "/lib/libc.so.6"
    """
    return "/" + str(path.relative_to(rootfs))


def get_file_size(path: Path) -> int:
    """Get file size in bytes, return 0 if file doesn't exist.

    Args:
        path: Path to file

    Returns:
        File size in bytes, or 0 if file doesn't exist

    Example:
        >>> get_file_size(Path("/tmp/test.bin"))
        1024
    """
    try:
        return path.stat().st_size
    except (FileNotFoundError, OSError):
        return 0
