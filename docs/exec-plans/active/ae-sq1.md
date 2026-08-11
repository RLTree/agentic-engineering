# AE-SQ1 successor qualification program

Status: **F0 STATIC AUTHORITY FREEZE ONLY**
Program owner: repository owner
Program integrator: root conductor
Active-plan path: `docs/exec-plans/active/ae-sq1.md`
Machine-readable authority: `evals/ae-sq1/program-authority.json`
Authority date: 2026-08-10, America/Los_Angeles

## 1. Owner authorization and succession boundary

The owner authorizes **AE-SQ1** as a distinct successor program. AE-SQ1 starts
from its own prospective authority and namespace. It does not continue the
predecessor experiment.

AE-SQ1 is **not AQ10, H6, a retry, a resume, a reopen, a cure, or a
reinterpretation** of any predecessor task, mechanism, corpus, result, or
decision. No later AE-SQ1 observation can alter, cure, supersede, or weaken the
predecessor terminal record.

The predecessor program is immutable history at:

- commit `340b79399a987e6aad0d5435fa540a1db511489d`;
- tree `c47aeb3642d7fdcf90f47f990ddf3915f3cbb933`; and
- the exact Git paths, blobs, and raw SHA-256 digests closed in
  `evals/ae-sq1/program-authority.json`.

Only these predecessor terminal bits may cross the succession boundary:

1. the predecessor is terminal and stopped;
2. its successful-program conditions were not met;
3. its public release and promotion decision was negative; and
4. its artifacts remain immutable history.

No predecessor task text, case, corpus, prompt, candidate mechanism, diagnostic,
score, raw observation, aggregate result, inferred failure cause, or outcome may
be used to design, author, tune, select, score, retry, or interpret AE-SQ1. The
Git bindings preserve history; they are not AE-SQ1 design inputs.

The sole narrow exception is read-only inspection of the pinned H4 protocol at
commit `d6f9e6089e6e11f158a2d3bf4af717fc026548d4`, tree
`6b65ea1e125836c9ae684e869f1156e5750c7a0b`, path
`evals/foundation-v4/unresolved-decision-graph-protocol-v8.json`, blob
`5fe35b98dce5373d974d05ba3a29819605f5bc4f`, raw SHA-256
`a145766c475de5ed1411bc86467a1a82c3cdaa18782b772ef00901238f590fd5`.
That inspection may prove only that SLEC-1 is materially non-isomorphic to H4.
H4 mechanics and every predecessor outcome remain forbidden successor design,
tuning, scoring, or interpretation inputs.

The completed A0 foundation-currentness work and A1 structural package-identity
work are **revalidated imported prerequisites only**. AE-SQ1 does not rerun them,
promote their claims, or count them as successor stage results. A0 imports only
the current foundation authority bit. A1 imports only the exact structural
package-identity bit. Neither proves activation, isolated value, composition,
host behavior, field value, release readiness, or production behavior.

This F0 authorization permits the local static authority files named above.
Provisional noncanonical external-research, candidate, evaluator, and runner
drafts may coexist in the live worktree before F0. F0 makes none of them
authoritative. F1/F2 or later authority arises only after post-F0 exact review or
regeneration and a separately sequenced commit. This plan does not claim that
source collection or candidate drafting never occurred. F0 forbids heldout
authoring, model or corpus observation, downstream staging/commit, external
access, spending, publication, release, promotion, deletion, and migration.

## 2. Sole active stage graph

The sole active stage graph is:

```text
SQ1-AQ -> SQ1-AS -> SQ1-AC -> SQ1-AH -> SQ1-AF -> SQ1-AR
    |        |        |        |        |
    +--------+--------+--------+--------+----> SQ1-AR on any blocking failure
```

