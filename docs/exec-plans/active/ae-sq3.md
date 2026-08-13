# AE-SQ3 distinct successor qualification program

Status: **TERMINAL — SQ3-AR AFTER SQ3-F1A NOT_PASS; NO REOPEN**
Program owner: repository owner
Program integrator: root conductor
Active-plan path: `docs/exec-plans/active/ae-sq3.md`
Machine-readable authority: `evals/ae-sq3/program-authority.json`
Authority date: 2026-08-12, America/Los_Angeles
Claim ceiling: structural F1A custody and checker-contract failure closeout only

## 1. New program identity and predecessor boundary

The owner authorizes **AE-SQ3** as a new, distinct successor program. AE-SQ3 is
not an AE-SQ2 retry, reopen, resume, continuation, cure, reinterpretation, H6,
or delayed SQ2 phase. AE-SQ2 remains terminal at `SQ2-AR`; no AE-SQ3 result can
alter that record. The SQ3 candidate is `AE-SQ3-SLEC-3`, a new candidate
identity that must be frozen under SQ3 custody. Its candidate bytes and fresh
corpus are not continuations of any predecessor attempt.

AE-SQ2 terminal custody is anchored by:

- diagnostic record commit `e2562ca4da5f3dc14fb07c1522f911e2dfe4334d`,
  blob `f5dc5b67435c78d0b214ac21fc69531c9bae7d3e`, and raw SHA-256
  `1e2352fe42453b03cafac06e9c2e98638af17ad6a3e5dfaf389baf9da39d6502`;
- internal record SHA-256
  `5bb323666e5fe54d39df3fb91a65e1dd44c96ac5a4f3c9e967d2481a5eda5e9c`
  and aggregate SHA-256
  `d333397b1bc0a633d80ac43bbf1ae6e9b5aafdfb6af5b01ad5493f9fb3292235`;
  and
- terminal decision `evals/ae-sq2/ar/terminal-decision.json`, raw SHA-256
  `f705401afd219eafaf13be273a7386b503400cc2f1ef0b072d74a7ec14919ada`.

Only this bounded diagnosis crosses into SQ3: four of four synthetic calls were
classified `schema_unsupported`, every other classification was zero, and all
usage counters were zero. The cause is actionable only as a provider-schema
compatibility repair. No raw prompt, output, event, message, task, case, label,
score, or behavioral outcome crosses the boundary. The diagnostic is not AQ
evidence and cannot tune candidate behavior, evaluator formulas or thresholds,
cases, labels, or interpretation.

The stale pre-fix diagnostic-record digest is not custody and must not appear in
SQ3 authority or bindings. AE-SQ1, AE-SQ2, and `EXECPLAN.md` remain immutable.

## 2. Owner authorization and exact phase graph

The owner authorizes the complete bounded SQ3 chain below, including one
four-call live canary and a conditional 320-call batch. Authority does not prove
execution or success. No additional diagnostic call is authorized or needed.

```text
SQ3-F0 -> SQ3-F1A -> SQ3-F1B -> SQ3-F2 -> SQ3-F3 -> SQ3-F4
                                                           |
                                                        PASS
                                                           v
                                                       SQ3-F5
                                                           |
                                                     COMPLETE
                                                           v
                                                       SQ3-F6
                                                      /       \
                                                  PASS       NOT PASS
                                                   |             |
                                                   v             v
                                      SQ3-AS-HANDOFF           SQ3-AR

Any blocking failure, invalid canary, or incomplete/invalid batch -> SQ3-AR
```

| Phase | Purpose | Model calls | Successful edge |
|---|---|---:|---|
| `SQ3-F0` | this program authority | 0 | `SQ3-F1A` |
| `SQ3-F1A` | implement repaired candidate, evaluator, runner, and schemas | 0 | `SQ3-F1B` |
| `SQ3-F1B` | manifest-only exact freeze of F1A bytes and custody | 0 | `SQ3-F2` |
| `SQ3-F2` | independently author, validate, and freeze fresh 2 x 20 holdout | 0 | `SQ3-F3` |
| `SQ3-F3` | one zero-model preflight | 0 | `SQ3-F4` on pass only |
| `SQ3-F4` | one non-corpus canary | exactly 4 if entered | `SQ3-F5` on pass only |
| `SQ3-F5` | conditional 80-presentation heldout batch | at most 320 | `SQ3-F6` only when complete and valid |
| `SQ3-F6` | deterministic global logical AND | 0 | handoff on pass; otherwise AR |
| `SQ3-AS-HANDOFF` | pass-only downstream routing state | 0 | separate authority required |
| `SQ3-AR` | terminal closeout | 0 | none |

A failed or invalid canary terminates SQ3 before the batch. An incomplete,
failed, or invalid batch terminates SQ3 and cannot be repaired or compensated
by scoring or a later stage. A complete valid batch reaches F6, where any
missing or nonpassing required value makes the global AND fail.

## 3. Diagnosed repair, with no second diagnostic

