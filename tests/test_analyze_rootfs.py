"""Tests for scripts/analyze_rootfs.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import tomlkit

# Add scripts directory to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from analyze_rootfs import (
    COMPLEX_FIELDS,
    SIMPLE_FIELDS,
    DetectedLicense,
    GplBinary,
    KernelModule,
    LicenseFile,
    RootfsAnalysis,
    SharedLibrary,
    analyze_busybox,
    analyze_gpl_binaries,
    analyze_kernel_modules,
    analyze_license_files,
    analyze_shared_libraries,
    detect_library_licenses,
    extract_kernel_version,
    find_squashfs_rootfs,
    parse_os_release,
)
from lib.output import output_toml


class TestKernelModule:
    """Test KernelModule dataclass."""

    def test_kernel_module_creation(self):
        """Test creating a KernelModule."""
        module = KernelModule(
            name="rockchip_vpu.ko",
            path="/lib/modules/5.10.110/rockchip_vpu.ko",
            size=102400,
        )

        assert module.name == "rockchip_vpu.ko"
        assert module.path == "/lib/modules/5.10.110/rockchip_vpu.ko"
        assert module.size == 102400

    def test_kernel_module_is_frozen(self):
        """Test that KernelModule is immutable (frozen)."""
        module = KernelModule(name="test.ko", path="/test.ko", size=1024)

        with pytest.raises(AttributeError):
            module.name = "other.ko"  # type: ignore

    def test_kernel_module_uses_slots(self):
        """Test that KernelModule uses __slots__ for memory efficiency."""
        module = KernelModule(name="test.ko", path="/test.ko", size=1024)

        # __slots__ prevents adding arbitrary attributes
        # Note: frozen dataclasses with slots raise FrozenInstanceError
        with pytest.raises((AttributeError, TypeError)):
            module.extra_field = "test"  # type: ignore


class TestSharedLibrary:
    """Test SharedLibrary dataclass."""

    def test_shared_library_creation(self):
        """Test creating a SharedLibrary."""
        lib = SharedLibrary(
            name="libc.so.6",
            path="/lib/libc.so.6",
            size=2048000,
        )

        assert lib.name == "libc.so.6"
        assert lib.path == "/lib/libc.so.6"
        assert lib.size == 2048000

    def test_shared_library_is_frozen(self):
        """Test that SharedLibrary is immutable (frozen)."""
        lib = SharedLibrary(name="libc.so.6", path="/lib/libc.so.6", size=2048000)

        with pytest.raises(AttributeError):
            lib.size = 999999  # type: ignore

    def test_shared_library_uses_slots(self):
        """Test that SharedLibrary uses __slots__ for memory efficiency."""
        lib = SharedLibrary(name="libc.so.6", path="/lib/libc.so.6", size=2048000)

        # __slots__ prevents adding arbitrary attributes
        # Note: frozen dataclasses with slots raise FrozenInstanceError
        with pytest.raises((AttributeError, TypeError)):
            lib.license = "LGPL"  # type: ignore


class TestGplBinary:
    """Test GplBinary dataclass."""

    def test_gpl_binary_creation(self):
        """Test creating a GplBinary."""
        binary = GplBinary(
            name="busybox",
            path="/bin/busybox",
            license="GPL-2.0",
            version="BusyBox v1.36.1",
        )

        assert binary.name == "busybox"
        assert binary.path == "/bin/busybox"
        assert binary.license == "GPL-2.0"
        assert binary.version == "BusyBox v1.36.1"

    def test_gpl_binary_without_version(self):
        """Test creating a GplBinary without version (optional field)."""
        binary = GplBinary(
            name="bash",
            path="/bin/bash",
            license="GPL-3.0+",
        )

        assert binary.name == "bash"
        assert binary.version is None

    def test_gpl_binary_is_frozen(self):
        """Test that GplBinary is immutable (frozen)."""
        binary = GplBinary(name="bash", path="/bin/bash", license="GPL-3.0+")

        with pytest.raises(AttributeError):
            binary.license = "MIT"  # type: ignore


class TestLicenseFile:
    """Test LicenseFile dataclass."""

    def test_license_file_creation(self):
        """Test creating a LicenseFile."""
        license_file = LicenseFile(
            path="/usr/share/licenses/busybox/LICENSE",
            content_preview="GNU GENERAL PUBLIC LICENSE\nVersion 2",
        )

        assert license_file.path == "/usr/share/licenses/busybox/LICENSE"
        assert "GNU GENERAL PUBLIC LICENSE" in license_file.content_preview

    def test_license_file_is_frozen(self):
        """Test that LicenseFile is immutable (frozen)."""
        license_file = LicenseFile(path="/LICENSE", content_preview="MIT License")

        with pytest.raises(AttributeError):
            license_file.path = "/OTHER"  # type: ignore


class TestDetectedLicense:
    """Test DetectedLicense dataclass."""

    def test_detected_license_creation(self):
        """Test creating a DetectedLicense."""
        detected = DetectedLicense(
            component="libc.so",
            license="LGPL-2.1",
            detection_method="Known library name matching",
        )

        assert detected.component == "libc.so"
        assert detected.license == "LGPL-2.1"
        assert detected.detection_method == "Known library name matching"

    def test_detected_license_is_frozen(self):
        """Test that DetectedLicense is immutable (frozen)."""
        detected = DetectedLicense(component="libc.so", license="LGPL-2.1", detection_method="test")

        with pytest.raises(AttributeError):
            detected.license = "MIT"  # type: ignore


class TestRootfsAnalysis:
    """Test RootfsAnalysis dataclass."""

    def test_rootfs_analysis_creation(self):
        """Test creating a RootfsAnalysis."""
        analysis = RootfsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/squashfs-root",
        )

        assert analysis.firmware_file == "test.img"
        assert analysis.rootfs_path == "/tmp/squashfs-root"
        assert analysis.kernel_modules_count == 0
        assert analysis.busybox_found is False

    def test_rootfs_analysis_with_optional_fields(self):
        """Test creating a RootfsAnalysis with optional fields."""
        analysis = RootfsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/squashfs-root",
            os_name="OpenWrt",
            os_version="23.05.0",
            kernel_version="5.10.110",
        )

        assert analysis.os_name == "OpenWrt"
        assert analysis.os_version == "23.05.0"
        assert analysis.kernel_version == "5.10.110"

    def test_add_metadata(self):
        """Test adding source metadata."""
        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path="/tmp/root")

        analysis.add_metadata("os_name", "/etc/os-release", "NAME field")

        assert analysis._source["os_name"] == "/etc/os-release"
        assert analysis._method["os_name"] == "NAME field"

    def test_to_dict_excludes_none(self):
        """Test to_dict excludes None values."""
        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path="/tmp/root")

        result = analysis.to_dict()

        assert "firmware_file" in result
        assert "rootfs_path" in result
        assert "os_name" not in result  # Should be excluded (None)
        assert "kernel_version" not in result  # Should be excluded (None)

    def test_to_dict_includes_metadata(self):
        """Test to_dict includes source metadata."""
        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path="/tmp/root")
        analysis.add_metadata("firmware_file", "filesystem", "basename(firmware_path)")

        result = analysis.to_dict()

        assert result["firmware_file"] == "test.img"
        assert result["firmware_file_source"] == "filesystem"
        assert result["firmware_file_method"] == "basename(firmware_path)"

    def test_to_dict_converts_kernel_modules(self):
        """Test to_dict converts KernelModule objects to dicts."""
        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path="/tmp/root")
        analysis.kernel_modules = [
            KernelModule(name="test.ko", path="/lib/modules/test.ko", size=1024)
        ]

        result = analysis.to_dict()

        assert len(result["kernel_modules"]) == 1
        assert result["kernel_modules"][0]["name"] == "test.ko"
        assert result["kernel_modules"][0]["path"] == "/lib/modules/test.ko"
        assert result["kernel_modules"][0]["size"] == 1024

    def test_to_dict_converts_shared_libraries(self):
        """Test to_dict converts SharedLibrary objects to dicts."""
        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path="/tmp/root")
        analysis.shared_libraries = [
            SharedLibrary(name="libc.so.6", path="/lib/libc.so.6", size=2048000)
        ]

        result = analysis.to_dict()

        assert len(result["shared_libraries"]) == 1
        assert result["shared_libraries"][0]["name"] == "libc.so.6"
        assert result["shared_libraries"][0]["path"] == "/lib/libc.so.6"
        assert result["shared_libraries"][0]["size"] == 2048000

    def test_to_dict_converts_gpl_binaries(self):
        """Test to_dict converts GplBinary objects to dicts."""
        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path="/tmp/root")
        analysis.gpl_binaries = [
            GplBinary(name="busybox", path="/bin/busybox", license="GPL-2.0", version="1.36.1")
        ]

        result = analysis.to_dict()

        assert len(result["gpl_binaries"]) == 1
        assert result["gpl_binaries"][0]["name"] == "busybox"
        assert result["gpl_binaries"][0]["license"] == "GPL-2.0"
        assert result["gpl_binaries"][0]["version"] == "1.36.1"

    def test_to_dict_converts_license_files(self):
        """Test to_dict converts LicenseFile objects to dicts."""
        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path="/tmp/root")
        analysis.license_files = [LicenseFile(path="/LICENSE", content_preview="MIT License")]

        result = analysis.to_dict()

        assert len(result["license_files"]) == 1
        assert result["license_files"][0]["path"] == "/LICENSE"
        assert result["license_files"][0]["content_preview"] == "MIT License"

    def test_to_dict_converts_detected_licenses(self):
        """Test to_dict converts DetectedLicense objects to dicts."""
        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path="/tmp/root")
        analysis.detected_licenses = [
            DetectedLicense(
                component="libc.so", license="LGPL-2.1", detection_method="name matching"
            )
        ]

        result = analysis.to_dict()

        assert len(result["detected_licenses"]) == 1
        assert result["detected_licenses"][0]["component"] == "libc.so"
        assert result["detected_licenses"][0]["license"] == "LGPL-2.1"
        assert result["detected_licenses"][0]["detection_method"] == "name matching"

    def test_to_dict_excludes_internal_fields(self):
        """Test to_dict excludes internal fields (starting with _)."""
        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path="/tmp/root")
        analysis.add_metadata("firmware_file", "test", "test method")

        result = analysis.to_dict()

        assert "_source" not in result
        assert "_method" not in result


class TestFindSquashfsRootfs:
    """Test find_squashfs_rootfs function."""

    def test_find_squashfs_rootfs_success(self, tmp_path):
        """Test finding squashfs-root directory."""
        # Create a fake extraction directory structure
        extract_dir = tmp_path / "firmware.img.extracted"
        squashfs_root = extract_dir / "squashfs-root"
        squashfs_root.mkdir(parents=True)

        result = find_squashfs_rootfs(extract_dir)

        assert result == squashfs_root

    def test_find_squashfs_rootfs_nested(self, tmp_path):
        """Test finding squashfs-root in nested directory."""
        # Create nested structure
        extract_dir = tmp_path / "firmware.img.extracted"
        nested = extract_dir / "1234" / "5678"
        squashfs_root = nested / "squashfs-root"
        squashfs_root.mkdir(parents=True)

        result = find_squashfs_rootfs(extract_dir)

        assert result == squashfs_root

    def test_find_squashfs_rootfs_not_found(self, tmp_path):
        """Test that missing squashfs-root causes exit."""
        extract_dir = tmp_path / "firmware.img.extracted"
        extract_dir.mkdir(parents=True)

        with pytest.raises(SystemExit) as exc_info:
            find_squashfs_rootfs(extract_dir)

        assert exc_info.value.code == 1


class TestParseOsRelease:
    """Test parse_os_release function."""

    def test_parse_os_release_success(self, tmp_path):
        """Test parsing /etc/os-release file."""
        rootfs = tmp_path / "rootfs"
        etc_dir = rootfs / "etc"
        etc_dir.mkdir(parents=True)

        os_release = etc_dir / "os-release"
        os_release.write_text(
            'NAME="OpenWrt"\nVERSION="23.05.0"\nPRETTY_NAME="OpenWrt 23.05.0"\nID="openwrt"\n'
        )

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        parse_os_release(rootfs, analysis)

        assert analysis.os_name == "OpenWrt"
        assert analysis.os_version == "23.05.0"
        assert analysis.os_pretty_name == "OpenWrt 23.05.0"
        assert analysis._source["os_name"] == "/etc/os-release"
        assert analysis._method["os_name"] == "NAME field"

    def test_parse_os_release_missing_file(self, tmp_path):
        """Test parsing when /etc/os-release doesn't exist."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        parse_os_release(rootfs, analysis)

        # Should not crash, fields should remain None
        assert analysis.os_name is None
        assert analysis.os_version is None

    def test_parse_os_release_partial_data(self, tmp_path):
        """Test parsing /etc/os-release with partial data."""
        rootfs = tmp_path / "rootfs"
        etc_dir = rootfs / "etc"
        etc_dir.mkdir(parents=True)

        os_release = etc_dir / "os-release"
        os_release.write_text('NAME="OpenWrt"\n')

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        parse_os_release(rootfs, analysis)

        assert analysis.os_name == "OpenWrt"
        assert analysis.os_version is None


