#!/usr/bin/env python3
"""Tests for scripts/lib/finders.py."""

import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib.finders import (
    find_and_create,
    find_by_names,
    find_elf_binaries,
    find_files,
    find_libraries,
    get_file_size,
    get_relative_path,
)


@dataclass
class MockObject:
    """Mock object for testing find_and_create."""

    name: str
    path: str


class TestFindFiles:
    """Test find_files function."""

    def test_find_files_by_pattern(self, tmp_path):
        """Test finding files by glob pattern."""
        # Create test files
        (tmp_path / "test1.txt").touch()
        (tmp_path / "test2.txt").touch()
        (tmp_path / "other.md").touch()

        results = find_files(tmp_path, ["*.txt"])
        assert len(results) == 2
        assert all(p.suffix == ".txt" for p in results)

    def test_find_files_multiple_patterns(self, tmp_path):
        """Test finding files with multiple patterns."""
        (tmp_path / "file.txt").touch()
        (tmp_path / "file.md").touch()
        (tmp_path / "file.py").touch()

        results = find_files(tmp_path, ["*.txt", "*.md"])
        assert len(results) == 2

    def test_find_files_with_exclusions(self, tmp_path):
        """Test finding files with exclusion patterns."""
        (tmp_path / "test.py").touch()
        (tmp_path / "test.pyc").touch()
        (tmp_path / "data.py").touch()

        results = find_files(tmp_path, ["*.py*"], exclude_patterns=["*.pyc"])
        assert len(results) == 2
        assert not any(p.suffix == ".pyc" for p in results)

    def test_find_files_type_file(self, tmp_path):
        """Test finding only files (not directories)."""
        (tmp_path / "file.txt").touch()
        (tmp_path / "subdir").mkdir()

        results = find_files(tmp_path, ["*"], file_type="file")
        assert len(results) == 1
        assert results[0].is_file()

    def test_find_files_type_dir(self, tmp_path):
        """Test finding only directories (not files)."""
        (tmp_path / "file.txt").touch()
        (tmp_path / "subdir").mkdir()

        results = find_files(tmp_path, ["*"], file_type="dir")
        assert len(results) == 1
        assert results[0].is_dir()

    def test_find_files_first_match_only(self, tmp_path):
        """Test returning only first match per pattern."""
        (tmp_path / "test1.txt").touch()
        (tmp_path / "test2.txt").touch()
        (tmp_path / "test3.txt").touch()

        results = find_files(tmp_path, ["*.txt"], first_match_only=True)
        assert len(results) == 1

    def test_find_files_nested_directories(self, tmp_path):
        """Test finding files in nested directories."""
        subdir = tmp_path / "level1" / "level2"
        subdir.mkdir(parents=True)
        (subdir / "nested.txt").touch()

        results = find_files(tmp_path, ["*.txt"])
        assert len(results) == 1
        assert "level2" in str(results[0])

    def test_find_files_deduplication(self, tmp_path):
        """Test that duplicate matches are removed."""
        (tmp_path / "test.txt").touch()

        # Same file matched by two patterns
        results = find_files(tmp_path, ["*.txt", "test.*"])
        assert len(results) == 1

    def test_find_files_empty_results(self, tmp_path):
        """Test finding with no matches."""
        results = find_files(tmp_path, ["*.nonexistent"])
        assert len(results) == 0

    def test_find_files_sorted_output(self, tmp_path):
        """Test that results are sorted."""
        (tmp_path / "b.txt").touch()
        (tmp_path / "a.txt").touch()
        (tmp_path / "c.txt").touch()

        results = find_files(tmp_path, ["*.txt"])
        names = [p.name for p in results]
        assert names == sorted(names)


