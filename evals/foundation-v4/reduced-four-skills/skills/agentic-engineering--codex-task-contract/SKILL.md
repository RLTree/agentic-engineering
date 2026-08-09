---
name: codex-task-contract
description: "Proposal-only advice for turning an ambiguous task into a bounded, evidence-linked contract."
---

# Codex Task Contract

## Proposal-only advisory scope

Provide a proposed task contract only. Do not take effects, assign authority, adopt policy, or claim completion, efficacy, product value, or operational readiness. Describe suggested owners as proposed owners.

Use this skill when outcome, context, scope, assumptions, approval threshold, or acceptance evidence is ambiguous. Defer decisions owned by a single architecture, verification, or learning specialist.

## Decision procedure

1. State the objective and intended outcome; identify the relevant context and authoritative sources. Label information as observed fact, reversible assumption, hypothesis, decision, or unknown.
2. Define proposed deliverables, constraints, scope, and anti-goals so plausible adjacent work is excluded.
3. Separate reversible assumptions from decisions that cross an approval threshold. Propose escalation for irreversible, externally visible, privileged, expensive, security-sensitive, persistent-data, public-interface, or product-defining choices.
4. Map each proposed acceptance criterion to the evidence that could test it: command, test, trace, rendered interaction, benchmark, artifact inspection, or review. Keep source evidence distinct from unexecuted or unavailable evidence.
5. Return a compact proposed contract with open questions, approval boundaries, acceptance-to-evidence mapping, and residual uncertainty; do not represent the proposal as an executed result.

## Triggered references

Read no reference by default. The parent selects any payload; do not load templates, schemas, or canonical libraries.

- `plugins/agentic-engineering/skills/codex-task-contract/references/assumption-approval-policy.md` — when deciding whether an uncertainty is reversible or requires informed approval.
- `plugins/agentic-engineering/skills/codex-task-contract/references/vocabulary-translator.md` — when adjectives such as robust, safe, or agentic need translation into observable requirements and evidence.
