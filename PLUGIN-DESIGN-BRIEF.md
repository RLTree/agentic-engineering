# Plugin Design Brief

## 1. Situation

The user has strong architectural instincts but lacks compact vocabulary and reusable contracts for asking Codex to produce coherent, professional agentic systems. The failure pattern is excessive conversational repair: ambiguous adjectives are interpreted inconsistently; control flow remains hidden; state, effects, recovery and evidence are added late; and Rust implementation details become coupled to whichever provider/framework is chosen first.

## 2. Evidence

The design uses 125 mapped sources, prioritizing official Codex and OpenAI documentation, lifecycle and systems standards, primary engineering reports, protocol specifications, official Rust/Tokio/Cargo/OpenTelemetry sources, original research, and the user-provided Design Judgment plugin. `EVIDENCE-MATRIX.csv` maps every source to an operational behavior. The strongest repeated findings are:

- prompt quality is only one part of a control architecture;
- simple workflows should precede adaptive loops, graphs, durability and multiple agents;
- skills benefit from focused jobs and progressive disclosure;
- model judgment should be separated from deterministic policy, state, permissions, budgets and effects;
- evaluation must include trajectory, recovery and safety;
- durable effects require idempotency/reconciliation;
- Rust agent systems need typed domain/effect boundaries plus structured concurrency and fault testing;
- offline evaluation is preflight evidence, while controlled representative use is needed to expose workflow, intervention, effect, and adoption failures;
- full-lifecycle assurance needs explicit decision rights, evidence thresholds, feedback paths, and retirement obligations rather than phase-gate theater.

## 3. Divergent package directions considered

### A. One comprehensive master skill

Advantages: one invocation and one document.  
Rejected because: large always-on instructions harm selection/context economy, mix unrelated jobs, and make negative triggering difficult.

### B. A full runtime plugin with hooks, MCP servers and a Rust framework

Advantages: more automation and executable integration.  
Rejected because: it silently chooses privileges, credentials, framework/runtime, protocol versions and deployment assumptions for arbitrary repositories. It creates supply-chain and safety obligations unrelated to the decision-support goal.

### C. Router plus focused skills, references, assets and deterministic validators

Advantages: precise activation, progressive disclosure, inspectability, portability, least privilege, and reusable deliverables.  
Selected.

## 4. Commitment

The plugin contains 27 independently routable skills: one cross-layer architecture router, one lifecycle orchestrator, and 25 focused companion skills. It ships no default connector, hook, background service, telemetry backend, or framework dependency. Deep material lives in 106 skill-local and 15 shared references. Templates, schemas, and adaptable Rust modules turn recommendations into durable contracts. Scripts enforce structural, evidence, routing, lifecycle, schema, and packaging integrity without performing project effects.

## 5. Interaction contract

The router first identifies the failed outcome, implicit decision and responsible layer. It then selects the smallest fitting topology and invokes companion skills only for consequential sub-decisions. Every skill returns a named engineering artifact, calls out common failures, and requires facts/assumptions/decisions/residual risks to remain distinct. Completion requires acceptance evidence.

Skills are allowed to make reversible, repository-consistent assumptions. They require escalation at public-contract, dependency, data, privilege, production, cost, external-effect, destructive, or product-defining boundaries.

## 6. Rust commitment

Rust is split into architecture, runtime, durability, protocols and verification. This prevents a provider SDK, Tokio mechanics, persistence platform or MCP/A2A wire type from becoming the whole architecture. The included code demonstrates boundaries but deliberately avoids version pinning or claiming a compiled library.

## 7. Verification

Mandatory release gates check plugin and marketplace structure, manifest/frontmatter, 27 unique skills, metadata budget, 106 nonempty skill-local references, 15 shared references, internal links, 125-source evidence consistency, scenario/behavior/routing/lifecycle coverage, JSON Schema validity, placeholder/secret absence, Rust anti-patterns, file hashes, archive safety, and calibrated confidence.

The package also supplies—but does not claim to have executed—a blind GPT-5.6 Sol baseline/candidate A/B and a downstream Rust compile/test matrix. Their absence is included in confidence rather than hidden.

## 8. Version 2 expansion commitment: field learning and lifecycle assurance

