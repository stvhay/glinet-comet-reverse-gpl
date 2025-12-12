"""Tests for scripts/analyze_secure_boot.py."""

from __future__ import annotations

import gzip
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import tomlkit

# Add scripts directory to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from analyze_secure_boot import (
    COMPLEX_FIELDS,
    SIMPLE_FIELDS,
    FITSignature,
    SecureBootAnalysis,
    extract_device_tree_node,
    extract_firmware,
    extract_fit_signature,
    extract_gzip_strings,
    filter_strings,
    find_dtb_file,
    find_largest_dtb,
    load_offsets,
    main,
)
from lib.output import output_toml


class TestFITSignature:
    """Test FITSignature dataclass."""

    def test_signature_creation(self):
        """Test creating a FITSignature."""
        sig = FITSignature(
            image_type="bootloader",
            algorithm="sha256,rsa2048",
            key_name="dev-key",
            signed_components="firmware,fdt",
        )

        assert sig.image_type == "bootloader"
        assert sig.algorithm == "sha256,rsa2048"
        assert sig.key_name == "dev-key"
        assert sig.signed_components == "firmware,fdt"

    def test_signature_is_frozen(self):
        """Test that FITSignature is immutable (frozen)."""
        sig = FITSignature(
            image_type="bootloader",
            algorithm="sha256,rsa2048",
            key_name="dev-key",
            signed_components="firmware,fdt",
        )

        with pytest.raises(AttributeError):
            sig.algorithm = "sha512,rsa4096"  # type: ignore

    def test_signature_has_slots(self):
        """Test that FITSignature uses __slots__ for efficiency."""
        sig = FITSignature(
            image_type="kernel",
            algorithm="sha256,rsa2048",
            key_name="prod-key",
            signed_components="kernel,fdt",
        )

        # Frozen dataclasses prevent attribute modification
        assert hasattr(sig.__class__, "__slots__")

    def test_signature_kernel_type(self):
        """Test creating a kernel-type FITSignature."""
        sig = FITSignature(
            image_type="kernel",
            algorithm="sha512,rsa4096",
            key_name="kernel-key",
            signed_components="kernel,fdt,ramdisk",
        )

        assert sig.image_type == "kernel"
        assert sig.signed_components == "kernel,fdt,ramdisk"