There are no other active stages or edges. Every blocking failure routes
directly to `SQ1-AR`. A later stage cannot compensate for, average over, cure,
reinterpret, or reopen an earlier failure. A stage may begin only after its
immediate predecessor has a closed passing result, except that `SQ1-AR` accepts
the direct failure edges above. `SQ1-AF` may close only as the omission described
in section 8.

## 3. Frozen program-wide rules

These rules freeze at F0 before any candidate or evaluator becomes canonical,
any heldout is authored, or any model/corpus observation occurs:

1. Exactly one fresh candidate may enter `SQ1-AQ`.
2. The candidate must be materially non-H4 and based only on independently
   collected external evidence frozen inside the AE-SQ1 namespace.
3. SLEC-1 is the fixed identifier for the owner-selected
   four-isolated-assessor mechanism; no acronym expansion is asserted here.
   The candidate must instantiate SLEC-1 without importing predecessor mechanism
   or outcome information.
4. The exact candidate bytes and complete evaluator contract, schemas, formulas,
   thresholds, schedule, condition adapter, and failure rules must freeze before
   either heldout split is authored.
5. Two authors independently create two 20-case heldout splits. Neither author
   may access the other split or any outcome while authoring. The frozen corpus
   therefore contains exactly 40 unique cases.
6. Every case is presented once under `current` and once under `reduced`, for
   exactly 80 presentations. No case/condition presentation may be duplicated,
   skipped, or replaced.
7. Each `SQ1-AQ` presentation is one four-capsule unit. It produces exactly four
   isolated assessor calls, each in a unique child context with no sibling
   transcript or state. The four outputs are joined only by the frozen
   deterministic parent evaluator after all four calls close.
8. There is exactly one non-corpus canary unit. It uses four isolated calls and
   no heldout text, labels, nonce, metadata, or derived content.
9. The first heldout-backed model invocation consumes both frozen splits
   immediately and irreversibly. The earlier non-corpus canary does not consume
   them because it contains no corpus material. Once consumed, the corpus is
   `NO_REPLAY` for every purpose, including debugging, repair, confirmation, or
   a successor candidate.
10. There is no post-observation retry. A completed weak, malformed, partial, or
    failing model output is scored as observed.
11. At most one infrastructure retry is permitted. It may repeat only the entire
    four-call non-corpus canary attempt, and only if the first attempt has zero
    completed child outputs and zero semantic child observations. Candidate,
    evaluator, prompt, schedule, model, reasoning, and runner input bytes must
    remain unchanged. A retry that launches calls counts all four calls. Any
    changed byte, any heldout retry, any observed child, or any second
    infrastructure failure routes to `SQ1-AR`.
12. Only one candidate-bound aggregate result may leave evaluator custody. Case,
    split, capsule, condition, assessor, gate, score, trace, transcript, and raw
    output results remain non-reportable.
13. Missing, skipped, undefined, non-finite, malformed, duplicate, extra, or
    unevaluable required values fail the noncompensatory global logical AND.
    Neither condition nor any later metric can compensate.
14. Predecessor data beyond the four terminal bits in section 1 are forbidden
    imports. Historical Git-object verification is allowed only to prove that
    the predecessor bytes remain preserved.
15. The model is exactly `gpt-5.5` with reasoning effort exactly `medium`.
    There is no model, provider, reasoning-effort, or mode fallback.
16. Static checks, a canary, and a successful process exit are evidence for only
    their named boundary. They do not establish a stage pass by themselves.

## 4. Exact model-invocation budget

| Stage | Normal plan | Absolute hard ceiling | Derivation |
|---|---:|---:|---|
| `SQ1-AQ` | 324 | 328 | four-call non-corpus canary + 80 x four calls; absolute adds one unchanged whole-canary retry after zero child observation |
| `SQ1-AS` | at most 108 | 156 | 12-task design below; independent frozen hard stop |
| `SQ1-AC` | at most 96 | 144 | 8-task design below; independent frozen hard stop |
| `SQ1-AH` | 0 | 0 | offline deterministic checks only |
| `SQ1-AF` | 0 | 0 | omitted absent separate authority |
| `SQ1-AR` | 0 | 0 | deterministic claim-vector closeout only |
| **All-pass program** | **624** | **628** | normal: 324 + 156 + 144; absolute adds only the qualifying four-call canary retry |

