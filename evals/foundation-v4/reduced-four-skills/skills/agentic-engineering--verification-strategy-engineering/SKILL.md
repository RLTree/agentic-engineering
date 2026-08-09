---
name: verification-strategy-engineering
description: "Explicit, proposal-only advice for choosing proportional verification evidence for an exact software or agent candidate."
---

# Verification Strategy Engineering

## Advisory scope

Produce a proposal only. This skill takes no effects, assigns no authority, adopts no policy, and makes no completion, efficacy, or product claim. Use recommendation, proposed owner, and proposed disposition language; leave execution and acceptance to the named authority.

## Decision procedure

1. Bind the request to the exact candidate and surface. Classify the relevant change shape and state whether current behavior has been reproduced; `no_change` and `partial_change` are valid proposed dispositions.
2. Identify material failure modes and propose a risk assessment from consequence, reversibility, novelty, ambiguity, blast radius, external effects, legacy uncertainty, and observability.
3. Propose an oracle that can distinguish relevant wrong from right behavior. State its limitations; where it is weak, recommend independent boundary evidence and a lower claim ceiling.
4. Recommend the smallest verification modes that could falsify the material failures. Reject modes that add ceremony without retiring risk. Match the mode to the candidate: behavior, characterization, contract/integration, invariant, differential, fault/recovery, browser/journey, accessibility, performance, security, migration, rollout, or field evidence.
5. Propose anti-gaming controls: representative fixtures, independent expected values, real-boundary evidence for consequential mocked paths, and mutation, reversal, differential, or held-out checks when fault detection is uncertain.
6. Propose freshness rules binding evidence to the exact candidate and surface, including what must be rerun after source, package, installation, deployment, or runtime changes.
7. State a proposed disposition, proposed owner, residual risks, invalidation triggers, and a structural-evidence-only claim ceiling unless independently executed evidence supports more.

## Proposal shape

- Exact candidate and surface; current-behavior status.
- Proposed risk and failure model.
- Recommended and rejected verification modes, with rationale.
- Proposed oracle, fixture and boundary strategy, plus limitations.
- Proposed freshness, stop, failure-routing, ownership, and disposition rules.
- Residual risk and claim ceiling.

## Triggered frozen-source references

Read no reference by default. The parent selects any payload; do not load templates, schemas, or canonical libraries.

- `plugins/agentic-engineering/skills/verification-strategy-engineering/references/verification-mode-selection.md` — trigger: selecting a mode for a named change shape.
- `plugins/agentic-engineering/skills/verification-strategy-engineering/references/test-oracle-quality.md` — trigger: assessing whether an oracle detects relevant wrong behavior.
- `plugins/agentic-engineering/skills/verification-strategy-engineering/references/browser-field-and-effect-verification.md` — trigger: a user journey, external effect, or field boundary is material.