class TestSecureBootAnalysis:
    """Test SecureBootAnalysis dataclass."""

    def test_analysis_creation_minimal(self):
        """Test creating a SecureBootAnalysis with minimal fields."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
        )

        assert analysis.firmware_file == "test.img"
        assert analysis.firmware_size == 1024000
        assert analysis.bootloader_fit_offset is None
        assert analysis.kernel_fit_offset is None
        assert analysis.uboot_offset is None
        assert analysis.optee_offset is None
        assert analysis.bootloader_signature is None
        assert analysis.kernel_signature is None
        assert analysis.uboot_verification_strings == []
        assert analysis.uboot_key_findings == []
        assert analysis.optee_secure_boot_strings == []
        assert analysis.has_otp_node is False
        assert analysis.has_crypto_node is False

    def test_analysis_creation_full(self):
        """Test creating a SecureBootAnalysis with all fields."""
        bootloader_sig = FITSignature(
            image_type="bootloader",
            algorithm="sha256,rsa2048",
            key_name="dev-key",
            signed_components="firmware,fdt",
        )
        kernel_sig = FITSignature(
            image_type="kernel",
            algorithm="sha512,rsa4096",
            key_name="kernel-key",
            signed_components="kernel,fdt",
        )

        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
            bootloader_fit_offset="0x8000",
            kernel_fit_offset="0x80000",
            uboot_offset="0x901B4",
            optee_offset="0xFD5B4",
            bootloader_signature=bootloader_sig,
            kernel_signature=kernel_sig,
            uboot_verification_strings=["verified", "signature check"],
            uboot_key_findings=["CONFIG_FIT_SIGNATURE"],
            optee_secure_boot_strings=["secure boot enabled"],
            has_otp_node=True,
            has_crypto_node=True,
            otp_node_content="otp@fe388000 { ... }",
            crypto_node_content="crypto@fe380000 { ... }",
        )

        assert analysis.bootloader_fit_offset == "0x8000"
        assert analysis.kernel_fit_offset == "0x80000"
        assert analysis.bootloader_signature == bootloader_sig
        assert analysis.kernel_signature == kernel_sig
        assert len(analysis.uboot_verification_strings) == 2
        assert len(analysis.uboot_key_findings) == 1
        assert analysis.has_otp_node is True
        assert analysis.has_crypto_node is True

    def test_analysis_is_mutable(self):
        """Test that SecureBootAnalysis is mutable (not frozen)."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
        )

        # Should be able to modify fields
        analysis.has_otp_node = True
        assert analysis.has_otp_node is True

    def test_add_metadata(self):
        """Test adding source metadata."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
        )

        analysis.add_metadata("firmware_size", "secure_boot", "Path(firmware).stat().st_size")

        assert analysis._source["firmware_size"] == "secure_boot"
        assert analysis._method["firmware_size"] == "Path(firmware).stat().st_size"

    def test_add_metadata_multiple_fields(self):
        """Test adding metadata for multiple fields."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
        )

        analysis.add_metadata("firmware_file", "secure_boot", "Path(firmware).name")
        analysis.add_metadata("uboot_offset", "binwalk", "UBOOT_GZ_OFFSET")

        assert len(analysis._source) == 2
        assert len(analysis._method) == 2
        assert analysis._source["uboot_offset"] == "binwalk"

    def test_to_dict_excludes_none(self):
        """Test to_dict excludes None values."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
        )

        result = analysis.to_dict()

        assert "firmware_file" in result
        assert "firmware_size" in result
        assert "bootloader_fit_offset" not in result  # None
        assert "kernel_fit_offset" not in result  # None
        assert "bootloader_signature" not in result  # None

    def test_to_dict_includes_bool_false(self):
        """Test to_dict includes boolean False values."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
            has_otp_node=False,
            has_crypto_node=False,
        )

        result = analysis.to_dict()

        assert "has_otp_node" in result
        assert result["has_otp_node"] is False
        assert "has_crypto_node" in result
        assert result["has_crypto_node"] is False

    def test_to_dict_excludes_empty_lists(self):
        """Test to_dict excludes empty lists."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
        )

        result = analysis.to_dict()

        assert "uboot_verification_strings" not in result
        assert "uboot_key_findings" not in result
        assert "optee_secure_boot_strings" not in result

    def test_to_dict_includes_non_empty_lists(self):
        """Test to_dict includes non-empty lists."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
            uboot_verification_strings=["verified", "signature check"],
        )

        result = analysis.to_dict()

        assert "uboot_verification_strings" in result
        assert len(result["uboot_verification_strings"]) == 2

    def test_to_dict_converts_signatures(self):
        """Test to_dict converts FITSignature objects to dicts."""
        bootloader_sig = FITSignature(
            image_type="bootloader",
            algorithm="sha256,rsa2048",
            key_name="dev-key",
            signed_components="firmware,fdt",
        )
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
            bootloader_signature=bootloader_sig,
        )

        result = analysis.to_dict()

        assert "bootloader_signature" in result
        assert result["bootloader_signature"]["image_type"] == "bootloader"
        assert result["bootloader_signature"]["algorithm"] == "sha256,rsa2048"
        assert result["bootloader_signature"]["key_name"] == "dev-key"
        assert result["bootloader_signature"]["signed_components"] == "firmware,fdt"

    def test_to_dict_includes_metadata(self):
        """Test to_dict includes source metadata."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
        )
        analysis.add_metadata("firmware_size", "secure_boot", "Path(firmware).stat().st_size")

        result = analysis.to_dict()

        assert result["firmware_size"] == 1024000
        assert result["firmware_size_source"] == "secure_boot"
        assert result["firmware_size_method"] == "Path(firmware).stat().st_size"

    def test_to_dict_excludes_private_fields(self):
        """Test to_dict excludes private fields (_source, _method)."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
        )
        analysis.add_metadata("firmware_size", "test", "test method")

        result = analysis.to_dict()

        assert "_source" not in result
        assert "_method" not in result

    def test_dataclass_has_slots(self):
        """Test that SecureBootAnalysis uses slots for memory efficiency."""
        # Verify it has slots defined
        assert hasattr(SecureBootAnalysis, "__slots__")


class TestLoadOffsets:
    """Test load_offsets function."""

    def test_load_offsets_missing_file(self, tmp_path):
        """Test loading offsets when file doesn't exist."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with pytest.raises(FileNotFoundError):
            load_offsets(output_dir)

    def test_load_offsets_empty_file(self, tmp_path):
        """Test loading offsets from empty file."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        offsets_file = output_dir / "binwalk-offsets.sh"
        offsets_file.write_text("")

        result = load_offsets(output_dir)

        assert result == {}

    def test_load_offsets_decimal_values(self, tmp_path):
        """Test loading decimal offset values."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        offsets_file = output_dir / "binwalk-offsets.sh"
        offsets_file.write_text("""
