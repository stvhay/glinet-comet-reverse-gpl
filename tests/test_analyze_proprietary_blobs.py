"""Tests for scripts/analyze_proprietary_blobs.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import tomlkit

# Add scripts directory to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from analyze_proprietary_blobs import (
    BinaryAnalysis,
    FirmwareBlob,
    KernelModule,
    LibraryInfo,
    ProprietaryBlobsAnalysis,
    analyze_binary,
    analyze_proprietary_blobs,
    extract_firmware,
    find_all_rockchip_libs,
    find_firmware_blobs,
    find_kernel_modules,
    find_libraries,
    find_rootfs,
    find_wifi_bt_blobs,
    get_file_size,
    has_gpl_string,
    main,
)
from lib.output import output_toml


class TestLibraryInfo:
    """Test LibraryInfo dataclass."""

    def test_library_info_creation(self):
        """Test creating a LibraryInfo."""
        lib = LibraryInfo(
            name="librockchip_mpp.so",
            path="/usr/lib/librockchip_mpp.so",
            size=1024000,
            purpose="Video codec (1024000 bytes)",
        )

        assert lib.name == "librockchip_mpp.so"
        assert lib.path == "/usr/lib/librockchip_mpp.so"
        assert lib.size == 1024000
        assert lib.purpose == "Video codec (1024000 bytes)"

    def test_library_info_is_frozen(self):
        """Test that LibraryInfo is immutable (frozen)."""
        lib = LibraryInfo(
            name="librga.so",
            path="/usr/lib/librga.so",
            size=512000,
            purpose="2D graphics (512000 bytes)",
        )

        with pytest.raises(AttributeError):
            lib.size = 999999  # type: ignore

    def test_library_info_uses_slots(self):
        """Test that LibraryInfo uses __slots__ for memory efficiency."""
        lib = LibraryInfo(
            name="librga.so",
            path="/usr/lib/librga.so",
            size=512000,
            purpose="2D graphics",
        )

        # __slots__ prevents adding arbitrary attributes
        with pytest.raises((AttributeError, TypeError)):
            lib.extra_field = "test"  # type: ignore


class TestFirmwareBlob:
    """Test FirmwareBlob dataclass."""

    def test_firmware_blob_creation(self):
        """Test creating a FirmwareBlob."""
        blob = FirmwareBlob(
            name="fw_bcm43455.bin",
            path="/lib/firmware/brcm/fw_bcm43455.bin",
            size=204800,
        )

        assert blob.name == "fw_bcm43455.bin"
        assert blob.path == "/lib/firmware/brcm/fw_bcm43455.bin"
        assert blob.size == 204800

    def test_firmware_blob_is_frozen(self):
        """Test that FirmwareBlob is immutable (frozen)."""
        blob = FirmwareBlob(
            name="test.bin",
            path="/lib/firmware/test.bin",
            size=1024,
        )

        with pytest.raises(AttributeError):
            blob.name = "other.bin"  # type: ignore

    def test_firmware_blob_uses_slots(self):
        """Test that FirmwareBlob uses __slots__ for memory efficiency."""
        blob = FirmwareBlob(
            name="test.bin",
            path="/lib/firmware/test.bin",
            size=1024,
        )

        # __slots__ prevents adding arbitrary attributes
        with pytest.raises((AttributeError, TypeError)):
            blob.vendor = "Broadcom"  # type: ignore


class TestKernelModule:
    """Test KernelModule dataclass."""

    def test_kernel_module_creation(self):
        """Test creating a KernelModule."""
        module = KernelModule(
            name="rockchip_vpu.ko",
            path="/lib/modules/5.10.110/rockchip_vpu.ko",
            size=102400,
            has_gpl=True,
        )

        assert module.name == "rockchip_vpu.ko"
        assert module.path == "/lib/modules/5.10.110/rockchip_vpu.ko"
        assert module.size == 102400
        assert module.has_gpl is True

    def test_kernel_module_without_gpl(self):
        """Test creating a KernelModule without GPL."""
        module = KernelModule(
            name="proprietary.ko",
            path="/lib/modules/proprietary.ko",
            size=51200,
            has_gpl=False,
        )

        assert module.has_gpl is False

    def test_kernel_module_is_frozen(self):
        """Test that KernelModule is immutable (frozen)."""
        module = KernelModule(
            name="test.ko",
            path="/lib/modules/test.ko",
            size=1024,
            has_gpl=True,
        )

        with pytest.raises(AttributeError):
            module.has_gpl = False  # type: ignore

    def test_kernel_module_uses_slots(self):
        """Test that KernelModule uses __slots__ for memory efficiency."""
        module = KernelModule(
            name="test.ko",
            path="/lib/modules/test.ko",
            size=1024,
            has_gpl=True,
        )

        # __slots__ prevents adding arbitrary attributes
        with pytest.raises((AttributeError, TypeError)):
            module.license = "GPL"  # type: ignore


class TestBinaryAnalysis:
    """Test BinaryAnalysis dataclass."""

    def test_binary_analysis_creation(self):
        """Test creating a BinaryAnalysis."""
        analysis = BinaryAnalysis(
            library_name="librockchip_mpp.so",
            file_type="ELF 64-bit LSB shared object",
            interesting_strings=["Copyright 2023 Rockchip", "Version 1.0"],
        )

        assert analysis.library_name == "librockchip_mpp.so"
        assert analysis.file_type == "ELF 64-bit LSB shared object"
        assert len(analysis.interesting_strings) == 2
        assert "Copyright 2023 Rockchip" in analysis.interesting_strings

    def test_binary_analysis_empty_strings(self):
        """Test creating a BinaryAnalysis with empty strings list."""
        analysis = BinaryAnalysis(
            library_name="test.so",
            file_type="ELF",
        )

        assert analysis.interesting_strings == []

    def test_binary_analysis_is_frozen(self):
        """Test that BinaryAnalysis is immutable (frozen)."""
        analysis = BinaryAnalysis(
            library_name="test.so",
            file_type="ELF",
        )

        with pytest.raises(AttributeError):
            analysis.file_type = "other"  # type: ignore

    def test_binary_analysis_uses_slots(self):
        """Test that BinaryAnalysis uses __slots__ for memory efficiency."""
        analysis = BinaryAnalysis(
            library_name="test.so",
            file_type="ELF",
        )

        # __slots__ prevents adding arbitrary attributes
        with pytest.raises((AttributeError, TypeError)):
            analysis.extra_field = "test"  # type: ignore


class TestProprietaryBlobsAnalysis:
    """Test ProprietaryBlobsAnalysis dataclass."""

    def test_analysis_creation(self):
        """Test creating a ProprietaryBlobsAnalysis."""
        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/squashfs-root",
        )

        assert analysis.firmware_file == "test.img"
        assert analysis.rootfs_path == "/tmp/squashfs-root"
        assert analysis.mpp_libraries == []
        assert analysis.rga_libraries == []
        assert analysis.isp_libraries == []
        assert analysis.npu_libraries == []
        assert analysis.all_rockchip_libs == []
        assert analysis.wifi_bt_blobs == []
        assert analysis.firmware_blobs == []
        assert analysis.kernel_modules == []
        assert analysis.binary_analysis is None
        assert analysis.rockchip_count == 0
        assert analysis.firmware_blob_count == 0
        assert analysis.kernel_module_count == 0

    def test_analysis_is_mutable(self):
        """Test that ProprietaryBlobsAnalysis is mutable (not frozen)."""
        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/root",
        )

        # Should be able to modify fields
        analysis.rockchip_count = 5
        assert analysis.rockchip_count == 5

    def test_add_metadata(self):
        """Test adding source metadata."""
        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/root",
        )

        analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")

        assert analysis._source["firmware_file"] == "filesystem"
        assert analysis._method["firmware_file"] == "Path(firmware).name"

    def test_add_metadata_multiple_fields(self):
        """Test adding metadata for multiple fields."""
        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/root",
        )

        analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")
        analysis.add_metadata("rockchip_count", "filesystem", "count all_rockchip_libs")

        assert len(analysis._source) == 2
        assert len(analysis._method) == 2

    def test_to_dict_excludes_none(self):
        """Test to_dict excludes None values."""
        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/root",
        )

        result = analysis.to_dict()

        assert "firmware_file" in result
        assert "rootfs_path" in result
        assert "binary_analysis" not in result  # Should be excluded (None)

    def test_to_dict_includes_metadata(self):
        """Test to_dict includes source metadata."""
        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/root",
        )
        analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")

        result = analysis.to_dict()

        assert result["firmware_file"] == "test.img"
        assert result["firmware_file_source"] == "filesystem"
        assert result["firmware_file_method"] == "Path(firmware).name"

    def test_to_dict_converts_library_info(self):
        """Test to_dict converts LibraryInfo objects to dicts."""
        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/root",
        )
        analysis.mpp_libraries = [
            LibraryInfo(
                name="librockchip_mpp.so",
                path="/usr/lib/librockchip_mpp.so",
                size=1024000,
                purpose="Video codec (1024000 bytes)",
            )
        ]

        result = analysis.to_dict()

        assert len(result["mpp_libraries"]) == 1
        assert result["mpp_libraries"][0]["name"] == "librockchip_mpp.so"
        assert result["mpp_libraries"][0]["path"] == "/usr/lib/librockchip_mpp.so"
        assert result["mpp_libraries"][0]["size"] == 1024000
        assert result["mpp_libraries"][0]["purpose"] == "Video codec (1024000 bytes)"

    def test_to_dict_converts_firmware_blobs(self):
        """Test to_dict converts FirmwareBlob objects to dicts."""
        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/root",
        )
        analysis.firmware_blobs = [
            FirmwareBlob(
                name="test.bin",
                path="/lib/firmware/test.bin",
                size=2048,
            )
        ]

        result = analysis.to_dict()

        assert len(result["firmware_blobs"]) == 1
        assert result["firmware_blobs"][0]["name"] == "test.bin"
        assert result["firmware_blobs"][0]["path"] == "/lib/firmware/test.bin"
        assert result["firmware_blobs"][0]["size"] == 2048

    def test_to_dict_converts_kernel_modules(self):
        """Test to_dict converts KernelModule objects to dicts."""
        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/root",
        )
        analysis.kernel_modules = [
            KernelModule(
                name="test.ko",
                path="/lib/modules/test.ko",
                size=1024,
                has_gpl=True,
            )
        ]

        result = analysis.to_dict()

        assert len(result["kernel_modules"]) == 1
        assert result["kernel_modules"][0]["name"] == "test.ko"
        assert result["kernel_modules"][0]["path"] == "/lib/modules/test.ko"
        assert result["kernel_modules"][0]["size"] == 1024
        assert result["kernel_modules"][0]["has_gpl"] is True

    def test_to_dict_converts_binary_analysis(self):
        """Test to_dict converts BinaryAnalysis object to dict."""
        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/root",
        )
        analysis.binary_analysis = BinaryAnalysis(
            library_name="test.so",
            file_type="ELF",
            interesting_strings=["Version 1.0", "Copyright 2023"],
        )

        result = analysis.to_dict()

        assert "binary_analysis" in result
        assert result["binary_analysis"]["library_name"] == "test.so"
        assert result["binary_analysis"]["file_type"] == "ELF"
        assert len(result["binary_analysis"]["interesting_strings"]) == 2

    def test_to_dict_excludes_internal_fields(self):
        """Test to_dict excludes internal fields (starting with _)."""
        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/root",
        )
        analysis.add_metadata("firmware_file", "test", "test method")

        result = analysis.to_dict()

        assert "_source" not in result
        assert "_method" not in result


class TestGetFileSize:
    """Test get_file_size function."""

    def test_get_file_size_success(self, tmp_path):
        """Test getting file size."""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"x" * 1024)

        size = get_file_size(test_file)

        assert size == 1024

    def test_get_file_size_empty_file(self, tmp_path):
        """Test getting size of empty file."""
        test_file = tmp_path / "empty.bin"
        test_file.write_bytes(b"")

        size = get_file_size(test_file)

        assert size == 0

    def test_get_file_size_large_file(self, tmp_path):
        """Test getting size of large file."""
        test_file = tmp_path / "large.bin"
        test_file.write_bytes(b"x" * 10_000_000)  # 10 MB

        size = get_file_size(test_file)

        assert size == 10_000_000


class TestFindLibraries:
    """Test find_libraries function."""

    def test_find_libraries_success(self, tmp_path):
        """Test finding libraries matching patterns."""
        rootfs = tmp_path / "rootfs"
        lib_dir = rootfs / "usr/lib"
        lib_dir.mkdir(parents=True)

        # Create test libraries
        (lib_dir / "librockchip_mpp.so").write_bytes(b"x" * 1024)
        (lib_dir / "libmpp.so.1").write_bytes(b"x" * 2048)

        patterns = ["librockchip_mpp.so*", "libmpp.so*"]
        result = find_libraries(rootfs, patterns, "Video codec")

        assert len(result) == 2
        assert any(lib.name == "librockchip_mpp.so" for lib in result)
        assert any(lib.name == "libmpp.so" for lib in result)

    def test_find_libraries_with_versions(self, tmp_path):
        """Test finding versioned libraries (e.g., .so.1.2.3)."""
        rootfs = tmp_path / "rootfs"
        lib_dir = rootfs / "usr/lib"
        lib_dir.mkdir(parents=True)

        (lib_dir / "librga.so.1.2.3").write_bytes(b"x" * 4096)

        patterns = ["librga.so*"]
        result = find_libraries(rootfs, patterns, "2D graphics")

        assert len(result) == 1
        assert result[0].name == "librga.so"  # Base name without version
        assert result[0].size == 4096

    def test_find_libraries_no_matches(self, tmp_path):
        """Test finding libraries when no matches exist."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        patterns = ["librockchip_mpp.so*"]
        result = find_libraries(rootfs, patterns, "Video codec")

        assert result == []

    def test_find_libraries_multiple_matches_takes_first(self, tmp_path):
        """Test that only first match per pattern is returned."""
        rootfs = tmp_path / "rootfs"
        lib_dir1 = rootfs / "usr/lib"
        lib_dir2 = rootfs / "usr/local/lib"
        lib_dir1.mkdir(parents=True)
        lib_dir2.mkdir(parents=True)

        # Create duplicate libraries in different locations
        (lib_dir1 / "librga.so").write_bytes(b"x" * 1024)
        (lib_dir2 / "librga.so").write_bytes(b"x" * 2048)

        patterns = ["librga.so*"]
        result = find_libraries(rootfs, patterns, "2D graphics")

        # Should only return one library (first match)
        assert len(result) == 1

    def test_find_libraries_purpose_includes_size(self, tmp_path):
        """Test that purpose includes file size."""
        rootfs = tmp_path / "rootfs"
        lib_dir = rootfs / "usr/lib"
        lib_dir.mkdir(parents=True)

        (lib_dir / "librga.so").write_bytes(b"x" * 512000)

        patterns = ["librga.so*"]
        result = find_libraries(rootfs, patterns, "2D graphics")

        assert len(result) == 1
        assert "512000 bytes" in result[0].purpose


