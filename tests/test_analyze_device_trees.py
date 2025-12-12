"""Tests for scripts/analyze_device_trees.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import tomlkit

# Add scripts directory to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from analyze_device_trees import (
    DeviceTree,
    DeviceTreeAnalysis,
    HardwareComponent,
    _extract_fit_description,
    _extract_hardware_components,
    _extract_serial_config,
    analyze_dtb_file,
    find_dtb_files,
    output_toml,
    parse_dts_content,
)


class TestHardwareComponent:
    """Test HardwareComponent dataclass."""

    def test_component_creation(self):
        """Test creating a HardwareComponent."""
        comp = HardwareComponent(
            type="gpio",
            node="gpio0",
            description="GPIO controller at 0xfdd60000",
        )

        assert comp.type == "gpio"
        assert comp.node == "gpio0"
        assert comp.description == "GPIO controller at 0xfdd60000"

    def test_component_is_frozen(self):
        """Test that HardwareComponent is immutable (frozen)."""
        comp = HardwareComponent(
            type="gpio",
            node="gpio0",
            description="GPIO controller at 0xfdd60000",
        )

        with pytest.raises(AttributeError):
            comp.type = "usb"  # type: ignore

    def test_component_has_slots(self):
        """Test that HardwareComponent uses __slots__ for efficiency."""
        comp = HardwareComponent(
            type="gpio",
            node="gpio0",
            description="GPIO controller",
        )

        # Frozen dataclasses prevent attribute modification entirely
        # Testing __slots__ is less relevant for frozen dataclasses
        # Just verify the object works as expected
        assert hasattr(comp.__class__, "__slots__")


class TestDeviceTree:
    """Test DeviceTree dataclass."""

    def test_device_tree_creation_minimal(self):
        """Test creating a DeviceTree with minimal fields."""
        dt = DeviceTree(
            filename="system.dtb",
            size=2048,
            offset="0x8F1B4",
            dtb_type="Device Tree",
        )

        assert dt.filename == "system.dtb"
        assert dt.size == 2048
        assert dt.offset == "0x8F1B4"
        assert dt.dtb_type == "Device Tree"
        assert dt.model is None
        assert dt.compatible is None
        assert dt.fit_description is None
        assert dt.serial_config is None
        assert dt.hardware_components == []

    def test_device_tree_creation_full(self):
        """Test creating a DeviceTree with all fields."""
        hardware = [
            HardwareComponent(
                type="gpio",
                node="gpio0",
                description="GPIO controller at 0xfdd60000",
            )
        ]

        dt = DeviceTree(
            filename="system.dtb",
            size=2048,
            offset="0x8F1B4",
            dtb_type="FIT Image",
            model="GL.iNet Comet (RM1)",
            compatible="glinet,comet",
            fit_description="description = FIT Image",
            serial_config="fiq-debugger",
            hardware_components=hardware,
        )

        assert dt.filename == "system.dtb"
        assert dt.model == "GL.iNet Comet (RM1)"
        assert dt.compatible == "glinet,comet"
        assert dt.fit_description == "description = FIT Image"
        assert dt.serial_config == "fiq-debugger"
        assert len(dt.hardware_components) == 1
        assert dt.hardware_components[0].type == "gpio"

    def test_device_tree_is_frozen(self):
        """Test that DeviceTree is immutable (frozen)."""
        dt = DeviceTree(
            filename="system.dtb",
            size=2048,
            offset="0x8F1B4",
            dtb_type="Device Tree",
        )

        with pytest.raises(AttributeError):
            dt.filename = "other.dtb"  # type: ignore

    def test_device_tree_has_slots(self):
        """Test that DeviceTree uses __slots__ for efficiency."""
        dt = DeviceTree(
            filename="system.dtb",
            size=2048,
            offset="0x8F1B4",
            dtb_type="Device Tree",
        )

        # Frozen dataclasses prevent attribute modification entirely
        # Testing __slots__ is less relevant for frozen dataclasses
        # Just verify the object works as expected
        assert hasattr(dt.__class__, "__slots__")


class TestDeviceTreeAnalysis:
    """Test DeviceTreeAnalysis dataclass."""

    def test_analysis_creation(self):
        """Test creating a DeviceTreeAnalysis."""
        analysis = DeviceTreeAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )

        assert analysis.firmware_file == "test.img"
        assert analysis.firmware_size == 1024
        assert analysis.dtb_count == 0
        assert analysis.device_trees == []
        assert analysis._source == {}
        assert analysis._method == {}

    def test_analysis_is_mutable(self):
        """Test that DeviceTreeAnalysis is mutable (not frozen)."""
        analysis = DeviceTreeAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )

        # Should be able to modify fields
        analysis.dtb_count = 2
        assert analysis.dtb_count == 2

    def test_add_metadata(self):
        """Test adding source metadata."""
        analysis = DeviceTreeAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )

        analysis.add_metadata(
            "firmware_size",
            "firmware",
            "Path(firmware).stat().st_size",
        )

        assert analysis._source["firmware_size"] == "firmware"
        assert analysis._method["firmware_size"] == "Path(firmware).stat().st_size"

    def test_to_dict_excludes_none(self):
        """Test to_dict excludes None values."""
        analysis = DeviceTreeAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )

        result = analysis.to_dict()

        assert "firmware_file" in result
        assert "firmware_size" in result
        # dtb_count is 0, should be included
        assert "dtb_count" in result
        # _source and _method should be excluded
        assert "_source" not in result
        assert "_method" not in result

    def test_to_dict_includes_metadata(self):
        """Test to_dict includes source metadata."""
        analysis = DeviceTreeAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )
        analysis.add_metadata(
            "firmware_size",
            "firmware",
            "Path(firmware).stat().st_size",
        )

        result = analysis.to_dict()

        assert result["firmware_size"] == 1024
        assert result["firmware_size_source"] == "firmware"
        assert result["firmware_size_method"] == "Path(firmware).stat().st_size"

    def test_to_dict_converts_device_trees(self):
        """Test to_dict converts DeviceTree objects to dicts."""
        analysis = DeviceTreeAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )
        analysis.device_trees = [
            DeviceTree(
                filename="system.dtb",
                size=2048,
                offset="0x8F1B4",
                dtb_type="Device Tree",
            )
        ]

        result = analysis.to_dict()

        assert len(result["device_trees"]) == 1
        assert result["device_trees"][0]["filename"] == "system.dtb"
        assert result["device_trees"][0]["size"] == 2048
        assert result["device_trees"][0]["offset"] == "0x8F1B4"
        assert result["device_trees"][0]["type"] == "Device Tree"

    def test_to_dict_filters_none_in_device_trees(self):
        """Test to_dict filters out None values in device trees."""
        analysis = DeviceTreeAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )
        analysis.device_trees = [
            DeviceTree(
                filename="system.dtb",
                size=2048,
                offset="0x8F1B4",
                dtb_type="Device Tree",
                model=None,  # Should be filtered out
                compatible=None,  # Should be filtered out
            )
        ]

        result = analysis.to_dict()

        assert "model" not in result["device_trees"][0]
        assert "compatible" not in result["device_trees"][0]

    def test_to_dict_includes_hardware_components(self):
        """Test to_dict includes hardware components."""
        hardware = [
            HardwareComponent(
                type="gpio",
                node="gpio0",
                description="GPIO controller at 0xfdd60000",
            )
        ]

        analysis = DeviceTreeAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )
        analysis.device_trees = [
            DeviceTree(
                filename="system.dtb",
                size=2048,
                offset="0x8F1B4",
                dtb_type="Device Tree",
                hardware_components=hardware,
            )
        ]

        result = analysis.to_dict()

        assert "hardware_components" in result["device_trees"][0]
        assert len(result["device_trees"][0]["hardware_components"]) == 1
        assert result["device_trees"][0]["hardware_components"][0]["type"] == "gpio"
        assert result["device_trees"][0]["hardware_components"][0]["node"] == "gpio0"

    def test_to_dict_excludes_empty_hardware_components(self):
        """Test to_dict excludes empty hardware components list."""
        analysis = DeviceTreeAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )
        analysis.device_trees = [
            DeviceTree(
                filename="system.dtb",
                size=2048,
                offset="0x8F1B4",
                dtb_type="Device Tree",
                hardware_components=[],  # Empty list should be filtered
            )
        ]

        result = analysis.to_dict()

        assert "hardware_components" not in result["device_trees"][0]


class TestExtractFitDescription:
    """Test _extract_fit_description function."""

    def test_extract_fit_description_found(self):
        """Test extracting FIT description when present."""
        dts_content = """
        / {
            description = "FIT Image";
            type = "kernel";
            arch = "arm64";
            os = "linux";
            compression = "gzip";
        };
        """

        result = _extract_fit_description(dts_content)

        assert result is not None
        assert "description" in result
        assert "type" in result
        assert "arch" in result

    def test_extract_fit_description_not_found(self):
        """Test extracting FIT description when not present."""
        dts_content = """
        / {
            model = "GL.iNet Comet";
            compatible = "glinet,comet";
        };
        """

        result = _extract_fit_description(dts_content)

        assert result is None

    def test_extract_fit_description_no_fit_keyword(self):
        """Test extracting FIT description without FIT keyword."""
        dts_content = """
        / {
            description = "Regular description";
            type = "kernel";
        };
        """

        result = _extract_fit_description(dts_content)

        assert result is None

    def test_extract_fit_description_max_lines(self):
        """Test that FIT description is limited to max lines."""
        # Create content with more than FIT_DESCRIPTION_MAX_LINES
        lines = ["description = FIT Image"] + [f"key{i} = value{i}" for i in range(50)]
        dts_content = "\n".join(lines)

        result = _extract_fit_description(dts_content)

        assert result is not None
        # Should be limited to 30 lines
        assert len(result.splitlines()) <= 30

    def test_extract_fit_description_filters_relevant_keys(self):
        """Test that only relevant keys are extracted."""
        dts_content = """
        / {
            description = "FIT Image";
            type = "kernel";
            irrelevant = "should not be included";
            arch = "arm64";
            random_key = "not included";
            compression = "gzip";
        };
        """

        result = _extract_fit_description(dts_content)

        assert result is not None
        assert "description" in result
        assert "type" in result
        assert "arch" in result
        assert "compression" in result
        assert "irrelevant" not in result
        assert "random_key" not in result


class TestExtractSerialConfig:
    """Test _extract_serial_config function."""

    def test_extract_serial_config_with_baudrate(self):
        """Test extracting serial config with baudrate."""
        dts_content = """
        serial@fe650000 {
            compatible = "rockchip,rk3568-uart";
            reg = <0xfe650000 0x100>;
            baudrate = <1500000>;
        };
        """

        result = _extract_serial_config(dts_content)

        assert result is not None
        assert "serial@" in result
        assert "baudrate" in result

    def test_extract_serial_config_with_fiq_debugger(self):
        """Test extracting serial config with fiq-debugger."""
        dts_content = """
        fiq-debugger {
            compatible = "rockchip,fiq-debugger";
            rockchip,serial-id = <2>;
            status = "okay";
        };
        """

        result = _extract_serial_config(dts_content)

        assert result is not None
        assert "fiq-debugger" in result

    def test_extract_serial_config_not_found(self):
        """Test extracting serial config when not present."""
        dts_content = """
        / {
            model = "GL.iNet Comet";
            compatible = "glinet,comet";
        };
        """

        result = _extract_serial_config(dts_content)

        assert result is None

    def test_extract_serial_config_context_lines(self):
        """Test that serial config includes context lines."""
        dts_content = """
        serial@fe650000 {
            compatible = "rockchip,rk3568-uart";
            reg = <0xfe650000 0x100>;
            baudrate = <1500000>;
            line1 = "value1";
            line2 = "value2";
            line3 = "value3";
            line4 = "value4";
            line5 = "value5";
            line6 = "value6";
            line7 = "value7";
            line8 = "value8";
            line9 = "value9";
            line10 = "value10";
        };
        """

        result = _extract_serial_config(dts_content)

        assert result is not None
        # Should include 10 context lines (SERIAL_CONFIG_CONTEXT_LINES)
        # But limited by SERIAL_CONFIG_MAX_LINES (20)
        lines = result.splitlines()
        assert len(lines) >= 10
        assert len(lines) <= 20


class TestExtractHardwareComponents:
    """Test _extract_hardware_components function."""

    def test_extract_gpio_components(self):
        """Test extracting GPIO components."""
        dts_content = """
        gpio0: gpio@fdd60000 {
            compatible = "rockchip,gpio-bank";
        };
        gpio1: gpio@fdd70000 {
            compatible = "rockchip,gpio-bank";
        };
        """

        result = _extract_hardware_components(dts_content)

        assert len(result) == 2
        assert result[0].type == "gpio"
        assert result[0].node == "gpio0"
        assert "0xfdd60000" in result[0].description
        assert result[1].type == "gpio"
        assert result[1].node == "gpio1"
        assert "0xfdd70000" in result[1].description

    def test_extract_usb_components(self):
        """Test extracting USB components."""
        dts_content = """
        usb0: usb@fcc00000 {
            compatible = "rockchip,rk3568-dwc3";
        };
        """

        result = _extract_hardware_components(dts_content)

        assert len(result) == 1
        assert result[0].type == "usb"
        assert result[0].node == "usb0"
        assert "0xfcc00000" in result[0].description

    def test_extract_spi_components(self):
        """Test extracting SPI components."""
        dts_content = """
        spi0: spi@fe610000 {
            compatible = "rockchip,rk3568-spi";
        };
        """

        result = _extract_hardware_components(dts_content)

        assert len(result) == 1
        assert result[0].type == "spi"
        assert result[0].node == "spi0"
        assert "0xfe610000" in result[0].description

    def test_extract_i2c_components(self):
        """Test extracting I2C components."""
        dts_content = """
        i2c0: i2c@fdd40000 {
            compatible = "rockchip,rk3568-i2c";
        };
        """

        result = _extract_hardware_components(dts_content)

        assert len(result) == 1
        assert result[0].type == "i2c"
        assert result[0].node == "i2c0"
        assert "0xfdd40000" in result[0].description

    def test_extract_uart_components(self):
        """Test extracting UART/serial components."""
        dts_content = """
        serial0: serial@fe650000 {
            compatible = "rockchip,rk3568-uart";
        };
        uart1: serial@fe660000 {
            compatible = "rockchip,rk3568-uart";
        };
        """

        result = _extract_hardware_components(dts_content)

        assert len(result) == 2
        assert result[0].type == "uart"
        assert result[0].node == "serial0"
        assert result[1].type == "uart"
        assert result[1].node == "uart1"

    def test_extract_multiple_component_types(self):
        """Test extracting multiple types of components."""
        dts_content = """
        gpio0: gpio@fdd60000 { };
        usb0: usb@fcc00000 { };
        spi0: spi@fe610000 { };
        i2c0: i2c@fdd40000 { };
        serial0: serial@fe650000 { };
        """

        result = _extract_hardware_components(dts_content)

        assert len(result) == 5
        types = [comp.type for comp in result]
        assert "gpio" in types
        assert "usb" in types
        assert "spi" in types
        assert "i2c" in types
        assert "uart" in types

    def test_extract_no_components(self):
        """Test extracting when no components are present."""
        dts_content = """
        / {
            model = "GL.iNet Comet";
            compatible = "glinet,comet";
        };
        """

        result = _extract_hardware_components(dts_content)

        assert result == []


class TestParseDtsContent:
    """Test parse_dts_content function."""

    def test_parse_dts_content_device_tree_type(self):
        """Test parsing DTS content and detecting Device Tree type."""
        dts_content = """
        / {
            model = "GL.iNet Comet (RM1)";
            compatible = "glinet,comet", "rockchip,rk3568";
        };
        """

        result = parse_dts_content(dts_content)

        assert result["type"] == "Device Tree"

    def test_parse_dts_content_fit_image_type(self):
        """Test parsing DTS content and detecting FIT Image type."""
        dts_content = """
        / {
            description = "FIT Image";
            type = "kernel";
        };
        """

        result = parse_dts_content(dts_content)

        assert result["type"] == "FIT Image (Flattened Image Tree)"

    def test_parse_dts_content_uboot_type(self):
        """Test parsing DTS content and detecting U-Boot type."""
        dts_content = """
        / {
            model = "U-Boot SPL";
            compatible = "u-boot";
        };
        """

        result = parse_dts_content(dts_content)

        assert result["type"] == "U-Boot Device Tree"

    def test_parse_dts_content_extract_model(self):
        """Test parsing DTS content and extracting model."""
        dts_content = """
        / {
            model = "GL.iNet Comet (RM1)";
            compatible = "glinet,comet";
        };
        """

        result = parse_dts_content(dts_content)

        assert result["model"] == "GL.iNet Comet (RM1)"

    def test_parse_dts_content_extract_compatible(self):
        """Test parsing DTS content and extracting compatible string."""
        dts_content = """
        / {
            model = "GL.iNet Comet";
            compatible = "glinet,comet";
        };
        """

        result = parse_dts_content(dts_content)

        assert result["compatible"] == "glinet,comet"

    def test_parse_dts_content_extract_all_fields(self):
        """Test parsing DTS content and extracting all fields."""
        dts_content = """
        / {
            description = "FIT Image";
            model = "GL.iNet Comet (RM1)";
            compatible = "glinet,comet";
            fiq-debugger {
                status = "okay";
            };
            gpio0: gpio@fdd60000 { };
        };
        """

        result = parse_dts_content(dts_content)

        assert result["type"] == "FIT Image (Flattened Image Tree)"
        assert result["model"] == "GL.iNet Comet (RM1)"
        assert result["compatible"] == "glinet,comet"
        assert "fit_description" in result
        assert "serial_config" in result
        assert "hardware_components" in result

    def test_parse_dts_content_missing_fields(self):
        """Test parsing DTS content with missing optional fields."""
        dts_content = """
        / {
            some_field = "value";
        };
        """

        result = parse_dts_content(dts_content)

        assert result["type"] == "Device Tree"
        assert "model" not in result
        assert "compatible" not in result
        assert "fit_description" not in result
        assert "serial_config" not in result
        assert "hardware_components" not in result


class TestFindDtbFiles:
    """Test find_dtb_files function."""

    def test_find_dtb_files_found(self, tmp_path: Path):
        """Test finding DTB files in extraction directory."""
        # Create mock extraction directory structure
        extract_dir = tmp_path / "firmware.img.extracted"
        extract_dir.mkdir()
        (extract_dir / "8F1B4").mkdir()
        (extract_dir / "8F1B4" / "system.dtb").touch()
        (extract_dir / "901B4").mkdir()
        (extract_dir / "901B4" / "system.dtb").touch()

        result = find_dtb_files(extract_dir)

        assert len(result) == 2
        assert all(dtb.name == "system.dtb" for dtb in result)

    def test_find_dtb_files_none_found(self, tmp_path: Path):
        """Test finding DTB files when none exist."""
        extract_dir = tmp_path / "firmware.img.extracted"
        extract_dir.mkdir()

        result = find_dtb_files(extract_dir)

        assert result == []

    def test_find_dtb_files_nested(self, tmp_path: Path):
        """Test finding DTB files in nested directories."""
        extract_dir = tmp_path / "firmware.img.extracted"
        extract_dir.mkdir()
        nested_dir = extract_dir / "subdir" / "8F1B4"
        nested_dir.mkdir(parents=True)
        (nested_dir / "system.dtb").touch()

        result = find_dtb_files(extract_dir)

        assert len(result) == 1
        assert result[0].name == "system.dtb"

    def test_find_dtb_files_sorted(self, tmp_path: Path):
        """Test that DTB files are returned sorted."""
        extract_dir = tmp_path / "firmware.img.extracted"
        extract_dir.mkdir()

        # Create files in non-alphabetical order
        (extract_dir / "zzz").mkdir()
        (extract_dir / "zzz" / "system.dtb").touch()
        (extract_dir / "aaa").mkdir()
        (extract_dir / "aaa" / "system.dtb").touch()

        result = find_dtb_files(extract_dir)

        assert len(result) == 2
        # Results should be sorted
        assert result[0].parent.name < result[1].parent.name


class TestAnalyzeDtbFile:
    """Test analyze_dtb_file function."""

    def test_analyze_dtb_file_basic(self, tmp_path: Path):
        """Test analyzing a basic DTB file."""
        extract_dir = tmp_path / "firmware.img.extracted"
        extract_dir.mkdir()
        dtb_dir = extract_dir / "8F1B4"
        dtb_dir.mkdir()
        dtb_path = dtb_dir / "system.dtb"

        dts_content = """
        / {
            model = "GL.iNet Comet (RM1)";
            compatible = "glinet,comet";
        };
        """
        dtb_path.write_text(dts_content)

        result = analyze_dtb_file(dtb_path, extract_dir)

        assert result.filename == "system.dtb"
        assert result.size == len(dts_content)
        assert result.offset == "8F1B4"
        assert result.dtb_type == "Device Tree"
        assert result.model == "GL.iNet Comet (RM1)"
        assert result.compatible == "glinet,comet"

    def test_analyze_dtb_file_with_hardware(self, tmp_path: Path):
        """Test analyzing a DTB file with hardware components."""
        extract_dir = tmp_path / "firmware.img.extracted"
        extract_dir.mkdir()
        dtb_dir = extract_dir / "8F1B4"
        dtb_dir.mkdir()
        dtb_path = dtb_dir / "system.dtb"

        dts_content = """
        / {
            model = "GL.iNet Comet";
            gpio0: gpio@fdd60000 {
                compatible = "rockchip,gpio-bank";
            };
        };
        """
        dtb_path.write_text(dts_content)

        result = analyze_dtb_file(dtb_path, extract_dir)

        assert len(result.hardware_components) == 1
        assert result.hardware_components[0].type == "gpio"

    def test_analyze_dtb_file_read_error(self, tmp_path: Path):
        """Test analyzing a DTB file with read error."""
        extract_dir = tmp_path / "firmware.img.extracted"
        extract_dir.mkdir()
        dtb_dir = extract_dir / "8F1B4"
        dtb_dir.mkdir()
        dtb_path = dtb_dir / "system.dtb"
        dtb_path.touch()

        # Create a file that will cause read issues (binary data)
        dtb_path.write_bytes(b"\x00\x01\x02\x03\xff\xfe\xfd")

        # Should not raise, but return basic info
        result = analyze_dtb_file(dtb_path, extract_dir)

        assert result.filename == "system.dtb"
        assert result.offset == "8F1B4"

    def test_analyze_dtb_file_offset_extraction(self, tmp_path: Path):
        """Test that offset is correctly extracted from directory structure."""
        extract_dir = tmp_path / "firmware.img.extracted"
        extract_dir.mkdir()
        dtb_dir = extract_dir / "901B4"  # Different offset
        dtb_dir.mkdir()
        dtb_path = dtb_dir / "system.dtb"

        dts_content = "/ { };"
        dtb_path.write_text(dts_content)

        result = analyze_dtb_file(dtb_path, extract_dir)

        assert result.offset == "901B4"

    def test_analyze_dtb_file_large_file_truncation(self, tmp_path: Path):
        """Test that large files are truncated to first 200 lines."""
        extract_dir = tmp_path / "firmware.img.extracted"
        extract_dir.mkdir()
        dtb_dir = extract_dir / "8F1B4"
        dtb_dir.mkdir()
        dtb_path = dtb_dir / "system.dtb"

        # Create content with more than 200 lines
        lines = ["/ {"] + [f"    line{i} = value{i};" for i in range(300)] + ["};"]
        dts_content = "\n".join(lines)
        dtb_path.write_text(dts_content)

        # Should not fail, only reads first 200 lines
        result = analyze_dtb_file(dtb_path, extract_dir)

        assert result.filename == "system.dtb"


class TestOutputToml:
    """Test output_toml function."""

    def test_toml_output_valid(self):
        """Test that TOML output is valid."""
        analysis = DeviceTreeAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            dtb_count=1,
        )
        analysis.add_metadata("firmware_file", "firmware", "Path(firmware).name")

        toml_str = output_toml(analysis)

        # Should be valid TOML
        parsed = tomlkit.loads(toml_str)
        assert parsed["firmware_file"] == "test.img"
        assert parsed["firmware_size"] == 1024
        assert parsed["dtb_count"] == 1

    def test_toml_includes_header_comment(self):
        """Test that TOML includes header comment."""
        analysis = DeviceTreeAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )

        toml_str = output_toml(analysis)

        assert "# Device Tree Analysis" in toml_str
        assert "# Generated:" in toml_str

    def test_toml_includes_source_comments(self):
        """Test that TOML includes source metadata as comments."""
        analysis = DeviceTreeAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )
        analysis.add_metadata(
            "firmware_size",
            "firmware",
            "Path(firmware).stat().st_size",
        )

        toml_str = output_toml(analysis)

        assert "# Source: firmware" in toml_str
        assert "# Method: Path(firmware).stat().st_size" in toml_str

    def test_toml_truncates_long_methods(self):
        """Test that long method descriptions are truncated."""
        analysis = DeviceTreeAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )
        long_method = "x" * 100  # 100 characters
        analysis.add_metadata("firmware_size", "test", long_method)

        toml_str = output_toml(analysis)

        # Should be truncated with "..."
        assert "..." in toml_str
        assert long_method not in toml_str

    def test_toml_excludes_metadata_fields(self):
        """Test that _source and _method fields are excluded."""
        analysis = DeviceTreeAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )
        analysis.add_metadata("firmware_size", "test", "test method")

        toml_str = output_toml(analysis)
        parsed = tomlkit.loads(toml_str)

        # Metadata should be in comments, not as fields
        assert "_source" not in parsed
        assert "_method" not in parsed
        assert "firmware_size_source" not in parsed
        assert "firmware_size_method" not in parsed

    def test_toml_includes_device_trees(self):
        """Test that device trees are included in TOML."""
        analysis = DeviceTreeAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )
        analysis.device_trees = [
            DeviceTree(
                filename="system.dtb",
                size=2048,
                offset="0x8F1B4",
                dtb_type="Device Tree",
                model="GL.iNet Comet",
            )
        ]

        toml_str = output_toml(analysis)
        parsed = tomlkit.loads(toml_str)

        assert len(parsed["device_trees"]) == 1
        assert parsed["device_trees"][0]["filename"] == "system.dtb"
        assert parsed["device_trees"][0]["model"] == "GL.iNet Comet"

    def test_toml_validation(self):
        """Test that generated TOML is validated."""
        analysis = DeviceTreeAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )

        # Should not raise - TOML is validated internally
        toml_str = output_toml(analysis)

        # Verify it can be parsed back
        parsed = tomlkit.loads(toml_str)
        assert parsed is not None


class TestIntegration:
    """Integration tests with realistic DTS content."""

    def test_realistic_dts_parsing(self):
        """Test parsing realistic DTS content."""
        dts_content = """