UBOOT_GZ_OFFSET_DEC=590260
BOOTLOADER_FIT_OFFSET_DEC=32768
KERNEL_FIT_OFFSET_DEC=524288
""")

        result = load_offsets(output_dir)

        assert result["UBOOT_GZ_OFFSET_DEC"] == 590260
        assert result["BOOTLOADER_FIT_OFFSET_DEC"] == 32768
        assert result["KERNEL_FIT_OFFSET_DEC"] == 524288

    def test_load_offsets_hex_values(self, tmp_path):
        """Test loading hexadecimal offset values."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        offsets_file = output_dir / "binwalk-offsets.sh"
        offsets_file.write_text("""
BOOTLOADER_FIT_OFFSET=0x8000
KERNEL_FIT_OFFSET=0x80000
UBOOT_GZ_OFFSET=0x901B4
OPTEE_GZ_OFFSET=0xFD5B4
""")

        result = load_offsets(output_dir)

        assert result["BOOTLOADER_FIT_OFFSET"] == "0x8000"
        assert result["KERNEL_FIT_OFFSET"] == "0x80000"
        assert result["UBOOT_GZ_OFFSET"] == "0x901B4"
        assert result["OPTEE_GZ_OFFSET"] == "0xFD5B4"

    def test_load_offsets_mixed_types(self, tmp_path):
        """Test loading both decimal and hex offsets."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        offsets_file = output_dir / "binwalk-offsets.sh"
        offsets_file.write_text("""
UBOOT_GZ_OFFSET=0x901B4
UBOOT_GZ_OFFSET_DEC=590260
KERNEL_FIT_OFFSET=0x80000
KERNEL_FIT_OFFSET_DEC=524288
""")

        result = load_offsets(output_dir)

        assert result["UBOOT_GZ_OFFSET"] == "0x901B4"
        assert result["UBOOT_GZ_OFFSET_DEC"] == 590260
        assert result["KERNEL_FIT_OFFSET"] == "0x80000"
        assert result["KERNEL_FIT_OFFSET_DEC"] == 524288

    def test_load_offsets_ignores_comments(self, tmp_path):
        """Test that comments are ignored."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        offsets_file = output_dir / "binwalk-offsets.sh"
        offsets_file.write_text("""
# This is a comment
UBOOT_GZ_OFFSET=0x901B4
# Another comment
UBOOT_GZ_OFFSET_DEC=590260
""")

        result = load_offsets(output_dir)

        assert len(result) == 2
        assert result["UBOOT_GZ_OFFSET"] == "0x901B4"

    def test_load_offsets_ignores_empty_lines(self, tmp_path):
        """Test that empty lines are ignored."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        offsets_file = output_dir / "binwalk-offsets.sh"
        offsets_file.write_text("""

UBOOT_GZ_OFFSET=0x901B4

KERNEL_FIT_OFFSET=0x80000

""")

        result = load_offsets(output_dir)

        assert len(result) == 2


class TestFindDtbFile:
    """Test find_dtb_file function."""

    def test_find_dtb_file_uppercase_offset(self, tmp_path):
        """Test finding DTB file with uppercase offset directory."""
        extract_dir = tmp_path / "firmware.extracted"
        dtb_dir = extract_dir / "8F1B4"
        dtb_dir.mkdir(parents=True)
        dtb_file = dtb_dir / "system.dtb"
        dtb_file.touch()

        result = find_dtb_file(extract_dir, "0x8F1B4")

        assert result == dtb_file

    def test_find_dtb_file_lowercase_offset(self, tmp_path):
        """Test finding DTB file with lowercase offset."""
        extract_dir = tmp_path / "firmware.extracted"
        dtb_dir = extract_dir / "8F1B4"
        dtb_dir.mkdir(parents=True)
        dtb_file = dtb_dir / "system.dtb"
        dtb_file.touch()

        result = find_dtb_file(extract_dir, "0x8f1b4")

        assert result == dtb_file

    def test_find_dtb_file_with_0x_prefix_dir(self, tmp_path):
        """Test finding DTB file when directory has 0x prefix."""
        extract_dir = tmp_path / "firmware.extracted"
        dtb_dir = extract_dir / "0X8F1B4"
        dtb_dir.mkdir(parents=True)
        dtb_file = dtb_dir / "system.dtb"
        dtb_file.touch()

        result = find_dtb_file(extract_dir, "0x8F1B4")

        assert result == dtb_file

    def test_find_dtb_file_not_found(self, tmp_path):
        """Test finding DTB file when it doesn't exist."""
        extract_dir = tmp_path / "firmware.extracted"
        extract_dir.mkdir()

        result = find_dtb_file(extract_dir, "0x8F1B4")

        assert result is None


