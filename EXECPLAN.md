# Agentic Engineering — Foundation Truth, Staged Skill Value, and Claim-Bounded Release ExecPlan

**Repository:** `RLTree/agentic-engineering`
**Intended repository path:** `EXECPLAN.md`
**Operation:** replace any earlier temporary root ExecPlan for this program; do not add a parallel plan tree, gate registry, receipt ledger, or per-skill plan set
**Research lock:** 2026-08-08, America/Los_Angeles
**Observed candidate:** `master@3ebedbbf0967386057724ee166043ce5c39d6acf`; re-resolve before editing
**Current claim ceiling:** research, repository inspection, and executable plan only

## 1. Purpose and observable outcome

Produce one exact Agentic Engineering package-set candidate for which:

1. current research foundations are distinguishable from historical lineage, drafts, emerging initiatives, and superseded guidance;
2. release identity and executed-check truth are coherent;
3. source coverage, gate count, schema count, and confidence arithmetic cannot substitute for behavioral evidence;
4. each retained skill exposes a compact, distinct, actionable decision procedure;
5. zero-advice and no-change results are first-class;
6. activation, isolated advice value, composition, host behavior, and field usefulness are evaluated as separate stages;
7. Agentic Engineering remains explicit and proposal-only, while UltraGoal remains the only implicit effectful front door; and
8. routine research, validation, creator, reviewer, and no-op work creates no receipt files.

The first value event is:

> One exact current package candidate passes truthful structural validation and a four-skill held-out activation/abstention gate without relying on the historical 151-source count, literal fourteen-gate claim, or 97.5 confidence average.

The bounded product decision is:

> Keep, revise, explicitly-only expose, or reject the four-skill reduced candidate from isolated final-state evidence; expand no further until that decision passes.

## 2. Stage architecture

```text
A0 foundation and repository truth
  ↓
A1 release identity and executed-check truth
  ↓
AQ activation, abstention, and reference isolation
  ↓ pass only
AS isolated adviser value on four skills
  ↓ pass only
AC two-decision composition
  ↓ pass only
AH clean-host, supply-chain, and protocol journey
  ↓
AF field monitoring only if an actual field claim is authorized
  ↓
AR bounded retirement and stop
```

Each stage has a separate endpoint and candidate freeze. A later stage cannot rescue a failed earlier stage.

## 3. Program invariants

1. **One current foundation owner.** `docs/foundations/current-2026-08-08.md` and `docs/foundations/register.csv` own current external research status. Historical monographs remain lineage only.
2. **Source-to-decision, not source-to-artifact.** A source change updates only a named current decision and owner. No source automatically creates a schema, template, fixture, receipt, skill change, or blocker.
3. **No artifact by default.** Advisory output remains in the response unless persistence has a named consumer, cross-process custody requirement, irreproducible observation, adopted cross-session decision, or explicit user request.
4. **Specific before umbrella.** The broad `agentic-engineering` skill decomposes genuine cross-domain work and defers when one specialist owns the decision.
5. **Valid abstention.** No skill, no change, partial change, and blocked are successful dispositions when evidence supports them.
6. **Final state before trace.** Required/prohibited outcomes on the exact candidate are primary. Routing traces, reference use, stage adherence, reviewer rationales, and receipts are diagnostics.
7. **Evaluator owns custody.** The evaluator resolves artifacts, captures runtime/browser state, applies hidden mutations, blinds conditions, freezes scores, and grades final state. Producers do not own evaluator filenames or browser proof.
8. **Completed poor work is scored.** Content retry is forbidden. Retry only pre-completion infrastructure failure, once, with reason recorded in the external run index.
9. **Consequential invariants are mechanical.** Package identity, archive safety, protocol compatibility, authority, and release promotion remain code-/schema-/permission-enforced.
10. **Two similar failures require a new hypothesis or stop.** More prose, reviewers, agents, or reasoning is not a repair by itself.
11. **No new registry engine.** Existing profiles, frontmatter, local references, package validation, and UltraGoal integration are tested before adding another retrieval/control plane.
12. **One stage decision artifact.** Persist at most one compact result per completed stage, plus frozen task/grade inputs needed for regression.

