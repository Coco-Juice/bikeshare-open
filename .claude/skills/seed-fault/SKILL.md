---
name: seed-fault
description: Seed a named fault on purpose, capture the red test and hook stderr verbatim, restore to green, and record the incident with a turn count. Use to demonstrate a guardrail, test the hook, or re-run a fault from docs/SEEDED_FAULTS.md after code changes.
allowed-tools: Read, Edit, Bash(python -m pytest*), Bash(make*), Bash(git diff:*), Bash(git status), Bash(git checkout --:*)
---

# Seeding fault: $ARGUMENTS

$ARGUMENTS is the fault to seed (a short name, optionally with a file),
e.g. `forbidden-column`, `drop-shift cnt_roll_7`, `encoder-raise`,
matching or extending docs/SEEDED_FAULTS.md.

Work in this order. A fault that is never confirmed red, or never fully
restored, scores as a broken repo. Do not skip the restore step.

1. **Confirm the tree is green and clean first.** Run `make test` (or
   `python -m pytest tests/test_leakage.py -q`) and check
   `git status --short` for src/. Seeding on top of an unknown state
   makes the turn count and the red output meaningless.

2. **State the exact change before making it** -- one line, quoted as a
   before/after diff. If the fault cannot be expressed as a single
   minimal edit, it is two faults; pick one.

3. **Seed with one Edit to src/.** The PostToolUse hook
   (.claude/hooks/check_leakage.sh) fires on that edit and its stderr
   arrives attached to the same tool result -- that output is the
   evidence, verbatim. If the hook fires with a red test, the exercise
   works; if it does NOT fire, that is a finding to record (see step 6),
   not a reason to stop.

4. **Capture the red test yourself** with `python -m pytest -q` (full
   suite) so the record shows exactly which tests went red and what
   failed for the right reason. Paste real output, never a description
   of it.

5. **Restore exactly**: revert the single edit (Edit back, or
   `git checkout -- <file>`), re-run the suite, and confirm
   `git status --short` shows src/ clean. The only edit a seed-fault run
   may leave behind is a newly added *regression test* for the fault,
   applied while green, so the fault goes red next time (precedent:
   fault 3, the encoder raise).

6. **Record the incident in docs/SEEDED_FAULTS.md**: the exact change,
   the hook's stderr verbatim, the red test output verbatim, and the
   turn count (number of agent turns from the seeding edit to a verified
   green restore). If the fault produced no red test or no hook fire,
   say so plainly and explain why -- an invisible fault is the most
   valuable row in the table, not an empty one.

7. **Verify with git**: `git diff` on the seeded file must be empty
   (modulo any regression test added in step 5). Nothing may survive the
   exercise.

Rules:
- Never seed two faults at once; one edit, one red run, one restore.
- Never "fix" the fault by redefining what it broke (e.g. deleting or
  weakening the test that went red). The test is the witness; the
  restore is for the source.
- If the hook is broken (e.g. a missing interpreter), record that as the
  hook's stderr anyway: a hook that exits silently is a finding.
- Count turns honestly. A fix that took you three tries with detours
  gets its real number -- the count is the deliverable.
