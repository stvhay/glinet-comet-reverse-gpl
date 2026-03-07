#!/usr/bin/env python3
"""Integrate Ghidra headless analysis results into the analysis pipeline.

Usage: ./scripts/analyze_ghidra.py [firmware.img] [--format FORMAT]

This script:
1. Invokes run_ghidra_analysis.sh to run Ghidra headless analysis
2. Reads JSON intermediates from results/ghidra/
3. Produces results/ghidra_analysis.toml with structured findings

Arguments:
    firmware.img      Path to firmware file (optional, downloads default if not provided)
    --format FORMAT   Output format: 'toml' (default) or 'json'
"""

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lib.analysis_base import AnalysisBase
from lib.base_script import AnalysisScript
from lib.logging import error, info, section, warn


@dataclass(slots=True)
class ModuleInterface:
    """Kernel module interface extracted from Ghidra analysis."""

    name: str
    init_function: str | None
    exit_function: str | None
    exported_symbols: list[str] = field(default_factory=list)
    gpl_symbols: list[str] = field(default_factory=list)
    ioctl_handlers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "init_function": self.init_function,
            "exit_function": self.exit_function,
            "exported_symbols": self.exported_symbols,
            "gpl_symbols": self.gpl_symbols,
            "ioctl_handlers": self.ioctl_handlers,
        }


@dataclass(slots=True)
class GPLSymbolRef:
    """Reference to a GPL-exported symbol used by a binary."""

    symbol: str
    binary: str
    is_gpl_only: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "binary": self.binary,
            "is_gpl_only": self.is_gpl_only,
        }


@dataclass(slots=True)
class GhidraAnalysis(AnalysisBase):
    """Results of Ghidra headless binary analysis."""

    firmware_file: str = ""
    firmware_size: int = 0
    kernel_modules_analyzed: int = 0
    uboot_analyzed: bool = False
    uboot_command_count: int = 0
    uboot_function_count: int = 0
    total_functions_found: int = 0
    total_gpl_strings_found: int = 0
    kernel_module_interfaces: list[ModuleInterface] = field(default_factory=list)
    gpl_symbol_usage: list[GPLSymbolRef] = field(default_factory=list)
    reconstructed_headers: list[str] = field(default_factory=list)

    # Source metadata
    _source: dict[str, str] = field(default_factory=dict)
    _method: dict[str, str] = field(default_factory=dict)
    _reproducibility: dict[str, str] = field(default_factory=dict)
    _hardware_metadata: dict[str, dict[str, str]] = field(default_factory=dict)

    def _convert_complex_field(self, key: str, value: Any) -> tuple[bool, Any]:
        if key == "kernel_module_interfaces":
            return True, [item.to_dict() for item in value]
        if key == "gpl_symbol_usage":
            return True, [item.to_dict() for item in value]
        return False, None


def _parse_ko_json(data: dict[str, Any], json_file: Path, analysis: GhidraAnalysis) -> None:
    """Parse a single kernel module JSON file into the analysis."""
    binary_name = data.get("binary", json_file.stem)

    init_func = data["module_init"].get("name") if data.get("module_init") else None
    exit_func = data["module_exit"].get("name") if data.get("module_exit") else None

    exported = [s.get("name", "") for s in data.get("exported_symbols", [])]
    gpl_syms = [s.get("name", "") for s in data.get("exported_symbols", []) if s.get("is_gpl")]
    ioctl = [h.get("name", "") for h in data.get("ioctl_handlers", [])]

    analysis.kernel_module_interfaces.append(
        ModuleInterface(
            name=binary_name,
            init_function=init_func,
            exit_function=exit_func,
            exported_symbols=exported,
            gpl_symbols=gpl_syms,
            ioctl_handlers=ioctl,
        )
    )

    for sym in data.get("exported_symbols", []):
        if sym.get("is_gpl"):
            analysis.gpl_symbol_usage.append(
                GPLSymbolRef(
                    symbol=sym.get("name", ""),
                    binary=binary_name,
                    is_gpl_only=True,
                )
            )


def _parse_kernel_modules(results_dir: Path, analysis: GhidraAnalysis) -> int:
    """Parse all kernel module JSON files. Returns count of modules parsed."""
    ko_count = 0
    for json_file in sorted(results_dir.glob("ko_*.json")):
        try:
            data = json.loads(json_file.read_text())
        except (json.JSONDecodeError, OSError) as e:
            warn(f"Failed to read {json_file.name}: {e}")
            continue
        ko_count += 1
        _parse_ko_json(data, json_file, analysis)

    analysis.kernel_modules_analyzed = ko_count
    analysis.add_metadata(
        "kernel_modules_analyzed",
        "ghidra",
        "count of ko_*.json files in results/ghidra/",
    )
    return ko_count


