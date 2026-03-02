#!/usr/bin/env python3
"""Tests for scripts/insert_citations.py — citation insertion tool."""

import sys
from pathlib import Path

import tomlkit

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from insert_citations import (
    CitationRef,
    build_reverse_index,
    compute_code_block_mask,
    extract_fact_values,
    process_file,
)
from verify_traceability import check_uncited_facts


class TestExtractFactValues:
    """Test fact value extraction from text lines."""

    def test_hex_offset(self) -> None:
        matches = extract_fact_values("The offset is 0x1000 in the firmware.")
        assert len(matches) == 1
        assert matches[0] == ("0x1000", "hex offset")

    def test_version_string(self) -> None:
        matches = extract_fact_values("Linux kernel 4.19.111 is used.")
        assert len(matches) == 1
        assert matches[0] == ("4.19.111", "version string")

    def test_sha_hash(self) -> None:
        sha = "a" * 40
        matches = extract_fact_values(f"Commit: {sha}")
        assert len(matches) == 1
        assert matches[0] == (sha, "SHA hash")

    def test_absolute_path(self) -> None:
        matches = extract_fact_values("Found at /usr/lib/librga.so")
        assert len(matches) == 1
        assert matches[0] == ("/usr/lib/librga.so", "absolute path")

    def test_no_match(self) -> None:
        matches = extract_fact_values("Nothing special here.")
        assert len(matches) == 0

    def test_multi_match(self) -> None:
        matches = extract_fact_values("Offset 0x1000 and version 4.19.111")
        assert len(matches) == 2
        values = {m[0] for m in matches}
        assert "0x1000" in values
        assert "4.19.111" in values


class TestBuildReverseIndex:
    """Test reverse index building from TOML files."""

    def test_scalar_indexed(self, tmp_path: Path) -> None:
        results = tmp_path / "results"
        results.mkdir()
        doc = tomlkit.document()
        doc.add("uboot_offset", "0x901B4")
        (results / "binwalk.toml").write_text(tomlkit.dumps(doc))

        index = build_reverse_index(results)
        assert "0x901B4" in index
        assert index["0x901B4"].toml_file == "results/binwalk.toml"
        assert index["0x901B4"].field_name == "uboot_offset"
        assert index["0x901B4"].is_scalar is True

    def test_embedded_version(self, tmp_path: Path) -> None:
        results = tmp_path / "results"
        results.mkdir()
        doc = tomlkit.document()
        doc.add("kernel_version", "vermagic=4.19.111 SMP preempt mod_unload ARMv7 p2v8")
        (results / "rootfs.toml").write_text(tomlkit.dumps(doc))

        index = build_reverse_index(results)
        assert "4.19.111" in index
        assert index["4.19.111"].field_name == "kernel_version"

    def test_array_of_objects(self, tmp_path: Path) -> None:
        results = tmp_path / "results"
        results.mkdir()
        content = """\
[[partitions]]
region = "Bootloader"
offset = "0x8F1B4"
type = "FIT"
"""
        (results / "boot_process.toml").write_text(content)

        index = build_reverse_index(results)
        assert "0x8F1B4" in index
        assert index["0x8F1B4"].field_name == "partitions"
        assert index["0x8F1B4"].is_scalar is False

    def test_string_array(self, tmp_path: Path) -> None:
        results = tmp_path / "results"
        results.mkdir()
        doc = tomlkit.document()
        doc.add(
            "recovery_modes",
            ["boot mode: recovery (cmd)", "boot mode: recovery (key)"],
        )
        (results / "uboot.toml").write_text(tomlkit.dumps(doc))

        index = build_reverse_index(results)
        # These strings don't match any fact patterns, so they won't be indexed
        assert len(index) == 0

    def test_string_array_with_paths(self, tmp_path: Path) -> None:
        results = tmp_path / "results"
        results.mkdir()
        doc = tomlkit.document()
        doc.add(
            "all_rockchip_libs",
            ["/usr/lib/librga.so", "/usr/lib/librockchip_mpp.so"],
        )
        (results / "proprietary_blobs.toml").write_text(tomlkit.dumps(doc))

        index = build_reverse_index(results)
        assert "/usr/lib/librga.so" in index
        assert index["/usr/lib/librga.so"].field_name == "all_rockchip_libs"

    def test_priority_scalar_over_array(self, tmp_path: Path) -> None:
        results = tmp_path / "results"
        results.mkdir()
        # File 1: scalar with offset
        doc1 = tomlkit.document()
        doc1.add("uboot_offset", "0x901B4")
        (results / "binwalk.toml").write_text(tomlkit.dumps(doc1))

        # File 2: array with same offset
        content = """\
[[identified_components]]
offset = "0x901B4"
type = "gzip"
"""
        # Write second file that also has the value but as array
        (results / "boot_process.toml").write_text(content)

        index = build_reverse_index(results)
        assert "0x901B4" in index
        # Scalar should win
        assert index["0x901B4"].is_scalar is True

    def test_priority_binwalk_over_rootfs(self, tmp_path: Path) -> None:
        results = tmp_path / "results"
        results.mkdir()
        # binwalk.toml (priority 0)
        doc1 = tomlkit.document()
        doc1.add("squashfs_offset", "0x1CEA1B4")
        (results / "binwalk.toml").write_text(tomlkit.dumps(doc1))

        # rootfs.toml (priority 2) — both scalar, so priority decides
        doc2 = tomlkit.document()
        doc2.add("some_offset", "0x1CEA1B4")
        (results / "rootfs.toml").write_text(tomlkit.dumps(doc2))

        index = build_reverse_index(results)
        assert index["0x1CEA1B4"].toml_file == "results/binwalk.toml"

    def test_skips_test_toml(self, tmp_path: Path) -> None:
        results = tmp_path / "results"
        results.mkdir()
        doc = tomlkit.document()
        doc.add("offset", "0xDEAD")
        (results / "test.toml").write_text(tomlkit.dumps(doc))

        index = build_reverse_index(results)
        assert len(index) == 0

    def test_skips_manifest_toml(self, tmp_path: Path) -> None:
        results = tmp_path / "results"
        results.mkdir()
        doc = tomlkit.document()
        doc.add("offset", "0xBEEF")
        (results / ".manifest.toml").write_text(tomlkit.dumps(doc))

        index = build_reverse_index(results)
        assert len(index) == 0

    def test_table_subfields(self, tmp_path: Path) -> None:
        results = tmp_path / "results"
        results.mkdir()
        content = """\
[ssh_server]
name = "sshd"
path = "/etc/ssh/sshd_config"
description = "OpenSSH server"
"""
        (results / "network_services.toml").write_text(content)

        index = build_reverse_index(results)
        assert "/etc/ssh/sshd_config" in index
        assert index["/etc/ssh/sshd_config"].field_name == "ssh_server"


