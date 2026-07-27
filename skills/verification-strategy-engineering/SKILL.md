---
name: verification-strategy-engineering
description: Use when a software or agent change needs a proportional proof strategy before implementation, review, or release.
---
# Verification Strategy Engineering

## Core principle

Select the smallest evidence portfolio that can falsify the important failure modes of the exact change and candidate. Verification ceremony that cannot detect the defect is not assurance.

## Outcome

Produce a **Verification Mode Contract** selecting the smallest credible set of proofs for the change, risk, oracle, and claim.

The goal is not maximum test ceremony. The goal is evidence that would detect the important ways this change could be wrong without creating a slower, easier-to-game proxy system.

## Workflow

1. **Classify the change.** Identify behavior, state, data, interface, concurrency, security, performance, migration, operational, user-journey, or documentation effects.
2. **Establish risk.** Consider consequence, reversibility, novelty, ambiguity, blast radius, external effects, legacy uncertainty, and observability.
3. **Check whether change is needed.** Reproduce the request against current behavior. A verified `no_change` or `partial_change` decision is a successful outcome.
4. **Choose the oracle.** Name what can distinguish correct from incorrect behavior and its limitations. When no strong oracle exists, use independent evidence and lower the claim ceiling.
5. **Select modes.** Choose only those that retire material risk:
   - no-change or current-behavior proof;
   - test-first behavior proof;
   - characterization-first legacy protection;
   - unit, contract, integration, or end-to-end checks;
   - property, invariant, state-machine, or model-based testing;
   - differential, metamorphic, or mutation testing;
   - concurrency, cancellation, saturation, fault, crash, retry, or recovery testing;
   - browser, journey, accessibility, performance, security, migration, rollout, or field evidence.
6. **Control test quality.** Prefer real behavior and contract boundaries. Mock only where the boundary itself is the subject or the real dependency is unsafe, unavailable, or prohibitively costly. Require representative integration evidence for mocked critical paths.
7. **Define freshness and independence.** Bind evidence to the exact candidate and surface. Specify what must be rerun after change, review, packaging, installation, or deployment.
8. **Set stop and claim rules.** State the required evidence, acceptable residual risk, failure routing, and maximum claim supported.

## Output contract

Include:

- change and exact candidate/surface;
- risk and failure model;
- current-behavior reproduction and no-change disposition;
- selected and rejected verification modes with rationale;
- oracle, fixtures, representative populations, and anti-gaming controls;
- mock policy and real-boundary evidence;
- commands, environments, artifact identities, and freshness rules;
- repair budget and structured feedback contract;
- acceptance evidence, residual risk, claim ceiling, and invalidation triggers.

## Boundaries

- TDD is one mode, not a universal constitution.
- A passing test written after the change is not proof that the test can detect the defect; use red/green, mutation, reversal, differential, or held-out evidence when that distinction matters.
- Coverage percentage is not a substitute for fault-detection evidence.
- Do not multiply end-to-end suites when a smaller stable oracle retires the risk.

## Common failures

- Assuming a requested defect still exists instead of reproducing current behavior.
- Using TDD, coverage percentage, or an end-to-end suite as a universal proxy for correctness.
- Testing mocks while leaving the real consequential boundary unobserved.
- Reusing stale evidence across source, package, installation, deployment, or runtime surfaces.


## References

- `references/verification-mode-selection.md`
- `references/test-oracle-quality.md`
- `references/risk-based-evidence-ladder.md`
- `references/browser-field-and-effect-verification.md`
- `../../references/no-change-and-abstention.md`
- `../../references/repair-budget-and-feedback.md`

Use `../../assets/templates/verification-mode-contract.md` and `../../assets/schemas/verification-mode-contract.schema.json`.
