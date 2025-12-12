# Codebase Refactoring Plan 2025

**Status:** Planning
**Created:** 2025-12-12
**Target Completion:** Q1 2025
**Tracking Issue:** #TBD

## Executive Summary

This refactoring plan addresses code quality, maintainability, and test coverage across the entire Python analysis framework (8 scripts, 4 libraries, 11 test files, 556 tests, ~15,000 LOC).

**Goals:**
1. Reduce code duplication by ~1,000 lines
2. Improve test coverage with integration tests
3. Standardize error handling and logging
4. Create reusable abstractions for common patterns
5. Maintain 100% test pass rate throughout

**Current State:** GOOD
- Well-structured dataclasses with consistent patterns
- Good test coverage (556 tests, all passing)
- Consistent use of metadata tracking
- Main issues: boilerplate duplication, inconsistent utilities

---

## Phase 1: Core Infrastructure (Foundation)

**Effort:** 5-7 commits | **Impact:** -800 lines, improved maintainability

### 1.1 Extract BaseScript Class
**File:** `scripts/lib/base_script.py` (NEW)

**Problem:** All 8 analysis scripts duplicate 50-100 lines of main() boilerplate:
- Argument parsing (firmware path, --format flag)
- Path setup (script_dir, project_root, output_dir, work_dir)
- Firmware acquisition (download or use provided path)
- Output formatting (TOML/JSON selection)
- Success logging

**Solution:**
```python
class AnalysisScript(ABC):
    """Base class for firmware analysis scripts."""

    def __init__(
        self,
        description: str,
        analysis_class: type[AnalysisBase],
        simple_fields: list[str],
        complex_fields: list[str],
    ):
        self.description = description
        self.analysis_class = analysis_class
        self.simple_fields = simple_fields
        self.complex_fields = complex_fields

    @abstractmethod
    def analyze(self, firmware: Path, work_dir: Path) -> AnalysisBase:
        """Implement script-specific analysis logic."""
        pass

    def run(self) -> None:
        """Standard entry point for all analysis scripts."""
        args = self._parse_args()
        firmware = get_firmware_path(args.firmware, self._work_dir)
        analysis = self.analyze(firmware, self._work_dir)
        self._output_results(analysis, args.format)
        self._log_success(analysis)
```

**Benefits:**
- Each script reduces from ~70 lines to ~10 lines in main()
- Consistent argument handling across all scripts
- Easier to add new global flags (e.g., --verbose, --cache-dir)

**Test Coverage:**
- Unit tests for AnalysisScript base class
- Integration tests verify each script works with base class

**Acceptance Criteria:**
- [ ] All 8 scripts refactored to use BaseScript
- [ ] All 556 existing tests still pass
- [ ] New tests for BaseScript (10+ tests)
- [ ] Documentation updated

---

### 1.2 Create Binary/Library Finder Module
**File:** `scripts/lib/finders.py` (NEW)

**Problem:** 5 different "find files by pattern" implementations:
- `find_libraries()` (analyze_proprietary_blobs.py)
- `find_web_servers()` (analyze_network_services.py)
- `find_network_services()` (analyze_network_services.py)
- `find_kernel_modules()` (analyze_rootfs.py)
- `find_firmware_blobs()` (analyze_proprietary_blobs.py)

All follow pattern: `rootfs.rglob(pattern) + filter + create objects`

**Solution:**
```python
def find_files(
    rootfs: Path,
    patterns: list[str],
    exclude_patterns: list[str] | None = None,
    file_type: Literal["file", "symlink", "any"] = "any",
) -> list[Path]:
    """Generic file finder with pattern matching."""

def find_and_create(
    rootfs: Path,
    patterns: list[str],
    creator_func: Callable[[Path], T],
    exclude_patterns: list[str] | None = None,
) -> list[T]:
    """Find files and create objects from them."""

def find_elf_binaries(rootfs: Path, names: list[str]) -> list[Path]:
    """Find ELF binaries by name."""

def find_libraries(rootfs: Path, patterns: list[str]) -> list[Path]:
    """Find shared libraries (.so files)."""
```

**Benefits:**
- Eliminates ~150 lines of duplicate code
- Consistent file finding behavior
- Easy to add caching layer later
- Better testability (mock once, not 5 times)

**Test Coverage:**
- Unit tests with temp directories
- Edge cases: symlinks, missing directories, large file trees
- Performance tests (1000+ files)

