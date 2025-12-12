#!/usr/bin/env python3
"""Analyze firmware structure using binwalk.

Usage: ./scripts/analyze-binwalk.py [firmware.img] [--format FORMAT]

Outputs: TOML (default) or JSON to stdout with source metadata
         Also generates binwalk-offsets.sh for backward compatibility

This script performs a binwalk scan of the firmware image to identify
embedded files, compression, and partition structure.

Arguments:
    firmware.img      Path to firmware file (optional, downloads default if not provided)
    --format FORMAT   Output format: 'toml' (default) or 'json'
"""

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

# Binwalk output format constants
# Example line: "586164    0x8F1B4    Device tree blob (DTB)"
BINWALK_HEX_OFFSET_INDEX = 1
BINWALK_DESCRIPTION_START_INDEX = 2
BINWALK_MIN_FIELDS = 3

# TOML formatting constants
TOML_MAX_COMMENT_LENGTH = 80
TOML_COMMENT_TRUNCATE_LENGTH = 77


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
class Component:
    """A component identified by binwalk."""

    offset: str  # Hex offset like "0x8F1B4"
    type: str  # Component type (first word of description)
    description: str  # Full description


@dataclass(slots=True)
class BinwalkAnalysis:
    """Results of binwalk firmware analysis."""

    firmware_file: str
    firmware_size: int
    squashfs_count: int = 0
    gzip_count: int = 0
    dtb_count: int = 0
    ext4_count: int = 0
    bootloader_fit_offset: str | None = None
    uboot_offset: str | None = None
    optee_offset: str | None = None
    kernel_fit_offset: str | None = None
    rootfs_cpio_offset: str | None = None
    squashfs_offset: str | None = None
    squashfs_size: int | None = None
    identified_components: list[Component] = field(default_factory=list)

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

            if key == "identified_components":
                # Convert components to dicts
                result[key] = [
                    {"offset": c.offset, "type": c.type, "description": c.description}
                    for c in value
                ]
            else:
                result[key] = value

                # Add source metadata if available
                if key in self._source:
                    result[f"{key}_source"] = self._source[key]
                if key in self._method:
                    result[f"{key}_method"] = self._method[key]

        return result


