#!/usr/bin/env python3
"""Base class for firmware analysis scripts.

This module provides a common framework for all analysis scripts,
eliminating boilerplate and ensuring consistent behavior.
"""

import argparse
from abc import ABC, abstractmethod
from pathlib import Path

from lib.analysis_base import AnalysisBase
from lib.firmware import get_firmware_path
from lib.logging import success
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

        # Run analysis
        analysis = self.analyze(firmware_path)

        # Output results
        self._output_results(analysis, args.format)

        # Post-processing (optional)
        self.post_process(analysis)

        # Success message
        success(self.get_success_message(analysis))
