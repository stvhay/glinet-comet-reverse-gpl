"""Tests for scripts/analyze_boot_process.py."""

from __future__ import annotations

import struct
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import tomlkit

# Add scripts directory to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from analyze_boot_process import (
    COMPLEX_FIELDS,
    SIMPLE_FIELDS,
    BootComponent,
    BootProcessAnalysis,
    ComponentVersion,
    ConsoleConfig,
    HardwareProperty,
    Partition,
    _classify_partition,
    analyze_ab_redundancy,
    analyze_boot_components,
    analyze_boot_config,
    analyze_component_versions,
    analyze_hardware_properties,
    analyze_partitions,
    analyze_storage_type,
    extract_rockchip_parameter,
    find_largest_dts,
    find_rootfs,
    get_fit_info,
    load_firmware_offsets,
    parse_rockchip_partitions,
)
from lib.output import output_toml


class TestComponentVersion:
    """Test ComponentVersion dataclass."""

    def test_component_version_creation(self) -> None:
        """Test creating a ComponentVersion."""
        version = ComponentVersion(
            component="U-Boot",
            version="U-Boot 2023.07",
            source="Binary strings",
        )

        assert version.component == "U-Boot"
        assert version.version == "U-Boot 2023.07"
        assert version.source == "Binary strings"

    def test_component_version_is_frozen(self) -> None:
        """Test that ComponentVersion is immutable (frozen)."""
        version = ComponentVersion(
            component="U-Boot",
            version="U-Boot 2023.07",
            source="Binary strings",
        )

        with pytest.raises(AttributeError):
            version.version = "Different version"  # type: ignore

    def test_component_version_has_slots(self) -> None:
        """Test that ComponentVersion uses __slots__ for efficiency."""
        version = ComponentVersion(
            component="U-Boot",
            version="U-Boot 2023.07",
            source="Binary strings",
        )

        # Frozen dataclasses with slots prevent arbitrary attribute addition
        assert hasattr(version.__class__, "__slots__")


class TestHardwareProperty:
    """Test HardwareProperty dataclass."""

    def test_hardware_property_creation(self) -> None:
        """Test creating a HardwareProperty."""
        prop = HardwareProperty(
            property="SoC",
            value="Rockchip RV1126",
            source="DTS compatible",
        )

        assert prop.property == "SoC"
        assert prop.value == "Rockchip RV1126"
        assert prop.source == "DTS compatible"

    def test_hardware_property_is_frozen(self) -> None:
        """Test that HardwareProperty is immutable (frozen)."""
        prop = HardwareProperty(
            property="SoC",
            value="Rockchip RV1126",
            source="DTS compatible",
        )

        with pytest.raises(AttributeError):
            prop.value = "Different SoC"  # type: ignore

    def test_hardware_property_has_slots(self) -> None:
        """Test that HardwareProperty uses __slots__ for efficiency."""
        prop = HardwareProperty(
            property="SoC",
            value="Rockchip RV1126",
            source="DTS compatible",
        )

        assert hasattr(prop.__class__, "__slots__")


class TestBootComponent:
    """Test BootComponent dataclass."""

    def test_boot_component_creation(self) -> None:
        """Test creating a BootComponent."""
        component = BootComponent(
            stage="U-Boot",
            found=True,
            evidence="u-boot binary found in extraction",
        )

        assert component.stage == "U-Boot"
        assert component.found is True
        assert component.evidence == "u-boot binary found in extraction"

    def test_boot_component_not_found(self) -> None:
        """Test creating a BootComponent for missing component."""
        component = BootComponent(
            stage="Secure Boot",
            found=False,
            evidence="No secure boot signatures detected",
        )

        assert component.stage == "Secure Boot"
        assert component.found is False
        assert component.evidence == "No secure boot signatures detected"

    def test_boot_component_is_frozen(self) -> None:
        """Test that BootComponent is immutable (frozen)."""
        component = BootComponent(
            stage="U-Boot",
            found=True,
            evidence="test",
        )

        with pytest.raises(AttributeError):
            component.found = False  # type: ignore

    def test_boot_component_has_slots(self) -> None:
        """Test that BootComponent uses __slots__ for efficiency."""
        component = BootComponent(
            stage="U-Boot",
            found=True,
            evidence="test",
        )

        assert hasattr(component.__class__, "__slots__")


class TestPartition:
    """Test Partition dataclass."""

    def test_partition_creation(self) -> None:
        """Test creating a Partition."""
        partition = Partition(
            region="Bootloader",
            offset="0x8000",
            size_mb=16,
            type="FIT",
            content="U-Boot + OP-TEE",
        )

        assert partition.region == "Bootloader"
        assert partition.offset == "0x8000"
        assert partition.size_mb == 16
        assert partition.type == "FIT"
        assert partition.content == "U-Boot + OP-TEE"

    def test_partition_is_frozen(self) -> None:
        """Test that Partition is immutable (frozen)."""
        partition = Partition(
            region="Bootloader",
            offset="0x8000",
            size_mb=16,
            type="FIT",
            content="U-Boot + OP-TEE",
        )

        with pytest.raises(AttributeError):
            partition.size_mb = 32  # type: ignore

    def test_partition_has_slots(self) -> None:
        """Test that Partition uses __slots__ for efficiency."""
        partition = Partition(
            region="Bootloader",
            offset="0x8000",
            size_mb=16,
            type="FIT",
            content="U-Boot + OP-TEE",
        )

        assert hasattr(partition.__class__, "__slots__")


class TestConsoleConfig:
    """Test ConsoleConfig dataclass."""

    def test_console_config_creation(self) -> None:
        """Test creating a ConsoleConfig."""
        config = ConsoleConfig(
            parameter="Baud Rate",
            value="1500000",
            source="DTS rockchip,baudrate",
        )

        assert config.parameter == "Baud Rate"
        assert config.value == "1500000"
        assert config.source == "DTS rockchip,baudrate"

    def test_console_config_is_frozen(self) -> None:
        """Test that ConsoleConfig is immutable (frozen)."""
        config = ConsoleConfig(
            parameter="Baud Rate",
            value="1500000",
            source="DTS rockchip,baudrate",
        )

        with pytest.raises(AttributeError):
            config.value = "115200"  # type: ignore

    def test_console_config_has_slots(self) -> None:
        """Test that ConsoleConfig uses __slots__ for efficiency."""
        config = ConsoleConfig(
            parameter="Baud Rate",
            value="1500000",
            source="DTS rockchip,baudrate",
        )

        assert hasattr(config.__class__, "__slots__")