class TestFindAllRockchipLibs:
    """Test find_all_rockchip_libs function."""

    def test_find_all_rockchip_libs_success(self, tmp_path):
        """Test finding all Rockchip libraries."""
        rootfs = tmp_path / "rootfs"
        lib_dir = rootfs / "usr/lib"
        lib_dir.mkdir(parents=True)

        # Create various Rockchip libraries
        (lib_dir / "librockchip_mpp.so").write_bytes(b"x" * 1024)
        (lib_dir / "librk_aiq.so").write_bytes(b"x" * 2048)
        (lib_dir / "librga.so").write_bytes(b"x" * 4096)

        result = find_all_rockchip_libs(rootfs)

        assert len(result) == 3
        assert "/usr/lib/librockchip_mpp.so" in result
        assert "/usr/lib/librk_aiq.so" in result
        assert "/usr/lib/librga.so" in result

    def test_find_all_rockchip_libs_sorted(self, tmp_path):
        """Test that results are sorted."""
        rootfs = tmp_path / "rootfs"
        lib_dir = rootfs / "usr/lib"
        lib_dir.mkdir(parents=True)

        # Create files in non-alphabetical order
        (lib_dir / "libz_mpp.so").write_bytes(b"x" * 1024)
        (lib_dir / "liba_rga.so").write_bytes(b"x" * 2048)

        result = find_all_rockchip_libs(rootfs)

        # Should be sorted
        assert result == sorted(result)

    def test_find_all_rockchip_libs_excludes_pyc(self, tmp_path):
        """Test that .pyc files are excluded."""
        rootfs = tmp_path / "rootfs"
        lib_dir = rootfs / "usr/lib"
        lib_dir.mkdir(parents=True)

        (lib_dir / "librockchip_mpp.so").write_bytes(b"x" * 1024)
        (lib_dir / "librockchip.pyc").write_bytes(b"x" * 2048)

        result = find_all_rockchip_libs(rootfs)

        assert len(result) == 1
        assert "/usr/lib/librockchip_mpp.so" in result
        assert not any(".pyc" in path for path in result)

    def test_find_all_rockchip_libs_no_duplicates(self, tmp_path):
        """Test that duplicate paths are removed."""
        rootfs = tmp_path / "rootfs"
        lib_dir = rootfs / "usr/lib"
        lib_dir.mkdir(parents=True)

        # Create a library that matches multiple patterns
        (lib_dir / "librockchip_mpp.so").write_bytes(b"x" * 1024)

        result = find_all_rockchip_libs(rootfs)

        # Should only appear once even if it matches multiple patterns
        assert result.count("/usr/lib/librockchip_mpp.so") == 1

    def test_find_all_rockchip_libs_none_found(self, tmp_path):
        """Test finding when no Rockchip libraries exist."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        result = find_all_rockchip_libs(rootfs)

        assert result == []


class TestFindWifiBtBlobs:
    """Test find_wifi_bt_blobs function."""

    def test_find_wifi_bt_blobs_broadcom(self, tmp_path):
        """Test finding Broadcom WiFi/BT blobs."""
        rootfs = tmp_path / "rootfs"
        fw_dir = rootfs / "lib/firmware/brcm"
        fw_dir.mkdir(parents=True)

        (fw_dir / "fw_bcm43455.bin").write_bytes(b"x" * 204800)
        (fw_dir / "nvram_43455.txt").write_bytes(b"x" * 1024)

        result = find_wifi_bt_blobs(rootfs)

        assert len(result) == 2
        blob_names = [blob.name for blob in result]
        assert "fw_bcm43455.bin" in blob_names
        assert "nvram_43455.txt" in blob_names

    def test_find_wifi_bt_blobs_realtek(self, tmp_path):
        """Test finding Realtek WiFi blobs."""
        rootfs = tmp_path / "rootfs"
        fw_dir = rootfs / "lib/firmware"
        fw_dir.mkdir(parents=True)

        (fw_dir / "rtl8822cu_fw.bin").write_bytes(b"x" * 102400)

        result = find_wifi_bt_blobs(rootfs)

        assert len(result) == 1
        assert result[0].name == "rtl8822cu_fw.bin"

    def test_find_wifi_bt_blobs_none_found(self, tmp_path):
        """Test finding when no WiFi/BT blobs exist."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        result = find_wifi_bt_blobs(rootfs)

        assert result == []

    def test_find_wifi_bt_blobs_includes_size(self, tmp_path):
        """Test that blob size is correctly captured."""
        rootfs = tmp_path / "rootfs"
        fw_dir = rootfs / "lib/firmware"
        fw_dir.mkdir(parents=True)

        (fw_dir / "fw_bcm43455.bin").write_bytes(b"x" * 204800)

        result = find_wifi_bt_blobs(rootfs)

        assert len(result) == 1
        assert result[0].size == 204800


