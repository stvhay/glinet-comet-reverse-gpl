#!/usr/bin/env python3
"""Analyze boot process and partition layout.

Usage: ./scripts/analyze_boot_process.py [firmware.img] [--format FORMAT]

Outputs: TOML (default) or JSON to stdout with source metadata
         Also generates boot-process.md for backward compatibility

This script documents:
- Boot chain (BROM -> SPL -> OP-TEE -> U-Boot -> Kernel)
- Partition layout
- FIT image structure
- A/B slot configuration

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
from functools import cache
from pathlib import Path

import tomlkit

# Color codes for stderr logging
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
NC = "\033[0m"  # No Color

# Default firmware URL
DEFAULT_FIRMWARE_URL = "https://fw.gl-inet.com/kvm/rm1/release/glkvm-RM1-1.7.2-1128-1764344791.img"

# TOML formatting constants
TOML_MAX_COMMENT_LENGTH = 80
TOML_COMMENT_TRUNCATE_LENGTH = 77

# A/B redundancy detection threshold
MIN_FIT_IMAGES_FOR_AB = 2

# FIT info extraction limit
FIT_INFO_LINE_LIMIT = 30


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
class ComponentVersion:
    """Version information for a boot component."""

    component: str
    version: str
    source: str


@dataclass(frozen=True, slots=True)
class HardwareProperty:
    """Hardware platform property."""

    property: str
    value: str
    source: str


@dataclass(frozen=True, slots=True)
class BootComponent:
    """Boot chain component detection."""

    stage: str
    found: bool
    evidence: str


@dataclass(frozen=True, slots=True)
class Partition:
    """Partition/region information."""

    region: str
    offset: str
    size_mb: int
    type: str
    content: str


@dataclass(frozen=True, slots=True)
class ConsoleConfig:
    """Console configuration."""

    parameter: str
    value: str
    source: str


@dataclass(slots=True)
class BootProcessAnalysis:
    """Results of boot process analysis."""

    firmware_file: str
    firmware_size: int
    hardware_properties: list[HardwareProperty] = field(default_factory=list)
    boot_components: list[BootComponent] = field(default_factory=list)
    component_versions: list[ComponentVersion] = field(default_factory=list)
    partitions: list[Partition] = field(default_factory=list)
    bootloader_fit_info: str | None = None
    kernel_fit_info: str | None = None
    ab_redundancy: bool = False
    ab_evidence: str | None = None
    kernel_cmdline: str | None = None
    console_configs: list[ConsoleConfig] = field(default_factory=list)

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

            # Convert complex types to dicts
            if key == "hardware_properties":
                result[key] = [
                    {"property": p.property, "value": p.value, "source": p.source} for p in value
                ]
            elif key == "boot_components":
                result[key] = [
                    {"stage": c.stage, "found": c.found, "evidence": c.evidence} for c in value
                ]
            elif key == "component_versions":
                result[key] = [
                    {"component": v.component, "version": v.version, "source": v.source}
                    for v in value
                ]
            elif key == "partitions":
                result[key] = [
                    {
                        "region": p.region,
                        "offset": p.offset,
                        "size_mb": p.size_mb,
                        "type": p.type,
                        "content": p.content,
                    }
                    for p in value
                ]
            elif key == "console_configs":
                result[key] = [
                    {"parameter": c.parameter, "value": c.value, "source": c.source} for c in value
                ]
            else:
                result[key] = value

                # Add source metadata if available
                if key in self._source:
                    result[f"{key}_source"] = self._source[key]
                if key in self._method:
                    result[f"{key}_method"] = self._method[key]

        return result


def get_firmware_path(firmware_arg: str | None, work_dir: Path) -> Path:
    """Get firmware path, downloading if necessary."""
    if firmware_arg:
        firmware = Path(firmware_arg)
        if not firmware.exists():
            error(f"Firmware file not found: {firmware}")
            sys.exit(1)
        return firmware

    # Download default firmware
    firmware_url = DEFAULT_FIRMWARE_URL
    firmware_file = firmware_url.split("/")[-1]
    firmware_path = work_dir / firmware_file

    if not firmware_path.exists():
        info(f"Downloading firmware: {firmware_url}")
        work_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["curl", "-L", "-o", str(firmware_path), firmware_url], check=True)

    return firmware_path


def extract_firmware(firmware: Path, work_dir: Path) -> Path:
    """Extract firmware using binwalk."""
    extract_base = work_dir / "extractions"
    extract_dir = extract_base / f"{firmware.name}.extracted"

    if not extract_dir.exists():
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

    return extract_dir


def find_rootfs(extract_dir: Path) -> Path | None:
    """Find SquashFS rootfs in extractions."""
    # Look for squashfs-root directory
    for path in extract_dir.rglob("squashfs-root"):
        if path.is_dir():
            return path
    return None


def get_fit_info(dts_file: Path) -> str | None:
    """Extract FIT information from DTS file."""
    if dts_file.exists():
        try:
            return dts_file.read_text()
        except Exception:
            return None
    return None


@cache
def load_firmware_offsets(output_dir: Path) -> dict[str, str | int]:
    """Load firmware offsets from binwalk analysis artifact."""
    offsets_file = output_dir / "binwalk-offsets.sh"

    if not offsets_file.exists():
        error(f"Firmware offsets not found: {offsets_file}")
        error("Run analyze_binwalk.py first to generate offset artifacts")
        sys.exit(1)

    # Parse shell variable assignments
    offsets: dict[str, str | int] = {}
    content = offsets_file.read_text()

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if "=" in line:
            key, value = line.split("=", 1)
            # Remove quotes if present
            value = value.strip('"').strip("'")
            # Store as int if it looks like a decimal number
            if value.isdigit():
                offsets[key] = int(value)
            else:
                offsets[key] = value

    info("Loaded firmware offsets from binwalk analysis")
    return offsets


def analyze_boot_process(
    firmware: Path, extract_dir: Path, output_dir: Path
) -> BootProcessAnalysis:
    """Analyze boot process and partition layout."""
    section("Analyzing boot chain")

    # Load offsets from binwalk analysis
    offsets = load_firmware_offsets(output_dir)

    # Create analysis object
    analysis = BootProcessAnalysis(
        firmware_file=firmware.name,
        firmware_size=firmware.stat().st_size,
    )

    analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")
    analysis.add_metadata("firmware_size", "filesystem", "Path(firmware).stat().st_size")

    # Convert hex offsets to directory names (binwalk uses uppercase hex without 0x prefix)
    bootloader_offset_dec = offsets.get("BOOTLOADER_FIT_OFFSET_DEC")
    kernel_offset_dec = offsets.get("KERNEL_FIT_OFFSET_DEC")

    if bootloader_offset_dec and isinstance(bootloader_offset_dec, int):
        bootloader_dir = f"{bootloader_offset_dec:X}"
    else:
        bootloader_dir = None

    if kernel_offset_dec and isinstance(kernel_offset_dec, int):
        kernel_dir = f"{kernel_offset_dec:X}"
    else:
        kernel_dir = None

    # Get DTS files if available
    bootloader_dts = extract_dir / bootloader_dir / "system.dtb" if bootloader_dir else None
    kernel_dts = extract_dir / kernel_dir / "system.dtb" if kernel_dir else None

    # Extract FIT information
    if bootloader_dts:
        analysis.bootloader_fit_info = get_fit_info(bootloader_dts)
        if analysis.bootloader_fit_info:
            analysis.add_metadata(
                "bootloader_fit_info",
                "device-tree",
                f"read {bootloader_dts.relative_to(extract_dir)}",
            )

    if kernel_dts:
        analysis.kernel_fit_info = get_fit_info(kernel_dts)
        if analysis.kernel_fit_info:
            analysis.add_metadata(
                "kernel_fit_info", "device-tree", f"read {kernel_dts.relative_to(extract_dir)}"
            )

    # Analyze hardware properties
    kernel_full_dts = find_largest_dts(extract_dir)
    if kernel_full_dts:
        analyze_hardware_properties(kernel_full_dts, analysis, extract_dir)

    # Analyze boot components
    analyze_boot_components(firmware, extract_dir, offsets, analysis)

    # Analyze component versions
    analyze_component_versions(firmware, extract_dir, analysis)

    # Analyze partition layout
    analyze_partitions(offsets, analysis)

    # Analyze A/B redundancy
    analyze_ab_redundancy(extract_dir, analysis)

    # Analyze boot configuration
    if kernel_full_dts:
        analyze_boot_config(kernel_full_dts, analysis)

    return analysis


def find_largest_dts(extract_dir: Path) -> Path | None:
    """Find the largest DTS file which contains full device tree."""
    dts_files = list(extract_dir.rglob("system.dtb"))
    if not dts_files:
        return None

    # Return largest file
    return max(dts_files, key=lambda p: p.stat().st_size)


def analyze_hardware_properties(
    dts_file: Path, analysis: BootProcessAnalysis, extract_dir: Path
) -> None:
    """Extract hardware platform properties from device tree."""
    try:
        content = dts_file.read_text()

        # Extract compatible string
        if match := re.search(r'compatible = "([^"]+)"', content):
            compat = match.group(1)
            analysis.hardware_properties.append(
                HardwareProperty(
                    property="Device Tree Compatible", value=f"`{compat}`", source="DTS"
                )
            )

            # Derive SoC from compatible string
            if "rv1126" in compat:
                analysis.hardware_properties.append(
                    HardwareProperty(
                        property="SoC", value="Rockchip RV1126", source="DTS compatible"
                    )
                )

        # Derive architecture from ELF binaries in rootfs
        rootfs = find_rootfs(extract_dir)
        if rootfs:
            for elf_sample in rootfs.rglob("*"):
                if elf_sample.is_file() and elf_sample.stat().st_mode & 0o111:
                    try:
                        result = subprocess.run(
                            ["file", str(elf_sample)],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        if arch_match := re.search(r"(ARM|x86-64|aarch64)", result.stdout):
                            arch = arch_match.group(1)
                            analysis.hardware_properties.append(
                                HardwareProperty(
                                    property="Architecture", value=arch, source="ELF header"
                                )
                            )
                            break
                    except Exception:
                        continue
    except Exception:
        pass


def analyze_boot_components(
    firmware: Path,
    extract_dir: Path,
    offsets: dict[str, str | int],
    analysis: BootProcessAnalysis,
) -> None:
    """Analyze boot chain components."""
    # Check for OP-TEE
    tee_found = any(extract_dir.rglob("tee.bin"))
    analysis.boot_components.append(
        BootComponent(
            stage="OP-TEE",
            found=tee_found,
            evidence="tee.bin found in extraction" if tee_found else "tee.bin not found",
        )
    )

    # Check for U-Boot
    uboot_files = list(extract_dir.rglob("u-boot*"))
    if uboot_files:
        analysis.boot_components.append(
            BootComponent(
                stage="U-Boot",
                found=True,
                evidence="u-boot binary found in extraction",
            )
        )
    else:
        # Check firmware strings
        try:
            result = subprocess.run(
                ["strings", str(firmware)],
                capture_output=True,
                text=True,
                check=False,
            )
            uboot_in_strings = "U-Boot" in result.stdout
            analysis.boot_components.append(
                BootComponent(
                    stage="U-Boot",
                    found=uboot_in_strings,
                    evidence=(
                        "U-Boot strings found in firmware"
                        if uboot_in_strings
                        else "U-Boot not identified"
                    ),
                )
            )
        except Exception:
            analysis.boot_components.append(
                BootComponent(stage="U-Boot", found=False, evidence="U-Boot not identified")
            )

    # Check for kernel FIT
    kernel_fit_offset = offsets.get("KERNEL_FIT_OFFSET")
    if kernel_fit_offset:
        analysis.boot_components.append(
            BootComponent(
                stage="Kernel",
                found=True,
                evidence=f"FIT image at offset `{kernel_fit_offset}`",
            )
        )
    else:
        analysis.boot_components.append(
            BootComponent(stage="Kernel", found=False, evidence="Kernel FIT not identified")
        )

    # Check for initramfs/CPIO
    rootfs_cpio_offset = offsets.get("ROOTFS_CPIO_OFFSET")
    if rootfs_cpio_offset:
        analysis.boot_components.append(
            BootComponent(
                stage="Initramfs",
                found=True,
                evidence=f"CPIO at offset `{rootfs_cpio_offset}`",
            )
        )
    else:
        analysis.boot_components.append(
            BootComponent(stage="Initramfs", found=False, evidence="CPIO not identified")
        )

    # Check for SquashFS
    squashfs_offset = offsets.get("SQUASHFS_OFFSET")
    if squashfs_offset:
        analysis.boot_components.append(
            BootComponent(
                stage="SquashFS",
                found=True,
                evidence=f"Filesystem at offset `{squashfs_offset}`",
            )
        )
    else:
        analysis.boot_components.append(
            BootComponent(stage="SquashFS", found=False, evidence="SquashFS not identified")
        )


def analyze_component_versions(
    firmware: Path, extract_dir: Path, analysis: BootProcessAnalysis
) -> None:
    """Extract component versions."""
    # Extract U-Boot version
    try:
        result = subprocess.run(
            ["strings", str(firmware)],
            capture_output=True,
            text=True,
            check=False,
        )
        if match := re.search(r"U-Boot [0-9]+\.[0-9]+\.[0-9]+", result.stdout):
            uboot_version = match.group(0)
        else:
            uboot_version = "unknown"
    except Exception:
        uboot_version = "unknown"

    analysis.component_versions.append(
        ComponentVersion(component="U-Boot", version=uboot_version, source="Binary strings")
    )

    # Extract kernel version from modules
    rootfs = find_rootfs(extract_dir)
    kernel_version = "unknown"
    if rootfs:
        for ko_file in rootfs.rglob("*.ko"):
            try:
                result = subprocess.run(
                    ["strings", str(ko_file)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if match := re.search(r"vermagic=([0-9]+\.[0-9]+\.[0-9]+)", result.stdout):
                    kernel_version = match.group(1)
                    break
            except Exception:
                continue

    analysis.component_versions.append(
        ComponentVersion(component="Linux Kernel", version=kernel_version, source="Module vermagic")
    )

    # Get Buildroot version if available
    if rootfs:
        os_release = rootfs / "etc" / "os-release"
        if os_release.exists():
            try:
                content = os_release.read_text()
                if match := re.search(r'^VERSION="?([^"\n]+)"?', content, re.MULTILINE):
                    br_version = match.group(1)
                    analysis.component_versions.append(
                        ComponentVersion(
                            component="Buildroot", version=br_version, source="/etc/os-release"
                        )
                    )
            except Exception:
                pass


def analyze_partitions(offsets: dict[str, str | int], analysis: BootProcessAnalysis) -> None:
    """Analyze partition layout from offsets."""
    bootloader_fit_offset = offsets.get("BOOTLOADER_FIT_OFFSET")
    bootloader_fit_offset_dec = offsets.get("BOOTLOADER_FIT_OFFSET_DEC")
    kernel_fit_offset = offsets.get("KERNEL_FIT_OFFSET")
    kernel_fit_offset_dec = offsets.get("KERNEL_FIT_OFFSET_DEC")
    rootfs_cpio_offset = offsets.get("ROOTFS_CPIO_OFFSET")
    rootfs_cpio_offset_dec = offsets.get("ROOTFS_CPIO_OFFSET_DEC")
    squashfs_offset = offsets.get("SQUASHFS_OFFSET")
    squashfs_offset_dec = offsets.get("SQUASHFS_OFFSET_DEC")
    squashfs_size = offsets.get("SQUASHFS_SIZE")

    # Calculate sizes from offsets
    if (
        bootloader_fit_offset
        and bootloader_fit_offset_dec
        and kernel_fit_offset_dec
        and isinstance(bootloader_fit_offset_dec, int)
        and isinstance(kernel_fit_offset_dec, int)
    ):
        bl_size = (kernel_fit_offset_dec - bootloader_fit_offset_dec) // 1024 // 1024
        analysis.partitions.append(
            Partition(
                region="Bootloader",
                offset=str(bootloader_fit_offset),
                size_mb=bl_size,
                type="FIT",
                content="U-Boot + OP-TEE",
            )
        )

    if (
        kernel_fit_offset
        and kernel_fit_offset_dec
        and rootfs_cpio_offset_dec
        and isinstance(kernel_fit_offset_dec, int)
        and isinstance(rootfs_cpio_offset_dec, int)
    ):
        kernel_size = (rootfs_cpio_offset_dec - kernel_fit_offset_dec) // 1024 // 1024
        analysis.partitions.append(
            Partition(
                region="Kernel",
                offset=str(kernel_fit_offset),
                size_mb=kernel_size,
                type="FIT",
                content="Linux kernel + DTB",
            )
        )

    if (
        rootfs_cpio_offset
        and rootfs_cpio_offset_dec
        and squashfs_offset_dec
        and isinstance(rootfs_cpio_offset_dec, int)
        and isinstance(squashfs_offset_dec, int)
    ):
        cpio_size = (squashfs_offset_dec - rootfs_cpio_offset_dec) // 1024 // 1024
        analysis.partitions.append(
            Partition(
                region="Initramfs",
                offset=str(rootfs_cpio_offset),
                size_mb=cpio_size,
                type="CPIO",
                content="Early userspace",
            )
        )

    if squashfs_offset and squashfs_size and isinstance(squashfs_size, int):
        sq_size = squashfs_size // 1024 // 1024
        analysis.partitions.append(
            Partition(
                region="Root FS",
                offset=str(squashfs_offset),
                size_mb=sq_size,
                type="SquashFS",
                content="Main filesystem",
            )
        )


def analyze_ab_redundancy(extract_dir: Path, analysis: BootProcessAnalysis) -> None:
    """Analyze A/B partition scheme."""
    bootloader_fits = len(list(extract_dir.rglob("system.dtb")))

    if bootloader_fits > MIN_FIT_IMAGES_FOR_AB:
        analysis.ab_redundancy = True
        analysis.ab_evidence = (
            f"Found {bootloader_fits} FIT image DTBs in extraction. "
            "Multiple bootloader/kernel slots suggests A/B OTA support."
        )
        analysis.add_metadata(
            "ab_redundancy",
            "binwalk-extraction",
            f"count system.dtb files: {bootloader_fits} > 2",
        )
    else:
        analysis.ab_redundancy = False


def analyze_boot_config(dts_file: Path, analysis: BootProcessAnalysis) -> None:
    """Extract boot configuration from device tree."""
    try:
        content = dts_file.read_text()

        # Extract kernel command line
        if match := re.search(r'bootargs = "([^"]+)"', content):
            analysis.kernel_cmdline = match.group(1)
            analysis.add_metadata(
                "kernel_cmdline", "device-tree", "extract bootargs property from DTS"
            )

        # Extract UART/console settings
        baudrate = None
        if match := re.search(r"rockchip,baudrate = <([^>]+)>", content):
            baudrate = int(match.group(1))

        # Try to extract console from stdout-path or bootargs
        console_match = re.search(r'stdout-path = "([^"]+)"', content)
        if not console_match and analysis.kernel_cmdline:
            console_match = re.search(r"console=([^ ]+)", analysis.kernel_cmdline)
        console = console_match.group(1) if console_match else None

        if baudrate:
            analysis.console_configs.append(
                ConsoleConfig(
                    parameter="Baud Rate", value=str(baudrate), source="DTS rockchip,baudrate"
                )
            )

        if console:
            analysis.console_configs.append(
                ConsoleConfig(parameter="Console", value=console, source="DTS stdout-path/bootargs")
            )

    except Exception:
        pass


def generate_markdown(analysis: BootProcessAnalysis, output_file: Path) -> None:  # noqa: PLR0912, PLR0915
    """Generate markdown report for backward compatibility."""
    timestamp = datetime.now(UTC).isoformat()

    with output_file.open("w") as f:
        # Header
        f.write("# Boot Process and Partition Layout\n")
        f.write("\n")
        f.write("**GL.iNet Comet (GL-RM1) Firmware**\n")
        f.write("\n")
        f.write(f"Generated: {timestamp}\n")
        f.write("\n")
        f.write("Analysis of the GL.iNet Comet boot chain and storage layout.\n")
        f.write("\n")

        # Hardware Platform
        if analysis.hardware_properties:
            f.write("## Hardware Platform\n")
            f.write("\n")
            f.write("| Property | Value | Source |\n")
            f.write("|----------|-------|--------|\n")
            for prop in analysis.hardware_properties:
                f.write(f"| {prop.property} | {prop.value} | {prop.source} |\n")
            f.write("\n")

        # Boot Chain
        f.write("## Boot Chain\n")
        f.write("\n")
        f.write("See [docs/reference/rockchip-boot-chain.md](")
        f.write("../docs/reference/rockchip-boot-chain.md)\n")
        f.write("for the standard Rockchip RV1126 boot sequence.\n")
        f.write("\n")
        f.write("Components found in this firmware:\n")
        f.write("\n")
        f.write("| Stage | Found | Evidence |\n")
        f.write("|-------|-------|----------|\n")
        for component in analysis.boot_components:
            found_icon = "✅" if component.found else "❓"
            f.write(f"| {component.stage} | {found_icon} | {component.evidence} |\n")
        f.write("\n")

        # Component Versions
        if analysis.component_versions:
            f.write("## Component Versions\n")
            f.write("\n")
            f.write("| Component | Version | Source |\n")
            f.write("|-----------|---------|--------|\n")
            for version in analysis.component_versions:
                f.write(f"| {version.component} | {version.version} | {version.source} |\n")
            f.write("\n")

        # Partition Layout
        if analysis.partitions:
            f.write("## Partition Layout\n")
            f.write("\n")
            f.write("Derived from firmware offsets in `binwalk-offsets.sh`:\n")
            f.write("\n")
            f.write("| Region | Offset | Size | Type | Content |\n")
            f.write("|--------|--------|------|------|---------||\n")
            for partition in analysis.partitions:
                f.write(
                    f"| {partition.region} | `{partition.offset}` | ~{partition.size_mb} MB | "
                    f"{partition.type} | {partition.content} |\n"
                )
            f.write("\n")
            f.write("*Note: Sizes calculated from offset differences. ")
            f.write("Actual partition table may differ.*\n")
            f.write("\n")

        # FIT Image Structure
        f.write("## FIT Image Structure\n")
        f.write("\n")

        if analysis.bootloader_fit_info:
            f.write("### Bootloader FIT\n")
            f.write("\n")
            f.write("```\n")
            # Extract configurations section
            if "configurations" in analysis.bootloader_fit_info:
                lines = analysis.bootloader_fit_info.split("\n")
                in_config = False
                line_count = 0
                for line in lines:
                    if "configurations" in line:
                        in_config = True
                    if in_config:
                        f.write(line + "\n")
                        line_count += 1
                        if line_count >= FIT_INFO_LINE_LIMIT:
                            break
            else:
                f.write("Could not parse\n")
            f.write("```\n")
        else:
            f.write("*Bootloader FIT DTS not available*\n")
        f.write("\n")

        if analysis.kernel_fit_info:
            f.write("### Kernel FIT\n")
            f.write("\n")
            f.write("```\n")
            # Extract configurations section
            if "configurations" in analysis.kernel_fit_info:
                lines = analysis.kernel_fit_info.split("\n")
                in_config = False
                line_count = 0
                for line in lines:
                    if "configurations" in line:
                        in_config = True
                    if in_config:
                        f.write(line + "\n")
                        line_count += 1
                        if line_count >= FIT_INFO_LINE_LIMIT:
                            break
            else:
                f.write("Could not parse\n")
            f.write("```\n")
        else:
            f.write("*Kernel FIT DTS not available*\n")
        f.write("\n")

        # A/B Partition Scheme
        f.write("## A/B Partition Scheme\n")
        f.write("\n")
        if analysis.ab_redundancy and analysis.ab_evidence:
            f.write("**Evidence of A/B redundancy:**\n")
            f.write("\n")
            f.write(f"- {analysis.ab_evidence}\n")
        else:
            f.write("*No clear evidence of A/B partition scheme found.*\n")
        f.write("\n")

        # Boot Configuration
        f.write("## Boot Configuration\n")
        f.write("\n")

        if analysis.kernel_cmdline:
            f.write("### Kernel Command Line\n")
            f.write("\n")
            f.write("```\n")
            f.write(analysis.kernel_cmdline)
            f.write("\n```\n")
            f.write("\n")

        if analysis.console_configs:
            f.write("### Console Configuration\n")
            f.write("\n")
            f.write("| Parameter | Value | Source |\n")
            f.write("|-----------|-------|--------|\n")
            for config in analysis.console_configs:
                f.write(f"| {config.parameter} | {config.value} | {config.source} |\n")
            f.write("\n")

    success("Wrote boot-process.md")


def output_toml(analysis: BootProcessAnalysis) -> str:
    """Convert analysis to TOML format.

    Args:
        analysis: BootProcessAnalysis object

    Returns:
        TOML string with source metadata as comments
    """
    doc = tomlkit.document()

    # Add header comments
    doc.add(tomlkit.comment("Boot process and partition layout analysis"))
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
        description="Analyze boot process and partition layout",
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

    # Initialize directories
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    # Get firmware path
    firmware = get_firmware_path(args.firmware, work_dir)
    info(f"Analyzing: {firmware}")

    # Extract firmware
    extract_dir = extract_firmware(firmware, work_dir)

    # Analyze boot process
    analysis = analyze_boot_process(firmware, extract_dir, output_dir)

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

    # Generate legacy markdown output
    section("Generating markdown report")
    md_output = output_dir / "boot-process.md"
    generate_markdown(analysis, md_output)


if __name__ == "__main__":
    main()
