# Coverage Improvement Plan

**Created**: 2025-12-12
**Current Overall Coverage**: 62%
**Target Overall Coverage**: 80%

## Executive Summary

This document outlines the strategy for improving test coverage across Python analysis scripts in the glinet-comet-reversing project. The plan prioritizes:

1. **Unblocking commits** - Write tests for 4 new scripts (0% coverage)
2. **Addressing gaps** - Improve low-coverage scripts (<60%)
3. **Integration testing** - Add end-to-end tests for main() functions

## Current Coverage State

As of commit `045da58` (2025-12-12):

| Script | Coverage | Lines | Status |
|--------|----------|-------|--------|
| analysis.py | 96% | 26/27 | ✅ Excellent |
| analyze_rootfs.py | 74% | 206/279 | ✅ Good |
| render_template.py | 73% | 88/121 | ✅ Good |
| analyze_device_trees.py | 66% | 145/220 | ⚠️ Moderate |
| analyze_binwalk.py | 49% | 64/131 | ❌ Low |
| analyze_uboot.py | 39% | 76/196 | ❌ Low |
| **TOTAL** | **62%** | **605/974** | ⚠️ **Moderate** |

### Scripts Without Tests (Excluded from Coverage)

These scripts are in `pyproject.toml` omit list and **cannot be committed** until tested:

- `scripts/analyze_boot_process.py` - 0% coverage
- `scripts/analyze_network_services.py` - 0% coverage
- `scripts/analyze_proprietary_blobs.py` - 0% coverage
- `scripts/analyze_secure_boot.py` - 0% coverage

## Prioritized Roadmap

### Priority 1: Unblock New Script Commits (CRITICAL)

**Goal**: Write comprehensive tests for 4 new Python scripts
**Target Coverage**: >60% per script, with integration tests for main()
**Estimated Tests**: ~150-200 total (35-50 per script)

#### 1.1 analyze_boot_process.py

**Test Requirements**:
- Unit tests for dataclasses (InitScript, SystemdService, BootProcessAnalysis)
- Tests for init script parsing logic
- Tests for systemd service file parsing
- Tests for boot configuration detection
- TOML/JSON output format validation
- Integration test: main() with mocked filesystem
- Mock file I/O with unittest.mock

**Key Complexity**:
- `generate_markdown()` function has complexity warnings (noqa: PLR0912, PLR0915)
- Multiple file format parsers (init scripts, systemd units, boot configs)

#### 1.2 analyze_network_services.py

**Test Requirements**:
- Unit tests for dataclasses (NetworkService, UserAccount, SensitiveFile, NetworkAnalysis)
- Tests for service detection logic
- Tests for user account parsing
- Tests for sensitive file identification
- TOML/JSON output format validation
- Integration test: main() with mocked filesystem

#### 1.3 analyze_proprietary_blobs.py

**Test Requirements**:
- Unit tests for dataclasses (ProprietaryBlob, ProprietaryBlobAnalysis)
- Tests for Rockchip MPP/RGA/ISP/NPU detection
- Tests for WiFi/BT blob identification
- Tests for kernel module classification
- TOML/JSON output format validation
- Integration test: main() with mocked filesystem

#### 1.4 analyze_secure_boot.py

**Test Requirements**:
- Unit tests for dataclasses (FITSignature, SecureBootAnalysis)
- Tests for FIT image signature parsing
- Tests for U-Boot verification detection
- Tests for OP-TEE analysis
- Tests for OTP/crypto configuration
- TOML/JSON output format validation
- Integration test: main() with mocked filesystem

**Success Criteria**:
- All 4 scripts have >60% coverage
- All scripts have at least 1 integration test for main()
- All new tests pass
- Scripts can be committed and removed from pyproject.toml omit list

### Priority 2: Improve Low Coverage Scripts

#### 2.1 analyze_binwalk.py (49% → 80%)

**Current State**:
- 64/131 lines covered
- 67 lines need coverage

**Coverage Gaps**:
- main() function integration test missing
- Error handling paths untested
- Binwalk output parsing edge cases

**Test Additions Needed**:
- Integration test for main() with mock subprocess
- Tests for malformed binwalk output
- Tests for missing firmware file
- Tests for empty binwalk results
- Tests for offset parsing edge cases

