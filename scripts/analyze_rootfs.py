#!/usr/bin/env python3
"""Analyze root filesystem contents.

Usage: ./scripts/analyze_rootfs.py [firmware.img] [--format FORMAT]

Outputs: TOML (default) or JSON to stdout with source metadata

This script performs GPL compliance analysis by:
- Extracting SquashFS filesystem from firmware
- Analyzing filesystem structure and contents
- Identifying GPL-licensed binaries
- Listing packages and versions
- Parsing license files
- Outputting structured data with source tracking
"""

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lib.analysis_base import AnalysisBase
from lib.logging import error, info, section, success, warn
from lib.output import output_json, output_toml

# Constants
DEFAULT_FIRMWARE_URL = "https://fw.gl-inet.com/kvm/rm1/release/glkvm-RM1-1.7.2-1128-1764344791.img"
MAX_LICENSE_FILE_SIZE = 100000
MAX_LICENSE_FILES = 50
MAX_LICENSE_PREVIEW_LINES = 50


@dataclass(frozen=True, slots=True)
class KernelModule:
    """A kernel module (.ko file) found in the filesystem."""

    name: str
    path: str
    size: int


@dataclass(frozen=True, slots=True)
class SharedLibrary:
    """A shared library (.so file) found in the filesystem."""

    name: str
    path: str
    size: int


@dataclass(frozen=True, slots=True)
class GplBinary:
    """A GPL-licensed binary found in the filesystem."""

    name: str
    path: str
    license: str
    version: str | None = None


@dataclass(frozen=True, slots=True)
class LicenseFile:
    """A license or copyright file found in the filesystem."""

    path: str
    content_preview: str  # First 50 lines


@dataclass(frozen=True, slots=True)
class DetectedLicense:
    """A detected license from library name or file analysis."""

    component: str
    license: str
    detection_method: str


@dataclass(slots=True)
class RootfsAnalysis(AnalysisBase):
    """Results of root filesystem analysis."""

    firmware_file: str
    rootfs_path: str
    os_name: str | None = None
    os_version: str | None = None
    os_pretty_name: str | None = None
    kernel_version: str | None = None
    kernel_modules_count: int = 0
    shared_libraries_count: int = 0
    busybox_found: bool = False
    busybox_version: str | None = None
    kernel_modules: list[KernelModule] = field(default_factory=list)
    shared_libraries: list[SharedLibrary] = field(default_factory=list)
    gpl_binaries: list[GplBinary] = field(default_factory=list)
    license_files: list[LicenseFile] = field(default_factory=list)
    detected_licenses: list[DetectedLicense] = field(default_factory=list)

    # Source metadata for each field
    _source: dict[str, str] = field(default_factory=dict)
    _method: dict[str, str] = field(default_factory=dict)

    def _convert_complex_field(self, key: str, value: Any) -> tuple[bool, Any]:
        """Convert complex fields to serializable format."""
        if key == "kernel_modules":
            return True, [{"name": m.name, "path": m.path, "size": m.size} for m in value]
        if key == "shared_libraries":
            return True, [
                {"name": lib.name, "path": lib.path, "size": lib.size} for lib in value
            ]
        if key == "gpl_binaries":
            return True, [
                {
                    "name": b.name,
                    "path": b.path,
                    "license": b.license,
                    "version": b.version,
                }
                for b in value
            ]
        if key == "license_files":
            return True, [
                {"path": lf.path, "content_preview": lf.content_preview} for lf in value
            ]
        if key == "detected_licenses":
            return True, [
                {
                    "component": dl.component,
                    "license": dl.license,
                    "detection_method": dl.detection_method,
                }
                for dl in value
            ]
        return False, None


def run_binwalk_extraction(firmware: Path, work_dir: Path) -> Path:
    """Extract firmware using binwalk and return extraction directory."""
    extract_base = work_dir / "extractions"
    extract_dir = extract_base / f"{firmware.name}.extracted"

    if extract_dir.exists():
        info(f"Using cached extraction: {extract_dir}")
        return extract_dir

    extract_base.mkdir(parents=True, exist_ok=True)

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

    if not extract_dir.exists():
        error(f"Binwalk extraction failed: {extract_dir}")
        sys.exit(1)

    return extract_dir


