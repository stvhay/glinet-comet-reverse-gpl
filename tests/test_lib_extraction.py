#!/usr/bin/env python3
"""Tests for scripts/lib/extraction.py."""

import gzip
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib.extraction import (
    extract_firmware_component,
    extract_gzip_at_offset,
    extract_strings,
    filter_strings,
)


class TestExtractStrings:
    """Test extract_strings function."""

    def test_extract_strings_basic(self):
        """Test basic string extraction."""
        data = b"Hello\x00World\x00"
        result = extract_strings(data)
        assert "Hello" in result
        assert "World" in result

    def test_extract_strings_min_length(self):
        """Test minimum length filtering."""
        data = b"Hi\x00Hello\x00"
        result = extract_strings(data, min_length=4)
        assert "Hello" in result
        assert "Hi" not in result  # Too short

    def test_extract_strings_custom_min_length(self):
        """Test custom minimum length."""
        data = b"Hi\x00Hello\x00A\x00"
        result = extract_strings(data, min_length=2)
        assert "Hi" in result
        assert "Hello" in result
        assert "A" not in result

    def test_extract_strings_empty_data(self):
        """Test with empty data."""
        result = extract_strings(b"")
        assert result == []

    def test_extract_strings_no_printable(self):
        """Test with no printable characters."""
        data = b"\x00\x01\x02\x03\x04"
        result = extract_strings(data)
        assert result == []

    def test_extract_strings_mixed_binary(self):
        """Test with mixed binary and text."""
        data = b"\x00\x01test\x02\x03another\x00"
        result = extract_strings(data)
        assert "test" in result
        assert "another" in result

    def test_extract_strings_last_string(self):
        """Test that last string is captured."""
        data = b"start\x00middle\x00test"
        result = extract_strings(data)
        assert "test" in result  # "test" is 4 chars, meets min_length

    def test_extract_strings_special_chars(self):
        """Test with special printable characters."""
        data = b"Hello, World!\x00"
        result = extract_strings(data)
        assert "Hello, World!" in result


class TestFilterStrings:
    """Test filter_strings function."""

    def test_filter_by_keywords(self):
        """Test filtering by keywords."""
        strings = ["version 1.0", "copyright 2025", "hello world"]
        result = filter_strings(strings, keywords=["version", "copyright"])
        assert "version 1.0" in result
        assert "copyright 2025" in result
        assert "hello world" not in result

    def test_filter_case_insensitive(self):
        """Test case-insensitive keyword matching."""
        strings = ["Version 1.0", "COPYRIGHT 2025"]
        result = filter_strings(strings, keywords=["version", "copyright"])
        assert len(result) == 2

    def test_filter_case_sensitive(self):
        """Test case-sensitive keyword matching."""
        strings = ["Version 1.0", "version 2.0"]
        result = filter_strings(strings, keywords=["version"], case_sensitive=True)
        assert "version 2.0" in result
        assert "Version 1.0" not in result

    def test_filter_by_single_regex(self):
        """Test filtering by single regex pattern."""
        strings = ["version 1.0", "v2.0", "hello"]
        result = filter_strings(strings, regex=r"v.*\d+\.\d+")
        assert "version 1.0" in result
        assert "v2.0" in result
        assert "hello" not in result

    def test_filter_by_multiple_regex(self):
        """Test filtering by multiple regex patterns."""
        strings = ["version 1.0", "build 123", "hello"]
        result = filter_strings(strings, regex_patterns=[r"version", r"build"])
        assert "version 1.0" in result
        assert "build 123" in result
        assert "hello" not in result

    def test_filter_empty_strings(self):
        """Test filtering empty list."""
        result = filter_strings([], keywords=["test"])
        assert result == []

    def test_filter_no_matches(self):
        """Test when no strings match."""
        strings = ["hello", "world"]
        result = filter_strings(strings, keywords=["notfound"])
        assert result == []

    def test_filter_sorted_unique(self):
        """Test that results are sorted and unique."""
        strings = ["zebra", "apple", "zebra", "banana"]
        result = filter_strings(strings, keywords=["a", "b", "z"])
        assert result == ["apple", "banana", "zebra"]

    def test_filter_combined_keywords_and_regex(self):
        """Test combining keywords and regex."""
        strings = ["version 1.0", "build 123", "copyright", "hello"]
        result = filter_strings(
            strings,
            keywords=["copyright"],
            regex_patterns=[r"version", r"build"],
        )
        assert "version 1.0" in result
        assert "build 123" in result
        assert "copyright" in result
        assert "hello" not in result


