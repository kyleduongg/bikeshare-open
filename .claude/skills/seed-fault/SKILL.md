---
name: seed-fault
description: Seed one named fault into the pipeline, capture the PostToolUse hook and failing pytest evidence, restore the original code, and verify recovery. Use for the repeated Exercise 2 fault-injection workflow.
allowed-tools: Read, Edit, Bash(python -m pytest*), Bash(make test*), Bash(git diff*), Bash(git status*)
---

# Seeding a fault: $ARGUMENTS

Work in this order. Do not skip step 3 (approval).

## Hard rules

- Never modify `data/raw/**`, anything under `tests/`, or permissions
  (`.claude/settings.json`, `.claude/settings.local.json`, hooks). The
  fault goes in source code only (normally `src/`).
- Never invent, paraphrase, or reconstruct hook output or test results.
  Quote only text actually returned by the tools in this session. If
  something was not produced, write "not captured" and say why.
- Introduce exactly one fault, with Edit. No other edits except the
  restoring Edit in step 5.
- No commits, no `git checkout`/`git restore`/`git stash`; restore with Edit.

## Steps

1. **Identify the fault and the file.** Interpret `$ARGUMENTS` (e.g.
   "use casual as a feature", "random split", "lag without shift(1)").
   If empty or ambiguous, ask the user rather than guessing. Read the
   target file and the relevant rules in `CLAUDE.md` / `src/config.py`.
   Record the file, the exact original lines, and the exact replacement
   lines. Choose a fault that a test in `tests/` is expected to catch;
   if no existing test could catch it, say so now.

2. **Establish a baseline.** Run `make test` and confirm it passes before
   any change. If it already fails, stop and report; the evidence would be
   contaminated.

3. **Ask for approval.** Show the user the file, the original lines, the
   exact modified lines, and the test expected to fail. Wait for an
   explicit yes. Do not call Edit on the fault until approved. If
   declined, stop and change nothing.

4. **Introduce the fault.** Make one Edit with the approved change.
   Copy verbatim whatever the PostToolUse hook
   (`.claude/hooks/check_leakage.sh`) reports after the Edit: its status
   message and any output or failure text. Then run
   `python -m pytest -x -q` (or the specific test file) and copy the
   failing output verbatim: test names, assertion message, summary line.
   If the hook printed nothing, record that fact.

5. **Restore the original code.** Make one Edit that reverses step 4
   exactly, using the original lines recorded in step 1. Capture the
   PostToolUse hook output for this Edit as well. Run `git diff` on the
   file and confirm it is empty (or matches the pre-existing state).

6. **Verify recovery.** Run `make test` and confirm it passes with the
   same count as the baseline. Run `git status` to confirm no file other
   than the untouched pre-existing state differs (no data, test, or
   permission changes).

7. **Report**, in this order:
   - **Fault:** name, file, and line(s).
   - **Exact changes:** original vs. faulty lines, and the restore edit.
   - **Evidence:** verbatim PostToolUse hook output (fault edit and
     restore edit) and verbatim failing pytest output.
   - **Recovery:** the passing `make test` summary line and the clean
     `git diff` / `git status` result.
   - **Repair-turn count:** the number of agent repair attempts from the
     first failing signal to the passing `make test`. Count each repair
     attempt (an Edit that tries to fix the code) as one repair turn. A
     separate verification command such as `make test` does not count as
     an additional repair attempt. Report the actual number, without
     guessing, with a one-line list of what each attempt was. With the
     prescribed workflow this is normally 1: the restore Edit. State any
     deviation plainly.

If any step fails unexpectedly (restore does not give a clean diff, tests
still fail after restoring), stop, report the actual output, and do not
attempt unrelated fixes.
