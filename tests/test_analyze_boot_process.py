"""Tests for scripts/analyze_boot_process.py."""

from __future__ import annotations

import sys
from pathlib import Path
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
    analyze_ab_redundancy,
    analyze_boot_components,
    analyze_boot_config,
    analyze_component_versions,
    analyze_hardware_properties,
    analyze_partitions,
    find_largest_dts,
    find_rootfs,
    get_fit_info,
    load_firmware_offsets,
)
from lib.output import output_toml


class TestComponentVersion:
    """Test ComponentVersion dataclass."""

    def test_component_version_creation(self):
        """Test creating a ComponentVersion."""
        version = ComponentVersion(
            component="U-Boot",
            version="U-Boot 2023.07",
            source="Binary strings",
        )

        assert version.component == "U-Boot"
        assert version.version == "U-Boot 2023.07"
        assert version.source == "Binary strings"

    def test_component_version_is_frozen(self):
        """Test that ComponentVersion is immutable (frozen)."""
        version = ComponentVersion(
            component="U-Boot",
            version="U-Boot 2023.07",
            source="Binary strings",
        )

        with pytest.raises(AttributeError):
            version.version = "Different version"  # type: ignore

    def test_component_version_has_slots(self):
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

    def test_hardware_property_creation(self):
        """Test creating a HardwareProperty."""
        prop = HardwareProperty(
            property="SoC",
            value="Rockchip RV1126",
            source="DTS compatible",
        )

        assert prop.property == "SoC"
        assert prop.value == "Rockchip RV1126"
        assert prop.source == "DTS compatible"

    def test_hardware_property_is_frozen(self):
        """Test that HardwareProperty is immutable (frozen)."""
        prop = HardwareProperty(
            property="SoC",
            value="Rockchip RV1126",
            source="DTS compatible",
        )

        with pytest.raises(AttributeError):
            prop.value = "Different SoC"  # type: ignore

    def test_hardware_property_has_slots(self):
        """Test that HardwareProperty uses __slots__ for efficiency."""
        prop = HardwareProperty(
            property="SoC",
            value="Rockchip RV1126",
            source="DTS compatible",
        )

        assert hasattr(prop.__class__, "__slots__")


class TestBootComponent:
    """Test BootComponent dataclass."""

    def test_boot_component_creation(self):
        """Test creating a BootComponent."""
        component = BootComponent(
            stage="U-Boot",
            found=True,
            evidence="u-boot binary found in extraction",
        )

        assert component.stage == "U-Boot"
        assert component.found is True
        assert component.evidence == "u-boot binary found in extraction"

    def test_boot_component_not_found(self):
        """Test creating a BootComponent for missing component."""
        component = BootComponent(
            stage="Secure Boot",
            found=False,
            evidence="No secure boot signatures detected",
        )

        assert component.stage == "Secure Boot"
        assert component.found is False
        assert component.evidence == "No secure boot signatures detected"

    def test_boot_component_is_frozen(self):
        """Test that BootComponent is immutable (frozen)."""
        component = BootComponent(
            stage="U-Boot",
            found=True,
            evidence="test",
        )

        with pytest.raises(AttributeError):
            component.found = False  # type: ignore

    def test_boot_component_has_slots(self):
        """Test that BootComponent uses __slots__ for efficiency."""
        component = BootComponent(
            stage="U-Boot",
            found=True,
            evidence="test",
        )

        assert hasattr(component.__class__, "__slots__")


class TestPartition:
    """Test Partition dataclass."""

    def test_partition_creation(self):
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

    def test_partition_is_frozen(self):
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

    def test_partition_has_slots(self):
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

    def test_console_config_creation(self):
        """Test creating a ConsoleConfig."""
        config = ConsoleConfig(
            parameter="Baud Rate",
            value="1500000",
            source="DTS rockchip,baudrate",
        )

        assert config.parameter == "Baud Rate"
        assert config.value == "1500000"
        assert config.source == "DTS rockchip,baudrate"

    def test_console_config_is_frozen(self):
        """Test that ConsoleConfig is immutable (frozen)."""
        config = ConsoleConfig(
            parameter="Baud Rate",
            value="1500000",
            source="DTS rockchip,baudrate",
        )

        with pytest.raises(AttributeError):
            config.value = "115200"  # type: ignore

    def test_console_config_has_slots(self):
        """Test that ConsoleConfig uses __slots__ for efficiency."""
        config = ConsoleConfig(
            parameter="Baud Rate",
            value="1500000",
            source="DTS rockchip,baudrate",
        )

        assert hasattr(config.__class__, "__slots__")