class TestFindFirmwareBlobs:
    """Test find_firmware_blobs function."""

    def test_find_firmware_blobs_success(self, tmp_path):
        """Test finding firmware blobs in /lib/firmware."""
        rootfs = tmp_path / "rootfs"
        fw_dir = rootfs / "lib/firmware"
        fw_dir.mkdir(parents=True)

        (fw_dir / "blob1.bin").write_bytes(b"x" * 1024)
        (fw_dir / "blob2.bin").write_bytes(b"x" * 2048)

        result = find_firmware_blobs(rootfs)

        assert len(result) == 2
        blob_names = [blob.name for blob in result]
        assert "blob1.bin" in blob_names
        assert "blob2.bin" in blob_names

    def test_find_firmware_blobs_nested(self, tmp_path):
        """Test finding firmware blobs in nested directories."""
        rootfs = tmp_path / "rootfs"
        fw_dir = rootfs / "lib/firmware/vendor/subdir"
        fw_dir.mkdir(parents=True)

        (fw_dir / "nested_blob.bin").write_bytes(b"x" * 4096)

        result = find_firmware_blobs(rootfs)

        assert len(result) == 1
        assert result[0].name == "nested_blob.bin"
        assert "/lib/firmware/vendor/subdir/nested_blob.bin" in result[0].path

    def test_find_firmware_blobs_directory_not_exists(self, tmp_path):
        """Test finding when /lib/firmware doesn't exist."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        result = find_firmware_blobs(rootfs)

        assert result == []

    def test_find_firmware_blobs_limited_to_50(self, tmp_path):
        """Test that output is limited to 50 blobs."""
        rootfs = tmp_path / "rootfs"
        fw_dir = rootfs / "lib/firmware"
        fw_dir.mkdir(parents=True)

        # Create 60 blobs
        for i in range(60):
            (fw_dir / f"blob{i:03d}.bin").write_bytes(b"x" * 1024)

        result = find_firmware_blobs(rootfs)

        # Should be limited to 50
        assert len(result) == 50


class TestHasGplString:
    """Test has_gpl_string function."""

    @patch("subprocess.run")
    def test_has_gpl_string_found(self, mock_run, tmp_path):
        """Test detecting GPL string in kernel module."""
        ko_file = tmp_path / "test.ko"
        ko_file.write_bytes(b"dummy")

        # Mock subprocess.run to return GPL string
        mock_run.return_value = MagicMock(
            stdout="some text\nlicense=GPL\nmore text\n",
            returncode=0,
        )

        result = has_gpl_string(ko_file)

        assert result is True
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_has_gpl_string_case_insensitive(self, mock_run, tmp_path):
        """Test that GPL detection is case-insensitive."""
        ko_file = tmp_path / "test.ko"
        ko_file.write_bytes(b"dummy")

        # Mock with lowercase "gpl"
        mock_run.return_value = MagicMock(
            stdout="some text\nlicense=gpl\nmore text\n",
            returncode=0,
        )

        result = has_gpl_string(ko_file)

        assert result is True

    @patch("subprocess.run")
    def test_has_gpl_string_not_found(self, mock_run, tmp_path):
        """Test when GPL string is not found."""
        ko_file = tmp_path / "test.ko"
        ko_file.write_bytes(b"dummy")

        mock_run.return_value = MagicMock(
            stdout="some text\nproprietary\nmore text\n",
            returncode=0,
        )

        result = has_gpl_string(ko_file)

        assert result is False

    @patch("subprocess.run")
    def test_has_gpl_string_exception(self, mock_run, tmp_path):
        """Test that exceptions are handled gracefully."""
        ko_file = tmp_path / "test.ko"
        ko_file.write_bytes(b"dummy")

        mock_run.side_effect = Exception("strings command failed")

        result = has_gpl_string(ko_file)

        assert result is False


class TestFindKernelModules:
    """Test find_kernel_modules function."""

    @patch("analyze_proprietary_blobs.has_gpl_string")
    def test_find_kernel_modules_success(self, mock_has_gpl, tmp_path):
        """Test finding kernel modules."""
        rootfs = tmp_path / "rootfs"
        modules_dir = rootfs / "lib/modules/5.10.110"
        modules_dir.mkdir(parents=True)

        (modules_dir / "rockchip_vpu.ko").write_bytes(b"x" * 102400)
        (modules_dir / "dwc3.ko").write_bytes(b"x" * 51200)

        # Mock GPL detection - return True for all
        mock_has_gpl.return_value = True

        result = find_kernel_modules(rootfs)

        assert len(result) == 2
        # Verify both modules are found (order may vary)
        module_names = {mod.name for mod in result}
        assert "rockchip_vpu.ko" in module_names
        assert "dwc3.ko" in module_names
        # All should have has_gpl=True due to mock
        assert all(mod.has_gpl for mod in result)

    @patch("analyze_proprietary_blobs.has_gpl_string")
    def test_find_kernel_modules_limited_to_30(self, mock_has_gpl, tmp_path):
        """Test that output is limited to 30 modules."""
        rootfs = tmp_path / "rootfs"
        modules_dir = rootfs / "lib/modules/5.10.110"
        modules_dir.mkdir(parents=True)

        # Create 40 modules
        for i in range(40):
            (modules_dir / f"module{i:03d}.ko").write_bytes(b"x" * 1024)

        mock_has_gpl.return_value = True

        result = find_kernel_modules(rootfs)

        # Should be limited to 30
        assert len(result) == 30

    def test_find_kernel_modules_none_found(self, tmp_path):
        """Test finding when no kernel modules exist."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        result = find_kernel_modules(rootfs)

        assert result == []


