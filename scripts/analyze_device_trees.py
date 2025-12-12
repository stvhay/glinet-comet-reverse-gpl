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

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field, fields
from datetime import UTC, datetime
from pathlib import Path

import tomlkit

# Color codes for stderr logging
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
NC = "\033[0m"  # No Color

# Device tree analysis constants
FDT_MAGIC = "d00dfeed"  # FDT magic number (big-endian)
TOML_MAX_COMMENT_LENGTH = 80
TOML_COMMENT_TRUNCATE_LENGTH = 77
FIT_DESCRIPTION_MAX_LINES = 30
SERIAL_CONFIG_CONTEXT_LINES = 10
SERIAL_CONFIG_MAX_LINES = 20


def info(msg: str) -> None:
    """Log info message to stderr."""
    print(f"{GREEN}[INFO]{NC} {msg}", file=sys.stderr)


def warn(msg: str) -> None:
    """Log warning message to stderr."""
    print(f"{YELLOW}[WARN]{NC} {msg}", file=sys.stderr)


def error(msg: str) -> None:
    """Log error message to stderr."""
    print(f"{RED}[ERROR]{NC} {msg}", file=sys.stderr)


def success(msg: str) -> None:
    """Log success message to stderr."""
    print(f"{GREEN}[OK]{NC} {msg}", file=sys.stderr)


