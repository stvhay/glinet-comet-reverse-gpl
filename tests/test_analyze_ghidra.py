"""Tests for scripts/analyze_ghidra.py."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from analyze_ghidra import (
    GhidraAnalysis,
    GPLSymbolRef,
    ModuleInterface,
    parse_ghidra_results,
)

# Sample Ghidra JSON output for testing (mocks what Jython scripts produce)
SAMPLE_KO_JSON = {
    "binary": "test_driver.ko",
    "type": "kernel_module",
    "module_init": {"name": "test_init", "address": "0x1000"},
    "module_exit": {"name": "test_exit", "address": "0x2000"},
    "exported_symbols": [
        {"name": "test_func", "address": "0x3000", "is_gpl": True},
        {"name": "helper_func", "address": "0x4000", "is_gpl": False},
    ],
    "ioctl_handlers": [
        {"name": "test_ioctl", "address": "0x5000", "size": 256},
    ],
    "file_operations": [
        {"name": "test_fops", "address": "0x6000"},
    ],
    "module_info": {"license": "GPL", "author": "Vendor"},
}

SAMPLE_GENERIC_JSON = {
    "binary": "test_driver.ko",
    "format": "ELF",
    "language": "ARM:LE:32:v7",
    "compiler": "gcc",
    "image_base": "0x0",
    "function_count": 42,
    "functions": [
        {
            "name": "test_init",
            "address": "0x1000",
            "size": 100,
            "is_external": False,
            "is_thunk": False,
        },
    ],
    "symbols": [],
    "imports": [],
    "exports": [{"name": "test_func", "address": "0x3000"}],
    "gpl_strings": [
        {"address": "0x7000", "value": "GPL v2"},
    ],
}

SAMPLE_UBOOT_JSON = {
    "binary": "u-boot.bin",
    "type": "uboot",
    "commands": [
        {"name": "do_bootm", "address": "0x8000", "type": "handler"},
    ],
    "board_init_functions": [
        {"name": "board_init_f", "address": "0x9000", "size": 512},
    ],
    "env_defaults": [
        {"address": "0xa000", "key": "bootcmd", "value": "run distro_bootcmd"},
    ],
    "function_count": 150,
}


class TestModuleInterface:
    """Test ModuleInterface dataclass."""

    def test_creation(self) -> None:
        mi = ModuleInterface(
            name="test_driver",
            init_function="test_init",
            exit_function="test_exit",
            exported_symbols=["test_func"],
            gpl_symbols=["test_func"],
            ioctl_handlers=["test_ioctl"],
        )
        assert mi.name == "test_driver"
        assert mi.init_function == "test_init"
        assert len(mi.exported_symbols) == 1
        assert len(mi.gpl_symbols) == 1

    def test_to_dict(self) -> None:
        mi = ModuleInterface(
            name="test_driver",
            init_function="test_init",
            exit_function=None,
            exported_symbols=[],
            gpl_symbols=[],
            ioctl_handlers=[],
        )
        d = mi.to_dict()
        assert d["name"] == "test_driver"
        assert d["init_function"] == "test_init"
        assert d["exit_function"] is None


class TestGPLSymbolRef:
    """Test GPLSymbolRef dataclass."""

    def test_creation(self) -> None:
        ref = GPLSymbolRef(
            symbol="test_func",
            binary="test_driver.ko",
            is_gpl_only=True,
        )
        assert ref.symbol == "test_func"
        assert ref.is_gpl_only is True


class TestGhidraAnalysis:
    """Test GhidraAnalysis dataclass."""

    def test_creation_defaults(self) -> None:
        analysis = GhidraAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )
        assert analysis.firmware_file == "test.img"
        assert analysis.kernel_modules_analyzed == 0
        assert analysis.uboot_analyzed is False
        assert analysis.kernel_module_interfaces == []
        assert analysis.gpl_symbol_usage == []

    def test_metadata_tracking(self) -> None:
        analysis = GhidraAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
        )
        analysis.add_metadata(
            "kernel_modules_analyzed",
            "ghidra",
            "analyzeHeadless kernel module count",
        )
        assert analysis._source["kernel_modules_analyzed"] == "ghidra"


class TestParseGhidraResults:
    """Test parse_ghidra_results function."""

    def test_parse_kernel_module(self, tmp_path: Path) -> None:
        results_dir = tmp_path / "results" / "ghidra"
        results_dir.mkdir(parents=True)
        (results_dir / "ko_test_driver.json").write_text(json.dumps(SAMPLE_KO_JSON))
        (results_dir / "generic_test_driver.json").write_text(json.dumps(SAMPLE_GENERIC_JSON))

        analysis = GhidraAnalysis(firmware_file="test.img", firmware_size=1024)
        parse_ghidra_results(results_dir, analysis)

        assert analysis.kernel_modules_analyzed == 1
        assert len(analysis.kernel_module_interfaces) == 1
        mi = analysis.kernel_module_interfaces[0]
        assert mi.name == "test_driver.ko"
        assert mi.init_function == "test_init"
        assert mi.exit_function == "test_exit"

    def test_parse_gpl_symbols(self, tmp_path: Path) -> None:
        results_dir = tmp_path / "results" / "ghidra"
        results_dir.mkdir(parents=True)
        (results_dir / "ko_test_driver.json").write_text(json.dumps(SAMPLE_KO_JSON))

        analysis = GhidraAnalysis(firmware_file="test.img", firmware_size=1024)
        parse_ghidra_results(results_dir, analysis)

        assert len(analysis.gpl_symbol_usage) == 1
        assert analysis.gpl_symbol_usage[0].symbol == "test_func"
        assert analysis.gpl_symbol_usage[0].is_gpl_only is True

    def test_parse_uboot(self, tmp_path: Path) -> None:
        results_dir = tmp_path / "results" / "ghidra"
        results_dir.mkdir(parents=True)
        (results_dir / "uboot.json").write_text(json.dumps(SAMPLE_UBOOT_JSON))

        analysis = GhidraAnalysis(firmware_file="test.img", firmware_size=1024)
        parse_ghidra_results(results_dir, analysis)

        assert analysis.uboot_analyzed is True
        assert analysis.uboot_command_count == 1
        assert analysis.uboot_function_count == 150

    def test_empty_results_dir(self, tmp_path: Path) -> None:
        results_dir = tmp_path / "results" / "ghidra"
        results_dir.mkdir(parents=True)

        analysis = GhidraAnalysis(firmware_file="test.img", firmware_size=1024)
        parse_ghidra_results(results_dir, analysis)

        assert analysis.kernel_modules_analyzed == 0
        assert analysis.uboot_analyzed is False

    def test_to_dict_with_modules(self) -> None:
        analysis = GhidraAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            kernel_modules_analyzed=1,
            kernel_module_interfaces=[
                ModuleInterface(
                    name="test.ko",
                    init_function="init",
                    exit_function="exit",
                    exported_symbols=["sym1"],
                    gpl_symbols=["sym1"],
                    ioctl_handlers=[],
                ),
            ],
        )
        d = analysis.to_dict()
        assert d["kernel_modules_analyzed"] == 1
        assert isinstance(d["kernel_module_interfaces"], list)
        assert d["kernel_module_interfaces"][0]["name"] == "test.ko"
