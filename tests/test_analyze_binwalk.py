"""Tests for scripts/analyze-binwalk.py."""

import sys
from pathlib import Path

import pytest
import tomlkit

# Add scripts directory to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from analyze_binwalk import (
    BinwalkAnalysis,
    Component,
    _extract_offset_from_lines,
    output_toml,
    parse_binwalk_output,
)


class TestComponent:
    """Test Component dataclass."""

    def test_component_creation(self):
        """Test creating a Component."""
        comp = Component(
            offset="0x8F1B4",
            type="Device",
            description="Device tree blob (DTB), version: 17",
        )

        assert comp.offset == "0x8F1B4"
        assert comp.type == "Device"
        assert comp.description == "Device tree blob (DTB), version: 17"

    def test_component_is_frozen(self):
        """Test that Component is immutable (frozen)."""
        comp = Component(offset="0x8F1B4", type="Device", description="DTB")

        with pytest.raises(AttributeError):
            comp.offset = "0x12345"  # type: ignore


class TestBinwalkAnalysis:
    """Test BinwalkAnalysis dataclass."""

    def test_analysis_creation(self):
        """Test creating a BinwalkAnalysis."""
        analysis = BinwalkAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )

        assert analysis.firmware_file == "test.img"
        assert analysis.firmware_size == 1024
        assert analysis.squashfs_count == 0
        assert analysis.bootloader_fit_offset is None

    def test_add_metadata(self):
        """Test adding source metadata."""
        analysis = BinwalkAnalysis(firmware_file="test.img", firmware_size=1024)

        analysis.add_metadata("firmware_size", "stat", "stat -f%z test.img")

        assert analysis._source["firmware_size"] == "stat"
        assert analysis._method["firmware_size"] == "stat -f%z test.img"

    def test_to_dict_excludes_none(self):
        """Test to_dict excludes None values."""
        analysis = BinwalkAnalysis(firmware_file="test.img", firmware_size=1024)

        result = analysis.to_dict()

        assert "firmware_file" in result
        assert "firmware_size" in result
        assert "bootloader_fit_offset" not in result  # Should be excluded (None)

    def test_to_dict_includes_metadata(self):
        """Test to_dict includes source metadata."""
        analysis = BinwalkAnalysis(firmware_file="test.img", firmware_size=1024)
        analysis.add_metadata("firmware_size", "stat", "stat -f%z test.img")

        result = analysis.to_dict()

        assert result["firmware_size"] == 1024
        assert result["firmware_size_source"] == "stat"
        assert result["firmware_size_method"] == "stat -f%z test.img"

    def test_to_dict_converts_components(self):
        """Test to_dict converts Component objects to dicts."""
        analysis = BinwalkAnalysis(firmware_file="test.img", firmware_size=1024)
        analysis.identified_components = [
            Component(offset="0x100", type="gzip", description="gzip compressed data")
        ]

        result = analysis.to_dict()

        assert len(result["identified_components"]) == 1
        assert result["identified_components"][0]["offset"] == "0x100"
        assert result["identified_components"][0]["type"] == "gzip"


class TestParseBinwalkOutput:
    """Test parse_binwalk_output function."""

    def test_parse_empty_output(self):
        """Test parsing empty binwalk output."""
        result = parse_binwalk_output("")
        assert result == []

    def test_parse_header_only(self):
        """Test parsing binwalk output with only headers."""
        output = """
DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
"""
        result = parse_binwalk_output(output)
        assert result == []

    def test_parse_single_component(self):
        """Test parsing single component."""
        output = """
DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
586164        0x8F1B4         Device tree blob (DTB), version: 17
"""
        result = parse_binwalk_output(output)

        assert len(result) == 1
        assert result[0].offset == "0x8F1B4"
        assert result[0].type == "Device"
        assert "Device tree blob" in result[0].description

    def test_parse_multiple_components(self):
        """Test parsing multiple components."""
        output = """
DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
586164        0x8F1B4         Device tree blob (DTB), version: 17
590260        0x901B4         gzip compressed data, original file name: "u-boot.bin"
1037748       0xFD5B4         gzip compressed data, original file name: "tee.bin"
"""
        result = parse_binwalk_output(output)

        assert len(result) == 3
        assert result[0].offset == "0x8F1B4"
        assert result[1].offset == "0x901B4"
        assert result[2].offset == "0xFD5B4"

    def test_parse_ignores_continuation_lines(self):
        """Test that continuation lines without hex offset are ignored."""
        output = """
DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
586164        0x8F1B4         Device tree blob (DTB), version: 17, size: 2048
                              additional description line
590260        0x901B4         gzip compressed data
"""
        result = parse_binwalk_output(output)

        # Should only get 2 components, ignoring the continuation line
        assert len(result) == 2

    def test_parse_extracts_type_correctly(self):
        """Test that component type (first word) is extracted correctly."""
        output = """
DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
586164        0x8F1B4         Device tree blob (DTB)
590260        0x901B4         gzip compressed data
1037748       0xFD5B4         SquashFS filesystem, version 4.0
"""
        result = parse_binwalk_output(output)

        assert result[0].type == "Device"
        assert result[1].type == "gzip"
        assert result[2].type == "SquashFS"


