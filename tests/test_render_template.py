#!/usr/bin/env python3
"""
Tests for scripts/render_template.py and scripts/analysis.py.

This test suite covers:
- Template rendering with analyze() function
- TrackedValue and footnote generation
- Cache invalidation logic
- Error handling
- Integration tests with actual template files
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
import tomlkit

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from analysis import (
    TrackedValue,
    analyze,
    atomic_write,
    convert_to_tracked_values,
    hash_analysis_script,
    hash_file,
    hash_firmware,
    is_cache_valid,
    update_manifest,
)
from render_template import FootnoteRegistry, render_template


class TestTrackedValue:
    """Test TrackedValue class."""

    def test_tracked_value_creation(self):
        """Test creating a TrackedValue."""
        tv = TrackedValue("0x2000", "kernel", "binwalk firmware.img | grep kernel")

        assert tv.value == "0x2000"
        assert tv.source == "kernel"
        assert tv.method == "binwalk firmware.img | grep kernel"

    def test_tracked_value_str(self):
        """Test string representation returns the value."""
        tv = TrackedValue(42, "test", "echo 42")
        assert str(tv) == "42"

    def test_tracked_value_repr(self):
        """Test repr shows all details."""
        tv = TrackedValue(42, "test", "echo 42")
        assert "TrackedValue" in repr(tv)
        assert "42" in repr(tv)
        assert "test" in repr(tv)

    def test_tracked_value_equality(self):
        """Test equality comparison."""
        tv1 = TrackedValue(42, "test", "method1")
        tv2 = TrackedValue(42, "test", "method2")
        tv3 = TrackedValue(43, "test", "method1")

        # TrackedValues with same value are equal
        assert tv1 == tv2
        assert tv1 != tv3

        # Can compare with raw values
        assert tv1 == 42
        assert tv1 != 43

    def test_tracked_value_int_conversion(self):
        """Test conversion to int."""
        tv = TrackedValue("42", "test", "method")
        assert int(tv) == 42

    def test_tracked_value_float_conversion(self):
        """Test conversion to float."""
        tv = TrackedValue("3.14", "test", "method")
        assert float(tv) == 3.14

    def test_tracked_value_no_method(self):
        """Test TrackedValue without method."""
        tv = TrackedValue("test", "source")
        assert tv.value == "test"
        assert tv.source == "source"
        assert tv.method is None


class TestFootnoteRegistry:
    """Test FootnoteRegistry class."""

    def test_registry_creation(self):
        """Test creating a FootnoteRegistry."""
        registry = FootnoteRegistry()
        assert registry.footnotes == []
        assert registry.footnote_map == {}

    def test_add_footnote(self):
        """Test adding footnotes."""
        registry = FootnoteRegistry()

        tv1 = TrackedValue("0x2000", "kernel", "binwalk -e")
        tv2 = TrackedValue("0x4000", "kernel", "binwalk -e")
        tv3 = TrackedValue("0x8000", "filesystem", "unsquashfs")

        # First unique footnote
        num1 = registry.add(tv1)
        assert num1 == 1

        # Same source+method should reuse footnote
        num2 = registry.add(tv2)
        assert num2 == 1

        # Different source+method gets new footnote
        num3 = registry.add(tv3)
        assert num3 == 2

    def test_add_same_footnote_twice(self):
        """Test adding the same footnote returns same number."""
        registry = FootnoteRegistry()
        tv1 = TrackedValue("value1", "test", "method")
        tv2 = TrackedValue("value2", "test", "method")  # Same source/method

        num1 = registry.add(tv1)
        num2 = registry.add(tv2)

        assert num1 == num2 == 1
        assert len(registry.footnotes) == 1

    def test_render_footnotes(self):
        """Test rendering footnotes as markdown."""
        registry = FootnoteRegistry()

        tv1 = TrackedValue("0x2000", "kernel", "binwalk -e")
        tv2 = TrackedValue("data", "filesystem", "ls -la")

        registry.add(tv1)
        registry.add(tv2)

        rendered = registry.render()

        assert "## Sources" in rendered
        assert "[^1]:" in rendered
        assert "[^2]:" in rendered
        assert "scripts/analyze_kernel.sh" in rendered
        assert "scripts/analyze_filesystem.sh" in rendered
        assert "binwalk -e" in rendered
        assert "ls -la" in rendered

    def test_render_empty_footnotes(self):
        """Test rendering with no footnotes."""
        registry = FootnoteRegistry()
        rendered = registry.render()
        assert rendered == ""

    def test_render_footnote_without_method(self):
        """Test rendering footnote without method."""
        registry = FootnoteRegistry()
        tv = TrackedValue("value", "test", None)
        registry.add(tv)

        rendered = registry.render()

        assert "[^1]:" in rendered
        assert "scripts/analyze_test.sh" in rendered
        # Should not have " - " when no method
        assert " - `" not in rendered


class TestConvertToTrackedValues:
    """Test convert_to_tracked_values function."""

    def test_convert_with_source_metadata(self):
        """Test converting dict with source metadata."""
        result = {
            "offset": "0x2000",
            "offset_source": "kernel",
            "offset_method": "binwalk firmware.img",
            "size": 1024,
        }

        tracked = convert_to_tracked_values(result, "kernel")

        assert isinstance(tracked["offset"], TrackedValue)
        assert tracked["offset"].value == "0x2000"
        assert tracked["offset"].source == "kernel"
        assert tracked["offset"].method == "binwalk firmware.img"

        # Size has no metadata, should be plain value
        assert tracked["size"] == 1024
        assert not isinstance(tracked["size"], TrackedValue)

    def test_convert_filters_metadata_keys(self):
        """Test that metadata keys are filtered out."""
        result = {
            "offset": "0x2000",
            "offset_source": "kernel",
            "offset_method": "binwalk",
        }

        tracked = convert_to_tracked_values(result, "kernel")

        assert "offset" in tracked
        assert "offset_source" not in tracked
        assert "offset_method" not in tracked

    def test_convert_uses_analysis_type_as_default_source(self):
        """Test that analysis_type is used as default source."""
        result = {
            "value": 42,
            "value_method": "echo 42",  # Has method but no source
        }

        tracked = convert_to_tracked_values(result, "test")

        assert isinstance(tracked["value"], TrackedValue)
        assert tracked["value"].source == "test"

    def test_convert_empty_dict(self):
        """Test converting empty dict."""
        result = {}
        tracked = convert_to_tracked_values(result, "test")
        assert tracked == {}


class TestHashFile:
    """Test hash_file function."""

    def test_hash_file(self, tmp_path):
        """Test hashing a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        hash1 = hash_file(test_file)

        # Should return 16-character hex string
        assert len(hash1) == 16
        assert all(c in "0123456789abcdef" for c in hash1)

    def test_hash_same_file_same_hash(self, tmp_path):
        """Test that same file produces same hash."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        hash1 = hash_file(test_file)
        hash2 = hash_file(test_file)

        assert hash1 == hash2

    def test_hash_different_content_different_hash(self, tmp_path):
        """Test that different content produces different hash."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("Content A")
        file2.write_text("Content B")

        hash1 = hash_file(file1)
        hash2 = hash_file(file2)

        assert hash1 != hash2


