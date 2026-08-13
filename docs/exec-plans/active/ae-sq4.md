# AE-SQ4 distinct successor qualification program

Status: **ACTIVE — SQ4-F0 AUTHORITY; SQ4-F1A NEXT**
Program owner: repository owner
Program integrator: root conductor
Active-plan path: `docs/exec-plans/active/ae-sq4.md`
Machine-readable authority: `evals/ae-sq4/program-authority.json`
Authority date: 2026-08-12, America/Los_Angeles
Claim ceiling: structural successor authority and source-backed repair contract only

## 1. Distinct identity and terminal predecessor

The owner authorizes **AE-SQ4** as a new program with candidate identity
`AE-SQ4-SLEC-4`. It is not an SQ3 retry, reopen, resume, refreeze, second F1A,
continuation, cure, reinterpretation, H6, or delayed SQ3 phase. SQ3 remains
terminal at `SQ3-AR`; no SQ4 result may alter that record.

SQ3 reached F1A only. Commit
`c06c433cdc2581e1747c10e520eb2fdd857cdccd` is `NOT_PASS` because its
checker cannot validate the exact immutable SQ2-D0 record: it requires an
invented `program_id` and `mode="diagnostic"`, whereas the record has no
`program_id` and correctly records `mode="live"`. Published sibling
`b31e8b619ae1ef75aef179bbba7212235258178f` is superseded and has the same
checker defect. Neither attempt produced F1B. SQ3 authored no corpus or
preflight and made zero diagnostic, canary, batch, or other model calls.

Only two bounded inputs cross the boundary:

1. the source-backed repair contract—a provider-supported recursively closed
   schema subset plus a separate fail-closed local semantic validator and
   strict completed-event lifecycle; and
2. the exact SQ2-D0 aggregate custody at commit
   `e2562ca4da5f3dc14fb07c1522f911e2dfe4334d`, including record raw SHA-256
   `1e2352fe42453b03cafac06e9c2e98638af17ad6a3e5dfaf389baf9da39d6502`,
   record SHA-256
   `5bb323666e5fe54d39df3fb91a65e1dd44c96ac5a4f3c9e967d2481a5eda5e9c`,
   and aggregate SHA-256
   `d333397b1bc0a633d80ac43bbf1ae6e9b5aafdfb6af5b01ad5493f9fb3292235`.

No SQ3 candidate qualification, corpus, task, label, prompt, output, event,
message, score, result, or behavioral claim crosses. SQ3 F1A source may be
inspected only as source-backed implementation evidence; SQ4 must freeze all
candidate bytes anew under SQ4 custody and cannot claim SQ3 qualification.

## 2. Exact phase graph and budgets

```text
SQ4-F0 -> SQ4-F1A -> SQ4-F1B -> SQ4-F2 -> SQ4-F3 -> SQ4-F4
                                                           |
                                                        PASS
                                                           v
                                                       SQ4-F5
                                                           |
                                                     COMPLETE
                                                           v
                                                       SQ4-F6
                                                      /       \
                                                  PASS       NOT PASS
                                                   |             |
                                                   v             v
                                      SQ4-AS-HANDOFF           SQ4-AR

Any blocking failure, invalid canary, or incomplete/invalid batch -> SQ4-AR
```

| Phase | Purpose | Model calls | Successful edge |
|---|---|---:|---|
| `SQ4-F0` | this distinct authority | 0 | `SQ4-F1A` |
| `SQ4-F1A` | one corrected implementation commit | 0 | `SQ4-F1B` on pass |
| `SQ4-F1B` | one manifest-only freeze commit | 0 | `SQ4-F2` on pass |
| `SQ4-F2` | fresh independently authored 2 x 20 holdout | 0 | `SQ4-F3` on pass |
| `SQ4-F3` | one zero-model preflight | 0 | `SQ4-F4` on pass |
| `SQ4-F4` | one non-corpus canary | exactly 4 if entered | `SQ4-F5` on pass |
| `SQ4-F5` | conditional 80-presentation batch | at most 320 | `SQ4-F6` only if complete and valid |
| `SQ4-F6` | deterministic global logical AND | 0 | handoff on pass; otherwise AR |
| `SQ4-AS-HANDOFF` | pass-only routing state | 0 | separate authority required |
| `SQ4-AR` | terminal closeout | 0 | none |

