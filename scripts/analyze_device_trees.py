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

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lib.analysis_base import AnalysisBase
from lib.base_script import AnalysisScript
from lib.devicetree import DeviceTreeParser, HardwareComponent
from lib.finders import find_files
from lib.firmware import extract_firmware
from lib.logging import info, section, warn

# Device tree analysis constants
FDT_MAGIC = "d00dfeed"  # FDT magic number (big-endian)


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


def parse_dts_content(dts_content: str) -> dict[str, str | list[HardwareComponent]]:
    """Parse DTS content and extract key information.

    Args:
        dts_content: Device tree source content

    Returns:
        Dictionary with extracted information
    """
    # Use DeviceTreeParser for all extraction
    parser = DeviceTreeParser(dts_content)
    return parser.parse()


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