class TestAtomicWrite:
    """Test atomic_write context manager."""

    def test_atomic_write_creates_file(self, tmp_path):
        """Test that atomic_write creates a file."""
        test_file = tmp_path / "test.txt"

        with atomic_write(test_file) as f:
            f.write("Test content")

        assert test_file.exists()
        assert test_file.read_text() == "Test content"

    def test_atomic_write_creates_parent_dirs(self, tmp_path):
        """Test that atomic_write creates parent directories."""
        test_file = tmp_path / "subdir" / "test.txt"

        with atomic_write(test_file) as f:
            f.write("Test content")

        assert test_file.exists()

    def test_atomic_write_cleans_up_on_error(self, tmp_path):
        """Test that temp file is cleaned up on error."""
        test_file = tmp_path / "test.txt"

        with pytest.raises(ValueError), atomic_write(test_file) as f:
            f.write("Test")
            raise ValueError("Test error")

        # Original file should not exist
        assert not test_file.exists()

        # No .tmp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_atomic_write_overwrites_existing(self, tmp_path):
        """Test that atomic_write overwrites existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Old content")

        with atomic_write(test_file) as f:
            f.write("New content")

        assert test_file.read_text() == "New content"


class TestManifestFunctions:
    """Test manifest-related functions."""

    def test_update_manifest_creates_new(self, tmp_path, monkeypatch):
        """Test creating a new manifest file."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)
        results_dir = tmp_path / "results"
        results_dir.mkdir()

        manifest_file = results_dir / ".manifest.toml"

        # Create a dummy firmware file for hashing
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()
        firmware_file = downloads_dir / "firmware.img"
        firmware_file.write_bytes(b"fake firmware")

        # Create a dummy analysis script
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        script_file = scripts_dir / "analyze_test.sh"
        script_file.write_text("#!/bin/bash\necho test")

        update_manifest("test", manifest_file)

        assert manifest_file.exists()
        manifest = tomlkit.load(manifest_file.open())
        assert "test" in manifest
        assert "firmware_hash" in manifest["test"]
        assert "script_hash" in manifest["test"]
        assert "last_updated" in manifest["test"]

    def test_update_manifest_updates_existing(self, tmp_path, monkeypatch):
        """Test updating an existing manifest."""
        monkeypatch.chdir(tmp_path)
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        manifest_file = results_dir / ".manifest.toml"

        # Create initial manifest
        manifest = tomlkit.document()
        manifest["old_entry"] = {"firmware_hash": "old", "script_hash": "old"}
        with manifest_file.open("w") as f:
            tomlkit.dump(manifest, f)

        # Create dummy files
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()
        (downloads_dir / "firmware.img").write_bytes(b"firmware")
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "analyze_test.sh").write_text("script")

        update_manifest("test", manifest_file)

        manifest = tomlkit.load(manifest_file.open())
        assert "old_entry" in manifest  # Should preserve old entries
        assert "test" in manifest  # Should add new entry


