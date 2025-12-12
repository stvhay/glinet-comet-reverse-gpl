#!/usr/bin/env python3
"""Analyze secure boot configuration in firmware.

Usage: ./scripts/analyze_secure_boot.py [firmware.img] [--format FORMAT]

Outputs: TOML (default) or JSON to stdout with source metadata

This script extracts and analyzes secure boot related information from the firmware,
including FIT image signatures, U-Boot verification strings, OP-TEE secure boot flags,
and device tree OTP/crypto configuration.

Arguments:
    firmware.img      Path to firmware file (optional, downloads default if not provided)
    --format FORMAT   Output format: 'toml' (default) or 'json'
"""

from __future__ import annotations

import argparse
import gzip
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lib.analysis_base import AnalysisBase
from lib.firmware import get_firmware_path
from lib.logging import error, info, section, success
from lib.output import output_json, output_toml

# String extraction constants
MIN_STRING_LENGTH = 4
ASCII_PRINTABLE_MIN = 32
ASCII_PRINTABLE_MAX = 126


@dataclass(frozen=True, slots=True)
class FITSignature:
    """FIT image signature information."""

    image_type: str  # "bootloader" or "kernel"
    algorithm: str  # RSA signature algorithm (e.g., "sha256,rsa2048")
    key_name: str  # Key name hint
    signed_components: str  # Components that are signed (e.g., "firmware,fdt")


@dataclass(slots=True)
class SecureBootAnalysis(AnalysisBase):
    """Results of secure boot analysis."""

    firmware_file: str
    firmware_size: int
    bootloader_fit_offset: str | None = None
    kernel_fit_offset: str | None = None
    uboot_offset: str | None = None
    optee_offset: str | None = None

    # FIT image signatures
    bootloader_signature: FITSignature | None = None
    kernel_signature: FITSignature | None = None

    # U-Boot verification strings
    uboot_verification_strings: list[str] = field(default_factory=list)
    uboot_key_findings: list[str] = field(default_factory=list)

    # OP-TEE secure boot strings
    optee_secure_boot_strings: list[str] = field(default_factory=list)

    # Device tree info
    has_otp_node: bool = False
    has_crypto_node: bool = False
    otp_node_content: str | None = None
    crypto_node_content: str | None = None

    # Source metadata for each field
    _source: dict[str, str] = field(default_factory=dict)
    _method: dict[str, str] = field(default_factory=dict)

    def _convert_complex_field(self, key: str, value: Any) -> tuple[bool, Any]:
        """Convert complex fields to serializable format."""
        if key in ("bootloader_signature", "kernel_signature") and value is not None:
            return True, {
                "image_type": value.image_type,
                "algorithm": value.algorithm,
                "key_name": value.key_name,
                "signed_components": value.signed_components,
            }
        return False, None


def load_offsets(output_dir: Path) -> dict[str, str | int]:
    """Load firmware offsets from binwalk-offsets.sh.

    Args:
        output_dir: Directory containing binwalk-offsets.sh

    Returns:
        Dictionary with offset values (both hex strings and decimal ints)

    Raises:
        FileNotFoundError: If offsets file doesn't exist
    """
    offsets_file = output_dir / "binwalk-offsets.sh"
    if not offsets_file.exists():
        error(f"Firmware offsets not found: {offsets_file}")
        error("Run analyze_binwalk.py first to generate offset artifacts")
        raise FileNotFoundError(offsets_file)

    offsets = {}
    with offsets_file.open() as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                # Try to parse as int for _DEC variables
                if key.endswith("_DEC"):
                    offsets[key] = int(value)
                else:
                    offsets[key] = value

    info("Loaded firmware offsets from binwalk analysis")
    return offsets


def extract_firmware(firmware: Path, work_dir: Path) -> Path:
    """Extract firmware using binwalk.

    Args:
        firmware: Path to firmware file
        work_dir: Work directory for extractions

    Returns:
        Path to extracted directory
    """
    extract_base = work_dir / "extractions"
    extract_dir = extract_base / f"{firmware.name}.extracted"

    extract_base.mkdir(parents=True, exist_ok=True)

    if not extract_dir.exists():
        info("Extracting firmware with binwalk...")
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

    return extract_dir


