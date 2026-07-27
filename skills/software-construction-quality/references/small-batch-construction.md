# Small-batch construction

Construct agentic systems in reviewable, integrated increments that preserve decision intent, testability, rollback and exact artifact evidence. Small batches reduce hidden coupling and make field learning actionable.

## Vocabulary
- **change batch:** Coherent set of modifications that can be reasoned about, verified and reverted together.
- **vertical completion:** Implementation, tests, observability, security, documentation, deployment and acceptance evidence for one bounded outcome.
- **semantic diff:** Change in system behavior, authority, state, effects or evidence—not only lines changed.
- **integration cadence:** Maximum time work may remain unintegrated with the main product path.
- **artifact parity:** Evidence that the reviewed source/config matches the built and delivered artifact.

## Decision procedure
1. Restate the execution contract, acceptance criteria, anti-goals, affected requirements/ADRs, operating envelope and risk.
2. Select the smallest coherent slice; identify semantic behavior, interfaces, state/effects, migrations, observability and rollback.
3. Inspect repository conventions and existing tests before editing; avoid parallel reinvention.
4. Implement with typed boundaries, explicit errors, deterministic controls, feature/exposure separation, and no hidden authority expansion.
5. Run the verification ladder from focused checks to exact packaged artifact; review the semantic diff and provenance.
6. Update trace links, docs/runbooks, change/evidence ledger and follow-up field signal before handoff.

## Decision table

| Batch property | Healthy signal | Stop/split signal |
|---|---|---|
| Scope | one decision/outcome | multiple unrelated behaviors |
| Review | intent and effects understandable | reviewer must reconstruct architecture |
| Verification | focused plus integration evidence | only broad flaky suite |
| Rollback | bounded and rehearsable | irreversible migration/effect mixed in |
| Field learning | clear expected signal | no way to attribute outcome |

## Evidence obligations
- Acceptance evidence is produced with the change, not deferred to a stabilization phase.
- Generated code is held to repository types, security, tests and maintenance standards.
- Feature flags control exposure but do not authorize prohibited effects.
- Unrelated cleanup is separated unless required for safety or verifiability.

## Review questions
1. What behavior or authority changes, even if the diff looks small?
2. Can this batch be verified and reverted independently?
3. Which field or operational signal should move after release?
4. Are generated abstractions earning their lifecycle cost?

## Failure patterns
- Large speculative batch: implementation outruns evidence and review capacity.
- Code-only done: tests, observability, rollback, docs or migration omitted.
- Diff-count productivity: lines or tickets substitute for outcomes and quality.

## Research basis

Supported by DORA small-batch delivery, secure SDLC, agent-first repository practice, and reliable release engineering [R95] [R108] [R110].
