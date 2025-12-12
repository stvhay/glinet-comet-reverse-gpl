#!/usr/bin/env bash
# Batch render all wiki templates
#
# Usage: ./scripts/render_wiki.sh
#
# Discovers all templates in templates/wiki/*.md.j2 and renders them to wiki/*.md
# using render_template.py. Shows progress and reports any failures at the end.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# shellcheck disable=SC1091  # lib/common.sh is sourced at runtime
source "$SCRIPT_DIR/lib/common.sh"

# Directories
TEMPLATES_DIR="$PROJECT_ROOT/templates/wiki"
OUTPUT_DIR="$PROJECT_ROOT/wiki"
RENDERER="$SCRIPT_DIR/render_template.py"

# Require Python and render_template.py
require_command python3

# Check for Jinja2 module
if ! python3 -c "import jinja2" 2>/dev/null; then
    error "Python module 'jinja2' not found"
    error "Please run this script within 'nix develop' shell"
    exit 1
fi

if [[ ! -f "$RENDERER" ]]; then
    error "Renderer not found: $RENDERER"
    exit 1
fi

# Find all wiki templates
section "Discovering templates"

if [[ ! -d "$TEMPLATES_DIR" ]]; then
    warn "Templates directory not found: $TEMPLATES_DIR"
    info "No templates to render"
    exit 0
fi

# Use mapfile to safely handle filenames with spaces
mapfile -t TEMPLATES < <(find "$TEMPLATES_DIR" -name "*.md.j2" -type f | sort)

if [[ ${#TEMPLATES[@]} -eq 0 ]]; then
    info "No templates found in $TEMPLATES_DIR"
    exit 0
fi

info "Found ${#TEMPLATES[@]} template(s)"

# Render each template
section "Rendering templates"

FAILED=()
SUCCESS_COUNT=0

for template in "${TEMPLATES[@]}"; do
    # Calculate output path: templates/wiki/Foo.md.j2 -> wiki/Foo.md
    base=$(basename "$template" .md.j2)
    output="$OUTPUT_DIR/${base}.md"

    # Show progress
    info "Rendering: $base.md.j2 -> $base.md"

    # Render template (capture both stdout and stderr, but let renderer print to stderr)
    if python3 "$RENDERER" "$template" "$output" 2>&1; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        FAILED+=("$template")
        error "Failed to render: $base.md.j2"
    fi
done

# Report results
section "Summary"

echo ""
if [[ ${#FAILED[@]} -eq 0 ]]; then
    success "All $SUCCESS_COUNT template(s) rendered successfully"
    echo ""
    echo "Output: $OUTPUT_DIR/"
    exit 0
else
    error "Failed to render ${#FAILED[@]} template(s):"
    echo ""
    for template in "${FAILED[@]}"; do
        echo "  ✗ $(basename "$template")"
    done
    echo ""
    info "Successfully rendered: $SUCCESS_COUNT"
    info "Failed: ${#FAILED[@]}"
    exit 1
fi