SQ3-F1A must replace the provider-facing output schema with a recursively closed
supported subset. The only provider-schema keywords permitted are `type`,
`properties`, `required`, `additionalProperties`, `items`, `enum`,
`description`, `minItems`, `maxItems`, `$defs`, and `$ref`. Every object lists
all properties in `required` and sets `additionalProperties` to false.

Provider-facing use of `allOf`, `if`, `then`, `else`, `not`, `uniqueItems`,
`pattern`, `minLength`, `maxLength`, `minimum`, `maximum`, dependent-keyword
families, unevaluated-keyword families, or any undeclared schema keyword is
forbidden. Rich conditional, uniqueness, anchor, cardinality, syntax, and
domain invariants remain mandatory, but are enforced by the frozen local
semantic validator after provider decoding and before the parent resolver,
evaluator, or scorer. Provider-schema validation and local semantic validation
must both pass; neither substitutes for the other.

F1A must also repair lifecycle accounting so a call is observed only after a
recognized completed event and valid decoded capsule. Stdout presence, process
exit alone, stderr text, or a timeout cannot establish completion. Unknown,
tool, effect, malformed, duplicate, or extra events fail closed. Raw material is
transient and aggregate-only persistence remains mandatory.

The repair is authorized directly from the bounded SQ2 diagnosis. SQ3 has a
diagnostic call budget of zero. A proposed diagnostic call, schema fallback,
model fallback, or result-informed repair routes to SQ3-AR.

## 4. F1 two-commit freeze

SQ3-F1A is one implementation commit containing the repaired provider schema,
local semantic schema and validator, candidate and condition adapter, resolver,
runner, evaluator, scorer, run-index implementation, all other execution
schemas, and their deterministic tests. It contains no corpus, split, schedule,
live result, preflight result, or freeze manifest.

SQ3-F1B is a second commit whose only new program artifact is the exact freeze
manifest. It binds the F0 authority, bounded SQ2 diagnosis, F1A commit and tree,
every required file path/blob/raw SHA-256, `AE-SQ3-SLEC-3`, `gpt-5.5` with
`medium` reasoning, supported provider subset, local semantic validator, event
and lifecycle rules, evaluator formulas and thresholds, global AND, budgets,
zero retry, raw-retention prohibition, aggregate-only projection, and the exact
durable state schema below.

No corpus authoring may begin until F1B passes independent strict review.
Candidate, evaluator, runner, schemas, formulas, thresholds, model, effort,
budgets, persistence, and routing are immutable after F1B. Any semantic change
requires terminal SQ3-AR and another new program identity.

## 5. Exact durable one-shot/run-index schema

The F1 implementation must use one unified, canonical, owner-only durable state
record for the one-shot execution boundary and run index. Its top-level keys are
exactly, in canonical order:

```text
binding
custody_key
program_id
record_sha256
schema_version
state_sha256
status
```

The values are fixed as follows:

- `schema_version`: `ae-sq3-one-shot-run-index-v1`;
- `program_id`: `AE-SQ3`;
- `custody_key`: SHA-256 of canonical `binding`;
- `binding`: an exact object with only
  `corpus_manifest_sha256`, `f1_freeze_sha256`,
  `preflight_record_sha256`, `program_authority_sha256`, and
  `run_manifest_sha256`;
- `status`: exactly `claimed`, `completed`, or `invalid`;
- `record_sha256`: null exactly while `claimed`, otherwise one SHA-256; and
- `state_sha256`: SHA-256 of the canonical record with `state_sha256` omitted.

All five binding values are lowercase 64-hex SHA-256 digests. No top-level or
nested extension key is permitted. The state is created with an atomic
owner-only no-follow exclusive claim before the first canary child. Existing,
malformed, noncanonical, wrong-owner, wrong-mode, symlinked, hardlinked,
digest-invalid, or differently bound state permits no child spawn. Interruption
after claim leaves a durable terminal no-reuse boundary. Terminal replacement
is atomic. Dry runs and zero-model preflight cannot claim execution state.

This schema is part of F0 authority, not an implementation suggestion. Strict
recursive and mutation-red tests must reject every added, missing, reordered,
wrongly typed, noncanonical, or inconsistently hashed field.

## 6. Fresh corpus and independent validation

Only after F1B, two independent blinded authors each create exactly 20 new
cases. Each sees only the frozen authoring contract and neither can see the
other split, predecessor task/case/corpus/label material, D0 model material,
any live output, or any result. The corpus is fresh relative to every
predecessor and is not an SQ2 continuation.

An independent corpus custodian validates exact 2 x 20 authorship, 40 unique
cases, schema and semantic closure, historical no-replay digest separation,
label reachability, and the exact 80-presentation schedule: every case once in
`current` and once in `reduced`, four isolated calls per presentation. F2 freezes
the split digests, independence receipts, corpus manifest, schedule, run
manifest, and no-replay custody. No result-informed change is permitted.

The first heldout-backed F5 call consumes both splits permanently as
`NO_REPLAY`. Duplicate, replacement, extra, top-up, or replay presentations are
forbidden.

## 7. One zero-model preflight