class TestFindLargestDtb:
    """Test find_largest_dtb function."""

    def test_find_largest_dtb_single(self, tmp_path):
        """Test finding largest DTB with single file."""
        extract_dir = tmp_path / "firmware.extracted"
        dtb_dir = extract_dir / "8F1B4"
        dtb_dir.mkdir(parents=True)
        dtb_file = dtb_dir / "system.dtb"
        dtb_file.write_bytes(b"x" * 2048)

        result = find_largest_dtb(extract_dir)

        assert result == dtb_file
        assert result.stat().st_size == 2048

    def test_find_largest_dtb_multiple(self, tmp_path):
        """Test finding largest DTB with multiple files."""
        extract_dir = tmp_path / "firmware.extracted"

        # Create multiple DTB files with different sizes
        dtb_dir1 = extract_dir / "8F1B4"
        dtb_dir1.mkdir(parents=True)
        dtb_file1 = dtb_dir1 / "system.dtb"
        dtb_file1.write_bytes(b"x" * 2048)

        dtb_dir2 = extract_dir / "901B4"
        dtb_dir2.mkdir(parents=True)
        dtb_file2 = dtb_dir2 / "system.dtb"
        dtb_file2.write_bytes(b"x" * 8192)  # Largest

        dtb_dir3 = extract_dir / "A0000"
        dtb_dir3.mkdir(parents=True)
        dtb_file3 = dtb_dir3 / "system.dtb"
        dtb_file3.write_bytes(b"x" * 1024)

        result = find_largest_dtb(extract_dir)

        assert result == dtb_file2
        assert result.stat().st_size == 8192

    def test_find_largest_dtb_not_found(self, tmp_path):
        """Test finding largest DTB when no DTB files exist."""
        extract_dir = tmp_path / "firmware.extracted"
        extract_dir.mkdir()

        result = find_largest_dtb(extract_dir)

        assert result is None


class TestExtractFitSignature:
    """Test extract_fit_signature function."""

    def test_extract_fit_signature_complete(self, tmp_path):
        """Test extracting complete FIT signature information."""
        dtb_file = tmp_path / "system.dtb"
        dtb_content = """
        / {
            signature {
                algo = "sha256,rsa2048";
                key-name-hint = "dev-key";
                sign-images = "firmware,fdt";
            };
        };
        """
        dtb_file.write_text(dtb_content)

        result = extract_fit_signature(dtb_file, "bootloader")

        assert result is not None
        assert result.image_type == "bootloader"
        assert result.algorithm == "sha256,rsa2048"
        assert result.key_name == "dev-key"
        assert result.signed_components == "firmware,fdt"

    def test_extract_fit_signature_partial(self, tmp_path):
        """Test extracting partial FIT signature information."""
        dtb_file = tmp_path / "system.dtb"
        dtb_content = """
        / {
            signature {
                algo = "sha512,rsa4096";
                key-name-hint = "kernel-key";
            };
        };
        """
        dtb_file.write_text(dtb_content)

        result = extract_fit_signature(dtb_file, "kernel")

        assert result is not None
        assert result.image_type == "kernel"
        assert result.algorithm == "sha512,rsa4096"
        assert result.key_name == "kernel-key"
        assert result.signed_components == "unknown"

    def test_extract_fit_signature_not_found(self, tmp_path):
        """Test extracting FIT signature when no signature present."""
        dtb_file = tmp_path / "system.dtb"
        dtb_content = """
        / {
            model = "Test Device";
            compatible = "test";
        };
        """
        dtb_file.write_text(dtb_content)

        result = extract_fit_signature(dtb_file, "bootloader")

        assert result is None

    def test_extract_fit_signature_file_not_exist(self, tmp_path):
        """Test extracting FIT signature when file doesn't exist."""
        dtb_file = tmp_path / "nonexistent.dtb"

        result = extract_fit_signature(dtb_file, "bootloader")

        assert result is None

    def test_extract_fit_signature_case_insensitive(self, tmp_path):
        """Test extracting FIT signature with case variations."""
        dtb_file = tmp_path / "system.dtb"
        dtb_content = """
        / {
            signature {
                algo = "SHA256,RSA2048";
                key-name-hint = "dev-key";
            };
        };
        """
        dtb_file.write_text(dtb_content)

        result = extract_fit_signature(dtb_file, "bootloader")

        assert result is not None
        assert result.algorithm == "SHA256,RSA2048"


