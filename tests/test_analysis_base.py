#!/usr/bin/env python3
"""Tests for scripts/lib/analysis_base.py — reproducibility and hardware metadata."""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomlkit

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib.analysis_base import AnalysisBase
from lib.output import output_toml


@dataclass
class SampleAnalysis(AnalysisBase):
    """Minimal analysis dataclass for testing."""

    version: str | None = None
    offset: int | None = None

    _source: dict[str, str] = field(default_factory=dict)
    _method: dict[str, str] = field(default_factory=dict)
    _reproducibility: dict[str, str] = field(default_factory=dict)
    _hardware_metadata: dict[str, dict[str, str]] = field(default_factory=dict)

    def _convert_complex_field(self, key: str, value: Any) -> tuple[bool, Any]:  # noqa: ARG002
        return False, None


@dataclass
class SampleWithListAnalysis(AnalysisBase):
    """Analysis dataclass with a complex (list) field for testing."""

    name: str | None = None
    items: list[dict[str, str]] = field(default_factory=list)

    _source: dict[str, str] = field(default_factory=dict)
    _method: dict[str, str] = field(default_factory=dict)
    _reproducibility: dict[str, str] = field(default_factory=dict)
    _hardware_metadata: dict[str, dict[str, str]] = field(default_factory=dict)

    def _convert_complex_field(self, key: str, value: Any) -> tuple[bool, Any]:
        if key == "items":
            return True, value
        return False, None


class TestReproducibilityMetadata:
    """Test reproducibility metadata tracking."""

    def test_default_reproducibility_is_software(self) -> None:
        analysis = SampleAnalysis()
        analysis.version = "1.0"
        analysis.add_metadata("version", "firmware", "strings | grep")
        assert analysis._reproducibility["version"] == "software"

    def test_explicit_software_reproducibility(self) -> None:
        analysis = SampleAnalysis()
        analysis.version = "1.0"
        analysis.add_metadata("version", "firmware", "strings | grep", reproducibility="software")
        assert analysis._reproducibility["version"] == "software"

    def test_explicit_hardware_reproducibility(self) -> None:
        analysis = SampleAnalysis()
        analysis.version = "1.0"
        analysis.add_metadata("version", "firmware", "UART capture", reproducibility="hardware")
        assert analysis._reproducibility["version"] == "hardware"

    def test_to_dict_emits_reproducibility(self) -> None:
        analysis = SampleAnalysis()
        analysis.version = "1.0"
        analysis.add_metadata("version", "firmware", "strings | grep")
        d = analysis.to_dict()
        assert d["version_reproducibility"] == "software"

    def test_backward_compat_three_arg_add_metadata(self) -> None:
        analysis = SampleAnalysis()
        analysis.version = "1.0"
        analysis.add_metadata("version", "firmware", "strings | grep")
        d = analysis.to_dict()
        assert d["version_source"] == "firmware"
        assert d["version_method"] == "strings | grep"
        assert d["version_reproducibility"] == "software"


class TestHardwareMetadata:
    """Test hardware-dependent metadata tracking."""

    def test_add_hardware_metadata_sets_all_fields(self) -> None:
        analysis = SampleAnalysis()
        analysis.offset = 0x100
        analysis.add_hardware_metadata(
            "offset",
            "UART log",
            "serial console capture",
            equipment="USB-UART adapter",
            procedure="Boot with UART connected at 115200 baud",
            performed="2025-01-15",
            operator="Test Engineer",
        )
        assert analysis._reproducibility["offset"] == "hardware"
        assert analysis._hardware_metadata["offset"]["equipment"] == "USB-UART adapter"
        expected_procedure = "Boot with UART connected at 115200 baud"
        assert analysis._hardware_metadata["offset"]["procedure"] == expected_procedure
        assert analysis._hardware_metadata["offset"]["performed"] == "2025-01-15"
        assert analysis._hardware_metadata["offset"]["operator"] == "Test Engineer"

    def test_to_dict_emits_hardware_fields(self) -> None:
        analysis = SampleAnalysis()
        analysis.offset = 0x100
        analysis.add_hardware_metadata(
            "offset",
            "UART log",
            "serial console capture",
            equipment="USB-UART adapter",
            procedure="Boot capture",
            performed="2025-01-15",
            operator="Test Engineer",
        )
        d = analysis.to_dict()
        assert d["offset_reproducibility"] == "hardware"
        assert d["offset_equipment"] == "USB-UART adapter"
        assert d["offset_procedure"] == "Boot capture"
        assert d["offset_performed"] == "2025-01-15"
        assert d["offset_operator"] == "Test Engineer"