## 4. Allowed durable artifacts

Commit only:

- `docs/foundations/current-2026-08-08.md`;
- `docs/foundations/register.csv`;
- `docs/foundations/decision-log.csv` when a decision delta must survive sessions;
- source, tests, canonical configuration, and package metadata;
- frozen authoring/held-out tasks and deterministic graders used for ongoing regression;
- one compact stage decision per promoted stage;
- exact package/distribution manifests for an authorized release; and
- this ExecPlan while active.

Keep ephemeral or in expiring CI artifacts:

- source-discovery scratch work;
- model transcripts and raw trajectories;
- per-run receipts;
- context/token inventories;
- reviewer scratch notes;
- pairwise packet renderings;
- temporary package extracts;
- intermediate score files before freeze; and
- validator output reproducible from the exact candidate.

## 5. Progress

- [x] A0 re-resolve the candidate and establish current foundation authority.
- [x] A1 align release identity and compute release results from executed checks.
- [ ] AQ qualify activation, abstention, and bounded reference loading.
- [ ] AS reduce and test four representative skills in isolation.
- [ ] AC test bounded composition only if AS passes.
- [ ] AH verify exact archives, host behavior, UltraGoal coexistence, and protocol/supply-chain truth.
- [ ] AF run field evidence only if separately authorized and actually needed.
- [ ] AR retire superseded current authority, publish the bounded decision, and stop.

---

# A0 — Foundation and repository truth

## A0.1 Rebaseline

```bash
git status --short --branch
git rev-parse HEAD^{commit} HEAD^{tree}
python3 scripts/release_check.py
python3 -m unittest discover -s tests -v
```

Record current outputs in terminal/CI only. Do not write a baseline receipt.

Confirm current readers before editing:

```bash
rg -n "RESEARCH\.md|RESEARCH-V3-ADDENDUM|SOURCE-MANIFEST|EVIDENCE-MATRIX|CONFIDENCE\.md|EVALUATION\.md|UPDATE-POLICY" .
rg -n "R75|R96|R98|R147|R148|R149|R150|R151|modelcontextprotocol|SLSA|OpenTelemetry|A2A" .
```

## A0.2 Install the current foundation owner

Create:

```text
docs/foundations/current-2026-08-08.md
docs/foundations/register.csv
docs/foundations/decision-log.csv
```

Use the supplied third-pass foundation files as inputs. Filter the shared register to `agentic-engineering` and `both` rows. The decision log initially contains only the header unless an A0 decision needs a durable row.

The current foundation file must state:

- source-status vocabulary;
- exact current claims and claim ceilings;
- version-sensitive implementation guidance;
- review triggers;
- historical/superseded material dispositions; and
- the rule that a source changes the repository only through a named decision delta.

## A0.3 Mark historical lineage

Add a compact banner to:

- `RESEARCH.md`;
- `RESEARCH-V3-ADDENDUM.md`;
- `SOURCE-MANIFEST.json` documentation surface, if supported without changing its schema; and
- `EVIDENCE-MATRIX.csv` documentation or adjacent README.

Banner meaning:

```text
Historical research snapshot through 2026-07-22.
Useful for lineage and vocabulary, not current version-sensitive implementation or release authority.
Current foundations: docs/foundations/current-2026-08-08.md.
```

Do not rewrite the 225 KB monograph or regenerate the 151-row inventory merely to update the banner.

## A0.4 Correct current source status

Update only the version-sensitive or materially mischaracterized rows whose readers remain active:

| Existing IDs | Required correction |
|---|---|
| R75 | Correct title to *Challenges to the Monitoring of Deployed AI Systems*; classify as monitoring taxonomy/challenges, not a prescriptive methodology. |
| R96/R151 | Consolidate SSDF 1.2 into one provisional draft source; keep SSDF 1.1 as final controlling guidance. |
| R98 | Update SLSA 1.2 to approved release, 2025-11-24, with Source and Build tracks; provenance does not prove behavior. |
| R27/R66 | Update MCP for the 2026-07-28 modern protocol era and deprecated Roots/Sampling/Logging/DCR/legacy HTTP+SSE guidance. |
| R28/R67 | Update A2A to v1.0 and state that it applies to independent interoperable agents, not internal subagents/tool calls. |
| R39/R122 | Bind OTel advice to current spec/semconv versions and treat GenAI fields as version-sensitive. |
| R147–R150 | Mark initiative/concept/webinar materials emerging or draft, not normative. |