class TestAnalyzeBinary:
    """Test analyze_binary function."""

    @patch("subprocess.run")
    def test_analyze_binary_success(self, mock_run, tmp_path):
        """Test analyzing a binary library."""
        lib_file = tmp_path / "librockchip_mpp.so"
        lib_file.write_bytes(b"dummy")

        # Mock file and strings commands
        def mock_subprocess(*args, **_kwargs):
            cmd = args[0]
            if cmd[0] == "file":
                return MagicMock(
                    stdout="ELF 64-bit LSB shared object, ARM aarch64, version 1 (SYSV)",
                    returncode=0,
                )
            if cmd[0] == "strings":
                return MagicMock(
                    stdout=(
                        "random text\n"
                        "Copyright 2023 Rockchip\n"
                        "Version 1.0\n"
                        "Build date: 2023-12-15\n"
                        "more text\n"
                    ),
                    returncode=0,
                )
            return MagicMock(returncode=1)

        mock_run.side_effect = mock_subprocess

        result = analyze_binary(lib_file)

        assert result is not None
        assert result.library_name == "librockchip_mpp.so"
        assert "ELF 64-bit LSB shared object" in result.file_type
        assert len(result.interesting_strings) == 3
        assert "Copyright 2023 Rockchip" in result.interesting_strings
        assert "Version 1.0" in result.interesting_strings

    @patch("subprocess.run")
    def test_analyze_binary_limited_strings(self, mock_run, tmp_path):
        """Test that interesting strings are limited to MAX_INTERESTING_STRINGS."""
        lib_file = tmp_path / "test.so"
        lib_file.write_bytes(b"dummy")

        # Create many interesting strings
        strings = "\n".join([f"Copyright {i}" for i in range(100)])

        def mock_subprocess(*args, **_kwargs):
            cmd = args[0]
            if cmd[0] == "file":
                return MagicMock(stdout="ELF", returncode=0)
            if cmd[0] == "strings":
                return MagicMock(stdout=strings, returncode=0)
            return MagicMock(returncode=1)

        mock_run.side_effect = mock_subprocess

        result = analyze_binary(lib_file)

        assert result is not None
        # Should be limited to MAX_INTERESTING_STRINGS (20)
        assert len(result.interesting_strings) == 20

    def test_analyze_binary_file_not_exists(self, tmp_path):
        """Test analyzing when file doesn't exist."""
        lib_file = tmp_path / "nonexistent.so"

        result = analyze_binary(lib_file)

        assert result is None

    @patch("subprocess.run")
    def test_analyze_binary_file_command_fails(self, mock_run, tmp_path):
        """Test when file command fails."""
        lib_file = tmp_path / "test.so"
        lib_file.write_bytes(b"dummy")

        mock_run.side_effect = Exception("file command failed")

        result = analyze_binary(lib_file)

        assert result is not None
        assert result.file_type == "unknown"

    @patch("subprocess.run")
    def test_analyze_binary_strings_command_fails(self, mock_run, tmp_path):
        """Test when strings command fails."""
        lib_file = tmp_path / "test.so"
        lib_file.write_bytes(b"dummy")

        def mock_subprocess(*args, **_kwargs):
            cmd = args[0]
            if cmd[0] == "file":
                return MagicMock(stdout="ELF", returncode=0)
            if cmd[0] == "strings":
                raise Exception("strings command failed")
            return MagicMock(returncode=1)

        mock_run.side_effect = mock_subprocess

        result = analyze_binary(lib_file)

        assert result is not None
        assert result.interesting_strings == []


