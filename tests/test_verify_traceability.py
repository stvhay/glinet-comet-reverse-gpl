#!/usr/bin/env python3
"""Tests for scripts/verify_traceability.py — citation verifier."""

import sys
from pathlib import Path

import tomlkit

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from verify_traceability import (
    check_citation_integrity,
    check_uncited_facts,
    find_markdown_docs,
    has_adjacent_citation,
    is_in_code_block,
    parse_citations,
)


class TestFindMarkdownDocs:
    """Test documentation file discovery."""

    def test_finds_md_files(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Hello")
        (tmp_path / "guide.md").write_text("# Guide")
        docs = find_markdown_docs(tmp_path)
        assert len(docs) == 2

    def test_skips_plans_subdir(self, tmp_path: Path) -> None:
        (tmp_path / "plans").mkdir()
        (tmp_path / "plans" / "draft.md").write_text("# Draft")
        (tmp_path / "top.md").write_text("# Top")
        docs = find_markdown_docs(tmp_path)
        assert len(docs) == 1
        assert docs[0].name == "top.md"

    def test_skips_archive_subdir(self, tmp_path: Path) -> None:
        (tmp_path / "archive").mkdir()
        (tmp_path / "archive" / "old.md").write_text("# Old")
        docs = find_markdown_docs(tmp_path)
        assert len(docs) == 0

    def test_skips_quality_subdir(self, tmp_path: Path) -> None:
        (tmp_path / "quality").mkdir()
        (tmp_path / "quality" / "policy.md").write_text("# Policy")
        docs = find_markdown_docs(tmp_path)
        assert len(docs) == 0


class TestParseCitations:
    """Test citation parsing from Markdown files."""

    def test_single_citation(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text("The version is 1.0. <!-- cite: results/uboot.toml#version -->\n")
        citations = parse_citations(doc)
        assert len(citations) == 1
        assert citations[0].toml_file == "results/uboot.toml"
        assert citations[0].field_name == "version"
        assert citations[0].line_number == 1

    def test_multi_ref_citation(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text(
            "Info here. <!-- cite: results/uboot.toml#version, results/binwalk.toml#offset -->\n"
        )
        citations = parse_citations(doc)
        assert len(citations) == 2
        assert citations[0].field_name == "version"
        assert citations[1].toml_file == "results/binwalk.toml"
        assert citations[1].field_name == "offset"

    def test_no_citations(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text("No citations here.\n")
        citations = parse_citations(doc)
        assert len(citations) == 0

    def test_multiple_citations_in_file(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text(
            "Line one <!-- cite: results/uboot.toml#version -->\n"
            "Line two\n"
            "Line three <!-- cite: results/binwalk.toml#offset -->\n"
        )
        citations = parse_citations(doc)
        assert len(citations) == 2
        assert citations[0].line_number == 1
        assert citations[1].line_number == 3


class TestCitationIntegrity:
    """Test citation integrity checking."""

    def test_valid_citation_passes(self, tmp_path: Path) -> None:
        toml_dir = tmp_path / "results"
        toml_dir.mkdir()
        doc = tomlkit.document()
        doc.add("version", "2017.09")
        (toml_dir / "uboot.toml").write_text(tomlkit.dumps(doc))

        doc_file = tmp_path / "test.md"
        doc_file.write_text("Version <!-- cite: results/uboot.toml#version -->\n")

        citations = parse_citations(doc_file)
        errors = check_citation_integrity(citations, tmp_path)
        assert len(errors) == 0

    def test_missing_toml_file_errors(self, tmp_path: Path) -> None:
        doc_file = tmp_path / "test.md"
        doc_file.write_text("Version <!-- cite: results/missing.toml#version -->\n")

        citations = parse_citations(doc_file)
        errors = check_citation_integrity(citations, tmp_path)
        assert len(errors) == 1
        assert errors[0].severity == "error"
        assert errors[0].check == "citation_integrity"
        assert "not found" in errors[0].message

    def test_missing_field_errors(self, tmp_path: Path) -> None:
        toml_dir = tmp_path / "results"
        toml_dir.mkdir()
        doc = tomlkit.document()
        doc.add("version", "2017.09")
        (toml_dir / "uboot.toml").write_text(tomlkit.dumps(doc))

        doc_file = tmp_path / "test.md"
        doc_file.write_text("Offset <!-- cite: results/uboot.toml#nonexistent -->\n")

        citations = parse_citations(doc_file)
        errors = check_citation_integrity(citations, tmp_path)
        assert len(errors) == 1
        assert errors[0].severity == "error"
        assert "nonexistent" in errors[0].message


class TestCodeBlockDetection:
    """Test fenced code block detection."""

    def test_not_in_block(self) -> None:
        lines = ["normal line", "another line"]
        assert not is_in_code_block(lines, 1)

    def test_in_block(self) -> None:
        lines = ["```", "code here", "more code", "```"]
        assert is_in_code_block(lines, 1)
        assert is_in_code_block(lines, 2)

    def test_after_block(self) -> None:
        lines = ["```", "code", "```", "normal"]
        assert not is_in_code_block(lines, 3)


class TestAdjacentCitation:
    """Test adjacent citation detection."""

    def test_same_line(self) -> None:
        lines = ["value 0x100 <!-- cite: results/uboot.toml#offset -->"]
        assert has_adjacent_citation(lines, 0)

    def test_next_line(self) -> None:
        lines = ["value 0x100", "<!-- cite: results/uboot.toml#offset -->"]
        assert has_adjacent_citation(lines, 0)

    def test_no_adjacent(self) -> None:
        lines = ["value 0x100", "unrelated line", "another line"]
        assert not has_adjacent_citation(lines, 0)


class TestUncitedFacts:
    """Test uncited fact detection."""

    def test_uncited_hex_offset_warns(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text("The offset is 0x1000 in the firmware.\n")
        warnings = check_uncited_facts(doc)
        assert len(warnings) == 1
        assert warnings[0].severity == "warning"
        assert warnings[0].check == "uncited_fact"

    def test_cited_hex_no_warning(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text("The offset is 0x1000. <!-- cite: results/uboot.toml#offset -->\n")
        warnings = check_uncited_facts(doc)
        assert len(warnings) == 0

    def test_hex_in_code_block_no_warning(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text("```\n0x1000\n```\n")
        warnings = check_uncited_facts(doc)
        assert len(warnings) == 0

    def test_uncited_version_warns(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text("Uses version 4.19.111 of the kernel.\n")
        warnings = check_uncited_facts(doc)
        assert len(warnings) == 1
        assert "version string" in warnings[0].message

    def test_uncited_sha_hash_warns(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        sha = "a" * 40
        doc.write_text(f"Commit hash: {sha}\n")
        warnings = check_uncited_facts(doc)
        assert len(warnings) == 1
        assert "SHA hash" in warnings[0].message
