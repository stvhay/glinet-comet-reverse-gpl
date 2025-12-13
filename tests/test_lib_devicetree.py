#!/usr/bin/env python3
"""Tests for scripts/lib/devicetree.py."""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib.devicetree import DeviceTreeParser, HardwareComponent


class TestHardwareComponent:
    """Test HardwareComponent dataclass."""

    def test_hardware_component_creation(self):
        """Test creating HardwareComponent."""
        comp = HardwareComponent(type="gpio", node="gpio0", description="GPIO controller at 0x1234")
        assert comp.type == "gpio"
        assert comp.node == "gpio0"
        assert comp.description == "GPIO controller at 0x1234"

    def test_hardware_component_immutable(self):
        """Test that HardwareComponent is frozen (immutable)."""
        comp = HardwareComponent(type="usb", node="usb0", description="USB controller")
        try:
            comp.type = "spi"  # Should raise FrozenInstanceError
            raise AssertionError("Should not be able to modify frozen dataclass")
        except Exception:
            pass  # Expected


class TestDeviceTreeParserExtractModel:
    """Test extract_model method."""

    def test_extract_model_simple(self):
        """Test extracting simple model string."""
        dts = 'model = "Rockchip RK3588 Test Board";'
        parser = DeviceTreeParser(dts)
        assert parser.extract_model() == "Rockchip RK3588 Test Board"

    def test_extract_model_with_whitespace(self):
        """Test model extraction with various whitespace."""
        dts = '  model  =  "Test Model"  ;'
        parser = DeviceTreeParser(dts)
        assert parser.extract_model() == "Test Model"

    def test_extract_model_multiline(self):
        """Test model extraction from multiline DTS."""
        dts = """
        / {
            model = "GL.iNet Comet RM1";
            compatible = "glinet,comet-rm1";
        };
        """
        parser = DeviceTreeParser(dts)
        assert parser.extract_model() == "GL.iNet Comet RM1"

    def test_extract_model_missing(self):
        """Test when model is missing."""
        dts = 'compatible = "test\ndevice";'
        parser = DeviceTreeParser(dts)
        assert parser.extract_model() is None

    def test_extract_model_empty_string(self):
        """Test with empty DTS content."""
        parser = DeviceTreeParser("")
        assert parser.extract_model() is None


class TestDeviceTreeParserExtractCompatible:
    """Test extract_compatible method."""

    def test_extract_compatible_simple(self):
        """Test extracting simple compatible string."""
        dts = 'compatible = "glinet,comet-rm1";'
        parser = DeviceTreeParser(dts)
        assert parser.extract_compatible() == "glinet,comet-rm1"

    def test_extract_compatible_multiline(self):
        """Test compatible extraction from multiline DTS."""
        dts = """
        / {
            model = "Test Board";
            compatible = "rockchip,rk3588";
        };
        """
        parser = DeviceTreeParser(dts)
        assert parser.extract_compatible() == "rockchip,rk3588"

    def test_extract_compatible_missing(self):
        """Test when compatible is missing."""
        dts = 'model = "Test Board";'
        parser = DeviceTreeParser(dts)
        assert parser.extract_compatible() is None


class TestDeviceTreeParserExtractFitDescription:
    """Test extract_fit_description method."""

    def test_extract_fit_description_simple(self):
        """Test extracting FIT description."""
        dts = """
        FIT Image
        description = "U-Boot FIT Image";
        type = "kernel";
        arch = "arm64";
        """
        parser = DeviceTreeParser(dts)
        result = parser.extract_fit_description()
        assert result is not None
        assert "description" in result
        assert "type" in result
        assert "arch" in result

    def test_extract_fit_description_multiple_properties(self):
        """Test FIT with multiple properties."""
        dts = """
        FIT Image
        description = "Test Image";
        type = "kernel";
        os = "linux";
        compression = "gzip";
        algo = "sha256";
        """
        parser = DeviceTreeParser(dts)
        result = parser.extract_fit_description()
        assert result is not None
        assert "description" in result
        assert "type" in result
        assert "os" in result
        assert "compression" in result
        assert "algo" in result

    def test_extract_fit_description_not_fit(self):
        """Test when DTS is not a FIT image."""
        dts = 'model = "Test Board";'
        parser = DeviceTreeParser(dts)
        assert parser.extract_fit_description() is None

    def test_extract_fit_description_max_lines(self):
        """Test that FIT extraction respects line limit."""
        # Create DTS with 40 FIT properties (exceeds max)
        lines = ["FIT Image description"]
        lines.extend([f'description = "value{i}";' for i in range(40)])
        dts = "\n".join(lines)

        parser = DeviceTreeParser(dts)
        result = parser.extract_fit_description()
        assert result is not None
        # Should be limited by FIT_DESCRIPTION_MAX_LINES (30)
        assert len(result.splitlines()) <= 30


