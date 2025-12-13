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

import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from lib.analysis_base import AnalysisBase
from lib.base_script import AnalysisScript
from lib.extraction import extract_gzip_at_offset, extract_strings
from lib.logging import error, info, section, success, warn
from lib.offsets import OffsetManager

# U-Boot extraction constants
UBOOT_EXTRACT_SIZE = 500000  # Read 500KB to capture full gzip stream

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


# extract_gzip_at_offset and extract_strings_from_data are now imported from lib.extraction


def analyze_uboot(firmware_path: str, output_dir: Path) -> UBootAnalysis:  # noqa: PLR0912, PLR0915
    """Analyze U-Boot bootloader in firmware and return structured results."""
    firmware = Path(firmware_path)

    # Create analysis object
    analysis = UBootAnalysis(
        firmware_file=firmware.name,
        firmware_size=firmware.stat().st_size,
    )
    analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")
    analysis.add_metadata("firmware_size", "filesystem", "Path(firmware).stat().st_size")

    # Load offsets from binwalk analysis
    offset_manager = OffsetManager(output_dir)
    try:
        offset_manager.load_from_shell_script()
    except FileNotFoundError:
        warn("Firmware offsets not found: binwalk-offsets.sh")
        warn("Run analyze_binwalk.py first to generate offset artifacts")

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
    offset_dec = offset_manager.get_dec("UBOOT_GZ")
    if not analysis.version and offset_dec is not None:
        offset_hex = offset_manager.get_hex("UBOOT_GZ") or hex(offset_dec)

        info(f"Attempting to extract U-Boot from gzip at offset {offset_hex}")

        # Extract and decompress
        decompressed_data = extract_gzip_at_offset(firmware, offset_dec, UBOOT_EXTRACT_SIZE)

        if decompressed_data:
            uboot_strings = extract_strings(decompressed_data)

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


class UBootScript(AnalysisScript):
    """U-Boot analysis script."""

    def __init__(self):
        """Initialize U-Boot analysis script."""
        super().__init__(
            description="Analyze U-Boot bootloader information from firmware",
            title="U-Boot bootloader analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )

    def analyze(self, firmware_path: str) -> AnalysisBase:
        """Run U-Boot analysis on firmware.

        Args:
            firmware_path: Path to firmware file

        Returns:
            UBootAnalysis results
        """
        return analyze_uboot(firmware_path, self.output_dir)

    def post_process(self, analysis: AnalysisBase) -> None:
        """Generate legacy markdown file.

        Args:
            analysis: Completed U-Boot analysis
        """
        if isinstance(analysis, UBootAnalysis):
            write_legacy_markdown(analysis, self.output_dir)


if __name__ == "__main__":
    UBootScript().run()