def find_squashfs_rootfs(extract_dir: Path) -> Path:
    """Find SquashFS rootfs in extraction directory."""
    # Look for squashfs-root directory
    for rootfs in extract_dir.rglob("squashfs-root"):
        if rootfs.is_dir():
            info(f"Found rootfs: {rootfs}")
            return rootfs

    error(f"Could not find SquashFS rootfs in {extract_dir}")
    sys.exit(1)


def parse_os_release(rootfs: Path, analysis: RootfsAnalysis) -> None:
    """Parse /etc/os-release file."""
    os_release = rootfs / "etc/os-release"
    if not os_release.exists():
        return

    try:
        content = os_release.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            if line.startswith("NAME="):
                analysis.os_name = line.split("=", 1)[1].strip('"')
                analysis.add_metadata("os_name", "/etc/os-release", "NAME field")
            elif line.startswith("VERSION="):
                analysis.os_version = line.split("=", 1)[1].strip('"')
                analysis.add_metadata("os_version", "/etc/os-release", "VERSION field")
            elif line.startswith("PRETTY_NAME="):
                analysis.os_pretty_name = line.split("=", 1)[1].strip('"')
                analysis.add_metadata("os_pretty_name", "/etc/os-release", "PRETTY_NAME field")
    except Exception as e:
        warn(f"Failed to parse /etc/os-release: {e}")


def extract_kernel_version(rootfs: Path, analysis: RootfsAnalysis) -> None:
    """Extract kernel version from module vermagic."""
    # Find first .ko file
    try:
        ko_file = next(rootfs.rglob("*.ko"))
    except StopIteration:
        warn("No kernel modules found to extract version")
        return

    try:
        # Run strings on the .ko file
        result = subprocess.run(
            ["strings", str(ko_file)],
            capture_output=True,
            text=True,
            check=False,
        )

        # Look for vermagic= string
        for line in result.stdout.splitlines():
            if "vermagic=" in line:
                analysis.kernel_version = line
                analysis.add_metadata(
                    "kernel_version",
                    "kernel module",
                    f"strings {ko_file.name} | grep vermagic",
                )
                break
    except Exception as e:
        warn(f"Failed to extract kernel version: {e}")


def analyze_kernel_modules(rootfs: Path, analysis: RootfsAnalysis) -> None:
    """Analyze kernel modules (.ko files)."""
    modules = []
    for ko_file in rootfs.rglob("*.ko"):
        if ko_file.is_file():
            path_relative = str(ko_file.relative_to(rootfs))
            modules.append(
                KernelModule(
                    name=ko_file.name,
                    path=f"/{path_relative}",
                    size=ko_file.stat().st_size,
                )
            )

    analysis.kernel_modules = sorted(modules, key=lambda m: m.path)
    analysis.kernel_modules_count = len(modules)
    analysis.add_metadata(
        "kernel_modules_count",
        "filesystem scan",
        "find rootfs -name '*.ko' | wc -l",
    )


def analyze_shared_libraries(rootfs: Path, analysis: RootfsAnalysis) -> None:
    """Analyze shared libraries (.so files)."""
    libraries = []
    for so_file in rootfs.rglob("*.so*"):
        if so_file.is_file():
            path_relative = str(so_file.relative_to(rootfs))
            libraries.append(
                SharedLibrary(
                    name=so_file.name,
                    path=f"/{path_relative}",
                    size=so_file.stat().st_size,
                )
            )

    # Sort and limit to first 100 for output
    analysis.shared_libraries = sorted(libraries, key=lambda lib: lib.path)[:100]
    analysis.shared_libraries_count = len(libraries)
    analysis.add_metadata(
        "shared_libraries_count",
        "filesystem scan",
        "find rootfs -name '*.so*' | wc -l",
    )