**Acceptance Criteria:**
- [ ] 5 scripts refactored to use lib.finders
- [ ] All existing tests pass
- [ ] New finders tests (15+ tests)
- [ ] Performance: <100ms for 1000 files

---

### 1.3 Create String Extraction Module
**File:** `scripts/lib/extraction.py` (NEW)

**Problem:** 3 scripts duplicate gzip extraction and string filtering:
- `analyze_uboot.py`: extract_gzip_at_offset() + extract_strings_from_data()
- `analyze_secure_boot.py`: similar implementation
- `analyze_proprietary_blobs.py`: strings extraction logic

**Solution:**
```python
def extract_gzip_at_offset(
    firmware: Path,
    offset: int,
    size: int | None = None,
) -> bytes:
    """Extract and decompress gzip data at firmware offset."""

def extract_strings(
    data: bytes,
    min_length: int = 4,
    encoding: str = "utf-8",
) -> list[str]:
    """Extract printable strings from binary data."""

def filter_strings(
    strings: list[str],
    keywords: list[str] | None = None,
    regex: str | None = None,
) -> list[str]:
    """Filter strings by keywords or regex."""

def extract_firmware_component(
    firmware: Path,
    offset: str | int,
    keywords: list[str],
) -> list[str]:
    """High-level: extract gzipped component and filter strings."""
```

**Benefits:**
- Consolidates 3 duplicate implementations
- Better error handling (gzip corruption, offset out of bounds)
- Testable with small binary fixtures

**Test Coverage:**
- Unit tests with crafted binary data
- Edge cases: invalid gzip, zero-length data, bad offsets
- Integration tests with real firmware offsets

**Acceptance Criteria:**
- [ ] 3 scripts refactored to use lib.extraction
- [ ] All existing tests pass
- [ ] New extraction tests (20+ tests)
- [ ] Handles corrupted gzip gracefully

---

## Phase 2: Specialized Utilities

**Effort:** 3-4 commits | **Impact:** -180 lines, better modularity

### 2.1 Create Device Tree Parsing Module
**File:** `scripts/lib/devicetree.py` (NEW)

**Problem:** DTS parsing duplicated in 3 scripts:
- `analyze_device_trees.py`: _extract_fit_description(), _extract_serial_config(), _extract_hardware_components()
- `analyze_boot_process.py`: similar FIT extraction
- `analyze_secure_boot.py`: DTB node extraction

**Solution:**
```python
class DeviceTreeParser:
    """Parser for device tree source (DTS) content."""

    def __init__(self, dts_content: str):
        self.content = dts_content

    def extract_model(self) -> str | None:
        """Extract model string."""

    def extract_compatible(self) -> str | None:
        """Extract compatible string."""

    def extract_fit_description(self) -> str | None:
        """Extract FIT image description."""

    def extract_serial_config(self) -> str | None:
        """Extract serial/UART configuration."""

    def extract_hardware_components(self) -> list[HardwareComponent]:
        """Extract GPIO, USB, SPI, I2C, UART components."""

    def is_fit_image(self) -> bool:
        """Check if DTS is a FIT image."""
```

**Benefits:**
- Consolidates ~100 lines of regex parsing
- Single source of truth for DTS patterns
- Easier to add new extraction patterns

**Test Coverage:**
- Unit tests with various DTS snippets
- Edge cases: malformed DTS, missing properties
- Real-world DTS files from firmware

**Acceptance Criteria:**
- [ ] 3 scripts refactored to use DeviceTreeParser
- [ ] All existing tests pass
- [ ] New devicetree tests (15+ tests)
- [ ] Handles malformed DTS gracefully

---

### 2.2 Create Offset Management Module
**File:** `scripts/lib/offsets.py` (NEW)

**Problem:** Offset loading duplicated in 3 scripts:
- `analyze_uboot.py`: load_binwalk_offsets()
- `analyze_secure_boot.py`: load_offsets()
- `analyze_boot_process.py`: inline offset reading
- `analyze_binwalk.py`: write_legacy_offsets_file() (output side)

**Solution:**
```python
class OffsetManager:
    """Manage firmware offsets from binwalk analysis."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.offsets: dict[str, int | str] = {}

    def load_from_shell_script(self, script_path: Path) -> None:
        """Load offsets from binwalk-offsets.sh."""

    def load_from_toml(self, toml_path: Path) -> None:
        """Load offsets from TOML analysis results."""

    def get(self, key: str) -> int | str | None:
        """Get offset by key (e.g., 'UBOOT_OFFSET')."""

    def get_hex(self, key: str) -> str | None:
        """Get hex offset (e.g., '0x8F1B4')."""

    def get_dec(self, key: str) -> int | None:
        """Get decimal offset."""

    def write_shell_script(self, script_path: Path) -> None:
        """Write offsets to shell script."""
```