class TestCacheValidation:
    """Test cache validation logic."""

    def test_cache_invalid_if_no_results_file(self, tmp_path, monkeypatch):
        """Test cache is invalid if results file doesn't exist."""
        monkeypatch.chdir(tmp_path)
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        manifest_file = results_dir / ".manifest.toml"

        # Create manifest but no results file
        manifest = tomlkit.document()
        manifest["test"] = {"firmware_hash": "abc", "script_hash": "def"}
        with manifest_file.open("w") as f:
            tomlkit.dump(manifest, f)

        assert not is_cache_valid("test", manifest_file)

    def test_cache_invalid_if_no_manifest(self, tmp_path, monkeypatch):
        """Test cache is invalid if manifest doesn't exist."""
        monkeypatch.chdir(tmp_path)
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        manifest_file = results_dir / ".manifest.toml"

        # Create results file but no manifest
        results_file = results_dir / "test.toml"
        results_file.write_text("test = 1")

        assert not is_cache_valid("test", manifest_file)

    def test_cache_invalid_if_not_in_manifest(self, tmp_path, monkeypatch):
        """Test cache is invalid if analysis type not in manifest."""
        monkeypatch.chdir(tmp_path)
        results_dir = tmp_path / "results"
        results_dir.mkdir()

        # Create results file and manifest, but different analysis type
        results_file = results_dir / "test.toml"
        results_file.write_text("test = 1")

        manifest_file = results_dir / ".manifest.toml"
        manifest = tomlkit.document()
        manifest["other"] = {"firmware_hash": "abc", "script_hash": "def"}
        with manifest_file.open("w") as f:
            tomlkit.dump(manifest, f)

        assert not is_cache_valid("test", manifest_file)

    def test_cache_valid_if_hashes_match(self, tmp_path, monkeypatch):
        """Test cache is valid if all hashes match."""
        monkeypatch.chdir(tmp_path)
        results_dir = tmp_path / "results"
        results_dir.mkdir()

        # Create firmware and script
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()
        firmware_file = downloads_dir / "firmware.img"
        firmware_file.write_bytes(b"firmware content")

        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        script_file = scripts_dir / "analyze_test.sh"
        script_file.write_text("#!/bin/bash\necho test")

        # Calculate actual hashes
        fw_hash = hash_file(firmware_file)
        script_hash = hash_file(script_file)

        # Create results file and manifest with matching hashes
        results_file = results_dir / "test.toml"
        results_file.write_text("test = 1")

        manifest_file = results_dir / ".manifest.toml"
        manifest = tomlkit.document()
        manifest["test"] = {
            "firmware_hash": fw_hash,
            "script_hash": script_hash,
            "last_updated": "2025-01-01T00:00:00",
        }
        with manifest_file.open("w") as f:
            tomlkit.dump(manifest, f)

        assert is_cache_valid("test", manifest_file)

    def test_cache_invalid_if_firmware_changed(self, tmp_path, monkeypatch):
        """Test cache is invalid if firmware hash changed."""
        monkeypatch.chdir(tmp_path)
        results_dir = tmp_path / "results"
        results_dir.mkdir()

        # Create initial firmware
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()
        firmware_file = downloads_dir / "firmware.img"
        firmware_file.write_bytes(b"original")
        old_hash = hash_file(firmware_file)

        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        script_file = scripts_dir / "analyze_test.sh"
        script_file.write_text("script")
        script_hash = hash_file(script_file)

        # Create manifest with old hash
        results_file = results_dir / "test.toml"
        results_file.write_text("test = 1")

        manifest_file = results_dir / ".manifest.toml"
        manifest = tomlkit.document()
        manifest["test"] = {
            "firmware_hash": old_hash,
            "script_hash": script_hash,
        }
        with manifest_file.open("w") as f:
            tomlkit.dump(manifest, f)

        # Change firmware
        firmware_file.write_bytes(b"modified")

        assert not is_cache_valid("test", manifest_file)