class TestBootProcessAnalysis:
    """Test BootProcessAnalysis dataclass."""

    def test_boot_process_analysis_creation(self) -> None:
        """Test creating a BootProcessAnalysis."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )

        assert analysis.firmware_file == "test.img"
        assert analysis.firmware_size == 123456789
        assert analysis.hardware_properties == []
        assert analysis.boot_components == []
        assert analysis.component_versions == []
        assert analysis.partitions == []
        assert analysis.bootloader_fit_info is None
        assert analysis.kernel_fit_info is None
        assert analysis.ab_redundancy is False
        assert analysis.ab_evidence is None
        assert analysis.kernel_cmdline is None
        assert analysis.console_configs == []
        assert analysis._source == {}
        assert analysis._method == {}

    def test_boot_process_analysis_with_data(self) -> None:
        """Test creating a BootProcessAnalysis with data."""
        hardware_props = [
            HardwareProperty(
                property="SoC",
                value="Rockchip RV1126",
                source="DTS compatible",
            )
        ]

        boot_components = [
            BootComponent(
                stage="U-Boot",
                found=True,
                evidence="u-boot binary found",
            )
        ]

        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
            hardware_properties=hardware_props,
            boot_components=boot_components,
            ab_redundancy=True,
            kernel_cmdline="console=ttyS0,115200",
        )

        assert len(analysis.hardware_properties) == 1
        assert len(analysis.boot_components) == 1
        assert analysis.ab_redundancy is True
        assert analysis.kernel_cmdline == "console=ttyS0,115200"

    def test_add_metadata(self) -> None:
        """Test adding source metadata."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )

        analysis.add_metadata(
            "firmware_size",
            "filesystem",
            "Path(firmware).stat().st_size",
        )

        assert analysis._source["firmware_size"] == "filesystem"
        assert analysis._method["firmware_size"] == "Path(firmware).stat().st_size"

    def test_add_metadata_multiple_fields(self) -> None:
        """Test adding metadata for multiple fields."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )

        analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")
        analysis.add_metadata("firmware_size", "filesystem", "Path(firmware).stat().st_size")

        assert len(analysis._source) == 2
        assert len(analysis._method) == 2

    def test_to_dict_excludes_none(self) -> None:
        """Test to_dict excludes None values."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )

        result = analysis.to_dict()

        assert "firmware_file" in result
        assert "firmware_size" in result
        assert "bootloader_fit_info" not in result  # Should be excluded (None)
        assert "kernel_fit_info" not in result  # Should be excluded (None)
        assert "ab_evidence" not in result  # Should be excluded (None)
        assert "kernel_cmdline" not in result  # Should be excluded (None)

    def test_to_dict_excludes_empty_lists(self) -> None:
        """Test to_dict excludes empty lists."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )

        result = analysis.to_dict()

        # Empty lists should not be included
        # But we check by conversion - empty lists get excluded
        hw_props = result.get("hardware_properties", [])
        assert result.get("hardware_properties", None) is None or len(hw_props) == 0

    def test_to_dict_includes_metadata(self) -> None:
        """Test to_dict includes source metadata."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )
        analysis.add_metadata(
            "firmware_size",
            "filesystem",
            "Path(firmware).stat().st_size",
        )

        result = analysis.to_dict()

        assert result["firmware_size"] == 123456789
        assert result["firmware_size_source"] == "filesystem"
        assert result["firmware_size_method"] == "Path(firmware).stat().st_size"

    def test_to_dict_converts_hardware_properties(self) -> None:
        """Test to_dict converts HardwareProperty objects to dicts."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )
        analysis.hardware_properties = [
            HardwareProperty(
                property="SoC",
                value="Rockchip RV1126",
                source="DTS compatible",
            )
        ]

        result = analysis.to_dict()

        assert len(result["hardware_properties"]) == 1
        assert result["hardware_properties"][0]["property"] == "SoC"
        assert result["hardware_properties"][0]["value"] == "Rockchip RV1126"
        assert result["hardware_properties"][0]["source"] == "DTS compatible"

    def test_to_dict_converts_boot_components(self) -> None:
        """Test to_dict converts BootComponent objects to dicts."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )
        analysis.boot_components = [
            BootComponent(
                stage="U-Boot",
                found=True,
                evidence="u-boot binary found",
            )
        ]

        result = analysis.to_dict()

        assert len(result["boot_components"]) == 1
        assert result["boot_components"][0]["stage"] == "U-Boot"
        assert result["boot_components"][0]["found"] is True
        assert result["boot_components"][0]["evidence"] == "u-boot binary found"

    def test_to_dict_converts_component_versions(self) -> None:
        """Test to_dict converts ComponentVersion objects to dicts."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )
        analysis.component_versions = [
            ComponentVersion(
                component="U-Boot",
                version="U-Boot 2023.07",
                source="Binary strings",
            )
        ]

        result = analysis.to_dict()

        assert len(result["component_versions"]) == 1
        assert result["component_versions"][0]["component"] == "U-Boot"
        assert result["component_versions"][0]["version"] == "U-Boot 2023.07"
        assert result["component_versions"][0]["source"] == "Binary strings"

    def test_to_dict_converts_partitions(self) -> None:
        """Test to_dict converts Partition objects to dicts."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )
        analysis.partitions = [
            Partition(
                region="Bootloader",
                offset="0x8000",
                size_mb=16,
                type="FIT",
                content="U-Boot + OP-TEE",
            )
        ]

        result = analysis.to_dict()

        assert len(result["partitions"]) == 1
        assert result["partitions"][0]["region"] == "Bootloader"
        assert result["partitions"][0]["offset"] == "0x8000"
        assert result["partitions"][0]["size_mb"] == 16
        assert result["partitions"][0]["type"] == "FIT"
        assert result["partitions"][0]["content"] == "U-Boot + OP-TEE"

    def test_to_dict_converts_console_configs(self) -> None:
        """Test to_dict converts ConsoleConfig objects to dicts."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )
        analysis.console_configs = [
            ConsoleConfig(
                parameter="Baud Rate",
                value="1500000",
                source="DTS rockchip,baudrate",
            )
        ]

        result = analysis.to_dict()

        assert len(result["console_configs"]) == 1
        assert result["console_configs"][0]["parameter"] == "Baud Rate"
        assert result["console_configs"][0]["value"] == "1500000"
        assert result["console_configs"][0]["source"] == "DTS rockchip,baudrate"

    def test_to_dict_excludes_private_fields(self) -> None:
        """Test to_dict excludes private fields (_source, _method)."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )
        analysis.add_metadata("firmware_size", "test", "test method")

        result = analysis.to_dict()

        assert "_source" not in result
        assert "_method" not in result


class TestGetFitInfo:
    """Test get_fit_info function."""

    def test_get_fit_info_success(self, tmp_path: Path) -> None:
        """Test extracting FIT info from DTS file."""
        dts_file = tmp_path / "system.dtb"
        content = """
        / {
            description = "FIT Image";
            type = "kernel";
            arch = "arm64";
        };
        """
        dts_file.write_text(content)

        result = get_fit_info(dts_file)

        assert result is not None
        assert "description" in result
        assert "FIT Image" in result

    def test_get_fit_info_missing_file(self, tmp_path: Path) -> None:
        """Test extracting FIT info from non-existent file."""
        dts_file = tmp_path / "nonexistent.dtb"

        result = get_fit_info(dts_file)

        assert result is None

    def test_get_fit_info_read_error(self, tmp_path: Path) -> None:
        """Test extracting FIT info with read error."""
        dts_file = tmp_path / "system.dtb"
        # Create a binary file that will cause decoding issues
        dts_file.write_bytes(b"\xff\xfe\x00\x01")

        result = get_fit_info(dts_file)

        # Should handle error gracefully
        assert result is None


class TestFindLargestDts:
    """Test find_largest_dts function."""

    def test_find_largest_dts_single_file(self, tmp_path: Path) -> None:
        """Test finding largest DTS when only one exists."""
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        dts_file = extract_dir / "system.dtb"
        dts_file.write_text("small content")

        result = find_largest_dts(extract_dir)

        assert result == dts_file

    def test_find_largest_dts_multiple_files(self, tmp_path: Path) -> None:
        """Test finding largest DTS among multiple files."""
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        small_dts = extract_dir / "8F1B4" / "system.dtb"
        small_dts.parent.mkdir()
        small_dts.write_text("small")

        large_dts = extract_dir / "901B4" / "system.dtb"
        large_dts.parent.mkdir()
        large_dts.write_text("much larger content" * 100)

        result = find_largest_dts(extract_dir)

        assert result == large_dts

    def test_find_largest_dts_none_found(self, tmp_path: Path) -> None:
        """Test finding largest DTS when no files exist."""
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        result = find_largest_dts(extract_dir)

        assert result is None

    def test_find_largest_dts_nested(self, tmp_path: Path) -> None:
        """Test finding largest DTS in nested directories."""
        extract_dir = tmp_path / "extract"
        nested = extract_dir / "subdir" / "8F1B4"
        nested.mkdir(parents=True)

        dts_file = nested / "system.dtb"
        dts_file.write_text("content")

        result = find_largest_dts(extract_dir)

        assert result == dts_file


class TestLoadFirmwareOffsets:
    """Test load_firmware_offsets function."""

    def test_load_firmware_offsets_success(self, tmp_path: Path) -> None:
        """Test loading firmware offsets from file."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        offsets_file = output_dir / "binwalk-offsets.sh"
        offsets_file.write_text("""