class TestReproducibilityTomlOutput:
    """Test TOML output includes reproducibility metadata as comments."""

    def test_toml_has_reproducibility_comment(self) -> None:
        analysis = SampleAnalysis()
        analysis.version = "1.0"
        analysis.add_metadata("version", "firmware", "strings | grep")
        toml_str = output_toml(analysis, "Test")
        assert "# Reproducibility: software" in toml_str

    def test_toml_hardware_fields_render_as_comments(self) -> None:
        analysis = SampleAnalysis()
        analysis.offset = 256
        analysis.add_hardware_metadata(
            "offset",
            "UART log",
            "serial console capture",
            equipment="USB-UART adapter",
            procedure="Boot capture",
            performed="2025-01-15",
            operator="Test Engineer",
        )
        toml_str = output_toml(analysis, "Test")
        assert "# Reproducibility: hardware" in toml_str
        assert "# Equipment: USB-UART adapter" in toml_str
        assert "# Procedure: Boot capture" in toml_str
        assert "# Performed: 2025-01-15" in toml_str
        assert "# Operator: Test Engineer" in toml_str

    def test_metadata_keys_dont_leak_as_toml_fields(self) -> None:
        analysis = SampleAnalysis()
        analysis.version = "1.0"
        analysis.add_metadata("version", "firmware", "strings | grep")
        toml_str = output_toml(analysis, "Test")
        parsed = tomlkit.loads(toml_str)
        # Only the actual field should appear as a TOML key
        assert "version" in parsed
        # Metadata should be comments, not keys
        assert "version_source" not in parsed
        assert "version_method" not in parsed
        assert "version_reproducibility" not in parsed


class TestComplexFieldMetadata:
    """Test metadata tracking for complex (list/dict) fields."""

    def test_to_dict_emits_metadata_for_complex_fields(self) -> None:
        analysis = SampleWithListAnalysis()
        analysis.name = "test"
        analysis.items = [{"key": "value"}]
        analysis.add_metadata("items", "binwalk", "output parsing")
        d = analysis.to_dict()
        assert d["items_source"] == "binwalk"
        assert d["items_method"] == "output parsing"
        assert d["items_reproducibility"] == "software"

    def test_toml_renders_metadata_comments_for_complex_fields(self) -> None:
        analysis = SampleWithListAnalysis()
        analysis.name = "test"
        analysis.items = [{"key": "value"}]
        analysis.add_metadata("items", "binwalk", "output parsing")
        toml_str = output_toml(analysis, "Test")
        assert "# Source: binwalk" in toml_str
        assert "# Method: output parsing" in toml_str
        assert "# Reproducibility: software" in toml_str

    def test_toml_complex_field_metadata_appears_before_section(self) -> None:
        analysis = SampleWithListAnalysis()
        analysis.name = "test"
        analysis.items = [{"key": "value"}]
        analysis.add_metadata("items", "binwalk", "output parsing")
        toml_str = output_toml(analysis, "Test")
        # Metadata comments should appear before the section header
        source_pos = toml_str.index("# Source: binwalk")
        header_pos = toml_str.index("# Items")
        assert source_pos < header_pos

    def test_toml_complex_field_metadata_keys_not_in_parsed(self) -> None:
        analysis = SampleWithListAnalysis()
        analysis.name = "test"
        analysis.items = [{"key": "value"}]
        analysis.add_metadata("items", "binwalk", "output parsing")
        toml_str = output_toml(analysis, "Test")
        parsed = tomlkit.loads(toml_str)
        assert "items" in parsed
        assert "items_source" not in parsed
        assert "items_method" not in parsed
        assert "items_reproducibility" not in parsed