def analyze_busybox(rootfs: Path, analysis: RootfsAnalysis) -> None:
    """Analyze BusyBox binary."""
    busybox_path = rootfs / "bin/busybox"
    if not busybox_path.exists():
        return

    analysis.busybox_found = True
    analysis.add_metadata("busybox_found", "filesystem", "test -f /bin/busybox")

    try:
        # Extract version using strings
        result = subprocess.run(
            ["strings", str(busybox_path)],
            capture_output=True,
            text=True,
            check=False,
        )

        for line in result.stdout.splitlines():
            if "BusyBox v" in line:
                analysis.busybox_version = line
                analysis.add_metadata(
                    "busybox_version",
                    "/bin/busybox",
                    "strings /bin/busybox | grep 'BusyBox v'",
                )
                break

        # Add to GPL binaries
        analysis.gpl_binaries.append(
            GplBinary(
                name="busybox",
                path="/bin/busybox",
                license="GPL-2.0",
                version=analysis.busybox_version,
            )
        )
    except Exception as e:
        warn(f"Failed to analyze BusyBox: {e}")


def analyze_gpl_binaries(rootfs: Path, analysis: RootfsAnalysis) -> None:
    """Identify GPL-licensed binaries."""
    # Known GPL binaries to search for
    gpl_binaries_map = {
        # GNU Coreutils (GPL-3.0+)
        "ls": "GPL-3.0+",
        "cp": "GPL-3.0+",
        "mv": "GPL-3.0+",
        "rm": "GPL-3.0+",
        "cat": "GPL-3.0+",
        "grep": "GPL-3.0+",
        "sed": "GPL-3.0+",
        "awk": "GPL-3.0+",
        # Shell interpreters
        "bash": "GPL-3.0+",
        "sh": "GPL",
        "ash": "GPL-2.0",
        "dash": "GPL",
        # Compression tools
        "tar": "GPL-3.0+",
        "gzip": "GPL-3.0+",
        "bzip2": "GPL",
        "xz": "GPL",
    }

    for binary_name, license_str in gpl_binaries_map.items():
        # Search for the binary in common locations
        search_paths = [
            rootfs / "bin",
            rootfs / "usr/bin",
            rootfs / "sbin",
            rootfs / "usr/sbin",
        ]
        for search_path in search_paths:
            if not search_path.exists():
                continue

            binary_path = search_path / binary_name
            if binary_path.exists() and binary_path.is_file():
                path_relative = str(binary_path.relative_to(rootfs))

                # Check if it's a symlink to busybox
                detected_license = license_str
                if binary_path.is_symlink():
                    detected_license = "BusyBox (GPL-2.0)"

                analysis.gpl_binaries.append(
                    GplBinary(
                        name=binary_name,
                        path=f"/{path_relative}",
                        license=detected_license,
                    )
                )
                break  # Found it, move to next binary


def analyze_license_files(rootfs: Path, analysis: RootfsAnalysis) -> None:
    """Find and analyze license files."""
    license_patterns = [
        "*license*",
        "*LICENSE*",
        "*copying*",
        "*COPYING*",
        "*copyright*",
        "*COPYRIGHT*",
    ]

    license_files = []
    for pattern in license_patterns:
        for license_file in rootfs.rglob(pattern):
            if not license_file.is_file():
                continue

            # Skip very large files
            if license_file.stat().st_size > MAX_LICENSE_FILE_SIZE:
                continue

            try:
                content = license_file.read_text(encoding="utf-8", errors="replace")
                # Get first N lines
                lines = content.splitlines()[:MAX_LICENSE_PREVIEW_LINES]
                preview = "\n".join(lines)

                path_relative = str(license_file.relative_to(rootfs))
                license_files.append(
                    LicenseFile(
                        path=f"/{path_relative}",
                        content_preview=preview,
                    )
                )

                # Limit total license files
                if len(license_files) >= MAX_LICENSE_FILES:
                    break
            except Exception as e:
                warn(f"Failed to read license file {license_file}: {e}")

        if len(license_files) >= MAX_LICENSE_FILES:
            break

    analysis.license_files = sorted(license_files, key=lambda lf: lf.path)