class TestOutputToml:
    """Test output_toml function via lib.output."""

    def test_toml_output_valid(self):
        """Test that TOML output is valid."""
        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/squashfs-root",
        )
        analysis.rockchip_count = 5
        analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")

        toml_str = output_toml(
            analysis, title="Test", simple_fields=["firmware_file", "rockchip_count"]
        )

        # Should be valid TOML
        parsed = tomlkit.loads(toml_str)
        assert parsed["firmware_file"] == "test.img"
        assert parsed["rockchip_count"] == 5

    def test_toml_includes_header(self):
        """Test that TOML includes header comments."""

        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/root",
        )

        toml_str = output_toml(analysis, title="Test Title")

        assert "# Test Title" in toml_str
        assert "# Generated:" in toml_str

    def test_toml_includes_source_comments(self):
        """Test that TOML includes source metadata as comments."""

        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/root",
        )
        analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")

        toml_str = output_toml(analysis, title="Test", simple_fields=["firmware_file"])

        assert "# Source: filesystem" in toml_str
        assert "# Method: Path(firmware).name" in toml_str

    def test_toml_truncates_long_methods(self):
        """Test that long method descriptions are truncated."""

        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/root",
        )
        long_method = "x" * 100  # 100 characters
        analysis.add_metadata("firmware_file", "test", long_method)

        toml_str = output_toml(analysis, title="Test", simple_fields=["firmware_file"])

        # Should be truncated with "..."
        assert "..." in toml_str
        assert long_method not in toml_str

    def test_toml_excludes_metadata_fields(self):
        """Test that _source and _method suffix fields are not in final TOML."""

        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/root",
        )
        analysis.add_metadata("firmware_file", "test", "test method")

        toml_str = output_toml(analysis, title="Test", simple_fields=["firmware_file"])
        parsed = tomlkit.loads(toml_str)

        # Metadata should be in comments, not as fields
        assert "firmware_file_source" not in parsed
        assert "firmware_file_method" not in parsed

    def test_toml_includes_library_arrays(self):
        """Test that library arrays are included in TOML."""

        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/root",
        )
        analysis.mpp_libraries = [
            LibraryInfo(
                name="librockchip_mpp.so",
                path="/usr/lib/librockchip_mpp.so",
                size=1024000,
                purpose="Video codec (1024000 bytes)",
            )
        ]

        toml_str = output_toml(analysis, title="Test", complex_fields=["mpp_libraries"])
        parsed = tomlkit.loads(toml_str)

        assert len(parsed["mpp_libraries"]) == 1
        assert parsed["mpp_libraries"][0]["name"] == "librockchip_mpp.so"
        assert parsed["mpp_libraries"][0]["size"] == 1024000

    def test_toml_includes_string_arrays(self):
        """Test that string arrays (all_rockchip_libs) are included."""

        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/root",
        )
        analysis.all_rockchip_libs = [
            "/usr/lib/librockchip_mpp.so",
            "/usr/lib/librga.so",
        ]

        toml_str = output_toml(analysis, title="Test", complex_fields=["all_rockchip_libs"])
        parsed = tomlkit.loads(toml_str)

        assert len(parsed["all_rockchip_libs"]) == 2
        assert "/usr/lib/librockchip_mpp.so" in parsed["all_rockchip_libs"]

    def test_toml_validates_output(self):
        """Test that output_toml validates generated TOML by parsing it."""

        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/root",
        )

        # Should not raise any exceptions
        toml_str = output_toml(analysis, title="Test")

        # Should be parseable
        parsed = tomlkit.loads(toml_str)
        assert isinstance(parsed, dict)


