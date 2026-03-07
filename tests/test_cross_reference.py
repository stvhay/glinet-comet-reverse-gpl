"""Tests for scripts/cross_reference.py."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from cross_reference import (
    CrossReferenceAnalysis,
    ModifiedFunction,
    VendorModule,
    classify_function,
    find_function_in_upstream,
    parse_and_classify,
)


class TestModifiedFunction:
    """Test ModifiedFunction dataclass."""

    def test_creation(self) -> None:
        mf = ModifiedFunction(
            name="test_func",
            binary="test.ko",
            upstream_file="drivers/test/test.c",
            classification="modified",
        )
        assert mf.name == "test_func"
        assert mf.classification == "modified"

    def test_to_dict(self) -> None:
        mf = ModifiedFunction(
            name="test_func",
            binary="test.ko",
            upstream_file="drivers/test/test.c",
            classification="vendor_added",
        )
        d = mf.to_dict()
        assert d["classification"] == "vendor_added"


class TestVendorModule:
    """Test VendorModule dataclass."""

    def test_creation(self) -> None:
        vm = VendorModule(
            name="vendor_driver.ko",
            function_count=10,
            gpl_symbols_used=["printk", "kmalloc"],
        )
        assert vm.name == "vendor_driver.ko"
        assert len(vm.gpl_symbols_used) == 2


class TestCrossReferenceAnalysis:
    """Test CrossReferenceAnalysis dataclass."""

    def test_defaults(self) -> None:
        analysis = CrossReferenceAnalysis(
            upstream_kernel_version="4.19.111",
            upstream_uboot_version="2017.09",
        )
        assert analysis.total_functions_analyzed == 0
        assert analysis.unmodified_count == 0
        assert analysis.modified_count == 0
        assert analysis.vendor_added_count == 0


class TestFindFunctionInUpstream:
    """Test finding function definitions in upstream source."""

    def test_find_existing_function(self, tmp_path: Path) -> None:
        # Create a mock upstream source tree
        driver_dir = tmp_path / "drivers" / "test"
        driver_dir.mkdir(parents=True)
        (driver_dir / "test.c").write_text(
            "static int test_init(struct platform_device *pdev)\n{\n    return 0;\n}\n"
        )
        result = find_function_in_upstream("test_init", tmp_path)
        assert result is not None
        assert "drivers/test/test.c" in result

    def test_function_not_found(self, tmp_path: Path) -> None:
        driver_dir = tmp_path / "drivers"
        driver_dir.mkdir(parents=True)
        (driver_dir / "empty.c").write_text("/* empty */\n")
        result = find_function_in_upstream("nonexistent_func", tmp_path)
        assert result is None

    def test_skips_non_c_files(self, tmp_path: Path) -> None:
        (tmp_path / "readme.txt").write_text("test_init is mentioned here\n")
        result = find_function_in_upstream("test_init", tmp_path)
        assert result is None


class TestClassifyFunction:
    """Test function classification logic."""

    def test_upstream_match(self) -> None:
        result = classify_function("test_init", "drivers/test/test.c")
        assert result == "upstream_match"

    def test_vendor_added(self) -> None:
        result = classify_function("vendor_custom_func", None)
        assert result == "vendor_added"


class TestParseAndClassify:
    """Test the full parse-and-classify pipeline."""

    def test_with_kernel_module(self, tmp_path: Path) -> None:
        # Set up mock Ghidra results
        ghidra_dir = tmp_path / "ghidra"
        ghidra_dir.mkdir()
        ko_data = {
            "binary": "test_driver.ko",
            "type": "kernel_module",
            "module_init": {"name": "test_init", "address": "0x1000"},
            "module_exit": {"name": "test_exit", "address": "0x2000"},
            "exported_symbols": [
                {"name": "test_func", "address": "0x3000", "is_gpl": False},
            ],
            "ioctl_handlers": [],
            "file_operations": [],
            "module_info": {},
        }
        (ghidra_dir / "ko_test_driver.json").write_text(json.dumps(ko_data))

        generic_data = {
            "binary": "test_driver.ko",
            "function_count": 5,
            "functions": [
                {
                    "name": "test_init",
                    "address": "0x1000",
                    "size": 100,
                    "is_external": False,
                    "is_thunk": False,
                },
                {
                    "name": "test_func",
                    "address": "0x3000",
                    "size": 50,
                    "is_external": False,
                    "is_thunk": False,
                },
                {
                    "name": "vendor_helper",
                    "address": "0x4000",
                    "size": 30,
                    "is_external": False,
                    "is_thunk": False,
                },
            ],
            "symbols": [],
            "imports": [],
            "exports": [],
            "gpl_strings": [],
        }
        (ghidra_dir / "generic_test_driver.json").write_text(json.dumps(generic_data))

        # Set up mock upstream
        upstream_dir = tmp_path / "upstream"
        kernel_dir = upstream_dir / "linux" / "drivers" / "test"
        kernel_dir.mkdir(parents=True)
        (kernel_dir / "test.c").write_text(
            "static int test_init(struct platform_device *pdev) { return 0; }\n"
            "int test_func(void) { return 42; }\n"
        )

        analysis = CrossReferenceAnalysis(
            upstream_kernel_version="4.19.111",
            upstream_uboot_version="2017.09",
        )
        parse_and_classify(ghidra_dir, upstream_dir / "linux", None, analysis)

        assert analysis.total_functions_analyzed == 3
        # test_init and test_func found upstream, vendor_helper not
        assert analysis.vendor_added_count >= 1
