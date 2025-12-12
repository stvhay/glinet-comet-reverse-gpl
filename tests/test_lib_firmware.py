"""Tests for scripts/lib/firmware.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts directory to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib.firmware import (
    DEFAULT_FIRMWARE_URL,
    extract_firmware,
    find_squashfs_rootfs,
    get_firmware_path,
)


class TestDefaultFirmwareUrl:
    """Test DEFAULT_FIRMWARE_URL constant."""

    def test_url_is_defined(self):
        """Test that DEFAULT_FIRMWARE_URL is defined."""
        assert DEFAULT_FIRMWARE_URL
        assert isinstance(DEFAULT_FIRMWARE_URL, str)

    def test_url_points_to_glinet(self):
        """Test that URL points to GL.iNet firmware."""
        assert "fw.gl-inet.com" in DEFAULT_FIRMWARE_URL
        assert "glkvm-RM1" in DEFAULT_FIRMWARE_URL


class TestGetFirmwarePath:
    """Test get_firmware_path function."""

    def test_returns_user_provided_path_if_exists(self, tmp_path):
        """Test that user-provided path is returned if it exists."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"test")

        result = get_firmware_path(str(firmware), tmp_path)

        assert result == firmware

    def test_exits_if_user_provided_path_not_exists(self, tmp_path):
        """Test that it exits if user-provided path doesn't exist."""
        firmware = tmp_path / "nonexistent.img"

        with pytest.raises(SystemExit):
            get_firmware_path(str(firmware), tmp_path)

    def test_downloads_firmware_if_not_exists(self, tmp_path):
        """Test that firmware is downloaded if it doesn't exist."""
        with patch("subprocess.run") as mock_run:
            result = get_firmware_path(None, tmp_path)

            # Should have called curl
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "curl"
            assert "-L" in args
            assert DEFAULT_FIRMWARE_URL in args

            # Should return path to downloaded file
            assert result.parent == tmp_path
            assert "glkvm-RM1" in result.name

    def test_uses_existing_downloaded_firmware(self, tmp_path):
        """Test that existing downloaded firmware is reused."""
        firmware_file = DEFAULT_FIRMWARE_URL.split("/")[-1]
        firmware = tmp_path / firmware_file
        firmware.write_bytes(b"test")

        with patch("subprocess.run") as mock_run:
            result = get_firmware_path(None, tmp_path)

            # Should not have called curl
            mock_run.assert_not_called()

            # Should return existing file
            assert result == firmware

    def test_creates_work_dir_if_not_exists(self, tmp_path):
        """Test that work directory is created if it doesn't exist."""
        work_dir = tmp_path / "nonexistent"

        with patch("subprocess.run"):
            get_firmware_path(None, work_dir)

            assert work_dir.exists()

    def test_exits_on_download_failure(self, tmp_path):
        """Test that it exits if download fails."""
        with (
            patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "curl")),
            pytest.raises(SystemExit),
        ):
            get_firmware_path(None, tmp_path)

    def test_uses_custom_firmware_url(self, tmp_path):
        """Test that custom firmware URL can be provided."""
        custom_url = "https://example.com/custom-firmware.img"

        with patch("subprocess.run") as mock_run:
            result = get_firmware_path(None, tmp_path, firmware_url=custom_url)

            # Should have called curl with custom URL
            args = mock_run.call_args[0][0]
            assert custom_url in args

            # Should return path based on custom URL
            assert result.name == "custom-firmware.img"


class TestExtractFirmware:
    """Test extract_firmware function."""

    def test_extracts_firmware_if_not_exists(self, tmp_path):
        """Test that firmware is extracted if extraction doesn't exist."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"test")

        with patch("subprocess.run") as mock_run:
            result = extract_firmware(firmware, tmp_path)

            # Should have called binwalk
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "binwalk"
            assert "-e" in args
            assert str(firmware) in args

            # Should return extraction directory
            assert result.parent.name == "extractions"
            assert result.name == "firmware.img.extracted"

    def test_reuses_existing_extraction(self, tmp_path):
        """Test that existing extraction is reused."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"test")

        extract_dir = tmp_path / "extractions" / "firmware.img.extracted"
        extract_dir.mkdir(parents=True)

        with patch("subprocess.run") as mock_run:
            result = extract_firmware(firmware, tmp_path)

            # Should not have called binwalk
            mock_run.assert_not_called()

            # Should return existing extraction directory
            assert result == extract_dir

    def test_creates_extraction_directory(self, tmp_path):
        """Test that extraction directory is created."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"test")

        with patch("subprocess.run"):
            extract_firmware(firmware, tmp_path)

            extract_base = tmp_path / "extractions"
            assert extract_base.exists()

    def test_exits_if_binwalk_not_found(self, tmp_path):
        """Test that it exits if binwalk is not found."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"test")

        with (
            patch("subprocess.run", side_effect=FileNotFoundError),
            pytest.raises(SystemExit),
        ):
            extract_firmware(firmware, tmp_path)