All live calls use exactly `gpt-5.5`, reasoning effort `medium`, with no model,
provider, effort, or mode fallback. Diagnostic budget is zero; canary budget is
4; conditional batch budget is 320; qualification ceiling is 324; retry ceiling
is zero. Every attempted invocation counts.

## 3. Correct D0 validation and inherited repair

SQ4-F1A must validate the actual bounded D0 artifacts, not a synthetic surrogate.
The D0 record root keys are exactly those frozen in the SQ4 authority. It has no
`program_id`; `diagnostic_id` is `AE-SQ2-D0-2026-08-12-01`; `mode` is `live`;
and `status` is `completed`. The checker must authenticate the frozen Git commit,
tree/path/blob/raw SHA-256, D0 authority SHA-256, D0 schema SHA-256, internal
record SHA-256, aggregate SHA-256, classification total 4 with
`schema_unsupported=4`, and all-zero usage. It must recompute internal digests
under the original frozen schemas. Requiring an invented field, changing
`mode`, weakening closure, or rewriting D0 routes to SQ4-AR.

The provider-facing schema permits only `type`, `properties`, `required`,
`additionalProperties`, `items`, `enum`, `description`, `minItems`, `maxItems`,
`$defs`, and `$ref`. Every object requires every property and sets
`additionalProperties` false. Rich conditional, uniqueness, anchor,
cardinality, syntax, and domain constraints are enforced by a separately frozen
local semantic validator after provider decoding and before resolution,
evaluation, or scoring. Both layers must pass. Lifecycle observation requires a
recognized completed event plus a provider-valid and locally valid capsule;
stdout, process exit, stderr, or timeout alone cannot establish completion.
Unknown, tool, effect, malformed, duplicate, or extra events fail closed.

SQ4 has no diagnostic-call phase. Any diagnostic call, fallback, or
result-informed repair terminates SQ4.

## 4. One F1A and one manifest-only F1B

SQ4-F1A is exactly one implementation commit directly after the SQ4-F0
authority commit. It must be the only accepted F1A and must contain the complete
SQ4 candidate, provider/local schemas, candidate authority and adapter,
resolver, evaluator, scorer, runner, run-index, execution schemas, corrected D0
checker, and strict deterministic tests. It contains no freeze manifest,
corpus, split, schedule, preflight result, live result, or downstream artifact.
No sibling, alternate F1A, same-program repair, or refreeze can qualify.

SQ4-F1B is the direct child of the passing F1A. Its only new program artifact is
`evals/ae-sq4/f1/repaired-freeze.json`. It binds the SQ4-F0 authority, SQ3
terminal custody, exact SQ2-D0 source custody, F1A commit/tree, every required
path/blob/raw SHA-256, candidate ID, model configuration, formulas, thresholds,
event rules, budgets, privacy, durable-state contract, zero retry, global AND,
and routing. No corpus authoring begins until independent strict F1B review
passes. Any semantic change after F1B terminates SQ4.

## 5. Exact durable one-shot state

The unified run-index record uses schema
`ae-sq4-one-shot-run-index-v1`, program ID `AE-SQ4`, and exactly these canonical
top-level keys:

```text
binding
custody_key
program_id
record_sha256
schema_version
state_sha256
status
```

`binding` has only `corpus_manifest_sha256`, `f1_freeze_sha256`,
`preflight_record_sha256`, `program_authority_sha256`, and
`run_manifest_sha256`. Every binding value is lowercase 64-hex; `custody_key`
is SHA-256 of canonical binding. Status is `claimed`, `completed`, or `invalid`;
`record_sha256` is null exactly while claimed; `state_sha256` authenticates the
canonical record with that field omitted. No extension or reordering is valid.