class TestExtractGzipAtOffset:
    """Test extract_gzip_at_offset function."""

    def test_extract_gzip_python_method(self, tmp_path):
        """Test gzip extraction with Python method."""
        # Create test data
        original_data = b"Hello, this is test data!"
        compressed = gzip.compress(original_data)

        # Write to temp file
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(compressed)

        # Extract
        result = extract_gzip_at_offset(test_file, 0, len(compressed), use_dd=False)

        assert result == original_data

    def test_extract_gzip_with_offset(self, tmp_path):
        """Test gzip extraction from offset."""
        # Create test data with offset
        original_data = b"Test data"
        compressed = gzip.compress(original_data)
        prefix = b"\x00" * 100

        # Write to temp file
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(prefix + compressed)

        # Extract from offset
        result = extract_gzip_at_offset(test_file, 100, len(compressed), use_dd=False)

        assert result == original_data

    def test_extract_gzip_invalid_data(self, tmp_path):
        """Test with invalid gzip data."""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"not gzip data")

        result = extract_gzip_at_offset(test_file, 0, 13, use_dd=False)

        assert result is None

    def test_extract_gzip_nonexistent_file(self):
        """Test with nonexistent file."""
        result = extract_gzip_at_offset(Path("/nonexistent.bin"), 0, 100, use_dd=False)

        assert result is None

    def test_extract_gzip_empty_result(self, tmp_path):
        """Test when extraction returns empty."""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"")

        result = extract_gzip_at_offset(test_file, 0, 0, use_dd=False)

        assert result is None


class TestExtractFirmwareComponent:
    """Test extract_firmware_component function."""

    def test_extract_component_with_keywords(self, tmp_path):
        """Test extracting component with keyword filtering."""
        # Create test data
        original_data = b"version 1.0\x00build 123\x00hello world\x00"
        compressed = gzip.compress(original_data)

        # Write to temp file
        test_file = tmp_path / "firmware.bin"
        test_file.write_bytes(compressed)

        # Extract with keywords
        result = extract_firmware_component(
            test_file,
            0,
            len(compressed),
            keywords=["version", "build"],
            use_dd=False,
        )

        assert "version 1.0" in result
        assert "build 123" in result
        assert "hello world" not in result

    def test_extract_component_with_regex(self, tmp_path):
        """Test extracting component with regex filtering."""
        original_data = b"version 1.0\x00v2.0\x00hello\x00"
        compressed = gzip.compress(original_data)

        test_file = tmp_path / "firmware.bin"
        test_file.write_bytes(compressed)

        result = extract_firmware_component(
            test_file,
            0,
            len(compressed),
            regex_patterns=[r"v.*\d+\.\d+"],
            use_dd=False,
        )

        assert "version 1.0" in result
        assert "v2.0" in result
        assert "hello" not in result

    def test_extract_component_no_filter(self, tmp_path):
        """Test extracting all strings without filtering."""
        original_data = b"string1\x00string2\x00string3\x00"
        compressed = gzip.compress(original_data)

        test_file = tmp_path / "firmware.bin"
        test_file.write_bytes(compressed)

        result = extract_firmware_component(
            test_file,
            0,
            len(compressed),
            use_dd=False,
        )

        assert len(result) == 3
        assert "string1" in result
        assert "string2" in result
        assert "string3" in result

    def test_extract_component_invalid_gzip(self, tmp_path):
        """Test with invalid gzip data."""
        test_file = tmp_path / "firmware.bin"
        test_file.write_bytes(b"not gzip")

        result = extract_firmware_component(
            test_file,
            0,
            8,
            keywords=["test"],
            use_dd=False,
        )

        assert result == []


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_extraction_pipeline(self, tmp_path):
        """Test complete extraction pipeline."""
        # Create realistic test data
        data_parts = [
            "U-Boot 2023.04",
            "Build date: Jan 1 2024",
            "Copyright (C) 2024",
            "Random data here",
            "GPL license",
        ]
        original_data = "\x00".join(data_parts).encode()
        compressed = gzip.compress(original_data)

        # Write to temp firmware file
        firmware = tmp_path / "test_firmware.bin"
        firmware.write_bytes(compressed)

        # Extract component
        strings = extract_firmware_component(
            firmware,
            0,
            len(compressed),
            keywords=["U-Boot", "Copyright", "GPL"],
            use_dd=False,
        )

        assert "U-Boot 2023.04" in strings
        assert "Copyright (C) 2024" in strings
        assert "GPL license" in strings
        assert "Random data here" not in strings
        assert "Build date: Jan 1 2024" not in strings

    def test_multiple_filters(self, tmp_path):
        """Test using multiple filtering strategies."""
        data = b"version 1.0\nbuild 123\nv2.0\ncopyright\nhello"
        compressed = gzip.compress(data)

        firmware = tmp_path / "firmware.bin"
        firmware.write_bytes(compressed)

        # First filter by keywords
        all_strings = extract_firmware_component(
            firmware,
            0,
            len(compressed),
            use_dd=False,
        )

        # Then apply additional filtering
        filtered = filter_strings(
            all_strings,
            keywords=["version"],
            regex_patterns=[r"v\d+"],
        )

        assert "version 1.0" in filtered
        assert "v2.0" in filtered
