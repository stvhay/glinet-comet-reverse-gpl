# Python Style Guide

## Modern and Pythonic Code Standards

This project uses Python 3.11+ and follows modern Python best practices.

### Core Principles

1. **Explicit is better than implicit** - Use type hints, clear names
2. **Readability counts** - Code is read more than written
3. **Batteries included** - Use stdlib before external dependencies
4. **Type safety** - Leverage static typing for reliability

### Required Practices

#### Type Hints (PEP 484, 604, 585)

```python
from __future__ import annotations  # Always use for forward references

# Use modern union syntax (Python 3.10+)
def analyze(path: str | Path) -> dict[str, Any]:
    ...

# NOT: Optional[str], use str | None
firmware_offset: str | None = None

# Use generic types from collections module
components: list[Component] = []
metadata: dict[str, str] = {}
```

#### Dataclasses (PEP 557)

```python
from dataclasses import dataclass, field

# Use slots=True for memory efficiency (Python 3.10+)
# Use frozen=True for immutable data
@dataclass(frozen=True, slots=True)
class Component:
    """A firmware component."""
    offset: str
    type: str
    description: str

# Mutable dataclasses
@dataclass(slots=True)
class Analysis:
    """Analysis results."""
    components: list[Component] = field(default_factory=list)
```

#### Pathlib Over os.path

```python
from pathlib import Path

# YES
firmware = Path("firmware.img")
size = firmware.stat().st_size
output_dir = Path("/tmp") / "analysis"
output_dir.mkdir(parents=True, exist_ok=True)

# NO
import os
size = os.path.getsize("firmware.img")
os.makedirs("/tmp/analysis", exist_ok=True)
```

#### F-strings for Formatting

```python
# YES
info(f"Analyzing: {firmware.name}")
offset_hex = f"0x{offset:X}"

# NO
info("Analyzing: %s" % firmware.name)
info("Analyzing: {}".format(firmware.name))
```

#### Context Managers

```python
# Always use 'with' for file operations
with open(output_file, "w") as f:
    json.dump(data, f, indent=2)

# NOT:
f = open(output_file, "w")
json.dump(data, f)
f.close()
```

#### List/Dict Comprehensions

```python
# YES - concise and readable
components = [parse_line(line) for line in output.splitlines() if line.strip()]
metadata = {k: v for k, v in data.items() if v is not None}

# NO - verbose loops for simple transformations
components = []
for line in output.splitlines():
    if line.strip():
        components.append(parse_line(line))
```

#### Error Handling

```python
# Specific exceptions, clear messages
try:
    result = subprocess.run(["binwalk", firmware], check=True, capture_output=True)
except FileNotFoundError as e:
    error(f"binwalk not found: {e}")
    sys.exit(1)
except subprocess.CalledProcessError as e:
    error(f"binwalk failed: {e.stderr}")
    sys.exit(1)

# NOT: bare except
try:
    ...
except:
    pass
```

### Code Quality Tools

#### Ruff (Primary Linter and Formatter)

**Ruff is the primary tool** - it's 10-100x faster than alternatives and includes most pythonicness checks.

```bash
# Check code
ruff check scripts/

# Auto-fix issues
ruff check --fix scripts/

# Format code
ruff format scripts/
```

Configuration in `pyproject.toml`:
```toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort (import sorting)
    "B",    # flake8-bugbear (common bugs)
    "C4",   # flake8-comprehensions (better comprehensions)
    "UP",   # pyupgrade (modern syntax)
    "SIM",  # flake8-simplify (simplify code)
    "RET",  # flake8-return (better returns)
    "ARG",  # flake8-unused-arguments
    "PTH",  # flake8-use-pathlib (prefer pathlib)
    "PL",   # Pylint rules
    "RUF",  # Ruff-specific rules
]
```

**What Ruff checks for pythonicness:**

- **UP** (pyupgrade): Modern Python syntax
  - `dict[str, int]` instead of `Dict[str, int]`
  - `str | None` instead of `Optional[str]`
  - f-strings instead of `.format()` or `%`

- **C4** (comprehensions): Better list/dict comprehensions
  - List comprehensions instead of `map()` + `lambda`
  - Dict comprehensions instead of `dict(zip(...))`

- **SIM** (simplify): Simplify common patterns
  - `return bool(x)` → `return bool(x)`
  - Simplify `if/else` chains
  - Remove unnecessary `elif` after `return`

- **B** (bugbear): Catch common mistakes
  - Mutable default arguments
  - Unnecessary generator (rewritten as list/dict comprehension)
  - Loop control variable reuse

