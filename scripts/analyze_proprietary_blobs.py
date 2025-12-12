#!/usr/bin/env python3
"""Analyze proprietary/closed-source binaries in firmware.

Usage: ./scripts/analyze_proprietary_blobs.py [firmware.img] [--format FORMAT]

Outputs: TOML (default) or JSON to stdout with source metadata

This script identifies:
- Rockchip proprietary libraries (MPP, RGA, ISP)
- Vendor-specific binaries
- Closed-source drivers and blobs
- Binary analysis (strings, symbols)

Arguments:
    firmware.img      Path to firmware file (optional, downloads default if not provided)
    --format FORMAT   Output format: 'toml' (default) or 'json'
"""

from __future__ import annotations

import argparse
import json
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

# Default firmware URL
DEFAULT_FIRMWARE_URL = "https://fw.gl-inet.com/kvm/rm1/release/glkvm-RM1-1.7.2-1128-1764344791.img"

# TOML formatting constants
TOML_MAX_COMMENT_LENGTH = 80
TOML_COMMENT_TRUNCATE_LENGTH = 77

# Binary analysis constants
MAX_INTERESTING_STRINGS = 20  # Maximum number of interesting strings to extract


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
class LibraryInfo:
    """Information about a proprietary library."""

    name: str  # Library name (e.g., "librockchip_mpp.so")
    path: str  # Path relative to rootfs
    size: int  # Size in bytes
    purpose: str  # Description of library purpose


@dataclass(frozen=True, slots=True)
class FirmwareBlob:
    """Information about a firmware blob."""

    name: str  # Filename
    path: str  # Path relative to rootfs
    size: int  # Size in bytes


@dataclass(frozen=True, slots=True)
class KernelModule:
    """Information about a kernel module."""

    name: str  # Module filename
    path: str  # Path relative to rootfs
    size: int  # Size in bytes
    has_gpl: bool  # Whether module contains GPL string


@dataclass(frozen=True, slots=True)
class BinaryAnalysis:
    """Binary analysis of a proprietary library."""

    library_name: str
    file_type: str
    interesting_strings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProprietaryBlobsAnalysis:
    """Results of proprietary blobs analysis."""

    firmware_file: str
    rootfs_path: str

    # Rockchip libraries by category
    mpp_libraries: list[LibraryInfo] = field(default_factory=list)  # Media Processing Platform
    rga_libraries: list[LibraryInfo] = field(default_factory=list)  # Graphics Acceleration
    isp_libraries: list[LibraryInfo] = field(default_factory=list)  # Image Signal Processor
    npu_libraries: list[LibraryInfo] = field(default_factory=list)  # Neural Processing Unit
    all_rockchip_libs: list[str] = field(default_factory=list)  # All Rockchip library paths

    # Other vendor components
    wifi_bt_blobs: list[FirmwareBlob] = field(default_factory=list)
    firmware_blobs: list[FirmwareBlob] = field(default_factory=list)
    kernel_modules: list[KernelModule] = field(default_factory=list)

    # Binary analysis
    binary_analysis: BinaryAnalysis | None = None

    # Summary counts
    rockchip_count: int = 0
    firmware_blob_count: int = 0
    kernel_module_count: int = 0

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

            # Convert lists of dataclass objects to dicts
            if key in {
                "mpp_libraries",
                "rga_libraries",
                "isp_libraries",
                "npu_libraries",
            }:
                result[key] = [
                    {
                        "name": lib.name,
                        "path": lib.path,
                        "size": lib.size,
                        "purpose": lib.purpose,
                    }
                    for lib in value
                ]
            elif key in {"wifi_bt_blobs", "firmware_blobs"}:
                result[key] = [
                    {"name": blob.name, "path": blob.path, "size": blob.size} for blob in value
                ]
            elif key == "kernel_modules":
                result[key] = [
                    {
                        "name": mod.name,
                        "path": mod.path,
                        "size": mod.size,
                        "has_gpl": mod.has_gpl,
                    }
                    for mod in value
                ]
            elif key == "binary_analysis" and value is not None:
                result[key] = {
                    "library_name": value.library_name,
                    "file_type": value.file_type,
                    "interesting_strings": value.interesting_strings,
                }
            else:
                result[key] = value

            # Add source metadata if available
            if key in self._source:
                result[f"{key}_source"] = self._source[key]
            if key in self._method:
                result[f"{key}_method"] = self._method[key]

        return result