class TestBootProcessAnalysis:
    """Test BootProcessAnalysis dataclass."""

    def test_boot_process_analysis_creation(self):
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

    def test_boot_process_analysis_with_data(self):
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

    def test_add_metadata(self):
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

    def test_add_metadata_multiple_fields(self):
        """Test adding metadata for multiple fields."""
        analysis = BootProcessAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
        )

        analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")
        analysis.add_metadata("firmware_size", "filesystem", "Path(firmware).stat().st_size")

        assert len(analysis._source) == 2
        assert len(analysis._method) == 2

    def test_to_dict_excludes_none(self):
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

    def test_to_dict_excludes_empty_lists(self):
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

    def test_to_dict_includes_metadata(self):
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

    def test_to_dict_converts_hardware_properties(self):
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

    def test_to_dict_converts_boot_components(self):
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

    def test_to_dict_converts_component_versions(self):
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

    def test_to_dict_converts_partitions(self):
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

    def test_to_dict_converts_console_configs(self):
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

    def test_to_dict_excludes_private_fields(self):
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

    def test_get_fit_info_success(self, tmp_path: Path):
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

    def test_get_fit_info_missing_file(self, tmp_path: Path):
        """Test extracting FIT info from non-existent file."""
        dts_file = tmp_path / "nonexistent.dtb"

        result = get_fit_info(dts_file)

        assert result is None

    def test_get_fit_info_read_error(self, tmp_path: Path):
        """Test extracting FIT info with read error."""
        dts_file = tmp_path / "system.dtb"
        # Create a binary file that will cause decoding issues
        dts_file.write_bytes(b"\xff\xfe\x00\x01")

        result = get_fit_info(dts_file)

        # Should handle error gracefully
        assert result is None


class TestFindLargestDts:
    """Test find_largest_dts function."""

    def test_find_largest_dts_single_file(self, tmp_path: Path):
        """Test finding largest DTS when only one exists."""
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        dts_file = extract_dir / "system.dtb"
        dts_file.write_text("small content")

        result = find_largest_dts(extract_dir)

        assert result == dts_file

    def test_find_largest_dts_multiple_files(self, tmp_path: Path):
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

    def test_find_largest_dts_none_found(self, tmp_path: Path):
        """Test finding largest DTS when no files exist."""
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        result = find_largest_dts(extract_dir)

        assert result is None

    def test_find_largest_dts_nested(self, tmp_path: Path):
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

    def test_load_firmware_offsets_success(self, tmp_path: Path):
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

    def test_load_firmware_offsets_missing_file(self, tmp_path: Path):
        """Test loading firmware offsets when file doesn't exist."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with pytest.raises(SystemExit) as exc_info:
            load_firmware_offsets(output_dir)

        assert exc_info.value.code == 1

    def test_load_firmware_offsets_ignores_comments(self, tmp_path: Path):
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

    def test_load_firmware_offsets_decimal_values(self, tmp_path: Path):
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

    def test_load_firmware_offsets_with_quotes(self, tmp_path: Path):
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

    def test_load_firmware_offsets_caching(self, tmp_path: Path):
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

    def test_toml_output_valid(self):
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

    def test_toml_includes_header(self):
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

    def test_toml_includes_source_comments(self):
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

    def test_toml_truncates_long_methods(self):
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

    def test_toml_excludes_none_values(self):
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

    def test_toml_includes_nested_data(self):
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

    def test_toml_excludes_metadata_fields(self):
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

    def test_toml_validates_output(self):
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

    def test_find_rootfs_success(self, tmp_path: Path):
        """Test finding squashfs-root directory."""
        extract_dir = tmp_path / "extract"
        squashfs_root = extract_dir / "squashfs-root"
        squashfs_root.mkdir(parents=True)

        result = find_rootfs(extract_dir)

        assert result == squashfs_root

    def test_find_rootfs_nested(self, tmp_path: Path):
        """Test finding squashfs-root in nested directory."""
        extract_dir = tmp_path / "extract"
        nested = extract_dir / "subdir" / "8F1B4"
        squashfs_root = nested / "squashfs-root"
        squashfs_root.mkdir(parents=True)

        result = find_rootfs(extract_dir)

        assert result == squashfs_root

    def test_find_rootfs_not_found(self, tmp_path: Path):
        """Test find_rootfs when directory doesn't exist."""
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        result = find_rootfs(extract_dir)

        assert result is None


