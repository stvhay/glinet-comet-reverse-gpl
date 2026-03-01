# Issue Workflow

Standard process for tracking work via GitHub Issues.

## When to Create Issues

**Always create an issue before:**
- Adding or modifying analysis scripts
- Changing infrastructure or the traceability pipeline
- Modifying documentation that contains factual claims

**Direct commits to main are acceptable for:**
- Single-file typo fixes and formatting
- Simple chores (dependency bumps, lint fixes)
- Scratchpad and status updates

## Labels

Every issue must have a `type:` label. Templates apply these automatically.

| Label | Use for |
|---|---|
| `type:analysis` | Analysis scripts and findings |
| `type:infrastructure` | Framework, tooling, CI/CD |
| `type:documentation` | Documentation updates |
| `type:hardware` | Hardware investigation and verification |
| `type:bug` | Something broken |
| `type:chore` | Maintenance tasks |
| `type:ideation` | Exploratory ideas and hypotheses |

Additional labels as needed:

| Label | Use for |
|---|---|
| `priority:high/medium/low` | Active work prioritization |
| `future-work` | Deferred until project re-activates |
| `epic` | Multi-issue tracking |
| `legal` | Licensing and compliance |
| `ci-failure` | Auto-filed CI failures |

## Branches

Create a branch for any change that touches more than 2 files or needs review.

**Naming:** `<type>/<issue-number>-<short-description>`

Examples:
- `feat/95-reproducibility-metadata`
- `fix/72-ci-test-failure`
- `docs/97-add-citations`

## Pull Requests

Create a PR for all branch work. Requirements:

- Title: concise, under 70 characters
- Body: reference the issue(s) addressed (`Closes #95`)
- Request review for changes to analysis scripts or the traceability pipeline
- CI must pass before merge

## Issue Templates

Templates are in `.github/ISSUE_TEMPLATE/`. Blank issues are disabled -- use a template. Available: Analysis Task, Infrastructure, Bug Report, Documentation, Chore, Ideation.

## Closing Issues

Close with a comment documenting what was done:
- What changed (files, scripts, tests)
- How it was verified (CI, manual test, review)
- Any follow-up work created as new issues