def get_file_size(file_path: Path) -> int:
    """Get file size in bytes, handling cross-platform stat."""
    return file_path.stat().st_size


def find_libraries(rootfs: Path, patterns: list[str], purpose_prefix: str) -> list[LibraryInfo]:
    """Find libraries matching patterns in rootfs.

    Args:
        rootfs: Path to rootfs directory
        patterns: List of glob patterns to search for
        purpose_prefix: Prefix for purpose description

    Returns:
        List of LibraryInfo objects for found libraries
    """
    libraries = []

    for pattern in patterns:
        # Find files matching pattern
        found_files = list(rootfs.rglob(pattern))

        # Take first match for each pattern
        if found_files:
            lib_file = found_files[0]
            if lib_file.is_file():
                size = get_file_size(lib_file)
                rel_path = "/" + str(lib_file.relative_to(rootfs))

                # Extract base library name without version
                base_name = lib_file.name.split(".so")[0] + ".so"

                libraries.append(
                    LibraryInfo(
                        name=base_name,
                        path=rel_path,
                        size=size,
                        purpose=f"{purpose_prefix} ({size} bytes)",
                    )
                )

    return libraries


def find_all_rockchip_libs(rootfs: Path) -> list[str]:
    """Find all Rockchip libraries in rootfs.

    Args:
        rootfs: Path to rootfs directory

    Returns:
        List of paths relative to rootfs
    """
    lib_paths = []

    # Search patterns for Rockchip libraries
    patterns = ["librockchip*", "librk*", "*rga*", "*mpp*"]

    for pattern in patterns:
        for lib_file in rootfs.rglob(pattern):
            # Skip .pyc files
            if lib_file.suffix == ".pyc":
                continue
            if lib_file.is_file():
                rel_path = "/" + str(lib_file.relative_to(rootfs))
                if rel_path not in lib_paths:
                    lib_paths.append(rel_path)

    return sorted(lib_paths)


def find_wifi_bt_blobs(rootfs: Path) -> list[FirmwareBlob]:
    """Find WiFi/Bluetooth firmware blobs.

    Args:
        rootfs: Path to rootfs directory

    Returns:
        List of FirmwareBlob objects
    """
    blobs = []

    # Broadcom/Cypress WiFi patterns
    bcm_patterns = ["bcmdhd*.ko", "fw_bcm*.bin", "nvram*.txt", "brcmfmac*.bin"]

    # Realtek WiFi patterns
    rtl_patterns = ["rtl*.bin", "rtl*.ko"]

    all_patterns = bcm_patterns + rtl_patterns

    for pattern in all_patterns:
        found_files = list(rootfs.rglob(pattern))
        if found_files:
            blob_file = found_files[0]
            if blob_file.is_file():
                size = get_file_size(blob_file)
                rel_path = "/" + str(blob_file.relative_to(rootfs))
                blobs.append(FirmwareBlob(name=blob_file.name, path=rel_path, size=size))

    return blobs


def find_firmware_blobs(rootfs: Path) -> list[FirmwareBlob]:
    """Find firmware blobs in /lib/firmware.

    Args:
        rootfs: Path to rootfs directory

    Returns:
        List of FirmwareBlob objects
    """
    blobs = []
    firmware_dir = rootfs / "lib" / "firmware"

    if not firmware_dir.exists():
        return blobs

    for fw_file in firmware_dir.rglob("*"):
        if fw_file.is_file():
            size = get_file_size(fw_file)
            rel_path = "/" + str(fw_file.relative_to(rootfs))
            blobs.append(FirmwareBlob(name=fw_file.name, path=rel_path, size=size))

    # Limit to first 50 for sanity
    return blobs[:50]


def has_gpl_string(ko_file: Path) -> bool:
    """Check if kernel module contains GPL string.

    Args:
        ko_file: Path to .ko kernel module file

    Returns:
        True if module contains "GPL" string (case-insensitive)
    """
    try:
        result = subprocess.run(
            ["strings", str(ko_file)], capture_output=True, text=True, check=False
        )
        return "gpl" in result.stdout.lower()
    except Exception:
        return False


def find_kernel_modules(rootfs: Path) -> list[KernelModule]:
    """Find kernel modules (.ko files).

    Args:
        rootfs: Path to rootfs directory

    Returns:
        List of KernelModule objects (limited to 30)
    """
    modules = []

    for ko_file in rootfs.rglob("*.ko"):
        if ko_file.is_file():
            size = get_file_size(ko_file)
            rel_path = "/" + str(ko_file.relative_to(rootfs))
            has_gpl = has_gpl_string(ko_file)

            modules.append(
                KernelModule(name=ko_file.name, path=rel_path, size=size, has_gpl=has_gpl)
            )

    # Limit to first 30
    return modules[:30]