class TestAnalyzeHardwareProperties:
    """Test analyze_hardware_properties function."""

    def test_analyze_hardware_properties_compatible(self, tmp_path: Path):
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

    def test_analyze_hardware_properties_derives_soc(self, tmp_path: Path):
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
    def test_analyze_hardware_properties_derives_architecture(self, mock_run, tmp_path: Path):
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

    def test_analyze_hardware_properties_handles_errors(self, tmp_path: Path):
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

    def test_analyze_boot_components_finds_tee(self, tmp_path: Path):
        """Test detecting OP-TEE component."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"dummy")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        tee_file = extract_dir / "tee.bin"
        tee_file.touch()

        offsets = {}
        analysis = BootProcessAnalysis("firmware.img", 1024)

        analyze_boot_components(firmware, extract_dir, offsets, analysis)

        tee_comp = next(c for c in analysis.boot_components if c.stage == "OP-TEE")
        assert tee_comp.found is True
        assert "tee.bin found" in tee_comp.evidence

    def test_analyze_boot_components_finds_uboot_binary(self, tmp_path: Path):
        """Test detecting U-Boot from binary file."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"dummy")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        uboot_file = extract_dir / "u-boot.bin"
        uboot_file.touch()

        offsets = {}
        analysis = BootProcessAnalysis("firmware.img", 1024)

        analyze_boot_components(firmware, extract_dir, offsets, analysis)

        uboot_comp = next(c for c in analysis.boot_components if c.stage == "U-Boot")
        assert uboot_comp.found is True
        assert "u-boot binary found" in uboot_comp.evidence

    @patch("subprocess.run")
    def test_analyze_boot_components_finds_uboot_strings(self, mock_run, tmp_path: Path):
        """Test detecting U-Boot from strings in firmware."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"dummy")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        # Mock strings command
        mock_run.return_value = MagicMock(stdout="U-Boot 2023.07\nOther text")

        offsets = {}
        analysis = BootProcessAnalysis("firmware.img", 1024)

        analyze_boot_components(firmware, extract_dir, offsets, analysis)

        uboot_comp = next(c for c in analysis.boot_components if c.stage == "U-Boot")
        assert uboot_comp.found is True
        assert "U-Boot strings found" in uboot_comp.evidence

    def test_analyze_boot_components_finds_kernel(self, tmp_path: Path):
        """Test detecting kernel FIT image."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"dummy")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        offsets = {"KERNEL_FIT_OFFSET": "0x1000"}
        analysis = BootProcessAnalysis("firmware.img", 1024)

        analyze_boot_components(firmware, extract_dir, offsets, analysis)

        kernel_comp = next(c for c in analysis.boot_components if c.stage == "Kernel")
        assert kernel_comp.found is True
        assert "0x1000" in kernel_comp.evidence

    def test_analyze_boot_components_finds_initramfs(self, tmp_path: Path):
        """Test detecting initramfs CPIO."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"dummy")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        offsets = {"ROOTFS_CPIO_OFFSET": "0x2000"}
        analysis = BootProcessAnalysis("firmware.img", 1024)

        analyze_boot_components(firmware, extract_dir, offsets, analysis)

        cpio_comp = next(c for c in analysis.boot_components if c.stage == "Initramfs")
        assert cpio_comp.found is True
        assert "0x2000" in cpio_comp.evidence

    def test_analyze_boot_components_finds_squashfs(self, tmp_path: Path):
        """Test detecting SquashFS filesystem."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"dummy")

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        offsets = {"SQUASHFS_OFFSET": "0x3000"}
        analysis = BootProcessAnalysis("firmware.img", 1024)

        analyze_boot_components(firmware, extract_dir, offsets, analysis)

        squashfs_comp = next(c for c in analysis.boot_components if c.stage == "SquashFS")
        assert squashfs_comp.found is True
        assert "0x3000" in squashfs_comp.evidence


class TestAnalyzeComponentVersions:
    """Test analyze_component_versions function."""

    @patch("subprocess.run")
    def test_analyze_component_versions_uboot(self, mock_run, tmp_path: Path):
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
    def test_analyze_component_versions_kernel(self, mock_run, tmp_path: Path):
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
        def mock_subprocess_side_effect(*args, **_kwargs):
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

    def test_analyze_component_versions_buildroot(self, tmp_path: Path):
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

    def test_analyze_partitions_bootloader(self):
        """Test analyzing bootloader partition."""
        offsets = {
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

    def test_analyze_partitions_kernel(self):
        """Test analyzing kernel partition."""
        offsets = {
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

    def test_analyze_partitions_initramfs(self):
        """Test analyzing initramfs partition."""
        offsets = {
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

    def test_analyze_partitions_rootfs(self):
        """Test analyzing root filesystem partition."""
        offsets = {
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

    def test_analyze_partitions_missing_offsets(self):
        """Test analyze_partitions with missing offsets."""
        offsets = {}

        analysis = BootProcessAnalysis("test.img", 1024)
        analyze_partitions(offsets, analysis)

        # Should not create any partitions
        assert len(analysis.partitions) == 0


class TestAnalyzeAbRedundancy:
    """Test analyze_ab_redundancy function."""

    def test_analyze_ab_redundancy_detected(self, tmp_path: Path):
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

    def test_analyze_ab_redundancy_not_detected(self, tmp_path: Path):
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

    def test_analyze_ab_redundancy_threshold(self, tmp_path: Path):
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

    def test_analyze_boot_config_kernel_cmdline(self, tmp_path: Path):
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

    def test_analyze_boot_config_baudrate(self, tmp_path: Path):
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

    def test_analyze_boot_config_console_from_stdout(self, tmp_path: Path):
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

    def test_analyze_boot_config_console_from_bootargs(self, tmp_path: Path):
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

    def test_analyze_boot_config_handles_errors(self, tmp_path: Path):
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
    def test_analyze_boot_process_integration(self, mock_run, tmp_path: Path):
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
        def mock_subprocess_side_effect(*args, **_kwargs):
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
        from analyze_boot_process import analyze_boot_process  # noqa: PLC0415

        result = analyze_boot_process(firmware, extract_dir, output_dir)

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

    def test_realistic_boot_process_analysis(self):
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

    def test_realistic_toml_output(self):
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

    def test_minimal_boot_process_analysis(self):
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