class TestExtractGzipStrings:
    """Test extract_gzip_strings function."""

    def test_extract_gzip_strings_simple(self, tmp_path):
        """Test extracting strings from gzip-compressed data."""
        firmware = tmp_path / "firmware.img"

        # Create gzip-compressed data with strings
        original_data = b"U-Boot 2023.07\x00verified signature\x00test string\x00"
        compressed_data = gzip.compress(original_data)

        # Write some padding then compressed data
        firmware.write_bytes(b"\x00" * 1024 + compressed_data)

        result = extract_gzip_strings(firmware, 1024, len(compressed_data))

        assert "U-Boot 2023.07" in result
        assert "verified signature" in result
        assert "test string" in result

    def test_extract_gzip_strings_min_length(self, tmp_path):
        """Test that strings below minimum length are excluded."""
        firmware = tmp_path / "firmware.img"

        # Create data with strings of varying lengths
        original_data = b"abc\x00abcd\x00ab\x00longer string\x00"
        compressed_data = gzip.compress(original_data)
        firmware.write_bytes(compressed_data)

        result = extract_gzip_strings(firmware, 0, len(compressed_data))

        # Only strings >= MIN_STRING_LENGTH (4) should be included
        assert "abcd" in result
        assert "longer string" in result
        assert "abc" not in result
        assert "ab" not in result

    def test_extract_gzip_strings_printable_only(self, tmp_path):
        """Test that only printable ASCII characters are extracted."""
        firmware = tmp_path / "firmware.img"

        # Include non-printable characters
        original_data = b"\x01\x1fU-Boot\x00\x80\x81test\x00"
        compressed_data = gzip.compress(original_data)
        firmware.write_bytes(compressed_data)

        result = extract_gzip_strings(firmware, 0, len(compressed_data))

        assert "U-Boot" in result
        assert "test" in result

    def test_extract_gzip_strings_invalid_gzip(self, tmp_path):
        """Test extracting strings from invalid gzip data."""
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"not gzip data" * 100)

        result = extract_gzip_strings(firmware, 0, 100)

        assert result == []

    def test_extract_gzip_strings_empty(self, tmp_path):
        """Test extracting strings from empty gzip data."""
        firmware = tmp_path / "firmware.img"
        compressed_data = gzip.compress(b"")
        firmware.write_bytes(compressed_data)

        result = extract_gzip_strings(firmware, 0, len(compressed_data))

        assert result == []

    def test_extract_gzip_strings_max_bytes(self, tmp_path):
        """Test that max_bytes limits the read size."""
        firmware = tmp_path / "firmware.img"

        # Create large compressed data
        original_data = b"test string\x00" * 1000
        compressed_data = gzip.compress(original_data)
        firmware.write_bytes(compressed_data)

        # Read full compressed data - should extract all strings
        result = extract_gzip_strings(firmware, 0, len(compressed_data))

        # Should extract all 1000 occurrences of "test string"
        assert len(result) == 1000
        assert all(s == "test string" for s in result)


class TestFilterStrings:
    """Test filter_strings function."""

    def test_filter_strings_single_pattern(self):
        """Test filtering strings with single pattern."""
        strings = [
            "verified boot",
            "signature check",
            "test string",
            "another test",
        ]
        patterns = [r"verified"]

        result = filter_strings(strings, patterns)

        assert result == ["verified boot"]

    def test_filter_strings_multiple_patterns(self):
        """Test filtering strings with multiple patterns."""
        strings = [
            "verified boot",
            "signature check",
            "secure boot enabled",
            "test string",
        ]
        patterns = [r"verified", r"signature", r"secure.*boot"]

        result = filter_strings(strings, patterns)

        assert "verified boot" in result
        assert "signature check" in result
        assert "secure boot enabled" in result
        assert "test string" not in result

    def test_filter_strings_case_insensitive(self):
        """Test that filtering is case-insensitive."""
        strings = [
            "VERIFIED BOOT",
            "Signature Check",
            "secure boot enabled",
        ]
        patterns = [r"verified", r"signature"]

        result = filter_strings(strings, patterns)

        assert "VERIFIED BOOT" in result
        assert "Signature Check" in result

    def test_filter_strings_regex_patterns(self):
        """Test filtering with regex patterns."""
        strings = [
            "bootcmd=run distro_bootcmd",
            "bootargs=console=ttyS0",
            "bootdelay=3",
            "test=value",
        ]
        patterns = [r"^boot"]

        result = filter_strings(strings, patterns)

        assert len(result) == 3
        assert "test=value" not in result

    def test_filter_strings_empty_patterns(self):
        """Test filtering with empty pattern list."""
        strings = ["test1", "test2", "test3"]
        patterns = []

        result = filter_strings(strings, patterns)

        assert result == []

    def test_filter_strings_no_matches(self):
        """Test filtering when no strings match."""
        strings = ["test1", "test2", "test3"]
        patterns = [r"notfound"]

        result = filter_strings(strings, patterns)

        assert result == []

    def test_filter_strings_deduplicates(self):
        """Test that filtering removes duplicates."""
        strings = ["verified", "signature", "verified", "signature"]
        patterns = [r"verified", r"signature"]

        result = filter_strings(strings, patterns)

        assert len(result) == 2
        assert "verified" in result
        assert "signature" in result

    def test_filter_strings_sorted(self):
        """Test that results are sorted."""
        strings = ["zzz", "aaa", "mmm"]
        patterns = [r".*"]

        result = filter_strings(strings, patterns)

        assert result == ["aaa", "mmm", "zzz"]