def analyze_binary(lib_file: Path) -> BinaryAnalysis | None:
    """Analyze a binary library file.

    Args:
        lib_file: Path to library file

    Returns:
        BinaryAnalysis object or None if analysis fails
    """
    if not lib_file.exists():
        return None

    # Get file type
    try:
        file_result = subprocess.run(
            ["file", "-b", str(lib_file)], capture_output=True, text=True, check=False
        )
        file_type = file_result.stdout.strip().split(",")[0] if file_result.stdout else "unknown"
    except Exception:
        file_type = "unknown"

    # Extract interesting strings
    interesting_strings = []
    try:
        strings_result = subprocess.run(
            ["strings", str(lib_file)], capture_output=True, text=True, check=False
        )

        if strings_result.returncode == 0:
            # Filter for interesting strings
            keywords = ["copyright", "version", "rockchip", "license", "build"]
            for line in strings_result.stdout.splitlines():
                line_lower = line.lower()
                if any(kw in line_lower for kw in keywords):
                    interesting_strings.append(line.strip())
                    if len(interesting_strings) >= MAX_INTERESTING_STRINGS:
                        break
    except Exception:
        pass

    return BinaryAnalysis(
        library_name=lib_file.name,
        file_type=file_type,
        interesting_strings=interesting_strings,
    )


def extract_firmware(firmware_path: Path, work_dir: Path) -> Path:
    """Extract firmware using binwalk if needed.

    Args:
        firmware_path: Path to firmware file
        work_dir: Working directory for extractions

    Returns:
        Path to extraction directory
    """
    extract_base = work_dir / "extractions"
    extract_dir = extract_base / f"{firmware_path.name}.extracted"

    if not extract_dir.exists():
        info("Extracting firmware with binwalk...")
        extract_base.mkdir(parents=True, exist_ok=True)

        try:
            subprocess.run(
                ["binwalk", "-e", "--run-as=root", str(firmware_path)],
                cwd=extract_base,
                capture_output=True,
                check=False,
            )
        except FileNotFoundError:
            error("binwalk command not found")
            error("Please run this script within 'nix develop' shell")
            sys.exit(1)

    return extract_dir


def find_rootfs(extract_dir: Path) -> Path:
    """Find SquashFS rootfs in extraction directory.

    Args:
        extract_dir: Path to extraction directory

    Returns:
        Path to squashfs-root directory

    Raises:
        SystemExit: If rootfs not found
    """
    # Look for squashfs-root directory
    rootfs_dirs = list(extract_dir.rglob("squashfs-root"))

    if not rootfs_dirs or not rootfs_dirs[0].is_dir():
        error(f"Could not find SquashFS rootfs in {extract_dir}")
        sys.exit(1)

    return rootfs_dirs[0]