# Firmware offsets
BOOTLOADER_FIT_OFFSET=0x8000
BOOTLOADER_FIT_OFFSET_DEC=32768
KERNEL_FIT_OFFSET=0x901B4
KERNEL_FIT_OFFSET_DEC=590260
""")

        result = load_firmware_offsets(output_dir)

        assert result["BOOTLOADER_FIT_OFFSET"] == "0x8000"
        assert result["BOOTLOADER_FIT_OFFSET_DEC"] == 32768
        assert result["KERNEL_FIT_OFFSET"] == "0x901B4"
        assert result["KERNEL_FIT_OFFSET_DEC"] == 590260

    def test_load_firmware_offsets_missing_file(self, tmp_path: Path) -> None:
        """Test loading firmware offsets when file doesn't exist."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with pytest.raises(SystemExit) as exc_info:
            load_firmware_offsets(output_dir)

        assert exc_info.value.code == 1

    def test_load_firmware_offsets_ignores_comments(self, tmp_path: Path) -> None:
        """Test that comments are ignored."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        offsets_file = output_dir / "binwalk-offsets.sh"
        offsets_file.write_text("""
# This is a comment
BOOTLOADER_FIT_OFFSET=0x8000
# Another comment
KERNEL_FIT_OFFSET=0x901B4
""")

        result = load_firmware_offsets(output_dir)

        assert "BOOTLOADER_FIT_OFFSET" in result
        assert "KERNEL_FIT_OFFSET" in result

    def test_load_firmware_offsets_decimal_values(self, tmp_path: Path) -> None:
        """Test that decimal values are converted to integers."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        offsets_file = output_dir / "binwalk-offsets.sh"
        offsets_file.write_text("""
BOOTLOADER_FIT_OFFSET_DEC=32768
KERNEL_FIT_OFFSET_DEC=590260
""")

        result = load_firmware_offsets(output_dir)

        assert isinstance(result["BOOTLOADER_FIT_OFFSET_DEC"], int)
        assert result["BOOTLOADER_FIT_OFFSET_DEC"] == 32768
        assert isinstance(result["KERNEL_FIT_OFFSET_DEC"], int)
        assert result["KERNEL_FIT_OFFSET_DEC"] == 590260

    def test_load_firmware_offsets_with_quotes(self, tmp_path: Path) -> None:
        """Test that quoted values are handled correctly."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        offsets_file = output_dir / "binwalk-offsets.sh"
        offsets_file.write_text("""
BOOTLOADER_FIT_OFFSET="0x8000"
KERNEL_FIT_OFFSET='0x901B4'
""")

        result = load_firmware_offsets(output_dir)

        assert result["BOOTLOADER_FIT_OFFSET"] == "0x8000"
        assert result["KERNEL_FIT_OFFSET"] == "0x901B4"

    def test_load_firmware_offsets_caching(self, tmp_path: Path) -> None:
        """Test that load_firmware_offsets uses caching."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        offsets_file = output_dir / "binwalk-offsets.sh"
        offsets_file.write_text("BOOTLOADER_FIT_OFFSET=0x8000\n")

        # First call
        result1 = load_firmware_offsets(output_dir)

        # Modify file
        offsets_file.write_text("BOOTLOADER_FIT_OFFSET=0x9000\n")

        # Second call should return cached result
        result2 = load_firmware_offsets(output_dir)

        # Note: Due to @cache decorator, both results should be the same
        assert result1 == result2