class TestFindSquashfsRootfs:
    """Test find_squashfs_rootfs function."""

    def test_finds_rootfs_in_top_level(self, tmp_path):
        """Test that rootfs is found in top-level directory."""
        rootfs = tmp_path / "squashfs-root"
        rootfs.mkdir()

        result = find_squashfs_rootfs(tmp_path)

        assert result == rootfs

    def test_finds_rootfs_in_subdirectory(self, tmp_path):
        """Test that rootfs is found in subdirectory."""
        subdir = tmp_path / "sub"
        subdir.mkdir()
        rootfs = subdir / "squashfs-root"
        rootfs.mkdir()

        result = find_squashfs_rootfs(tmp_path)

        assert result == rootfs

    def test_finds_rootfs_in_nested_directory(self, tmp_path):
        """Test that rootfs is found in deeply nested directory."""
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)
        rootfs = nested / "squashfs-root"
        rootfs.mkdir()

        result = find_squashfs_rootfs(tmp_path)

        assert result == rootfs

    def test_exits_if_rootfs_not_found(self, tmp_path):
        """Test that it exits if rootfs is not found."""
        with pytest.raises(SystemExit):
            find_squashfs_rootfs(tmp_path)

    def test_ignores_rootfs_if_not_directory(self, tmp_path):
        """Test that non-directory rootfs is ignored."""
        rootfs_file = tmp_path / "squashfs-root"
        rootfs_file.write_text("not a directory")

        with pytest.raises(SystemExit):
            find_squashfs_rootfs(tmp_path)


class TestIntegration:
    """Integration tests for firmware module."""

    def test_full_workflow_with_user_firmware(self, tmp_path):
        """Test full workflow with user-provided firmware."""
        # Create fake firmware
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"test")

        # Create fake extraction
        extract_dir = tmp_path / "extractions" / "firmware.img.extracted"
        rootfs = extract_dir / "squashfs-root"
        rootfs.mkdir(parents=True)

        # Get firmware path
        firmware_path = get_firmware_path(str(firmware), tmp_path)
        assert firmware_path == firmware

        # Extract firmware
        with patch("subprocess.run"):
            extracted = extract_firmware(firmware_path, tmp_path)
            assert extracted == extract_dir

        # Find rootfs
        found_rootfs = find_squashfs_rootfs(extracted)
        assert found_rootfs == rootfs

    def test_full_workflow_with_download(self, tmp_path):
        """Test full workflow with downloaded firmware."""
        # Create fake extraction structure
        firmware_file = DEFAULT_FIRMWARE_URL.split("/")[-1]
        extract_dir = tmp_path / "extractions" / f"{firmware_file}.extracted"
        rootfs = extract_dir / "a" / "b" / "squashfs-root"
        rootfs.mkdir(parents=True)

        # Mock download
        with patch("subprocess.run") as mock_run:

            def create_firmware(*_args, **_kwargs):
                firmware = tmp_path / firmware_file
                firmware.write_bytes(b"test")

            mock_run.side_effect = create_firmware

            # Get firmware path (should download)
            firmware_path = get_firmware_path(None, tmp_path)
            assert firmware_path.name == firmware_file

        # Extract firmware
        with patch("subprocess.run"):
            extracted = extract_firmware(firmware_path, tmp_path)
            assert extracted.name == f"{firmware_file}.extracted"

        # Find rootfs
        found_rootfs = find_squashfs_rootfs(extracted)
        assert found_rootfs == rootfs