SQ3-F3 has exactly one attempt and zero model calls. It verifies the exact F1B
and F2 bindings, supported provider-schema subset, local semantic validation,
strict schemas, 2 x 20 independence and uniqueness, 80 x 4 schedule, formulas,
global-AND coverage, lifecycle and effect-event rejection, counters, budgets,
aggregate-only projection, zero retry, raw-persistence prohibition, and an
unclaimed one-shot state.

Only exact F3 `PASS` reaches F4. Failure, drift, omission, or unevaluable state
routes to SQ3-AR. F3 cannot repair bytes or run twice.

## 8. Canary, batch, and global AND

SQ3-F4 is one four-call synthetic non-corpus unit using the exact F1B bytes and
model configuration. It passes only when all four isolated calls start and
complete once, all capsules pass provider and local semantic validation, the
parent join closes, counters reconcile, no tool/effect/unknown event is
accepted, and no forbidden raw material persists. Only that exact pass permits
F5. No retry, top-up, replacement, second canary, byte change, or fallback is
permitted.

SQ3-F5 conditionally executes exactly 80 frozen presentations and at most 320
attempted calls. Every attempted invocation counts, including rejected,
malformed, timed-out, empty, or failed calls. No call or presentation is ever
retried. An incomplete or invalid batch terminates SQ3. A complete valid batch
reaches F6 without any result-informed change.

SQ3-F6 emits one candidate-bound aggregate status and digest. `PASS` is the
logical AND of every required run-integrity, capsule, evaluator, gate, metric,
condition, and presentation value. Missing, skipped, undefined, nonfinite,
malformed, duplicate, extra, unevaluable, rejected, or failed values are false.
There is no averaging, compensation, threshold repair, override, or later-stage
cure. Only exact `PASS` opens `SQ3-AS-HANDOFF`; every other state routes to
SQ3-AR. The handoff is not downstream execution authority.

## 9. Model, budgets, privacy, and claims

Every live SQ3 call uses exactly `gpt-5.5` with reasoning effort `medium` and no
model, provider, effort, or mode fallback.

| Budget | Calls |
|---|---:|
| diagnostics | 0 |
| one canary | 4 |
| conditional batch | 320 |
| qualification hard ceiling | 324 |
| retry hard ceiling | 0 |

Raw prompts, task text, model output, event payloads, transcripts, messages,
case-, split-, condition-, presentation-, assessor-, gate-, or score-level
results may not leave their frozen custody. Only the final aggregate status and
digest may leave evaluator custody.

SQ3-F0 proves authority only. F1-F3 prove exact bytes and compatibility only.
F4 is gateway evidence only. F6 can prove at most one exact-candidate aggregate
in the frozen 40-case, two-condition SQ3 envelope. Nothing here proves product,
host, field, production, security, release, publication, promotion, or general
provider/model performance.

## 10. Namespace, acceptance, and next transition

New program artifacts live under `evals/ae-sq3/`. AE-SQ1, AE-SQ2, their durable
state, and `EXECPLAN.md` are immutable. SQ3-F0 consists only of this plan,
`evals/ae-sq3/program-authority.json`, the SQ2 terminal decision, the two new
tests, and the exact foundation pointer/log updates. It executes no model call,
authors no corpus, and changes no candidate or runner byte.

F0 passes only when strict duplicate-key, type, order, recursive closure, exact
digest, predecessor custody, phase graph, provider-repair, durable-state,
privacy, zero-retry, global-AND, and pass-only tests pass; mutation reds reject
weakened authority; the foundation pointer names SQ3 exactly; the two decision
rows occur exactly once; JSON parses; Ruff and `git diff --check` pass; and no
out-of-scope byte changed.

The next authorized transition was SQ3-F1A implementation with zero live calls
and zero corpus authoring. No later phase could begin before its immediate gate.

## 11. Terminal checkpoint after SQ3-F1A

SQ3-F1A commit `c06c433cdc2581e1747c10e520eb2fdd857cdccd`
(tree `54312ecc9469801a90e02a32ca7c44d7a6fcf699`) is `NOT_PASS`.
Its frozen checker validates the immutable SQ2-D0 diagnostic record against an
invented `program_id` field and requires `mode` to equal `diagnostic`. The exact
record at commit `e2562ca4da5f3dc14fb07c1522f911e2dfe4334d` has no
`program_id` field and correctly records `mode` as `live`; therefore that
checker cannot validate the exact bounded predecessor custody authorized by
SQ3-F0. This is a checker-contract failure, not permission to rewrite D0.

Published sibling `b31e8b619ae1ef75aef179bbba7212235258178f` is superseded,
uses the same invalid checker contract, and never produced SQ3-F1B. No freeze
manifest, SQ3 corpus, preflight, canary, batch, aggregate, or downstream result
exists. SQ3 made zero diagnostic, canary, batch, or other model calls. Uncommitted
checker repair bytes are not SQ3 authority and cannot cure the committed F1A.

SQ3 is terminal at `SQ3-AR`: no retry, reopen, resume, refreeze, second F1A,
F1B, F2, F3, F4, F5, F6, H6, downstream action, release, publication, or
promotion is permitted. The exact terminal record is
`evals/ae-sq3/ar/terminal-decision.json`. Only a distinct owner-authorized new
program ID may proceed; no successor result can alter SQ3's terminal record.
