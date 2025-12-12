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
        auto_simple: list[str] = []
        auto_complex: list[str] = []

        for key, value in data.items():
            # Skip metadata fields
            if key.endswith("_source") or key.endswith("_method"):
                continue

            # Classify by type
            if isinstance(value, list | dict):
                auto_complex.append(key)
            else:
                auto_simple.append(key)

        if simple_fields is None:
            simple_fields = auto_simple
        if complex_fields is None:
            complex_fields = auto_complex

    # Add simple fields first (primitives with metadata comments)
    for key in simple_fields:
        if key not in data:
            continue

        value = data[key]

        # Add source metadata as comment
        if f"{key}_source" in data:
            doc.add(tomlkit.comment(f"Source: {data[f'{key}_source']}"))
        if f"{key}_method" in data:
            method = data[f"{key}_method"]
            if len(method) > TOML_MAX_COMMENT_LENGTH:
                doc.add(
                    tomlkit.comment(
                        f"Method: {method[:TOML_COMMENT_TRUNCATE_LENGTH]}..."
                    )
                )
            else:
                doc.add(tomlkit.comment(f"Method: {method}"))

        doc.add(key, value)
        doc.add(tomlkit.nl())

    # Add complex fields (arrays/objects with header comments)
    for key in complex_fields:
        if key not in data or not data[key]:
            continue

        # Add descriptive header comment
        doc.add(tomlkit.comment(key.replace("_", " ").title()))
        doc.add(key, data[key])
        doc.add(tomlkit.nl())

    # Generate TOML string
    toml_str = tomlkit.dumps(doc)

    # Validate by parsing it back
    try:
        tomlkit.loads(toml_str)
    except Exception as e:
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
    except Exception as e:
        error(f"Generated invalid JSON: {e}")
        sys.exit(1)

    return json_str
