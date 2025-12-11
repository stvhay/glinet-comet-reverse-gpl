#!/usr/bin/env python3
"""
Tests for scripts/render_template.py
"""

import sys
from pathlib import Path
import tempfile
import shutil

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from analysis import TrackedValue
from render_template import FootnoteRegistry, render_template


class TestFootnoteRegistry:
    """Test FootnoteRegistry class."""

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


class TestTemplateRendering:
    """Test end-to-end template rendering."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.orig_cwd = Path.cwd()

        import os
        os.chdir(self.test_dir)

        # Create test structure
        (self.test_dir / "scripts").mkdir()
        (self.test_dir / "templates").mkdir()
        (self.test_dir / "results").mkdir()

        # Create test analysis script
        test_script = self.test_dir / "scripts" / "analyze_render_test.sh"
        test_script.write_text("""#!/usr/bin/env bash
cat <<'EOF'
{
  "offset": "0x2000",
  "offset_source": "render_test",
  "offset_method": "binwalk firmware.img"
}
EOF
""")
        test_script.chmod(0o755)

    def teardown_method(self):
        """Clean up test environment."""
        import os
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.test_dir)

    def test_render_with_tracked_values(self):
        """Test rendering a template with tracked values."""
        # Create test template
        template_path = self.test_dir / "templates" / "test.md.j2"
        template_path.write_text("""
{% set data = analyze('render_test') %}
Offset: {{ data.offset | src }}
{{ render_footnotes() }}
""")

        # Render template
        from analysis import analyze
        analyze.cache_clear()  # Clear cache for clean test

        rendered = render_template(template_path)

        # Check rendered content
        assert "Offset: 0x2000[^1]" in rendered
        assert "## Sources" in rendered
        assert "scripts/analyze_render_test.sh" in rendered
        assert "binwalk firmware.img" in rendered

    def test_render_to_file(self):
        """Test rendering template to output file."""
        template_path = self.test_dir / "templates" / "test.md.j2"
        template_path.write_text("# Test\nSimple template")

        output_path = self.test_dir / "output" / "test.md"

        from analysis import analyze
        analyze.cache_clear()

        render_template(template_path, output_path)

        assert output_path.exists()
        assert "# Test" in output_path.read_text()