class TestIntegration:
    """Integration tests with realistic data."""

    @patch("analyze_proprietary_blobs.has_gpl_string")
    @patch("subprocess.run")
    def test_realistic_proprietary_blobs_analysis(  # noqa: PLR0915
        self, mock_run, mock_has_gpl, tmp_path
    ):
        """Test complete analysis workflow with realistic filesystem."""
        # Create realistic filesystem structure
        rootfs = tmp_path / "squashfs-root"

        # Create Rockchip libraries
        lib_dir = rootfs / "usr/lib"
        lib_dir.mkdir(parents=True)
        (lib_dir / "librockchip_mpp.so").write_bytes(b"x" * 1024000)
        (lib_dir / "librga.so.1.2.3").write_bytes(b"x" * 512000)
        (lib_dir / "librkaiq.so").write_bytes(b"x" * 256000)

        # Create WiFi/BT blobs
        fw_dir = rootfs / "lib/firmware/brcm"
        fw_dir.mkdir(parents=True)
        (fw_dir / "fw_bcm43455.bin").write_bytes(b"x" * 204800)

        # Create firmware blobs
        fw_base = rootfs / "lib/firmware"
        (fw_base / "blob1.bin").write_bytes(b"x" * 1024)
        (fw_base / "blob2.bin").write_bytes(b"x" * 2048)

        # Create kernel modules
        modules_dir = rootfs / "lib/modules/5.10.110"
        modules_dir.mkdir(parents=True)
        (modules_dir / "rockchip_vpu.ko").write_bytes(b"x" * 102400)
        (modules_dir / "dwc3.ko").write_bytes(b"x" * 51200)

        # Mock GPL detection
        mock_has_gpl.side_effect = [True, False]

        # Mock binary analysis
        def mock_subprocess(*args, **_kwargs):
            cmd = args[0]
            if cmd[0] == "file":
                return MagicMock(
                    stdout="ELF 64-bit LSB shared object",
                    returncode=0,
                )
            if cmd[0] == "strings":
                return MagicMock(
                    stdout="Copyright 2023 Rockchip\nVersion 1.0\n",
                    returncode=0,
                )
            return MagicMock(returncode=1)

        mock_run.side_effect = mock_subprocess

        # Create analysis object and populate it
        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path=str(rootfs),
        )

        # Find MPP libraries
        analysis.mpp_libraries = find_libraries(
            rootfs, ["librockchip_mpp.so*", "libmpp.so*"], "Video codec"
        )

        # Find RGA libraries
        analysis.rga_libraries = find_libraries(rootfs, ["librga.so*"], "2D graphics")

        # Find ISP libraries
        analysis.isp_libraries = find_libraries(
            rootfs, ["librkaiq.so*", "librkisp.so*"], "Camera ISP"
        )

        # Find all Rockchip libs
        analysis.all_rockchip_libs = find_all_rockchip_libs(rootfs)

        # Find WiFi/BT blobs
        analysis.wifi_bt_blobs = find_wifi_bt_blobs(rootfs)

        # Find firmware blobs
        analysis.firmware_blobs = find_firmware_blobs(rootfs)

        # Find kernel modules
        analysis.kernel_modules = find_kernel_modules(rootfs)

        # Binary analysis
        if analysis.mpp_libraries:
            mpp_lib_path = rootfs / analysis.mpp_libraries[0].path.lstrip("/")
            analysis.binary_analysis = analyze_binary(mpp_lib_path)

        # Calculate counts
        analysis.rockchip_count = len(analysis.all_rockchip_libs)
        analysis.firmware_blob_count = len(analysis.firmware_blobs)
        analysis.kernel_module_count = len(analysis.kernel_modules)

        # Verify results
        assert len(analysis.mpp_libraries) == 1
        assert len(analysis.rga_libraries) == 1
        assert len(analysis.isp_libraries) == 1
        assert analysis.rockchip_count == 3
        assert len(analysis.wifi_bt_blobs) == 1
        assert len(analysis.firmware_blobs) == 3
        assert len(analysis.kernel_modules) == 2
        assert analysis.binary_analysis is not None

        # Verify TOML output

        toml_str = output_toml(
            analysis,
            title="Test",
            simple_fields=["firmware_file", "rockchip_count"],
            complex_fields=["mpp_libraries", "kernel_modules"],
        )
        parsed = tomlkit.loads(toml_str)

        assert parsed["firmware_file"] == "test.img"
        assert parsed["rockchip_count"] == 3
        assert len(parsed["mpp_libraries"]) == 1
        assert len(parsed["kernel_modules"]) == 2

    def test_json_output_format(self):
        """Test JSON output format conversion."""
        mpp_lib = LibraryInfo(
            name="librockchip_mpp.so",
            path="/usr/lib/librockchip_mpp.so",
            size=1024000,
            purpose="Video codec (1024000 bytes)",
        )

        blob = FirmwareBlob(
            name="fw_bcm43455.bin",
            path="/lib/firmware/brcm/fw_bcm43455.bin",
            size=204800,
        )

        module = KernelModule(
            name="rockchip_vpu.ko",
            path="/lib/modules/5.10.110/rockchip_vpu.ko",
            size=102400,
            has_gpl=True,
        )

        binary_analysis = BinaryAnalysis(
            library_name="librockchip_mpp.so",
            file_type="ELF 64-bit LSB shared object",
            interesting_strings=["Copyright 2023 Rockchip", "Version 1.0"],
        )

        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/squashfs-root",
            mpp_libraries=[mpp_lib],
            wifi_bt_blobs=[blob],
            kernel_modules=[module],
            binary_analysis=binary_analysis,
            all_rockchip_libs=["/usr/lib/librockchip_mpp.so"],
            rockchip_count=1,
        )

        analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")

        # Convert to dict and JSON
        result_dict = analysis.to_dict()
        json_str = json.dumps(result_dict, indent=2)

        # Parse back
        parsed_json = json.loads(json_str)

        # Verify structure
        assert parsed_json["firmware_file"] == "test.img"
        assert len(parsed_json["mpp_libraries"]) == 1
        assert parsed_json["mpp_libraries"][0]["name"] == "librockchip_mpp.so"
        assert parsed_json["mpp_libraries"][0]["size"] == 1024000
        assert len(parsed_json["wifi_bt_blobs"]) == 1
        assert len(parsed_json["kernel_modules"]) == 1
        assert parsed_json["kernel_modules"][0]["has_gpl"] is True
        assert "binary_analysis" in parsed_json
        assert parsed_json["binary_analysis"]["library_name"] == "librockchip_mpp.so"
        assert len(parsed_json["binary_analysis"]["interesting_strings"]) == 2
        assert parsed_json["firmware_file_source"] == "filesystem"


