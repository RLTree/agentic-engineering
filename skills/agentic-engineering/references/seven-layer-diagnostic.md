# Seven-layer diagnostic

Use this diagnostic when an agentic result is plausible but repeatedly misses intent, coherence, safety, or finish. Do not begin by rewriting the prompt. First locate the decision that is implicit or unenforced.

## The layers

| Layer | Owns | Typical symptoms when weak | Durable repair |
|---|---|---|---|
| Specification | outcome, scope, invariants, acceptance, anti-goals | repeated clarification, plausible-but-wrong output, scope drift | execution contract, acceptance-to-evidence matrix |
| Context | working evidence, retrieval, provenance, compaction | forgotten constraints, stale guidance, irrelevant fixation | repository map, retrieval policy, progressive disclosure, checkpoint summary |
| Harness | tools, permissions, state, tracing, recovery | unsafe or inconsistent tool use, transcript archaeology, retry chaos | typed tool gateway, run state, approval policy, effect journal |
| Loop | observe/plan/act/verify/update/stop | endless research, repeated edits, premature success | budgets, oracle, recovery taxonomy, stop policy |
| Graph | branches, cycles, joins, interrupts, checkpoints | hidden control flow, duplicate effects, unrecoverable approval | typed state, explicit nodes/edges, reducers, replay tests |
| System | actors, trust, delegation, protocols, operations | worker conflict, unclear ownership, cascading failure | role/capability contracts, fan-in owner, failure containment |
| Software delivery | repository legibility, tests, CI, artifacts, maintenance | one-off success that cannot be reproduced or reviewed | AGENTS.md, skills, tests, evals, ADRs, exact-delivery checks |

## Diagnostic procedure

1. **Name the failed outcome.** Describe the observable gap without attributing motive to the model.
2. **Identify the missing decision.** Ask what a competent implementer would need to decide differently.
3. **Locate the enforcing layer.** Choose the lowest layer capable of making the decision reliable.
4. **Separate instruction from mechanism.** A one-time preference may remain in the task contract; a recurring invariant belongs in repository or harness infrastructure.
5. **Define an oracle.** State what evidence would show the repair worked and what regression would show it failed.
6. **Avoid layer collapse.** Do not use a graph to compensate for weak acceptance criteria or a longer prompt to compensate for unsafe tools.

## Symptom-to-layer probes

### “The agent asks too many questions.”
Check the assumption policy before blaming context. Distinguish reversible assumptions from consequence-bearing choices and state the threshold for escalation.

### “The result works but is not coherent.”
Check specification and product invariants. Coherence requires one product truth, hierarchy, interaction contract, and explicit anti-goals—not more implementation detail.

### “The agent keeps editing but does not converge.”
Check the loop contract. Require a discriminating verification step, state delta, remaining defect list, and maximum repeated-action count.

### “Retries created duplicates.”
Check harness and graph effect semantics. External effects require stable action IDs, idempotency keys, pre/post effect records, and reconciliation after ambiguous failures.

### “Parallel workers conflict.”
Check system ownership and fan-in. Work packages must be non-overlapping or have one authoritative integrator and a deterministic merge order.

### “The next session repeats old mistakes.”
Check software delivery. Promote repeated correction to AGENTS.md, a skill, test, eval, linter, schema, or policy according to what can enforce it.

## Output

Produce a short diagnosis with: failed outcome; implicit decision; responsible layer; proposed durable mechanism; evidence that will validate the repair; and a revisit trigger. When more than two layers are implicated, order repairs from foundational to downstream: specification → context → harness → loop/graph → system → delivery.
