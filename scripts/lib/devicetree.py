#!/usr/bin/env python3
"""Device tree parsing utilities.

This module provides a DeviceTreeParser class for extracting information
from device tree source (DTS) files. It consolidates DTS parsing logic
that was duplicated across multiple analysis scripts.
"""

import re
from dataclasses import dataclass

# DTS parsing constants
FIT_DESCRIPTION_MAX_LINES = 30
SERIAL_CONFIG_CONTEXT_LINES = 10
SERIAL_CONFIG_MAX_LINES = 20


@dataclass(frozen=True, slots=True)
class HardwareComponent:
    """A hardware component identified in the device tree."""

    type: str  # Component type (e.g., "gpio", "usb", "spi")
    node: str  # Device tree node name
    description: str  # Full description from DTS


class DeviceTreeParser:
    """Parser for device tree source (DTS) content.

    Extracts structured information from DTS files including:
    - Model and compatible strings
    - FIT image descriptions
    - Serial/UART configuration
    - Hardware components (GPIO, USB, SPI, I2C, UART)

    Example:
        >>> dts_content = Path("system.dtb").read_text()
        >>> parser = DeviceTreeParser(dts_content)
        >>> model = parser.extract_model()
        >>> components = parser.extract_hardware_components()
    """

    def __init__(self, dts_content: str):
        """Initialize parser with DTS content.

        Args:
            dts_content: Device tree source content as string
        """
        self.content = dts_content

    def extract_model(self) -> str | None:
        """Extract model string from DTS.

        Returns:
            Model string if found, None otherwise

        Example:
            >>> parser.extract_model()
            'Rockchip RK3588 GL.iNet Comet RM1'
        """
        if model_match := re.search(r'^\s*model\s*=\s*"([^"]*)"', self.content, re.MULTILINE):
            return model_match.group(1)
        return None

    def extract_compatible(self) -> str | None:
        """Extract compatible string from DTS.

        Returns:
            Compatible string if found, None otherwise

        Example:
            >>> parser.extract_compatible()
            'glinet,comet-rm1'
        """
        if compat_match := re.search(r'^\s*compatible\s*=\s*"([^"]*)"', self.content, re.MULTILINE):
            return compat_match.group(1)
        return None

    def extract_fit_description(self) -> str | None:
        """Extract FIT image description from DTS.

        FIT (Flattened Image Tree) images contain metadata about embedded images.
        This extracts key FIT properties like description, type, arch, os, etc.

        Returns:
            Multi-line FIT description if present, None otherwise
        """
        if "description" not in self.content or "FIT" not in self.content:
            return None

        fit_lines = []
        for line in self.content.splitlines():
            if re.search(
                r"^\s*(description|type|arch|os|compression|algo|key-name-hint|sign-images)\s*=",
                line,
            ):
                fit_lines.append(line.strip())
                if len(fit_lines) >= FIT_DESCRIPTION_MAX_LINES:
                    break

        return "\n".join(fit_lines) if fit_lines else None

    def extract_serial_config(self) -> str | None:
        """Extract serial/UART configuration from DTS.

        Looks for serial/UART configuration including fiq-debugger and
        serial@ nodes with their properties.

        Returns:
            Multi-line serial configuration if found, None otherwise
        """
        if "baudrate" not in self.content and "fiq-debugger" not in self.content:
            return None

        serial_lines = []
        in_serial_block = False
        lines_collected = 0

        for line in self.content.splitlines():
            if "fiq-debugger" in line or "serial@" in line:
                in_serial_block = True
                serial_lines.append(line.strip())
                lines_collected = 0
            elif in_serial_block:
                serial_lines.append(line.strip())
                lines_collected += 1
                if lines_collected >= SERIAL_CONFIG_CONTEXT_LINES:
                    break

        return "\n".join(serial_lines[:SERIAL_CONFIG_MAX_LINES]) if serial_lines else None

    def extract_hardware_components(self) -> list[HardwareComponent]:
        """Extract hardware components from DTS.

        Identifies GPIO, USB, SPI, I2C, and UART controllers with their
        memory-mapped addresses.

        Returns:
            List of HardwareComponent objects

        Example:
            >>> components = parser.extract_hardware_components()
            >>> [c.type for c in components]
            ['gpio', 'gpio', 'usb', 'spi', 'i2c', 'uart']
        """
        hardware_components: list[HardwareComponent] = []

        # Map of component types to their regex patterns
        component_patterns = {
            "gpio": r"(gpio\d+):\s*gpio@([0-9a-fA-F]+)",
            "usb": r"(usb\d+):\s*usb@([0-9a-fA-F]+)",
            "spi": r"(spi\d+):\s*spi@([0-9a-fA-F]+)",
            "i2c": r"(i2c\d+):\s*i2c@([0-9a-fA-F]+)",
            "uart": r"(serial\d+|uart\d+):\s*serial@([0-9a-fA-F]+)",
        }

        for comp_type, pattern in component_patterns.items():
            for match in re.finditer(pattern, self.content):
                node = match.group(1)
                addr = match.group(2)
                description = f"{comp_type.upper()} controller at 0x{addr}"
                hardware_components.append(
                    HardwareComponent(type=comp_type, node=node, description=description)
                )

        return hardware_components

    def is_fit_image(self) -> bool:
        """Check if DTS represents a FIT image.

        Returns:
            True if FIT image structure detected, False otherwise
        """
        return "FIT Image" in self.content or bool(re.search(r"fit.*source", self.content))

    def get_type(self) -> str:
        """Determine device tree type.

        Returns:
            One of:
            - "FIT Image (Flattened Image Tree)"
            - "U-Boot Device Tree"
            - "Device Tree"
        """
        if self.is_fit_image():
            return "FIT Image (Flattened Image Tree)"
        if "U-Boot" in self.content:
            return "U-Boot Device Tree"
        return "Device Tree"

    def parse(self) -> dict[str, str | list[HardwareComponent]]:
        """Parse DTS content and extract all information.

        Convenience method that calls all extraction methods and returns
        a dictionary with results.

        Returns:
            Dictionary with keys:
            - type: Device tree type
            - model: Model string (if present)
            - compatible: Compatible string (if present)
            - fit_description: FIT description (if present)
            - serial_config: Serial configuration (if present)
            - hardware_components: List of HardwareComponent objects

        Example:
            >>> parser = DeviceTreeParser(dts_content)
            >>> result = parser.parse()
            >>> print(result['model'])
            'Rockchip RK3588 GL.iNet Comet RM1'
        """
        result: dict[str, str | list[HardwareComponent]] = {}

        # Type
        result["type"] = self.get_type()

        # Model
        if model := self.extract_model():
            result["model"] = model

        # Compatible
        if compatible := self.extract_compatible():
            result["compatible"] = compatible

        # FIT description
        if fit_desc := self.extract_fit_description():
            result["fit_description"] = fit_desc

        # Serial config
        if serial_config := self.extract_serial_config():
            result["serial_config"] = serial_config

        # Hardware components
        if hardware_components := self.extract_hardware_components():
            result["hardware_components"] = hardware_components

        return result
