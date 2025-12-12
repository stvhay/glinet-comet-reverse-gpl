#!/usr/bin/env python3
"""Analyze device tree blobs from firmware.

Usage: ./scripts/analyze_device_trees.py [firmware.img] [--format FORMAT]

Outputs: TOML (default) or JSON to stdout with source metadata

This script extracts DTB files from the firmware and analyzes:
- Device tree model and compatible strings
- FIT image structure (if present)
- Hardware configuration details (GPIO, USB, SPI, I2C, UART)

Arguments:
    firmware.img      Path to firmware file (optional, downloads default if not provided)
    --format FORMAT   Output format: 'toml' (default) or 'json'
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lib.analysis_base import AnalysisBase
from lib.base_script import AnalysisScript
from lib.finders import find_files
from lib.firmware import extract_firmware
from lib.logging import info, section, warn

# Device tree analysis constants
FDT_MAGIC = "d00dfeed"  # FDT magic number (big-endian)
FIT_DESCRIPTION_MAX_LINES = 30
SERIAL_CONFIG_CONTEXT_LINES = 10
SERIAL_CONFIG_MAX_LINES = 20


@dataclass(frozen=True, slots=True)
class HardwareComponent:
    """A hardware component identified in the device tree."""

    type: str  # Component type (e.g., "gpio", "usb", "spi")
    node: str  # Device tree node name
    description: str  # Full description from DTS


@dataclass(frozen=True, slots=True)
class DeviceTree:
    """A device tree blob and its metadata."""

    filename: str
    size: int
    offset: str  # Hex offset in firmware
    dtb_type: str  # "FIT Image", "U-Boot Device Tree", or "Device Tree"
    model: str | None = None
    compatible: str | None = None
    fit_description: str | None = None
    serial_config: str | None = None
    hardware_components: list[HardwareComponent] = field(default_factory=list)


@dataclass(slots=True)
class DeviceTreeAnalysis(AnalysisBase):
    """Results of device tree analysis."""

    firmware_file: str
    firmware_size: int
    dtb_count: int = 0
    device_trees: list[DeviceTree] = field(default_factory=list)

    # Source metadata for each field
    _source: dict[str, str] = field(default_factory=dict)
    _method: dict[str, str] = field(default_factory=dict)

    def _convert_complex_field(self, key: str, value: Any) -> tuple[bool, Any]:
        """Convert complex fields to serializable format."""
        if key == "device_trees":
            return True, [
                {
                    k: v
                    for k, v in {
                        "filename": dt.filename,
                        "size": dt.size,
                        "offset": dt.offset,
                        "type": dt.dtb_type,
                        "model": dt.model,
                        "compatible": dt.compatible,
                        "fit_description": dt.fit_description,
                        "serial_config": dt.serial_config,
                        "hardware_components": [
                            {
                                "type": hc.type,
                                "node": hc.node,
                                "description": hc.description,
                            }
                            for hc in dt.hardware_components
                        ]
                        if dt.hardware_components
                        else None,
                    }.items()
                    if v is not None
                }
                for dt in value
            ]
        return False, None


def find_dtb_files(extract_dir: Path) -> list[Path]:
    """Find all device tree blob files in extraction directory."""
    # Look for system.dtb files (these are FIT images or DTBs extracted by binwalk)
    return find_files(extract_dir, ["system.dtb"], file_type="file")


def _extract_fit_description(dts_content: str) -> str | None:
    """Extract FIT image description from DTS content."""
    if "description" not in dts_content or "FIT" not in dts_content:
        return None

    fit_lines = []
    for line in dts_content.splitlines():
        if re.search(
            r"^\s*(description|type|arch|os|compression|algo|key-name-hint|sign-images)\s*=",
            line,
        ):
            fit_lines.append(line.strip())
            if len(fit_lines) >= FIT_DESCRIPTION_MAX_LINES:
                break

    return "\n".join(fit_lines) if fit_lines else None


def _extract_serial_config(dts_content: str) -> str | None:
    """Extract serial/UART configuration from DTS content."""
    if "baudrate" not in dts_content and "fiq-debugger" not in dts_content:
        return None

    serial_lines = []
    in_serial_block = False
    lines_collected = 0

    for line in dts_content.splitlines():
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


def _extract_hardware_components(dts_content: str) -> list[HardwareComponent]:
    """Extract hardware components from DTS content."""
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
        for match in re.finditer(pattern, dts_content):
            node = match.group(1)
            addr = match.group(2)
            description = f"{comp_type.upper()} controller at 0x{addr}"
            hardware_components.append(
                HardwareComponent(type=comp_type, node=node, description=description)
            )

    return hardware_components


def parse_dts_content(dts_content: str) -> dict[str, str | list[HardwareComponent]]:
    """Parse DTS content and extract key information.

    Args:
        dts_content: Device tree source content

    Returns:
        Dictionary with extracted information
    """
    result: dict[str, str | list[HardwareComponent]] = {}

    # Determine type
    if "FIT Image" in dts_content or re.search(r"fit.*source", dts_content):
        result["type"] = "FIT Image (Flattened Image Tree)"
    elif "U-Boot" in dts_content:
        result["type"] = "U-Boot Device Tree"
    else:
        result["type"] = "Device Tree"

    # Extract model
    if model_match := re.search(r'^\s*model\s*=\s*"([^"]*)"', dts_content, re.MULTILINE):
        result["model"] = model_match.group(1)

    # Extract compatible string
    if compat_match := re.search(r'^\s*compatible\s*=\s*"([^"]*)"', dts_content, re.MULTILINE):
        result["compatible"] = compat_match.group(1)

    # Extract FIT description if present
    if fit_desc := _extract_fit_description(dts_content):
        result["fit_description"] = fit_desc

    # Extract serial/UART configuration
    if serial_config := _extract_serial_config(dts_content):
        result["serial_config"] = serial_config

    # Extract hardware components
    if hardware_components := _extract_hardware_components(dts_content):
        result["hardware_components"] = hardware_components

    return result


def analyze_dtb_file(dtb_path: Path, extract_dir: Path) -> DeviceTree:
    """Analyze a single DTB file.

    Args:
        dtb_path: Path to DTB file
        extract_dir: Base extraction directory (for offset calculation)

    Returns:
        DeviceTree object with analysis results
    """
    # Get file size
    dtb_size = dtb_path.stat().st_size

    # Calculate offset from directory structure
    # binwalk creates directories like "8F1B4" for offset 0x8F1B4
    rel_path = dtb_path.relative_to(extract_dir)
    offset_dir = rel_path.parts[0] if rel_path.parts else "unknown"

    # Read content (binwalk may extract as text DTS, not binary DTB)
    try:
        with dtb_path.open("r", encoding="utf-8", errors="ignore") as f:
            dts_content = "".join(f.readlines()[:200])  # Read first 200 lines
    except Exception as e:
        warn(f"Failed to read {dtb_path}: {e}")
        dts_content = ""

    # Parse DTS content
    parsed = parse_dts_content(dts_content)

    return DeviceTree(
        filename=dtb_path.name,
        size=dtb_size,
        offset=offset_dir,
        dtb_type=str(parsed.get("type", "Device Tree")),
        model=parsed.get("model") if isinstance(parsed.get("model"), str) else None,
        compatible=parsed.get("compatible") if isinstance(parsed.get("compatible"), str) else None,
        fit_description=parsed.get("fit_description")
        if isinstance(parsed.get("fit_description"), str)
        else None,
        serial_config=parsed.get("serial_config")
        if isinstance(parsed.get("serial_config"), str)
        else None,
        hardware_components=parsed.get("hardware_components", [])  # type: ignore[arg-type]
        if isinstance(parsed.get("hardware_components"), list)
        else [],
    )


def analyze_device_trees(firmware_path: str, work_dir: Path) -> DeviceTreeAnalysis:
    """Analyze device trees in firmware and return structured results.

    Args:
        firmware_path: Path to firmware image
        work_dir: Working directory for extraction

    Returns:
        DeviceTreeAnalysis object with all extracted data
    """
    # Extract firmware
    section("Extracting Firmware")
    firmware = Path(firmware_path)
    extract_dir = extract_firmware(firmware, work_dir)

    # Create analysis object with firmware metadata
    analysis = DeviceTreeAnalysis(
        firmware_file=firmware.name,
        firmware_size=firmware.stat().st_size,
    )
    analysis.add_metadata("firmware_file", "firmware", "Path(firmware).name")
    analysis.add_metadata("firmware_size", "firmware", "Path(firmware).stat().st_size")

    # Find DTB files
    section("Finding Device Tree Blobs")
    dtb_files = find_dtb_files(extract_dir)
    analysis.set_count_with_metadata("dtb_count", dtb_files, "binwalk", "find extracted DTB files")
    info(f"Found {analysis.dtb_count} device tree blobs")

    # Analyze each DTB
    for dtb_path in dtb_files:
        info(f"Analyzing: {dtb_path.name}")
        device_tree = analyze_dtb_file(dtb_path, extract_dir)
        analysis.device_trees.append(device_tree)

    return analysis


# Field order for TOML output
SIMPLE_FIELDS = [
    "firmware_file",
    "firmware_size",
    "dtb_count",
]

COMPLEX_FIELDS = [
    "device_trees",
]


class DeviceTreeScript(AnalysisScript):
    """Device tree analysis script."""

    def __init__(self):
        """Initialize device tree analysis script."""
        super().__init__(
            description="Analyze device tree blobs from firmware",
            title="Device tree analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )

    def analyze(self, firmware_path: str) -> AnalysisBase:
        """Run device tree analysis on firmware.

        Args:
            firmware_path: Path to firmware file

        Returns:
            DeviceTreeAnalysis results
        """
        return analyze_device_trees(firmware_path, self.work_dir)

    def get_success_message(self, analysis: AnalysisBase) -> str:
        """Generate success message after analysis.

        Args:
            analysis: The completed analysis results

        Returns:
            Success message string
        """
        if isinstance(analysis, DeviceTreeAnalysis):
            return self.format_count_message(analysis.dtb_count, "device tree")
        return super().get_success_message(analysis)


if __name__ == "__main__":
    DeviceTreeScript().run()