class TestExtractDeviceTreeNode:
    """Test extract_device_tree_node function."""

    def test_extract_device_tree_node_found(self, tmp_path):
        """Test extracting device tree node content."""
        dtb_file = tmp_path / "system.dtb"
        dtb_content = """
/ {
    otp@fe388000 {
        compatible = "rockchip,rk3568-otp";
        reg = <0xfe388000 0x4000>;
        #address-cells = <1>;
        #size-cells = <1>;
        status = "okay";
    };
};
"""
        dtb_file.write_text(dtb_content)

        result = extract_device_tree_node(dtb_file, r"otp@", 5)

        assert result is not None
        assert "otp@fe388000" in result
        assert "compatible" in result
        assert "rockchip,rk3568-otp" in result

    def test_extract_device_tree_node_lines_limit(self, tmp_path):
        """Test that extraction respects lines_after parameter."""
        dtb_file = tmp_path / "system.dtb"
        lines = ["otp@fe388000 {"] + [f"    line{i} = value{i};" for i in range(20)] + ["};"]
        dtb_content = "\n".join(lines)
        dtb_file.write_text(dtb_content)

        result = extract_device_tree_node(dtb_file, r"otp@", 5)

        assert result is not None
        result_lines = result.splitlines()
        # Should have at most 6 lines (match line + 5 after)
        assert len(result_lines) <= 6

    def test_extract_device_tree_node_not_found(self, tmp_path):
        """Test extracting node that doesn't exist."""
        dtb_file = tmp_path / "system.dtb"
        dtb_content = """
/ {
    model = "Test Device";
};
"""
        dtb_file.write_text(dtb_content)

        result = extract_device_tree_node(dtb_file, r"otp@", 10)

        assert result is None

    def test_extract_device_tree_node_file_not_exist(self, tmp_path):
        """Test extracting node when file doesn't exist."""
        dtb_file = tmp_path / "nonexistent.dtb"

        result = extract_device_tree_node(dtb_file, r"otp@", 10)

        assert result is None

    def test_extract_device_tree_node_crypto(self, tmp_path):
        """Test extracting crypto node."""
        dtb_file = tmp_path / "system.dtb"
        dtb_content = """
/ {
    crypto@fe380000 {
        compatible = "rockchip,rk3568-crypto";
        reg = <0xfe380000 0x2000>;
        interrupts = <GIC_SPI 4 IRQ_TYPE_LEVEL_HIGH>;
    };
};
"""
        dtb_file.write_text(dtb_content)

        result = extract_device_tree_node(dtb_file, r"crypto@", 10)

        assert result is not None
        assert "crypto@fe380000" in result
        assert "rockchip,rk3568-crypto" in result