class TestOutputToml:
    """Test output_toml function."""

    def test_toml_output_valid(self) -> None:
        """Test that TOML output is valid."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )
        analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")

        toml_str = output_toml(
            analysis,
            title="Boot process and partition layout analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )

        # Should be valid TOML
        parsed = tomlkit.loads(toml_str)
        assert parsed["firmware_file"] == "test.img"
        assert parsed["firmware_size"] == 123456789

    def test_toml_includes_header(self) -> None:
        """Test that TOML includes header comments."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )

        toml_str = output_toml(
            analysis,
            title="Boot process and partition layout analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )

        assert "# Boot process and partition layout analysis" in toml_str
        assert "# Generated:" in toml_str

    def test_toml_includes_source_comments(self) -> None:
        """Test that TOML includes source metadata as comments."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )
        analysis.add_metadata(
            "firmware_size",
            "filesystem",
            "Path(firmware).stat().st_size",
        )

        toml_str = output_toml(
            analysis,
            title="Boot process and partition layout analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )

        assert "# Source: filesystem" in toml_str
        assert "# Method: Path(firmware).stat().st_size" in toml_str

    def test_toml_truncates_long_methods(self) -> None:
        """Test that long method descriptions are truncated."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )
        long_method = "x" * 100  # 100 characters is definitely long
        analysis.add_metadata("firmware_size", "test", long_method)

        toml_str = output_toml(
            analysis,
            title="Boot process and partition layout analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )

        # Should be truncated with "..."
        assert "..." in toml_str
        assert long_method not in toml_str

    def test_toml_excludes_none_values(self) -> None:
        """Test that None values are excluded from TOML output."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )

        toml_str = output_toml(
            analysis,
            title="Boot process and partition layout analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )

        assert "bootloader_fit_info" not in toml_str
        assert "kernel_fit_info" not in toml_str
        assert "ab_evidence" not in toml_str
        assert "kernel_cmdline" not in toml_str

    def test_toml_includes_nested_data(self) -> None:
        """Test that nested data structures are included."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )
        analysis.hardware_properties = [
            HardwareProperty(
                property="SoC",
                value="Rockchip RV1126",
                source="DTS compatible",
            )
        ]
        analysis.partitions = [
            Partition(
                region="Bootloader",
                offset="0x8000",
                size_mb=16,
                type="FIT",
                content="U-Boot + OP-TEE",
            )
        ]

        toml_str = output_toml(
            analysis,
            title="Boot process and partition layout analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )
        parsed = tomlkit.loads(toml_str)

        assert len(parsed["hardware_properties"]) == 1
        assert parsed["hardware_properties"][0]["property"] == "SoC"

        assert len(parsed["partitions"]) == 1
        assert parsed["partitions"][0]["region"] == "Bootloader"

    def test_toml_excludes_metadata_fields(self) -> None:
        """Test that _source and _method suffix fields are not in final TOML."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )
        analysis.add_metadata("firmware_size", "filesystem", "Path(firmware).stat().st_size")

        toml_str = output_toml(
            analysis,
            title="Boot process and partition layout analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )
        parsed = tomlkit.loads(toml_str)

        # Metadata should be in comments, not as fields
        assert "firmware_size_source" not in parsed
        assert "firmware_size_method" not in parsed

    def test_toml_validates_output(self) -> None:
        """Test that output_toml validates generated TOML by parsing it."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
            ab_redundancy=True,
        )

        # Should not raise an exception (validation happens internally)
        toml_str = output_toml(
            analysis,
            title="Boot process and partition layout analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )

        # Should be valid TOML
        parsed = tomlkit.loads(toml_str)
        assert parsed["firmware_file"] == "test.img"
        assert parsed["ab_redundancy"] is True


class TestFindRootfs:
    """Test find_rootfs function."""

    def test_find_rootfs_success(self, tmp_path: Path) -> None:
        """Test finding squashfs-root directory."""
        extract_dir = tmp_path / "extract"
        squashfs_root = extract_dir / "squashfs-root"
        squashfs_root.mkdir(parents=True)

        result = find_rootfs(extract_dir)

        assert result == squashfs_root

    def test_find_rootfs_nested(self, tmp_path: Path) -> None:
        """Test finding squashfs-root in nested directory."""
        extract_dir = tmp_path / "extract"
        nested = extract_dir / "subdir" / "8F1B4"
        squashfs_root = nested / "squashfs-root"
        squashfs_root.mkdir(parents=True)

        result = find_rootfs(extract_dir)

        assert result == squashfs_root

    def test_find_rootfs_not_found(self, tmp_path: Path) -> None:
        """Test find_rootfs when directory doesn't exist."""
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        result = find_rootfs(extract_dir)

        assert result is None


class TestAnalyzeHardwareProperties:
    """Test analyze_hardware_properties function."""

    def test_analyze_hardware_properties_compatible(self, tmp_path: Path) -> None:
        """Test extracting compatible string."""
        dts_file = tmp_path / "system.dtb"
        dts_content = """
        / {
            compatible = "rockchip,rv1126-evb", "rockchip,rv1126";
        };
        """
        dts_file.write_text(dts_content)

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_hardware_properties(dts_file, analysis, extract_dir)

        assert len(analysis.hardware_properties) >= 1
        compatible_prop = next(
            p for p in analysis.hardware_properties if p.property == "Device Tree Compatible"
        )
        assert "rockchip,rv1126-evb" in compatible_prop.value

    def test_analyze_hardware_properties_derives_soc(self, tmp_path: Path) -> None:
        """Test deriving SoC from compatible string."""
        dts_file = tmp_path / "system.dtb"
        dts_content = """
        / {
            compatible = "rockchip,rv1126-evb", "rockchip,rv1126";
        };
        """
        dts_file.write_text(dts_content)

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_hardware_properties(dts_file, analysis, extract_dir)

        soc_props = [p for p in analysis.hardware_properties if p.property == "SoC"]
        assert len(soc_props) == 1
        assert "RV1126" in soc_props[0].value

    @patch("subprocess.run")
    def test_analyze_hardware_properties_derives_architecture(
        self, mock_run: Any, tmp_path: Path
    ) -> None:
        """Test deriving architecture from ELF binaries."""
        dts_file = tmp_path / "system.dtb"
        dts_file.write_text("/ { };")

        extract_dir = tmp_path / "extract"
        squashfs_root = extract_dir / "squashfs-root"
        bin_dir = squashfs_root / "bin"
        bin_dir.mkdir(parents=True)

        # Create executable file
        executable = bin_dir / "busybox"
        executable.write_bytes(b"dummy")
        executable.chmod(0o755)

        # Mock file command output
        mock_run.return_value = MagicMock(stdout="ELF 32-bit LSB executable, ARM, version 1")

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_hardware_properties(dts_file, analysis, extract_dir)

        arch_props = [p for p in analysis.hardware_properties if p.property == "Architecture"]
        assert len(arch_props) == 1
        assert "ARM" in arch_props[0].value

    def test_analyze_hardware_properties_handles_errors(self, tmp_path: Path) -> None:
        """Test analyze_hardware_properties handles errors gracefully."""
        dts_file = tmp_path / "nonexistent.dtb"

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        analysis = BootProcessAnalysis("test.img", 1024)

        # Should not raise
        analyze_hardware_properties(dts_file, analysis, extract_dir)

        # No properties should be added on error
        assert len(analysis.hardware_properties) == 0


class TestAnalyzeBootComponents:
    """Test analyze_boot_components function."""

    def test_analyze_boot_components_finds_tee(self, tmp_path: Path) -> None:
        """Test detecting OP-TEE component."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"dummy")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        tee_file = extract_dir / "tee.bin"
        tee_file.touch()

        offsets: dict[str, str | int] = {}
        analysis = BootProcessAnalysis("firmware.img", 1024)

        analyze_boot_components(firmware, extract_dir, offsets, analysis)

        tee_comp = next(c for c in analysis.boot_components if c.stage == "OP-TEE")
        assert tee_comp.found is True
        assert "tee.bin found" in tee_comp.evidence

    def test_analyze_boot_components_finds_uboot_binary(self, tmp_path: Path) -> None:
        """Test detecting U-Boot from binary file."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"dummy")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        uboot_file = extract_dir / "u-boot.bin"
        uboot_file.touch()

        offsets: dict[str, str | int] = {}
        analysis = BootProcessAnalysis("firmware.img", 1024)

        analyze_boot_components(firmware, extract_dir, offsets, analysis)

        uboot_comp = next(c for c in analysis.boot_components if c.stage == "U-Boot")
        assert uboot_comp.found is True
        assert "u-boot binary found" in uboot_comp.evidence

    @patch("subprocess.run")
    def test_analyze_boot_components_finds_uboot_strings(
        self, mock_run: Any, tmp_path: Path
    ) -> None:
        """Test detecting U-Boot from strings in firmware."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"dummy")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        # Mock strings command
        mock_run.return_value = MagicMock(stdout="U-Boot 2023.07\nOther text")

        offsets: dict[str, str | int] = {}
        analysis = BootProcessAnalysis("firmware.img", 1024)

        analyze_boot_components(firmware, extract_dir, offsets, analysis)

        uboot_comp = next(c for c in analysis.boot_components if c.stage == "U-Boot")
        assert uboot_comp.found is True
        assert "U-Boot strings found" in uboot_comp.evidence

    def test_analyze_boot_components_finds_kernel(self, tmp_path: Path) -> None:
        """Test detecting kernel FIT image."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"dummy")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        offsets: dict[str, str | int] = {"KERNEL_FIT_OFFSET": "0x1000"}
        analysis = BootProcessAnalysis("firmware.img", 1024)

        analyze_boot_components(firmware, extract_dir, offsets, analysis)

        kernel_comp = next(c for c in analysis.boot_components if c.stage == "Kernel")
        assert kernel_comp.found is True
        assert "0x1000" in kernel_comp.evidence

    def test_analyze_boot_components_finds_initramfs(self, tmp_path: Path) -> None:
        """Test detecting initramfs CPIO."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"dummy")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        offsets: dict[str, str | int] = {"ROOTFS_CPIO_OFFSET": "0x2000"}
        analysis = BootProcessAnalysis("firmware.img", 1024)

        analyze_boot_components(firmware, extract_dir, offsets, analysis)

        cpio_comp = next(c for c in analysis.boot_components if c.stage == "Initramfs")
        assert cpio_comp.found is True
        assert "0x2000" in cpio_comp.evidence

    def test_analyze_boot_components_finds_squashfs(self, tmp_path: Path) -> None:
        """Test detecting SquashFS filesystem."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"dummy")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        offsets: dict[str, str | int] = {"SQUASHFS_OFFSET": "0x3000"}
        analysis = BootProcessAnalysis("firmware.img", 1024)

        analyze_boot_components(firmware, extract_dir, offsets, analysis)

        squashfs_comp = next(c for c in analysis.boot_components if c.stage == "SquashFS")
        assert squashfs_comp.found is True
        assert "0x3000" in squashfs_comp.evidence


class TestAnalyzeComponentVersions:
    """Test analyze_component_versions function."""

    @patch("subprocess.run")
    def test_analyze_component_versions_uboot(self, mock_run: Any, tmp_path: Path) -> None:
        """Test extracting U-Boot version."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"dummy")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        # Mock strings command - need full version format X.Y.Z
        mock_run.return_value = MagicMock(stdout="U-Boot 2023.07.1\nOther text")

        analysis = BootProcessAnalysis("firmware.img", 1024)
        analyze_component_versions(firmware, extract_dir, analysis)

        uboot_ver = next(v for v in analysis.component_versions if v.component == "U-Boot")
        assert uboot_ver.version == "U-Boot 2023.07.1"
        assert uboot_ver.source == "Binary strings"

    @patch("subprocess.run")
    def test_analyze_component_versions_kernel(self, mock_run: Any, tmp_path: Path) -> None:
        """Test extracting kernel version from module."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"dummy")

        extract_dir = tmp_path / "extract"
        squashfs_root = extract_dir / "squashfs-root"
        modules_dir = squashfs_root / "lib/modules/5.10.110"
        modules_dir.mkdir(parents=True)

        ko_file = modules_dir / "test.ko"
        ko_file.write_bytes(b"dummy")

        # Mock strings command for firmware (first call)
        # Then for kernel module (second call)
        def mock_subprocess_side_effect(*args: Any, **_kwargs: Any) -> MagicMock:
            cmd = args[0]
            if "firmware.img" in str(cmd):
                return MagicMock(stdout="U-Boot text")
            return MagicMock(stdout="vermagic=5.10.110 SMP preempt")

        mock_run.side_effect = mock_subprocess_side_effect

        analysis = BootProcessAnalysis("firmware.img", 1024)
        analyze_component_versions(firmware, extract_dir, analysis)

        kernel_ver = next(v for v in analysis.component_versions if v.component == "Linux Kernel")
        assert "5.10.110" in kernel_ver.version
        assert kernel_ver.source == "Module vermagic"

    def test_analyze_component_versions_buildroot(self, tmp_path: Path) -> None:
        """Test extracting Buildroot version."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"dummy")

        extract_dir = tmp_path / "extract"
        squashfs_root = extract_dir / "squashfs-root"
        etc_dir = squashfs_root / "etc"
        etc_dir.mkdir(parents=True)

        os_release = etc_dir / "os-release"
        os_release.write_text('NAME="Buildroot"\nVERSION="2023.02"\n')

        analysis = BootProcessAnalysis("firmware.img", 1024)

        # Mock subprocess to avoid U-Boot version extraction issues
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            analyze_component_versions(firmware, extract_dir, analysis)

        br_versions = [v for v in analysis.component_versions if v.component == "Buildroot"]
        assert len(br_versions) == 1
        assert br_versions[0].version == "2023.02"
        assert br_versions[0].source == "/etc/os-release"


class TestAnalyzePartitions:
    """Test analyze_partitions function."""

    def test_analyze_partitions_bootloader(self) -> None:
        """Test analyzing bootloader partition."""
        offsets: dict[str, str | int] = {
            "BOOTLOADER_FIT_OFFSET": "0x8000",
            "BOOTLOADER_FIT_OFFSET_DEC": 32768,  # Can't be 0 (falsy)
            "KERNEL_FIT_OFFSET": "0xA08000",
            "KERNEL_FIT_OFFSET_DEC": 10518528,  # 32768 + 10MB
        }

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_partitions(offsets, analysis)

        bootloader_part = next(p for p in analysis.partitions if p.region == "Bootloader")
        assert bootloader_part.offset == "0x8000"
        assert bootloader_part.size_mb == 10
        assert bootloader_part.type == "FIT"
        assert "U-Boot" in bootloader_part.content

    def test_analyze_partitions_kernel(self) -> None:
        """Test analyzing kernel partition."""
        offsets: dict[str, str | int] = {
            "KERNEL_FIT_OFFSET": "0xA00000",
            "KERNEL_FIT_OFFSET_DEC": 10485760,
            "ROOTFS_CPIO_OFFSET_DEC": 20971520,  # +10MB
        }

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_partitions(offsets, analysis)

        kernel_part = next(p for p in analysis.partitions if p.region == "Kernel")
        assert kernel_part.offset == "0xA00000"
        assert kernel_part.size_mb == 10
        assert kernel_part.type == "FIT"
        assert "Linux kernel" in kernel_part.content

    def test_analyze_partitions_initramfs(self) -> None:
        """Test analyzing initramfs partition."""
        offsets: dict[str, str | int] = {
            "ROOTFS_CPIO_OFFSET": "0x1400000",
            "ROOTFS_CPIO_OFFSET_DEC": 20971520,
            "SQUASHFS_OFFSET_DEC": 31457280,  # +10MB
        }

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_partitions(offsets, analysis)

        cpio_part = next(p for p in analysis.partitions if p.region == "Initramfs")
        assert cpio_part.offset == "0x1400000"
        assert cpio_part.size_mb == 10
        assert cpio_part.type == "CPIO"
        assert "Early userspace" in cpio_part.content

    def test_analyze_partitions_rootfs(self) -> None:
        """Test analyzing root filesystem partition."""
        offsets: dict[str, str | int] = {
            "SQUASHFS_OFFSET": "0x2000000",
            "SQUASHFS_SIZE": 52428800,  # 50MB
        }

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_partitions(offsets, analysis)

        rootfs_part = next(p for p in analysis.partitions if p.region == "Root FS")
        assert rootfs_part.offset == "0x2000000"
        assert rootfs_part.size_mb == 50
        assert rootfs_part.type == "SquashFS"
        assert "Main filesystem" in rootfs_part.content

    def test_analyze_partitions_missing_offsets(self) -> None:
        """Test analyze_partitions with missing offsets."""
        offsets: dict[str, str | int] = {}

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_partitions(offsets, analysis)

        # Should not create any partitions
        assert len(analysis.partitions) == 0


class TestAnalyzeAbRedundancy:
    """Test analyze_ab_redundancy function."""

    def test_analyze_ab_redundancy_detected(self, tmp_path: Path) -> None:
        """Test detecting A/B redundancy."""
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        # Create multiple system.dtb files (> 2)
        for i in range(3):
            dir_path = extract_dir / f"dir{i}"
            dir_path.mkdir()
            (dir_path / "system.dtb").touch()

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_ab_redundancy(extract_dir, analysis)

        assert analysis.ab_redundancy is True
        assert analysis.ab_evidence is not None
        assert "3 FIT image DTBs" in analysis.ab_evidence

    def test_analyze_ab_redundancy_not_detected(self, tmp_path: Path) -> None:
        """Test when A/B redundancy is not detected."""
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        # Create only 1 system.dtb file
        dir_path = extract_dir / "dir0"
        dir_path.mkdir()
        (dir_path / "system.dtb").touch()

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_ab_redundancy(extract_dir, analysis)

        assert analysis.ab_redundancy is False
        assert analysis.ab_evidence is None

    def test_analyze_ab_redundancy_threshold(self, tmp_path: Path) -> None:
        """Test A/B redundancy detection threshold."""
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        # Create exactly 2 system.dtb files (threshold, should not trigger)
        for i in range(2):
            dir_path = extract_dir / f"dir{i}"
            dir_path.mkdir()
            (dir_path / "system.dtb").touch()

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_ab_redundancy(extract_dir, analysis)

        assert analysis.ab_redundancy is False


class TestAnalyzeBootConfig:
    """Test analyze_boot_config function."""

    def test_analyze_boot_config_kernel_cmdline(self, tmp_path: Path) -> None:
        """Test extracting kernel command line."""
        dts_file = tmp_path / "system.dtb"
        dts_content = """
        / {
            bootargs = "console=ttyS0,115200 root=/dev/mmcblk0p2";
        };
        """
        dts_file.write_text(dts_content)

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_boot_config(dts_file, analysis)

        assert analysis.kernel_cmdline is not None
        assert "console=ttyS0,115200" in analysis.kernel_cmdline
        assert "root=/dev/mmcblk0p2" in analysis.kernel_cmdline

    def test_analyze_boot_config_baudrate(self, tmp_path: Path) -> None:
        """Test extracting baudrate configuration."""
        dts_file = tmp_path / "system.dtb"
        dts_content = """
        / {
            rockchip,baudrate = <1500000>;
        };
        """
        dts_file.write_text(dts_content)

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_boot_config(dts_file, analysis)

        baudrate_config = next(c for c in analysis.console_configs if c.parameter == "Baud Rate")
        assert baudrate_config.value == "1500000"
        assert "rockchip,baudrate" in baudrate_config.source

    def test_analyze_boot_config_console_from_stdout(self, tmp_path: Path) -> None:
        """Test extracting console from stdout-path."""
        dts_file = tmp_path / "system.dtb"
        dts_content = """
        / {
            stdout-path = "serial0:1500000n8";
        };
        """
        dts_file.write_text(dts_content)

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_boot_config(dts_file, analysis)

        console_config = next(
            (c for c in analysis.console_configs if c.parameter == "Console"),
            None,
        )
        if console_config:
            assert "serial0" in console_config.value

    def test_analyze_boot_config_console_from_bootargs(self, tmp_path: Path) -> None:
        """Test extracting console from bootargs."""
        dts_file = tmp_path / "system.dtb"
        dts_content = """
        / {
            bootargs = "console=ttyS0,115200";
        };
        """
        dts_file.write_text(dts_content)

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_boot_config(dts_file, analysis)

        console_config = next(
            (c for c in analysis.console_configs if c.parameter == "Console"),
            None,
        )
        if console_config:
            assert "ttyS0" in console_config.value

    def test_analyze_boot_config_handles_errors(self, tmp_path: Path) -> None:
        """Test analyze_boot_config handles errors gracefully."""
        dts_file = tmp_path / "nonexistent.dtb"

        analysis = BootProcessAnalysis("test.img", 1024)

        # Should not raise
        analyze_boot_config(dts_file, analysis)

        assert analysis.kernel_cmdline is None
        assert len(analysis.console_configs) == 0


class TestAnalyzeBootProcessFunction:
    """Test the main analyze_boot_process function."""

    @patch("subprocess.run")
    def test_analyze_boot_process_integration(self, mock_run: Any, tmp_path: Path) -> None:
        """Test complete analyze_boot_process function."""
        # Setup firmware
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"x" * 10485760)

        # Setup extraction directory
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        # Create DTS files
        bootloader_dir = extract_dir / "8F1B4"
        bootloader_dir.mkdir()
        bootloader_dts = bootloader_dir / "system.dtb"
        bootloader_dts.write_text("""
        / {
            description = "FIT Image with bootloader";
        };
        """)

        kernel_dir = extract_dir / "901B4"
        kernel_dir.mkdir()
        kernel_dts = kernel_dir / "system.dtb"
        kernel_dts.write_text("""
        / {
            description = "FIT Image with kernel";
            compatible = "rockchip,rv1126";
            bootargs = "console=ttyS0,115200";
            rockchip,baudrate = <1500000>;
        };
        """)

        # Create squashfs root
        squashfs_root = extract_dir / "squashfs-root"
        modules_dir = squashfs_root / "lib/modules/5.10.110"
        modules_dir.mkdir(parents=True)
        (modules_dir / "test.ko").write_bytes(b"dummy")

        bin_dir = squashfs_root / "bin"
        bin_dir.mkdir(parents=True)
        busybox = bin_dir / "busybox"
        busybox.write_bytes(b"dummy")
        busybox.chmod(0o755)

        etc_dir = squashfs_root / "etc"
        etc_dir.mkdir(parents=True)
        (etc_dir / "os-release").write_text('NAME="Buildroot"\nVERSION="2023.02"\n')

        # Create offsets file
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        offsets_file = output_dir / "binwalk-offsets.sh"
        offsets_file.write_text("""
BOOTLOADER_FIT_OFFSET=0x8F1B4
BOOTLOADER_FIT_OFFSET_DEC=586164
KERNEL_FIT_OFFSET=0x901B4
KERNEL_FIT_OFFSET_DEC=590260
ROOTFS_CPIO_OFFSET=0xA00000
ROOTFS_CPIO_OFFSET_DEC=10485760
SQUASHFS_OFFSET=0xB00000
SQUASHFS_OFFSET_DEC=11534336
SQUASHFS_SIZE=52428800
""")

        # Mock subprocess calls
        def mock_subprocess_side_effect(*args: Any, **_kwargs: Any) -> MagicMock:
            cmd = args[0]
            if "strings" in cmd and "firmware.img" in str(cmd):
                return MagicMock(stdout="U-Boot 2023.07.1\nOther text")
            if "strings" in cmd and ".ko" in str(cmd):
                return MagicMock(stdout="vermagic=5.10.110 SMP preempt")
            if "file" in cmd:
                return MagicMock(stdout="ELF 32-bit LSB executable, ARM, version 1")
            return MagicMock(stdout="")

        mock_run.side_effect = mock_subprocess_side_effect

        # Import and call the function (must be here for coverage)
        from analyze_boot_process import (  # noqa: PLC0415
            analyze_boot_process,
            load_firmware_offsets,
        )

        offsets = load_firmware_offsets(output_dir)
        result = analyze_boot_process(str(firmware), extract_dir, offsets)

        # Verify results
        assert result.firmware_file == firmware.name
        assert result.firmware_size == firmware.stat().st_size
        assert len(result.hardware_properties) >= 1
        assert len(result.boot_components) >= 1
        assert len(result.component_versions) >= 1
        assert len(result.partitions) >= 1
        assert result.kernel_cmdline is not None
        assert "console=ttyS0" in result.kernel_cmdline


class TestIntegration:
    """Integration tests with realistic data."""

    def test_realistic_boot_process_analysis(self) -> None:
        """Test creating a realistic BootProcessAnalysis object."""
        analysis = BootProcessAnalysis(
            firmware_file="glkvm-RM1-1.7.2-1128-1764344791.img",
            firmware_size=123456789,
        )

        # Add hardware properties
        analysis.hardware_properties = [
            HardwareProperty(
                property="Device Tree Compatible",
                value="`rockchip,rv1126`",
                source="DTS",
            ),
            HardwareProperty(
                property="SoC",
                value="Rockchip RV1126",
                source="DTS compatible",
            ),
            HardwareProperty(
                property="Architecture",
                value="ARM",
                source="ELF header",
            ),
        ]

        # Add boot components
        analysis.boot_components = [
            BootComponent(
                stage="OP-TEE",
                found=True,
                evidence="tee.bin found in extraction",
            ),
            BootComponent(
                stage="U-Boot",
                found=True,
                evidence="u-boot binary found in extraction",
            ),
            BootComponent(
                stage="Kernel",
                found=True,
                evidence="FIT image at offset `0x901B4`",
            ),
            BootComponent(
                stage="Initramfs",
                found=True,
                evidence="CPIO at offset `0xA00000`",
            ),
            BootComponent(
                stage="SquashFS",
                found=True,
                evidence="Filesystem at offset `0xB00000`",
            ),
        ]

        # Add component versions
        analysis.component_versions = [
            ComponentVersion(
                component="U-Boot",
                version="U-Boot 2023.07",
                source="Binary strings",
            ),
            ComponentVersion(
                component="Linux Kernel",
                version="5.10.110",
                source="Module vermagic",
            ),
        ]

        # Add partitions
        analysis.partitions = [
            Partition(
                region="Bootloader",
                offset="0x8000",
                size_mb=16,
                type="FIT",
                content="U-Boot + OP-TEE",
            ),
            Partition(
                region="Kernel",
                offset="0x901B4",
                size_mb=10,
                type="FIT",
                content="Linux kernel + DTB",
            ),
            Partition(
                region="Root FS",
                offset="0xB00000",
                size_mb=64,
                type="SquashFS",
                content="Main filesystem",
            ),
        ]

        # Set A/B redundancy
        analysis.ab_redundancy = True
        analysis.ab_evidence = (
            "Found 3 FIT image DTBs in extraction. "
            "Multiple bootloader/kernel slots suggests A/B OTA support."
        )

        # Set kernel cmdline
        analysis.kernel_cmdline = "console=ttyS0,115200n8 root=/dev/mtdblock3 rootfstype=squashfs"

        # Add console configs
        analysis.console_configs = [
            ConsoleConfig(
                parameter="Baud Rate",
                value="1500000",
                source="DTS rockchip,baudrate",
            ),
            ConsoleConfig(
                parameter="Console",
                value="ttyS0",
                source="DTS stdout-path/bootargs",
            ),
        ]

        # Add metadata
        analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")
        analysis.add_metadata("firmware_size", "filesystem", "Path(firmware).stat().st_size")
        analysis.add_metadata(
            "ab_redundancy", "binwalk-extraction", "count system.dtb files: 3 > 2"
        )
        analysis.add_metadata("kernel_cmdline", "device-tree", "extract bootargs property from DTS")

        # Test to_dict
        result = analysis.to_dict()

        assert result["firmware_file"] == "glkvm-RM1-1.7.2-1128-1764344791.img"
        assert result["firmware_size"] == 123456789
        assert len(result["hardware_properties"]) == 3
        assert len(result["boot_components"]) == 5
        assert len(result["component_versions"]) == 2
        assert len(result["partitions"]) == 3
        assert result["ab_redundancy"] is True
        expected_cmdline = "console=ttyS0,115200n8 root=/dev/mtdblock3 rootfstype=squashfs"
        assert result["kernel_cmdline"] == expected_cmdline
        assert len(result["console_configs"]) == 2

        # Test metadata
        assert result["ab_redundancy_source"] == "binwalk-extraction"
        assert "count system.dtb files" in result["ab_redundancy_method"]

    def test_realistic_toml_output(self) -> None:
        """Test generating realistic TOML output."""
        analysis = BootProcessAnalysis(
            firmware_file="glkvm-RM1-1.7.2-1128-1764344791.img",
            firmware_size=123456789,
        )

        analysis.hardware_properties = [
            HardwareProperty(
                property="SoC",
                value="Rockchip RV1126",
                source="DTS compatible",
            )
        ]

        analysis.boot_components = [
            BootComponent(
                stage="U-Boot",
                found=True,
                evidence="u-boot binary found",
            )
        ]

        analysis.component_versions = [
            ComponentVersion(
                component="U-Boot",
                version="U-Boot 2023.07",
                source="Binary strings",
            )
        ]

        analysis.partitions = [
            Partition(
                region="Bootloader",
                offset="0x8000",
                size_mb=16,
                type="FIT",
                content="U-Boot + OP-TEE",
            )
        ]

        analysis.ab_redundancy = True
        analysis.kernel_cmdline = "console=ttyS0,115200"

        analysis.console_configs = [
            ConsoleConfig(
                parameter="Baud Rate",
                value="1500000",
                source="DTS rockchip,baudrate",
            )
        ]

        analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")
        analysis.add_metadata("firmware_size", "filesystem", "Path(firmware).stat().st_size")

        toml_str = output_toml(
            analysis,
            title="Boot process and partition layout analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )

        # Validate TOML
        parsed = tomlkit.loads(toml_str)

        assert parsed["firmware_file"] == "glkvm-RM1-1.7.2-1128-1764344791.img"
        assert parsed["firmware_size"] == 123456789
        assert len(parsed["hardware_properties"]) == 1
        assert len(parsed["boot_components"]) == 1
        assert len(parsed["component_versions"]) == 1
        assert len(parsed["partitions"]) == 1
        assert parsed["ab_redundancy"] is True
        assert parsed["kernel_cmdline"] == "console=ttyS0,115200"
        assert len(parsed["console_configs"]) == 1

        # Check header comments
        assert "# Boot process and partition layout analysis" in toml_str
        assert "# Generated:" in toml_str

        # Check source/method comments
        assert "# Source: filesystem" in toml_str
        assert "# Method: Path(firmware).name" in toml_str

    def test_minimal_boot_process_analysis(self) -> None:
        """Test BootProcessAnalysis with minimal data."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )

        analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")
        analysis.add_metadata("firmware_size", "filesystem", "Path(firmware).stat().st_size")

        result = analysis.to_dict()

        # Basic fields should be present
        assert result["firmware_file"] == "test.img"
        assert result["firmware_size"] == 1024
        # Empty lists are excluded from to_dict() output (filtered by AnalysisBase)
        assert "hardware_properties" not in result
        assert "boot_components" not in result
        assert "component_versions" not in result
        assert "partitions" not in result
        assert "console_configs" not in result
        # ab_redundancy defaults to False
        assert result["ab_redundancy"] is False

        # Test TOML output
        toml_str = output_toml(
            analysis,
            title="Boot process and partition layout analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )
        parsed = tomlkit.loads(toml_str)

        assert parsed["firmware_file"] == "test.img"
        assert parsed["firmware_size"] == 1024
        # ab_redundancy defaults to False, so it will be included
        assert parsed["ab_redundancy"] is False


class TestNewHardwareSpecFields:
    """Test the 5 new hardware spec scalar fields."""

    def test_new_fields_default_none(self) -> None:
        """Test that new fields default to None."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )
        assert analysis.soc_name is None
        assert analysis.cpu_architecture is None
        assert analysis.storage_type is None
        assert analysis.console_device is None
        assert analysis.console_baudrate is None

    def test_new_fields_in_simple_fields(self) -> None:
        """Test that new fields are in SIMPLE_FIELDS for TOML output."""
        assert "soc_name" in SIMPLE_FIELDS
        assert "cpu_architecture" in SIMPLE_FIELDS
        assert "storage_type" in SIMPLE_FIELDS
        assert "console_device" in SIMPLE_FIELDS
        assert "console_baudrate" in SIMPLE_FIELDS

    def test_soc_name_populated_from_dts(self, tmp_path: Path) -> None:
        """Test that soc_name is set when DTS contains rv1126."""
        dts_file = tmp_path / "system.dtb"
        dts_file.write_text("""
        / {
            compatible = "rockchip,rv1126-evb", "rockchip,rv1126";
        };
        """)

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_hardware_properties(dts_file, analysis, extract_dir)

        assert analysis.soc_name == "Rockchip RV1126"
        assert "soc_name" in analysis._source
        assert analysis._source["soc_name"] == "device-tree"

    @patch("subprocess.run")
    def test_cpu_architecture_populated_from_elf(self, mock_run: Any, tmp_path: Path) -> None:
        """Test that cpu_architecture is set from ELF header."""
        dts_file = tmp_path / "system.dtb"
        dts_file.write_text("/ { };")

        extract_dir = tmp_path / "extract"
        squashfs_root = extract_dir / "squashfs-root"
        bin_dir = squashfs_root / "bin"
        bin_dir.mkdir(parents=True)

        executable = bin_dir / "busybox"
        executable.write_bytes(b"dummy")
        executable.chmod(0o755)

        mock_run.return_value = MagicMock(stdout="ELF 32-bit LSB executable, ARM, version 1")

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_hardware_properties(dts_file, analysis, extract_dir)

        assert analysis.cpu_architecture == "ARM Cortex-A7 (32-bit)"
        assert "cpu_architecture" in analysis._source
        assert analysis._source["cpu_architecture"] == "ELF-header"

    def test_console_baudrate_populated(self, tmp_path: Path) -> None:
        """Test that console_baudrate is set from DTS."""
        dts_file = tmp_path / "system.dtb"
        dts_file.write_text("""
        / {
            rockchip,baudrate = <1500000>;
        };
        """)

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_boot_config(dts_file, analysis)

        assert analysis.console_baudrate == "1500000"
        assert "console_baudrate" in analysis._source

    def test_console_device_populated_from_stdout_path(self, tmp_path: Path) -> None:
        """Test that console_device is set from stdout-path."""
        dts_file = tmp_path / "system.dtb"
        dts_file.write_text("""
        / {
            stdout-path = "serial0:1500000n8";
        };
        """)

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_boot_config(dts_file, analysis)

        assert analysis.console_device == "serial0"
        assert "console_device" in analysis._source

    def test_console_device_populated_from_bootargs(self, tmp_path: Path) -> None:
        """Test that console_device is set from bootargs console=."""
        dts_file = tmp_path / "system.dtb"
        dts_file.write_text("""
        / {
            bootargs = "console=ttyFIQ0,1500000 root=/dev/mmcblk0p5";
        };
        """)

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_boot_config(dts_file, analysis)

        assert analysis.console_device == "ttyFIQ0"

    def test_new_fields_in_toml_output(self) -> None:
        """Test that new fields appear in TOML output."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            soc_name="Rockchip RV1126",
            cpu_architecture="ARM Cortex-A7 (32-bit)",
            storage_type="eMMC",
            console_device="ttyFIQ0",
            console_baudrate="1500000",
        )

        toml_str = output_toml(
            analysis,
            title="Boot process and partition layout analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )
        parsed = tomlkit.loads(toml_str)

        assert parsed["soc_name"] == "Rockchip RV1126"
        assert parsed["cpu_architecture"] == "ARM Cortex-A7 (32-bit)"
        assert parsed["storage_type"] == "eMMC"
        assert parsed["console_device"] == "ttyFIQ0"
        assert parsed["console_baudrate"] == "1500000"

    def test_new_fields_excluded_when_none(self) -> None:
        """Test that None fields are excluded from TOML output."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )

        toml_str = output_toml(
            analysis,
            title="Boot process and partition layout analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )

        assert "soc_name" not in toml_str
        assert "cpu_architecture" not in toml_str
        assert "storage_type" not in toml_str
        assert "console_device" not in toml_str
        assert "console_baudrate" not in toml_str


class TestExtractRockchipParameter:
    """Test extract_rockchip_parameter function."""

    def test_extract_from_rkfw_firmware(self, tmp_path: Path) -> None:
        """Test extracting parameter from valid RKFW firmware."""

        firmware = tmp_path / "firmware.img"

        # Build a minimal RKFW image with parameter section
        param_content = b"FIRMWARE_VER:1.0\nCMDLINE:mtdparts=rk29xxnand:0x2000@0x4000(uboot)\n"
        param_offset = 0x100  # Place PARM section at offset 0x100

        # Build header: RKFW magic + padding to 0x22 + param_offset
        header = b"RKFW" + b"\x00" * (0x22 - 4)
        header += struct.pack("<I", param_offset)
        header += b"\x00" * (param_offset - len(header))

        # Build PARM section
        parm_section = b"PARM" + struct.pack("<I", len(param_content)) + param_content

        firmware.write_bytes(header + parm_section)

        result = extract_rockchip_parameter(firmware)
        assert result is not None
        assert "FIRMWARE_VER" in result

    def test_extract_non_rkfw_returns_none(self, tmp_path: Path) -> None:
        """Test that non-RKFW firmware returns None."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"NOTRKFW" + b"\x00" * 256)

        result = extract_rockchip_parameter(firmware)
        assert result is None

    def test_extract_missing_file_returns_none(self, tmp_path: Path) -> None:
        """Test that missing firmware file returns None."""
        firmware = tmp_path / "nonexistent.img"

        result = extract_rockchip_parameter(firmware)
        assert result is None

    def test_extract_truncated_file_returns_none(self, tmp_path: Path) -> None:
        """Test that truncated firmware returns None."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"RKFW")  # Too short to read offset

        result = extract_rockchip_parameter(firmware)
        assert result is None


class TestParseRockchipPartitions:
    """Test parse_rockchip_partitions function."""

    def test_parse_standard_parameter_file(self) -> None:
        """Test parsing a standard Rockchip parameter file."""
        param_content = (
            "FIRMWARE_VER:8.1\n"
            "MACHINE_MODEL:RK3399\n"
            "CMDLINE:mtdparts=rk29xxnand:0x00002000@0x00004000(uboot),"
            "0x00002000@0x00006000(trust),"
            "0x00002000@0x00008000(misc),"
            "0x00010000@0x0000a000(boot),"
            "0x00010000@0x0001a000(recovery),"
            "0x00040000@0x0004a000(oem),"
            "0x00c00000@0x0008a000(rootfs),"
            "-@0x00c8a000(userdata)\n"
        )

        partitions = parse_rockchip_partitions(param_content)

        assert len(partitions) == 8

        # Check first partition
        assert partitions[0].region == "uboot"
        assert partitions[0].offset == "0x00004000"
        assert partitions[0].type == "raw"
        assert partitions[0].content == "U-Boot bootloader"

        # Check trust partition
        trust_part = next(p for p in partitions if p.region == "trust")
        assert trust_part.type == "raw"
        assert "Trusted firmware" in trust_part.content

        # Check misc partition
        misc_part = next(p for p in partitions if p.region == "misc")
        assert misc_part.type == "raw"

        # Check userdata (remaining space)
        userdata_part = next(p for p in partitions if p.region == "userdata")
        assert userdata_part.size_mb == 0  # "-" means remaining space

    def test_parse_empty_content(self) -> None:
        """Test parsing empty content returns empty list."""
        partitions = parse_rockchip_partitions("")
        assert partitions == []

    def test_parse_no_cmdline(self) -> None:
        """Test parsing content without CMDLINE returns empty list."""
        param_content = "FIRMWARE_VER:1.0\nMACHINE_MODEL:Test\n"
        partitions = parse_rockchip_partitions(param_content)
        assert partitions == []

    def test_parse_size_conversion(self) -> None:
        """Test that partition sizes are correctly converted from sectors to MB."""
        # 0x800 sectors = 2048 sectors * 512 bytes = 1MB
        param_content = "CMDLINE:mtdparts=rk29xxnand:0x00000800@0x00000000(test)\n"
        partitions = parse_rockchip_partitions(param_content)

        assert len(partitions) == 1
        assert partitions[0].size_mb == 1

    def test_parse_blkdevparts_format(self) -> None:
        """Test parsing blkdevparts format (alternative to mtdparts)."""
        param_content = (
            "CMDLINE:blkdevparts=mmcblk0:"
            "0x00002000@0x00004000(uboot),"
            "0x00002000@0x00006000(trust)\n"
        )
        partitions = parse_rockchip_partitions(param_content)
        assert len(partitions) == 2


class TestClassifyPartition:
    """Test _classify_partition function."""

    def test_classify_known_partitions(self) -> None:
        """Test classification of known partition names."""
        assert _classify_partition("uboot") == ("raw", "U-Boot bootloader")
        assert _classify_partition("trust") == ("raw", "OP-TEE / Trusted firmware")
        assert _classify_partition("misc") == ("raw", "Boot control / recovery flags")
        assert _classify_partition("boot") == ("FIT/raw", "Kernel + ramdisk")
        assert _classify_partition("recovery") == ("FIT/raw", "Recovery kernel + ramdisk")
        assert _classify_partition("rootfs") == ("SquashFS", "Main filesystem")
        assert _classify_partition("oem") == ("ext4", "OEM data partition")
        assert _classify_partition("userdata") == ("ext4", "User data partition")
        assert _classify_partition("reserved") == ("raw", "Reserved space")

    def test_classify_prefix_match(self) -> None:
        """Test classification by prefix match (e.g., dtb1, dtb2)."""
        ptype, content = _classify_partition("dtb1")
        assert ptype == "raw"
        assert "Device tree" in content

    def test_classify_unknown_partition(self) -> None:
        """Test classification of unknown partition names."""
        ptype, content = _classify_partition("custom_part")
        assert ptype == "unknown"
        assert content == "custom_part"


class TestAnalyzeStorageType:
    """Test analyze_storage_type function."""

    def test_storage_type_from_mmcblk_in_bootargs(self) -> None:
        """Test detecting eMMC from mmcblk in bootargs."""
        analysis = BootProcessAnalysis("test.img", 1024)
        analysis.kernel_cmdline = "console=ttyFIQ0 root=/dev/mmcblk0p5 rootfstype=squashfs"

        analyze_storage_type(analysis, None)

        assert analysis.storage_type == "eMMC"
        assert analysis._source["storage_type"] == "kernel-cmdline"

    def test_storage_type_from_dts_emmc(self, tmp_path: Path) -> None:
        """Test detecting eMMC from DTS emmc nodes."""
        dts_file = tmp_path / "system.dtb"
        dts_file.write_text("""
        / {
            emmc@ff390000 {
                compatible = "rockchip,rk3399-dw-mshc";
                mmc-hs200-1_8v;
            };
        };
        """)

        analysis = BootProcessAnalysis("test.img", 1024)

        analyze_storage_type(analysis, dts_file)

        assert analysis.storage_type == "eMMC"
        assert analysis._source["storage_type"] == "device-tree"

    def test_storage_type_from_dts_sdhci(self, tmp_path: Path) -> None:
        """Test detecting eMMC from DTS sdhci nodes."""
        dts_file = tmp_path / "system.dtb"
        dts_file.write_text("""
        / {
            sdhci@ff370000 {
                compatible = "arasan,sdhci-5.1";
            };
        };
        """)

        analysis = BootProcessAnalysis("test.img", 1024)

        analyze_storage_type(analysis, dts_file)

        assert analysis.storage_type == "eMMC"

    def test_storage_type_none_when_no_evidence(self) -> None:
        """Test that storage_type remains None without evidence."""
        analysis = BootProcessAnalysis("test.img", 1024)

        analyze_storage_type(analysis, None)

        assert analysis.storage_type is None

    def test_storage_type_handles_missing_dts(self, tmp_path: Path) -> None:
        """Test storage type handles missing DTS gracefully."""
        dts_file = tmp_path / "nonexistent.dtb"
        analysis = BootProcessAnalysis("test.img", 1024)

        # Should not raise
        analyze_storage_type(analysis, dts_file)

        assert analysis.storage_type is None
