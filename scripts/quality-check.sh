#!/usr/bin/env bash
# Run all quality checks that CI runs
# Use this before committing to catch issues early

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

# Track if any checks fail
FAILED=0

echo "1️⃣  Shellcheck on bash scripts..."
if shellcheck scripts/*.sh 2>/dev/null; then
    echo -e "${GREEN}✅ Shellcheck passed${NC}"
else
    echo -e "${RED}❌ Shellcheck failed${NC}"
    FAILED=1
fi
echo ""

echo "2️⃣  Ruff linting..."
if ruff check scripts/ tests/; then
    echo -e "${GREEN}✅ Linting passed${NC}"
else
    echo -e "${RED}❌ Linting failed${NC}"
    echo -e "${YELLOW}   Fix with: ruff check --fix scripts/ tests/${NC}"
    FAILED=1
fi
echo ""

echo "3️⃣  Ruff formatting check..."
if ruff format --check scripts/ tests/; then
    echo -e "${GREEN}✅ Formatting check passed${NC}"
else
    echo -e "${RED}❌ Formatting check failed${NC}"
    echo -e "${YELLOW}   Fix with: ruff format scripts/ tests/${NC}"
    FAILED=1
fi
echo ""

echo "4️⃣  Running pytest with coverage..."
if pytest; then
    echo -e "${GREEN}✅ All tests passed with coverage${NC}"
else
    echo -e "${RED}❌ Tests failed${NC}"
    FAILED=1
fi
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅✅✅ All quality checks passed! ✅✅✅${NC}"
    echo ""
    echo "Safe to commit and push."
    exit 0
else
    echo -e "${RED}❌❌❌ Some quality checks failed ❌❌❌${NC}"
    echo ""
    echo "Please fix the issues above before committing."
    exit 1
fi
