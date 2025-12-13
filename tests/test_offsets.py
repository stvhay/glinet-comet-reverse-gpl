"""Tests for lib.offsets module."""

import sys
from pathlib import Path

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib.offsets import OffsetManager


@pytest.fixture
def sample_offsets_file(tmp_path: Path) -> Path:
    """Create a sample binwalk-offsets.sh file."""
    offsets_file = tmp_path / "binwalk-offsets.sh"
    offsets_file.write_text("""# Firmware offsets extracted from binwalk analysis
# Generated: 2025-12-13T10:00:00+00:00
# Source: firmware.img
#
# These values are parsed from binwalk output and should be used
# by other analysis scripts instead of hardcoding offsets.

# Bootloader FIT image (contains U-Boot + OP-TEE)
BOOTLOADER_FIT_OFFSET=0x8000
BOOTLOADER_FIT_OFFSET_DEC=32768

# U-Boot binary (gzip compressed)
UBOOT_GZ_OFFSET=0x1E240
UBOOT_GZ_OFFSET_DEC=123456

# OP-TEE binary (gzip compressed)
OPTEE_GZ_OFFSET=0x3C4E0
OPTEE_GZ_OFFSET_DEC=246496

# Kernel FIT image (contains kernel + DTB)
KERNEL_FIT_OFFSET=0x8F1B4
KERNEL_FIT_OFFSET_DEC=586164

# Root filesystem CPIO archive
ROOTFS_CPIO_OFFSET=0xA5458
ROOTFS_CPIO_OFFSET_DEC=676952

# SquashFS filesystem (main rootfs)
SQUASHFS_OFFSET=0x200000
SQUASHFS_OFFSET_DEC=2097152
SQUASHFS_SIZE=12345678
""")
    return offsets_file


@pytest.fixture
def offset_manager(tmp_path: Path, sample_offsets_file: Path) -> OffsetManager:
    """Create an OffsetManager with sample data loaded."""
    manager = OffsetManager(tmp_path)
    manager.load_from_shell_script(sample_offsets_file)
    return manager