class TestExtractKernelVersion:
    """Test extract_kernel_version function."""

    @patch("subprocess.run")
    def test_extract_kernel_version_success(self, mock_run, tmp_path):
        """Test extracting kernel version from module."""
        rootfs = tmp_path / "rootfs"
        lib_modules = rootfs / "lib/modules/5.10.110"
        lib_modules.mkdir(parents=True)

        ko_file = lib_modules / "test.ko"
        ko_file.write_text("dummy")

        # Mock subprocess.run to return version string
        mock_run.return_value = MagicMock(
            stdout="some text\nvermagic=5.10.110 SMP preempt mod_unload aarch64\nmore text\n"
        )

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        extract_kernel_version(rootfs, analysis)

        assert "vermagic=5.10.110" in analysis.kernel_version
        assert analysis._source["kernel_version"] == "kernel module"
        assert "strings" in analysis._method["kernel_version"]

    def test_extract_kernel_version_no_modules(self, tmp_path):
        """Test extracting kernel version when no modules exist."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        extract_kernel_version(rootfs, analysis)

        # Should not crash, version should remain None
        assert analysis.kernel_version is None


class TestAnalyzeKernelModules:
    """Test analyze_kernel_modules function."""

    def test_analyze_kernel_modules_success(self, tmp_path):
        """Test analyzing kernel modules."""
        rootfs = tmp_path / "rootfs"
        lib_modules = rootfs / "lib/modules/5.10.110"
        lib_modules.mkdir(parents=True)

        # Create some .ko files
        module1 = lib_modules / "rockchip_vpu.ko"
        module1.write_bytes(b"x" * 1024)

        module2 = lib_modules / "test.ko"
        module2.write_bytes(b"x" * 2048)

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        analyze_kernel_modules(rootfs, analysis)

        assert analysis.kernel_modules_count == 2
        assert len(analysis.kernel_modules) == 2

        # Verify sorted by path
        assert analysis.kernel_modules[0].name == "rockchip_vpu.ko"
        assert analysis.kernel_modules[0].size == 1024
        assert analysis.kernel_modules[0].path.startswith("/lib/modules")

    def test_analyze_kernel_modules_empty(self, tmp_path):
        """Test analyzing when no kernel modules exist."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        analyze_kernel_modules(rootfs, analysis)

        assert analysis.kernel_modules_count == 0
        assert len(analysis.kernel_modules) == 0


