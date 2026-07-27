# Agent-ready repository rubric

Score each dimension 0–3: absent, partial, reliable, exemplary. A repository is agent-ready when a fresh coding agent can make a bounded change, prove it, and hand it off without hidden tribal knowledge.

## Dimensions

1. **Outcome and domain clarity:** product/system purpose, users, invariants and major workflows are discoverable.
2. **Architecture legibility:** package map, dependency direction, public boundaries, state/effect ownership and generated code are explicit.
3. **Layered guidance:** concise AGENTS.md files provide scoped conventions without contradiction or duplication.
4. **Fast feedback:** setup and fast validation are deterministic, documented and reasonably quick.
5. **Full verification:** release/test/security/migration commands exist and exact artifacts can be tested.
6. **Representative examples:** canonical code and tests demonstrate patterns better than prose alone.
7. **Specification and decisions:** task plans/ADRs capture consequential choices, alternatives and acceptance evidence.
8. **Tooling and environment:** dependencies, fixtures, secrets, network assumptions and sandbox needs are reproducible.
9. **Security and data boundaries:** sensitive paths, permissions, prohibited actions and approval requirements are visible/enforced.
10. **Agent evals:** recurrent agent failures and key workflows have fixtures/graders.
11. **Observability and operations:** logs/traces/metrics/runbooks support debugging and recovery.
12. **Artifact handoff:** branches/PRs/packages/reports/digests are the unit of review, not chat claims.

## Blocking deficiencies

No reliable test command, undocumented generated files, hidden production effects, contradictory guidance, unowned mutable state, secrets required in prompts, or no way to verify the delivered artifact.

## Improvement order

Fix blockers and fast feedback first. Then architecture/guidance, verification, security/effect controls, and evaluation. Do not begin by writing a massive agent manual; replace stable rules with code/tests/types where possible.

## Evidence

Require file/command references for every score. Re-score after real agent tasks and record which corrections were needed. The rubric is useful only when it predicts fewer repair turns and safer accepted changes.
