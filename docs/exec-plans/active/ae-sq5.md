# AE-SQ5 distinct successor qualification program

Status: **TERMINAL — SQ5-F1G NOT_PASS -> SQ5-AR**
Program: `AE-SQ5`
Candidate: `AE-SQ5-SLEC-5`
Machine authority: `evals/ae-sq5/program-authority.json`
Authority date: 2026-08-13, America/Los_Angeles
Claim ceiling: exact committed-byte custody and production-loader rejection only; no F2 qualification, preflight, model, runtime-success, downstream, release, or effect claim

## 0. Terminal closeout (2026-08-13)

AE-SQ5 is permanently terminal. The committed F1G receipt at
`4af4ad00cc11b903a2b6d796b3578d7e76e0aaca` is a 1,623-byte Git blob whose
raw SHA-256 is
`ffe6dca737c8e2a9f93a5bcdf596bec2569d6998efcc79d6583dd39ffb2a216d`.
It ends in line feed. The frozen production `canonical_json` projection is
1,622 bytes, has no trailing line feed, and has SHA-256
`52b7b29bfbe85b8260e659a17273793ebbfa90c3e7c5afb3e0b9d56588a9203d`.
Those byte streams are unequal.

The actual frozen production `_load_base_state` route, executed at detached
F2B `4760ecb53997fe693a76531057eaf8c13014434d`, raises
`PreflightError: F1G receipt is not exact canonical UTF-8 JSON` before F2
validation. F1G is therefore `NOT_PASS`, which takes the already frozen
`SQ5-F1G:NOT_PASS->SQ5-AR` edge. The durable terminal routing artifact is
`evals/ae-sq5/ar/terminal-decision.json`.

F2A `e74e3ef5055ac95442ecd3b342d4a47bc2b0345d` and F2B
`4760ecb53997fe693a76531057eaf8c13014434d` are unreferenced and unpublished
evidence objects only. They did not qualify, cannot compensate for F1G, and
must never be reused. Their author A/B task material is also prohibited in any
successor. F3 was not attempted; model, canary, and batch calls are all zero.
No retry, repair, refreeze, reinterpretation, reopen, resume, or downstream
route exists in AE-SQ5.

The remaining sections preserve the preterminal authority as history. They do
not authorize another AE-SQ5 action. The only next route is the distinct
owner-authorized AE-SQ6 program in `docs/exec-plans/active/ae-sq6.md`.

## 1. Distinct identity and terminal boundary

AE-SQ5 is a new owner-authorized program. It is not a retry, reopen, resume,
repair, refreeze, continuation, cure, reinterpretation, delayed phase, or H6 of
AE-SQ4. AE-SQ4 remains terminal at `SQ4-AR`; AE-SQ5 cannot change its bytes,
state, evidence, or conclusion.

The only evidence that crosses the boundary is the aggregate structural failure
contract: SQ4's authored split authority named F1B as the candidate commit/tree,
while the frozen runner required the F1A implementation commit/tree. No SQ4
task text, case, split, corpus, label, prompt, output, event, capsule, score,
result, schedule, author object, or F2A object may be reused. The SQ4 standalone
corpus-validation PASS has no qualification effect in AE-SQ5.

AE-SQ5 must freeze a new candidate under identity `AE-SQ5-SLEC-5` and author a
new 2 x 20 holdout only after its own F1 gate passes.

## 2. Closed phase graph and call budgets

```text
SQ5-F0 -> SQ5-F1A -> SQ5-F1B -> SQ5-F1G -> SQ5-F2A -> SQ5-F2B -> SQ5-F3
                                                                           |
                                                                           v
                                                                        SQ5-F4
                                                                           |
                                                                          PASS
                                                                           v
                                                                        SQ5-F5
                                                                           |
                                                                      COMPLETE
                                                                           v
                                                                        SQ5-F6
                                                                       /       \
                                                                   PASS       NOT PASS
                                                                    |             |
                                                                    v             v
                                                       SQ5-AS-HANDOFF           SQ5-AR

Any blocking failure, invalid canary, or incomplete/invalid batch -> SQ5-AR
```

| Phase | Purpose | Model calls | Successful edge |
|---|---|---:|---|
| `SQ5-F0` | this distinct authority | 0 | `SQ5-F1A` |
| `SQ5-F1A` | one new implementation commit | 0 | `SQ5-F1B` on pass |
| `SQ5-F1B` | one manifest-only freeze commit | 0 | `SQ5-F1G` on pass |
| `SQ5-F1G` | zero-corpus real-byte author-template gate | 0 | `SQ5-F2A` on pass |
| `SQ5-F2A` | exact fresh-corpus merge and four-artifact closure | 0 | `SQ5-F2B` on pass |
| `SQ5-F2B` | canonical run manifest plus embedded independent receipt | 0 | `SQ5-F3` only on pass |
| `SQ5-F3` | one zero-model preflight | 0 | `SQ5-F4` on pass |
| `SQ5-F4` | one non-corpus canary | exactly 4 if entered | `SQ5-F5` on pass |
| `SQ5-F5` | conditional 80-presentation batch | at most 320 | `SQ5-F6` only if complete and valid |
| `SQ5-F6` | deterministic global logical AND | 0 | handoff on pass; otherwise AR |
| `SQ5-AS-HANDOFF` | pass-only routing state | 0 | separate authority required |
| `SQ5-AR` | terminal closeout | 0 | none |