class TestAnalyzeSharedLibraries:
    """Test analyze_shared_libraries function."""

    def test_analyze_shared_libraries_success(self, tmp_path):
        """Test analyzing shared libraries."""
        rootfs = tmp_path / "rootfs"
        lib_dir = rootfs / "lib"
        lib_dir.mkdir(parents=True)

        # Create some .so files
        libc = lib_dir / "libc.so.6"
        libc.write_bytes(b"x" * 2048000)

        libm = lib_dir / "libm.so.6"
        libm.write_bytes(b"x" * 1024000)

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        analyze_shared_libraries(rootfs, analysis)

        assert analysis.shared_libraries_count == 2
        assert len(analysis.shared_libraries) == 2

        # Verify sorted by path
        assert analysis.shared_libraries[0].name == "libc.so.6"
        assert analysis.shared_libraries[0].size == 2048000

    def test_analyze_shared_libraries_limits_output(self, tmp_path):
        """Test that output is limited to 100 libraries."""
        rootfs = tmp_path / "rootfs"
        lib_dir = rootfs / "lib"
        lib_dir.mkdir(parents=True)

        # Create 150 .so files
        for i in range(150):
            lib = lib_dir / f"lib{i:03d}.so"
            lib.write_bytes(b"x" * 1024)

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        analyze_shared_libraries(rootfs, analysis)

        assert analysis.shared_libraries_count == 150
        assert len(analysis.shared_libraries) == 100  # Limited to 100

    def test_analyze_shared_libraries_versioned_names(self, tmp_path):
        """Test analyzing libraries with version suffixes like .so.1.2.3."""
        rootfs = tmp_path / "rootfs"
        lib_dir = rootfs / "lib"
        lib_dir.mkdir(parents=True)

        # Create versioned .so files
        lib_versioned = lib_dir / "libtest.so.1.2.3"
        lib_versioned.write_bytes(b"x" * 1024)

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        analyze_shared_libraries(rootfs, analysis)

        assert analysis.shared_libraries_count == 1
        assert analysis.shared_libraries[0].name == "libtest.so.1.2.3"


