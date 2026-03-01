# Design: Traceability Enforcement for Clean Room Analysis

**Date:** 2026-03-01
**Epic:** Replaces #77 (Embedded Workflow System)
**Priority:** High
**Type:** Infrastructure

## Problem

This project reverse-engineers GPL-licensed components in proprietary firmware using strict black-box methodology. Every finding must be provably derived from automated, reproducible analysis -- not from prior knowledge or training data. If challenged, we must demonstrate an unbroken chain from firmware to scripts to results to documentation.

The existing analysis pipeline (`scripts/ → results/*.toml → Jinja templates → docs/`) already supports traceability. But nothing *enforces* it. Findings can bypass the pipeline, citations can break, and CI doesn't verify the chain holds.

Epic #77 attempted to solve a related problem (agent QA integration) with checkpoint files, scoring rubrics, and measurement frameworks. That approach produced ~2,000 lines of process documentation without addressing the actual requirement: proving every finding derives from reproducible analysis.

## Solution

One rule: **every factual claim in the repository must trace to a script output, and CI must verify this.**

Three enforcement layers:

1. **Prevention** -- metadata infrastructure ensures scripts produce traceable output
2. **Citation** -- documentation (generated or hand-written) cites specific results
3. **Verification** -- CI checks that all citations resolve and results are current

## Traceability Chain

```
scripts/analyze_*.py
    → results/*.toml (source + method metadata per field)
        → docs/ (Jinja with | src, or hand-written with <!-- cite: --> )
            → CI verifies all citations resolve to current results
```

## Reproducibility Classes

Not all findings are software-reproducible. Some require physical hardware (serial console, JTAG, button combinations). Both are valid clean room findings with different reproducibility models.

### Software-Reproducible

- **Input:** Firmware image (downloadable, SHA256 hashable)
- **Method:** Script execution
- **Verification:** Re-run script, compare output
- **CI:** Automated -- regenerate and diff

```toml
# Reproducibility: software
# Source: gzip_extraction
# Method: gunzip data at offset 0x901B4 | strings | grep "U-Boot"
version = "U-Boot 2017.09-gfd8bfa2acd-dirty"
```

Required metadata: `Reproducibility`, `Source`, `Method`

### Hardware-Derived

- **Input:** Physical device + documented test setup
- **Method:** Documented procedure with equipment list
- **Verification:** Re-run procedure on same hardware, compare output
- **CI:** Cannot re-derive; verifies citation exists, metadata is complete, TOML hasn't been modified since attestation (git history)

```toml
# Reproducibility: hardware
# Source: serial_console_capture
# Method: Connect USB-UART at 1500000 baud to debug header pins 4(TX)/5(RX)
# Equipment: USB-UART adapter (3.3V), terminal emulator
# Procedure: Power on device, capture first 30 seconds of output
# Performed: 2025-12-15T14:30:00Z
# Operator: stvhay
maskrom_entry = "Hold reset button during power-on for 3+ seconds"
```

Required metadata: `Reproducibility`, `Source`, `Method`, `Equipment`, `Procedure`, `Performed`, `Operator`

The standard for hardware-derived findings: enough detail that someone with access to the same hardware could reproduce the result.

## Citation Format

### Jinja Templates (no change)

The `| src` filter already generates footnotes with script links and method descriptions:

```jinja
{{ dt.model | src }}
```

Renders as `RV1126 [^1]` with footnote linking to the script and method.

### Hand-Written Docs (new)

HTML comments that CI can parse:

```markdown
The firmware runs U-Boot 2017.09 <!-- cite: results/uboot.toml#version -->
```

Synthesizing multiple results:

```markdown
The kernel and rootfs are both GPL-encumbered.
<!-- cite: results/binwalk.toml#rootfs_type, results/kernel.toml#version -->
```

### Citation Rules

- References use format `results/<file>.toml#<field>`
- The field must exist in the referenced TOML file
- CI resolves each reference and fails on broken links
- Prose that interprets without citing specific values (legal reasoning, architectural conclusions) needs no citation, but must not contain reproducible facts (offsets, versions, hashes, component names)

## Changes to Existing Infrastructure

### Scripts (`scripts/lib/`) -- additive

`AnalysisBase` already tracks `source` and `method`. Add `reproducibility`:

```python
# analysis_base.py
def add_metadata(self, field_name, source, method, reproducibility="software"):
    """reproducibility: 'software' or 'hardware'"""

def add_hardware_metadata(self, field_name, source, method,
                          equipment, procedure, performed, operator):
    """Convenience method for hardware-derived findings"""
```

TOML output formatter (`lib/output.py`) extended to write `# Reproducibility:` and hardware fields when present.

