# Session End Checklist

**IMPORTANT:** Before responding to user with "work complete", "ready for next task", or similar session-ending phrases, complete this checklist.

## Work Status Verification
- [ ] All planned work complete (or at clear stopping point)
- [ ] All issues closed that should be closed (verify on GitHub)
- [ ] All commits pushed to remote (`git status` shows clean, no unpushed commits)
- [ ] All tests passing (pytest ran successfully: 647/647 tests)
- [ ] No uncommitted changes (unless intentionally left for next session)
- [ ] No outstanding errors or warnings

## Scratchpad Update (P5 MANDATORY - Enforced by Pre-Commit Hook)

**Use cache system for fast update:**
```python
from scripts.lib.scratchpad_cache import update, add_completion, set_session_info

# Update current work to "Session ending"
update("Session ending - preparing summary")

# Add any final completions
add_completion("✅ Issue #X - Description (CLOSED)")
```

- [ ] Scratchpad file exists: `/tmp/claude-glinet-comet-reversing/scratchpad.md`
- [ ] "Last Updated" timestamp is CURRENT (<2 min ago)
- [ ] "Current Work" field shows "Session ending" or similar
- [ ] "Session Summary" section completed (if applicable):
  - [ ] Work completed this session
  - [ ] Commits made (count and brief description)
  - [ ] Test status (all passing, coverage %)
  - [ ] Next planned work or "Session ended"
- [ ] "Recent Completions" section updated:
  - [ ] Issues closed listed with links
  - [ ] Epic progress updated (if applicable)
- [ ] "Recent Commits" automatically updated by post-commit hook

## Quality Gates
- [ ] All quality checks passed (pytest, ruff, shellcheck)
- [ ] No CI/CD failures on GitHub
- [ ] Documentation up to date with changes made
- [ ] No open TODOs or FIXMEs introduced without tracking

## Communication
- [ ] User informed of completion clearly
- [ ] Next steps clearly stated (if any)
- [ ] Any blockers or issues flagged to user
- [ ] Any questions for user asked before ending

## Pre-Commit Hook Verification
- [ ] If committing final scratchpad: Hook will verify <15 min staleness
- [ ] If hook blocks: Update scratchpad timestamp and retry
- [ ] Post-commit hook will auto-update timestamp after commit

## Final Steps

1. **Update scratchpad one last time:**
   ```bash
   python3 -c "from scripts.lib.scratchpad_cache import update; update('Session ending')"
   /Users/hays/Projects/glinet-comet-reversing/scripts/generate-scratchpad.sh
   ```

2. **Commit and push scratchpad:**
   ```bash
   git add .scratchpad.md
   git commit -m "docs: Update scratchpad - session end"
   git push
   ```

3. **Verify gist updated:**
   - Check GitHub gist shows current timestamp
   - Verify "Last Updated" matches current time

4. **Respond to user:**
   - Provide session summary
   - List completed work
   - Mention next steps (if applicable)

**BLOCKING RULE:** If ANY checkbox above is unchecked, work is NOT complete. Do not end session.

**Reference:** P5 Section 5.5 Step 5 (PROCEDURES.md), NCR-2025-12-13-001

---

*This checklist implements CA #5 from NCR-2025-12-13-001*
