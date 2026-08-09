# Staged evaluation

> **Superseded Version 3 strategy:** its aggregate release rule is historical
> lineage. `EXECPLAN.md` and `docs/foundations/current-2026-08-08.md` control the
> current staged evaluation and claim ceilings.

Agentic Engineering evaluation is noncompensatory and candidate-bound. The stage graph and stop rules in `EXECPLAN.md` control this document. Passing a later stage cannot repair a failed earlier stage.

| Stage | Decision | Primary evidence | Claim ceiling |
|---|---|---|---|
| A1 | Is the four-pack candidate structurally coherent and truthfully reported? | Exact-candidate, zero-write structural checks with observations | Structural package only. |
| AQ | Do the current and reduced packages select the intended adviser or abstain? | Frozen activation and abstention tasks | Tested routing and abstention only. |
| AS | Does each representative adviser improve a separate builder's final state? | Held-out tasks and evaluator-owned scoring | Isolated advice value on the tested tasks. |
| AC | Do selected advisers compose for exactly two decisions? | New held-out two-decision tasks | Tested composition only. |
| AH | Do exact archives and the approved host boundary behave as required? | Exact archive and clean-host journey | Tested host, supply-chain, and protocol behavior only. |
| AF | Is a field claim warranted? | Separately authorized representative field evidence | Observed field outcomes in the stated operating envelope. |

## A1 structural release

`python3 scripts/release_check.py` is zero-write by default. It records the candidate identity, checks actually executed, observations for each passing check, and claim states. In A1, `structural_package` may be observed only when those checks pass; host installation and discovery, activation and abstention, isolated advice value, composition, and field usefulness remain unobserved.

The command must reject incomplete package sets, identity disagreement, duplicated skill identity, changed package inputs after capture, a full-release claim based on a subset, a passing check without observations, and behavioral labels on structural output. It creates no per-check receipt files by default.

## Later stages

AQ uses frozen authoring and held-out sets, measures explicit invocation separately, and accepts no-skill as a valid disposition. AS uses a fresh adviser, a separate fresh builder, evaluator-owned artifacts, and final-state outcomes as the primary result. Completed weak output is scored, not content-retried.

AC is locked unless AS passes. AH is not a substitute for activation or advice value and must test the exact candidate at the actual archive and host boundary. AF is not implied by participation, package validation, or prior stages. It requires separate authorization before any field activity and retains its own privacy, operating-envelope, and stop rules.

Only one compact stage decision may be retained for a promoted stage, plus the frozen regression inputs required by the plan. Raw trajectories, per-run receipts, and temporary extracts remain ephemeral unless a named custody need requires otherwise.