def detect_library_licenses(rootfs: Path, analysis: RootfsAnalysis) -> None:
    """Detect licenses from known library names."""
    # Known library -> license mapping
    known_licenses = {
        "libc.so": "LGPL-2.1",
        "libpthread": "LGPL-2.1",
        "libm.so": "LGPL-2.1",
        "libdl.so": "LGPL-2.1",
        "librt.so": "LGPL-2.1",
        "libstdc++": "GPL-3.0-with-GCC-exception",
        "libgcc": "GPL-3.0-with-GCC-exception",
        "libssl": "OpenSSL",
        "libcrypto": "OpenSSL",
        "libz.so": "Zlib",
        "libsqlite": "Public-Domain",
        "librockchip": "Apache-2.0",
        "librga": "Apache-2.0",
        "libavcodec": "LGPL-2.1",
        "libavformat": "LGPL-2.1",
        "libavutil": "LGPL-2.1",
    }

    detected = []
    for pattern, license_str in known_licenses.items():
        for lib_file in rootfs.rglob(f"*{pattern}*"):
            if lib_file.is_file() and ".so" in lib_file.name:
                detected.append(
                    DetectedLicense(
                        component=pattern,
                        license=license_str,
                        detection_method="Known library name matching",
                    )
                )
                break  # Found at least one instance

    analysis.detected_licenses = sorted(detected, key=lambda d: d.component)


def analyze_rootfs(firmware_path: str, work_dir: Path) -> RootfsAnalysis:
    """Analyze root filesystem and return structured results."""
    firmware = Path(firmware_path)

    if not firmware.exists():
        error(f"Firmware file not found: {firmware}")
        sys.exit(1)

    info(f"Analyzing rootfs in: {firmware}")

    # Extract firmware
    section("Extracting Firmware")
    extract_dir = run_binwalk_extraction(firmware, work_dir)

    # Find rootfs
    section("Finding SquashFS Rootfs")
    rootfs = find_squashfs_rootfs(extract_dir)

    # Create analysis object
    analysis = RootfsAnalysis(
        firmware_file=firmware.name,
        rootfs_path=str(rootfs),
    )

    analysis.add_metadata("firmware_file", "filesystem", "basename(firmware_path)")
    analysis.add_metadata("rootfs_path", "binwalk extraction", "find_squashfs_rootfs()")

    # Perform analyses
    section("Build Information")
    parse_os_release(rootfs, analysis)

    section("Kernel Version")
    extract_kernel_version(rootfs, analysis)

    section("Kernel Modules")
    analyze_kernel_modules(rootfs, analysis)

    section("Shared Libraries")
    analyze_shared_libraries(rootfs, analysis)

    section("GPL Binaries")
    analyze_busybox(rootfs, analysis)
    analyze_gpl_binaries(rootfs, analysis)

    section("License Files")
    analyze_license_files(rootfs, analysis)

    section("License Detection")
    detect_library_licenses(rootfs, analysis)

    return analysis


# Field order for TOML output
SIMPLE_FIELDS = [
    "firmware_file",
    "rootfs_path",
    "os_name",
    "os_version",
    "os_pretty_name",
    "kernel_version",
    "kernel_modules_count",
    "shared_libraries_count",
    "busybox_found",
    "busybox_version",
]

COMPLEX_FIELDS = [
    "kernel_modules",
    "shared_libraries",
    "gpl_binaries",
    "license_files",
    "detected_licenses",
]


def main() -> None:
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Analyze root filesystem contents",
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
            subprocess.run(
                ["curl", "-L", "-o", firmware_path, DEFAULT_FIRMWARE_URL],
                check=True,
            )

    # Analyze rootfs
    analysis = analyze_rootfs(firmware_path, work_dir)

    # Output in requested format
    if args.format == "json":
        print(output_json(analysis))
    else:  # toml
        print(
            output_toml(
                analysis,
                title="Root filesystem analysis",
                simple_fields=SIMPLE_FIELDS,
                complex_fields=COMPLEX_FIELDS,
            )
        )

    success("Rootfs analysis complete")


if __name__ == "__main__":
    main()
