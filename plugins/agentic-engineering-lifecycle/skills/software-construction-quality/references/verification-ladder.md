# Verification ladder

Escalate verification to the consequence and failure modes of the change. A model assertion, successful build, or single happy-path test is not completion evidence for a consequential agentic product.

## Vocabulary
- **oracle:** Rule or mechanism that determines whether behavior is acceptable.
- **property test:** Generated examples checking an invariant across broad input space.
- **contract test:** Verification that interacting components honor a versioned interface and semantics.
- **fault/recovery test:** Deliberate failure, interruption or ambiguity used to verify state and recovery.
- **exact-artifact test:** Execution against the same package, configuration and dependency resolution intended for delivery.

## Decision procedure
1. Map each acceptance criterion, risk, requirement, quality scenario, effect and recovery path to an evidence method.
2. Run static/schema/type/lint/format checks and focused unit/property/state-machine tests.
3. Run integration/contract/protocol tests for tools, providers, storage, queues, identity and policy.
4. Exercise concurrency, cancellation, deadlines, saturation, fault, restart, replay, ambiguous effects and rollback.
5. Run security, privacy, supply-chain, migration, accessibility/performance and end-to-end tests as applicable.
6. Verify the exact packaged artifact and deployment configuration; preserve commands, versions, results and gaps.
7. For agent behavior, include outcome, trajectory, recovery, safety and representative field evidence.

## Decision table

| Claim | Minimum credible evidence | Additional high-consequence evidence |
|---|---|---|
| Pure transformation | unit/property test | mutation or independent oracle |
| Tool/effect contract | schema + integration | fault/reconciliation and permission test |
| Loop/graph behavior | state/trajectory tests | replay, budget, interrupt, recovery |
| Production reliability | load/fault/PRR | game day and SLO observation |
| Product value | representative validation | controlled field/causal evidence |

## Evidence obligations
- Every required criterion has evidence or is explicitly unmet.
- Tests cover negative, denied, ambiguous and recovery paths.
- Model-based graders are calibrated and not the sole oracle for their own outputs.
- Environment/toolchain gaps reduce confidence and are not described as passed.

## Review questions
1. What failure class can pass the current tests?
2. Does this evidence exercise the exact artifact and configuration?
3. Which oracle is independent of the generating model?
4. What field evidence is still needed before broader autonomy?

## Failure patterns
- Build equals verified: compilation treated as outcome evidence.
- Happy-path pyramid: many unit tests but no effects, integration or recovery.
- Self-grading loop: the same model generates, judges and certifies behavior.

## Research basis

Combines secure verification, SRE testing, agent evaluation, and Rust verification practices [R72] [R74] [R95] [R109].