class TestTemplateRendering:
    """Test end-to-end template rendering."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.orig_cwd = Path.cwd()

        os.chdir(self.test_dir)

        # Create test structure
        (self.test_dir / "scripts").mkdir()
        (self.test_dir / "templates").mkdir()
        (self.test_dir / "results").mkdir()

        # Create test analysis script
        test_script = self.test_dir / "scripts" / "analyze_render_test.sh"
        test_script.write_text(
            """#!/usr/bin/env bash
cat <<'EOF'
{
  "offset": "0x2000",
  "offset_source": "render_test",
  "offset_method": "binwalk firmware.img"
}
EOF
"""
        )
        test_script.chmod(0o755)

    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.test_dir)

    def test_render_simple_template(self):
        """Test rendering a simple template."""
        template_file = self.test_dir / "templates" / "simple.md.j2"
        template_file.write_text("# Test\n\nHello, World!")

        result = render_template(template_file)

        assert result == "# Test\n\nHello, World!"

    def test_render_template_to_file(self):
        """Test rendering template to output file."""
        template_path = self.test_dir / "templates" / "test.md.j2"
        template_path.write_text("# Test\nSimple template")

        output_path = self.test_dir / "output" / "test.md"

        analyze.cache_clear()

        render_template(template_path, output_path)

        assert output_path.exists()
        assert "# Test" in output_path.read_text()

    def test_render_with_tracked_values(self):
        """Test rendering a template with tracked values."""
        # Create test template
        template_path = self.test_dir / "templates" / "test.md.j2"
        template_path.write_text(
            """
{% set data = analyze('render_test') %}
Offset: {{ data.offset | src }}
{{ render_footnotes() }}
"""
        )

        # Render template
        analyze.cache_clear()  # Clear cache for clean test

        rendered = render_template(template_path)

        # Check rendered content
        assert "Offset: 0x2000[^1]" in rendered
        assert "## Sources" in rendered
        assert "scripts/analyze_render_test.sh" in rendered
        assert "binwalk firmware.img" in rendered

    def test_render_with_src_filter(self):
        """Test template with |src filter for footnotes."""
        # Create dummy script first
        script_file = self.test_dir / "scripts" / "analyze_srctest.sh"
        script_file.write_text('#!/bin/bash\necho \'{"value": "test"}\'')
        script_file.chmod(0o755)

        # Create results file
        results_file = self.test_dir / "results" / "srctest.toml"
        results_file.write_text(
            'value = "test"\nvalue_source = "srctest"\nvalue_method = "echo test"'
        )

        # Create manifest with correct hashes
        manifest_file = self.test_dir / "results" / ".manifest.toml"
        manifest = tomlkit.document()
        manifest["srctest"] = {
            "firmware_hash": hash_firmware(),
            "script_hash": hash_file(script_file),
        }
        with manifest_file.open("w") as f:
            tomlkit.dump(manifest, f)

        # Create template
        template_file = self.test_dir / "templates" / "src.md.j2"
        template_file.write_text(
            "{% set data = analyze('srctest') %}\n"
            "Value: {{ data.value | src }}\n\n"
            "{{ render_footnotes() }}"
        )

        analyze.cache_clear()
        result = render_template(template_file)

        assert "Value: test[^1]" in result
        assert "## Sources" in result
        assert "[^1]:" in result


class TestAnalyzeFunction:
    """Test analyze() function."""

    def test_analyze_runs_bash_script(self, tmp_path, monkeypatch):
        """Test that analyze() runs bash script if it exists."""
        monkeypatch.chdir(tmp_path)

        # Create directories
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()

        # Create a bash script that outputs JSON
        script_file = scripts_dir / "analyze_test.sh"
        script_file.write_text("#!/bin/bash\necho '{\"value\": 42}'")
        script_file.chmod(0o755)

        # Clear the cache (analyze uses @lru_cache)
        analyze.cache_clear()

        result = analyze("test")

        assert result["value"] == 42

    def test_analyze_caches_results(self, tmp_path, monkeypatch):
        """Test that analyze() caches results to TOML file."""
        monkeypatch.chdir(tmp_path)

        # Setup
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()

        script_file = scripts_dir / "analyze_cache_test.sh"
        script_file.write_text('#!/bin/bash\necho \'{"cached": "yes"}\'')
        script_file.chmod(0o755)

        analyze.cache_clear()
        analyze("cache_test")

        # Check that results were saved
        results_file = results_dir / "cache_test.toml"
        assert results_file.exists()

        # Check manifest was updated
        manifest_file = results_dir / ".manifest.toml"
        assert manifest_file.exists()

    def test_analyze_raises_on_missing_script(self, tmp_path, monkeypatch):
        """Test that analyze() raises error if script doesn't exist."""
        monkeypatch.chdir(tmp_path)

        # Create directories but no script
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()

        analyze.cache_clear()

        with pytest.raises(FileNotFoundError) as excinfo:
            analyze("nonexistent")

        assert "nonexistent" in str(excinfo.value)

    def test_analyze_uses_cached_results(self, tmp_path, monkeypatch):
        """Test that analyze() uses cached results when valid."""
        monkeypatch.chdir(tmp_path)

        # Setup
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()
        firmware_file = downloads_dir / "firmware.img"
        firmware_file.write_bytes(b"firmware")

        script_file = scripts_dir / "analyze_cached.sh"
        script_file.write_text("#!/bin/bash\necho '{\"value\": 1}'")
        script_file.chmod(0o755)

        # Create results file with different value
        results_file = results_dir / "cached.toml"
        results_file.write_text("value = 999")

        # Create valid manifest
        manifest_file = results_dir / ".manifest.toml"
        manifest = tomlkit.document()
        manifest["cached"] = {
            "firmware_hash": hash_file(firmware_file),
            "script_hash": hash_file(script_file),
        }
        with manifest_file.open("w") as f:
            tomlkit.dump(manifest, f)

        analyze.cache_clear()
        result = analyze("cached")

        # Should use cached value (999), not run script (which would return 1)
        assert result["value"] == 999


