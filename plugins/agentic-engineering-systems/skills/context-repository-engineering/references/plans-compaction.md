# Plans, progress, and compaction

Long-running agent work needs a durable working record that survives context loss, process interruption, and handoff. The plan is an executable state artifact, not a ceremonial checklist.

## Plan structure

```markdown
# Plan: <outcome>
Status: active | blocked | complete | superseded
Last updated: <timestamp/commit>

## Invariants
## Acceptance-to-evidence matrix
## Decisions and rationale
## Work packages
- [ ] ID / owner / files / dependencies / deliverable / verification
## Current state
## Attempts and findings
## Effects and approvals
## Risks and blockers
## Next discriminating action
## Handoff
```

## Plan discipline

- Each work package has an observable deliverable and verification step.
- Update the plan when evidence changes the approach, not after every keystroke.
- Mark superseded decisions; do not silently rewrite history that matters for review.
- Separate “done” from “claimed done”: record command, result, artifact, and environment.
- Keep the next action specific enough that a fresh agent can execute it.

## Compaction protocol

1. Re-read objective, invariants, acceptance criteria, and current diff/state.
2. Reconcile transcript claims against files and tool evidence.
3. Collapse repeated exploration into findings and rejected hypotheses.
4. Preserve unresolved contradictions and failed approaches.
5. Record side effects, approvals, idempotency keys, and ambiguous outcomes.
6. Index large evidence rather than copying it wholesale.
7. Confirm a fresh reader can resume without the discarded context.

## Handoff quality gate

A handoff must answer: What is the outcome? What is authoritative? What changed? What remains? What evidence exists? What failed? What is unsafe to repeat? What approval is pending? What is the next discriminating action?

## Anti-patterns

- plan as a generic task checklist;
- completed items without evidence;
- transcript as the only state store;
- summary that loses exact file paths or IDs;
- silent changes to scope;
- compaction before reconciling ambiguous external effects;
- several agents updating one plan without ownership/version rules.
