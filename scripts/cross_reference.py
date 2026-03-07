#!/usr/bin/env python3
"""Cross-reference Ghidra analysis against upstream kernel and U-Boot source.

Usage: ./scripts/cross_reference.py [--ghidra-dir DIR] [--upstream-dir DIR] [--format FORMAT]

Compares function names from Ghidra decompiled output against upstream source
trees to classify functions as: upstream_match, modified, or vendor_added.

Outputs: results/cross_reference.toml
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lib.analysis_base import AnalysisBase
from lib.logging import error, info, section, success, warn
from lib.output import output_json, output_toml


@dataclass(slots=True)
class ModifiedFunction:
    """A function that was found and classified."""

    name: str
    binary: str
    upstream_file: str | None
    classification: str  # "upstream_match", "modified", "vendor_added"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "binary": self.binary,
            "upstream_file": self.upstream_file,
            "classification": self.classification,
        }


@dataclass(slots=True)
class VendorModule:
    """A kernel module not found in upstream — likely vendor-added."""

    name: str
    function_count: int
    gpl_symbols_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "function_count": self.function_count,
            "gpl_symbols_used": self.gpl_symbols_used,
        }


@dataclass(slots=True)
class CrossReferenceAnalysis(AnalysisBase):
    """Results of cross-referencing Ghidra output against upstream source."""

    upstream_kernel_version: str = ""
    upstream_uboot_version: str = ""
    total_functions_analyzed: int = 0
    unmodified_count: int = 0
    modified_count: int = 0
    vendor_added_count: int = 0
    modified_functions: list[ModifiedFunction] = field(default_factory=list)
    vendor_modules: list[VendorModule] = field(default_factory=list)

    # Source metadata
    _source: dict[str, str] = field(default_factory=dict)
    _method: dict[str, str] = field(default_factory=dict)
    _reproducibility: dict[str, str] = field(default_factory=dict)
    _hardware_metadata: dict[str, dict[str, str]] = field(default_factory=dict)

    def _convert_complex_field(self, key: str, value: Any) -> tuple[bool, Any]:
        if key in ("modified_functions", "vendor_modules"):
            return True, [item.to_dict() for item in value]
        return False, None


def find_function_in_upstream(func_name: str, upstream_dir: Path) -> str | None:
    """Search upstream source tree for a function definition.

    Uses grep to find C function definitions matching the name.
    Returns the relative file path if found, None otherwise.

    Args:
        func_name: Function name to search for
        upstream_dir: Root of upstream source tree

    Returns:
        Relative path to file containing the function, or None
    """
    if not upstream_dir.exists():
        return None

    # Search for function definition patterns in C files
    # Matches: "type func_name(" at start of line or after whitespace
    pattern = rf"\b{func_name}\s*\("

    try:
        result = subprocess.run(
            [
                "grep",
                "-rl",
                "--include=*.c",
                "--include=*.h",
                "-E",
                pattern,
                str(upstream_dir),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            # Return first match, relative to upstream_dir
            first_match = result.stdout.strip().splitlines()[0]
            try:
                return str(Path(first_match).relative_to(upstream_dir))
            except ValueError:
                return first_match
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


def classify_function(_func_name: str, upstream_file: str | None) -> str:
    """Classify a function based on upstream presence.

    Args:
        _func_name: Function name (reserved for future heuristics)
        upstream_file: File path in upstream if found, None otherwise

    Returns:
        Classification string: "upstream_match" or "vendor_added"
    """
    if upstream_file is not None:
        return "upstream_match"
    return "vendor_added"


def _get_module_functions(
    ghidra_dir: Path, ko_json: Path, module_name: str
) -> list[dict[str, Any]]:
    """Get function list for a module from generic or ko analysis."""
    generic_json = ghidra_dir / f"generic_{module_name}.json"
    if generic_json.exists():
        try:
            data = json.loads(generic_json.read_text())
            functions = data.get("functions", [])
            if functions:
                return functions
        except (json.JSONDecodeError, OSError):
            pass

    # Fall back to ko analysis for at least init/exit
    try:
        ko_data = json.loads(ko_json.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    functions: list[dict[str, Any]] = []
    if ko_data.get("module_init"):
        functions.append(ko_data["module_init"])
    if ko_data.get("module_exit"):
        functions.append(ko_data["module_exit"])
    return functions


def _classify_functions(
    functions: list[dict[str, Any]],
    binary_name: str,
    upstream: Path | None,
    analysis: CrossReferenceAnalysis,
) -> tuple[int, int, int]:
    """Classify functions against upstream, returns (analyzed, matches, vendor)."""
    analyzed = 0
    matches = 0
    vendor = 0
    for func in functions:
        name = func.get("name", "")
        if not name or func.get("is_thunk", False):
            continue

        analyzed += 1
        upstream_file = find_function_in_upstream(name, upstream) if upstream else None
        classification = classify_function(name, upstream_file)

        if classification == "upstream_match":
            matches += 1
        else:
            vendor += 1

        analysis.modified_functions.append(
            ModifiedFunction(
                name=name,
                binary=binary_name,
                upstream_file=upstream_file,
                classification=classification,
            )
        )
    return analyzed, matches, vendor


def _process_kernel_modules(
    ghidra_dir: Path,
    kernel_upstream: Path | None,
    analysis: CrossReferenceAnalysis,
) -> tuple[int, int, int]:
    """Process all kernel module JSON files. Returns (analyzed, matches, vendor)."""
    total_analyzed = 0
    total_matches = 0
    total_vendor = 0

    for ko_json in sorted(ghidra_dir.glob("ko_*.json")):
        module_name = ko_json.stem.replace("ko_", "")
        functions = _get_module_functions(ghidra_dir, ko_json, module_name)
        if not functions:
            continue

        a, m, v = _classify_functions(functions, f"{module_name}.ko", kernel_upstream, analysis)
        total_analyzed += a
        total_matches += m
        total_vendor += v

        # Check if the module itself exists upstream
        module_in_upstream = False
        if kernel_upstream:
            module_in_upstream = (
                find_function_in_upstream(module_name.replace("-", "_"), kernel_upstream)
                is not None
            )

        if not module_in_upstream:
            try:
                ko_data = json.loads(ko_json.read_text())
                gpl_syms = [
                    s.get("name", "")
                    for s in ko_data.get("exported_symbols", [])
                    if s.get("is_gpl")
                ]
            except (json.JSONDecodeError, OSError):
                gpl_syms = []

            analysis.vendor_modules.append(
                VendorModule(
                    name=f"{module_name}.ko",
                    function_count=len(functions),
                    gpl_symbols_used=gpl_syms,
                )
            )

    return total_analyzed, total_matches, total_vendor


def _process_uboot(
    ghidra_dir: Path,
    uboot_upstream: Path | None,
    analysis: CrossReferenceAnalysis,
) -> tuple[int, int, int]:
    """Process U-Boot JSON results. Returns (analyzed, matches, vendor)."""
    uboot_json = ghidra_dir / "uboot.json"
    if not uboot_json.exists() or not uboot_upstream:
        return 0, 0, 0

    try:
        data = json.loads(uboot_json.read_text())
    except (json.JSONDecodeError, OSError) as e:
        warn(f"Failed to read uboot.json: {e}")
        return 0, 0, 0

    commands = [{"name": c.get("name", "")} for c in data.get("commands", []) if c.get("name")]
    return _classify_functions(commands, "u-boot", uboot_upstream, analysis)


def parse_and_classify(
    ghidra_dir: Path,
    kernel_upstream: Path | None,
    uboot_upstream: Path | None,
    analysis: CrossReferenceAnalysis,
) -> None:
    """Parse Ghidra results and classify functions against upstream.

    Args:
        ghidra_dir: Path to results/ghidra/ with JSON files
        kernel_upstream: Path to upstream kernel source (or None to skip)
        uboot_upstream: Path to upstream U-Boot source (or None to skip)
        analysis: CrossReferenceAnalysis to populate
    """
    if not ghidra_dir.exists():
        warn(f"Ghidra results not found: {ghidra_dir}")
        return

    ka, km, kv = _process_kernel_modules(ghidra_dir, kernel_upstream, analysis)
    ua, um, uv = _process_uboot(ghidra_dir, uboot_upstream, analysis)

    analysis.total_functions_analyzed = ka + ua
    analysis.unmodified_count = km + um
    analysis.vendor_added_count = kv + uv
    analysis.add_metadata(
        "total_functions_analyzed",
        "cross_reference",
        "count of functions analyzed from Ghidra JSON output",
    )


SIMPLE_FIELDS = [
    "upstream_kernel_version",
    "upstream_uboot_version",
    "total_functions_analyzed",
    "unmodified_count",
    "modified_count",
    "vendor_added_count",
]

COMPLEX_FIELDS = [
    "modified_functions",
    "vendor_modules",
]


def main() -> None:
    """CLI entry point for cross-reference analysis."""
    parser = argparse.ArgumentParser(
        description="Cross-reference Ghidra output against upstream source",
    )
    parser.add_argument(
        "--ghidra-dir",
        default="results/ghidra",
        help="Path to Ghidra JSON results (default: results/ghidra)",
    )
    parser.add_argument(
        "--upstream-dir",
        default=str(Path.home() / ".cache" / "glinet-comet-re" / "upstream"),
        help="Path to upstream source cache (default: ~/.cache/glinet-comet-re/upstream)",
    )
    parser.add_argument(
        "--format",
        choices=["toml", "json"],
        default="toml",
        help="Output format (default: toml)",
    )
    args = parser.parse_args()

    ghidra_dir = Path(args.ghidra_dir)
    upstream_dir = Path(args.upstream_dir)

    kernel_upstream = upstream_dir / "linux"
    uboot_upstream = upstream_dir / "u-boot"

    if not ghidra_dir.exists():
        error(f"Ghidra results not found: {ghidra_dir}")
        error("Run analyze_ghidra.py first")
        sys.exit(1)

    analysis = CrossReferenceAnalysis(
        upstream_kernel_version="4.19.111",
        upstream_uboot_version="2017.09",
    )

    section("Cross-referencing Ghidra output against upstream source")

    if kernel_upstream.exists():
        info(f"Kernel upstream: {kernel_upstream}")
    else:
        warn(f"Kernel upstream not found: {kernel_upstream}")
        warn("Run scripts/fetch_upstream.sh first")
        kernel_upstream = None  # type: ignore[assignment]

    if uboot_upstream.exists():
        info(f"U-Boot upstream: {uboot_upstream}")
    else:
        warn(f"U-Boot upstream not found: {uboot_upstream}")
        uboot_upstream = None  # type: ignore[assignment]

    parse_and_classify(ghidra_dir, kernel_upstream, uboot_upstream, analysis)

    if args.format == "json":
        print(output_json(analysis))
    else:
        print(
            output_toml(
                analysis,
                title="Cross-reference analysis: firmware vs upstream",
                simple_fields=SIMPLE_FIELDS,
                complex_fields=COMPLEX_FIELDS,
            )
        )

    success(
        f"Cross-reference complete: {analysis.total_functions_analyzed} functions analyzed, "
        f"{analysis.vendor_added_count} vendor-added"
    )


if __name__ == "__main__":
    main()