Every live call uses exactly `gpt-5.5` with reasoning effort `medium`. There is
no model, provider, reasoning, or mode fallback. Diagnostic budget is zero;
canary budget is 4; conditional batch budget is 320; total qualification
ceiling is 324; retry ceiling is zero. Every attempted invocation counts.

## 3. F1 implementation, freeze, and mandatory author-template gate

F1A is exactly one new implementation commit directly after committed F0. It
contains the complete SQ5 candidate, schemas, evaluator, scorer, runner,
durable-state implementation, strict checks, and author-template builder and
validator. It contains no freeze manifest, corpus, authored split, schedule,
preflight result, live result, or downstream artifact. SQ4 candidate bytes are
not an SQ5 freeze and cannot be promoted or refrozen.

F1A has an authority-embedded exhaustive active-role ledger. Its changed paths
from exact committed F0 must equal that ledger exactly, in order and set: no
missing, extra, reordered, duplicate, or aliased role or path is accepted.
Every active path uses the SQ5 namespace and is an exact Git `100644` regular
blob. Every SQ5 active-role blob object ID and raw SHA-256 must differ from
every sealed SQ4 F1A role, including tests. Owned identity fields must name
`AE-SQ5` and `SLEC-5`. The pinned historical digest inventory and other named
predecessor evidence remain external immutable provenance only; they may not
be copied into the SQ5 namespace or occupy an active candidate role.

F1B is the direct child of the passing F1A. Its only new program artifact is
`evals/ae-sq5/f1/repaired-freeze.json`. It binds the exact F1A implementation
commit/tree and every frozen byte. No semantic change is permitted after F1B.

F1G is a mandatory deterministic gate after exact F1B and before any author
lane opens. It makes zero model calls and contains no task, case, label, or
corpus content. Using the frozen F1A builder and real canonical JSON bytes, it
must create and reparse a synthetic author-template authority whose:

- `program_id` is `AE-SQ5` and `candidate_id` is `AE-SQ5-SLEC-5`;
- `candidate_commit` and `candidate_tree` equal the F1A implementation identity;
- the separate `f1_freeze_sha256` equals the F1B manifest digest; and
- every frozen contract digest matches the F1A profile.

The gate must prove byte equality through write/read or equivalent byte-stream
round trip, pass the same frozen runtime validation used for F2B, and include a
red fixture that substitutes the F1B commit/tree as candidate identity and is
rejected with the exact fail-closed authority-mismatch class. It must also
validate the exact taskless author template that will be supplied to both
authors. A source-only assertion, dictionary-only fixture, mock profile, or
test that accepts F1B as the implementation identity does not pass. F1G is
one-shot and result-blind; any failure routes to SQ5-AR. Only `SQ5-F1G:PASS`
opens F2A author lanes.

F1G is a receipt-only commit directly after F1B. Its sole new program artifact
is `evals/ae-sq5/f1/author-template-gate.json`, validated by
`evals/ae-sq5/f1/author-template-gate-schema.json` frozen in F1A. The canonical
receipt binds the F1A commit/tree and builder/validator bytes, the F1B
commit/tree and freeze digest, the exact taskless template digest, attempt 1,
zero model calls, positive real-byte round-trip PASS, the exact F1B-as-candidate
`PreflightError` red rejection, and an aggregate digest over the unsigned
receipt. No transient command result can open F2A. Both author commits must be
direct children of exact F1G; F2A has ordered parent roles F1G, author A, author
B; and F2B and F3 must bind the F1G commit, tree, receipt blob, and raw SHA-256.

One frozen `expected_authority` helper is the sole source for author-template
and corpus-authority construction. The corpus validator requires that exact
expected authority as an explicit argument; a standalone corpus-validator PASS
can establish only structural corpus validity and can never establish F2B or AQ
PASS. The loader targets the checker and authority bytes frozen in F1A. It must
reject an ambient `--root` checker, ambient authority, or any target/ambient
byte mismatch rather than silently importing mutable workspace code. F1G and
F2B must enter the exact production `_load_base_state` path from an ephemeral
private Git snapshot containing authenticated F1A bytes. A partial loader,
mock, or live-worktree substitution cannot pass.

## 4. Fresh corpus and custody

After F1G passes, two independently routed authors each create exactly 20 new
cases under the validated taskless template. Each sees only the frozen SQ5
authoring contract and cannot see the other split, any predecessor task/case/
corpus/label material, diagnostic or live material, or any outcome. Neither
SQ4 split, author commit, corpus manifest, schedule, combined corpus digest, nor
F2A object may be copied, replayed, imported, or treated as a starting corpus.

