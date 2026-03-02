# Design: Claude Code Contributor Guide

**Issue:** #15
**Date:** 2026-03-01
**Status:** Approved

## Goal

Create a concise guide for experienced developers who want to use Claude Code to contribute to this project.

## Deliverables

1. `docs/CLAUDE-CODE-GUIDE.md` -- Standalone guide (~80 lines)
2. `wiki/Contributing-with-Claude-Code.md` -- Wiki copy
3. `wiki/_Sidebar.md` -- Add link under "Getting Started"

## Sections

### 1. Quick Setup (~50 words)

Four steps: install Claude Code, clone repo, `direnv allow`, `claude`. Link to Claude Code install docs. Note that CLAUDE.md loads automatically.

### 2. Project Context for Claude (~150 words)

- CLAUDE.md loads automatically -- contains methodology, legal constraints, firmware details, dev commands, git standards
- `results/*.toml` files provide structured firmware knowledge -- point Claude at these rather than describing findings
- Black-box methodology enforcement -- CLAUDE.md instructs Claude to follow traceability; contributors should be aware of these constraints

### 3. Subagents and Skills (~100 words)

- Subagents: `code-reviewer` (Opus, thorough review) and `quick-task` (Haiku, simple edits)
- Skills: `.claude/skills/` contains project workflows invokable via `/skill-name`. Point to directory, no enumeration.

## Wiki Integration

- Copy guide to `wiki/Contributing-with-Claude-Code.md`
- Add to `wiki/_Sidebar.md` under "Getting Started"

## Non-Goals

- Prompt catalogs or example sessions
- Beginner onboarding (covered by CONTRIBUTING.md)
- Reproducing CLAUDE.md content
