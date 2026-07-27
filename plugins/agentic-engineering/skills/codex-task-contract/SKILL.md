---
name: codex-task-contract
description: "Use when a consequential or ambiguous Codex request needs an explicit outcome, authority, evidence, and done contract."
---

# Codex Task Contract

## Core principle

Convert intuition and adjectives into observable decisions while preserving momentum. Ask only for information that crosses a consequence threshold; otherwise make explicit, reversible assumptions and verify them.

## Workflow

### 1. Extract the actual outcome

Restate the user or system outcome independently of the requested implementation. Identify the durable artifact, audience and operational environment.

### 2. Inventory known context

Name relevant repository areas, current behavior, examples, errors, interfaces, prior decisions and source-of-truth documents. Mark missing information by consequence rather than by curiosity.

### 3. Translate adjectives into contracts

Convert words such as robust, production-ready, scalable, polished, agentic and safe into state, interaction, failure, performance, evidence and handoff requirements. Use [the vocabulary translator](references/vocabulary-translator.md).

### 4. Set scope and anti-goals

Declare inclusions, exclusions, public contracts, dependency policy, migration boundary and diff budget. Name plausible but unwanted interpretations.

### 5. Define autonomy and escalation

Allow reversible, low-consequence assumptions. Require approval for irreversible, externally visible, privileged, expensive, security-sensitive or product-defining decisions. Use [the assumption and approval policy](references/assumption-approval-policy.md).

### 6. Map acceptance to evidence

For every acceptance criterion, specify the exact test, command, trace, rendered interaction, benchmark or review evidence. Include exact packaged/deployed artifact checks when delivery can differ from source.

### 7. Compile the execution contract

Use [the execution-contract schema](references/execution-contract-schema.md). Do not begin broad implementation until contradictions, missing decision owners and unsafe ambiguity are explicit.

## Output contract

Return a **Codex Execution Contract** with:

- objective and user/system outcome;
- context and authoritative sources;
- deliverables and integration points;
- constraints, invariants and compatibility;
- scope, non-scope and anti-goals;
- execution architecture and phases;
- autonomy, assumption and approval policy;
- acceptance-to-evidence matrix;
- handoff contents and residual-risk policy.

## Common failures

- **Adjective-only quality request:** “professional” replaces hierarchy, behavior and evidence. Translate it.
- **Asking about reversible implementation details:** asking everything before moving. Ask only when consequence exceeds the threshold.
- **Silent assumptions:** decisions disappear into implementation. Maintain an assumption ledger.
- **Weak done-when:** “tests pass” without naming relevant tests or user behavior. Tie each criterion to evidence.
- **Scope drift by plausibility:** Codex implements adjacent improvements. Use anti-goals and a smallest-coherent-change rule.
- **Completion without exact artifact:** source is changed but package, migration, docs or report is missing. Name every artifact and location.

## References

- [Execution-contract schema](references/execution-contract-schema.md)
- [Vocabulary translator](references/vocabulary-translator.md)
- [Assumption and approval policy](references/assumption-approval-policy.md)

## Shared references

- [Seven-layer map](../../references/seven-layer-map.md)
- [Architecture escalation](../../references/architecture-escalation.md)
- [GPT-5.6 Sol operating profile](../../references/gpt-5.6-sol-operating-profile.md)
- [Evidence and confidence](../../references/evidence-and-confidence.md)

## Version 3 prompt and execution selection

Keep the execution contract outcome-first and lean. State each rule once. Prefer changing model, reasoning effort, Pro, Programmatic Tool Calling, or Ultra configuration over adding model-specific procedural prose. Include a no-change success path, proportional verification, repair budget, and explicit authority for safe local actions. Read `../../references/gpt-5.6-execution-selection.md` and `../../references/no-change-and-abstention.md`.
