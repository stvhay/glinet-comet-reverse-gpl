#!/usr/bin/env python3
"""Citation verifier for traceability enforcement.

Scans Markdown documentation for citation comments and verifies they reference
valid TOML result fields. Also warns about uncited factual claims.

Usage:
    python scripts/verify_traceability.py --docs-dir docs --results-dir results
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import tomlkit


@dataclass
class Citation:
    """A parsed citation reference from a Markdown document."""

    file_path: Path
    line_number: int
    toml_file: str
    field_name: str
    raw_text: str


@dataclass
class VerificationError:
    """A verification problem found during scanning."""

    file_path: Path
    line_number: int
    check: str
    message: str
    severity: str


# Directories to skip when scanning for documentation
SKIP_SUBDIRS = {"plans", "archive", "quality"}

# Pattern for full citation comments: <!-- cite: results/file.toml#field -->
CITATION_COMMENT_RE = re.compile(r"<!--\s*cite:\s*(.+?)\s*-->")

# Pattern for individual references within a citation: file.toml#field
CITATION_REF_RE = re.compile(r"([\w./-]+\.toml)#(\w+)")

# Patterns that suggest factual claims needing citations
UNCITED_FACT_PATTERNS = [
    (re.compile(r"0x[0-9a-fA-F]{2,}"), "hex offset"),
    (re.compile(r"\d+\.\d+\.\d+"), "version string"),
    (re.compile(r"\b[a-f0-9]{40,64}\b"), "SHA hash"),
    (re.compile(r"/(?:usr|etc|var|opt|boot|dev|proc|sys)/\S+"), "absolute path"),
]


def find_markdown_docs(docs_dir: Path) -> list[Path]:
    """Find all Markdown files in docs_dir, skipping excluded subdirectories."""
    results = []
    for md_file in sorted(docs_dir.rglob("*.md")):
        # Check if any parent relative to docs_dir is in SKIP_SUBDIRS
        try:
            rel = md_file.relative_to(docs_dir)
        except ValueError:
            continue
        if any(part in SKIP_SUBDIRS for part in rel.parts[:-1]):
            continue
        results.append(md_file)
    return results


def parse_citations(doc_path: Path) -> list[Citation]:
    """Parse all citation comments from a Markdown file."""
    citations = []
    text = doc_path.read_text(encoding="utf-8")

    for line_idx, line in enumerate(text.splitlines()):
        for comment_match in CITATION_COMMENT_RE.finditer(line):
            raw_text = comment_match.group(0)
            refs_text = comment_match.group(1)
            for ref_match in CITATION_REF_RE.finditer(refs_text):
                citations.append(
                    Citation(
                        file_path=doc_path,
                        line_number=line_idx + 1,
                        toml_file=ref_match.group(1),
                        field_name=ref_match.group(2),
                        raw_text=raw_text,
                    )
                )

    return citations


def check_citation_integrity(
    citations: list[Citation], project_root: Path
) -> list[VerificationError]:
    """Verify that each citation references an existing TOML file and field."""
    errors = []
    toml_cache: dict[str, dict] = {}

    for citation in citations:
        toml_path = project_root / citation.toml_file

        # Load and cache TOML file
        if citation.toml_file not in toml_cache:
            if not toml_path.exists():
                errors.append(
                    VerificationError(
                        file_path=citation.file_path,
                        line_number=citation.line_number,
                        check="citation_integrity",
                        message=f"TOML file not found: {citation.toml_file}",
                        severity="error",
                    )
                )
                toml_cache[citation.toml_file] = {}
                continue
            try:
                toml_cache[citation.toml_file] = dict(
                    tomlkit.loads(toml_path.read_text(encoding="utf-8"))
                )
            except (tomlkit.exceptions.ParseError, ValueError) as e:
                errors.append(
                    VerificationError(
                        file_path=citation.file_path,
                        line_number=citation.line_number,
                        check="citation_integrity",
                        message=f"Cannot parse {citation.toml_file}: {e}",
                        severity="error",
                    )
                )
                toml_cache[citation.toml_file] = {}
                continue

        data = toml_cache[citation.toml_file]
        if not data:
            continue

        if citation.field_name not in data:
            errors.append(
                VerificationError(
                    file_path=citation.file_path,
                    line_number=citation.line_number,
                    check="citation_integrity",
                    message=(f"Field '{citation.field_name}' not found in {citation.toml_file}"),
                    severity="error",
                )
            )

    return errors


def is_in_code_block(lines: list[str], line_idx: int) -> bool:
    """Check if a line is inside a fenced code block."""
    in_block = False
    for i in range(line_idx):
        if lines[i].strip().startswith("```"):
            in_block = not in_block
    return in_block


def has_adjacent_citation(lines: list[str], line_idx: int) -> bool:
    """Check if a line or the next line contains a citation comment."""
    if CITATION_COMMENT_RE.search(lines[line_idx]):
        return True
    return bool(line_idx + 1 < len(lines) and CITATION_COMMENT_RE.search(lines[line_idx + 1]))


def check_uncited_facts(doc_path: Path) -> list[VerificationError]:
    """Scan for factual claims that lack adjacent citations."""
    warnings = []
    text = doc_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    for line_idx, line in enumerate(lines):
        if is_in_code_block(lines, line_idx):
            continue

        for pattern, description in UNCITED_FACT_PATTERNS:
            if pattern.search(line) and not has_adjacent_citation(lines, line_idx):
                warnings.append(
                    VerificationError(
                        file_path=doc_path,
                        line_number=line_idx + 1,
                        check="uncited_fact",
                        message=f"Uncited {description}: {line.strip()[:80]}",
                        severity="warning",
                    )
                )
                break  # One warning per line

    return warnings


def main() -> int:
    """Run the traceability verifier."""
    parser = argparse.ArgumentParser(description="Verify citation traceability in documentation")
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("docs"),
        help="Documentation directory to scan (default: docs)",
    )
    parser.add_argument(
        "--wiki-dir",
        type=Path,
        default=None,
        help="Additional wiki directory to scan",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
        help="Results directory containing TOML files (default: results)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )

    args = parser.parse_args()
    project_root = Path.cwd()

    # Collect all documentation files
    doc_files: list[Path] = []
    if args.docs_dir.exists():
        doc_files.extend(find_markdown_docs(args.docs_dir))
    if args.wiki_dir and args.wiki_dir.exists():
        doc_files.extend(find_markdown_docs(args.wiki_dir))

    if not doc_files:
        print("No documentation files found.")
        return 0

    # Parse all citations
    all_citations: list[Citation] = []
    for doc in doc_files:
        all_citations.extend(parse_citations(doc))

    # Check citation integrity
    all_errors: list[VerificationError] = []
    all_errors.extend(check_citation_integrity(all_citations, project_root))

    # Check for uncited facts
    for doc in doc_files:
        all_errors.extend(check_uncited_facts(doc))

    # Report results
    error_count = sum(1 for e in all_errors if e.severity == "error")
    warning_count = sum(1 for e in all_errors if e.severity == "warning")

    for err in all_errors:
        prefix = "ERROR" if err.severity == "error" else "WARNING"
        print(f"{prefix}: {err.file_path}:{err.line_number}: [{err.check}] {err.message}")

    print(f"\nScanned {len(doc_files)} files, found {len(all_citations)} citations.")
    print(f"Results: {error_count} errors, {warning_count} warnings.")

    if error_count > 0:
        return 1
    if args.strict and warning_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