class TestOffsetManager:
    """Tests for OffsetManager class."""

    def test_init_with_output_dir(self, tmp_path: Path):
        """Test initialization with output_dir."""
        manager = OffsetManager(tmp_path)
        assert manager.output_dir == tmp_path
        assert manager.offsets == {}

    def test_init_without_output_dir(self):
        """Test initialization without output_dir."""
        manager = OffsetManager()
        assert manager.output_dir is None
        assert manager.offsets == {}

    def test_load_from_shell_script_explicit_path(self, sample_offsets_file: Path):
        """Test loading offsets with explicit script path."""
        manager = OffsetManager()
        manager.load_from_shell_script(sample_offsets_file)

        # Check hex offsets (stored as strings)
        assert manager.offsets["BOOTLOADER_FIT_OFFSET"] == "0x8000"
        assert manager.offsets["UBOOT_GZ_OFFSET"] == "0x1E240"
        assert manager.offsets["KERNEL_FIT_OFFSET"] == "0x8F1B4"

        # Check decimal offsets (stored as ints)
        assert manager.offsets["BOOTLOADER_FIT_OFFSET_DEC"] == 32768
        assert manager.offsets["UBOOT_GZ_OFFSET_DEC"] == 123456
        assert manager.offsets["KERNEL_FIT_OFFSET_DEC"] == 586164

        # Check non-offset values
        assert manager.offsets["SQUASHFS_SIZE"] == "12345678"

    def test_load_from_shell_script_default_path(self, tmp_path: Path, sample_offsets_file: Path):
        """Test loading offsets with default path (output_dir/binwalk-offsets.sh)."""
        # Move file to expected location
        expected_path = tmp_path / "binwalk-offsets.sh"
        sample_offsets_file.rename(expected_path)

        manager = OffsetManager(tmp_path)
        manager.load_from_shell_script()

        assert manager.offsets["UBOOT_GZ_OFFSET"] == "0x1E240"
        assert manager.offsets["UBOOT_GZ_OFFSET_DEC"] == 123456

    def test_load_from_shell_script_file_not_found(self, tmp_path: Path):
        """Test loading from non-existent file raises FileNotFoundError."""
        manager = OffsetManager(tmp_path)
        with pytest.raises(FileNotFoundError, match="Offsets file not found"):
            manager.load_from_shell_script(tmp_path / "nonexistent.sh")

    def test_load_from_shell_script_no_output_dir(self):
        """Test loading without output_dir and without script_path raises ValueError."""
        manager = OffsetManager()
        with pytest.raises(ValueError, match="output_dir must be set"):
            manager.load_from_shell_script()

    def test_get_existing_key(self, offset_manager: OffsetManager):
        """Test get() with existing key."""
        assert offset_manager.get("UBOOT_GZ_OFFSET") == "0x1E240"
        assert offset_manager.get("UBOOT_GZ_OFFSET_DEC") == 123456

    def test_get_missing_key_default(self, offset_manager: OffsetManager):
        """Test get() with missing key returns default."""
        assert offset_manager.get("NONEXISTENT") is None
        assert offset_manager.get("NONEXISTENT", "default") == "default"

    def test_get_hex(self, offset_manager: OffsetManager):
        """Test get_hex() returns hex offset string."""
        assert offset_manager.get_hex("BOOTLOADER_FIT") == "0x8000"
        assert offset_manager.get_hex("UBOOT_GZ") == "0x1E240"
        assert offset_manager.get_hex("KERNEL_FIT") == "0x8F1B4"

    def test_get_hex_missing(self, offset_manager: OffsetManager):
        """Test get_hex() with missing offset returns None."""
        assert offset_manager.get_hex("NONEXISTENT") is None

    def test_get_dec(self, offset_manager: OffsetManager):
        """Test get_dec() returns decimal offset int."""
        assert offset_manager.get_dec("BOOTLOADER_FIT") == 32768
        assert offset_manager.get_dec("UBOOT_GZ") == 123456
        assert offset_manager.get_dec("KERNEL_FIT") == 586164

    def test_get_dec_missing(self, offset_manager: OffsetManager):
        """Test get_dec() with missing offset returns None."""
        assert offset_manager.get_dec("NONEXISTENT") is None

    def test_contains(self, offset_manager: OffsetManager):
        """Test __contains__ (in operator)."""
        assert "UBOOT_GZ_OFFSET" in offset_manager
        assert "UBOOT_GZ_OFFSET_DEC" in offset_manager
        assert "NONEXISTENT" not in offset_manager

    def test_getitem(self, offset_manager: OffsetManager):
        """Test __getitem__ (bracket notation)."""
        assert offset_manager["UBOOT_GZ_OFFSET"] == "0x1E240"
        assert offset_manager["UBOOT_GZ_OFFSET_DEC"] == 123456

    def test_getitem_missing_raises_keyerror(self, offset_manager: OffsetManager):
        """Test __getitem__ with missing key raises KeyError."""
        with pytest.raises(KeyError):
            _ = offset_manager["NONEXISTENT"]

    def test_ignores_comments(self, tmp_path: Path):
        """Test that comments are ignored during parsing."""
        offsets_file = tmp_path / "test.sh"
        offsets_file.write_text("""# This is a comment
# Another comment
OFFSET_A=0x1000
OFFSET_A_DEC=4096
# Inline comment should be ignored
""")

        manager = OffsetManager(tmp_path)
        manager.load_from_shell_script(offsets_file)

        assert len(manager.offsets) == 2
        assert manager.offsets["OFFSET_A"] == "0x1000"
        assert manager.offsets["OFFSET_A_DEC"] == 4096

    def test_ignores_empty_lines(self, tmp_path: Path):
        """Test that empty lines are ignored."""
        offsets_file = tmp_path / "test.sh"
        offsets_file.write_text("""
OFFSET_A=0x1000

OFFSET_A_DEC=4096

""")

        manager = OffsetManager(tmp_path)
        manager.load_from_shell_script(offsets_file)

        assert len(manager.offsets) == 2
        assert manager.offsets["OFFSET_A"] == "0x1000"
        assert manager.offsets["OFFSET_A_DEC"] == 4096
