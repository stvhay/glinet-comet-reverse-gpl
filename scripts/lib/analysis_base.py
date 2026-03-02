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
            _reproducibility: dict[str, str] = field(default_factory=dict)
            _hardware_metadata: dict[str, dict[str, str]] = field(default_factory=dict)

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
    _reproducibility: dict[str, str]
    _hardware_metadata: dict[str, dict[str, str]]

    def add_metadata(
        self,
        field_name: str,
        source: str,
        method: str,
        reproducibility: str = "software",
    ) -> None:
        """Add source metadata for a field.

        Args:
            field_name: Name of the field
            source: Source of the data (e.g., "U-Boot", "DTS")
            method: Method used to extract data (e.g., "strings | grep")
            reproducibility: Reproducibility class ("software" or "hardware")
        """
        self._source[field_name] = source
        self._method[field_name] = method
        self._reproducibility[field_name] = reproducibility

    def add_hardware_metadata(
        self,
        field_name: str,
        source: str,
        method: str,
        *,
        equipment: str,
        procedure: str,
        performed: str,
        operator: str,
    ) -> None:
        """Add hardware-dependent metadata for a field.

        Args:
            field_name: Name of the field
            source: Source of the data
            method: Method used to extract data
            equipment: Equipment used (e.g., "UART adapter")
            procedure: Procedure followed
            performed: Date performed
            operator: Person who performed the measurement
        """
        self.add_metadata(field_name, source, method, reproducibility="hardware")
        self._hardware_metadata[field_name] = {
            "equipment": equipment,
            "procedure": procedure,
            "performed": performed,
            "operator": operator,
        }

    def set_count_with_metadata(
        self,
        field_name: str,
        items: list[Any],
        source: str,
        method: str,
        reproducibility: str = "software",
    ) -> None:
        """Set a count field to len(items) and add metadata.

        Common pattern: count how many items and track the source.

        Args:
            field_name: Name of the count field (e.g., "device_tree_count")
            items: List to count
            source: Source of the data (e.g., "filesystem")
            method: Method used to extract data (e.g., "find ... -name '*.dtb'")
            reproducibility: Reproducibility class ("software" or "hardware")
        """
        setattr(self, field_name, len(items))
        self.add_metadata(field_name, source, method, reproducibility)

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

            # Add source metadata for all fields (simple and complex)
            if key in self._source:
                result[f"{key}_source"] = self._source[key]
            if key in self._method:
                result[f"{key}_method"] = self._method[key]
            if key in self._reproducibility:
                result[f"{key}_reproducibility"] = self._reproducibility[key]
            if key in self._hardware_metadata:
                hw = self._hardware_metadata[key]
                for hw_key in ("equipment", "procedure", "performed", "operator"):
                    result[f"{key}_{hw_key}"] = hw[hw_key]

        return result