def run_binwalk(firmware: Path) -> str:
    """Run binwalk on firmware and return output."""
    try:
        result = subprocess.run(
            ["binwalk", str(firmware)],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout
    except FileNotFoundError:
        error("binwalk command not found")
        error("Please run this script within 'nix develop' shell")
        sys.exit(1)


def parse_binwalk_output(output: str) -> list[Component]:
    """Parse binwalk output into structured components."""
    components = []

    for line in output.splitlines():
        # Only process lines that start with a number (data lines)
        if not re.match(r"^\d+", line):
            continue

        # Split line into fields
        parts = line.split()
        if len(parts) < BINWALK_MIN_FIELDS:
            continue

        hex_offset = parts[BINWALK_HEX_OFFSET_INDEX]
        description = " ".join(parts[BINWALK_DESCRIPTION_START_INDEX:])
        component_type = parts[BINWALK_DESCRIPTION_START_INDEX]

        # Only include lines with valid hex offsets
        if not hex_offset.startswith("0x"):
            continue

        components.append(
            Component(offset=hex_offset, type=component_type, description=description)
        )

    return components


def _extract_offset_from_lines(
    lines: list[str], search_term: str, additional_term: str = ""
) -> str | None:
    """Extract hex offset from binwalk output lines matching search terms.

    Args:
        lines: Lines from binwalk output
        search_term: Primary search term (case-insensitive)
        additional_term: Optional additional term that must also be present

    Returns:
        Hex offset string (e.g. "0x8F1B4") or None if not found
    """
    for line in lines:
        line_lower = line.lower()
        if search_term.lower() not in line_lower:
            continue
        if additional_term and additional_term.lower() not in line_lower:
            continue

        parts = line.split()
        if len(parts) >= BINWALK_MIN_FIELDS:
            return parts[BINWALK_HEX_OFFSET_INDEX]

    return None


def analyze_firmware(firmware_path: str) -> BinwalkAnalysis:
    """Analyze firmware with binwalk and return structured results."""
    firmware = Path(firmware_path)

    if not firmware.exists():
        error(f"Firmware file not found: {firmware}")
        sys.exit(1)

    info(f"Analyzing: {firmware}")

    # Run binwalk
    section("Binwalk Signature Scan")
    binwalk_output = run_binwalk(firmware)

    # Get firmware size
    firmware_size = firmware.stat().st_size

    # Create analysis object
    analysis = BinwalkAnalysis(
        firmware_file=firmware.name,
        firmware_size=firmware_size,
    )

    analysis.add_metadata("firmware_file", "binwalk", "Path(firmware).name")
    analysis.add_metadata("firmware_size", "binwalk", "Path(firmware).stat().st_size")

    # Parse components
    analysis.identified_components = parse_binwalk_output(binwalk_output)

    # Count component types (case-insensitive)
    analysis.squashfs_count = sum(
        1 for line in binwalk_output.lower().splitlines() if "squashfs" in line
    )
    analysis.gzip_count = sum(1 for line in binwalk_output.lower().splitlines() if "gzip" in line)
    analysis.dtb_count = sum(
        1
        for line in binwalk_output.lower().splitlines()
        if "device tree" in line or "dtb" in line or "flattened" in line
    )
    analysis.ext4_count = sum(
        1 for line in binwalk_output.lower().splitlines() if re.search(r"ext.*filesystem", line)
    )

    analysis.add_metadata("squashfs_count", "binwalk", "count lines matching 'squashfs'")
    analysis.add_metadata("gzip_count", "binwalk", "count lines matching 'gzip'")
    analysis.add_metadata(
        "dtb_count", "binwalk", "count lines matching 'device tree|dtb|flattened'"
    )
    analysis.add_metadata("ext4_count", "binwalk", "count lines matching 'ext.*filesystem'")

    # Extract key offsets using helper function
    lines = binwalk_output.splitlines()

    # Bootloader FIT (first device tree blob)
    if offset := _extract_offset_from_lines(lines, "device tree blob"):
        analysis.bootloader_fit_offset = offset
        analysis.add_metadata(
            "bootloader_fit_offset", "binwalk", "first line matching 'device tree blob'"
        )

    # U-Boot offset
    if offset := _extract_offset_from_lines(lines, "u-boot-nodtb.bin"):
        analysis.uboot_offset = offset
        analysis.add_metadata("uboot_offset", "binwalk", "first line matching 'u-boot-nodtb.bin'")

    # OP-TEE offset
    if offset := _extract_offset_from_lines(lines, "tee.bin"):
        analysis.optee_offset = offset
        analysis.add_metadata("optee_offset", "binwalk", "first line matching 'tee.bin'")

    # Kernel FIT offset (device tree blob with 96558 bytes)
    if offset := _extract_offset_from_lines(lines, "device tree blob", "96558 bytes"):
        analysis.kernel_fit_offset = offset
        analysis.add_metadata(
            "kernel_fit_offset", "binwalk", "first DTB line matching '96558 bytes'"
        )

    # Rootfs CPIO offset
    if offset := _extract_offset_from_lines(lines, "rootfs.cpio"):
        analysis.rootfs_cpio_offset = offset
        analysis.add_metadata("rootfs_cpio_offset", "binwalk", "first line matching 'rootfs.cpio'")

    # SquashFS offset and size
    if offset := _extract_offset_from_lines(lines, "squashfs"):
        analysis.squashfs_offset = offset
        analysis.add_metadata("squashfs_offset", "binwalk", "first line matching 'squashfs'")

        # Try to extract image size from the squashfs line
        for line in lines:
            if "squashfs" in line.lower():
                if match := re.search(r"image size:\s*(\d+)", line):
                    analysis.squashfs_size = int(match.group(1))
                    analysis.add_metadata(
                        "squashfs_size",
                        "binwalk",
                        "regex match 'image size: (\\d+)' in squashfs line",
                    )
                break

    return analysis


def write_legacy_offsets_file(analysis: BinwalkAnalysis, output_dir: Path) -> None:
    """Write binwalk-offsets.sh for backward compatibility."""
    offsets_file = output_dir / "binwalk-offsets.sh"
    output_dir.mkdir(parents=True, exist_ok=True)

    with offsets_file.open("w") as f:
        f.write("# Firmware offsets extracted from binwalk analysis\n")
        f.write(f"# Generated: {datetime.now(UTC).isoformat()}\n")
        f.write(f"# Source: {analysis.firmware_file}\n")
        f.write("#\n")
        f.write("# These values are parsed from binwalk output and should be used\n")
        f.write("# by other analysis scripts instead of hardcoding offsets.\n")
        f.write("\n")

        def write_offset(name: str, hex_offset: str | None, comment: str) -> None:
            """Write offset variable to shell script with hex and decimal values."""
            if hex_offset:
                dec_offset = int(hex_offset, 16)
                f.write(f"# {comment}\n")
                f.write(f"{name}_OFFSET={hex_offset}\n")
                f.write(f"{name}_OFFSET_DEC={dec_offset}\n")
                f.write("\n")

        write_offset(
            "BOOTLOADER_FIT",
            analysis.bootloader_fit_offset,
            "Bootloader FIT image (contains U-Boot + OP-TEE)",
        )
        write_offset("UBOOT_GZ", analysis.uboot_offset, "U-Boot binary (gzip compressed)")
        write_offset("OPTEE_GZ", analysis.optee_offset, "OP-TEE binary (gzip compressed)")
        write_offset(
            "KERNEL_FIT",
            analysis.kernel_fit_offset,
            "Kernel FIT image (contains kernel + DTB)",
        )
        write_offset("ROOTFS_CPIO", analysis.rootfs_cpio_offset, "Root filesystem CPIO archive")

        if analysis.squashfs_offset:
            dec_offset = int(analysis.squashfs_offset, 16)
            f.write("# SquashFS filesystem (main rootfs)\n")
            f.write(f"SQUASHFS_OFFSET={analysis.squashfs_offset}\n")
            f.write(f"SQUASHFS_OFFSET_DEC={dec_offset}\n")
            if analysis.squashfs_size:
                f.write(f"SQUASHFS_SIZE={analysis.squashfs_size}\n")
            f.write("\n")

    success("Wrote binwalk-offsets.sh (firmware offset artifacts)")


def output_toml(analysis: BinwalkAnalysis) -> str:
    """Convert analysis to TOML format.

    Args:
        analysis: BinwalkAnalysis object

    Returns:
        TOML string with source metadata as comments
    """
    doc = tomlkit.document()

    # Add firmware metadata
    doc.add(tomlkit.comment("Binwalk firmware analysis"))
    doc.add(tomlkit.comment(f"Generated: {datetime.now(UTC).isoformat()}"))
    doc.add(tomlkit.nl())

    # Convert analysis to dict
    data = analysis.to_dict()

    # Add fields to TOML, with source metadata as comments
    for key, value in data.items():
        # Skip source/method metadata fields (we'll add them as comments)
        if key.endswith("_source") or key.endswith("_method"):
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
        description="Analyze firmware structure using binwalk",
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
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    output_dir = project_root / "output"
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

    # Analyze firmware
    analysis = analyze_firmware(firmware_path)

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

    # Generate legacy offsets file
    section("Extracting firmware offsets")
    write_legacy_offsets_file(analysis, output_dir)


if __name__ == "__main__":
    main()
