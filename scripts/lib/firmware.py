"""Shared firmware handling utilities for analysis scripts."""

import subprocess
import sys
from pathlib import Path

from lib.logging import error, info

# Default firmware URL for GL.iNet Comet (RM1)
DEFAULT_FIRMWARE_URL = "https://fw.gl-inet.com/kvm/rm1/release/glkvm-RM1-1.7.2-1128-1764344791.img"


def get_firmware_path(
    firmware_arg: str | None, work_dir: Path, firmware_url: str = DEFAULT_FIRMWARE_URL
) -> Path:
    """Get firmware path, downloading if necessary.

    Args:
        firmware_arg: User-provided firmware path (optional)
        work_dir: Working directory for downloads
        firmware_url: URL to download firmware from (default: DEFAULT_FIRMWARE_URL)

    Returns:
        Path to firmware file

    Raises:
        SystemExit: If user-provided firmware doesn't exist or download fails
    """
    if firmware_arg:
        firmware = Path(firmware_arg)
        if not firmware.exists():
            error(f"Firmware file not found: {firmware}")
            sys.exit(1)
        return firmware

    # Download default firmware
    firmware_file = firmware_url.split("/")[-1]
    firmware_path = work_dir / firmware_file

    if not firmware_path.exists():
        info(f"Downloading firmware: {firmware_url}")
        work_dir.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["curl", "-L", "-o", str(firmware_path), firmware_url],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            error(f"Failed to download firmware: {e}")
            sys.exit(1)

    return firmware_path


def extract_firmware(firmware: Path, work_dir: Path) -> Path:
    """Extract firmware using binwalk.

    Args:
        firmware: Path to firmware file
        work_dir: Working directory for extractions

    Returns:
        Path to extraction directory

    Raises:
        SystemExit: If binwalk is not found
    """
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


def find_squashfs_rootfs(extract_dir: Path) -> Path:
    """Find SquashFS rootfs in extraction directory.

    Args:
        extract_dir: Path to binwalk extraction directory

    Returns:
        Path to squashfs-root directory

    Raises:
        SystemExit: If rootfs not found
    """
    # Look for squashfs-root directory
    for rootfs in extract_dir.rglob("squashfs-root"):
        if rootfs.is_dir():
            return rootfs

    error(f"Could not find SquashFS rootfs in {extract_dir}")
    sys.exit(1)


def offset_to_dir_name(offset: int | str) -> str:
    """Convert offset to binwalk extraction directory name format.

    Binwalk creates directories named with uppercase hex offsets without 0x prefix.

    Args:
        offset: Offset as int or hex string (e.g., 0x2000, "0x2000", 8192)

    Returns:
        Directory name (e.g., "2000")

    Examples:
        >>> offset_to_dir_name(0x2000)
        '2000'
        >>> offset_to_dir_name("0x2000")
        '2000'
        >>> offset_to_dir_name(8192)
        '2000'
    """
    if isinstance(offset, str):
        # Remove 0x prefix if present
        offset = offset.replace("0x", "").replace("0X", "")
        return offset.upper()
    # Convert int to hex without 0x prefix
    return f"{offset:X}"


def find_extracted_file(extract_dir: Path, pattern: str) -> Path | None:
    """Find first file matching pattern in extraction directory.

    Args:
        extract_dir: Path to binwalk extraction directory
        pattern: Glob pattern (e.g., "*.dtb", "*/boot/*")

    Returns:
        Path to first matching file, or None if not found
    """
    for match in extract_dir.rglob(pattern):
        if match.is_file():
            return match
    return None


def find_largest_dtb(extract_dir: Path) -> Path | None:
    """Find largest .dtb file in extraction directory.

    Args:
        extract_dir: Path to binwalk extraction directory

    Returns:
        Path to largest .dtb file, or None if no .dtb files found
    """
    dtb_files = list(extract_dir.rglob("*.dtb"))
    if not dtb_files:
        return None

    # Return largest by file size
    return max(dtb_files, key=lambda p: p.stat().st_size)


def extract_device_tree_node(dtb_path: Path, node_path: str) -> str:
    """Extract device tree node content using dtc.

    Args:
        dtb_path: Path to .dtb file
        node_path: Node path (e.g., "/chosen", "/memory")

    Returns:
        Node content as string (DTS format)

    Raises:
        SystemExit: If dtc command fails
    """
    try:
        result = subprocess.run(
            ["dtc", "-I", "dtb", "-O", "dts", str(dtb_path)],
            capture_output=True,
            text=True,
            check=True,
        )

        # Extract the specific node from the output
        dts_content = result.stdout
        lines = dts_content.split("\n")

        # Find the node
        node_start = None
        brace_count = 0
        node_lines = []

        for i, line in enumerate(lines):
            if node_path in line and "{" in line:
                node_start = i
                brace_count = 1
                node_lines.append(line)
            elif node_start is not None:
                node_lines.append(line)
                brace_count += line.count("{")
                brace_count -= line.count("}")
                if brace_count == 0:
                    break

        return "\n".join(node_lines) if node_lines else ""

    except subprocess.CalledProcessError as e:
        error(f"Failed to extract device tree node: {e}")
        sys.exit(1)
    except FileNotFoundError:
        error("dtc command not found")
        error("Please run this script within 'nix develop' shell")
        sys.exit(1)