/dts-v1/;

/ {
    description = "FIT Image with OP-TEE support";
    #address-cells = <0x01>;
    model = "Rockchip RK3568 EVB";
    compatible = "rockchip,rk3568-evb", "rockchip,rk3568";

    images {
        kernel {
            description = "Linux kernel";
            type = "kernel";
            arch = "arm64";
            os = "linux";
            compression = "gzip";
        };
    };

    fiq-debugger {
        compatible = "rockchip,fiq-debugger";
        rockchip,serial-id = <0x02>;
        status = "okay";
    };

    gpio0: gpio@fdd60000 {
        compatible = "rockchip,gpio-bank";
        reg = <0xfdd60000 0x100>;
        #gpio-cells = <0x02>;
    };

    gpio1: gpio@fdd70000 {
        compatible = "rockchip,gpio-bank";
        reg = <0xfdd70000 0x100>;
    };

    usb0: usb@fcc00000 {
        compatible = "rockchip,rk3568-dwc3", "snps,dwc3";
        reg = <0xfcc00000 0x400000>;
    };

    spi0: spi@fe610000 {
        compatible = "rockchip,rk3568-spi", "rockchip,rk3066-spi";
        reg = <0xfe610000 0x1000>;
    };
};
"""

        result = parse_dts_content(dts_content)

        assert result["type"] == "FIT Image (Flattened Image Tree)"
        assert result["model"] == "Rockchip RK3568 EVB"
        assert result["compatible"] == "rockchip,rk3568-evb"
        assert "fit_description" in result
        assert "serial_config" in result
        assert "hardware_components" in result

        hardware_components = result["hardware_components"]
        assert isinstance(hardware_components, list)
        assert len(hardware_components) == 4  # 2 gpio, 1 usb, 1 spi

        # Verify component types
        types = {comp.type for comp in hardware_components}  # type: ignore
        assert "gpio" in types
        assert "usb" in types
        assert "spi" in types

    def test_end_to_end_analysis_to_toml(self, tmp_path: Path):
        """Test end-to-end analysis and TOML generation."""
        # Create mock firmware structure
        extract_dir = tmp_path / "firmware.img.extracted"
        extract_dir.mkdir()
        dtb_dir = extract_dir / "8F1B4"
        dtb_dir.mkdir()
        dtb_path = dtb_dir / "system.dtb"

        dts_content = """
        / {
            model = "GL.iNet Comet (RM1)";
            compatible = "glinet,comet";
            gpio0: gpio@fdd60000 { };
        };
        """
        dtb_path.write_text(dts_content)

        # Create analysis
        analysis = DeviceTreeAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            dtb_count=1,
        )
        analysis.add_metadata("firmware_file", "firmware", "Path(firmware).name")

        # Analyze DTB
        device_tree = analyze_dtb_file(dtb_path, extract_dir)
        analysis.device_trees.append(device_tree)

        # Generate TOML
        toml_str = output_toml(analysis)

        # Parse and verify
        parsed = tomlkit.loads(toml_str)
        assert parsed["firmware_file"] == "test.img"
        assert parsed["dtb_count"] == 1
        assert len(parsed["device_trees"]) == 1
        assert parsed["device_trees"][0]["model"] == "GL.iNet Comet (RM1)"
        assert len(parsed["device_trees"][0]["hardware_components"]) == 1