**Benefits:**
- Eliminates ~80 lines of duplicate parsing
- Consistent offset access across scripts
- Supports both legacy .sh and new TOML formats

**Test Coverage:**
- Unit tests for shell script parsing
- Unit tests for TOML parsing
- Edge cases: missing files, malformed data

**Acceptance Criteria:**
- [ ] 4 scripts refactored to use OffsetManager
- [ ] All existing tests pass
- [ ] New offsets tests (12+ tests)
- [ ] Backward compatible with .sh files

---

## Phase 3: Code Quality

**Effort:** 4-5 commits | **Impact:** Better robustness, consistency

### 3.1 Standardize Error Handling
**Files:** All 8 analysis scripts

**Problem:** Inconsistent error handling:
- Some scripts: 0 try/except blocks
- Other scripts: 4 try/except blocks
- No custom exception types
- Silent failures in helper functions

**Solution:**
```python
# scripts/lib/exceptions.py (NEW)
class FirmwareAnalysisError(Exception):
    """Base exception for firmware analysis."""

class FirmwareNotFoundError(FirmwareAnalysisError):
    """Firmware file not found."""

class ExtractionError(FirmwareAnalysisError):
    """Firmware extraction failed."""

class ParsingError(FirmwareAnalysisError):
    """Failed to parse firmware component."""

# Standard error handling pattern:
try:
    result = risky_operation()
except SpecificError as e:
    error(f"Operation failed: {e}")
    sys.exit(1)
```

**Pattern to apply:**
1. All file I/O wrapped in try/except
2. All subprocess calls check return codes
3. All parsing operations validate input
4. Custom exceptions for domain errors

**Benefits:**
- Consistent error messages
- Better debugging information
- Graceful degradation where possible

**Test Coverage:**
- Test each error path
- Verify error messages
- Check sys.exit() codes

**Acceptance Criteria:**
- [ ] Custom exception types defined
- [ ] All file operations wrapped
- [ ] All subprocess calls checked
- [ ] All tests still pass
- [ ] New error tests (30+ tests)

---

### 3.2 Add Missing Type Hints and Docstrings
**Files:** All scripts and libraries

**Problem:**
- 5-10 helper functions lack docstrings
- Some complex return types not fully typed
- Test fixtures lack type hints

**Solution:**
1. Add docstrings to all functions (Google style)
2. Add type hints to all test fixtures
3. Run mypy in strict mode
4. Add py.typed marker

**Example:**
```python
def extract_gzip_at_offset(
    firmware: Path,
    offset: int,
    size: int | None = None,
) -> bytes:
    """Extract and decompress gzip data at firmware offset.

    Args:
        firmware: Path to firmware image file
        offset: Byte offset where gzip data starts
        size: Optional size limit for extraction

    Returns:
        Decompressed binary data

    Raises:
        ExtractionError: If offset is invalid or data is not valid gzip
    """
```

**Benefits:**
- Better IDE autocomplete
- Catch type errors at development time
- Self-documenting code

**Acceptance Criteria:**
- [ ] All functions have docstrings
- [ ] All functions have complete type hints
- [ ] mypy --strict passes
- [ ] py.typed marker added

---

### 3.3 Reduce Code Complexity
**Files:** 5 functions flagged by ruff

**Problem:** 5 functions with PLR0912/PLR0915 warnings:
- `generate_markdown()` (analyze_boot_process.py)
- `analyze_firmware()` (analyze_network_services.py)
- `analyze_secure_boot()` (analyze_secure_boot.py)
- `analyze_uboot()` (analyze_uboot.py)
- `write_legacy_markdown()` (analyze_uboot.py)

**Solution:**
1. Extract nested loops into helper functions
2. Use early returns to reduce nesting
3. Split 60+ line functions into 2-3 smaller functions
4. Use match/case for multi-branch logic (Python 3.10+)

**Example refactoring:**
```python
# Before: 60-line function with 3 nested loops
def analyze_firmware(firmware: Path) -> Analysis:
    # ... 60 lines of nested logic

# After: 4 focused functions
def analyze_firmware(firmware: Path) -> Analysis:
    components = _extract_components(firmware)
    versions = _determine_versions(components)
    metadata = _collect_metadata(firmware)
    return Analysis(components, versions, metadata)
```