The expansion considered three directions:

1. append one large “product lifecycle” section to the original router;
2. add a production telemetry runtime with opinionated services and dependencies;
3. add focused progressive-disclosure skills, shared decision models, typed assets, evidence contracts, and deterministic release gates.

The third direction was selected. One monolithic lifecycle skill would overload activation and context, while a runtime would introduce permissions, infrastructure assumptions, dependency churn, and a false claim that one implementation fits all products. Focused skills let Codex load only the relevant decision procedure while the umbrella lifecycle skill preserves continuity across stages.

The expansion makes two systems explicit:

- **controlled field learning:** learning charter, representative work, operating envelope, progressive exposure/autonomy, task/trajectory/effect/outcome/intervention evidence, privacy, causal limits, stop rules, and evidence-to-change records;
- **lifecycle assurance:** iterative decisions, owners, artifacts, evidence, readiness thresholds, feedback paths, and retirement obligations from discovery through operations.

The package remains advisory and artifact-generating rather than privileged. It ships no default production collector, feature-flag provider, deployment controller, identity system, or network integration. Those choices depend on the host product and must be version-pinned and authorized downstream.

## 9. Version 2 release evidence

The expansion is releasable only when:

- R71–R125 are present, mapped, and cited;
- all twelve new skills have unique positive and negative activation boundaries;
- every new skill has four focused references, a named deliverable, three scenarios, four positive/overlap routes, one negative route, a behavior contract, and a capability map;
- field-learning templates and schemas encode operating envelope, observations, metrics, experiments, decisions, and evidence;
- Rust assets encode typed observations, rollout decisions, and telemetry policy without claiming compilation;
- all original and expanded validators pass;
- the exact ZIP matches the source tree and passes the release gate after clean extraction;
- residual live Sol, product-pilot, and Rust-toolchain uncertainty is disclosed rather than scored as executed evidence.

## 10. Version 3 commitment: governed adaptation and proportional assurance

The version 3 audit rejected simply adding more specialist skills to the version 2 package. That would have increased conceptual coverage while risking Codex discovery truncation and overlapping authority. The selected design changes the package shape:

- no internal implicit gateway; the external Harness UltraGoal gateway owns first entry;
- 29 explicit specialists;
- trigger-only descriptions totaling 2,346 characters;
- advisory core, lifecycle, Rust, and full profiles;
- deterministic context-budget and profile gates.

Three new disciplines are first class:

1. **Engineering Learning Loop** — one provenance-bound learning at a time, mechanism attribution, counterevidence, smallest intervention, held-out/mutation/evolution evaluation, authority handoff, expiry, supersession, and retirement.
2. **Verification Strategy Engineering** — no-change proof and proportional selection among test-first, characterization, property, fault, concurrency, browser, migration, rollout, and field evidence.
3. **Product Fitness Engineering** — representative user value, full journeys, intervention, recovery, near misses, supervisory work, continuance, and evidence-bounded product claims.

The package also adds typed coordination and evidence contracts: No Change Decision, Task Evidence Packet, Review Verdict, Repair Loop Contract, Learning Adoption Record, Verification Mode Contract, and Skill Evaluation Case.

## 11. Version 3 rejection boundaries

The plugin does not adopt:

- mandatory skill invocation on a remote possibility of relevance;
- brainstorming or approval gates for every small change;
- TDD as the only legitimate proof method;
- universal fresh-subagent and multi-review execution;
- unbounded repair or review/fix loops;
- a second lifecycle, goal, plan, effect, evidence, claim, or knowledge authority beside the host root;
- activity, token reduction, command count, reviewer consensus, or telemetry presence as standalone product evidence.

Compound Engineering and Superpowers are treated as mechanism and failure evidence, not runtime dependencies or peer roots.

## 12. Version 3 release evidence

Release requires 14 deterministic source gates, 151 cited sources, 90 scenarios, 143 routing cases, 31 behavior contracts, 30 capability maps, 17 schemas, 11 Rust modules, and a calibrated confidence above 95. The exact archive must be checked separately after clean extraction. Live Sol behavior, real Product Fitness, and Rust compilation remain downstream evidence and are never inferred from package structure.