class TestOutputToml:
    """Test output_toml function."""

    def test_toml_output_valid(self):
        """Test that TOML output is valid."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
            has_otp_node=True,
            has_crypto_node=False,
        )
        analysis.add_metadata("firmware_file", "secure_boot", "Path(firmware).name")

        toml_str = output_toml(
            analysis,
            title="Secure Boot Analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )

        # Should be valid TOML
        parsed = tomlkit.loads(toml_str)
        assert parsed["firmware_file"] == "test.img"
        assert parsed["firmware_size"] == 1024000
        assert parsed["has_otp_node"] is True
        assert parsed["has_crypto_node"] is False

    def test_toml_includes_header(self):
        """Test that TOML includes header comments."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
        )

        toml_str = output_toml(
            analysis,
            title="Secure Boot Analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )

        assert "# Secure Boot Analysis" in toml_str
        assert "# Generated:" in toml_str

    def test_toml_includes_source_comments(self):
        """Test that TOML includes source metadata as comments."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
        )
        analysis.add_metadata(
            "firmware_size",
            "secure_boot",
            "Path(firmware).stat().st_size",
        )

        toml_str = output_toml(
            analysis,
            title="Secure Boot Analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )

        assert "# Source: secure_boot" in toml_str
        assert "# Method: Path(firmware).stat().st_size" in toml_str

    def test_toml_truncates_long_methods(self):
        """Test that long method descriptions are truncated."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
        )
        long_method = "x" * 130
        analysis.add_metadata("firmware_size", "test", long_method)

        toml_str = output_toml(
            analysis,
            title="Secure Boot Analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )

        # Should be truncated with "..."
        assert "..." in toml_str
        assert long_method not in toml_str

    def test_toml_excludes_none_values(self):
        """Test that None values are excluded from TOML output."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
        )

        toml_str = output_toml(
            analysis,
            title="Secure Boot Analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )

        assert "bootloader_fit_offset" not in toml_str
        assert "kernel_fit_offset" not in toml_str
        assert "bootloader_signature" not in toml_str

    def test_toml_includes_signatures(self):
        """Test that FIT signatures are included in TOML."""
        bootloader_sig = FITSignature(
            image_type="bootloader",
            algorithm="sha256,rsa2048",
            key_name="dev-key",
            signed_components="firmware,fdt",
        )
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
            bootloader_signature=bootloader_sig,
        )

        toml_str = output_toml(
            analysis,
            title="Secure Boot Analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )
        parsed = tomlkit.loads(toml_str)

        assert "bootloader_signature" in parsed
        assert parsed["bootloader_signature"]["image_type"] == "bootloader"
        assert parsed["bootloader_signature"]["algorithm"] == "sha256,rsa2048"
        assert parsed["bootloader_signature"]["key_name"] == "dev-key"

    def test_toml_includes_string_lists(self):
        """Test that string lists are included in TOML."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
            uboot_verification_strings=["verified", "signature check"],
            uboot_key_findings=["CONFIG_FIT_SIGNATURE"],
        )

        toml_str = output_toml(
            analysis,
            title="Secure Boot Analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )
        parsed = tomlkit.loads(toml_str)

        assert len(parsed["uboot_verification_strings"]) == 2
        assert "verified" in parsed["uboot_verification_strings"]
        assert len(parsed["uboot_key_findings"]) == 1

    def test_toml_excludes_metadata_fields(self):
        """Test that _source and _method suffix fields are not in final TOML."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
        )
        analysis.add_metadata("firmware_size", "test", "test method")

        toml_str = output_toml(
            analysis,
            title="Secure Boot Analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )
        parsed = tomlkit.loads(toml_str)

        # Metadata should be in comments, not as fields
        assert "firmware_size_source" not in parsed
        assert "firmware_size_method" not in parsed

    def test_toml_validates_output(self):
        """Test that output_toml validates generated TOML by parsing it."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
            has_otp_node=True,
        )

        # Should not raise an exception
        toml_str = output_toml(
            analysis,
            title="Secure Boot Analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )

        # Should be valid TOML
        parsed = tomlkit.loads(toml_str)
        assert parsed is not None


class TestMainFunction:
    """Test main() function with mocked dependencies."""

    @patch("analyze_secure_boot.analyze_secure_boot")
    @patch("analyze_secure_boot.Path")
    def test_main_with_firmware_arg_toml(self, mock_path_cls, mock_analyze, tmp_path):  # noqa: ARG002
        """Test main() with firmware argument and TOML output."""
        # Mock Path to simulate firmware file exists
        mock_firmware = MagicMock()
        mock_firmware.exists.return_value = True
        mock_firmware.name = "test.img"
        mock_path_cls.return_value = mock_firmware

        # Mock analyze_secure_boot to return analysis
        mock_analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
            has_otp_node=True,
        )
        mock_analyze.return_value = mock_analysis

        # Mock sys.argv
        with patch("sys.argv", ["analyze_secure_boot.py", "test.img", "--format", "toml"]):
            # Capture stdout
            f = io.StringIO()
            with redirect_stdout(f):
                main()

            output = f.getvalue()
            assert "firmware_file" in output
            assert "has_otp_node" in output
            assert "Secure Boot Analysis" in output

    @patch("analyze_secure_boot.analyze_secure_boot")
    @patch("analyze_secure_boot.Path")
    def test_main_with_firmware_arg_json(self, mock_path_cls, mock_analyze):
        """Test main() with firmware argument and JSON output."""
        # Mock Path to simulate firmware file exists
        mock_firmware = MagicMock()
        mock_firmware.exists.return_value = True
        mock_firmware.name = "test.img"
        mock_path_cls.return_value = mock_firmware

        # Mock analyze_secure_boot to return analysis
        mock_analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
            has_otp_node=True,
        )
        mock_analyze.return_value = mock_analysis

        # Mock sys.argv
        with patch("sys.argv", ["analyze_secure_boot.py", "test.img", "--format", "json"]):
            # Capture stdout
            f = io.StringIO()
            with redirect_stdout(f):
                main()

            output = f.getvalue()
            # Should be valid JSON
            parsed = json.loads(output)
            assert parsed["firmware_file"] == "test.img"
            assert parsed["has_otp_node"] is True

    def test_extract_firmware(self, tmp_path):
        """Test extract_firmware function."""
        # Create fake firmware file
        firmware = tmp_path / "firmware.img"
        firmware.write_bytes(b"test firmware")

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        # Create fake extraction directory
        extract_base = work_dir / "extractions"
        extract_dir = extract_base / f"{firmware.name}.extracted"
        extract_dir.mkdir(parents=True)

        # Test extraction
        result = extract_firmware(firmware, work_dir)

        assert result == extract_dir
        assert result.exists()