def section(msg: str) -> None:
    """Log section header to stderr."""
    print(f"\n{BLUE}=== {msg} ==={NC}", file=sys.stderr)


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
class DeviceTreeAnalysis:
    """Results of device tree analysis."""

    firmware_file: str
    firmware_size: int
    dtb_count: int = 0
    device_trees: list[DeviceTree] = field(default_factory=list)

    # Source metadata for each field
    _source: dict[str, str] = field(default_factory=dict)
    _method: dict[str, str] = field(default_factory=dict)

    def add_metadata(self, field_name: str, source: str, method: str) -> None:
        """Add source metadata for a field."""
        self._source[field_name] = source
        self._method[field_name] = method

    def to_dict(self) -> dict:
        """Convert to dictionary with source metadata."""
        result = {}
        for fld in fields(self):
            key = fld.name
            if key.startswith("_"):
                continue

            value = getattr(self, key)
            if value is None:
                continue

            if key == "device_trees":
                # Convert device trees to dicts, filtering out None values
                result[key] = [
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
            else:
                result[key] = value

                # Add source metadata if available
                if key in self._source:
                    result[f"{key}_source"] = self._source[key]
                if key in self._method:
                    result[f"{key}_method"] = self._method[key]

        return result


def run_binwalk_extract(firmware: Path, work_dir: Path) -> Path:
    """Extract firmware using binwalk and return extraction directory."""
    extract_base = work_dir / "extractions"
    extract_dir = extract_base / f"{firmware.name}.extracted"

    if extract_dir.exists():
        info(f"Using existing extraction: {extract_dir}")
        return extract_dir

    info("Extracting firmware with binwalk...")
    extract_base.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(
            ["binwalk", "-e", "--run-as=root", str(firmware)],
            cwd=extract_base,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        error("binwalk command not found")
        error("Please run this script within 'nix develop' shell")
        sys.exit(1)

    # Check for extraction in expected location or nested extractions dir
    if not extract_dir.exists():
        # Sometimes binwalk creates a nested extractions directory
        nested_extract_dir = extract_base / "extractions" / f"{firmware.name}.extracted"
        if nested_extract_dir.exists():
            extract_dir = nested_extract_dir
        else:
            error(f"Extraction failed: {extract_dir} not found")
            sys.exit(1)

    return extract_dir


def find_dtb_files(extract_dir: Path) -> list[Path]:
    """Find all device tree blob files in extraction directory."""
    # Look for system.dtb files (these are FIT images or DTBs extracted by binwalk)
    dtb_files = list(extract_dir.rglob("system.dtb"))
    return sorted(dtb_files)


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


def analyze_device_trees(firmware_path: str) -> DeviceTreeAnalysis:
    """Analyze device trees in firmware and return structured results.

    Args:
        firmware_path: Path to firmware image

    Returns:
        DeviceTreeAnalysis object with all extracted data
    """
    firmware = Path(firmware_path)

    if not firmware.exists():
        error(f"Firmware file not found: {firmware}")
        sys.exit(1)

    info(f"Analyzing: {firmware}")

    # Determine working directory
    work_dir = Path("/tmp/fw_analysis")
    work_dir.mkdir(parents=True, exist_ok=True)

    # Extract firmware
    section("Extracting Firmware")
    extract_dir = run_binwalk_extract(firmware, work_dir)

    # Create analysis object
    firmware_size = firmware.stat().st_size
    analysis = DeviceTreeAnalysis(
        firmware_file=firmware.name,
        firmware_size=firmware_size,
    )

    analysis.add_metadata("firmware_file", "firmware", "Path(firmware).name")
    analysis.add_metadata("firmware_size", "firmware", "Path(firmware).stat().st_size")

    # Find DTB files
    section("Finding Device Tree Blobs")
    dtb_files = find_dtb_files(extract_dir)
    analysis.dtb_count = len(dtb_files)
    analysis.add_metadata("dtb_count", "binwalk", "find extracted DTB files")

    info(f"Found {analysis.dtb_count} DTB/DTS files")

    # Analyze each DTB
    for dtb_path in dtb_files:
        info(f"Analyzing: {dtb_path.name}")
        device_tree = analyze_dtb_file(dtb_path, extract_dir)
        analysis.device_trees.append(device_tree)

    return analysis


def output_toml(analysis: DeviceTreeAnalysis) -> str:
    """Convert analysis to TOML format.

    Args:
        analysis: DeviceTreeAnalysis object

    Returns:
        TOML string with source metadata as comments
    """
    doc = tomlkit.document()

    # Add header
    doc.add(tomlkit.comment("Device Tree Analysis"))
    doc.add(tomlkit.comment(f"Generated: {datetime.now(UTC).isoformat()}"))
    doc.add(tomlkit.nl())

    # Convert analysis to dict
    data = analysis.to_dict()

    # Add fields to TOML, with source metadata as comments
    for key, value in data.items():
        # Skip metadata fields
        if key.endswith(("_source", "_method")):
            continue

        # Add source metadata as comment above field
        if f"{key}_source" in data:
            doc.add(tomlkit.comment(f"Source: {data[f'{key}_source']}"))
        if f"{key}_method" in data:
            method = data[f"{key}_method"]
            # Wrap long method descriptions
            if len(method) > TOML_MAX_COMMENT_LENGTH:
                doc.add(tomlkit.comment(f"Method: {method[:TOML_COMMENT_TRUNCATE_LENGTH]}..."))
            else:
                doc.add(tomlkit.comment(f"Method: {method}"))

        doc.add(key, value)
        doc.add(tomlkit.nl())

    # Generate TOML string
    toml_str = tomlkit.dumps(doc)

    # Validate by parsing it back
    try:
        tomlkit.loads(toml_str)
    except Exception as e:
        error(f"Generated invalid TOML: {e}")
        sys.exit(1)

    return toml_str


def main() -> None:
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Analyze device tree blobs from firmware",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "firmware",
        nargs="?",
        help="Path to firmware file (downloads default if not provided)",
    )
    parser.add_argument(
        "--format",
        choices=["toml", "json"],
        default="toml",
        help="Output format (default: toml)",
    )
    args = parser.parse_args()

    # Determine paths
    work_dir = Path("/tmp/fw_analysis")

    # Get firmware path
    if args.firmware:
        firmware_path = args.firmware
    else:
        # Default firmware URL - download if needed
        firmware_url = "https://fw.gl-inet.com/kvm/rm1/release/glkvm-RM1-1.7.2-1128-1764344791.img"
        firmware_file = firmware_url.split("/")[-1]
        firmware_path = str(work_dir / firmware_file)

        if not Path(firmware_path).exists():
            info(f"Downloading firmware: {firmware_url}")
            work_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["curl", "-L", "-o", firmware_path, firmware_url],
                check=True,
            )

    # Analyze device trees
    analysis = analyze_device_trees(firmware_path)

    # Output in requested format
    if args.format == "json":
        json_str = json.dumps(analysis.to_dict(), indent=2)
        # Validate by parsing it back
        try:
            json.loads(json_str)
        except Exception as e:
            error(f"Generated invalid JSON: {e}")
            sys.exit(1)
        print(json_str)
    else:  # toml
        print(output_toml(analysis))

    success(f"Analyzed {analysis.dtb_count} device tree(s)")


if __name__ == "__main__":
    main()
