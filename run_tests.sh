#!/bin/bash
# Test runner script for the Processing bot

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}Processing Bot - Test Suite Runner${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}\n"

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}⚠️  Virtual environment not detected. Activating...${NC}"
    source .venv/bin/activate
fi

# Install/update test dependencies
echo -e "${YELLOW}📦 Installing test dependencies...${NC}"
pip install -q pytest pytest-asyncio pytest-cov pytest-mock

echo -e "\n${YELLOW}🧪 Running test suite...${NC}\n"

# Run tests with different options based on arguments
case "${1:-}" in
    "coverage")
        echo -e "${BLUE}Running tests with coverage report...${NC}"
        pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing
        echo -e "\n${GREEN}✓ Coverage report generated in htmlcov/index.html${NC}"
        ;;
    "fast")
        echo -e "${BLUE}Running tests (fast mode, minimal output)...${NC}"
        pytest tests/ -q
        ;;
    "verbose")
        echo -e "${BLUE}Running tests (verbose mode)...${NC}"
        pytest tests/ -vv --tb=long
        ;;
    "watch")
        echo -e "${BLUE}Running tests in watch mode...${NC}"
        pytest-watch tests/
        ;;
    *)
        # Default: run with standard output
        pytest tests/ -v --tb=short
        ;;
esac

echo -e "\n${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Test suite completed successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"

# Print usage info
echo -e "\n${YELLOW}Usage:${NC}"
echo "  ./run_tests.sh              # Run tests (default)"
echo "  ./run_tests.sh coverage     # Run tests with coverage report"
echo "  ./run_tests.sh fast         # Run tests (minimal output)"
echo "  ./run_tests.sh verbose      # Run tests (very verbose)"
echo -e "  ./run_tests.sh watch        # Run tests in watch mode\n"
