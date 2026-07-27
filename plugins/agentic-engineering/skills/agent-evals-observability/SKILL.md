---
name: agent-evals-observability
description: "Use when evaluating agent, skill, harness, loop, graph, or coding behavior beyond one final answer."
---

# Agent Evals and Observability

## Core principle

Evaluate the behavior that matters on the task distribution you actually operate. A final answer score is insufficient for multi-step systems; preserve enough trajectory and effect evidence to explain success, failure and recovery.

## Workflow

### 1. Define the decision the eval informs

State whether the eval gates release, compares architecture/model/prompt versions, detects regression, calibrates approvals or diagnoses failures. Avoid benchmark collection without a decision owner.

### 2. Build from real failures

Turn production incidents, reviewer corrections, unsafe attempts, loops, duplicate effects and handoff defects into fixtures. Stratify by risk, task type, repository and failure mechanism.

### 3. Cover the evaluation stack

Use [the eval taxonomy](references/eval-taxonomy.md): outcome, constraint, trajectory, tool/effect, recovery, safety, cost/latency and human-review burden. Include deterministic checks wherever possible.

### 4. Specify traces

Capture stable IDs, model/config, context provenance, decisions, tools, state transitions, budgets, effects, approvals, verification and terminal reason. Apply redaction and sampling. Use [the trace and evidence schema](references/trace-evidence-schema.md).

### 5. Design graders

Prefer executable oracles. For model graders, define rubric, evidence input, ambiguity handling, calibration set, inter-grader agreement and adversarial cases. Do not let a grader infer facts absent from the trace.

### 6. Compare variants fairly

Freeze fixtures, environment, tool versions, budgets and evidence. Randomize/blind human review where practical. Report confidence intervals or at least paired wins/losses and failure categories.

### 7. Add release and online gates

Set thresholds by consequence, not a single aggregate average. Preserve a small fast regression suite and a broader scheduled suite. Monitor drift, cost, latency and novel failure clusters.

### 8. Close the loop

Every significant failure must map to a task-contract, context, harness, tool, loop, graph, security, product, lifecycle, or repository change plus a regression case. For representative live exposure, operating-envelope design, intervention evidence, and field-to-product decisions, compose with `$authentic-use-engineering`; do not treat an offline eval suite as proof of field fit.

## Output contract

Return an **Agent Evaluation and Evidence Plan** with:

- decision and target task distribution;
- fixture/source strategy;
- metrics across outcome, trajectory, recovery, safety and efficiency;
- trace schema and redaction;
- grader/oracle design and calibration;
- baseline/variant comparison protocol;
- release thresholds and online monitoring;
- failure-to-infrastructure workflow.

## Common failures

- **Final-answer-only eval:** unsafe or wasteful trajectories pass. Score process and effects.
- **Single demo as evaluation:** fixtures do not represent real failures. Seed from incidents and corrections.
- **LLM grader monoculture:** subjective graders replace executable truth. Use deterministic oracles first.
- **One composite score hiding safety failure:** severe safety failures disappear in averages. Use per-risk gates.
- **Unreproducible traces:** versions, context or tool outputs are missing. Capture causal state.
- **Self-reported tests as proof:** failures produce reports, not durable corrections. Require an owner and regression.

## References

- [Eval taxonomy](references/eval-taxonomy.md)
- [Trace and evidence schema](references/trace-evidence-schema.md)
- [Grader design](references/grader-design.md)
- [Failure-derived eval loop](references/failure-derived-evals.md)

## Shared references

- Seven-layer map (canonical repository reference library: seven-layer-map.md)
- Architecture escalation (canonical repository reference library: architecture-escalation.md)
- GPT-5.6 Sol operating profile (canonical repository reference library: gpt-5.6-sol-operating-profile.md)
- Evidence and confidence (canonical repository reference library: evidence-and-confidence.md)
- Controlled field-learning system (canonical repository reference library: controlled-field-learning-system.md)
- Field evidence ladder (canonical repository reference library: field-evidence-ladder.md)

## Version 3 skill and behavior evaluation

For material skill changes, compare against a no-skill or prior-version baseline and include explicit, implicit, contextual, negative, overlap, missing-access, small, consequential, no-change, and adversarial-proxy cases. Add held-out, semantic mutation, and specification-evolution splits when a rule is consequential. Score activation, following, composition, recovery, verified outcome, authority, safety, and efficiency separately. Read the canonical repository reference library (skill-behavior-evaluation.md) and use the canonical repository template or schema library (schemas/skill-eval-case.schema.json).