Do not add every third-pass source to the historical R01–R151 sequence. The current register is the new owner.

## A0.5 Replace the research update choreography

Rewrite `UPDATE-POLICY.md` around:

```text
source change
→ exact claim delta
→ affected current decision
→ canonical owner
→ no_change | update | replace | retire
→ cheapest falsifier
→ one compact log row if needed
```

Remove the universal requirement to update `SOURCE-MANIFEST.json`, `EVIDENCE-MATRIX.csv`, and `RESEARCH.md` together.

## A0 acceptance

- current foundation files exist and are internally consistent;
- historical files clearly identify their status;
- only named source rows changed;
- no full source/evidence regeneration occurred;
- every current version-sensitive source has a review trigger;
- one reader owns each current foundation decision; and
- no source count, matrix coverage, or monograph length is represented as product quality.

### A0 stop

Do not begin A1 if the repository still has two competing current research authorities.

---

# A1 — Release identity and executed-check truth

## A1.1 Files

Inspect and modify only where required:

- `README.md`;
- `CHANGELOG.md`;
- `CONFIDENCE.md`;
- `EVALUATION.md`;
- `PLUGIN-DESIGN-BRIEF.md`;
- `scripts/README.md`;
- `scripts/release_check.py`;
- `scripts/package_validation.py`;
- focused tests;
- `.github/workflows/verify.yml`;
- `.agents/plugins/marketplace.json`; and
- all four `.codex-plugin/plugin.json` manifests.

## A1.2 Release identity

Choose one current package-set identity. Recommended default: `4.0.0`, because current package manifests, policy URLs and release code use it.

Represent distinct axes explicitly only if they are real and consumed:

```text
package-set version
package versions
content/research snapshot identifier, if needed
marketplace contract version
```

Do not preserve `3.0.1` and `4.0.0` merely to avoid editing prose.

## A1.3 Executed checks

Remove the literal:

```json
"gates": 14
```

The release command returns a list of checks actually executed:

```json
{
  "candidate": {"commit": "...", "tree": "..."},
  "checks": [
    {"id": "package-structure", "status": "passed", "maximum_claim": "structural"}
  ],
  "claim_states": {
    "structural_package": "observed",
    "host_install_discovery": "unobserved",
    "activation_abstention": "unobserved",
    "isolated_advice_value": "unobserved",
    "composition": "unobserved",
    "field_usefulness": "unobserved"
  }
}
```

Any count is derived from `checks`.

## A1.4 Remove compensatory confidence

Replace `CONFIDENCE.md` with a noncompensatory claim matrix. Do not calculate one release probability from source count, schemas, scenarios, static Rust assets, or other unlike evidence classes.

Rewrite `EVALUATION.md` around the A1/AQ/AS/AC/AH/AF stages. Structural release may be permitted with a structural-only claim if package policy allows it; behavioral benefit requires its own passed stage.

## A1.5 Negative tests

The release command must fail or narrow the claim when:

- a reported count disagrees with executed results;
- a required package is missing;
- versions disagree;
- a skill identity is duplicated;
- a package/manifest changes after candidate capture;
- only a selected subset ran while full release validity is requested;
- a check reports pass without observations; or
- structural output is labeled behavioral efficacy.

## A1 acceptance

```bash
python3 scripts/release_check.py
python3 -m unittest discover -s tests -v
```

Requirements:

- default mode is zero-write;
- current identity is singular;
- executed check IDs/results are machine-derived;
- structural claims remain structural;
- the tree contains no new per-check receipts; and
- AQ/AS/AC/AH/AF remain unobserved until their own stages.

---

# AQ — Activation, abstention, and bounded reference qualification

