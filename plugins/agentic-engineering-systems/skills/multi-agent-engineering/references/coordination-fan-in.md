# Coordination and fan-in

The integration point is the system’s coherence boundary. Reserve one authoritative owner and explicit budget for it.

## Before fan-out

- freeze or version shared contracts;
- assign non-overlapping work and state ownership;
- define result schema and local oracle;
- record dependencies and merge order;
- reserve integration/test capacity;
- define partial failure and cancellation.

## During execution

Track worker lifecycle, artifact versions, budget, dependencies and findings. Share only decisions or evidence that materially affect other workers. Avoid a global mutable chat or plan unless updates are versioned and one actor owns conflict resolution.

## Fan-in strategies

- deterministic aggregation for independent homogeneous results;
- ranked selection with explicit rubric and tie-breaker;
- patch merge followed by one integrator’s semantic review;
- synthesis from evidence cards with source provenance;
- staged merge in dependency order.

Never ask the model to “combine everything” without a conflict and completeness contract.

## Integration checklist

1. Validate every expected worker result or classify missing/failed.
2. Check scope/ownership violations and duplicate work.
3. Resolve contradictory findings against authoritative evidence.
4. Apply merge/reducer deterministically where possible.
5. Re-run global tests/invariants; local worker tests are insufficient.
6. Inspect cross-package/API/data/security effects.
7. Produce one coherent decision record and handoff.
8. Cancel or close all workers and reconcile effects.

## Partial failure

Choose fail-fast, quorum, best-effort, fallback worker, or degrade-with-warning per work package. Do not invent quorum semantics for correctness-critical tasks where one missing result leaves a blind spot.

## Metrics

Measure accepted unique contribution, integration defects, overlap, fan-in latency, global verification failures, cancellation waste and total cost. More parallel activity is not inherently better.