def find_dtb_file(extract_dir: Path, offset_hex: str) -> Path | None:
    """Find DTB file in extracted directory based on offset.

    Args:
        extract_dir: Extracted firmware directory
        offset_hex: Hex offset (e.g., "0x8F1B4")

    Returns:
        Path to system.dtb file or None if not found
    """
    # Convert offset to uppercase hex without 0x prefix (binwalk directory naming)
    offset_int = int(offset_hex, 16)
    offset_upper = f"{offset_int:X}"

    dtb_path = extract_dir / offset_upper / "system.dtb"
    if dtb_path.exists():
        return dtb_path

    # Also try with 0x prefix
    dtb_path_alt = extract_dir / offset_hex.upper() / "system.dtb"
    if dtb_path_alt.exists():
        return dtb_path_alt

    return None


def find_largest_dtb(extract_dir: Path) -> Path | None:
    """Find the largest system.dtb file (full device tree).

    Args:
        extract_dir: Extracted firmware directory

    Returns:
        Path to largest system.dtb or None if not found
    """
    dtb_files = list(extract_dir.glob("*/system.dtb"))
    if not dtb_files:
        return None

    # Return the largest file
    return max(dtb_files, key=lambda p: p.stat().st_size)


def extract_fit_signature(dtb_file: Path, image_type: str) -> FITSignature | None:
    """Extract signature information from FIT image DTB.

    Args:
        dtb_file: Path to system.dtb file
        image_type: "bootloader" or "kernel"

    Returns:
        FITSignature object or None if no signature found
    """
    if not dtb_file.exists():
        return None

    content = dtb_file.read_text(errors="ignore")

    # Extract algorithm (look for RSA algorithm)
    algo_match = re.search(r'algo = "([^"]+rsa[^"]*)"', content, re.IGNORECASE)
    algorithm = algo_match.group(1) if algo_match else "unknown"

    # Extract key name
    key_match = re.search(r'key-name-hint = "([^"]+)"', content)
    key_name = key_match.group(1) if key_match else "unknown"

    # Extract signed components
    signed_match = re.search(r'sign-images = "([^"]+)"', content)
    signed_components = signed_match.group(1) if signed_match else "unknown"

    # Only return if we found at least one piece of info
    if algorithm != "unknown" or key_name != "unknown" or signed_components != "unknown":
        return FITSignature(
            image_type=image_type,
            algorithm=algorithm,
            key_name=key_name,
            signed_components=signed_components,
        )

    return None


def extract_gzip_strings(firmware: Path, offset_dec: int, max_bytes: int) -> list[str]:
    """Extract strings from gzip-compressed data in firmware.

    Args:
        firmware: Path to firmware file
        offset_dec: Decimal offset to start reading
        max_bytes: Maximum bytes to read

    Returns:
        List of strings found in decompressed data
    """
    try:
        # Read compressed data
        with firmware.open("rb") as f:
            f.seek(offset_dec)
            compressed_data = f.read(max_bytes)

        # Decompress
        decompressed = gzip.decompress(compressed_data)

        # Extract strings (printable ASCII, min length MIN_STRING_LENGTH)
        strings = []
        current = []
        for byte in decompressed:
            if ASCII_PRINTABLE_MIN <= byte <= ASCII_PRINTABLE_MAX:  # Printable ASCII
                current.append(chr(byte))
            elif current:
                if len(current) >= MIN_STRING_LENGTH:
                    strings.append("".join(current))
                current = []

        # Don't forget last string
        if current and len(current) >= MIN_STRING_LENGTH:
            strings.append("".join(current))

        return strings
    except (OSError, gzip.BadGzipFile):
        return []


def filter_strings(strings: list[str], patterns: list[str]) -> list[str]:
    """Filter strings by multiple regex patterns.

    Args:
        strings: List of strings to filter
        patterns: List of regex patterns (ORed together)

    Returns:
        Sorted unique list of matching strings
    """
    if not patterns:
        return []

    # Combine patterns with OR
    combined_pattern = "|".join(f"({p})" for p in patterns)
    regex = re.compile(combined_pattern, re.IGNORECASE)

    matches = [s for s in strings if regex.search(s)]
    return sorted(set(matches))


