"""Output formatting utilities for analysis scripts.

This module provides functions to convert analysis results to TOML and JSON formats
with source metadata tracking.
"""

import json
import sys
from datetime import UTC, datetime
from typing import Any

import tomlkit

from .logging import error

# TOML formatting constants
TOML_MAX_COMMENT_LENGTH = 80
TOML_COMMENT_TRUNCATE_LENGTH = 77

# Metadata suffix patterns used to identify metadata keys
METADATA_SUFFIXES = (
    "_source",
    "_method",
    "_reproducibility",
    "_equipment",
    "_procedure",
    "_performed",
    "_operator",
)


def _auto_detect_fields(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Classify data fields into simple (primitives) and complex (lists/dicts).

    Returns:
        Tuple of (simple_fields, complex_fields)
    """
    simple: list[str] = []
    complex_: list[str] = []

    for key, value in data.items():
        # Skip metadata keys where the base field exists in data
        if any(key.endswith(suffix) for suffix in METADATA_SUFFIXES):
            suffix = next(s for s in METADATA_SUFFIXES if key.endswith(s))
            base_key = key[: -len(suffix)]
            if base_key in data:
                continue

        if isinstance(value, list | dict):
            complex_.append(key)
        else:
            simple.append(key)

    return simple, complex_


def _add_simple_fields(
    doc: tomlkit.TOMLDocument, data: dict[str, Any], simple_fields: list[str]
) -> None:
    """Add simple fields with source metadata comments to TOML document."""
    for key in simple_fields:
        if key not in data:
            continue

        value = data[key]

        if f"{key}_source" in data:
            doc.add(tomlkit.comment(f"Source: {data[f'{key}_source']}"))
        if f"{key}_method" in data:
            method = data[f"{key}_method"]
            if len(method) > TOML_MAX_COMMENT_LENGTH:
                doc.add(tomlkit.comment(f"Method: {method[:TOML_COMMENT_TRUNCATE_LENGTH]}..."))
            else:
                doc.add(tomlkit.comment(f"Method: {method}"))
        if f"{key}_reproducibility" in data:
            doc.add(tomlkit.comment(f"Reproducibility: {data[f'{key}_reproducibility']}"))
        for hw_field in ("equipment", "procedure", "performed", "operator"):
            hw_key = f"{key}_{hw_field}"
            if hw_key in data:
                val = data[hw_key]
                if len(val) > TOML_MAX_COMMENT_LENGTH:
                    val = val[:TOML_COMMENT_TRUNCATE_LENGTH] + "..."
                doc.add(tomlkit.comment(f"{hw_field.title()}: {val}"))

        doc.add(key, value)
        doc.add(tomlkit.nl())


def output_toml(
    analysis: Any,
    title: str,
    simple_fields: list[str] | None = None,
    complex_fields: list[str] | None = None,
) -> str:
    """Convert analysis to TOML format with source metadata.

    Args:
        analysis: Analysis object with to_dict() method
        title: Title for the TOML document header
        simple_fields: Optional list of simple field names (in order)
                      If None, auto-detects primitives from to_dict()
        complex_fields: Optional list of complex field names (in order)
                       If None, auto-detects lists/dicts from to_dict()

    Returns:
        TOML string with source metadata as comments
    """
    doc = tomlkit.document()

    # Add header
    doc.add(tomlkit.comment(title))
    doc.add(tomlkit.comment(f"Generated: {datetime.now(UTC).isoformat()}"))
    doc.add(tomlkit.nl())

    # Convert analysis to dict
    data = analysis.to_dict()

    # Auto-detect simple vs complex fields if not provided
    if simple_fields is None or complex_fields is None:
        auto_simple, auto_complex = _auto_detect_fields(data)
        if simple_fields is None:
            simple_fields = auto_simple
        if complex_fields is None:
            complex_fields = auto_complex

    # Add simple fields first (primitives with metadata comments)
    _add_simple_fields(doc, data, simple_fields)

    # Add complex fields (arrays/objects with header comments)
    for key in complex_fields:
        if key not in data or not data[key]:
            continue

        doc.add(tomlkit.comment(key.replace("_", " ").title()))
        doc.add(key, data[key])
        doc.add(tomlkit.nl())

    # Generate TOML string
    toml_str: str = tomlkit.dumps(doc)

    # Validate by parsing it back
    try:
        tomlkit.loads(toml_str)
    except (tomlkit.exceptions.ParseError, ValueError) as e:
        error(f"Generated invalid TOML: {e}")
        sys.exit(1)

    return toml_str


def output_json(analysis: Any) -> str:
    """Convert analysis to JSON format with source metadata.

    Args:
        analysis: Analysis object with to_dict() method

    Returns:
        JSON string with source metadata
    """
    json_str = json.dumps(analysis.to_dict(), indent=2)

    # Validate by parsing it back
    try:
        json.loads(json_str)
    except (json.JSONDecodeError, ValueError) as e:
        error(f"Generated invalid JSON: {e}")
        sys.exit(1)

    return json_str