def _parse_generic_totals(results_dir: Path) -> tuple[int, int]:
    """Sum function counts and GPL strings from generic analysis files."""
    total_functions = 0
    total_gpl_strings = 0
    for json_file in sorted(results_dir.glob("generic_*.json")):
        try:
            data = json.loads(json_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        total_functions += data.get("function_count", 0)
        total_gpl_strings += len(data.get("gpl_strings", []))
    return total_functions, total_gpl_strings


def _parse_uboot(results_dir: Path, analysis: GhidraAnalysis) -> int:
    """Parse U-Boot JSON results. Returns function count from U-Boot."""
    uboot_file = results_dir / "uboot.json"
    if not uboot_file.exists():
        return 0
    try:
        data = json.loads(uboot_file.read_text())
    except (json.JSONDecodeError, OSError) as e:
        warn(f"Failed to read uboot.json: {e}")
        return 0

    analysis.uboot_analyzed = True
    analysis.uboot_command_count = len(data.get("commands", []))
    analysis.uboot_function_count = data.get("function_count", 0)
    analysis.add_metadata("uboot_analyzed", "ghidra", "presence of uboot.json in results/ghidra/")
    analysis.add_metadata("uboot_command_count", "ghidra", "count of commands in uboot.json")
    analysis.add_metadata("uboot_function_count", "ghidra", "function_count field in uboot.json")
    return data.get("function_count", 0)


def _parse_struct_headers(results_dir: Path, analysis: GhidraAnalysis) -> None:
    """Check for reconstructed headers from struct analysis."""
    for json_file in sorted(results_dir.glob("structs_*.json")):
        try:
            data = json.loads(json_file.read_text())
            if data.get("header_content"):
                header_name = json_file.stem.replace("structs_", "") + ".h"
                analysis.reconstructed_headers.append(header_name)
        except (json.JSONDecodeError, OSError):
            continue


def parse_ghidra_results(results_dir: Path, analysis: GhidraAnalysis) -> None:
    """Parse Ghidra JSON output files into the analysis dataclass.

    Args:
        results_dir: Path to results/ghidra/ containing JSON files
        analysis: GhidraAnalysis object to populate
    """
    if not results_dir.exists():
        warn(f"Ghidra results directory not found: {results_dir}")
        return

    _parse_kernel_modules(results_dir, analysis)
    total_functions, total_gpl_strings = _parse_generic_totals(results_dir)
    total_functions += _parse_uboot(results_dir, analysis)

    analysis.total_functions_found = total_functions
    analysis.total_gpl_strings_found = total_gpl_strings
    if total_functions > 0:
        analysis.add_metadata(
            "total_functions_found",
            "ghidra",
            "sum of function_count across all generic_*.json",
        )
    if total_gpl_strings > 0:
        analysis.add_metadata(
            "total_gpl_strings_found",
            "ghidra",
            "sum of gpl_strings across all generic_*.json",
        )

    _parse_struct_headers(results_dir, analysis)


SIMPLE_FIELDS = [
    "firmware_file",
    "firmware_size",
    "kernel_modules_analyzed",
    "uboot_analyzed",
    "uboot_command_count",
    "uboot_function_count",
    "total_functions_found",
    "total_gpl_strings_found",
]

COMPLEX_FIELDS = [
    "kernel_module_interfaces",
    "gpl_symbol_usage",
    "reconstructed_headers",
]


class GhidraScript(AnalysisScript):
    """Ghidra headless analysis integration script."""

    def __init__(self) -> None:
        super().__init__(
            description="Integrate Ghidra headless analysis results",
            title="Ghidra binary analysis",
            simple_fields=SIMPLE_FIELDS,
            complex_fields=COMPLEX_FIELDS,
        )

    def analyze(self, firmware_path: str) -> AnalysisBase:
        """Run Ghidra analysis pipeline."""
        firmware = Path(firmware_path)
        analysis = GhidraAnalysis(
            firmware_file=firmware.name,
            firmware_size=firmware.stat().st_size,
        )
        analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")
        analysis.add_metadata("firmware_size", "filesystem", "Path(firmware).stat().st_size")

        # Run Ghidra orchestrator
        section("Running Ghidra headless analysis")
        orchestrator = Path(__file__).parent / "ghidra" / "run_ghidra_analysis.sh"

        if not orchestrator.exists():
            error(f"Ghidra orchestrator not found: {orchestrator}")
            warn("Skipping Ghidra analysis — checking for existing results")
        else:
            extract_dir, _rootfs = self.initialize_extraction(firmware_path, need_rootfs=True)
            try:
                subprocess.run(
                    [str(orchestrator), str(extract_dir)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                info("Ghidra analysis completed successfully")
            except subprocess.CalledProcessError as e:
                warn(f"Ghidra analysis failed: {e.stderr[:500]}")
                warn("Attempting to parse any partial results")
            except FileNotFoundError:
                error("analyzeHeadless not found — run within 'nix develop' shell")

        # Parse results
        section("Parsing Ghidra results")
        project_root = Path(__file__).parent.parent
        results_dir = project_root / "results" / "ghidra"
        parse_ghidra_results(results_dir, analysis)

        return analysis


if __name__ == "__main__":
    GhidraScript().run()