class TestAnalyzeBusybox:
    """Test analyze_busybox function."""

    @patch("subprocess.run")
    def test_analyze_busybox_found(self, mock_run, tmp_path):
        """Test analyzing BusyBox when it exists."""
        rootfs = tmp_path / "rootfs"
        bin_dir = rootfs / "bin"
        bin_dir.mkdir(parents=True)

        busybox = bin_dir / "busybox"
        busybox.write_bytes(b"dummy binary")

        # Mock subprocess.run to return version string
        mock_run.return_value = MagicMock(stdout="BusyBox v1.36.1 (2024-01-01 12:00:00 UTC)\n")

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        analyze_busybox(rootfs, analysis)

        assert analysis.busybox_found is True
        assert "BusyBox v1.36.1" in analysis.busybox_version
        assert len(analysis.gpl_binaries) == 1
        assert analysis.gpl_binaries[0].name == "busybox"
        assert analysis.gpl_binaries[0].license == "GPL-2.0"

    def test_analyze_busybox_not_found(self, tmp_path):
        """Test analyzing when BusyBox doesn't exist."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        analyze_busybox(rootfs, analysis)

        assert analysis.busybox_found is False
        assert analysis.busybox_version is None


class TestAnalyzeGplBinaries:
    """Test analyze_gpl_binaries function."""

    def test_analyze_gpl_binaries_found(self, tmp_path):
        """Test identifying GPL binaries."""
        rootfs = tmp_path / "rootfs"
        bin_dir = rootfs / "bin"
        bin_dir.mkdir(parents=True)

        # Create some GPL binaries
        (bin_dir / "ls").write_bytes(b"dummy")
        (bin_dir / "grep").write_bytes(b"dummy")
        (bin_dir / "tar").write_bytes(b"dummy")

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        analyze_gpl_binaries(rootfs, analysis)

        binary_names = {b.name for b in analysis.gpl_binaries}
        assert "ls" in binary_names
        assert "grep" in binary_names
        assert "tar" in binary_names

    def test_analyze_gpl_binaries_symlink_to_busybox(self, tmp_path):
        """Test identifying symlinks to BusyBox."""
        rootfs = tmp_path / "rootfs"
        bin_dir = rootfs / "bin"
        bin_dir.mkdir(parents=True)

        # Create busybox binary
        busybox = bin_dir / "busybox"
        busybox.write_bytes(b"dummy")

        # Create symlink
        ls_symlink = bin_dir / "ls"
        ls_symlink.symlink_to(busybox)

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        analyze_gpl_binaries(rootfs, analysis)

        ls_binary = next(b for b in analysis.gpl_binaries if b.name == "ls")
        assert ls_binary.license == "BusyBox (GPL-2.0)"

    def test_analyze_gpl_binaries_multiple_locations(self, tmp_path):
        """Test finding binaries in different locations (bin, usr/bin, etc.)."""
        rootfs = tmp_path / "rootfs"

        # Create binaries in different locations
        bin_dir = rootfs / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "ls").write_bytes(b"dummy")

        usr_bin = rootfs / "usr/bin"
        usr_bin.mkdir(parents=True)
        (usr_bin / "awk").write_bytes(b"dummy")

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        analyze_gpl_binaries(rootfs, analysis)

        binary_names = {b.name for b in analysis.gpl_binaries}
        assert "ls" in binary_names
        assert "awk" in binary_names


class TestAnalyzeLicenseFiles:
    """Test analyze_license_files function."""

    def test_analyze_license_files_found(self, tmp_path):
        """Test finding license files."""
        rootfs = tmp_path / "rootfs"
        licenses_dir = rootfs / "usr/share/licenses/busybox"
        licenses_dir.mkdir(parents=True)

        license_file = licenses_dir / "LICENSE"
        license_content = "GNU GENERAL PUBLIC LICENSE\nVersion 2\n" * 10
        license_file.write_text(license_content)

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        analyze_license_files(rootfs, analysis)

        assert len(analysis.license_files) == 1
        assert "/usr/share/licenses/busybox/LICENSE" in analysis.license_files[0].path
        assert "GNU GENERAL PUBLIC LICENSE" in analysis.license_files[0].content_preview

    def test_analyze_license_files_preview_truncated(self, tmp_path):
        """Test that license file preview is truncated to 50 lines."""
        rootfs = tmp_path / "rootfs"
        license_dir = rootfs / "licenses"
        license_dir.mkdir(parents=True)

        license_file = license_dir / "LICENSE"
        # Create 100 lines
        lines = [f"Line {i}" for i in range(100)]
        license_file.write_text("\n".join(lines))

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        analyze_license_files(rootfs, analysis)

        assert len(analysis.license_files) == 1
        preview_lines = analysis.license_files[0].content_preview.splitlines()
        assert len(preview_lines) == 50  # Truncated to 50 lines

    def test_analyze_license_files_skips_large_files(self, tmp_path):
        """Test that very large license files are skipped."""
        rootfs = tmp_path / "rootfs"
        license_dir = rootfs / "licenses"
        license_dir.mkdir(parents=True)

        # Create a file larger than MAX_LICENSE_FILE_SIZE (100KB)
        large_license = license_dir / "LICENSE"
        large_license.write_bytes(b"x" * 200000)

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        analyze_license_files(rootfs, analysis)

        # Large file should be skipped
        assert len(analysis.license_files) == 0

    def test_analyze_license_files_case_insensitive(self, tmp_path):
        """Test finding license files with different case patterns."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        # Create files with different cases
        (rootfs / "LICENSE").write_text("License 1")
        (rootfs / "license").write_text("License 2")
        (rootfs / "COPYING").write_text("License 3")
        (rootfs / "copyright").write_text("License 4")

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        analyze_license_files(rootfs, analysis)

        # Should find all variants
        assert len(analysis.license_files) >= 3  # At least a few


