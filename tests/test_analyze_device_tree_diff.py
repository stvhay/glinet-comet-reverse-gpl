#!/usr/bin/env python3
"""Tests for scripts/analyze_device_tree_diff.py."""

import sys
from pathlib import Path

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from analyze_device_tree_diff import _extract_model_and_compatible, analyze

SAMPLE_DTS = """\
/dts-v1/;

/ {
    model = "rm1";
    compatible = "rockchip,rv1126-evb-ddr3-v13", "rockchip,rv1126";

    chosen {
        bootargs = "earlycon=uart8250,mmio32,0xff570000";
    };
};
"""


class TestAnalyze:
    """Test analyze() function."""

    def test_returns_all_expected_keys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test analyze() returns all keys expected by the template."""
        monkeypatch.chdir(tmp_path)
        dts_dir = tmp_path / "output" / "dtb"
        dts_dir.mkdir(parents=True)
        (dts_dir / "kernel-fit.dts").write_text(SAMPLE_DTS)

        result = analyze()

        expected_keys = {
            "model",
            "compatible",
            "reference_board",
            "customization_level",
            "gpl_implications",
            "reference_sources",
        }
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_extracts_model_from_dts(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test model extraction from sample DTS."""
        monkeypatch.chdir(tmp_path)
        dts_dir = tmp_path / "output" / "dtb"
        dts_dir.mkdir(parents=True)
        (dts_dir / "kernel-fit.dts").write_text(SAMPLE_DTS)

        result = analyze()

        assert result["model"] == "rm1"

    def test_extracts_compatible_from_dts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test compatible string extraction from sample DTS."""
        monkeypatch.chdir(tmp_path)
        dts_dir = tmp_path / "output" / "dtb"
        dts_dir.mkdir(parents=True)
        (dts_dir / "kernel-fit.dts").write_text(SAMPLE_DTS)

        result = analyze()

        assert result["compatible"] == "rockchip,rv1126-evb-ddr3-v13"

    def test_all_source_fields_equal_device_tree_diff(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test all _source fields equal 'device_tree_diff'."""
        monkeypatch.chdir(tmp_path)
        dts_dir = tmp_path / "output" / "dtb"
        dts_dir.mkdir(parents=True)
        (dts_dir / "kernel-fit.dts").write_text(SAMPLE_DTS)

        result = analyze()

        for key, value in result.items():
            if key.endswith("_source"):
                assert value == "device_tree_diff", f"{key} = {value!r}"

    def test_error_when_dts_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test FileNotFoundError when DTS file doesn't exist."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(FileNotFoundError, match=r"kernel-fit\.dts"):
            analyze()

    def test_unknown_model_when_not_in_dts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 'Unknown' model when DTS has no model line."""
        monkeypatch.chdir(tmp_path)
        dts_dir = tmp_path / "output" / "dtb"
        dts_dir.mkdir(parents=True)
        (dts_dir / "kernel-fit.dts").write_text("/dts-v1/;\n/ { };\n")

        result = analyze()

        assert result["model"] == "Unknown"
        assert result["compatible"] == "Unknown"

    def test_reference_sources_is_list(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test reference_sources is a list of URLs."""
        monkeypatch.chdir(tmp_path)
        dts_dir = tmp_path / "output" / "dtb"
        dts_dir.mkdir(parents=True)
        (dts_dir / "kernel-fit.dts").write_text(SAMPLE_DTS)

        result = analyze()

        assert isinstance(result["reference_sources"], list)
        assert len(result["reference_sources"]) == 3
        for url in result["reference_sources"]:
            assert url.startswith("https://")


class TestExtractModelAndCompatible:
    """Test _extract_model_and_compatible helper."""

    def test_extracts_both(self) -> None:
        model, compatible = _extract_model_and_compatible(SAMPLE_DTS)
        assert model == "rm1"
        assert compatible == "rockchip,rv1126-evb-ddr3-v13"

    def test_empty_content(self) -> None:
        model, compatible = _extract_model_and_compatible("")
        assert model is None
        assert compatible is None

    def test_model_only(self) -> None:
        model, compatible = _extract_model_and_compatible('    model = "test-board";')
        assert model == "test-board"
        assert compatible is None

    def test_takes_first_compatible(self) -> None:
        content = '    compatible = "first";\n    compatible = "second";'
        _, compatible = _extract_model_and_compatible(content)
        assert compatible == "first"
