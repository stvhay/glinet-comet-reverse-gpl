#!/usr/bin/env python3
"""Automated citation insertion for Markdown documentation.

Scans TOML result files to build a reverse index of fact values, then inserts
<!-- cite: results/file.toml#field --> comments into Markdown lines that contain
matching factual claims but lack citations.

Usage:
    python scripts/insert_citations.py --docs-dir docs --wiki-dir wiki --dry-run
    python scripts/insert_citations.py --docs-dir docs --wiki-dir wiki
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import tomlkit

sys.path.insert(0, str(Path(__file__).parent))

from lib.logging import info, section, success, warn
from verify_traceability import (
    UNCITED_FACT_PATTERNS,
    find_markdown_docs,
    has_adjacent_citation,
)

# TOML files to skip during index building
SKIP_TOML_FILES = {"test.toml", ".manifest.toml"}

# Markdown files to skip (Jinja-generated)
SKIP_MD_FILES = {"Device-Tree-Analysis.md"}

# Priority ranking for TOML files (lower = preferred)
TOML_PRIORITY: dict[str, int] = {
    "binwalk.toml": 0,
    "uboot.toml": 1,
    "rootfs.toml": 2,
    "boot_process.toml": 3,
    "secure_boot.toml": 4,
    "device_trees.toml": 5,
    "device_tree_diff.toml": 6,
    "network_services.toml": 7,
    "proprietary_blobs.toml": 8,
}

# Sub-fields to extract from array-of-objects and tables
INTERESTING_SUBFIELDS = {
    "name",
    "path",
    "offset",
    "description",
    "version",
    "evidence",
    "license",
    "component",
    "stage",
    "region",
    "type",
    "content",
    "purpose",
    "compatible",
    "model",
    "username",
    "hash_type",
}


@dataclass
class CitationRef:
    """A reference from a fact value back to a TOML field."""

    toml_file: str
    field_name: str
    is_scalar: bool
    priority: int = 99


@dataclass
class InsertionResult:
    """Result of processing a single Markdown file."""

    file_path: Path
    citations_added: int = 0
    gaps: list[str] = field(default_factory=list)


def extract_fact_values(text: str) -> list[tuple[str, str]]:
    """Extract factual values from a text line using verifier patterns.

    Returns list of (matched_value, description) tuples.
    """
    matches = []
    for pattern, description in UNCITED_FACT_PATTERNS:
        for m in pattern.finditer(text):
            matches.append((m.group(0), description))
    return matches


def _get_toml_priority(filename: str) -> int:
    """Get priority for a TOML file (lower = preferred)."""
    return TOML_PRIORITY.get(filename, 99)


def _register_value(
    index: dict[str, CitationRef],
    value: str,
    toml_file: str,
    field_name: str,
    is_scalar: bool,
) -> None:
    """Register a fact value in the reverse index with conflict resolution."""
    facts = extract_fact_values(value)
    priority = _get_toml_priority(Path(toml_file).name)
    ref = CitationRef(
        toml_file=toml_file,
        field_name=field_name,
        is_scalar=is_scalar,
        priority=priority,
    )

    for matched_value, _ in facts:
        existing = index.get(matched_value)
        if existing is None or (ref.is_scalar and not existing.is_scalar):
            index[matched_value] = ref
        elif existing.is_scalar and not ref.is_scalar:
            pass  # keep existing scalar
        elif ref.priority < existing.priority:
            index[matched_value] = ref


def _extract_embedded_versions(value: str) -> list[str]:
    """Extract embedded version substrings from a longer string.

    E.g. "vermagic=4.19.111 SMP preempt" -> ["4.19.111"]
    """
    version_re = re.compile(r"\d+\.\d+\.\d+")
    return version_re.findall(value)


def _register_with_embedded(
    index: dict[str, CitationRef],
    value: str,
    toml_ref: str,
    key: str,
    is_scalar: bool,
) -> None:
    """Register a value and any embedded version substrings."""
    _register_value(index, value, toml_ref, key, is_scalar=is_scalar)
    for ver in _extract_embedded_versions(value):
        if ver != value:
            _register_value(index, ver, toml_ref, key, is_scalar=is_scalar)


def _index_dict_subfields(
    index: dict[str, CitationRef], obj: dict, toml_ref: str, key: str
) -> None:
    """Index interesting sub-fields from a dict/table."""
    for subfield in INTERESTING_SUBFIELDS:
        subval = obj.get(subfield)
        if isinstance(subval, str):
            _register_with_embedded(index, subval, toml_ref, key, is_scalar=False)


def _index_value(index: dict[str, CitationRef], key: str, value: object, toml_ref: str) -> None:
    """Index a single top-level TOML key/value pair."""
    if isinstance(value, str):
        _register_with_embedded(index, value, toml_ref, key, is_scalar=True)
    elif isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            for item in value:
                _index_dict_subfields(index, item, toml_ref, key)
        elif isinstance(first, str):
            for entry in value:
                if isinstance(entry, str):
                    _register_with_embedded(index, entry, toml_ref, key, is_scalar=False)
    elif isinstance(value, dict):
        _index_dict_subfields(index, value, toml_ref, key)


def build_reverse_index(results_dir: Path) -> dict[str, CitationRef]:
    """Build a reverse index mapping fact values to TOML citation references.

    Walks each TOML file, extracts fact-pattern-matching values, and registers
    them with conflict resolution (scalar > array, lower priority > higher).
    """
    index: dict[str, CitationRef] = {}

    for toml_path in sorted(results_dir.glob("*.toml")):
        if toml_path.name in SKIP_TOML_FILES:
            continue

        try:
            data = tomlkit.loads(toml_path.read_text(encoding="utf-8"))
        except (tomlkit.exceptions.ParseError, ValueError) as e:
            warn(f"Cannot parse {toml_path.name}: {e}")
            continue

        toml_ref = f"results/{toml_path.name}"
        for key, value in data.items():
            _index_value(index, key, value, toml_ref)

    return index


def compute_code_block_mask(lines: list[str]) -> list[bool]:
    """Compute a boolean mask indicating which lines are inside fenced code blocks.

    Single O(n) pass instead of O(n^2) per-line is_in_code_block() calls.
    """
    mask = []
    in_block = False
    for line in lines:
        if line.strip().startswith("```"):
            in_block = not in_block
            mask.append(in_block)  # fence-open line is inside; fence-close is outside
        else:
            mask.append(in_block)
    return mask


def _should_skip_line(plain_lines: list[str], code_mask: list[bool], i: int) -> bool:
    """Check if a line should be skipped for citation insertion."""
    if code_mask[i]:
        return True
    if has_adjacent_citation(plain_lines, i):
        return True
    stripped = plain_lines[i].strip()
    return stripped.startswith("<!--") and stripped.endswith("-->")


def _insert_citation_into_line(line: str, citation: str) -> str:
    """Append a citation comment to a line, preserving the trailing newline."""
    if line.endswith("\n"):
        return line.rstrip("\n") + citation + "\n"
    return line + citation


def process_file(file_path: Path, index: dict[str, CitationRef], dry_run: bool) -> InsertionResult:
    """Process a single Markdown file, inserting citations where needed.

    Returns an InsertionResult with count of citations added and gap lines.
    """
    result = InsertionResult(file_path=file_path)
    text = file_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    plain_lines = text.splitlines()
    code_mask = compute_code_block_mask(plain_lines)
    modified = False

    for i in range(len(lines)):
        if _should_skip_line(plain_lines, code_mask, i):
            continue

        facts = extract_fact_values(plain_lines[i])
        if not facts:
            continue

        # Look up each fact in the index
        refs: dict[tuple[str, str], CitationRef] = {}
        unmatched = []
        for matched_value, description in facts:
            ref = index.get(matched_value)
            if ref is not None:
                refs[(ref.toml_file, ref.field_name)] = ref
            else:
                unmatched.append(f"{description}: {matched_value}")

        if refs:
            ref_strs = [f"{tf}#{fn}" for tf, fn in sorted(refs.keys())]
            citation = f" <!-- cite: {', '.join(ref_strs)} -->"
            lines[i] = _insert_citation_into_line(lines[i], citation)
            plain_lines[i] = plain_lines[i] + citation
            result.citations_added += 1
            modified = True
        elif unmatched:
            for gap in unmatched:
                result.gaps.append(f"{file_path.name}:{i + 1}: {gap}")

    if modified and not dry_run:
        file_path.write_text("".join(lines), encoding="utf-8")

    return result


def main() -> int:
    """Run the citation insertion tool."""
    parser = argparse.ArgumentParser(
        description="Insert citation comments into Markdown documentation"
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("docs"),
        help="Documentation directory to process (default: docs)",
    )
    parser.add_argument(
        "--wiki-dir",
        type=Path,
        default=None,
        help="Additional wiki directory to process",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
        help="Results directory containing TOML files (default: results)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )
    args = parser.parse_args()

    section("Building reverse index from TOML results")
    if not args.results_dir.exists():
        warn(f"Results directory not found: {args.results_dir}")
        return 1

    index = build_reverse_index(args.results_dir)
    info(f"Indexed {len(index)} unique fact values from TOML files")

    # Collect markdown files
    section("Collecting Markdown files")
    doc_files: list[Path] = []
    if args.docs_dir.exists():
        doc_files.extend(find_markdown_docs(args.docs_dir))
    if args.wiki_dir and args.wiki_dir.exists():
        doc_files.extend(find_markdown_docs(args.wiki_dir))

    # Filter out SKIP_MD_FILES
    doc_files = [f for f in doc_files if f.name not in SKIP_MD_FILES]

    if not doc_files:
        warn("No documentation files found.")
        return 0

    info(f"Found {len(doc_files)} Markdown files to process")

    # Process each file
    section("Inserting citations")
    total_added = 0
    all_gaps: list[str] = []
    mode = "DRY RUN" if args.dry_run else "LIVE"
    info(f"Mode: {mode}")

    for doc_file in doc_files:
        result = process_file(doc_file, index, dry_run=args.dry_run)
        total_added += result.citations_added
        all_gaps.extend(result.gaps)
        if result.citations_added > 0:
            info(f"  {doc_file.name}: +{result.citations_added} citations")

    # Summary
    section("Summary")
    success(f"Citations added: {total_added}")
    if all_gaps:
        warn(f"Unresolved gaps: {len(all_gaps)}")
        for gap in all_gaps:
            print(f"  GAP: {gap}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