The maximum is a hard ceiling, not a target. Direct failure routing can reduce
actual use. No unused invocation may be transferred across stages, spent on a
retry, or used for diagnostics. A counter counts every attempted model
invocation, including an invocation that returns malformed content. The one
permitted zero-observation whole-canary retry adds four counted calls, producing
the 328 AQ and 628 program absolute ceilings.

## 5. Freeze points F0-F11

Freeze points are monotonic. A closed freeze may be replaced only by terminating
the program at `SQ1-AR`; it cannot be edited in place after downstream access.

| Freeze | Owner | Frozen surface | Must precede | Exit evidence |
|---|---|---|---|---|
| F0 | program owner + root conductor | this plan, program authority JSON, active-plan pointer, one decision-log row, predecessor Git bindings, stage graph, budgets, claims and prohibitions | all canonical candidate/evaluator authority, heldout authoring and model/corpus observation | strict authority tests and raw plan digest |
| F1 | external-evidence steward | post-F0 reviewed or regenerated independent evidence packet, provenance, independence attestation and admissibility decision | canonical candidate authority | closed committed evidence manifest; no predecessor task/result/outcome inputs |
| F2 | candidate steward | post-F0 reviewed or regenerated one materially non-H4 SLEC-1 candidate and exact current/reduced bytes | evaluator completion and all heldout authoring | committed candidate manifest, byte digests and structural reds |
| F3 | evaluator steward | evaluator, schemas, formulas, thresholds, four-capsule join, global AND, aggregate projection and budgets | both split authors receive the contract | closed evaluator manifest and mutation reds |
| F4 | split-A author | first independent 20-case split | combined-corpus freeze | split digest and blinded-author receipt |
| F5 | split-B author | second independent 20-case split | combined-corpus freeze | split digest and blinded-author receipt independent of F4 |
| F6 | corpus custodian | 40-case corpus manifest, validator, uniqueness proof, 80-presentation schedule and no-replay/run-index policy | canary and heldout execution | exact digests and zero-model validation |
| F7 | run custodian | exact run packet, four-call non-corpus canary receipt, invocation counter, unchanged-byte retry state and usage authorization | first heldout-backed model call | successful non-corpus canary and all-byte equality proof |
| F8 | aggregate scorer | sole AQ aggregate, consumption bit and direct pass/fail route | `SQ1-AS` or terminal closeout | one aggregate status/digest; no subaggregate disclosure |
| F9 | AS owner | exact AS tasks, adviser/builder isolation, evaluator and 156-call ceiling before AS observation; then its sole aggregate route | `SQ1-AC` or terminal closeout | isolated-value aggregate only |
| F10 | AC owner | exact two-decision composition tasks, evaluator and 144-call ceiling before AC observation; then its sole aggregate route | `SQ1-AH` or terminal closeout | bounded-composition aggregate only |
| F11 | AH/AF/AR owners | offline AH envelope, AF authority check, separated AR claim-vector schema and stop actions before AH execution | AH checks and final closeout | AH literal status, AF literal omission status and separated AR vector |

No freeze permits model execution by implication. The responsible owner must also
hold any separately required usage authorization at the run boundary.

## 6. Exact ownership lanes

