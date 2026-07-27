# Context budget and retrieval policy

Context is a finite attention budget. Assemble the smallest sufficient, highest-signal evidence for the current decision; do not equate more tokens with more understanding.

## Context classes

- **Control:** task contract, active skill, policy, acceptance criteria.
- **State:** current run/task/node state, plan, decisions, remaining work.
- **Repository evidence:** relevant code, tests, schemas, docs, history.
- **Tool evidence:** structured results, errors, traces, diffs, builds.
- **Background knowledge:** references needed for the present decision.
- **Noise:** stale transcript, superseded plans, duplicate files, broad dumps.

Control and authoritative state must be distinguishable from untrusted retrieved content.

## Retrieval sequence

1. Start with repository map, task contract, root guidance, and current state.
2. Form a concrete information need: symbol, behavior, invariant, call path, failing test, or design decision.
3. Search narrowly, then open the smallest coherent neighborhood.
4. Follow dependency or call edges only as evidence requires.
5. Record provenance and freshness for external/tool-provided text.
6. Summarize decisions and evidence; evict or mark superseded material.

## Relevance test

Include a context item only when it can change one of: planned action, correctness judgment, safety/permission decision, verification, or handoff. Otherwise link or index it instead of injecting it.

## Progressive disclosure

Keep skill descriptions concise so selection remains accurate. Put procedures in SKILL.md, deep domain detail in `references/`, deterministic behavior in `scripts/`, and reusable output forms in `assets/`. Load full detail only when the current work invokes it.

## Compaction checkpoint

Before compaction or handoff, preserve:

- objective and acceptance criteria;
- authoritative current state and artifact paths;
- decisions with rationale;
- facts/assumptions/hypotheses;
- completed work and exact evidence;
- remaining work and dependencies;
- failures attempted and why they failed;
- permissions/approvals and side effects;
- next discriminating action.

A summary that says only “continue implementation” is not resumable.

## Context failure tests

Test with a fresh session: can it locate the right package, preserve invariants, avoid superseded guidance, and resume from the state record without transcript archaeology? Measure retrieval precision and missed critical context, not only token volume.
