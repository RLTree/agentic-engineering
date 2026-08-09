# Agentic Engineering 3.0 Research Addendum

> **Historical research snapshot through 2026-07-22.** Useful for lineage and
> vocabulary, not current version-sensitive implementation or release authority.
> Current foundations: `docs/foundations/current-2026-08-08.md`.

**Research lock:** July 22, 2026, America/Los_Angeles  
**Scope:** Evidence added after Agentic Engineering 2.0 and the UltraGoal, Compound Engineering, and Superpowers comparison.

## Executive decision

Version 3 retains the original control-architecture and full-lifecycle model, but changes how the plugin activates, learns, verifies, repairs, coordinates, and judges product value.

The upgrade operationalizes nine decisions:

1. **One implicit front door.** Specialist skills remain explicit. The release gate estimates the complete discovery payload and stays below a conservative limit because Codex may shorten or omit skills when the initial list crowds the prompt.
2. **No-change is a successful result.** A request to fix software does not prove a defect still exists. Current behavior must be reproduced, and `no_change`, `partial_change`, `change_required`, and `blocked` are distinct outcomes.
3. **Verification is selected, not ritualized.** TDD remains valuable where observing a test fail proves the oracle, but characterization, property, state-machine, differential, mutation, concurrency, browser, effect, rollout, or field evidence may be more appropriate.
4. **Repair loops are budgeted experiments.** Each attempt changes one material mechanism or gains new evidence. Structured feedback records failure location, observed value, and admissible alternatives. Repeated mechanisms trip a semantic circuit breaker.
5. **Skills are behavior-tested.** Explicit, implicit, contextual, negative, overlap, no-change, and adversarial cases are compared with a baseline. Consequential skills add held-out, mutation, and specification-evolution evaluation.
6. **Workers and reviewers exchange typed evidence.** A root-owned Task Evidence Packet defines identity, ownership, permissions, budgets, and verification. A Review Verdict is candidate-bound and cannot independently promote claims.
7. **Observed outcomes enter a governed learning loop.** Facts, interpretations, and mechanism hypotheses remain separate. One learning record produces the smallest intervention, held-out validation, authority handoff, freshness, supersession, and retirement.
8. **Product Fitness measures value and supervisory work.** Field Pulse and Product Journey Review complement controlled exposure by measuring representative outcomes, intervention, recovery, cognitive load, and continuance without confusing activity or telemetry with fit.
9. **Security continuously adapts.** Identity, authorization, containment, red-team discovery, monitored deployment, updates, and recovery replace the assumption that a fixed guardrail set permanently proves robustness.

## Evidence synthesis

### Leaner routing and configuration

OpenAI’s current skill documentation describes progressive disclosure and a bounded initial skill list. GPT-5.6 guidance reports directional internal evidence that leaner system prompts improved coding-agent scores while substantially reducing tokens and cost, and advises choosing Programmatic Tool Calling, multi-agent, Pro, and reasoning settings by task shape and representative evaluation. This supports a stable outcome contract, one host-owned implicit gateway, concise trigger-only descriptions, explicit specialists, and configuration changes instead of multiple prompting dialects.

### Appropriate inaction

FixedBench evaluates already-resolved software requests and reports substantial action bias across contemporary models and harnesses. Reproduction instructions help but can create false abstention on partially fixed cases. The plugin therefore makes current-behavior reproduction and four-way change disposition first-class, then evaluates both unnecessary action and premature abstention.

### Repair-loop proportionality

A July 2026 empirical study found most gains in examined repair workflows within the first three to four iterations and emphasized orchestration and feedback design. A paired study found large improvements from feedback that exposed location, observed value, and admissible alternatives. The plugin does not hardcode three attempts; it makes budget an evaluated project parameter and adds a semantic stop when the mechanism repeats without new evidence.

### Contextual verification over procedural ritual