- **PTH** (use-pathlib): Prefer pathlib over os.path
  - `Path(...).exists()` instead of `os.path.exists(...)`
  - `Path(...).stat()` instead of `os.stat(...)`

#### Additional Pythonicness Tools

##### Pylint (Comprehensive Checker)

More opinionated than Ruff, catches code smells:

```bash
pylint scripts/analyze-binwalk.py
```

Checks for:
- Code duplication
- Too many arguments/locals/branches
- Inconsistent return statements
- Naming conventions

**Note**: Pylint is slower and more opinionated. Use Ruff first.

##### Vulture (Dead Code Finder)

Finds unused code:

```bash
vulture scripts/
```

Finds:
- Unused functions, classes, variables
- Unreachable code
- Unused imports (also caught by Ruff)

##### Bandit (Security Linter)

Security-focused checks:

```bash
bandit -r scripts/
```

Finds:
- Use of `eval()` or `exec()`
- SQL injection risks
- Shell injection risks (subprocess with shell=True)
- Hardcoded passwords

**Recommendation**: Add to CI pipeline, but Ruff's security rules (S) cover most cases.

#### Recommended Configuration

For this project, use **Ruff only** for development, with these additional checks in CI:

```bash
# Development (fast, fix automatically)
ruff check --fix scripts/
ruff format scripts/

# CI (comprehensive)
ruff check scripts/           # Fast, catches 90% of issues
mypy scripts/                 # Type checking
bandit -r scripts/            # Security
pytest tests/                 # Unit tests
```

#### Mypy (Type Checking)

```bash
# Check types
mypy scripts/
```

Configuration in `mypy.ini`:
```ini
[mypy]
python_version = 3.11
strict = True
warn_return_any = True
warn_unused_configs = True
```

#### Pytest (Testing)

```python
# tests/test_analyze_binwalk.py
import pytest
from pathlib import Path
from scripts.analyze_binwalk import parse_binwalk_output, Component

def test_parse_binwalk_output():
    output = """
    586164    0x8F1B4    Device tree blob (DTB)
    590260    0x901B4    gzip compressed data
    """
    components = parse_binwalk_output(output)

    assert len(components) == 2
    assert components[0].offset == "0x8F1B4"
    assert components[0].type == "Device"
```

### Documentation

#### Docstrings (PEP 257, Google Style)

```python
def analyze_firmware(firmware_path: str) -> BinwalkAnalysis:
    """Analyze firmware with binwalk and return structured results.

    Args:
        firmware_path: Path to firmware image file

    Returns:
        BinwalkAnalysis object with all extracted data

    Raises:
        FileNotFoundError: If firmware file doesn't exist
        subprocess.CalledProcessError: If binwalk fails
    """
    ...
```

### Anti-Patterns to Avoid

#### ❌ Mutable Default Arguments

```python
# NO
def add_component(components=[]):  # BAD!
    components.append(...)
    return components

# YES
def add_component(components: list[Component] | None = None) -> list[Component]:
    if components is None:
        components = []
    components.append(...)
    return components

# OR (better with dataclasses)
@dataclass
class Analysis:
    components: list[Component] = field(default_factory=list)
```

#### ❌ String Formatting Vulnerabilities

```python
# NO - SQL injection risk
query = f"SELECT * FROM users WHERE name = '{name}'"

# YES - Use parameterized queries
cursor.execute("SELECT * FROM users WHERE name = ?", (name,))

# NO - Shell injection risk
os.system(f"binwalk {firmware}")

# YES - Use subprocess with list args
subprocess.run(["binwalk", firmware], check=True)
```

#### ❌ Ignoring Exceptions

```python
# NO
try:
    critical_operation()
except:
    pass  # Silent failure!

# YES - Log or handle appropriately
try:
    critical_operation()
except SpecificError as e:
    error(f"Operation failed: {e}")
    sys.exit(1)
```

### Performance Considerations

- Use `__slots__` in dataclasses to reduce memory
- Use generators for large datasets: `(x for x in ...)` vs `[x for x in ...]`
- Profile before optimizing: `python -m cProfile script.py`

### References

- [PEP 8](https://peps.python.org/pep-0008/) - Style Guide for Python Code
- [PEP 257](https://peps.python.org/pep-0257/) - Docstring Conventions
- [PEP 484](https://peps.python.org/pep-0484/) - Type Hints
- [PEP 585](https://peps.python.org/pep-0585/) - Type Hinting Generics In Standard Collections
- [PEP 604](https://peps.python.org/pep-0604/) - Allow writing union types as X | Y
- [Python 3.11 What's New](https://docs.python.org/3/whatsnew/3.11.html)
