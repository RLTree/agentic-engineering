# Evidence classes and calibrated confidence

Use evidence to change a decision, not to decorate a report.

## Evidence classes

- **A — constraint or standard:** normative protocol requirements, language/compiler rules, security invariants, public API contracts or user-mandated constraints. Treat as non-negotiable unless explicitly versioned or waived.
- **B — supported practice:** convergent first-party engineering guidance, mature operational experience or replicated empirical evidence. Use as a strong default, then adapt to local constraints.
- **C — emerging evidence:** recent research, young ecosystem practice or limited-replication results. Use for experiments with explicit rollback and evaluation.
- **D — directional signal:** trend, product announcement or plausible future direction. Use for awareness and option value, not as a production mandate.

## Translation card

For each consequential source, record:

1. source and date;
2. evidence class;
3. claim in your own words;
4. local decision it changes;
5. mechanism encoded in the system;
6. evaluation that could falsify the choice;
7. expiry/recheck condition.

## Confidence is not certainty

A confidence score should describe a bounded claim. This plugin's release confidence addresses the proposition:

> Using these skills on in-scope Codex and Rust agent-engineering tasks is more likely than not to improve architecture selection, specification completeness, safety, verification and reviewability relative to an unstructured prompt-only workflow.

It is not a promise that every project will improve, that every model will follow every instruction or that the code assets compile unchanged in every repository.

## Confidence components

Prefer an explicit weighted model:

- source relevance and recency;
- mechanism-to-evidence traceability;
- scope and scenario coverage;
- structural validation;
- behavioral contract coverage;
- target-model empirical transfer;
- implementation/toolchain verification;
- residual-risk severity.

Reduce confidence when the target model, repository, runtime or dependency versions were not exercised directly. Do not inflate confidence by counting documents or checks that do not test the claim.

## Evidence hierarchy for completion

From weakest to strongest:

1. model assertion;
2. source inspection;
3. static analysis;
4. unit test;
5. integration test;
6. fault/recovery or concurrency test;
7. end-to-end test in the exact packaged artifact/environment;
8. independent review or production telemetry against a predeclared criterion.

Match evidence strength to consequence. A destructive production operation needs more than a unit test; a documentation typo does not need a distributed fault-injection campaign.