All existing fields default to `reproducibility="software"`. No existing behavior changes.

### Jinja Templates -- no changes needed

`| src` filter and `FootnoteRegistry` already generate citations from `TrackedValue` metadata. The `reproducibility` field is available in footnotes if desired.

### Hand-Written Docs -- one-time migration

`GPL-COMPLIANCE-ANALYSIS.md` and similar docs need `<!-- cite: -->` comments added:

1. Identify every factual claim (offsets, versions, component names)
2. Find corresponding `results/*.toml#field`
3. Add citation comments
4. Any claim without TOML backing: write the script that produces it, or remove the claim

### CI -- new traceability job

Add a `traceability` job to `.github/workflows/ci.yml` with three checks:

**Check 1: Results freshness (software-reproducible only)**
- Re-run all analysis scripts against firmware
- Diff output against committed `results/*.toml`
- Fail if any software-reproducible field has drifted
- Skip hardware-derived fields

**Check 2: Citation integrity**
- Parse all docs for `<!-- cite: -->` references and `| src` footnotes
- Resolve each to `results/*.toml#field`
- Fail if any citation points to nonexistent file or field

**Check 3: Uncited facts detection**
- Scan docs for patterns resembling factual claims: hex offsets (`0x...`), version strings, file paths, SHA hashes
- Flag any without adjacent citation
- Start as warning, graduate to failure as coverage improves

Implementation: `scripts/verify_traceability.py` -- follows existing script patterns, tested, runs in CI.

## Migration Path

### Step 1: Add reproducibility metadata to framework

- Update `analysis_base.py` and `output.py` with `reproducibility` field
- All existing fields default to `software`
- Update tests

### Step 2: Build citation verifier

- Create `scripts/verify_traceability.py`
- Parse `<!-- cite: -->` syntax and `| src` footnotes
- Resolve against `results/*.toml`
- Report broken citations and uncited facts
- Run manually first, then add to CI

### Step 3: Add citations to hand-written docs

- One-time pass through `GPL-COMPLIANCE-ANALYSIS.md` and similar
- Claims without TOML backing get scripts written or get removed

### Step 4: CI enforcement

- Add `traceability` job to `ci.yml`
- Results freshness check
- Citation integrity check
- Uncited facts detection (warning → failure)

### Step 5: Migrate remaining bash scripts

- Move remaining analyses to Python pipeline with full metadata
- Each migration adds more coverage to verification

## What This Replaces

Epic #77's checkpoint/QMS apparatus is unnecessary for the actual requirement (traceability). This design replaces it:

| Epic #77 Component | Disposition | Rationale |
|---|---|---|
| Checkpoint files (`.claude/work/`) | Drop | Traceability lives in `results/*.toml` metadata |
| Quality rubrics and scoring | Drop | CI verifies citations mechanically |
| Measurement methodology | Drop | Pass/fail -- no subjective scoring |
| Exit criteria framework | Drop | Citations resolve or they don't |
| Narrative generation agent | Drop | Git history + cited docs tell the story |
| Scratchpad staleness monitoring | Drop | Not relevant to traceability |
| Session boundary protocols | Drop | Not relevant to traceability |
| WORKFLOW.md checkpoint guidelines | Drop | Replaced by citation requirements |
| Custom agent profiles | Keep | Useful for code review, orthogonal to traceability |

~2,000 lines of process documentation replaced by one verification script and a metadata field.

## QMS Documentation Disposition

The following docs under `docs/quality/` were created for Epic #77 and should be archived or removed:

- `EMBEDDED-WORKFLOW-EXIT-CRITERIA.md` -- no longer applicable
- `STATUS-UPDATE-QUALITY-CRITERIA.md` -- replaced by CI verification
- `STATUS-UPDATE-MEASUREMENT-METHODOLOGY.md` -- replaced by CI verification
- `PILOT-REVIEW-ISSUE-35.md` -- historical record, archive
- `SCRATCHPAD-FORMAT-SIMPLIFICATION.md` -- no longer applicable
- `RCA-2025-12-13-scratchpad-staleness.md` -- historical record, archive
- `NCR-2025-12-13-001-scratchpad-staleness.md` -- historical record, archive

Retain: `PROCEDURES.md` (P1-P4 still relevant), `QUALITY-POLICY.md`, `QUALITY-OBJECTIVES.md`, `RISK-REGISTER.md`.

## Success Criteria

This design succeeds when:

1. `uv run python scripts/verify_traceability.py` passes with zero broken citations
2. CI fails if a finding is committed without a traceable citation
3. All software-reproducible results can be regenerated from firmware + scripts
4. All hardware-derived results include enough procedure detail to reproduce
5. A third party reviewing the repository can follow the chain from any documented finding back to its source script and method
