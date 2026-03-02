# Design: Traceability Implementation (Epic)

**Date:** 2026-03-01
**Epic:** #103
**Sub-issues:** #104, #105, #97, #98, #106
**Design basis:** `docs/plans/2026-03-01-traceability-enforcement-design.md`

## Problem

The traceability enforcement design defines the chain: scripts → results → citations → CI verification. The infrastructure is partially built (analysis scripts, `AnalysisBase`, `verify_traceability.py`) but the chain is incomplete:

- Only 2 of 8 TOML result files are committed
- Zero citations exist in any hand-written document
- CI has no traceability verification
- Some factual claims in docs lack backing TOML fields

## Epic Structure

### Epic: Traceability Enforcement (#103)

```
#104  Generate and commit TOML results
  ↓
#105  Fill TOML field gaps for uncitable claims
  ↓
#97   Add citations to hand-written docs
  ↓
#98   Add traceability CI job
  ↓
#106  Enable strict uncited-facts enforcement
```

### Sub-issue 1: Generate and commit TOML results

Run full analysis pipeline against firmware. Commit all `results/*.toml` files. This creates the citation targets.

**Deliverables:**
- `results/binwalk.toml`
- `results/rootfs.toml`
- `results/boot-process.toml`
- `results/device-trees.toml`
- `results/network-services.toml`
- `results/proprietary-blobs.toml`
- `results/secure-boot.toml`
- Updated `results/.manifest.toml`

**Acceptance criteria:**
- All 8 analysis scripts produce valid TOML
- Results committed and parseable by `tomlkit`

### Sub-issue 2: Fill TOML field gaps

After generating results, audit every uncited fact in docs against available TOML fields. Add extraction logic for missing fields.

**Known likely gaps** (to be confirmed after Step 1):
- Firmware SHA256 hash
- Library version strings (FFmpeg, glibc, GLib, etc.)
- Specific file paths (`/usr/bin/coreutils`, `/system/lib/modules/bcmdhd.ko`)
- Build date for BusyBox
- Kernel vermagic string

**Approach:**
- Add fields to existing scripts (e.g., `analyze_rootfs.py` for library versions)
- Each new field gets `add_metadata(field, source, method)`
- Regenerate and re-commit TOML after additions

**Acceptance criteria:**
- Every factual claim in docs has a corresponding TOML field
- All new fields have source/method metadata

### Sub-issue 3: Add citations to hand-written docs (#97)

One-time pass adding `<!-- cite: results/<file>.toml#<field> -->` comments.

**Target documents:**
1. `docs/GPL-COMPLIANCE-ANALYSIS.md` (~30 citations)
2. `README.md` (~10 citations)
3. `docs/analysis/*.md` (6-8 files, varies)

**Citation rules:**
- Factual claims (versions, offsets, hashes, paths, component names) → cite
- Legal interpretation, reasoning, obligations → no citation needed
- External references (URLs, forum links) → no citation needed
- Template letter content → no citation needed

**Format:**
```markdown
The firmware runs U-Boot 2017.09 <!-- cite: results/uboot.toml#version -->
```

**Acceptance criteria:**
- `verify_traceability.py` reports zero broken citations (errors)
- All factual claims have citations

### Sub-issue 4: Add traceability CI job (#98)

New `traceability` job in `.github/workflows/ci.yml`.

**Three checks:**

1. **Results freshness** — Diff regenerated `results/*.toml` against committed versions. Compare value fields only, skip timestamps and generation metadata. Fail if software-reproducible fields drifted.

2. **Citation integrity** — Run `verify_traceability.py`. Fail on broken citations (missing TOML files or fields).

3. **Uncited facts detection** — Run pattern scanner from `verify_traceability.py`. Warning mode initially.

**Implementation:**
- Add `--check-freshness` mode to `verify_traceability.py` that loads two TOML directories and diffs value fields
- `traceability` job runs after `analyze` job, downloads regenerated artifacts
- Job passes on current codebase after citations are added

**Acceptance criteria:**
- CI job exists and runs
- Results freshness check detects drift
- Citation integrity check catches broken references
- Uncited facts scanner runs in warning mode

### Sub-issue 5: Enable strict uncited-facts enforcement

After all citations are complete, flip to `--strict` mode in CI so uncited facts fail the build.

**Acceptance criteria:**
- `verify_traceability.py --strict` passes
- CI uses `--strict` flag
- Any new uncited fact breaks CI

## Implementation Sequence

1. Generate and commit TOML results (requires firmware download)
2. Audit field coverage, fill gaps in scripts
3. Add citations to all hand-written docs
4. Add CI traceability job (warning mode)
5. Enable strict mode

Steps 1-2 can be done in one branch. Step 3 is a separate branch. Steps 4-5 can share a branch.

## Scope Boundary

**In scope:** Everything above.

**Not in scope (future work):**
- Migrating `docs/analysis/*.md` to Jinja templates
- Converting remaining bash analysis to Python
- Adding hardware-derived metadata
- Wiki content migration to Jinja

## Files Changed

| File/Dir | Change |
|----------|--------|
| `results/*.toml` | 6-8 new committed files |
| `scripts/analyze_*.py` | Field additions for gaps |
| `scripts/verify_traceability.py` | Add freshness check mode |
| `docs/GPL-COMPLIANCE-ANALYSIS.md` | ~30 citations |
| `README.md` | ~10 citations |
| `docs/analysis/*.md` | Citations (6-8 files) |
| `.github/workflows/ci.yml` | Add traceability job |