class TestIntegrationWithRealTemplates:
    """Integration tests with realistic templates and data."""

    def test_full_workflow(self, tmp_path, monkeypatch):
        """Test complete workflow: script -> results -> template -> output."""
        monkeypatch.chdir(tmp_path)

        # Setup directory structure
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()

        # Create analysis script
        script_file = scripts_dir / "analyze_kernel.sh"
        script_content = """#!/bin/bash
cat <<EOF
{
  "offset": "0x2000",
  "offset_source": "kernel",
  "offset_method": "binwalk firmware.img | grep kernel",
  "size": 4194304,
  "size_source": "kernel",
  "compression": "gzip"
}
EOF
"""
        script_file.write_text(script_content)
        script_file.chmod(0o755)

        # Create template
        template_file = tmp_path / "kernel.md.j2"
        template_content = """{% set k = analyze('kernel') %}
# Kernel Extraction

Offset: {{ k.offset | src }}
Size: {{ k.size }} bytes
Compression: {{ k.compression }}

{{ render_footnotes() }}
"""
        template_file.write_text(template_content)

        # Render template
        analyze.cache_clear()
        output_file = tmp_path / "kernel.md"
        render_template(template_file, output_file)

        # Verify output
        assert output_file.exists()
        content = output_file.read_text()
        assert "Offset: 0x2000[^1]" in content
        assert "Size: 4194304 bytes" in content
        assert "Compression: gzip" in content
        assert "## Sources" in content
        assert "[^1]:" in content
        assert "scripts/analyze_kernel.sh" in content

    def test_multiple_footnotes_same_source(self, tmp_path, monkeypatch):
        """Test that multiple values from same source share one footnote."""
        monkeypatch.chdir(tmp_path)

        # Setup
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()

        # Create dummy script
        script_file = scripts_dir / "analyze_multi.sh"
        script_file.write_text('#!/bin/bash\necho \'{"val1": "first"}\'')
        script_file.chmod(0o755)

        # Create results with multiple values from same source
        results_file = results_dir / "multi.toml"
        results_content = """
val1 = "first"
val1_source = "multi"
val1_method = "method1"
val2 = "second"
val2_source = "multi"
val2_method = "method1"
val3 = "third"
val3_source = "multi"
val3_method = "method2"
"""
        results_file.write_text(results_content)

        # Create manifest with correct hashes
        manifest_file = results_dir / ".manifest.toml"
        manifest = tomlkit.document()
        manifest["multi"] = {
            "firmware_hash": hash_firmware(),
            "script_hash": hash_file(script_file),
        }
        with manifest_file.open("w") as f:
            tomlkit.dump(manifest, f)

        # Create template
        template_file = tmp_path / "multi.md.j2"
        template_content = """{% set d = analyze('multi') %}
Value 1: {{ d.val1 | src }}
Value 2: {{ d.val2 | src }}
Value 3: {{ d.val3 | src }}

{{ render_footnotes() }}
"""
        template_file.write_text(template_content)

        analyze.cache_clear()
        result = render_template(template_file)

        # val1 and val2 share same source/method, should get [^1]
        # val3 has different method, should get [^2]
        assert "Value 1: first[^1]" in result
        assert "Value 2: second[^1]" in result
        assert "Value 3: third[^2]" in result
        assert "[^1]:" in result
        assert "[^2]:" in result