def analyze_proprietary_blobs(firmware_path: str, work_dir: Path) -> ProprietaryBlobsAnalysis:
    """Analyze proprietary blobs in firmware.

    Args:
        firmware_path: Path to firmware file
        work_dir: Working directory for extractions

    Returns:
        ProprietaryBlobsAnalysis object with all findings
    """
    firmware = Path(firmware_path)

    if not firmware.exists():
        error(f"Firmware file not found: {firmware}")
        sys.exit(1)

    info(f"Analyzing proprietary blobs in: {firmware}")

    # Extract firmware and find rootfs
    extract_dir = extract_firmware(firmware, work_dir)
    rootfs = find_rootfs(extract_dir)

    info(f"Using rootfs: {rootfs}")

    section("Scanning for proprietary binaries")

    # Create analysis object
    analysis = ProprietaryBlobsAnalysis(firmware_file=firmware.name, rootfs_path=str(rootfs))

    analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")
    analysis.add_metadata("rootfs_path", "binwalk", "find extracted squashfs-root")

    # Find MPP libraries
    mpp_patterns = ["librockchip_mpp.so*", "libmpp.so*", "librk_mpi.so*"]
    analysis.mpp_libraries = find_libraries(rootfs, mpp_patterns, "Video codec")
    analysis.add_metadata(
        "mpp_libraries",
        "filesystem",
        f"find rootfs -name {' -o -name '.join(repr(p) for p in mpp_patterns)}",
    )

    # Find RGA libraries
    rga_patterns = ["librga.so*", "librockchip_rga.so*"]
    analysis.rga_libraries = find_libraries(rootfs, rga_patterns, "2D graphics")
    analysis.add_metadata(
        "rga_libraries",
        "filesystem",
        f"find rootfs -name {' -o -name '.join(repr(p) for p in rga_patterns)}",
    )

    # Find ISP libraries
    isp_patterns = ["librkaiq.so*", "librkisp.so*", "librk_aiq.so*"]
    analysis.isp_libraries = find_libraries(rootfs, isp_patterns, "Camera ISP")
    analysis.add_metadata(
        "isp_libraries",
        "filesystem",
        f"find rootfs -name {' -o -name '.join(repr(p) for p in isp_patterns)}",
    )

    # Find NPU libraries
    npu_patterns = ["librknn_runtime.so*", "librknnrt.so*"]
    analysis.npu_libraries = find_libraries(rootfs, npu_patterns, "AI inference")
    analysis.add_metadata(
        "npu_libraries",
        "filesystem",
        f"find rootfs -name {' -o -name '.join(repr(p) for p in npu_patterns)}",
    )

    # Find all Rockchip libraries
    analysis.all_rockchip_libs = find_all_rockchip_libs(rootfs)
    analysis.add_metadata(
        "all_rockchip_libs",
        "filesystem",
        "find rootfs -name 'librockchip*' -o -name 'librk*' -o -name '*rga*' -o -name '*mpp*'",
    )

    # Find WiFi/BT blobs
    analysis.wifi_bt_blobs = find_wifi_bt_blobs(rootfs)
    analysis.add_metadata(
        "wifi_bt_blobs",
        "filesystem",
        "find rootfs -name 'bcmdhd*' -o -name 'fw_bcm*' -o -name 'brcmfmac*' -o -name 'rtl*'",
    )

    # Find firmware blobs
    analysis.firmware_blobs = find_firmware_blobs(rootfs)
    analysis.add_metadata("firmware_blobs", "filesystem", "find rootfs/lib/firmware -type f")

    # Find kernel modules
    analysis.kernel_modules = find_kernel_modules(rootfs)
    analysis.add_metadata(
        "kernel_modules",
        "filesystem",
        "find rootfs -name '*.ko' | strings | grep -i GPL",
    )

    # Binary analysis of MPP library if found
    if analysis.mpp_libraries:
        mpp_lib_name = analysis.mpp_libraries[0].path
        mpp_lib_file = rootfs / mpp_lib_name.lstrip("/")
        analysis.binary_analysis = analyze_binary(mpp_lib_file)
        analysis.add_metadata(
            "binary_analysis",
            "file+strings",
            (
                f"file {mpp_lib_name} && strings {mpp_lib_name} | "
                "grep -iE 'copyright|version|rockchip|license|build'"
            ),
        )

    # Calculate summary counts
    analysis.rockchip_count = len(analysis.all_rockchip_libs)
    analysis.firmware_blob_count = len(analysis.firmware_blobs)
    analysis.kernel_module_count = len(analysis.kernel_modules)

    analysis.add_metadata("rockchip_count", "filesystem", "count all_rockchip_libs results")
    analysis.add_metadata("firmware_blob_count", "filesystem", "count firmware_blobs results")
    analysis.add_metadata("kernel_module_count", "filesystem", "count kernel_modules results")

    return analysis


def output_toml(analysis: ProprietaryBlobsAnalysis) -> str:
    """Convert analysis to TOML format.

    Args:
        analysis: ProprietaryBlobsAnalysis object

    Returns:
        TOML string with source metadata as comments
    """
    doc = tomlkit.document()

    # Add header
    doc.add(tomlkit.comment("Proprietary blobs analysis"))
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
        description="Analyze proprietary/closed-source binaries in firmware",
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
        firmware_file = DEFAULT_FIRMWARE_URL.split("/")[-1]
        firmware_path = str(work_dir / firmware_file)

        if not Path(firmware_path).exists():
            info(f"Downloading firmware: {DEFAULT_FIRMWARE_URL}")
            work_dir.mkdir(parents=True, exist_ok=True)
            try:
                subprocess.run(
                    ["curl", "-L", "-o", firmware_path, DEFAULT_FIRMWARE_URL],
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                error(f"Failed to download firmware: {e}")
                sys.exit(1)

    # Analyze firmware
    analysis = analyze_proprietary_blobs(firmware_path, work_dir)

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


if __name__ == "__main__":
    main()
