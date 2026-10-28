Prepare a verifiable handoff for the current task.

Update `.context/STATE.md` from observed evidence: objective, user constraints,
acceptance criteria, checkout, completed changes, decisions, checks and pending work.
Inspect the relevant working tree state. Verify referenced artifacts exist and
identify their version or checksum when needed to recover the same evidence.

Keep unresolved requirements, errors and uncertainties explicit. Record enough
detail to resume without assuming that a summary preserves every implementation
detail. Do not copy secrets or large raw logs into the state file.

Report the state file path and the next action. Do not delete files, rewrite Git
history, or claim that conversation pruning/compaction has happened. The user or
the runtime controls the actual session compaction.
