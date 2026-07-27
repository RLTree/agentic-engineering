# Evaluation Strategy

## Release question

Does Agentic Engineering 3.0 provide a coherent, research-supported, falsifiable mechanism for improving Codex decisions and outcomes across agent architecture, authentic use, the full product lifecycle, software delivery, Product Fitness, evaluation, security, and agentic Rust—and is the distributed package itself valid and low privilege?

## 1. Discovery and activation

`validate_plugin.py`, `validate_official_contract.py`, `check_context_budget.py`, and `check_profiles.py` enforce:

- 30 unique trigger-only descriptions beginning with `Use when`;
- no internal implicit gateway; the external Harness UltraGoal gateway owns first entry;
- explicit specialist skills with local progressive-disclosure references;
- a 7,600-character description release limit and an 8,000-character conservative rendered fallback limit;
- four advisory active-skill profiles: core, lifecycle, Rust, and full;
- no default hooks, connectors, MCP servers, executables, or hidden network services.

The exact release measured 2,346 description characters and a conservative rendered estimate of 3,880 characters.

## 2. Evidence and mechanism traceability

`SOURCE-MANIFEST.json` and `EVIDENCE-MATRIX.csv` map 151 sources to operational changes. `evaluate_evidence.py` checks:

- contiguous R01–R151 identifiers;
- exact source-to-CSV correspondence;
- complete citation from `RESEARCH.md`;
- evidence-class ratios;
- source-to-skill coverage;
- a consolidated synthesis above 26,000 words.

The version 3 addendum covers current Codex skill and GPT-5.6 guidance, skill evaluation, Compound Engineering and Superpowers, DORA, NIST, no-change behavior, repair loops, structured feedback, harness repair, contextual verification, browser acceptance, mock quality, file-backed context, developer supervisory work, human-centered collaboration, productivity heterogeneity, identity, measurement, and continuous security.

## 3. Behavioral, routing, and overlap coverage

The release includes:

- **90** engineering scenarios across 30 domains;
- **143** routing cases: 87 should-invoke, 30 should-not-invoke, and 26 overlap;
- **31** behavior contracts: one global and one per skill;
- **30** capability maps joining deliverables, sources, references, scenarios, routes, and required capabilities.

Every skill has at least three positive scenarios, four positive/overlap routes, and one negative route. This corpus establishes intended behavior and routing coverage; it is not represented as a live Sol activation result.

## 4. Version 3 anti-gaming evaluation

Consequential skill changes should use `evals/run-skill-behavior-ab.md` and `assets/schemas/skill-eval-case.schema.json` to compare a prior version or no-skill baseline with the candidate across:

- explicit invocation;
- implicit gateway selection;
- contextual selection;
- negative and overlap cases;
- missing access;
- small and consequential work;
- already-fixed/no-change work;
- attempts to satisfy a visible proxy while missing the outcome.

The evaluation separately grades activation, following, composition, recovery, verified outcome, authority compliance, safety, style, and efficiency. Consequential rules add held-out, semantic mutation, and specification-evolution splits.

## 5. No-change and repair-loop study

`evals/run-no-change-and-repair-study.md` evaluates:

- correct abstention on already-fixed work;
- avoidance of premature abstention on partially fixed work;
- repair gain by attempt number;
- whether each attempt changes a material mechanism or gains evidence;
- structured feedback completeness;
- repeated-mechanism circuit breaking;
- rollback and human escalation for ambiguous effects.

The plugin does not hardcode a universal attempt count. It requires the project to calibrate a budget and enforces a semantic stop when iterations repeat without new evidence.

## 6. Verification strategy

`verification-strategy-engineering` returns a candidate-bound `Verification Mode Contract`. It distinguishes:

- current-behavior/no-change proof;
- test-first and characterization-first work;
- unit, contract, integration, and end-to-end evidence;
- property, invariant, state-machine, model-based, differential, metamorphic, and mutation testing;
- concurrency, cancellation, saturation, fault, crash, retry, recovery, browser, journey, accessibility, performance, security, migration, rollout, and field evidence.

The contract records oracle limitations, mock policy, real-boundary evidence, freshness, repair budget, acceptance evidence, and claim ceiling. This avoids both universal TDD and verification-free implementation.

## 7. Product Fitness and controlled field evidence

`evals/run-product-fitness-pilot.md` and `evals/run-controlled-field-pilot.md` test the progression from replay and shadow work to recommendation, approval-gated action, and bounded autonomy.

Required evidence includes:

- intended user, job, context, value event, outcome, and continuance;
- representative-work sample and operating envelope;
- assignment versus actual exposure;
- task, trajectory, action, effect, outcome, intervention, recovery, and near-miss joins;
- supervisory time, review rounds, correction effort, cognitive load, trust, and recovery burden;
- privacy, sampling, retention, and cardinality controls;
- advance, hold, narrow, revert, stop, redesign, or gather-more-evidence decisions.

A Field Pulse is a read model. It cannot promote a product claim. Agent-use, expert-use, and human-use evidence remain separate.

## 8. Typed coordination and review

The new schemas and Rust assets encode:

- `TaskEvidencePacket`: candidate, goal, plan, task, lease, worker, model, context, disjoint path and semantic ownership, permissions, budgets, cancellation, verification, evidence, blockers, and residual risk;
- `ReviewVerdict`: candidate-bound scope, reviewer independence, evidence inspected, findings, unverifiable claims, decision, claim ceiling, and rerun conditions;
- `RepairLoopContract`: validator, attempt budget, hypotheses, mechanism classes, one changed variable, structured feedback, evidence gained, and circuit decision;
- `LearningAdoptionRecord`: provenance, operating envelope, evidence class, facts, interpretations, hypotheses, counterevidence, responsible layer, intervention, held-out evaluation, decision, expiry, rollback, and authority handoff.

Workers and reviewers remain advisory. The host root retains shared contracts, effects, migrations, claim promotion, and final acceptance.

## 9. Rust static and downstream verification

`check_rust_assets.py` checks 11 `.rs` modules, their README, and 17 closed draft-2020-12 schemas. It rejects unbounded Tokio channels, untracked OS threads, universal untyped JSON at contract boundaries, `unsafe`, and recoverable-path `unwrap` or `expect` in reusable examples.

`evals/run-rust-compile-check.md` and `evals/run-rust-observability-check.md` remain downstream protocols for formatting, compilation, tests, Clippy, release build, feature/target matrices, concurrency, fault, crash-point, schema, propagation, privacy, sampling, and exact-artifact evidence.

## 10. Exact package validation

The aggregate release gate writes `FILE-MANIFEST.sha256` and `evals/results/release-report.json`. Final archive validation must additionally prove:

- ZIP CRC integrity;
- one expected top-level directory;
- safe relative paths and no path traversal;
- no symlinks, bytecode, VCS, editor, or operating-system residue;
- source-to-archive SHA-256 equality;
- internal file-manifest equality;
- a clean-extraction repeat of all 14 source gates.

## Release rule

Release only when every mandatory gate passes and calibrated confidence is at least 95.0. Optional live checks may remain unexecuted only when the report identifies them, lowers the empirical-transfer component, and ships exact reproduction protocols.