**Benefits:**
- Better testability
- Easier to understand
- Passes ruff complexity checks

**Acceptance Criteria:**
- [ ] All 5 functions refactored
- [ ] No PLR0912/PLR0915 warnings
- [ ] All existing tests pass
- [ ] New tests for extracted functions

---

## Phase 4: Test Improvements

**Effort:** 5-6 commits | **Impact:** Better coverage, fewer bugs

### 4.1 Add Integration Tests
**File:** `tests/integration/` (NEW)

**Problem:** All 556 tests use mocks - no end-to-end validation with real firmware.

**Solution:**
```python
# tests/integration/test_full_pipeline.py
class TestFullPipeline:
    """Integration tests with real firmware analysis."""

    def test_full_analysis_pipeline(self, firmware_fixture):
        """Test complete analysis pipeline."""
        # Download firmware (or use cached version)
        firmware = get_firmware_path(None, work_dir)

        # Run binwalk analysis
        binwalk_result = analyze_firmware(str(firmware))
        assert binwalk_result.squashfs_count > 0

        # Extract firmware
        extract_dir = extract_firmware(firmware, work_dir)
        assert extract_dir.exists()

        # Analyze device trees
        dt_result = analyze_device_trees(str(firmware))
        assert dt_result.dtb_count > 0

        # Verify output consistency
        assert binwalk_result.dtb_count == dt_result.dtb_count
```

**Test scenarios:**
1. Full pipeline: download → extract → analyze → output
2. Cached firmware handling
3. Multi-script consistency checks
4. Output format validation (TOML/JSON)

**Benefits:**
- Catch integration bugs
- Validate against real firmware
- Test caching behavior

**Acceptance Criteria:**
- [ ] 10+ integration tests
- [ ] Tests run in CI (with caching)
- [ ] All tests pass
- [ ] <5 minute execution time

---

### 4.2 Create Shared Test Fixtures
**File:** `tests/conftest.py` (UPDATE)

**Problem:** Test data embedded in test files (200+ lines per class).

**Solution:**
```python
# tests/conftest.py
@pytest.fixture
def mock_firmware(tmp_path: Path) -> Path:
    """Create minimal mock firmware file."""
    firmware = tmp_path / "test.img"
    firmware.write_bytes(b"mock firmware data")
    return firmware

@pytest.fixture
def mock_rootfs(tmp_path: Path) -> Path:
    """Create mock SquashFS rootfs structure."""
    rootfs = tmp_path / "squashfs-root"
    rootfs.mkdir()
    (rootfs / "bin").mkdir()
    (rootfs / "lib").mkdir()
    return rootfs

@pytest.fixture
def mock_dts_content() -> str:
    """Sample DTS content for testing."""
    return '''
    /dts-v1/;
    / {
        model = "Test Device";
        compatible = "test,device";
    };
    '''
```

**Benefits:**
- Reusable test data
- Less test code duplication
- Easier to add new test cases

**Acceptance Criteria:**
- [ ] 10+ shared fixtures
- [ ] All tests use fixtures
- [ ] Reduce test LOC by 20%

---

### 4.3 Improve Edge Case Coverage
**Files:** Tests for analyze_device_trees, analyze_binwalk, analyze_uboot

**Problem:** Light test coverage on 3 scripts:
- analyze_binwalk.py: 15.6% line-to-test ratio
- analyze_uboot.py: 12.4% ratio
- analyze_device_trees.py: 15% ratio

**Solution:** Add edge case tests:
```python
# Edge cases to test:
- Empty firmware files
- Corrupted gzip data
- Missing SquashFS partition
- Invalid hex offsets
- Malformed DTS content
- Binwalk extraction failures
- Out-of-bounds offset access
- Zero-length strings
- Unicode handling
```

**Test additions:**
- analyze_binwalk: +15 tests (empty firmware, no squashfs, invalid offsets)
- analyze_uboot: +20 tests (bad gzip, missing strings, offset errors)
- analyze_device_trees: +15 tests (malformed DTS, missing nodes)

**Benefits:**
- Better error handling validation
- Catch edge cases before production
- More robust analysis

**Acceptance Criteria:**
- [ ] +50 edge case tests added
- [ ] All 3 scripts >10% ratio
- [ ] All tests pass

---

## Phase 5: Documentation and Cleanup

**Effort:** 2-3 commits | **Impact:** Better developer experience