TDAD reports that code–test impact context reduced regressions in its studied configurations, while TDD prompting alone increased them. TDDev reports that browser acceptance infrastructure improved web-app generation but that mismatching enforcement protocol to model behavior erased benefit and multiplied cost. An empirical repository study finds agent-generated tests more likely to add mocks. Together these results support a Verification Mode Contract, explicit oracle and mock policy, and representative same-surface evidence rather than universal TDD.

### Anti-gaming skill evaluation

OpenAI’s skill-evaluation guidance calls for explicit, implicit, contextual, and negative cases with JSONL trajectory and artifact grading. Test-Driven AI Agent Definition adds visible/hidden splits, semantic mutation, and specification evolution. Version 3 combines these into an evaluation ladder that measures activation, following, composition, recovery, verified outcome, authority, safety, and efficiency.

### Layer-aware learning and knowledge lifecycle

HarnessFix reports held-out improvements from normalizing failed traces, localizing the responsible step and harness layer, clustering recurring flaws, and applying scoped repair operators. Compound Engineering demonstrates the value of capturing one durable learning at a time, while OpenAI’s harness account emphasizes feeding repeated failures back into tools, guardrails, documentation, and repository structure. Version 3 adopts the compounding mechanism but retains one authoritative registry, generated projections, and explicit freshness/supersession/retirement.

### Human and product outcomes

DORA’s current AI guidance emphasizes user-centricity, small batches, and AI-accessible internal evidence. Longitudinal and mixed-method studies identify supervisory engineering—direction, evaluation, and correction—as a growing category of work and show that perceived productivity can coexist with worse flow or cognitive load. A 2026 meta-analysis finds moderate but heterogeneous productivity benefits and no significant overall learning effect. Product Fitness therefore measures value, intervention, verification burden, ownership, recovery, and continuance rather than code volume, token use, or agent activity alone.

### Continuous agent security

NIST’s 2026 agent initiative and identity work emphasize interoperable standards, explicit identity, authorization, and secure adoption. NIST’s continuous-monitor-and-update research argues that no finite fixed guardrail set can be universally robust against adaptive adversarial prompts. Version 3 retains mandatory security boundaries and adds continuous red-team discovery, monitored deployment, updates, containment, and recovery.

## What Version 3 deliberately does not adopt

- a mandatory skill invocation whenever there is a remote possibility of relevance;
- brainstorming or approval gates for every small change;
- TDD as the only legitimate verification method;
- fresh subagent plus multiple reviewers for every task;
- unlimited review/fix loops;
- a second lifecycle, goal, plan, evidence, or knowledge authority beside the host system;
- token reduction, command count, reviewer consensus, or telemetry presence as standalone success metrics;
- product-fit claims from agent use, installation, one journey, or aggregate activity.

## Residual uncertainty

The package includes deterministic structural, schema, routing, evidence, context-budget, and static Rust checks. This environment does not provide a live Codex executable or Rust toolchain, so the blind GPT-5.6 Sol A/B, behavior evals, compile checks, and real Product Fitness pilot remain downstream protocols. The confidence score therefore reflects evidence quality, mechanism specificity, static validity, and falsifiability—not a measured probability of improvement on every repository.


## Version 3 source traceability

- Codex progressive disclosure, skill discovery, behavior evaluation, and lean GPT-5.6 orchestration: [R126] [R127] [R128].
- Compound Engineering and Superpowers mechanisms and limitations: [R129] [R130].
- User-centricity, small batches, internal evidence, and supervisory engineering: [R131] [R132] [R133] [R134].
- No-change/action bias and bounded repair-loop evidence: [R135] [R136] [R137] [R138].
- Contextual verification, hidden/mutation/evolution evaluation, browser acceptance, and mock quality: [R139] [R140] [R141] [R142].
- File-backed context, longitudinal developer experience, human-centered collaboration, and heterogeneous productivity effects: [R143] [R144] [R145] [R146].
- Agent standards, continuous security, measurement probes, identity/authority, and secure lifecycle practice: [R147] [R148] [R149] [R150] [R151].
