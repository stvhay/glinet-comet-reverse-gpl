"""Firmware offset management utilities.

Provides unified interface for loading and writing firmware offsets
from binwalk analysis results.
"""

from pathlib import Path


class OffsetManager:
    """Manage firmware offsets from binwalk analysis."""

    def __init__(self, output_dir: Path | None = None):
        """Initialize offset manager.

        Args:
            output_dir: Directory containing offset files (optional)
        """
        self.output_dir = output_dir
        self.offsets: dict[str, int | str] = {}

    def load_from_shell_script(self, script_path: Path | None = None) -> None:
        """Load offsets from binwalk-offsets.sh.

        Args:
            script_path: Path to shell script (defaults to output_dir/binwalk-offsets.sh)

        Raises:
            FileNotFoundError: If script file doesn't exist
        """
        if script_path is None:
            if self.output_dir is None:
                raise ValueError("output_dir must be set or script_path must be provided")
            script_path = self.output_dir / "binwalk-offsets.sh"

        if not script_path.exists():
            raise FileNotFoundError(f"Offsets file not found: {script_path}")

        self.offsets = {}
        with script_path.open() as f:
            for raw_line in f:
                line = raw_line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Parse variable assignments
                if "=" in line:
                    key, value = line.split("=", 1)
                    # Strip quotes from value
                    value = value.strip('"').strip("'")
                    # Parse decimal values
                    if key.endswith("_DEC"):
                        self.offsets[key] = int(value)
                    # Keep hex values as strings
                    else:
                        self.offsets[key] = value

    def get(self, key: str, default=None) -> int | str | None:
        """Get offset by key.

        Args:
            key: Offset key (e.g., 'UBOOT_GZ_OFFSET' or 'UBOOT_GZ_OFFSET_DEC')
            default: Default value if key not found

        Returns:
            Offset value (hex string or decimal int) or default
        """
        return self.offsets.get(key, default)

    def get_hex(self, name: str) -> str | None:
        """Get hex offset (e.g., '0x8F1B4').

        Args:
            name: Offset name without suffix (e.g., 'UBOOT_GZ')

        Returns:
            Hex offset string or None
        """
        key = f"{name}_OFFSET"
        value = self.offsets.get(key)
        return value if isinstance(value, str) else None

    def get_dec(self, name: str) -> int | None:
        """Get decimal offset.

        Args:
            name: Offset name without suffix (e.g., 'UBOOT_GZ')

        Returns:
            Decimal offset or None
        """
        key = f"{name}_OFFSET_DEC"
        value = self.offsets.get(key)
        return value if isinstance(value, int) else None

    def __contains__(self, key: str) -> bool:
        """Check if offset key exists.

        Args:
            key: Offset key to check

        Returns:
            True if key exists
        """
        return key in self.offsets

    def __getitem__(self, key: str) -> int | str:
        """Get offset by key (raises KeyError if not found).

        Args:
            key: Offset key

        Returns:
            Offset value

        Raises:
            KeyError: If key not found
        """
        return self.offsets[key]