class TestDetectLibraryLicenses:
    """Test detect_library_licenses function."""

    def test_detect_library_licenses_known_libraries(self, tmp_path):
        """Test detecting licenses from known library names."""
        rootfs = tmp_path / "rootfs"
        lib_dir = rootfs / "lib"
        lib_dir.mkdir(parents=True)

        # Create some known libraries
        (lib_dir / "libc.so.6").write_bytes(b"dummy")
        (lib_dir / "libpthread.so.0").write_bytes(b"dummy")
        (lib_dir / "libssl.so.1.1").write_bytes(b"dummy")
        (lib_dir / "libz.so.1").write_bytes(b"dummy")

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        detect_library_licenses(rootfs, analysis)

        detected_components = {d.component for d in analysis.detected_licenses}
        assert "libc.so" in detected_components
        assert "libpthread" in detected_components
        assert "libssl" in detected_components
        assert "libz.so" in detected_components

    def test_detect_library_licenses_correct_licenses(self, tmp_path):
        """Test that correct licenses are assigned to known libraries."""
        rootfs = tmp_path / "rootfs"
        lib_dir = rootfs / "lib"
        lib_dir.mkdir(parents=True)

        (lib_dir / "libc.so.6").write_bytes(b"dummy")
        (lib_dir / "libssl.so.1.1").write_bytes(b"dummy")

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        detect_library_licenses(rootfs, analysis)

        libc_license = next(d for d in analysis.detected_licenses if d.component == "libc.so")
        assert libc_license.license == "LGPL-2.1"

        libssl_license = next(d for d in analysis.detected_licenses if d.component == "libssl")
        assert libssl_license.license == "OpenSSL"

    def test_detect_library_licenses_sorted_output(self, tmp_path):
        """Test that detected licenses are sorted by component name."""
        rootfs = tmp_path / "rootfs"
        lib_dir = rootfs / "lib"
        lib_dir.mkdir(parents=True)

        # Create libraries in non-alphabetical order
        (lib_dir / "libz.so.1").write_bytes(b"dummy")
        (lib_dir / "libc.so.6").write_bytes(b"dummy")
        (lib_dir / "libm.so.6").write_bytes(b"dummy")

        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))
        detect_library_licenses(rootfs, analysis)

        # Should be sorted
        components = [d.component for d in analysis.detected_licenses]
        assert components == sorted(components)