class TestDeviceTreeParserExtractSerialConfig:
    """Test extract_serial_config method."""

    def test_extract_serial_config_fiq_debugger(self):
        """Test extracting serial config with fiq-debugger."""
        dts = """
        fiq-debugger {
            compatible = "rockchip,fiq-debugger";
            status = "okay";
        };
        """
        parser = DeviceTreeParser(dts)
        result = parser.extract_serial_config()
        assert result is not None
        assert "fiq-debugger" in result

    def test_extract_serial_config_serial_node(self):
        """Test extracting serial config with serial@ node."""
        dts = """
        baudrate = <1500000>;
        serial@fe650000 {
            compatible = "rockchip,rk3588-uart";
            reg = <0xfe650000 0x100>;
        };
        """
        parser = DeviceTreeParser(dts)
        result = parser.extract_serial_config()
        assert result is not None
        assert "serial@" in result

    def test_extract_serial_config_baudrate(self):
        """Test extracting serial config with baudrate."""
        dts = """
        fiq-debugger {
            baudrate = <1500000>;
        };
        """
        parser = DeviceTreeParser(dts)
        result = parser.extract_serial_config()
        assert result is not None
        assert "baudrate" in result

    def test_extract_serial_config_missing(self):
        """Test when serial config is missing."""
        dts = 'model = "Test Board";'
        parser = DeviceTreeParser(dts)
        assert parser.extract_serial_config() is None


class TestDeviceTreeParserExtractHardwareComponents:
    """Test extract_hardware_components method."""

    def test_extract_gpio_components(self):
        """Test extracting GPIO components."""
        dts = """
        gpio0: gpio@fd8a0000 {
            compatible = "rockchip,gpio";
        };
        gpio1: gpio@fec20000 {
            compatible = "rockchip,gpio";
        };
        """
        parser = DeviceTreeParser(dts)
        components = parser.extract_hardware_components()

        assert len(components) == 2
        assert components[0].type == "gpio"
        assert components[0].node == "gpio0"
        assert "fd8a0000" in components[0].description

    def test_extract_usb_components(self):
        """Test extracting USB components."""
        dts = """
        usb0: usb@fc000000 {
            compatible = "rockchip,rk3588-usb";
        };
        """
        parser = DeviceTreeParser(dts)
        components = parser.extract_hardware_components()

        assert len(components) == 1
        assert components[0].type == "usb"
        assert components[0].node == "usb0"
        assert "fc000000" in components[0].description

    def test_extract_spi_components(self):
        """Test extracting SPI components."""
        dts = 'spi0: spi@feb10000 { compatible = "rockchip,spi"; };'
        parser = DeviceTreeParser(dts)
        components = parser.extract_hardware_components()

        assert len(components) == 1
        assert components[0].type == "spi"

    def test_extract_i2c_components(self):
        """Test extracting I2C components."""
        dts = 'i2c0: i2c@fd880000 { compatible = "rockchip,i2c"; };'
        parser = DeviceTreeParser(dts)
        components = parser.extract_hardware_components()

        assert len(components) == 1
        assert components[0].type == "i2c"

    def test_extract_uart_components(self):
        """Test extracting UART components."""
        dts = """
        serial0: serial@fd890000 { };
        uart1: serial@fe650000 { };
        """
        parser = DeviceTreeParser(dts)
        components = parser.extract_hardware_components()

        assert len(components) == 2
        assert all(c.type == "uart" for c in components)

    def test_extract_mixed_components(self):
        """Test extracting multiple component types."""
        dts = """
        gpio0: gpio@fd8a0000 { };
        usb0: usb@fc000000 { };
        spi0: spi@feb10000 { };
        i2c0: i2c@fd880000 { };
        serial0: serial@fd890000 { };
        """
        parser = DeviceTreeParser(dts)
        components = parser.extract_hardware_components()

        assert len(components) == 5
        types = {c.type for c in components}
        assert types == {"gpio", "usb", "spi", "i2c", "uart"}

    def test_extract_hardware_components_empty(self):
        """Test when no hardware components found."""
        dts = 'model = "Test Board";'
        parser = DeviceTreeParser(dts)
        components = parser.extract_hardware_components()

        assert len(components) == 0


class TestDeviceTreeParserIsFitImage:
    """Test is_fit_image method."""

    def test_is_fit_image_true_with_fit_text(self):
        """Test FIT image detection with 'FIT Image' text."""
        dts = "FIT Image description"
        parser = DeviceTreeParser(dts)
        assert parser.is_fit_image() is True

    def test_is_fit_image_true_with_fit_source(self):
        """Test FIT image detection with 'fit source' pattern."""
        dts = "fit source kernel image"
        parser = DeviceTreeParser(dts)
        assert parser.is_fit_image() is True

    def test_is_fit_image_false(self):
        """Test non-FIT DTS."""
        dts = 'model = "Regular Device Tree";'
        parser = DeviceTreeParser(dts)
        assert parser.is_fit_image() is False