class TestErrorHandling:
    """Test error handling in various scenarios."""

    def test_script_returns_invalid_json(self, tmp_path, monkeypatch):
        """Test error when script returns invalid JSON."""
        monkeypatch.chdir(tmp_path)

        results_dir = tmp_path / "results"
        results_dir.mkdir()
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()

        # Create script that outputs invalid JSON
        script_file = scripts_dir / "analyze_badjson.sh"
        script_file.write_text("#!/bin/bash\necho 'not json'")
        script_file.chmod(0o755)

        analyze.cache_clear()

        with pytest.raises(json.JSONDecodeError):
            analyze("badjson")


class TestHashFirmware:
    """Test hash_firmware function."""

    def test_hash_firmware_no_file(self, tmp_path, monkeypatch):
        """Test hash_firmware when firmware doesn't exist."""
        monkeypatch.chdir(tmp_path)

        # No downloads directory, should return placeholder
        result = hash_firmware()

        assert result == "no-firmware-yet"

    def test_hash_firmware_with_file(self, tmp_path, monkeypatch):
        """Test hash_firmware when firmware exists."""
        monkeypatch.chdir(tmp_path)

        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()
        firmware_file = downloads_dir / "firmware.img"
        firmware_file.write_bytes(b"firmware content")

        result = hash_firmware()

        # Should return actual hash
        assert result != "no-firmware-yet"
        assert len(result) == 16


class TestHashAnalysisScript:
    """Test hash_analysis_script function."""

    def test_hash_script_bash(self, tmp_path, monkeypatch):
        """Test hashing a bash script."""
        monkeypatch.chdir(tmp_path)

        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        script_file = scripts_dir / "analyze_test.sh"
        script_file.write_text("#!/bin/bash\necho test")

        result = hash_analysis_script("test")

        assert len(result) == 16
        assert result != "unknown"

    def test_hash_script_python(self, tmp_path, monkeypatch):
        """Test hashing a python script."""
        monkeypatch.chdir(tmp_path)

        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        script_file = scripts_dir / "analyze_test.py"
        script_file.write_text("#!/usr/bin/env python3\nprint('test')")

        result = hash_analysis_script("test")

        assert len(result) == 16
        assert result != "unknown"

    def test_hash_script_not_found(self, tmp_path, monkeypatch):
        """Test when no script exists."""
        monkeypatch.chdir(tmp_path)

        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()

        result = hash_analysis_script("nonexistent")

        assert result == "unknown"