Every F2 JSON artifact must be an exact Git `100644` regular blob. The five
artifacts use strict canonical UTF-8 JSON: both splits, the schedule, corpus
manifest, and run manifest: no duplicate keys, nonfinite values, alternate encodings, trailing
bytes, or noncanonical serialization.

An independent nonauthor validates exact authorship, 40 unique cases,
recursive schema and semantic closure, historical exact-digest nonreplay,
label reachability, and a schedule of exactly 80 presentations: every case once
under `current` and once under `reduced`, with four isolated calls per
presentation. F2A is the exact three-parent merge `[F1G, author A, author B]`;
relative to F1G its artifact closure is exactly split A, split B, schedule, and
corpus manifest. F2A must bind split authority to the SQ5 F1A implementation
and bind F1B separately.

F2B is the exact direct child of passing F2A. Its sole delta is canonical
`evals/ae-sq5/f2/run-manifest.json`, validated by the run-manifest schema
frozen in F1A. The manifest embeds the independent nonauthor validator receipt
and binds F1A, F1B, F1G, F2A, both author commits and split bytes, all corpus
and schedule bytes/digests, and exact validator identity/blob/raw SHA-256. Its
status is PASS, `authorship_performed` is false, and errors/holds are empty.
Standalone content validation has no qualification effect. Only exact durable
`SQ5-F2B:PASS` opens F3. Any F2A or F2B failure terminates; neither phase has a
retry, replacement, or second attempt. No result-informed edit, replay,
replacement, duplicate, extra, or top-up is permitted. The first
heldout-backed F5 call permanently consumes both splits as `NO_REPLAY`.

## 5. Preflight, canary, batch, and global AND

F3 executes once with zero model calls. It proves exact F1B/F1G/F2A/F2B custody,
re-executes the real-byte candidate-vs-freeze author-authority contract,
validates all schemas and formulas, proves 2 x 20 and 80 x 4 closure, checks
strict lifecycle/counters/budgets/privacy, and proves the one-shot state is
safe and unclaimed. Only exact PASS reaches F4; no repair or second preflight
is permitted.

F4 is one four-call synthetic non-corpus canary using the exact frozen bytes.
All four calls must start and complete once, produce provider- and locally
valid capsules, close the parent join and counters, reject forbidden events,
and persist no raw content. Any invalidity terminates AE-SQ5 before the batch.

F5 conditionally executes exactly 80 frozen presentations and at most 320
attempted calls. Failed, rejected, malformed, empty, and timed-out attempts
count and are never retried. Only a complete valid batch reaches F6.

F6 emits exactly one candidate-bound aggregate status and digest. PASS is the
logical AND of every required integrity, capsule, evaluator, gate, metric,
condition, and presentation value. Missing, skipped, undefined, nonfinite,
malformed, duplicate, extra, unevaluable, rejected, or failed values are false.
There is no averaging, compensation, repair, override, or later cure. Only PASS
opens `SQ5-AS-HANDOFF`; every other state routes to terminal `SQ5-AR`. The
handoff is not downstream execution authority.

The only durable F6 projection is canonical aggregate-only JSON at
`evals/ae-sq5/f6/aggregate-result.json`. Its raw SHA-256 must equal the terminal
run-index `record_sha256`. A passing route may create only the distinct
`evals/ae-sq5/as/handoff.json` path; every nonpass route may create only the
distinct `evals/ae-sq5/ar/terminal-decision.json` path. Neither routing artifact
can alias, replace, or act as the F6 result.

F1A freezes closed schemas for all three outcome artifacts:
`evals/ae-sq5/f1/result-schema.json`,
`evals/ae-sq5/f1/handoff-schema.json`, and
`evals/ae-sq5/f1/terminal-decision-schema.json`. The canonical aggregate result
contains only schema/program/candidate identity, PASS-or-FAIL, and its aggregate
digest. Handoff is created only from the exact F6 PASS edge and binds that
result path/raw digest while conferring no execution authority. A terminal
decision is created only from one exact edge into SQ5-AR and binds that edge
and the last completed phase; it binds the aggregate result only if F6 was
entered. Handoff and terminal artifacts cannot coexist.

## 6. Privacy, claims, and next transition

Raw prompts, task text, outputs, event payloads, transcripts, messages, and
case-, split-, condition-, presentation-, assessor-, gate-, or score-level
results remain inside frozen custody. Only the final aggregate status and
digest may leave evaluator custody.

F0 proves authority only. F1-F3 prove bytes and compatibility only. F4 is only
a gateway. F6 can prove at most one exact-candidate aggregate in the frozen
40-case, two-condition SQ5 envelope. No phase proves general provider/model,
product, host, field, production, security, release, publication, promotion,
or effect claims.

The next authorized transition is one zero-model, zero-corpus SQ5-F1A
implementation commit. No later phase begins before its immediate gate.