def extract_device_tree_node(
    dtb_file: Path, node_pattern: str, lines_after: int = 10
) -> str | None:
    """Extract device tree node content.

    Args:
        dtb_file: Path to DTB file
        node_pattern: Regex pattern to match node (e.g., "otp@")
        lines_after: Number of lines to extract after match

    Returns:
        Node content or None if not found
    """
    if not dtb_file.exists():
        return None

    content = dtb_file.read_text(errors="ignore")
    lines = content.splitlines()

    for i, line in enumerate(lines):
        if re.search(node_pattern, line):
            # Extract this line and N lines after
            end_idx = min(i + lines_after + 1, len(lines))
            return "\n".join(lines[i:end_idx])

    return None


def analyze_secure_boot(  # noqa: PLR0912, PLR0915
    firmware_path: str, output_dir: Path, work_dir: Path
) -> SecureBootAnalysis:
    """Analyze secure boot configuration in firmware.

    Args:
        firmware_path: Path to firmware file
        output_dir: Output directory (for reading offsets)
        work_dir: Work directory for extractions

    Returns:
        SecureBootAnalysis object with all findings
    """
    firmware = Path(firmware_path)

    if not firmware.exists():
        error(f"Firmware file not found: {firmware}")
        sys.exit(1)

    info(f"Analyzing secure boot in: {firmware}")

    # Load offsets from binwalk analysis
    offsets = load_offsets(output_dir)

    # Create analysis object
    analysis = SecureBootAnalysis(
        firmware_file=firmware.name,
        firmware_size=firmware.stat().st_size,
    )

    analysis.add_metadata("firmware_file", "secure_boot", "Path(firmware).name")
    analysis.add_metadata("firmware_size", "secure_boot", "Path(firmware).stat().st_size")

    # Set offsets from binwalk
    if bootloader_offset := offsets.get("BOOTLOADER_FIT_OFFSET"):
        analysis.bootloader_fit_offset = str(bootloader_offset)
        analysis.add_metadata(
            "bootloader_fit_offset",
            "binwalk",
            "loaded from binwalk-offsets.sh BOOTLOADER_FIT_OFFSET",
        )

    if kernel_offset := offsets.get("KERNEL_FIT_OFFSET"):
        analysis.kernel_fit_offset = str(kernel_offset)
        analysis.add_metadata(
            "kernel_fit_offset",
            "binwalk",
            "loaded from binwalk-offsets.sh KERNEL_FIT_OFFSET",
        )

    if uboot_offset := offsets.get("UBOOT_GZ_OFFSET"):
        analysis.uboot_offset = str(uboot_offset)
        analysis.add_metadata(
            "uboot_offset", "binwalk", "loaded from binwalk-offsets.sh UBOOT_GZ_OFFSET"
        )

    if optee_offset := offsets.get("OPTEE_GZ_OFFSET"):
        analysis.optee_offset = str(optee_offset)
        analysis.add_metadata(
            "optee_offset", "binwalk", "loaded from binwalk-offsets.sh OPTEE_GZ_OFFSET"
        )

    # Extract firmware
    section("Extracting firmware")
    extract_dir = extract_firmware(firmware, work_dir)

    # Analyze FIT signatures
    section("Analyzing FIT signatures")

    if analysis.bootloader_fit_offset and (
        bootloader_dtb := find_dtb_file(extract_dir, analysis.bootloader_fit_offset)
    ):
        analysis.bootloader_signature = extract_fit_signature(bootloader_dtb, "bootloader")
        if analysis.bootloader_signature:
            analysis.add_metadata(
                "bootloader_signature",
                "fit_dtb",
                f"extracted from {bootloader_dtb.relative_to(extract_dir)} using regex",
            )

    if analysis.kernel_fit_offset and (
        kernel_dtb := find_dtb_file(extract_dir, analysis.kernel_fit_offset)
    ):
        analysis.kernel_signature = extract_fit_signature(kernel_dtb, "kernel")
        if analysis.kernel_signature:
            analysis.add_metadata(
                "kernel_signature",
                "fit_dtb",
                f"extracted from {kernel_dtb.relative_to(extract_dir)} using regex",
            )

    # Analyze U-Boot strings
    section("Analyzing U-Boot verification strings")

    if uboot_offset_dec := offsets.get("UBOOT_GZ_OFFSET_DEC"):
        uboot_strings = extract_gzip_strings(firmware, uboot_offset_dec, 500000)

        # Filter for verification-related strings
        verification_patterns = [
            r"verified",
            r"signature",
            r"secure.?boot",
            r"FIT.*sign",
            r"required",
            r"rsa.*verify",
        ]
        analysis.uboot_verification_strings = filter_strings(uboot_strings, verification_patterns)[
            :30
        ]

        if analysis.uboot_verification_strings:
            analysis.add_metadata(
                "uboot_verification_strings",
                "strings",
                (
                    "gunzip U-Boot | strings | grep -E "
                    "'verified|signature|secure.?boot|FIT.*sign|required|rsa.*verify'"
                ),
            )

        # Key findings
        key_patterns = [
            r"FIT:.*signed",
            r"Verified-boot:",
            r"Can't read verified-boot",
            r"CONFIG_FIT_SIGNATURE",
        ]
        analysis.uboot_key_findings = filter_strings(uboot_strings, key_patterns)

        if analysis.uboot_key_findings:
            analysis.add_metadata(
                "uboot_key_findings",
                "strings",
                (
                    "gunzip U-Boot | strings | grep -E "
                    "'FIT:.*signed|Verified-boot:|Can't read verified-boot|CONFIG_FIT_SIGNATURE'"
                ),
            )

    # Analyze OP-TEE strings
    section("Analyzing OP-TEE secure boot strings")

    if optee_offset_dec := offsets.get("OPTEE_GZ_OFFSET_DEC"):
        optee_strings = extract_gzip_strings(firmware, optee_offset_dec, 300000)

        # Filter for secure boot related strings
        secure_boot_patterns = [
            r"secure.?boot",
            r"otp.*key",
            r"set.*flag",
            r"key.*index",
            r"enable.*flag",
        ]
        analysis.optee_secure_boot_strings = filter_strings(optee_strings, secure_boot_patterns)[
            :30
        ]

        if analysis.optee_secure_boot_strings:
            analysis.add_metadata(
                "optee_secure_boot_strings",
                "strings",
                (
                    "gunzip OP-TEE | strings | grep -E "
                    "'secure.?boot|otp.*key|set.*flag|key.*index|enable.*flag'"
                ),
            )

    # Analyze device tree
    section("Analyzing device tree OTP/crypto nodes")

    if largest_dtb := find_largest_dtb(extract_dir):
        # Check for OTP node
        if otp_content := extract_device_tree_node(largest_dtb, r"otp@", 20):
            analysis.has_otp_node = True
            analysis.otp_node_content = otp_content
            analysis.add_metadata(
                "has_otp_node",
                "device_tree",
                f"grep 'otp@' in {largest_dtb.relative_to(extract_dir)}",
            )
            analysis.add_metadata(
                "otp_node_content",
                "device_tree",
                f"extracted 20 lines after 'otp@' match in {largest_dtb.relative_to(extract_dir)}",
            )

        # Check for crypto node
        if crypto_content := extract_device_tree_node(largest_dtb, r"crypto@", 20):
            analysis.has_crypto_node = True
            analysis.crypto_node_content = crypto_content
            analysis.add_metadata(
                "has_crypto_node",
                "device_tree",
                f"grep 'crypto@' in {largest_dtb.relative_to(extract_dir)}",
            )
            analysis.add_metadata(
                "crypto_node_content",
                "device_tree",
                (
                    f"extracted 20 lines after 'crypto@' match in "
                    f"{largest_dtb.relative_to(extract_dir)}"
                ),
            )

    return analysis


# Field order for TOML output
SIMPLE_FIELDS = [
    "firmware_file",
    "firmware_size",
    "bootloader_fit_offset",
    "kernel_fit_offset",
    "uboot_offset",
    "optee_offset",
    "has_otp_node",
    "has_crypto_node",
    "otp_node_content",
    "crypto_node_content",
]

COMPLEX_FIELDS = [
    "bootloader_signature",
    "kernel_signature",
    "uboot_verification_strings",
    "uboot_key_findings",
    "optee_secure_boot_strings",
]


def main() -> None:
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Analyze secure boot configuration in firmware",
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
    firmware = get_firmware_path(args.firmware, work_dir)
    firmware_path = str(firmware)

    # Analyze secure boot
    analysis = analyze_secure_boot(firmware_path, output_dir, work_dir)

    # Output in requested format
    if args.format == "json":
        print(output_json(analysis))
    else:  # toml
        print(
            output_toml(
                analysis,
                title="Secure Boot Analysis",
                simple_fields=SIMPLE_FIELDS,
                complex_fields=COMPLEX_FIELDS,
            )
        )

    success("Secure boot analysis complete")


if __name__ == "__main__":
    main()
