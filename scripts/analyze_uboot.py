#!/usr/bin/env python3
"""Analyze U-Boot bootloader information from firmware.

Usage: ./scripts/analyze_uboot.py [firmware.img] [--format FORMAT]

Outputs: TOML (default) or JSON to stdout with source metadata
         Also generates uboot-version.md for backward compatibility

This script extracts:
- U-Boot version string
- Build information
- Environment variables (if accessible)
- Boot commands
- Copyright/license information

Arguments:
    firmware.img      Path to firmware file (optional, downloads default if not provided)
    --format FORMAT   Output format: 'toml' (default) or 'json'
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from lib.analysis_base import AnalysisBase
from lib.logging import error, info, section, success, warn
from lib.output import output_json, output_toml

# U-Boot extraction constants
UBOOT_EXTRACT_SIZE = 500000  # Read 500KB to capture full gzip stream

# String extraction constants
MIN_STRING_LENGTH = 4  # Minimum length for extracted strings (matching GNU strings default)
ASCII_PRINTABLE_START = 32  # Space character
ASCII_PRINTABLE_END = 126  # Tilde character

# Field lists for TOML output
SIMPLE_FIELDS = [
    "firmware_file",
    "firmware_size",
    "version",
    "build_date",
    "extraction_method",
    "extraction_offset",
]
COMPLEX_FIELDS = [
    "boot_commands",
    "environment_variables",
    "supported_commands",
    "copyright_license",
]


@dataclass(slots=True)
class UBootAnalysis(AnalysisBase):
    """Results of U-Boot bootloader analysis."""

    firmware_file: str
    firmware_size: int
    version: str | None = None
    build_date: str | None = None
    boot_commands: list[str] = field(default_factory=list)
    environment_variables: list[str] = field(default_factory=list)
    supported_commands: list[str] = field(default_factory=list)
    copyright_license: list[str] = field(default_factory=list)
    extraction_method: str | None = None
    extraction_offset: str | None = None

    # Source metadata for each field
    _source: dict[str, str] = field(default_factory=dict)
    _method: dict[str, str] = field(default_factory=dict)


def run_strings(firmware: Path) -> str:
    """Run strings on firmware and return output."""
    try:
        result = subprocess.run(
            ["strings", str(firmware)],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout
    except FileNotFoundError:
        error("strings command not found")
        error("Please run this script within 'nix develop' shell")
        sys.exit(1)


def extract_gzip_at_offset(firmware: Path, offset: int, size: int) -> bytes | None:
    """Extract and decompress gzip data at a specific offset.

    Uses dd and gunzip like the bash script to handle embedded gzip properly.
    """
    try:
        # Use dd to extract data at offset, pipe to gunzip
        # This matches the bash script's approach which handles embedded gzip correctly
        dd_cmd = [
            "dd",
            f"if={firmware}",
            "bs=1",
            f"skip={offset}",
            f"count={size}",
        ]

        gunzip_cmd = ["gunzip"]

        # Run dd | gunzip pipeline
        dd_proc = subprocess.Popen(
            dd_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        gunzip_proc = subprocess.Popen(
            gunzip_cmd,
            stdin=dd_proc.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        # Close dd's stdout to allow it to receive SIGPIPE if gunzip exits
        if dd_proc.stdout:
            dd_proc.stdout.close()

        # Get decompressed output
        decompressed_data, _ = gunzip_proc.communicate()

        # Wait for both processes
        dd_proc.wait()

        return decompressed_data if decompressed_data else None

    except Exception as e:
        warn(f"Failed to decompress gzip at offset {hex(offset)}: {e}")
        return None


def extract_strings_from_data(data: bytes) -> list[str]:
    """Extract printable strings from binary data."""
    # Use strings command behavior: minimum length, printable ASCII
    result = []
    current = []

    for byte in data:
        if ASCII_PRINTABLE_START <= byte <= ASCII_PRINTABLE_END:
            current.append(chr(byte))
        else:
            if len(current) >= MIN_STRING_LENGTH:
                result.append("".join(current))
            current = []

    # Don't forget the last string
    if len(current) >= MIN_STRING_LENGTH:
        result.append("".join(current))

    return result


def load_binwalk_offsets(output_dir: Path) -> dict[str, int]:
    """Load firmware offsets from binwalk-offsets.sh."""
    offsets_file = output_dir / "binwalk-offsets.sh"

    if not offsets_file.exists():
        warn("Firmware offsets not found: binwalk-offsets.sh")
        warn("Run analyze_binwalk.py first to generate offset artifacts")
        return {}

    offsets = {}
    with offsets_file.open("r") as f:
        for line in f:
            # Parse lines like: UBOOT_GZ_OFFSET_DEC=123456
            if match := re.match(r"^([A-Z_]+)_OFFSET_DEC=(\d+)", line):
                name = match.group(1)
                value = int(match.group(2))
                offsets[name] = value
            # Also parse hex offsets like: UBOOT_GZ_OFFSET=0x1E240
            elif match := re.match(r"^([A-Z_]+)_OFFSET=(0x[0-9A-Fa-f]+)", line):
                name = match.group(1)
                value_hex = match.group(2)
                offsets[f"{name}_HEX"] = value_hex

    return offsets


def analyze_uboot(firmware_path: str) -> UBootAnalysis:  # noqa: PLR0912, PLR0915
    """Analyze U-Boot bootloader in firmware and return structured results."""
    firmware = Path(firmware_path)

    if not firmware.exists():
        error(f"Firmware file not found: {firmware}")
        sys.exit(1)

    info(f"Analyzing U-Boot in: {firmware}")

    # Get firmware size
    firmware_size = firmware.stat().st_size

    # Create analysis object
    analysis = UBootAnalysis(
        firmware_file=firmware.name,
        firmware_size=firmware_size,
    )

    analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")
    analysis.add_metadata("firmware_size", "filesystem", "Path(firmware).stat().st_size")

    # Determine paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    output_dir = project_root / "output"

    # Load offsets from binwalk analysis
    offsets = load_binwalk_offsets(output_dir)

    section("Extracting U-Boot version")

    # Method 1: Search firmware directly for U-Boot strings
    uboot_strings = []
    firmware_strings = run_strings(firmware)

    # Look for U-Boot version in firmware strings
    for line in firmware_strings.splitlines():
        if re.search(r"U-Boot [0-9]+\.[0-9]+", line):
            analysis.version = line.strip()
            analysis.add_metadata(
                "version", "strings", "strings firmware.img | grep 'U-Boot [0-9]'"
            )
            analysis.extraction_method = "direct_strings"
            analysis.add_metadata(
                "extraction_method", "strings", "strings command on firmware image"
            )
            break

    # Method 2: Try extracting from gzip-compressed U-Boot binary
    if not analysis.version and "UBOOT_GZ" in offsets:
        offset_dec = offsets["UBOOT_GZ"]
        offset_hex = offsets.get("UBOOT_GZ_HEX", hex(offset_dec))

        info(f"Attempting to extract U-Boot from gzip at offset {offset_hex}")

        # Extract and decompress
        decompressed_data = extract_gzip_at_offset(firmware, offset_dec, UBOOT_EXTRACT_SIZE)

        if decompressed_data:
            uboot_strings = extract_strings_from_data(decompressed_data)

            # Find version string
            for string in uboot_strings:
                if re.search(r"U-Boot [0-9]+\.[0-9]+", string):
                    analysis.version = string.strip()
                    analysis.add_metadata(
                        "version",
                        "gzip_extraction",
                        f"gunzip data at offset {offset_hex} | strings",
                    )
                    break

            # Find build date
            for string in uboot_strings:
                if re.match(r"^\([A-Za-z]+ [A-Za-z]+ [0-9]+", string):
                    analysis.build_date = string.strip()
                    analysis.add_metadata(
                        "build_date",
                        "gzip_extraction",
                        f"gunzip data at offset {offset_hex} | strings | grep build date pattern",
                    )
                    break

            analysis.extraction_method = "gzip_decompression"
            analysis.extraction_offset = offset_hex
            analysis.add_metadata(
                "extraction_method",
                "binwalk",
                f"gzip decompression at offset {offset_hex}",
            )
            analysis.add_metadata("extraction_offset", "binwalk", "UBOOT_GZ_OFFSET")

    # Parse detailed information from U-Boot strings
    if uboot_strings:
        section("Extracting U-Boot configuration")

        # Extract boot commands
        boot_commands = [s for s in uboot_strings if re.match(r"^boot(cmd|args|delay)=", s)]
        if boot_commands:
            analysis.boot_commands = boot_commands[:10]  # Limit to first 10
            analysis.add_metadata(
                "boot_commands",
                "gzip_extraction",
                "strings matching '^boot(cmd|args|delay)='",
            )

        # Extract environment variables (excluding boot commands)
        env_vars = [
            s for s in uboot_strings if re.match(r"^[a-z_]+=", s) and not s.startswith("boot")
        ]
        if env_vars:
            analysis.environment_variables = env_vars[:20]  # Limit to first 20
            analysis.add_metadata(
                "environment_variables",
                "gzip_extraction",
                "strings matching '^[a-z_]+=' excluding boot commands",
            )

        # Extract supported commands
        command_pattern = r"^(mmc|usb|tftp|nfs|dhcp|ping|md|mw|sf|nand)"
        commands = [s for s in uboot_strings if re.match(command_pattern, s)]
        if commands:
            # Remove duplicates and sort
            analysis.supported_commands = sorted(set(commands))[:20]  # Limit to first 20
            analysis.add_metadata(
                "supported_commands",
                "gzip_extraction",
                f"strings matching '{command_pattern}' | sort -u",
            )

        # Extract copyright/license information
        license_strings = [
            s for s in uboot_strings if re.search(r"copyright|license|GPL", s, re.IGNORECASE)
        ]
        if license_strings:
            analysis.copyright_license = license_strings[:10]  # Limit to first 10
            analysis.add_metadata(
                "copyright_license",
                "gzip_extraction",
                "strings matching 'copyright|license|GPL' (case-insensitive)",
            )

    if not analysis.version:
        warn("Could not extract U-Boot version")

    return analysis


def write_legacy_markdown(analysis: UBootAnalysis, output_dir: Path) -> None:  # noqa: PLR0912, PLR0915
    """Write uboot-version.md for backward compatibility."""
    markdown_file = output_dir / "uboot-version.md"
    output_dir.mkdir(parents=True, exist_ok=True)

    with markdown_file.open("w") as f:
        f.write("# U-Boot Bootloader Analysis\n")
        f.write("\n")
        f.write("**GL.iNet Comet (GL-RM1) Firmware**\n")
        f.write("\n")
        f.write(f"Generated: {datetime.now(UTC).isoformat()}\n")
        f.write("\n")
        f.write("U-Boot version and configuration extracted from firmware.\n")
        f.write("\n")

        f.write("## Version Information\n")
        f.write("\n")

        if analysis.version:
            f.write(f"- **Version:** `{analysis.version}`\n")
        else:
            f.write("- **Version:** Could not extract\n")

        if analysis.build_date:
            f.write(f"- **Build:** `{analysis.build_date}`\n")

        if analysis.extraction_method:
            f.write(f"- **Extraction Method:** {analysis.extraction_method}\n")

        if analysis.extraction_offset:
            f.write(f"- **Extraction Offset:** {analysis.extraction_offset}\n")

        f.write("\n")

        # U-Boot Strings Analysis
        f.write("## U-Boot Strings Analysis\n")
        f.write("\n")

        if analysis.boot_commands or analysis.environment_variables or analysis.supported_commands:
            if analysis.boot_commands:
                f.write("### Boot Commands\n")
                f.write("\n")
                f.write("```\n")
                for cmd in analysis.boot_commands:
                    f.write(f"{cmd}\n")
                f.write("```\n")
                f.write("\n")

            if analysis.environment_variables:
                f.write("### Environment Variables\n")
                f.write("\n")
                f.write("```\n")
                for var in analysis.environment_variables:
                    f.write(f"{var}\n")
                f.write("```\n")
                f.write("\n")

            if analysis.supported_commands:
                f.write("### Supported Commands\n")
                f.write("\n")
                f.write("```\n")
                for cmd in analysis.supported_commands:
                    f.write(f"{cmd}\n")
                f.write("```\n")
                f.write("\n")

            if analysis.copyright_license:
                f.write("### Copyright/License\n")
                f.write("\n")
                f.write("```\n")
                for line in analysis.copyright_license:
                    f.write(f"{line}\n")
                f.write("```\n")
        else:
            f.write("*Could not extract U-Boot binary for detailed analysis*\n")

    success("Wrote uboot-version.md")




def main() -> None:
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Analyze U-Boot bootloader information from firmware",
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

    # Analyze U-Boot
    analysis = analyze_uboot(firmware_path)

    # Output in requested format
    if args.format == "json":
        try:
            print(output_json(analysis))
        except ValueError as e:
            error(str(e))
            sys.exit(1)
    else:  # toml
        try:
            print(
                output_toml(
                    analysis, "U-Boot bootloader analysis", SIMPLE_FIELDS, COMPLEX_FIELDS
                )
            )
        except ValueError as e:
            error(str(e))
            sys.exit(1)

    # Generate legacy markdown file
    write_legacy_markdown(analysis, output_dir)


if __name__ == "__main__":
    main()