**Estimated New Tests**: 10-15

#### 2.2 analyze_uboot.py (39% → 80%)

**Current State**:
- 76/196 lines covered
- 120 lines need coverage

**Coverage Gaps**:
- main() function integration test missing
- U-Boot string extraction untested
- Command-line argument handling incomplete

**Test Additions Needed**:
- Integration test for main() with mock filesystem
- Tests for extract_uboot_strings() with real binary data
- Tests for load_binwalk_offsets() with various input formats
- Tests for --format json vs TOML output
- Tests for missing files and error conditions

**Estimated New Tests**: 15-20

**Success Criteria**:
- analyze_binwalk.py reaches 80% coverage
- analyze_uboot.py reaches 80% coverage
- All integration tests for main() functions pass

### Priority 3: Enhance Integration Testing

**Goal**: Add end-to-end tests that exercise full script workflows

**Test Scenarios**:
1. **Full firmware analysis pipeline**:
   - Download firmware → binwalk → extract → analyze
   - Verify TOML output can be consumed by templates
   - Verify source metadata is present in all outputs

2. **Template rendering pipeline**:
   - Run analysis script → cache results → render template
   - Verify footnotes are generated from source metadata
   - Verify all `| src` filters work correctly

3. **Error recovery**:
   - Missing firmware files
   - Corrupted firmware images
   - Missing dependencies (binwalk, dtc, etc.)

**Estimated New Tests**: 10-15 integration tests

**Success Criteria**:
- All main() functions have integration tests
- Template rendering pipeline has end-to-end test
- Error handling paths are tested

## Testing Best Practices

### Patterns to Follow

1. **Mock File I/O**: Use `unittest.mock.patch` for file operations
   ```python
   @patch("pathlib.Path.exists", return_value=True)
   @patch("pathlib.Path.read_text", return_value="mock data")
   def test_function(mock_read, mock_exists):
       # test logic
   ```

2. **Frozen Dataclasses**: Test immutability with `slots=True, frozen=True`
   ```python
   def test_dataclass_frozen():
       obj = MyDataClass(field="value")
       with pytest.raises(FrozenInstanceError):
           obj.field = "new value"
   ```

3. **TOML/JSON Output**: Verify both formats and source metadata
   ```python
   def test_output_format():
       result = analyze()
       assert "field" in result
       assert "field_source" in result
       assert "field_method" in result
   ```

4. **Integration Tests**: Mock subprocess and filesystem
   ```python
   @patch("subprocess.run")
   @patch("pathlib.Path.exists")
   def test_main(mock_exists, mock_run):
       main()
       assert mock_run.called
   ```

### Coverage Exclusions

Keep these patterns in `tool.coverage.report.exclude_lines`:
- `pragma: no cover`
- `def __repr__`
- `if __name__ == .__main__.:`
- `raise AssertionError`
- `raise NotImplementedError`

## Timeline and Dependencies

### Phase 1: Unblock Commits (Priority 1)
- **Duration**: Complete all 4 test suites
- **Blocking**: Cannot commit new scripts until complete
- **Deliverable**: 4 test files, >60% coverage each

### Phase 2: Improve Existing Scripts (Priority 2)
- **Duration**: Improve 2 scripts to 80% coverage
- **Dependencies**: None (can start immediately)
- **Deliverable**: Enhanced test_analyze_binwalk.py and test_analyze_uboot.py

### Phase 3: Integration Testing (Priority 3)
- **Duration**: Add 10-15 integration tests
- **Dependencies**: Phase 1 complete (need all scripts testable)
- **Deliverable**: End-to-end test suite

## Success Metrics

**Overall Target**: 80% code coverage across all Python scripts

**Per-Script Minimums**:
- Critical scripts (analysis.py, render_template.py): >90%
- Analysis scripts: >60%
- All scripts: Integration test for main()

**Quality Gates**:
- All tests pass
- No untested code committed
- All source metadata fields tested
- Template rendering pipeline tested end-to-end

## Maintenance

This plan should be updated when:
- New analysis scripts are added
- Coverage thresholds change
- New testing patterns emerge
- Project testing standards evolve

**Review Schedule**: After each phase completion

---

**Next Steps**: Begin Priority 1 - Write tests for analyze_boot_process.py