class TestOutputToml:
    """Test output_toml function."""

    def test_toml_output_valid(self):
        """Test that TOML output is valid."""
        analysis = RootfsAnalysis(
            firmware_file="test.img",
            rootfs_path="/tmp/squashfs-root",
            kernel_modules_count=5,
            shared_libraries_count=42,
        )
        analysis.add_metadata("firmware_file", "filesystem", "basename(firmware_path)")

        toml_str = output_toml(analysis, "Root filesystem analysis", SIMPLE_FIELDS, COMPLEX_FIELDS)

        # Should be valid TOML
        parsed = tomlkit.loads(toml_str)
        assert parsed["firmware_file"] == "test.img"
        assert parsed["kernel_modules_count"] == 5
        assert parsed["shared_libraries_count"] == 42

    def test_toml_includes_comments(self):
        """Test that TOML includes source metadata as comments."""
        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path="/tmp/root")
        analysis.add_metadata("firmware_file", "filesystem", "basename(firmware_path)")

        toml_str = output_toml(analysis, "Root filesystem analysis", SIMPLE_FIELDS, COMPLEX_FIELDS)

        assert "# Source: filesystem" in toml_str
        assert "# Method: basename(firmware_path)" in toml_str

    def test_toml_truncates_long_methods(self):
        """Test that long method descriptions are truncated."""
        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path="/tmp/root")
        long_method = "x" * 100  # 100 characters
        analysis.add_metadata("rootfs_path", "test", long_method)

        toml_str = output_toml(analysis, "Root filesystem analysis", SIMPLE_FIELDS, COMPLEX_FIELDS)

        # Should be truncated with "..."
        assert "..." in toml_str
        assert long_method not in toml_str

    def test_toml_excludes_none_values(self):
        """Test that None values are excluded from TOML output."""
        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path="/tmp/root")
        # os_name, kernel_version, etc. are None by default

        toml_str = output_toml(analysis, "Root filesystem analysis", SIMPLE_FIELDS, COMPLEX_FIELDS)

        assert "os_name" not in toml_str
        assert "kernel_version" not in toml_str
        assert "busybox_version" not in toml_str

    def test_toml_includes_arrays(self):
        """Test that arrays (kernel_modules, etc.) are included."""
        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path="/tmp/root")
        analysis.kernel_modules = [
            KernelModule(name="test.ko", path="/lib/modules/test.ko", size=1024)
        ]
        analysis.gpl_binaries = [
            GplBinary(name="busybox", path="/bin/busybox", license="GPL-2.0", version="1.36.1")
        ]

        toml_str = output_toml(analysis, "Root filesystem analysis", SIMPLE_FIELDS, COMPLEX_FIELDS)
        parsed = tomlkit.loads(toml_str)

        assert len(parsed["kernel_modules"]) == 1
        assert parsed["kernel_modules"][0]["name"] == "test.ko"

        assert len(parsed["gpl_binaries"]) == 1
        assert parsed["gpl_binaries"][0]["name"] == "busybox"
        assert parsed["gpl_binaries"][0]["version"] == "1.36.1"

    def test_toml_includes_header_comment(self):
        """Test that TOML includes header comment."""
        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path="/tmp/root")

        toml_str = output_toml(analysis, "Root filesystem analysis", SIMPLE_FIELDS, COMPLEX_FIELDS)

        assert "# Root filesystem analysis" in toml_str
        assert "# Generated:" in toml_str

    def test_toml_validates_output(self):
        """Test that output_toml validates generated TOML by parsing it."""
        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path="/tmp/root")

        # Should not raise any exceptions
        toml_str = output_toml(analysis, "Root filesystem analysis", SIMPLE_FIELDS, COMPLEX_FIELDS)

        # Should be parseable
        parsed = tomlkit.loads(toml_str)
        assert isinstance(parsed, dict)