class TestFindAndCreate:
    """Test find_and_create function."""

    def test_find_and_create_basic(self, tmp_path):
        """Test finding files and creating objects."""
        (tmp_path / "test1.txt").touch()
        (tmp_path / "test2.txt").touch()

        def creator(rootfs: Path, path: Path) -> MockObject:
            return MockObject(name=path.name, path=str(path.relative_to(rootfs)))

        results = find_and_create(tmp_path, ["*.txt"], creator)
        assert len(results) == 2
        assert all(isinstance(obj, MockObject) for obj in results)

    def test_find_and_create_with_exception(self, tmp_path):
        """Test that creator exceptions are handled gracefully."""
        (tmp_path / "test1.txt").touch()
        (tmp_path / "test2.txt").touch()

        call_count = [0]

        def creator(rootfs: Path, path: Path) -> MockObject:
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("Test exception")
            return MockObject(name=path.name, path=str(path.relative_to(rootfs)))

        results = find_and_create(tmp_path, ["*.txt"], creator)
        # Should have 1 result (second file succeeded)
        assert len(results) == 1

    def test_find_and_create_with_filters(self, tmp_path):
        """Test find_and_create with type and exclusion filters."""
        (tmp_path / "test.py").touch()
        (tmp_path / "test.pyc").touch()
        (tmp_path / "subdir").mkdir()

        def creator(rootfs: Path, path: Path) -> MockObject:
            return MockObject(name=path.name, path=str(path.relative_to(rootfs)))

        results = find_and_create(
            tmp_path, ["*.py*"], creator, exclude_patterns=["*.pyc"], file_type="file"
        )
        assert len(results) == 1
        assert results[0].name == "test.py"


class TestFindByNames:
    """Test find_by_names function."""

    def test_find_by_names_exact_match(self, tmp_path):
        """Test finding files by exact name."""
        (tmp_path / "nginx").touch()
        (tmp_path / "sshd").touch()

        results = find_by_names(tmp_path, {"nginx": "Nginx", "sshd": "SSH"})
        assert results["nginx"] is not None
        assert results["sshd"] is not None
        assert results["nginx"].name == "nginx"  # type: ignore[union-attr]

    def test_find_by_names_with_wildcard(self, tmp_path):
        """Test finding files with wildcard when exact match fails."""
        (tmp_path / "nginx-1.20").touch()
        (tmp_path / "sshd_config").touch()

        results = find_by_names(tmp_path, {"nginx": "Nginx", "sshd": "SSH"})
        assert results["nginx"] is not None
        assert "nginx" in results["nginx"].name  # type: ignore[union-attr]

    def test_find_by_names_not_found(self, tmp_path):
        """Test finding files that don't exist."""
        results = find_by_names(tmp_path, {"nonexistent": "Test"})
        assert results["nonexistent"] is None

    def test_find_by_names_type_filter(self, tmp_path):
        """Test finding by name with type filter."""
        (tmp_path / "testfile").touch()
        (tmp_path / "testdir").mkdir()

        # Looking for directories only
        results = find_by_names(tmp_path, {"testdir": "Test"}, file_type="dir")
        assert results["testdir"] is not None
        assert results["testdir"].is_dir()  # type: ignore[union-attr]


class TestFindElfBinaries:
    """Test find_elf_binaries function."""

    def test_find_elf_binaries_standard_locations(self, tmp_path):
        """Test finding binaries in standard locations."""
        bin_dir = tmp_path / "usr" / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "nginx").touch()
        (bin_dir / "sshd").touch()

        results = find_elf_binaries(tmp_path, ["nginx", "sshd"])
        assert len(results) == 2

    def test_find_elf_binaries_custom_directories(self, tmp_path):
        """Test finding binaries in custom directories."""
        custom_dir = tmp_path / "custom" / "bin"
        custom_dir.mkdir(parents=True)
        (custom_dir / "mybinary").touch()

        results = find_elf_binaries(tmp_path, ["mybinary"], directories=["custom/bin"])
        assert len(results) == 1
        assert results[0].name == "mybinary"

    def test_find_elf_binaries_with_wildcard(self, tmp_path):
        """Test finding binaries with version suffixes."""
        bin_dir = tmp_path / "usr" / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "python3.11").touch()

        results = find_elf_binaries(tmp_path, ["python"])
        assert len(results) == 1
        assert "python" in results[0].name

    def test_find_elf_binaries_missing_directories(self, tmp_path):
        """Test finding binaries when directories don't exist."""
        results = find_elf_binaries(tmp_path, ["nginx"])
        assert len(results) == 0

    def test_find_elf_binaries_stops_after_first_match(self, tmp_path):
        """Test that search stops after first match per binary."""
        # Create same binary in multiple locations
        for directory in ["bin", "usr/bin", "usr/local/bin"]:
            dir_path = tmp_path / directory
            dir_path.mkdir(parents=True)
            (dir_path / "nginx").touch()

        results = find_elf_binaries(tmp_path, ["nginx"])
        # Should only find one (first match)
        assert len(results) == 1


