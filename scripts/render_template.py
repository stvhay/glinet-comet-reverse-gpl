#!/usr/bin/env python3
"""
Render Jinja templates with analysis data.

Usage:
    ./scripts/render_template.py templates/test.md.j2 output/test.md
    ./scripts/render_template.py templates/test.md.j2  # outputs to stdout
"""

import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

# Add scripts directory to path so we can import analysis
sys.path.insert(0, str(Path(__file__).parent))

from analysis import analyze, TrackedValue


class FootnoteRegistry:
    """
    Registry for automatic footnote generation during template rendering.

    Tracks all footnotes and assigns sequential numbers.
    """

    def __init__(self):
        self.footnotes = []  # List of (source, method) tuples
        self.footnote_map = {}  # Map (source, method) to footnote number

    def add(self, tracked_value: TrackedValue) -> int:
        """
        Add a tracked value's source info to footnotes.

        Returns the footnote number.
        """
        key = (tracked_value.source, tracked_value.method)

        # Return existing footnote number if already registered
        if key in self.footnote_map:
            return self.footnote_map[key]

        # Add new footnote
        self.footnotes.append(key)
        footnote_num = len(self.footnotes)
        self.footnote_map[key] = footnote_num
        return footnote_num

    def render(self) -> str:
        """Render all collected footnotes as markdown."""
        if not self.footnotes:
            return ""

        lines = ["\n## Sources\n"]
        for i, (source, method) in enumerate(self.footnotes, 1):
            script_link = f"[scripts/analyze_{source}.sh](../scripts/analyze_{source}.sh)"
            if method:
                lines.append(f"[^{i}]: {script_link} - `{method}`")
            else:
                lines.append(f"[^{i}]: {script_link}")

        return "\n".join(lines)


def render_template(template_path: Path, output_path: Path = None) -> str:
    """
    Render a Jinja template with analysis functions available.

    Args:
        template_path: Path to .j2 template file
        output_path: Optional output path (if None, returns string)

    Returns:
        Rendered content as string
    """
    # Set up Jinja environment
    templates_dir = template_path.parent
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(['html', 'xml']),
        trim_blocks=True,
        lstrip_blocks=True
    )

    # Create footnote registry for this render
    footnote_registry = FootnoteRegistry()

    def src_filter(value):
        """
        Jinja filter to render a value with source footnote.

        Usage in template:
            {{ kernel.offset | src }}

        If value is a TrackedValue, renders as "value[^N]" with footnote.
        Otherwise, just renders the value.
        """
        if isinstance(value, TrackedValue):
            footnote_num = footnote_registry.add(value)
            return Markup(f"{value.value}[^{footnote_num}]")
        return str(value)

    def render_footnotes():
        """Function to render all collected footnotes."""
        return Markup(footnote_registry.render())

    # Make functions available to templates
    env.globals['analyze'] = analyze
    env.globals['render_footnotes'] = render_footnotes
    env.filters['src'] = src_filter

    # Load and render template
    template = env.get_template(template_path.name)
    rendered = template.render()

    # Write to file or return
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered)
        print(f"Rendered: {template_path} -> {output_path}", file=sys.stderr)
    else:
        return rendered

    return rendered


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: render_template.py TEMPLATE [OUTPUT]", file=sys.stderr)
        print("\nExamples:", file=sys.stderr)
        print("  render_template.py templates/test.md.j2", file=sys.stderr)
        print("  render_template.py templates/test.md.j2 output/test.md", file=sys.stderr)
        sys.exit(1)

    template_path = Path(sys.argv[1])
    if not template_path.exists():
        print(f"Error: Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    try:
        rendered = render_template(template_path, output_path)
        if not output_path:
            # Print to stdout if no output file specified
            print(rendered)
    except Exception as e:
        print(f"Error rendering template: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