class TestIntegration:
    """Integration tests with realistic data."""

    @patch("subprocess.run")
    def test_realistic_rootfs_analysis(self, mock_run, tmp_path):
        """Test complete analysis workflow with realistic filesystem."""
        # Create realistic filesystem structure
        rootfs = tmp_path / "squashfs-root"

        # Create /etc/os-release
        etc = rootfs / "etc"
        etc.mkdir(parents=True)
        (etc / "os-release").write_text(
            'NAME="OpenWrt"\nVERSION="23.05.0"\nPRETTY_NAME="OpenWrt 23.05.0"\n'
        )

        # Create kernel modules
        modules_dir = rootfs / "lib/modules/5.10.110"
        modules_dir.mkdir(parents=True)
        (modules_dir / "rockchip_vpu.ko").write_bytes(b"x" * 102400)
        (modules_dir / "dwc3.ko").write_bytes(b"x" * 51200)

        # Create shared libraries
        lib_dir = rootfs / "lib"
        lib_dir.mkdir(parents=True, exist_ok=True)
        (lib_dir / "libc.so.6").write_bytes(b"x" * 2048000)
        (lib_dir / "libpthread.so.0").write_bytes(b"x" * 204800)

        # Create GPL binaries
        bin_dir = rootfs / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "busybox").write_bytes(b"x" * 1024000)
        (bin_dir / "ls").symlink_to("busybox")

        # Create license files
        license_dir = rootfs / "usr/share/licenses"
        license_dir.mkdir(parents=True)
        (license_dir / "LICENSE").write_text("GNU GENERAL PUBLIC LICENSE\nVersion 2\n")

        # Mock subprocess for strings commands (kernel version and busybox)
        def mock_subprocess_side_effect(*args, **_kwargs):
            mock_result = MagicMock()
            # Check which file is being processed
            cmd = args[0]
            if "strings" in cmd:
                if "busybox" in str(cmd):
                    mock_result.stdout = "BusyBox v1.36.1 (2024-01-01)\n"
                else:
                    mock_result.stdout = "vermagic=5.10.110 SMP preempt mod_unload aarch64\n"
            return mock_result

        mock_run.side_effect = mock_subprocess_side_effect

        # Run complete analysis
        analysis = RootfsAnalysis(firmware_file="test.img", rootfs_path=str(rootfs))

        parse_os_release(rootfs, analysis)
        analyze_kernel_modules(rootfs, analysis)
        analyze_shared_libraries(rootfs, analysis)
        analyze_license_files(rootfs, analysis)
        detect_library_licenses(rootfs, analysis)

        # Call analyze_busybox explicitly to ensure it has version info
        analyze_busybox(rootfs, analysis)

        # Verify results
        assert analysis.os_name == "OpenWrt"
        assert analysis.kernel_modules_count == 2
        assert analysis.shared_libraries_count == 2
        assert len(analysis.gpl_binaries) >= 1  # At least busybox
        assert analysis.busybox_found is True
        assert analysis.busybox_version is not None
        assert len(analysis.license_files) >= 1
        assert len(analysis.detected_licenses) >= 2

        # Verify TOML output works (tests that all required fields are present)
        toml_str = output_toml(analysis, "Root filesystem analysis", SIMPLE_FIELDS, COMPLEX_FIELDS)
        parsed = tomlkit.loads(toml_str)
        assert parsed["os_name"] == "OpenWrt"
        assert parsed["kernel_modules_count"] == 2
        assert parsed["busybox_found"] is True