class TestExtractFirmware:
    """Test extract_firmware function."""

    @patch("subprocess.run")
    def test_extract_firmware_creates_directory(self, mock_run, tmp_path):
        """Test that extract_firmware creates extraction directory."""
        firmware = tmp_path / "test.img"
        firmware.write_bytes(b"dummy firmware")
        work_dir = tmp_path / "work"

        mock_run.return_value = MagicMock(returncode=0)

        extract_dir = extract_firmware(firmware, work_dir)

        # Verify binwalk was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "binwalk" in call_args[0][0]
        assert "-e" in call_args[0][0]

        # Verify expected path
        expected = work_dir / "extractions" / f"{firmware.name}.extracted"
        assert extract_dir == expected

    @patch("subprocess.run")
    def test_extract_firmware_reuses_existing(self, mock_run, tmp_path):
        """Test that existing extraction directory is reused."""
        firmware = tmp_path / "test.img"
        firmware.write_bytes(b"dummy firmware")
        work_dir = tmp_path / "work"

        # Create extraction directory
        extract_dir = work_dir / "extractions" / f"{firmware.name}.extracted"
        extract_dir.mkdir(parents=True)

        result = extract_firmware(firmware, work_dir)

        # Should not call binwalk if directory exists
        mock_run.assert_not_called()
        assert result == extract_dir


class TestFindRootfs:
    """Test find_rootfs function."""

    def test_find_rootfs_success(self, tmp_path):
        """Test finding squashfs-root directory."""
        extract_dir = tmp_path / "extractions"
        squashfs_root = extract_dir / "12345" / "squashfs-root"
        squashfs_root.mkdir(parents=True)

        result = find_rootfs(extract_dir)

        assert result == squashfs_root

    def test_find_rootfs_nested(self, tmp_path):
        """Test finding nested squashfs-root directory."""
        extract_dir = tmp_path / "extractions"
        squashfs_root = extract_dir / "a" / "b" / "c" / "squashfs-root"
        squashfs_root.mkdir(parents=True)

        result = find_rootfs(extract_dir)

        assert result == squashfs_root

    def test_find_rootfs_not_found(self, tmp_path):
        """Test that missing squashfs-root causes SystemExit."""
        extract_dir = tmp_path / "extractions"
        extract_dir.mkdir(parents=True)

        with pytest.raises(SystemExit) as exc_info:
            find_rootfs(extract_dir)

        assert exc_info.value.code == 1