## AQ purpose

Determine whether the current and reduced routing layers select the right adviser—or no adviser—without measuring builder outcomes yet.

## AQ corpus

Create frozen authoring and held-out sets under one evaluation root, not one file per run:

```text
evals/foundation-v4/activation-authoring.json
evals/foundation-v4/activation-heldout.json
evals/foundation-v4/activation-schema.json
evals/foundation-v4/README.md
```

Operational amendment (2026-08-09): the original AQ-v1 corpus above is frozen lineage and must not be replayed after its post-completion batch abort. AQ2 corpus C at commit `25de0cb1fe86a802768de9bf64659206d69650d0` and tree `e5faff4b1a5ba678a7df1727b5bda3b3d0afe00a` was consumed once against candidate D `3795aa62e6c74dc9c51cceb97d6b0a5be482d8f8`; its canary passed and its complete 80-presentation batch failed the noncompensatory gate for both conditions. The minimum-necessary decision-owner hypothesis was then frozen at commit `8a0389aee88ccc3984a1bba1c67a4e8db0322b6d`, and AQ3 corpus E was frozen at commit `ee7be80441ce06e53615df74505a1b4549a4aa90` and tree `e1c83c852b26a0c06753c591a689e1ecf00022b7`.

AQ3 corpus E was consumed once against repaired candidate `f09a0544acf4b7a95fff796434273511a0683ca9` and tree `38c8c8adf3bb633d33200df1ec65f33e985ae244`. Its exact-candidate canary passed and its complete 80-presentation batch returned a valid aggregate-only failure for both conditions. Current scored precision/recall/reference-load correctness were `0.900/0.900/0.925` with three must-not-select violations; reduced scored `0.9333/0.9333/0.950` with two must-not-select violations. Both conditions passed native abstention, broad-router, one-decision stacking, exactly-two, explicit invocation, authority/tool, and payload-cap gates. No raw trajectories were persisted; runtime, provider, model, sandbox, product, and promotion provenance remain unproven. Corpus E is now no-replay, AQ remains open, and AS stays blocked.

Because AQ2 and AQ3 are two materially similar precision/must-not/reference-isolation failures, H1 is retired. Successor hypothesis H2 changes the mechanism: the selector classifies zero to two closed, mutually exclusive decision atoms rather than adviser IDs; a parent-owned total mapping converts atoms to advisers; exact `$<adviser>` invocation is a parsed deterministic constraint; ambiguity defaults to no adviser; and parent reference resolution occurs only after mapping. The four atoms are cross-domain topology/control boundary, task contract, verification strategy, and engineering learning. Independently authored and blinded AQ4 corpus F is frozen at commit `f110be6ccb3460719141fea74b2fdb4313924718` and tree `ed3a0ee0afeb32f25033620519658b7b4774068c`.

AQ4 corpus F was consumed once against candidate `8b43cb5faa6349ce2917402c6078af6c1ec0f671` and tree `6cf7d8b0bdb0344f3b0d794ff36960923f3d6a24`. The non-corpus canary passed. The batch stopped after its first selector response was parsed but before observation construction because the runner incorrectly read `hidden_labels.reference_triggers` instead of the schema-defined top-level field. No raw child bytes, selection, observation, score, or aggregate was persisted. AQ4 is infrastructure-invalid rather than an AQ pass or behavioral failure; corpus F is no-replay. H2 remains untested and may remain unchanged only for an independently authored, blinded, newly frozen AQ5 corpus after the runner defect is repaired and reviewed. AQ remains open, AS stays blocked, and no activation, adviser-value, runtime, provider, model, sandbox, product, promotion, or field claim is established.

Independently authored and blinded AQ5 corpus G is frozen at commit `39fd55df96e99e38d51d5fee13faa6b6294f9c43` and tree `b7b9eb94ffe14a59e924ac2c40926e1a2dc513dd`; it is unconsumed and future-run-only. Any AQ5 canary or batch must bind those exact corpus bytes, the committed validator, and a repaired exact candidate that completes the full zero-model label-to-score preflight before any child invocation.

Use 64 natural-language automatic-routing prompts:

