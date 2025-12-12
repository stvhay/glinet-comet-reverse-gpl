"""Base class for analysis dataclasses with source metadata tracking.

This module provides a mixin class that adds source metadata tracking
capabilities to dataclasses.
"""

from dataclasses import fields
from typing import Any


class AnalysisBase:
    """Mixin class for analysis dataclasses.

    Provides:
    - add_metadata() method for tracking source/method metadata
    - to_dict() method that converts dataclass to dict with metadata

    Usage:
        @dataclass
        class MyAnalysis(AnalysisBase):
            field1: str
            field2: int
            _source: dict[str, str] = field(default_factory=dict)
            _method: dict[str, str] = field(default_factory=dict)

            def _convert_complex_field(
                self, key: str, value: Any
            ) -> tuple[bool, Any]:
                # Handle custom field conversions
                if key == "my_complex_field":
                    return True, [item.to_dict() for item in value]
                return False, None
    """

    _source: dict[str, str]
    _method: dict[str, str]

    def add_metadata(self, field_name: str, source: str, method: str) -> None:
        """Add source metadata for a field.

        Args:
            field_name: Name of the field
            source: Source of the data (e.g., "U-Boot", "DTS")
            method: Method used to extract data (e.g., "strings | grep")
        """
        self._source[field_name] = source
        self._method[field_name] = method

    def _convert_complex_field(self, key: str, value: Any) -> tuple[bool, Any]:  # noqa: ARG002
        """Convert a complex field to a serializable format.

        Subclasses should override this to handle their custom field types.

        Args:
            key: Field name
            value: Field value

        Returns:
            Tuple of (handled, converted_value)
            - handled: True if this method handled the conversion
            - converted_value: The converted value (only used if handled=True)
        """
        return False, None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with source metadata.

        Returns:
            Dictionary with all fields and their source metadata
        """
        result: dict[str, Any] = {}

        for fld in fields(self):  # type: ignore
            key = fld.name
            if key.startswith("_"):
                continue

            value = getattr(self, key)
            if value is None:
                continue

            # Skip empty lists
            if isinstance(value, list) and not value:
                continue

            # Try custom field conversion first
            handled, converted = self._convert_complex_field(key, value)
            if handled:
                result[key] = converted
            else:
                # Default: just use the value as-is
                result[key] = value

                # Add source metadata for simple fields
                if key in self._source:
                    result[f"{key}_source"] = self._source[key]
                if key in self._method:
                    result[f"{key}_method"] = self._method[key]

        return result