| Lane | Owns | Must not access or change |
|---|---|---|
| Program owner | objective, F0 authorization, consequential exceptions | heldout cases, raw outputs, or outcome-driven contract changes |
| Root conductor | stage order, custody, counters, PASS/HOLD and direct failure routing | candidate authorship, split authorship, scoring discretion, release actions |
| External-evidence steward | F1 public-source provenance and independence packet | predecessor tasks, corpora, mechanisms, diagnostics, scores, results or outcomes |
| Candidate steward | one F2 SLEC-1 candidate from F1 evidence only | heldout cases, labels, author identities, model observations and predecessor nonterminal material |
| Evaluator steward | F3 schemas, formulas, thresholds, four-output join and aggregate projection | heldout cases and all model observations before freeze |
| Split-A author | only F4 split A | split B, candidate implementation internals beyond the frozen authoring contract, and all outcomes |
| Split-B author | only F5 split B | split A, candidate implementation internals beyond the frozen authoring contract, and all outcomes |
| Corpus custodian | F6 validation, digests, schedule, blinding and no-replay state | case editing, candidate/evaluator editing and result interpretation |
| Run custodian | F7 execution envelope, exact bytes, invocation counter and stop behavior | contract changes, content retries, scoring changes and raw-result publication |
| Aggregate scorer | F8 deterministic global AND and aggregate projection | candidate/evaluator/corpus changes and subaggregate disclosure |
| AS owner | F9 isolated adviser/builder stage | AQ reinterpretation, AC work before pass, and field/host claims |
| AC owner | F10 exact two-decision composition stage | AS reinterpretation, AH work before pass, and generalized composition claims |
| AH operator | F11 offline unprivileged disposable-home checks | network, credentials, production, installed user home, clean-host claim or privileged action |
| AF authority custodian | F11 check for a separately named privacy/consent/envelope authority | participant contact, data collection or inferred field authority |
| AR integrator | separated claim vector, immutable references, retention and stop | averaging claims, reopening stages, release, publication, promotion, deletion or migration |

One person or agent may fill multiple lanes only if the access boundaries remain
mechanically enforceable. Split A and split B authorship must remain independent.

## 7. Canonical namespace and file names

All new program artifacts live under `evals/ae-sq1/`. No AE-SQ1 artifact may be
written under `evals/foundation-v4/` or overwrite a predecessor path.

```text
docs/exec-plans/active/ae-sq1.md
evals/ae-sq1/program-authority.json
evals/ae-sq1/external-evidence.json
evals/ae-sq1/historical-task-digests.json
evals/ae-sq1/candidate-manifest.json
evals/ae-sq1/slec1-authority.json
evals/ae-sq1/slec1-capsule-schema.json
evals/ae-sq1/slec1-resolution-schema.json
evals/ae-sq1/slec1-reference-policy.json
evals/ae-sq1/aq/corpus-schema.json
evals/ae-sq1/aq/evaluator-schema.json
evals/ae-sq1/aq/gates.json
evals/ae-sq1/aq/metrics.json
evals/ae-sq1/aq/split-a.json
evals/ae-sq1/aq/split-b.json
evals/ae-sq1/aq/corpus-manifest.json
evals/ae-sq1/aq/run-manifest-schema.json
evals/ae-sq1/aq/run-manifest.json
evals/ae-sq1/aq/aggregate.json
evals/ae-sq1/as/schema.json
evals/ae-sq1/ac/schema.json
evals/ae-sq1/ah/stage-authority.json
evals/ae-sq1/ah/result.json
evals/ae-sq1/af/omission.json
evals/ae-sq1/ar/decision.json
scripts/resolve_ae_sq1_slec.py
scripts/check_ae_sq1_candidate.py
scripts/validate_ae_sq1_corpus.py
scripts/ae_sq1_run_index.py
scripts/run_ae_sq1_aq.py
scripts/score_ae_sq1_aq.py
scripts/run_ae_sq1_as.py
scripts/run_ae_sq1_ac.py
scripts/check_ae_sq1_ah.py
scripts/close_ae_sq1.py
tests/test_ae_sq1_program_authority.py
tests/test_ae_sq1_external_evidence.py
tests/test_ae_sq1_historical_task_digests.py
tests/test_ae_sq1_slec.py
tests/test_ae_sq1_corpus_contract.py
tests/test_ae_sq1_evaluator.py
tests/test_ae_sq1_run_index.py
tests/test_run_ae_sq1_aq.py
tests/test_check_ae_sq1_candidate.py
tests/test_ae_sq1_as.py
tests/test_ae_sq1_ac.py
tests/test_ae_sq1_ah.py
tests/test_ae_sq1_ar.py
```