class TestExtractOffsetFromLines:
    """Test _extract_offset_from_lines helper function."""

    def test_extract_offset_found(self):
        """Test extracting offset when search term is found."""
        lines = [
            "DECIMAL       HEXADECIMAL     DESCRIPTION",
            "586164        0x8F1B4         Device tree blob (DTB)",
            "590260        0x901B4         gzip compressed data",
        ]

        offset = _extract_offset_from_lines(lines, "device tree blob")

        assert offset == "0x8F1B4"

    def test_extract_offset_not_found(self):
        """Test extracting offset when search term is not found."""
        lines = [
            "DECIMAL       HEXADECIMAL     DESCRIPTION",
            "586164        0x8F1B4         Device tree blob (DTB)",
        ]

        offset = _extract_offset_from_lines(lines, "squashfs")

        assert offset is None

    def test_extract_offset_case_insensitive(self):
        """Test that search is case-insensitive."""
        lines = ["586164        0x8F1B4         Device Tree Blob (DTB)"]

        offset = _extract_offset_from_lines(lines, "device tree blob")

        assert offset == "0x8F1B4"

    def test_extract_offset_with_additional_term(self):
        """Test extracting offset with additional search term."""
        lines = [
            "586164        0x8F1B4         Device tree blob (DTB), version: 17, size: 2048",
            "590260        0x901B4         Device tree blob (DTB), version: 17, size: 96558",
        ]

        # Find the one with "96558"
        offset = _extract_offset_from_lines(lines, "device tree blob", "96558")

        assert offset == "0x901B4"

    def test_extract_offset_returns_first_match(self):
        """Test that only the first match is returned."""
        lines = [
            "586164        0x8F1B4         gzip compressed data",
            "590260        0x901B4         gzip compressed data",
        ]

        offset = _extract_offset_from_lines(lines, "gzip")

        assert offset == "0x8F1B4"  # First match


class TestOutputToml:
    """Test output_toml function."""

    def test_toml_output_valid(self):
        """Test that TOML output is valid."""
        analysis = BinwalkAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            squashfs_count=1,
        )
        analysis.add_metadata("firmware_file", "test", "test method")

        toml_str = output_toml(analysis)

        # Should be valid TOML
        parsed = tomlkit.loads(toml_str)
        assert parsed["firmware_file"] == "test.img"
        assert parsed["firmware_size"] == 1024

    def test_toml_includes_comments(self):
        """Test that TOML includes source metadata as comments."""
        analysis = BinwalkAnalysis(firmware_file="test.img", firmware_size=1024)
        analysis.add_metadata("firmware_size", "stat", "stat -f%z test.img")

        toml_str = output_toml(analysis)

        assert "# Source: stat" in toml_str
        assert "# Method: stat -f%z test.img" in toml_str

    def test_toml_truncates_long_methods(self):
        """Test that long method descriptions are truncated."""
        analysis = BinwalkAnalysis(firmware_file="test.img", firmware_size=1024)
        long_method = "x" * 100  # 100 characters
        analysis.add_metadata("firmware_size", "test", long_method)

        toml_str = output_toml(analysis)

        # Should be truncated with "..."
        assert "..." in toml_str
        assert long_method not in toml_str

    def test_toml_excludes_none_values(self):
        """Test that None values are excluded from TOML output."""
        analysis = BinwalkAnalysis(firmware_file="test.img", firmware_size=1024)
        # bootloader_fit_offset is None by default

        toml_str = output_toml(analysis)

        assert "bootloader_fit_offset" not in toml_str

    def test_toml_includes_arrays(self):
        """Test that arrays (identified_components) are included."""
        analysis = BinwalkAnalysis(firmware_file="test.img", firmware_size=1024)
        analysis.identified_components = [
            Component(offset="0x100", type="gzip", description="gzip data"),
            Component(offset="0x200", type="Device", description="DTB"),
        ]

        toml_str = output_toml(analysis)
        parsed = tomlkit.loads(toml_str)

        assert len(parsed["identified_components"]) == 2
        assert parsed["identified_components"][0]["offset"] == "0x100"


class TestIntegration:
    """Integration tests with realistic binwalk output."""

    def test_realistic_binwalk_output(self):
        """Test parsing realistic binwalk output."""
        # fmt: off
        output = """

                                                  /tmp/firmware.img
--------------------------------------------------------------------------------
DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
586164        0x8F1B4         Device tree blob (DTB), version: 17
590260        0x901B4         gzip compressed data, file: "u-boot-nodtb.bin"
1037748       0xFD5B4         gzip compressed data, file: "tee.bin"
30319028      0x1CEA1B4       SquashFS filesystem, version: 4.0
--------------------------------------------------------------------------------

Analyzed 1 file for 85 file signatures in 209.0 milliseconds
"""
        # fmt: on
        components = parse_binwalk_output(output)

        assert len(components) == 4
        assert components[0].type == "Device"
        assert components[1].type == "gzip"
        assert components[2].type == "gzip"
        assert components[3].type == "SquashFS"

        # Verify offsets
        assert components[0].offset == "0x8F1B4"
        assert components[1].offset == "0x901B4"
        assert components[2].offset == "0xFD5B4"
        assert components[3].offset == "0x1CEA1B4"
