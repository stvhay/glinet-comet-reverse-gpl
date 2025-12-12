# Testing

Comprehensive test suite for Python analysis scripts.

## Running Tests

**Requirements:** Run tests within the nix development environment:

```bash
nix develop
pytest
```

### Run specific tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_analyze_binwalk.py

# Run specific test class
pytest tests/test_analyze_binwalk.py::TestParseBinwalkOutput

# Run specific test
pytest tests/test_analyze_binwalk.py::TestParseBinwalkOutput::test_parse_single_component

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=scripts --cov-report=html
```

### Skip slow tests

```bash
pytest -m "not slow"
```

## Test Structure

```
tests/
├── __init__.py
├── README.md
├── test_analyze_binwalk.py    # Tests for analyze-binwalk.py
└── fixtures/                   # Test data (future)
```

## Test Organization

Each test file follows this structure:

1. **Unit tests** - Test individual functions and classes
   - `TestComponent` - Test Component dataclass
   - `TestBinwalkAnalysis` - Test BinwalkAnalysis dataclass
   - `TestParseBinwalkOutput` - Test parsing logic
   - `TestExtractOffsetFromLines` - Test helper functions

2. **Integration tests** - Test with realistic data
   - `TestIntegration` - End-to-end tests with sample binwalk output

## Coverage

Run with coverage reporting:

```bash
pytest --cov=scripts --cov-report=term
pytest --cov=scripts --cov-report=html  # Generates htmlcov/index.html
```

Target: **>80% coverage** for all Python modules

## Writing Tests

### Test file naming

- `test_*.py` - Test files
- `Test*` - Test classes
- `test_*` - Test functions

### Example test

```python
def test_parse_single_component():
    """Test parsing single component."""
    output = """
DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
586164        0x8F1B4         Device tree blob (DTB), version: 17
"""
    result = parse_binwalk_output(output)

    assert len(result) == 1
    assert result[0].offset == "0x8F1B4"
    assert result[0].type == "Device"
```

### Markers

Use markers for special test types:

```python
@pytest.mark.slow
def test_large_firmware():
    """Test with large firmware file."""
    ...

@pytest.mark.integration
def test_full_workflow():
    """Test complete analysis workflow."""
    ...
```

## Best Practices

1. **One assertion per test** (when possible) - Makes failures clear
2. **Descriptive names** - `test_parse_empty_output` vs `test1`
3. **Arrange-Act-Assert** - Clear test structure
4. **Use fixtures** - For shared test data
5. **Test edge cases** - Empty input, None values, errors
6. **Test happy path first** - Then edge cases

## Continuous Integration

Tests run automatically on:
- Every push to `main`
- Every pull request
- Can be run locally: `pytest`

See `.github/workflows/test.yml` for CI configuration.
