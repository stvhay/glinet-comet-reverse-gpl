#!/usr/bin/env python3
"""
Tests for scripts/analysis.py
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import tomlkit

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from analysis import (
    TrackedValue,
    analyze,
    convert_to_tracked_values,
    hash_file,
    is_cache_valid,
)


class TestTrackedValue:
    """Test TrackedValue class."""

    def test_tracked_value_creation(self):
        """Test creating a TrackedValue."""
        tv = TrackedValue(42, "test", "echo 42")
        assert tv.value == 42
        assert tv.source == "test"
        assert tv.method == "echo 42"

    def test_tracked_value_str(self):
        """Test string representation."""
        tv = TrackedValue("0x2000", "kernel", "binwalk")
        assert str(tv) == "0x2000"

    def test_tracked_value_equality(self):
        """Test equality comparisons."""
        tv1 = TrackedValue(42, "test", "echo 42")
        tv2 = TrackedValue(42, "other", "different")
        assert tv1 == tv2  # Same value
        assert tv1 == 42  # Compare with raw value

    def test_tracked_value_int_conversion(self):
        """Test integer conversion."""
        tv = TrackedValue("42", "test", "echo 42")
        assert int(tv) == 42


class TestConvertToTrackedValues:
    """Test convert_to_tracked_values function."""

    def test_converts_with_metadata(self):
        """Test conversion of values with _source and _method metadata."""
        result = {
            "offset": "0x2000",
            "offset_source": "kernel",
            "offset_method": "binwalk -e",
            "size": 1024,
            "plain_value": "no metadata",
        }

        tracked = convert_to_tracked_values(result, "default")

        # Check tracked value
        assert isinstance(tracked["offset"], TrackedValue)
        assert tracked["offset"].value == "0x2000"
        assert tracked["offset"].source == "kernel"
        assert tracked["offset"].method == "binwalk -e"

        # Check plain value
        assert tracked["plain_value"] == "no metadata"

        # Metadata keys should not be in result
        assert "offset_source" not in tracked
        assert "offset_method" not in tracked

    def test_converts_with_default_source(self):
        """Test that values without _source use analysis_type as default."""
        result = {"value": 42, "value_method": "echo 42"}

        tracked = convert_to_tracked_values(result, "test_analysis")

        assert isinstance(tracked["value"], TrackedValue)
        assert tracked["value"].source == "test_analysis"


class TestHashFile:
    """Test hash_file function."""

    def test_hash_file(self):
        """Test hashing a file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)

        try:
            hash1 = hash_file(temp_path)
            assert len(hash1) == 16  # First 16 chars of SHA256

            # Same file should produce same hash
            hash2 = hash_file(temp_path)
            assert hash1 == hash2

            # Different content should produce different hash
            temp_path.write_text("different content")
            hash3 = hash_file(temp_path)
            assert hash1 != hash3
        finally:
            temp_path.unlink()


class TestCaching:
    """Test caching functionality."""

    def setup_method(self):
        """Set up test environment."""
        # Create temporary test directory
        self.test_dir = Path(tempfile.mkdtemp())
        self.orig_cwd = Path.cwd()

        # Change to test directory
        os.chdir(self.test_dir)

        # Create test structure
        (self.test_dir / "scripts").mkdir()
        (self.test_dir / "results").mkdir()

        # Create test analysis script
        test_script = self.test_dir / "scripts" / "analyze_testcache.sh"
        test_script.write_text("""#!/usr/bin/env bash
cat <<'EOF'
{
  "test": "value",
  "test_source": "testcache",
  "test_method": "echo value"
}
EOF
""")
        test_script.chmod(0o755)

    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.test_dir)

    def test_cache_invalidation_on_script_change(self):
        """Test that cache is invalidated when script changes."""
        # Clear the lru_cache for testing
        analyze.cache_clear()

        # First run - creates cache
        analyze("testcache")
        manifest_file = Path("results/.manifest.toml")
        assert manifest_file.exists()

        manifest1 = tomlkit.load(manifest_file.open())
        hash1 = manifest1["testcache"]["script_hash"]

        # Modify script
        test_script = Path("scripts/analyze_testcache.sh")
        test_script.write_text(test_script.read_text() + "\n# comment\n")

        # Clear lru_cache to force re-check
        analyze.cache_clear()

        # Second run - should detect change
        assert not is_cache_valid("testcache", manifest_file)

        # Run analysis again - should update cache
        analyze("testcache")

        manifest2 = tomlkit.load(manifest_file.open())
        hash2 = manifest2["testcache"]["script_hash"]

        # Hash should have changed
        assert hash1 != hash2