class TestAnalyzeProprietaryBlobs:
    """Test analyze_proprietary_blobs function."""

    @patch("analyze_proprietary_blobs.has_gpl_string")
    @patch("subprocess.run")
    def test_analyze_proprietary_blobs_integration(self, mock_run, mock_has_gpl, tmp_path):
        """Test analyze_proprietary_blobs with mocked filesystem."""
        # Create firmware file
        firmware = tmp_path / "test.img"
        firmware.write_bytes(b"dummy firmware")

        # Create extraction directory structure
        work_dir = tmp_path / "work"
        extract_dir = work_dir / "extractions" / f"{firmware.name}.extracted"
        rootfs = extract_dir / "12345" / "squashfs-root"
        rootfs.mkdir(parents=True)

        # Create Rockchip libraries
        lib_dir = rootfs / "usr/lib"
        lib_dir.mkdir(parents=True)
        (lib_dir / "librockchip_mpp.so").write_bytes(b"x" * 1024000)
        (lib_dir / "librga.so").write_bytes(b"x" * 512000)

        # Create WiFi/BT blobs
        fw_dir = rootfs / "lib/firmware/brcm"
        fw_dir.mkdir(parents=True)
        (fw_dir / "fw_bcm43455.bin").write_bytes(b"x" * 204800)

        # Create kernel modules
        modules_dir = rootfs / "lib/modules/5.10.110"
        modules_dir.mkdir(parents=True)
        (modules_dir / "rockchip_vpu.ko").write_bytes(b"x" * 102400)

        # Mock GPL detection
        mock_has_gpl.return_value = True

        # Mock subprocess (binwalk and binary analysis)
        def mock_subprocess(*args, **_kwargs):
            cmd = args[0]
            if isinstance(cmd, list) and "binwalk" in cmd:
                return MagicMock(returncode=0)
            if isinstance(cmd, list) and cmd[0] == "file":
                return MagicMock(stdout="ELF 64-bit LSB shared object", returncode=0)
            if isinstance(cmd, list) and cmd[0] == "strings":
                return MagicMock(stdout="Copyright 2023 Rockchip\nVersion 1.0\n", returncode=0)
            return MagicMock(returncode=0)

        mock_run.side_effect = mock_subprocess

        # Run analysis
        analysis = analyze_proprietary_blobs(str(firmware), work_dir)

        # Verify results
        assert analysis.firmware_file == firmware.name
        assert analysis.rockchip_count > 0
        assert len(analysis.all_rockchip_libs) > 0
        assert len(analysis.mpp_libraries) > 0 or len(analysis.rga_libraries) > 0
        assert analysis.binary_analysis is not None

    def test_analyze_proprietary_blobs_nonexistent_firmware(self, tmp_path):
        """Test that nonexistent firmware file causes SystemExit."""
        firmware = tmp_path / "nonexistent.img"
        work_dir = tmp_path / "work"

        with pytest.raises(SystemExit) as exc_info:
            analyze_proprietary_blobs(str(firmware), work_dir)

        assert exc_info.value.code == 1


class TestMain:
    """Test main function."""

    @patch("analyze_proprietary_blobs.get_firmware_path")
    @patch("analyze_proprietary_blobs.analyze_proprietary_blobs")
    @patch("sys.argv", ["analyze_proprietary_blobs.py", "test.img", "--format", "toml"])
    def test_main_with_firmware_toml_format(
        self, mock_analyze, mock_get_firmware, capsys
    ):
        """Test main function with firmware file and TOML format."""
        # Mock firmware path
        mock_get_firmware.return_value = Path("test.img")

        # Create mock analysis result
        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/squashfs-root",
            rockchip_count=5,
        )
        analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")

        mock_analyze.return_value = analysis

        # Run main
        main()

        # Verify analyze_proprietary_blobs was called
        mock_analyze.assert_called_once()

        # Capture output
        captured = capsys.readouterr()

        # Verify TOML output
        assert "# Proprietary blobs analysis" in captured.out
        assert "firmware_file" in captured.out
        assert "rockchip_count" in captured.out

        # Verify it's valid TOML
        parsed = tomlkit.loads(captured.out)
        assert parsed["firmware_file"] == "test.img"
        assert parsed["rockchip_count"] == 5

    @patch("analyze_proprietary_blobs.get_firmware_path")
    @patch("analyze_proprietary_blobs.analyze_proprietary_blobs")
    @patch("sys.argv", ["analyze_proprietary_blobs.py", "test.img", "--format", "json"])
    def test_main_with_firmware_json_format(
        self, mock_analyze, mock_get_firmware, capsys
    ):
        """Test main function with firmware file and JSON format."""
        # Mock firmware path
        mock_get_firmware.return_value = Path("test.img")

        # Create mock analysis result
        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/squashfs-root",
            rockchip_count=5,
        )
        analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")

        mock_analyze.return_value = analysis

        # Run main
        main()

        # Capture output
        captured = capsys.readouterr()

        # Verify JSON output
        parsed_json = json.loads(captured.out)
        assert parsed_json["firmware_file"] == "test.img"
        assert parsed_json["rockchip_count"] == 5
        assert parsed_json["firmware_file_source"] == "filesystem"

    @patch("analyze_proprietary_blobs.get_firmware_path")
    @patch("analyze_proprietary_blobs.analyze_proprietary_blobs")
    @patch("sys.argv", ["analyze_proprietary_blobs.py", "test.img"])
    def test_main_without_format_arg(self, mock_analyze, mock_get_firmware, capsys):
        """Test main function without format argument (defaults to TOML)."""
        # Mock firmware path
        mock_get_firmware.return_value = Path("test.img")

        # Create mock analysis result
        analysis = ProprietaryBlobsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/squashfs-root",
            rockchip_count=3,
        )

        mock_analyze.return_value = analysis

        # Run main
        main()

        # Capture output
        captured = capsys.readouterr()

        # Should default to TOML format
        assert "# Proprietary blobs analysis" in captured.out

        # Verify it's valid TOML
        parsed = tomlkit.loads(captured.out)
        assert parsed["firmware_file"] == "test.img"

    @patch("sys.argv", ["analyze_proprietary_blobs.py", "--format", "invalid"])
    def test_main_invalid_format(self):
        """Test main function with invalid format argument."""
        with pytest.raises(SystemExit) as exc_info:
            main()

        # argparse raises SystemExit with code 2 for invalid arguments
        assert exc_info.value.code == 2