At F0, only the active plan, program authority JSON, pointer update, one decision
row, and `tests/test_ae_sq1_program_authority.py` may be canonical, staged, or
committed. A reserved future path may coexist in the live worktree only as an
explicitly noncanonical uncommitted draft; its presence confers no authority and
it may not enter the F0 commit. No candidate, corpus, or model observation may
precede F0.

## 8. Stage-specific claim ceilings

### SQ1-AQ

`SQ1-AQ` may report only one exact-candidate aggregate status and its digest for
the frozen 40-case, two-condition, four-assessor SLEC-1 evaluation. It cannot
claim production routing, provider identity, runtime provenance, general
activation quality, product value, or release eligibility.

### SQ1-AS

`SQ1-AS` uses 12 fresh tasks and exactly four isolated-value conditions:

1. native one-shot;
2. equal-budget neutral analysis plus a fresh builder;
3. current explicit specialist advice plus a fresh builder; and
4. reduced explicit specialist advice plus a fresh builder.

Automatic routing is not rerun in AS because `SQ1-AQ` is its sole authority.
That is deliberate nonduplicative successor design, not skipped evidence. AS
uses at most seven base model calls per task plus at most two residual-review
calls per task: `12 x (7 + 2) = 108`. The separate 156-invocation program hard
stop remains fail-closed. Its 48-call margin is not transferable and cannot fund
extra conditions, routing reruns, content retries, or post-observation
diagnostics.

`SQ1-AS` may report isolated advice value only for the frozen representative
tasks and exact adviser/builder boundary. It cannot generalize to composition,
host behavior, product value, or field usefulness.

### SQ1-AC

`SQ1-AC` uses 8 fresh tasks and exactly four conditions:

1. neutral decomposition;
2. current explicit two-specialist composition;
3. reduced explicit two-specialist composition; and
4. a wrong-neighbor negative control.

AC uses at most ten base model calls per task plus at most two residual-review
calls per task: `8 x (10 + 2) = 96`. The separate 144-invocation program hard
stop remains fail-closed. Its 48-call margin is not transferable and cannot fund
extra conditions, arbitrary multi-specialist expansion, content retries, or
post-observation diagnostics.

`SQ1-AC` may report composition only for the frozen exact two-decision tasks. It
cannot generalize to arbitrary multi-skill, multi-agent, product, or field use.

### SQ1-AH

`SQ1-AH` is an **offline, unprivileged, disposable-home** check. Its only passing
literal is `NARROW_PASS`. It uses no network, credentials, privileged host,
installed user home, or production surface. `NARROW_PASS` is never production,
deployment, security, release, interoperability, installed-host, or clean-host
proof.

### SQ1-AF

Absent a separately named and owner-authorized privacy, consent, and operating-
envelope authority, `SQ1-AF` performs no field action and records exactly
`OMITTED_NO_FIELD_CLAIM`. Participation, earlier passes, public data, or a broad
program authorization cannot substitute for that separate authority. The
omission is not a pass and does not block the truthful terminal record.

### SQ1-AR

`SQ1-AR` records independent claim coordinates. It must not emit an aggregate
confidence, overall success score, release recommendation, or compensation
across coordinates. The vector is:

