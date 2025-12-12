#!/usr/bin/env python3
"""Render gist status from scratchpad using Jinja template."""

import re
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

SCRATCHPAD_PATH = Path("/tmp/claude-glinet-comet-reversing/scratchpad.md")
GIST_ID_FILE = Path("/tmp/claude-glinet-comet-reversing/gist-id.txt")
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def main():
    """Render gist template with current scratchpad content."""
    # Read scratchpad
    if not SCRATCHPAD_PATH.exists():
        print(f"Error: Scratchpad not found at {SCRATCHPAD_PATH}", file=sys.stderr)
        sys.exit(1)

    scratchpad_content = SCRATCHPAD_PATH.read_text()

    # Read gist ID
    if not GIST_ID_FILE.exists():
        print("Error: Gist not created yet. Run ./scripts/create-status-gist.sh first", file=sys.stderr)
        sys.exit(1)

    gist_id = GIST_ID_FILE.read_text().strip()

    # Update timestamp in scratchpad content
    timestamp = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p %Z")
    scratchpad_content = re.sub(
        r'^\*\*Last Updated:\*\* .*',
        f'**Last Updated:** {timestamp}',
        scratchpad_content,
        flags=re.MULTILINE
    )

    # Render template
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("gist-status.md.j2")
    rendered = template.render(
        scratchpad_content=scratchpad_content,
        gist_id=gist_id,
    )

    # Output to stdout
    print(rendered, end='')


if __name__ == "__main__":
    main()