The state is owner-only, no-follow, single-link, and atomically claimed with
exclusive creation before the first canary child. Existing, unsafe, malformed,
noncanonical, differently bound, or digest-invalid state prevents all child
spawns. An interrupted claim remains a terminal no-reuse boundary. Preflight
and dry runs cannot claim it.

## 6. Fresh F2 custody

After F1B passes, two blinded independent authors each create exactly 20 fresh
cases. Each sees only the frozen authoring contract and cannot see the other
split, predecessor task/case/corpus/label material, D0 model material, or any
live result. An independent custodian validates exact authorship, 40 unique
cases, recursive schema and semantic closure, historical exact-digest
nonreplay, label reachability, and a schedule of exactly 80 presentations: each
case once in `current` and once in `reduced`, four isolated calls each.

F2 freezes split digests, independence receipts, corpus manifest, schedule,
run manifest, and no-replay custody. The first heldout-backed F5 call consumes
both splits permanently as `NO_REPLAY`. No result-informed edits, replay,
replacement, duplicate, extra, or top-up presentation is permitted.

## 7. One zero-model F3 preflight

F3 runs exactly once and makes zero model calls. It proves exact F1B/F2
bindings; correct D0 validation; provider-subset and local-semantic closure;
strict schemas; 2 x 20 independence and uniqueness; 80 x 4 schedule; formula
totality and global-AND coverage; lifecycle/event/counter integrity; exact
budgets; aggregate-only persistence; zero forbidden raw persistence; and an
unclaimed one-shot state. Only exact `PASS` reaches F4. No repair or second
preflight is permitted.

## 8. Canary, batch, and global AND

F4 is one four-call synthetic non-corpus canary using exact F1B bytes. It passes
only if all calls start and complete once, every capsule passes both validation
layers, the parent join closes, counters reconcile, no tool/effect/unknown
event is accepted, and no forbidden raw material persists. Failure or invalidity
terminates SQ4 before the batch. There is no retry, top-up, replacement, second
canary, byte change, or fallback.

F5 conditionally executes exactly 80 frozen presentations and at most 320
attempted calls. Every failed, rejected, malformed, empty, or timed-out attempt
counts; none is retried. Only a complete valid batch reaches F6.

F6 emits exactly one candidate-bound aggregate status and digest. `PASS` is the
logical AND of every required run-integrity, capsule, evaluator, gate, metric,
condition, and presentation value. Missing, skipped, undefined, nonfinite,
malformed, duplicate, extra, unevaluable, rejected, or failed values are false.
There is no averaging, compensation, threshold repair, override, or later cure.
Only exact `PASS` opens `SQ4-AS-HANDOFF`; all other states route to SQ4-AR. The
handoff itself is not downstream execution authority.

## 9. Privacy, claims, and next transition

Raw prompts, task text, outputs, event payloads, transcripts, messages, and
case-, split-, condition-, presentation-, assessor-, gate-, or score-level
results may not leave frozen custody. Only the final aggregate status and digest
may leave evaluator custody.

F0 proves authority only. F1-F3 prove bytes and compatibility only. F4 is a
gateway only. F6 can prove at most one exact-candidate aggregate in the frozen
40-case, two-condition SQ4 envelope. No phase proves general provider/model,
product, host, field, production, security, release, publication, promotion,
or effect claims.

New artifacts live under `evals/ae-sq4/`. All predecessor program bytes and
durable state remain immutable. This F0 transition adds only the SQ3 terminal
checkpoint and record, this plan and machine authority, the foundation
pointer/log rows, and strict authority tests. It authors no corpus, changes no
candidate/runner byte, and makes no model call.

The next authorized transition is one SQ4-F1A implementation commit with zero
model calls and zero corpus. No later phase begins before its immediate gate.