- `program_authority`: F0 structural authority only;
- `aq_activation_selection`: pass, fail, or unobserved for the exact AQ envelope;
- `as_isolated_advice_value`: pass, fail, blocked, or unobserved;
- `ac_two_decision_composition`: pass, fail, blocked, or unobserved;
- `ah_offline_disposable_home`: `NARROW_PASS`, fail, blocked, or unobserved;
- `af_field_usefulness`: always `OMITTED_NO_FIELD_CLAIM` absent separate authority;
- `production_clean_host_security`: unproven;
- `public_release_publish_promotion`: not authorized; and
- `deletion_migration`: not authorized.

`SQ1-AR` retains artifacts in place and stops. This program authorizes no public
release, publish, promotion, deletion, or migration action under any vector.

## 9. Acceptance criteria

### F0 acceptance

F0 passes only if all of the following are true:

- the plan and authority JSON identify AE-SQ1 as a distinct successor and ban
  AQ10/H6/retry/resume/reopen/cure/reinterpretation semantics;
- the manifest binds this plan's raw SHA-256 without binding a future successor
  commit;
- the predecessor commit, tree, exact paths, blobs, and raw SHA-256 digests
  reproduce from Git at the immutable base;
- JSON parsing rejects duplicate keys and non-finite constants, and validators
  enforce exact types, key order, and object closure;
- the exact stage graph, direct-failure edges, normal 324/624 and absolute
  328/628 ceilings, 156/144 downstream hard stops, four-capsule isolation,
  no-replay, retry, aggregate-only, and global-AND rules are mutation-tested;
- the current-foundation file contains one minimal active-plan pointer change;
- `docs/foundations/decision-log.csv` has exactly one appended AE-SQ1 F0 row;
- no reserved candidate, evaluator, heldout, result, runner, or stage artifact is
  staged or committed with F0, noncanonical drafts confer no authority, and no
  candidate/corpus/model observation has occurred; and
- focused authority tests, foundation tests, Ruff, JSON parsing, diff review and
  status review pass.

F0 completion establishes only `structural-program-authority-frozen`. It leaves
F1 and every model-bearing stage on HOLD.

### Program acceptance

The program closes only through `SQ1-AR`. The all-pass path requires exact,
noncompensatory passing aggregates from SQ1-AQ, SQ1-AS, and SQ1-AC; an offline AH
`NARROW_PASS`; the truthful AF omission unless separately authorized; accurate
invocation and consumption counters; and a separated AR vector. A blocking
failure closes the remaining stage coordinates as blocked or unobserved and
routes directly to AR. No closeout state authorizes release or external action.

## 10. Low-risk substitutions

Before the owning freeze, the root conductor may accept these low-risk
substitutions if tests prove semantic identity and the decision is recorded:

- a temporary directory or disposable-home absolute path;
- a deterministic JSON serialization implementation;
- a local process-runner implementation;
- a deterministic schedule seed with the same 40 unique cases, two conditions,
  80 presentations, and four unique child contexts per presentation;
- task wording within the frozen AS or AC task contract that preserves freshness,
  condition identity, assessor/builder isolation, call counts, and evaluator
  semantics;
- test helper organization or file-internal function names; and
- an equivalent offline fixture that exercises the same AH boundary.

The following are not low-risk substitutions: predecessor inputs, candidate
mechanism, evidence-independence rule, model, reasoning effort, fallback,
candidate count, cases, split independence, presentation count, calls per unit,
budgets, evaluator formulas, thresholds, aggregation, stage order, failure
edges, retry count, no-replay, consumption point, isolation, AS/AC task counts or
conditions, the AS automatic-routing prohibition, permissions, network access,
claim ceilings, AF omission, or forbidden actions. Changing one requires
terminal closeout and a genuinely new owner-authorized program.

## 11. Current checkpoint

F0 is the only in-scope checkpoint. On successful static validation, report:

- **PASS:** AE-SQ1 F0 static authority is internally closed and predecessor
  history reproduces from the named Git base.
- **HOLD:** F1 independent external evidence and all candidate, heldout, model,
  host, field, release, publication, promotion, deletion, and migration work.