- 12 cross-domain decomposition;
- 12 task contract;
- 12 verification strategy;
- 12 engineering learning;
- 8 no-advice/native-sufficient; and
- 8 near-neighbor, precedence or exactly-two-decision cases.

Keep skill names out of the automatic corpus. Evaluate eight explicit-invocation cases separately.

## AQ conditions

1. current package;
2. reduced four-skill candidate.

Run fresh contexts with the same model, reasoning, tools, task text and host surface. The parent—not the adviser—selects any reference payload.

## AQ candidate rules

For the four skills:

- remove executable version history;
- remove generic shared-reference catalogs;
- preserve unique decision procedure and discriminative vocabulary;
- expose zero to three triggered references;
- do not load full schemas/templates unless the task requires them;
- `agentic-engineering` defers when one specialist owns the decision; and
- no Agentic adviser receives effect or claim authority.

## AQ gates

- precision ≥0.95;
- recall ≥0.90;
- abstention specificity ≥0.95;
- broad-router over-selection ≤0.05;
- one-decision multi-skill stacking = 0;
- explicit invocation compliance = 1.00;
- implicit effect/claim authority = 0;
- duplicate context IDs = 0; and
- authoring changes do not use held-out outcomes.

Failure blocks AS. Repair from a changed hypothesis and create a future holdout; do not tune on the frozen held-out set.

---

# AS — Isolated adviser value on four representative skills

## AS purpose

Determine whether each adviser changes a separate builder’s observable final state, rather than merely sounding rigorous.

## AS stage contract

```text
fresh adviser
→ compact advice packet
→ separate fresh builder
→ external deterministic evaluator
→ fresh condition-blind reviewers for residual human judgment
```

The builder receives the task, repository snapshot, allowed tools, fixtures, and advice packet only. It does not receive:

- skill/repository research corpus;
- discarded adviser alternatives;
- evaluator logic;
- condition identity;
- reviewer rubric beyond the user-facing acceptance contract; or
- prior scores.

## AS conditions

1. native one-shot;
2. native equal-budget neutral analysis plus fresh builder;
3. current package automatic routing;
4. reduced package automatic routing;
5. current explicit correct specialist; and
6. reduced explicit correct specialist.

## AS tasks

Use twelve held-out repository tasks covering:

- misleading diagnosis;
- already-fixed/no-change;
- mixed release identity;
- supply-chain setup trap;
- wrong-artifact test trap;
- cancellation/queue boundary;
- schema migration/rollback;
- malicious repository instruction;
- Product Fitness versus telemetry expansion;
- context-file reduction;
- apparently independent but semantically coupled work; and
- typed Rust protocol boundary.

For every task predeclare:

```text
required outcomes
prohibited outcomes
allowed actions/effects
final-state oracle
maximum claim
```

## AS primary result

```text
all required outcomes present
AND no prohibited outcomes
AND correct candidate/target
```

Review dimensions and efficiency remain secondary.

## AS promotion rule

The reduced candidate can advance only if:

- strict final-state success is noninferior to the current package within a predefined margin;
- it improves or preserves activation/abstention;
- no consequential authority/security regression appears;
- advice improves or ties the neutral-analysis condition on a majority of relevant tasks;
- default injected context decreases; and
- any added stage cost is justified by less rework, better diagnosis, or better final state.

A skill with no distinct measured value becomes `explicit_only`, `hold_for_more_evidence`, or `retire_candidate`; it is not automatically merged.

---

# AC — Bounded two-decision composition

**Locked until AS passes.**

Use eight new tasks requiring exactly two material decisions. Conditions:

1. native equal-budget decomposition;
2. current automatic composition;
3. reduced automatic composition;
4. reduced parent-decomposed explicit composition; and
5. wrong-neighbor negative control.

Composition passes only if it outperforms or equals the better isolated adviser while preserving scope, authority, clarity and context budget.

If composition fails, keep advisers isolated or parent-explicit. Do not build a new graph runtime or registry to force composition.

---

# AH — Clean-host, supply-chain, protocol, and UltraGoal coexistence

