# Design: Automated Citation Insertion

**Date:** 2026-03-01
**Issue:** #97 (Add citations to hand-written documentation)
**Epic:** #103 (Traceability Enforcement)
**Type:** Documentation / Infrastructure

## Problem

The traceability verifier (`scripts/verify_traceability.py`) reports 273 uncited fact warnings across 38 Markdown files and 0 existing citations. Every factual claim (version strings, hex offsets, SHA hashes, absolute paths) needs a `<!-- cite: results/<file>.toml#<field> -->` comment linking it to the TOML result that produced it.

## Approach

Write `scripts/insert_citations.py` — a script that builds a reverse index from TOML result data and uses it to automatically insert citation comments into Markdown documentation.

## Architecture

### Step 1: Build Reverse Index

Walk every TOML file in `results/`, extract all fact-like values, and map them to their citation reference.

Four TOML data shapes:

- **Scalar fields** — Direct value: `"0x8F1B4"` → `results/binwalk.toml#bootloader_fit_offset`
- **Embedded values** — Substrings: `"4.19.111"` extracted from `kernel_version` string → `results/rootfs.toml#kernel_version`
- **Array-of-objects fields** — Walk sub-fields: `shared_libraries[].path` → `results/rootfs.toml#shared_libraries`
- **String arrays** — Direct array entries: `all_rockchip_libs[]` → `results/proprietary_blobs.toml#all_rockchip_libs`

Priority rules when a value appears in multiple TOML files:
- Prefer scalar fields over array fields
- Prefer `binwalk.toml` for hex offsets
- Prefer `rootfs.toml` for versions and paths
- Prefer `uboot.toml` for U-Boot-specific data

### Step 2: Scan Markdown Files

For each file in `docs/` and `wiki/`:
- Skip files in `plans/`, `archive/`, `quality/` subdirectories
- Skip Jinja-generated output files (e.g., `wiki/Device-Tree-Analysis.md`)
- Process line by line, tracking code block state (skip fenced blocks)
- Skip lines that already have a citation comment

### Step 3: Match & Insert Citations

For each uncitable line:
1. Run the same four patterns the verifier uses (hex, version, SHA, path)
2. Extract the matched value
3. Look up in the reverse index
4. Append `<!-- cite: results/<file>.toml#<field> -->` to end of line
5. For multi-fact lines, combine references in one comment

### Step 4: Report Gaps

Any fact value with no TOML match is reported to stderr as an unresolvable gap. These need manual resolution (either add a TOML field or determine the citation is not needed).

## Citation Format

```markdown
| **Version** | 4.19.111 | <!-- cite: results/rootfs.toml#kernel_version -->
```

Multi-reference:
```markdown
<!-- cite: results/rootfs.toml#kernel_version results/binwalk.toml#firmware_file -->
```

## Validation

After running the insertion script:
```bash
uv run python scripts/verify_traceability.py --docs-dir docs --wiki-dir wiki
```

Target: 0 errors, 0 warnings.

## Scope

**In scope:** Citation insertion into hand-written Markdown files.

**Not in scope:** Modifying TOML files, analysis scripts, the verifier, or Jinja templates.

## Files

- **New:** `scripts/insert_citations.py`
- **Modified:** All 38 scanned Markdown files (citation comments added)
- **Unchanged:** `results/*.toml`, `scripts/verify_traceability.py`, `templates/`