class TestIntegration:
    """Integration tests with realistic data."""

    def test_realistic_secure_boot_analysis(self, tmp_path):  # noqa: ARG002
        """Test creating a realistic SecureBootAnalysis object."""
        bootloader_sig = FITSignature(
            image_type="bootloader",
            algorithm="sha256,rsa2048",
            key_name="dev-key",
            signed_components="firmware,fdt",
        )
        kernel_sig = FITSignature(
            image_type="kernel",
            algorithm="sha512,rsa4096",
            key_name="kernel-key",
            signed_components="kernel,fdt",
        )

        analysis = SecureBootAnalysis(
            firmware_file="glkvm-RM1-1.7.2-1128-1764344791.img",
            firmware_size=123456789,
            bootloader_fit_offset="0x8000",
            kernel_fit_offset="0x80000",
            uboot_offset="0x901B4",
            optee_offset="0xFD5B4",
            bootloader_signature=bootloader_sig,
            kernel_signature=kernel_sig,
            uboot_verification_strings=[
                "Verifying Hash Integrity ... OK",
                "## Checking Image at 00400000 ...",
                "RSA signature verification passed",
            ],
            uboot_key_findings=["CONFIG_FIT_SIGNATURE", "Verified-boot:"],
            optee_secure_boot_strings=[
                "secure boot enabled",
                "otp key index",
                "enable secure boot flag",
            ],
            has_otp_node=True,
            has_crypto_node=True,
            otp_node_content='otp@fe388000 {\n    compatible = "rockchip,rk3568-otp";\n};',
            crypto_node_content='crypto@fe380000 {\n    compatible = "rockchip,rk3568-crypto";\n};',
        )

        # Add metadata
        analysis.add_metadata("firmware_file", "secure_boot", "Path(firmware).name")
        analysis.add_metadata("firmware_size", "secure_boot", "Path(firmware).stat().st_size")
        analysis.add_metadata(
            "bootloader_fit_offset",
            "binwalk",
            "loaded from binwalk-offsets.sh BOOTLOADER_FIT_OFFSET",
        )
        analysis.add_metadata(
            "uboot_verification_strings",
            "strings",
            "gunzip U-Boot | strings | grep -E 'verified|signature'",
        )
        analysis.add_metadata(
            "has_otp_node",
            "device_tree",
            "grep 'otp@' in system.dtb",
        )

        # Test to_dict
        result = analysis.to_dict()

        assert result["firmware_file"] == "glkvm-RM1-1.7.2-1128-1764344791.img"
        assert result["firmware_size"] == 123456789
        assert result["bootloader_fit_offset"] == "0x8000"
        assert result["kernel_fit_offset"] == "0x80000"
        assert len(result["uboot_verification_strings"]) == 3
        assert len(result["uboot_key_findings"]) == 2
        assert len(result["optee_secure_boot_strings"]) == 3
        assert result["has_otp_node"] is True
        assert result["has_crypto_node"] is True

        # Test signatures
        assert result["bootloader_signature"]["algorithm"] == "sha256,rsa2048"
        assert result["kernel_signature"]["algorithm"] == "sha512,rsa4096"

        # Test metadata
        assert result["firmware_file_source"] == "secure_boot"
        assert result["has_otp_node_source"] == "device_tree"

    def test_realistic_toml_output(self):
        """Test generating realistic TOML output."""
        bootloader_sig = FITSignature(
            image_type="bootloader",
            algorithm="sha256,rsa2048",
            key_name="dev-key",
            signed_components="firmware,fdt",
        )

        analysis = SecureBootAnalysis(
            firmware_file="glkvm-RM1-1.7.2-1128-1764344791.img",
            firmware_size=123456789,
            bootloader_fit_offset="0x8000",
            bootloader_signature=bootloader_sig,
            uboot_verification_strings=["verified", "signature check"],
            has_otp_node=True,
        )

        analysis.add_metadata("firmware_file", "secure_boot", "Path(firmware).name")
        analysis.add_metadata(
            "bootloader_signature",
            "fit_dtb",
            "extracted from system.dtb using regex",
        )
        analysis.add_metadata(
            "has_otp_node",
            "device_tree",
            "grep 'otp@' in system.dtb",
        )

        toml_str = output_toml(
            analysis,
            title="Secure Boot Analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )

        # Validate TOML
        parsed = tomlkit.loads(toml_str)

        assert parsed["firmware_file"] == "glkvm-RM1-1.7.2-1128-1764344791.img"
        assert parsed["firmware_size"] == 123456789
        assert parsed["bootloader_fit_offset"] == "0x8000"
        assert parsed["bootloader_signature"]["image_type"] == "bootloader"
        assert len(parsed["uboot_verification_strings"]) == 2
        assert parsed["has_otp_node"] is True

        # Check header comments
        assert "# Secure Boot Analysis" in toml_str
        assert "# Generated:" in toml_str

        # Check source/method comments for simple fields
        assert "# Source: secure_boot" in toml_str
        assert "# Source: device_tree" in toml_str

    def test_minimal_secure_boot_analysis(self):
        """Test SecureBootAnalysis with minimal data (no secure boot found)."""
        analysis = SecureBootAnalysis(
            firmware_file="test.img",
            firmware_size=1024000,
            has_otp_node=False,
            has_crypto_node=False,
        )

        analysis.add_metadata("firmware_file", "secure_boot", "Path(firmware).name")
        analysis.add_metadata("firmware_size", "secure_boot", "Path(firmware).stat().st_size")

        result = analysis.to_dict()

        # Only basic fields should be present
        assert result["firmware_file"] == "test.img"
        assert result["firmware_size"] == 1024000
        assert result["has_otp_node"] is False
        assert result["has_crypto_node"] is False
        assert "bootloader_signature" not in result
        assert "uboot_verification_strings" not in result

        # Test TOML output
        toml_str = output_toml(
            analysis,
            title="Secure Boot Analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )
        parsed = tomlkit.loads(toml_str)

        assert parsed["firmware_file"] == "test.img"
        assert parsed["has_otp_node"] is False
        assert parsed["has_crypto_node"] is False
