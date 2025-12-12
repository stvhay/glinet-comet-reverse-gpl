#!/usr/bin/env python3
"""Base class for firmware analysis scripts.

This module provides a common framework for all analysis scripts,
eliminating boilerplate and ensuring consistent behavior.
"""

import argparse
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from lib.analysis_base import AnalysisBase
from lib.firmware import extract_firmware, find_squashfs_rootfs, get_firmware_path
from lib.logging import error, info, success, warn
from lib.output import output_json, output_toml


class AnalysisScript(ABC):
    """Base class for firmware analysis scripts.

    Provides common argument parsing, firmware loading, and output formatting.
    Subclasses only need to implement the analyze() method and define metadata.

    Example:
        class BinwalkScript(AnalysisScript):
            def __init__(self):
                super().__init__(
                    description="Analyze firmware structure using binwalk",
                    title="Binwalk firmware analysis",
                    simple_fields=["firmware_file", "squashfs_count"],
                    complex_fields=["identified_components"],
                )

            def analyze(self, firmware_path: str) -> AnalysisBase:
                return analyze_firmware(firmware_path)

        if __name__ == "__main__":
            BinwalkScript().run()
    """

    def __init__(
        self,
        description: str,
        title: str,
        simple_fields: list[str],
        complex_fields: list[str],
        work_dir: Path | None = None,
    ):
        """Initialize the analysis script.

        Args:
            description: Description for argument parser help text
            title: Title for TOML output header
            simple_fields: List of simple field names for TOML output
            complex_fields: List of complex field names for TOML output
            work_dir: Working directory for firmware extraction (default: /tmp/fw_analysis)
        """
        self.description = description
        self.title = title
        self.simple_fields = simple_fields
        self.complex_fields = complex_fields
        self.work_dir = work_dir or Path("/tmp/fw_analysis")

    @abstractmethod
    def analyze(self, firmware_path: str) -> AnalysisBase:
        """Perform the analysis on the firmware.

        This method must be implemented by subclasses to perform
        the actual analysis work.

        Args:
            firmware_path: Path to firmware file

        Returns:
            Analysis results as an AnalysisBase subclass
        """
        pass

    def post_process(self, analysis: AnalysisBase) -> None:  # noqa: B027
        """Optional post-processing after analysis.

        Override this method to perform additional work after analysis,
        such as writing legacy files or generating artifacts.

        Args:
            analysis: The completed analysis results
        """
        # Intentionally empty - this is an optional hook, not required
        ...

    def get_success_message(self, _analysis: AnalysisBase) -> str:
        """Generate success message after analysis.

        Override this to customize the success message.

        Args:
            _analysis: The completed analysis results (unused in base implementation)

        Returns:
            Success message string
        """
        return f"{self.title} complete"

    # Helper methods for common patterns

    @property
    def output_dir(self) -> Path:
        """Get output directory, creating if needed.

        Returns:
            Path to output/ directory
        """
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        output_dir = project_root / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def initialize_analysis(
        self,
        analysis_class: type[AnalysisBase],
        firmware_path: str,
        **kwargs,
    ) -> tuple[Path, AnalysisBase]:
        """Create analysis object with standard firmware metadata.

        Args:
            analysis_class: The AnalysisBase subclass to instantiate
            firmware_path: Path to firmware file
            **kwargs: Additional arguments to pass to analysis_class constructor

        Returns:
            Tuple of (firmware Path object, instantiated analysis object)
        """
        firmware = Path(firmware_path)
        analysis = analysis_class(
            firmware_file=firmware.name,
            firmware_size=firmware.stat().st_size,
            **kwargs,
        )
        analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")
        analysis.add_metadata("firmware_size", "filesystem", "Path(firmware).stat().st_size")
        return firmware, analysis

    def initialize_extraction(
        self, firmware_path: str, need_rootfs: bool = True
    ) -> tuple[Path, Path] | Path:
        """Extract firmware and optionally find rootfs.

        Args:
            firmware_path: Path to firmware file
            need_rootfs: Whether to find and return rootfs path

        Returns:
            If need_rootfs=True: tuple of (extract_dir, rootfs)
            If need_rootfs=False: extract_dir only
        """
        firmware = Path(firmware_path)
        extract_dir = extract_firmware(firmware, self.work_dir)

        if need_rootfs:
            rootfs = find_squashfs_rootfs(extract_dir)
            return extract_dir, rootfs
        return extract_dir

    def load_offsets(self, require_exists: bool = True) -> dict[str, str | int]:
        """Load firmware offsets from binwalk-offsets.sh.

        Args:
            require_exists: If True, exit with error if file doesn't exist.
                           If False, return empty dict with warning.

        Returns:
            Dictionary mapping offset names to values (str for hex, int for decimal)
        """
        offsets_file = self.output_dir / "binwalk-offsets.sh"

        if not offsets_file.exists():
            if require_exists:
                error(f"Firmware offsets not found: {offsets_file}")
                error("Run analyze_binwalk.py first to generate offsets")
                sys.exit(1)
            else:
                warn(f"Firmware offsets not found: {offsets_file}")
                return {}

        offsets = {}
        with offsets_file.open() as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    key, value = line.split("=", 1)
                    value = value.strip('"').strip("'")

                    # Store decimal values as int, hex as string
                    if key.endswith("_DEC"):
                        offsets[key] = int(value)
                    else:
                        offsets[key] = value

        return offsets

    def format_count_message(self, count: int, item_type: str) -> str:
        """Generate 'Analyzed N item(s)' message.

        Args:
            count: Number of items
            item_type: Type of item (e.g., "device tree", "kernel module")

        Returns:
            Formatted message string
        """
        plural = "" if count == 1 else "s"
        return f"Analyzed {count} {item_type}{plural}"

    def write_legacy_file(
        self,
        filename: str,
        content_generator: Callable[[TextIO], None],
        success_message: str | None = None,
    ) -> None:
        """Write legacy output file with standard pattern.

        Args:
            filename: Name of file to write in output directory
            content_generator: Callback function that writes content to file handle
            success_message: Optional success message (default: "Wrote {filename}")
        """
        output_file = self.output_dir / filename
        with output_file.open("w") as f:
            content_generator(f)
        success(success_message or f"Wrote {filename}")

    def _parse_args(self) -> argparse.Namespace:
        """Parse command line arguments.

        Returns:
            Parsed arguments
        """
        parser = argparse.ArgumentParser(
            description=self.description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "firmware",
            nargs="?",
            help="Path to firmware file (downloads default if not provided)",
        )
        parser.add_argument(
            "--format",
            choices=["toml", "json"],
            default="toml",
            help="Output format (default: toml)",
        )
        return parser.parse_args()

    def _output_results(self, analysis: AnalysisBase, format: str) -> None:
        """Output analysis results in requested format.

        Args:
            analysis: The completed analysis results
            format: Output format ("toml" or "json")
        """
        if format == "json":
            print(output_json(analysis))
        else:  # toml
            print(
                output_toml(
                    analysis,
                    title=self.title,
                    simple_fields=self.simple_fields,
                    complex_fields=self.complex_fields,
                )
            )

    def run(self) -> None:
        """Main entry point for the script.

        Parses arguments, loads firmware, runs analysis, outputs results.
        """
        # Parse arguments
        args = self._parse_args()

        # Get firmware path
        firmware = get_firmware_path(args.firmware, self.work_dir)
        firmware_path = str(firmware)

        # Standard analyzing message
        info(f"Analyzing: {firmware.name}")

        # Run analysis
        analysis = self.analyze(firmware_path)

        # Output results
        self._output_results(analysis, args.format)

        # Post-processing (optional)
        self.post_process(analysis)

        # Success message
        success(self.get_success_message(analysis))
