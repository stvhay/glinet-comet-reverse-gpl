"""Shared firmware handling utilities for analysis scripts."""

import subprocess
import sys
from pathlib import Path

from lib.logging import error, info

# Default firmware URL for GL.iNet Comet (RM1)
DEFAULT_FIRMWARE_URL = (
    "https://fw.gl-inet.com/kvm/rm1/release/glkvm-RM1-1.7.2-1128-1764344791.img"
)


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