class TestFindLibraries:
    """Test find_libraries function."""

    def test_find_libraries_standard_locations(self, tmp_path):
        """Test finding libraries in standard locations."""
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        (lib_dir / "libssl.so.1.1").touch()
        (lib_dir / "libcrypto.so.1.1").touch()

        results = find_libraries(tmp_path, ["libssl", "libcrypto"])
        assert len(results) == 2

    def test_find_libraries_custom_directories(self, tmp_path):
        """Test finding libraries in custom directories."""
        custom_dir = tmp_path / "custom" / "libs"
        custom_dir.mkdir(parents=True)
        (custom_dir / "libcustom.so").touch()

        results = find_libraries(tmp_path, ["libcustom"], lib_dirs=["custom/libs"])
        assert len(results) == 1

    def test_find_libraries_version_suffixes(self, tmp_path):
        """Test finding libraries with version numbers."""
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        (lib_dir / "libtest.so.1").touch()
        (lib_dir / "libtest.so.1.2.3").touch()

        results = find_libraries(tmp_path, ["libtest"])
        assert len(results) >= 1
        assert all(".so" in lib.name for lib in results)

    def test_find_libraries_nested_subdirectories(self, tmp_path):
        """Test finding libraries in nested subdirectories."""
        subdir = tmp_path / "lib" / "x86_64-linux-gnu"
        subdir.mkdir(parents=True)
        (subdir / "libssl.so.1.1").touch()

        results = find_libraries(tmp_path, ["libssl"])
        assert len(results) == 1

    def test_find_libraries_deduplication(self, tmp_path):
        """Test that duplicate library paths are removed."""
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        (lib_dir / "libtest.so").touch()

        # Same library should not be duplicated
        results = find_libraries(tmp_path, ["libtest", "libtest"])
        assert len(results) == 1

    def test_find_libraries_sorted_output(self, tmp_path):
        """Test that library results are sorted."""
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        (lib_dir / "libc.so").touch()
        (lib_dir / "liba.so").touch()
        (lib_dir / "libb.so").touch()

        results = find_libraries(tmp_path, ["liba", "libb", "libc"])
        names = [p.name for p in results]
        assert names == sorted(names)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_get_relative_path(self, tmp_path):
        """Test getting relative path with leading slash."""
        subdir = tmp_path / "lib"
        subdir.mkdir()
        file_path = subdir / "libtest.so"
        file_path.touch()

        result = get_relative_path(tmp_path, file_path)
        assert result == "/lib/libtest.so"
        assert result.startswith("/")

    def test_get_file_size(self, tmp_path):
        """Test getting file size."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        size = get_file_size(test_file)
        assert size == 13  # "Hello, World!" is 13 bytes

    def test_get_file_size_nonexistent(self, tmp_path):
        """Test getting size of nonexistent file."""
        nonexistent = tmp_path / "nonexistent.txt"

        size = get_file_size(nonexistent)
        assert size == 0


class TestPerformance:
    """Test performance with large file sets."""

    def test_find_files_many_files(self, tmp_path):
        """Test finding files with 1000+ files."""
        # Create 1000 test files
        for i in range(1000):
            (tmp_path / f"file{i}.txt").touch()

        # Also create some non-matching files
        for i in range(100):
            (tmp_path / f"other{i}.md").touch()

        start = time.time()
        results = find_files(tmp_path, ["*.txt"])
        elapsed = time.time() - start

        assert len(results) == 1000
        assert elapsed < 1.0  # Should complete in under 1 second