### 5.1 Update Documentation
**Files:** README.md, docs/, docstrings

**Tasks:**
1. Update README with new lib/ module structure
2. Add architecture diagram showing module dependencies
3. Create CONTRIBUTING.md with refactoring patterns
4. Update inline comments for complex algorithms
5. Generate API documentation (pdoc or sphinx)

**Acceptance Criteria:**
- [ ] README reflects new structure
- [ ] Architecture diagram created
- [ ] CONTRIBUTING.md written
- [ ] API docs generated

---

### 5.2 Cleanup and Polish
**Files:** All scripts

**Tasks:**
1. Remove unused imports (ruff --fix)
2. Standardize function naming (find_* vs get_*)
3. Alphabetize imports consistently
4. Remove commented-out code
5. Update copyright headers
6. Run black formatter on all files

**Acceptance Criteria:**
- [ ] No ruff warnings
- [ ] No mypy errors
- [ ] Black formatting applied
- [ ] All tests pass

---

## Metrics and Success Criteria

### Code Metrics
| Metric | Before | Target | Measurement |
|--------|--------|--------|-------------|
| Total LOC | ~15,000 | ~14,000 | -1,000 lines (-6.7%) |
| Duplicate code | ~1,200 | <200 | pylint --duplicate-code |
| Test count | 556 | 650+ | pytest --collect-only |
| Test pass rate | 100% | 100% | Maintained throughout |
| Ruff warnings | 3 | 0 | ruff check |
| Mypy errors | Unknown | 0 | mypy --strict |
| Function complexity | 5 flagged | 0 flagged | ruff PLR0912/PLR0915 |

### Developer Experience
- [ ] Time to add new analysis script: <30 minutes
- [ ] New contributor onboarding: <2 hours
- [ ] Test execution time: <2 minutes (unit), <5 minutes (integration)

### Quality Gates (CI)
- [ ] All tests pass
- [ ] Ruff check passes
- [ ] Mypy strict passes
- [ ] Coverage >80%

---

## Timeline Estimate

| Phase | Effort | Duration | Commits |
|-------|--------|----------|---------|
| Phase 1: Core Infrastructure | High | 2-3 weeks | 5-7 |
| Phase 2: Specialized Utilities | Medium | 1-2 weeks | 3-4 |
| Phase 3: Code Quality | Medium | 1-2 weeks | 4-5 |
| Phase 4: Test Improvements | High | 2-3 weeks | 5-6 |
| Phase 5: Documentation | Low | 1 week | 2-3 |
| **Total** | | **7-11 weeks** | **19-25 commits** |

**Note:** Timeline assumes part-time work (10-20 hours/week). Full-time work could complete in 3-5 weeks.

---

## Risk Mitigation

### Risk: Breaking existing functionality
**Mitigation:**
- Run full test suite after each commit
- Add integration tests early (Phase 4.1)
- Keep existing code until refactored version proven

### Risk: Scope creep
**Mitigation:**
- Stick to defined phases
- Track progress in GitHub issues
- Review PR scope before merging

### Risk: Test maintenance burden
**Mitigation:**
- Use shared fixtures (Phase 4.2)
- Avoid over-testing internal implementation
- Focus on public API contracts

---

## Review Points

**After Phase 1:**
- Review BaseScript API design
- Validate finders module with all scripts
- Assess developer experience improvements

**After Phase 3:**
- Review error handling consistency
- Check mypy strict mode feasibility
- Validate complexity reduction

**After Phase 5:**
- Final metrics review
- Developer documentation review
- Decide on next refactoring priorities

---

## Future Considerations (Out of Scope)

These items are noted but not part of this refactoring:

1. **Parallel analysis execution** - Run multiple scripts in parallel
2. **Caching layer** - Cache expensive operations (binwalk, extraction)
3. **GUI/web interface** - Web UI for firmware analysis
4. **Plugin system** - Allow custom analysis modules
5. **Performance optimization** - Profile and optimize slow operations
6. **Firmware comparison** - Compare multiple firmware versions
7. **Automated GPL source identification** - ML-based license detection

---

## References

- Issue tracking: GitHub Projects board (TBD)
- Code review guidelines: CONTRIBUTING.md (TBD)
- Testing strategy: docs/testing-strategy.md (TBD)
- Architecture decisions: docs/architecture/ (TBD)

---

**Document Status:** DRAFT → Ready for review
**Last Updated:** 2025-12-12
**Next Review:** After Phase 1 completion