class TestDeviceTreeParserGetType:
    """Test get_type method."""

    def test_get_type_fit_image(self):
        """Test type detection for FIT image."""
        dts = "FIT Image description"
        parser = DeviceTreeParser(dts)
        assert parser.get_type() == "FIT Image (Flattened Image Tree)"

    def test_get_type_uboot(self):
        """Test type detection for U-Boot device tree."""
        dts = "U-Boot device tree source"
        parser = DeviceTreeParser(dts)
        assert parser.get_type() == "U-Boot Device Tree"

    def test_get_type_regular(self):
        """Test type detection for regular device tree."""
        dts = 'model = "Regular Board";'
        parser = DeviceTreeParser(dts)
        assert parser.get_type() == "Device Tree"


class TestDeviceTreeParserParse:
    """Test parse method (integration test)."""

    def test_parse_complete_dts(self):
        """Test parsing complete DTS with all features."""
        dts = """
        / {
            model = "Rockchip RK3588 Test Board";
            compatible = "rockchip,rk3588";

            gpio0: gpio@fd8a0000 {
                compatible = "rockchip,gpio";
            };

            usb0: usb@fc000000 {
                compatible = "rockchip,usb";
            };
        };
        """
        parser = DeviceTreeParser(dts)
        result = parser.parse()

        assert result["type"] == "Device Tree"
        assert result["model"] == "Rockchip RK3588 Test Board"
        assert result["compatible"] == "rockchip,rk3588"
        assert "hardware_components" in result
        assert len(result["hardware_components"]) == 2

    def test_parse_fit_image(self):
        """Test parsing FIT image DTS."""
        dts = """
        FIT Image
        description = "U-Boot FIT Image";
        type = "kernel";
        arch = "arm64";

        gpio0: gpio@fd8a0000 { };
        """
        parser = DeviceTreeParser(dts)
        result = parser.parse()

        assert result["type"] == "FIT Image (Flattened Image Tree)"
        assert "fit_description" in result
        assert "hardware_components" in result

    def test_parse_minimal_dts(self):
        """Test parsing minimal DTS."""
        dts = 'model = "Minimal Board";'
        parser = DeviceTreeParser(dts)
        result = parser.parse()

        assert result["type"] == "Device Tree"
        assert result["model"] == "Minimal Board"
        assert "compatible" not in result  # Optional fields not present
        assert "fit_description" not in result
        assert "serial_config" not in result
        assert "hardware_components" not in result  # Empty list not included

    def test_parse_empty_dts(self):
        """Test parsing empty DTS."""
        parser = DeviceTreeParser("")
        result = parser.parse()

        assert result["type"] == "Device Tree"
        assert len(result) == 1  # Only type field


class TestIntegration:
    """Integration tests with realistic DTS content."""

    def test_realistic_rockchip_dts(self):
        """Test with realistic Rockchip DTS snippet."""
        dts = """
        /dts-v1/;

        / {
            compatible = "rockchip,rk3588";
            model = "Rockchip RK3588 EVB";

            gpio0: gpio@fd8a0000 {
                compatible = "rockchip,gpio-bank";
                reg = <0x0 0xfd8a0000 0x0 0x100>;
                interrupts = <0 277 4>;
            };

            usb0: usb@fc800000 {
                compatible = "generic-ehci";
                reg = <0x0 0xfc800000 0x0 0x40000>;
            };

            serial2: serial@feb50000 {
                compatible = "rockchip,rk3588-uart", "snps,dw-apb-uart";
                reg = <0x0 0xfeb50000 0x0 0x100>;
            };
        };
        """
        parser = DeviceTreeParser(dts)
        result = parser.parse()

        assert result["model"] == "Rockchip RK3588 EVB"
        assert result["compatible"] == "rockchip,rk3588"
        components = result["hardware_components"]
        assert len(components) == 3
        types = {c.type for c in components}
        assert types == {"gpio", "usb", "uart"}

    def test_realistic_fit_image(self):
        """Test with realistic FIT image DTS."""
        dts = """
        /dts-v1/;
        FIT Image

        / {
            description = "U-Boot fitImage for Rockchip RK3588";
            #address-cells = <1>;

            images {
                kernel {
                    description = "Linux kernel";
                    type = "kernel";
                    arch = "arm64";
                    os = "linux";
                    compression = "gzip";
                };
            };

            configurations {
                default = "config-1";
                config-1 {
                    description = "Boot Linux kernel";
                    kernel = "kernel";
                };
            };
        };
        """
        parser = DeviceTreeParser(dts)
        result = parser.parse()

        assert result["type"] == "FIT Image (Flattened Image Tree)"
        assert "fit_description" in result
        fit_desc = result["fit_description"]
        assert "description" in fit_desc
        assert "type" in fit_desc
        assert "arch" in fit_desc