class TestComputeCodeBlockMask:
    """Test fenced code block mask computation."""

    def test_no_blocks(self) -> None:
        lines = ["normal line", "another line"]
        mask = compute_code_block_mask(lines)
        assert mask == [False, False]

    def test_single_block(self) -> None:
        lines = ["before", "```", "inside", "```", "after"]
        mask = compute_code_block_mask(lines)
        assert mask == [False, True, True, False, False]

    def test_toggle_behavior(self) -> None:
        lines = ["```", "code", "```", "text", "```", "more code", "```"]
        mask = compute_code_block_mask(lines)
        assert mask == [True, True, False, False, True, True, False]

    def test_language_specifier(self) -> None:
        lines = ["```bash", "echo hello", "```"]
        mask = compute_code_block_mask(lines)
        assert mask == [True, True, False]


class TestProcessFile:
    """Test Markdown file processing."""

    def _make_index(self, mapping: dict[str, tuple[str, str, bool]]) -> dict[str, CitationRef]:
        """Helper to build a simple index from value -> (toml_file, field, is_scalar)."""
        index: dict[str, CitationRef] = {}
        for value, (tf, fn, sc) in mapping.items():
            index[value] = CitationRef(toml_file=tf, field_name=fn, is_scalar=sc)
        return index

    def test_inserts_citation(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text("The offset is 0x1000 in the firmware.\n")
        index = self._make_index({"0x1000": ("results/binwalk.toml", "uboot_offset", True)})

        result = process_file(doc, index, dry_run=False)
        assert result.citations_added == 1
        content = doc.read_text()
        assert "<!-- cite: results/binwalk.toml#uboot_offset -->" in content

    def test_idempotent(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text("The offset is 0x1000. <!-- cite: results/binwalk.toml#uboot_offset -->\n")
        index = self._make_index({"0x1000": ("results/binwalk.toml", "uboot_offset", True)})

        result = process_file(doc, index, dry_run=False)
        assert result.citations_added == 0
        content = doc.read_text()
        # Should still have exactly one citation
        assert content.count("<!-- cite:") == 1

    def test_skips_code_blocks(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text("```\n0x1000\n```\n")
        index = self._make_index({"0x1000": ("results/binwalk.toml", "uboot_offset", True)})

        result = process_file(doc, index, dry_run=False)
        assert result.citations_added == 0

    def test_preserves_existing_citations(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text(
            "Offset 0x1000 <!-- cite: results/other.toml#field -->\nAnother 0x2000 line.\n"
        )
        index = self._make_index(
            {
                "0x1000": ("results/binwalk.toml", "uboot_offset", True),
                "0x2000": ("results/binwalk.toml", "other_offset", True),
            }
        )

        result = process_file(doc, index, dry_run=False)
        assert result.citations_added == 1
        content = doc.read_text()
        # First line unchanged
        assert "<!-- cite: results/other.toml#field -->" in content
        # Second line gets citation
        assert "<!-- cite: results/binwalk.toml#other_offset -->" in content

    def test_reports_gaps(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text("Unknown offset 0xDEAD in the firmware.\n")
        index: dict[str, CitationRef] = {}

        result = process_file(doc, index, dry_run=False)
        assert result.citations_added == 0
        assert len(result.gaps) == 1
        assert "0xDEAD" in result.gaps[0]

    def test_dry_run(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        original = "The offset is 0x1000 in the firmware.\n"
        doc.write_text(original)
        index = self._make_index({"0x1000": ("results/binwalk.toml", "uboot_offset", True)})

        result = process_file(doc, index, dry_run=True)
        assert result.citations_added == 1
        # File should not be modified
        assert doc.read_text() == original

    def test_multi_ref_single_comment(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text("Offset 0x1000 and version 2.3.4 on same line.\n")
        index = self._make_index(
            {
                "0x1000": ("results/binwalk.toml", "offset", True),
                "2.3.4": ("results/rootfs.toml", "version", True),
            }
        )

        result = process_file(doc, index, dry_run=False)
        assert result.citations_added == 1
        content = doc.read_text()
        # Both refs in one comment
        assert "results/binwalk.toml#offset" in content
        assert "results/rootfs.toml#version" in content
        # Only one citation comment
        assert content.count("<!-- cite:") == 1

    def test_table_row_gets_citation(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text("| Offset | 0x1000 |\n")
        index = self._make_index({"0x1000": ("results/binwalk.toml", "uboot_offset", True)})

        result = process_file(doc, index, dry_run=False)
        assert result.citations_added == 1
        content = doc.read_text()
        assert "<!-- cite:" in content

    def test_no_newline_at_eof(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text("Offset 0x1000")  # no trailing newline
        index = self._make_index({"0x1000": ("results/binwalk.toml", "uboot_offset", True)})

        result = process_file(doc, index, dry_run=False)
        assert result.citations_added == 1
        content = doc.read_text()
        assert "<!-- cite: results/binwalk.toml#uboot_offset -->" in content


class TestIntegration:
    """End-to-end integration tests."""

    def test_insert_then_verify(self, tmp_path: Path) -> None:
        """Create sample TOML + docs, run insert, verify with check_uncited_facts."""
        # Create results
        results = tmp_path / "results"
        results.mkdir()
        doc = tomlkit.document()
        doc.add("uboot_offset", "0x901B4")
        doc.add("version", "U-Boot 2017.09")
        (results / "binwalk.toml").write_text(tomlkit.dumps(doc))

        # Create docs
        docs = tmp_path / "docs"
        docs.mkdir()
        md = docs / "test.md"
        md.write_text(
            "# Analysis\n\nU-Boot found at 0x901B4 in the firmware.\n\nThe version is 2017.09.\n"
        )

        # Verify uncited facts exist before insertion
        warnings_before = check_uncited_facts(md)
        assert len(warnings_before) > 0

        # Build index and process
        index = build_reverse_index(results)
        result = process_file(md, index, dry_run=False)
        assert result.citations_added > 0

        # Verify no uncited facts remain
        warnings_after = check_uncited_facts(md)
        assert len(warnings_after) == 0

    def test_insert_preserves_file_structure(self, tmp_path: Path) -> None:
        """Verify insertion doesn't corrupt Markdown structure."""
        results = tmp_path / "results"
        results.mkdir()
        doc = tomlkit.document()
        doc.add("kernel_offset", "0x49B9B4")
        (results / "binwalk.toml").write_text(tomlkit.dumps(doc))

        docs = tmp_path / "docs"
        docs.mkdir()
        md = docs / "test.md"
        original = (
            "# Title\n"
            "\n"
            "Some text about offset 0x49B9B4.\n"
            "\n"
            "```bash\n"
            "echo 0x49B9B4\n"
            "```\n"
            "\n"
            "More text.\n"
        )
        md.write_text(original)

        index = build_reverse_index(results)
        process_file(md, index, dry_run=False)

        content = md.read_text()
        lines = content.splitlines()

        # Title preserved
        assert lines[0] == "# Title"
        # Code block intact
        assert "```bash" in content
        # Citation only on the prose line, not the code block line
        assert content.count("<!-- cite:") == 1
        # The code block line should not have a citation
        for line in lines:
            if line.strip() == "echo 0x49B9B4":
                assert "<!-- cite:" not in line