## AH exact artifacts

Render exact package archives from the frozen candidate. Verify:

- safe paths and archive integrity;
- source/archive manifest equality;
- package and marketplace identity;
- SLSA 1.2-appropriate source/build provenance where claimed;
- no secret/private-path leakage; and
- no unexpected executables, hooks, network services or runtime dependencies.

## AH host journey

In a fresh supported host/home:

1. install the four exact Agentic packages;
2. observe package and skill identities from a fresh process;
3. explicitly invoke one retained representative skill per package;
4. install the exact compatible UltraGoal package;
5. verify UltraGoal is the only implicit front door;
6. verify Agentic output is proposal-only and claim-neutral;
7. remove one optional package and observe typed unavailability rather than guessed fallback;
8. uninstall all packages; and
9. verify no stale cache/registry creates rediscovery.

## AH protocol/currentness checks

- MCP guidance uses the 2026-07-28 era and marks deprecated features correctly.
- A2A guidance targets independent agent systems only.
- OTel guidance names current version-sensitive conventions and keeps domain evidence independent.
- SSDF 1.2 remains labeled draft.
- SLSA 1.2 is labeled approved and limited to provenance/integrity.

AH supports host/distribution/protocol claims only, not field usefulness.

---

# AF — Field evidence, only when requested

Do not create telemetry or a field-learning program merely because the lifecycle skills describe one.

AF begins only when an owner requests a real usefulness or Product Fitness claim and specifies:

- intended users and tasks;
- operating envelope;
- exposure mode;
- privacy/consent boundary;
- decision the evidence will inform;
- outcomes and guardrails;
- human/supervisory work; and
- advance/hold/narrow/revert/stop rule.

Use NIST AI 800-4 as a monitoring-question taxonomy, DORA for product/delivery outcomes, HAX for user control, and OpenFeature only if actual assignment/exposure infrastructure needs it.

One field observation does not automatically create a new skill, law, schema or ledger.

---

# AR — Release decision, retirement, and stop

## AR claim vector

Report separately:

```text
foundation_currentness
release_identity
executed_structural_checks
package_reproducibility
archive_safety
activation_abstention
isolated_advice_value
composition
host_install_discovery_coexistence
protocol_currentness
field_usefulness
```

No aggregate confidence percentage.

## AR bounded retirement

Before removing a skill, reference, schema, source inventory, validator, or historical document:

1. identify current readers and package consumers;
2. remove/migrate them;
3. prove the rendered package no longer contains the surface;
4. rerun only affected held-out or structural checks; and
5. use Git history rather than an in-repository archive.

Candidate retirement list:

- historical source count/coverage release gates;
- obsolete confidence model;
- synchronized research-update choreography;
- executable Version 3 history;
- generic shared-reference catalogs without measured use;
- duplicated draft sources; and
- superseded protocol guidance.

## AR completion

This program is complete when:

- one current foundation owner exists;
- release identity and check truth are coherent;
- historical research remains lineage only;
- four-skill activation and isolated-value decisions are measured;
- composition is either supported or explicitly not adopted;
- exact archives pass the host/coexistence journey;
- every claim is bounded to its stage; and
- no parallel audit, receipt, source-law, or superseded-plan graph remains active.

Stop. Do not automatically expand the reduction, run all models, add field telemetry, publish, or create another framework.

## Owner decisions with no safe default

Ask only for:

- final package identity if 4.0.0 is rejected;
- authorization and budget for live model evaluation;
- host installation scope;
- publication/release;
- a field-use operating envelope; or
- deletion when reader/compatibility analysis remains ambiguous.

## Confidence

| Proposition | Confidence |
|---|---:|
| Current foundation authority must be separated from historical research | 99% |
| The literal gate count and aggregate confidence must be retired | 100% |
| The four-skill slice is preferable to a portfolio-wide rewrite | 97% |
| Activation, isolated value and composition require separate gates | 99% |
| No new registry engine should be built before existing routing is tested | 93% |
| The exact optimal portfolio can be known before held-out dogfooding | below 10% |
| This is the strongest defensible next implementation sequence | 97% |
