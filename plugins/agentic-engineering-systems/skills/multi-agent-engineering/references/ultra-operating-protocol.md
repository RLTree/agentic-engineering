# GPT-5.6 Sol Ultra operating protocol

Ultra should be reserved for difficult work with meaningful parallel decomposition. Higher compute and more agents do not repair weak specifications, missing evidence, unsafe tools or coupled work.

## Entry gate

Before selecting Ultra, write:

- why a high/Max single-agent run is insufficient;
- independent workstreams and exclusions;
- expected critical-path or context-quality gain;
- shared-state and file ownership;
- per-worker evidence contract;
- integration owner and budget;
- cancellation/partial-failure policy;
- risk/permission boundaries.

## Good uses

Independent repository exploration, several evidence domains, implementation by disjoint modules after interfaces are fixed, broad test generation by subsystem, or alternative solutions evaluated by an independent rubric.

## Bad uses

One tightly coupled refactor, one product/design direction, rapid edits to shared interfaces, tasks without local verification, or “have several agents agree” where errors are correlated.

## Operating phases

1. **Contract:** normalize outcome, constraints, architecture and oracle.
2. **Decompose:** produce dependency-aware packages; reject overlap.
3. **Delegate:** give scoped context/tools/budgets and result schemas.
4. **Monitor:** track progress and intervene only on dependency/risk changes.
5. **Fan-in:** one authoritative integration pass resolves conflicts.
6. **Verify:** run global acceptance and safety checks on the exact artifact.
7. **Close:** cancel workers, reconcile effects, record evidence and residual risk.

## Confidence discipline

Do not convert worker count or consensus into confidence. Confidence should reflect evidence quality, independence, coverage, verification and known residuals. Report which parts benefited from parallel work and which remained single-owner judgments.
