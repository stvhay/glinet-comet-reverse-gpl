#!/usr/bin/env bash
# Run all quality checks that CI runs
# Use this before committing to catch issues early
#
# This script runs pytest, which includes:
# - All unit tests (556+ tests)
# - Code quality tests (format/lint/shellcheck)
# - Coverage checks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Running quality checks..."
echo ""

# Change to repo root
cd "$(git rev-parse --show-toplevel)"

# Check if we're in nix develop shell
if [ -z "$IN_NIX_SHELL" ]; then
    echo -e "${YELLOW}⚠️  Not in nix shell, entering nix develop...${NC}"
    exec nix develop --command bash "$0" "$@"
fi

echo "Running pytest (includes all tests + format/lint checks)..."
echo ""

if pytest; then
    echo ""
    echo -e "${GREEN}✅✅✅ All quality checks passed! ✅✅✅${NC}"
    echo ""
    echo "Safe to commit and push."
    exit 0
else
    echo ""
    echo -e "${RED}❌❌❌ Some quality checks failed ❌❌❌${NC}"
    echo ""
    echo "Quick fixes:"
    echo "  - See specific failures: pytest tests/test_code_quality.py -v"
    echo "  - Fix linting: ruff check --fix scripts/ tests/"
    echo "  - Fix formatting: ruff format scripts/ tests/"
    exit 1
fi
