# AE-SQ2 successor qualification program authority

Status: **TERMINAL — SQ2-AR; NO F1, CORPUS, QUALIFICATION, OR DOWNSTREAM EDGE**
Program owner: repository owner
Program integrator: root conductor
Terminal-plan path: `docs/exec-plans/active/ae-sq2.md`
Machine-readable authority: `evals/ae-sq2/program-authority.json`
Authority date: 2026-08-12, America/Los_Angeles
Claim ceiling: structural authority and unexecuted owner authorization only

## 1. Distinct successor and immutable history

The owner authorizes **AE-SQ2** as a distinct successor program. AE-SQ2 is not
an AE-SQ1 retry, reopen, resume, continuation, cure, reinterpretation, AQ10, or
H6. No AE-SQ2 observation or decision can alter, cure, supersede, or weaken the
terminal AE-SQ1 record.

AE-SQ1 remains immutable terminal history at:

- commit `9861df7c7894b35f5ce758ee1b005f80ceb0426e`;
- tree `573f53baa839a3b088548a7e7ba2050003911a7a`;
- immutable tag `ae-sq1-terminal-2026-08-11`;
- plan blob `ff649a88cdf8ffa1f1a4b6a8b6a71b2c01cc43b4`, raw SHA-256
  `ebc53ca6305837ecd089dd201542dcbb35c5478b6bbf31e1003a227440868418`;
  and
- namespace tree `47e799543415c8834d9753f5252dd73e33eb3639` at
  `evals/ae-sq1/`.

Only four terminal facts cross the boundary: AE-SQ1 is terminal and stopped,
its successful-program conditions were not met, release and promotion were
negative, and its artifacts remain immutable history. AE-SQ1 task text, cases,
corpus, labels, raw prompts, raw outputs, result payloads, diagnostics, scores,
aggregates, inferred causes, and outcomes are forbidden AE-SQ2 design, tuning,
authoring, scoring, or interpretation inputs.

Static non-corpus candidate, evaluator, and runner source may be inspected only
as an untrusted prospective draft. That source confers no AE-SQ2 authority and
must be bound anew at `SQ2-F1`. No AE-SQ1 path may be edited. `EXECPLAN.md`
remains unchanged immutable predecessor history.

## 2. Recorded owner authorization and execution boundary

This authority records the owner's explicit authorization for the complete
bounded AE-SQ2 qualification chain, including the live calls at `SQ2-D0`,
`SQ2-F4`, and `SQ2-F5`. The authorization is already granted; it does not need
to be inferred from a later static check. Each phase may execute only after its
immediate gate closes and only within the exact budgets below.

This F0 lane creates authority files and tests only. It performs no diagnostic,
canary, batch, corpus authoring, candidate freeze, external publication,
release, promotion, deletion, migration, field action, or downstream execution.
Authorization is not evidence that any authorized phase ran or passed.

The exact model for every AE-SQ2 live call is `gpt-5.5` with reasoning effort
`medium`. This static inheritance is a controlled configuration choice, not
transferred behavioral evidence from AE-SQ1. Model, provider, effort, and mode
fallback are forbidden.

## 3. Sole phase graph

```text
SQ2-F0 -> SQ2-D0 -> SQ2-F1 -> SQ2-F2 -> SQ2-F3 -> SQ2-F4
                                                         |
                                                   PASS only
                                                         v
            SQ2-AS-HANDOFF <- PASS <- SQ2-F6 <- SQ2-F5
                                      |
                                   NOT PASS
                                      v
                                    SQ2-AR

SQ2-D0/F1/F2/F3/F4 blocking failure -----------------> SQ2-AR
```

The phases are:

| Phase | Purpose | Model calls | Successful next edge |
|---|---|---:|---|
| `SQ2-F0` | this closed program authority | 0 | `SQ2-D0` |
| `SQ2-D0` | bounded diagnostic-only, non-corpus interface probe | at most 4 | `SQ2-F1` after a closed diagnostic record |
| `SQ2-F1` | bind the diagnosed repair, candidate, evaluator, runner, and budgets | 0 | `SQ2-F2` |
| `SQ2-F2` | author and freeze a fresh independent 2 x 20 corpus and 80-presentation schedule | 0 | `SQ2-F3` |
| `SQ2-F3` | exact zero-model compatibility and custody preflight | 0 | `SQ2-F4` on pass only |
| `SQ2-F4` | one four-call non-corpus qualification canary | exactly 4 if entered | `SQ2-F5` on pass only |
| `SQ2-F5` | conditional 80-presentation heldout batch | at most 320 | `SQ2-F6` for deterministic scoring |
| `SQ2-F6` | noncompensatory global logical AND and aggregate projection | 0 | `SQ2-AS-HANDOFF` on pass; otherwise `SQ2-AR` |
| `SQ2-AS-HANDOFF` | pass-only downstream handoff state | 0 under this authority | separately closed downstream authority |
| `SQ2-AR` | deterministic terminal closeout | 0 | none |

There are no other active phases or edges. A later phase cannot compensate for,
average over, cure, reinterpret, reopen, or resume an earlier failure.
`SQ2-AS-HANDOFF` is a routing state, not authority to execute downstream work.

## 4. Exact call budgets and no-retry rule

| Call-bearing phase | Normal design | Hard ceiling | Derivation |
|---|---:|---:|---|
| `SQ2-D0` diagnostic | 4 | 4 | four predeclared non-corpus slots, one attempt per slot |
| `SQ2-F4` canary | 4 | 4 | one non-corpus four-call unit |
| `SQ2-F5` batch | 320 | 320 | 40 cases x 2 conditions x 4 isolated calls |
| **Qualification only** | **324** | **324** | canary plus conditional batch; D0 is not qualification evidence |
| **Program through F6** | **328** | **328** | diagnostic plus qualification |

Every attempted model invocation counts, including malformed, empty, rejected,
timed-out, or transport-failed attempts. Unused calls expire in their phase and
cannot be transferred, used to top up a partial unit, or spent on another
diagnostic. There is no infrastructure retry, content retry, post-observation
retry, replay, replacement presentation, fallback, or second canary. A call or
presentation may be attempted at most once. No post-observation retry means
exactly zero retry calls in D0, canary, batch, and the entire program.

## 5. SQ2-D0 diagnostic-only contract

`SQ2-D0` occurs before candidate freeze and before any AE-SQ2 corpus exists. Its
sole purpose is to classify the non-corpus request/response/capsule/runner
interface sufficiently to define one diagnosed repair at `SQ2-F1`. D0 cannot
qualify AQ, satisfy the canary, consume a corpus, create a behavioral score,
change an evaluator threshold, or authorize a downstream edge.

Before the first call, the diagnostic custodian must freeze exactly four
synthetic non-corpus probe slots `p0`, `p1`, `p2`, and `p3` in that order and
their input SHA-256 digests. D0 is one indivisible four-slot diagnostic unit:
all four distinct slots must be attempted exactly once, `calls_started` must
equal four, and an early close is forbidden even when an earlier slot exposes a
decisive failure. The slots are nonadaptive, and no observed result may add,
replace, repeat, or reorder a slot. Probe bytes may exist only transiently for
the call.

The only permitted durable D0 fields are:

- diagnostic identifier, mode, status, claim ceiling, probe identifier, model,
  reasoning effort, authority SHA-256, and diagnostic-record-schema SHA-256;
- the exact closed container keys `input_schema`, `cli`, `calls`, `usage`,
  `classification_counts`, and `event_type_counts`, solely to contain the
  permitted leaves named here;
- input-schema path, byte count, and SHA-256; CLI path, version, and SHA-256;
- one closed classification from `transport_spawn`, `process_exit`,
  `signal_exit`, `timeout`, `empty_stdout`, `invalid_jsonl`, `unknown_event`,
  `missing_completed_message`, `provider_request_rejected`,
  `schema_unsupported`, `schema_invalid`, `semantic_invalid`,
  `valid_completed`, or `other_fail_closed`; and
- exit code or null, signal or null, request/stdout/stderr/completed-message byte
  counts and SHA-256 digests, closed event-type counts, closed usage-counter
  presence and values, one closed redacted error class, calls-started and calls-
  completed counters, counts by classification, aggregate SHA-256, and record
  SHA-256.

The aggregate call-counter field names are exactly `calls_started` and
`calls_completed`. `usage_observed_calls` is not permitted; usage presence is a
per-call closed Boolean and usage values remain closed per-call and aggregate
counters under the permitted `usage` container.

Classification precedence is frozen exactly as `transport_spawn`, `timeout`,
`schema_unsupported`, `provider_request_rejected`, `signal_exit`,
`process_exit`, `empty_stdout`, `invalid_jsonl`, `unknown_event`,
`missing_completed_message`, `schema_invalid`, `semantic_invalid`,
`valid_completed`, then `other_fail_closed`. The redacted error-class enum is
exactly `none`, `invalid_json_schema`, `invalid_request`, `authentication`,
`authorization`, `rate_limit`, `network`, `server`, or `other`.

Classification counters have exactly one key for every classification in the
closed classification enum, in that enum's order. Every value is an integer
(never a Boolean) from zero through four, and the values sum to exactly four.
Thus transport or provider rejection remains a classified attempted slot; it
does not permit early close or reduce the four-attempt requirement.

Raw prompts, task text, stdout, stderr, completed messages, model output,
excerpts, summaries, arbitrary error strings, transcripts, thread identifiers,
event bodies or payloads, provider payloads or error messages, stack traces,
and token-level logs must never be persisted. The parser classifies, counts,
and hashes transient bytes, then discards them. Missing material is represented
only by the corresponding zero byte count, SHA-256 of empty bytes when a digest
field is required, null exit code or signal where applicable, and a closed
classification.

D0 may inform one bounded repair to request framing, response decoding, capsule
schema adaptation, effect-event rejection, lifecycle accounting, or diagnostic
interface framing. It may not tune AQ task policy, condition semantics,
evaluator formulas or thresholds, future cases, or labels. D0 closes with a
diagnostic record, never `PASS`; starting fewer or more than four calls,
omitting, repeating, or reordering a slot, retaining forbidden data, or leaving
the record open routes to `SQ2-AR`.

## 6. SQ2-F1 diagnosed repair and exact freeze

`SQ2-F1` may begin only after D0 closes within budget and zero forbidden raw
material is retained. F1 must bind the diagnosed repair and the exact bytes or
digests for:

- the candidate mechanism and condition adapter;
- request framing, response decoder, capsule schema, and parent join;
- runner, event rejection, call accounting, and fail-closed stop behavior;
- evaluator schemas, formulas, thresholds, required values, and global AND;
- the exact `gpt-5.5` / `medium` model configuration with no fallback;
- diagnostic record digest and declared repair delta;
- raw-retention prohibition and aggregate-only result projection; and
- the no-retry state and phase budgets.

No corpus, case, label, heldout text, or model qualification result may inform
F1. Once F1 closes, candidate, runner, evaluator, model, conditions, formulas,
thresholds, persistence rules, and budgets are immutable for AE-SQ2. A failed
F1 or any proposed semantic refreeze routes to `SQ2-AR`; it does not reopen F1.

Fresh corpus authoring is forbidden until the exact F1 freeze is closed.

## 7. SQ2-F2 fresh corpus and presentation freeze

After F1, two independent blinded authors each create exactly 20 fresh cases.
Neither author may access the other split, D0 model material, any AE-SQ1 task or
corpus material, or any model outcome. The authors receive only the closed F1
authoring contract. The combined corpus must contain exactly 40 unique cases.

Each case is scheduled once under `current` and once under `reduced`, producing
exactly 80 unique presentations. Each presentation is one four-call isolated
unit. F2 freezes split digests, independence receipts, the combined manifest,
uniqueness proof, exact presentation schedule, run index, and no-replay state.

No case may be pre-authored, reserved, drafted, or imported before F1. No D0 or
F4 payload may contain heldout text, labels, nonces, metadata, or derived corpus
content. The first heldout-backed call at F5 consumes both splits immediately
and irreversibly as `NO_REPLAY`.

## 8. SQ2-F3 zero-model preflight

F3 uses zero model calls. It must verify exact F1 and F2 custody, all referenced
digests, schema closure, 2 x 20 authorship, 40-case uniqueness, the complete
80-presentation schedule, four-call isolation, formula totality, required-value
coverage, global-AND fail closure, event rejection, counters, budgets, aggregate
projection, no-retry state, and zero forbidden raw persistence.

Only an exact F3 pass may enter F4. A missing, inconsistent, unevaluable, or
failed preflight value routes to `SQ2-AR`. F3 failure cannot repair F1, rewrite
F2, invoke a model, or create a second preflight within AE-SQ2.

## 9. SQ2-F4 one live qualification canary

F4 is exactly one non-corpus four-call unit using the frozen F1 candidate,
runner, evaluator interface, model, reasoning effort, and persistence policy.
The four calls use isolated child contexts with no sibling transcript or state.
The canary contains no heldout material and does not consume F2.

F4 passes only if all four calls start and complete once, every required capsule
is schema-valid, no tool or effect event is accepted, counters reconcile, the
deterministic parent join closes, and no forbidden raw material persists. Any
other state fails directly to `SQ2-AR`. There is no canary retry, replacement,
top-up, byte change, or fallback. A canary pass is gateway evidence only; it is
not an AQ pass or behavioral qualification claim.

## 10. SQ2-F5 conditional 80-presentation batch

F5 may start only after the exact F4 pass. It presents all 40 frozen cases once
under each of `current` and `reduced`, for exactly 80 presentations and four
isolated calls per presentation. The hard ceiling is 320 attempted calls.

The first heldout call consumes the complete F2 corpus. Weak, malformed,
partial, missing, rejected, or failed calls are scored as observed and are never
retried. A stopped batch leaves the unattempted required values missing; it does
not create permission to restart or complete them later. Duplicate, replacement,
extra, or replayed presentations fail run integrity.

Only one candidate-bound aggregate status and digest may leave evaluator
custody. Raw outputs, transcripts, case-, split-, condition-, presentation-,
assessor-, gate-, or score-level results are nonreportable.

## 11. SQ2-F6 global AND and pass-only routing

F6 is deterministic and uses zero model calls. The sole AQ result is `PASS` if
and only if every required run-integrity, capsule, evaluator, gate, metric, and
condition value for all 80 presentations is passing under the frozen contract.
Missing, skipped, undefined, non-finite, malformed, duplicate, extra,
unevaluable, rejected, or failed values are false inputs to the global logical
AND. There is no averaging, threshold repair, condition compensation, later
stage compensation, or discretionary override.

Only exact global `PASS` routes to `SQ2-AS-HANDOFF`. Every non-pass, missing
aggregate, integrity failure, or unevaluable state routes to terminal `SQ2-AR`.
The handoff asserts only an exact-candidate aggregate pass in the frozen AE-SQ2
envelope. It does not itself authorize or prove isolated advice value,
composition, host behavior, field usefulness, production behavior, release,
publication, or promotion. Downstream execution requires its own closed
authority.

## 12. Custody lanes

| Lane | Owns | Must not do |
|---|---|---|
| Program owner | F0 objective, bounded authorization, consequential exceptions | inspect heldout/raw outputs or convert authorization into a pass claim |
| Root conductor | phase order, custody, counters, PASS/HOLD, failure routing | author cases, tune scoring, retry, or execute release actions |
| Diagnostic custodian | four predeclared D0 slots, transient classification/hashing, bounded record | persist raw material, adapt slots, qualify AQ, or author corpus |
| Repair steward | one diagnosed repair and F1 exact freeze | use corpus/outcome inputs or refreeze after F1 |
| Split-A author | fresh 20-case split A after F1 | access split B, D0 model material, AE-SQ1 corpus, or outcomes |
| Split-B author | fresh 20-case split B after F1 | access split A, D0 model material, AE-SQ1 corpus, or outcomes |
| Corpus custodian | F2 validation, digests, schedule, blinding, no-replay state | edit candidate/evaluator or interpret outcomes |
| Preflight custodian | deterministic F3 compatibility and custody proof | invoke a model or repair frozen bytes |
| Run custodian | F4/F5 exact execution, counters, isolation, stop behavior | retry, change bytes, score discretionarily, or publish raw material |
| Aggregate scorer | F6 global AND and aggregate-only projection | edit prior phases, compensate, disclose subaggregates, or route non-pass downstream |
| AR integrator | deterministic terminal retention and stop | reopen, resume, retry, release, publish, promote, delete, or migrate |

One person or agent may fill multiple lanes only if the stated access boundaries
remain mechanically enforceable. The two split authors must remain independent.

## 13. Canonical namespace and F0 scope

All AE-SQ2 artifacts live under `evals/ae-sq2/`; no AE-SQ2 artifact may write
under `evals/ae-sq1/` or overwrite another program.

Exactly five F0 paths are in scope:

```text
docs/exec-plans/active/ae-sq2.md
evals/ae-sq2/program-authority.json
tests/test_ae_sq2_program_authority.py
docs/foundations/current-2026-08-08.md
docs/foundations/decision-log.csv
```

Future D0-F6 paths may be reserved by the machine-readable authority, but they
confer no state or evidence merely by existing. They may not enter the F0 change.
`EXECPLAN.md`, AE-SQ1, candidate files, corpus files, runner files, and result
files are outside this lane.

The reserved D0 namespace includes its authority, diagnostic-record schema,
and diagnostic record under `evals/ae-sq2/d0/`. Its separately reserved support
identities are `scripts/diagnose_ae_sq2_handshake.py` and
`tests/test_diagnose_ae_sq2_handshake.py`. Reservation governs identity only:
these paths are not F0 files, their presence confers no phase state or evidence,
and their bytes must be closed and reviewed under D0 before execution.

## 14. Claim ceilings and terminal rules

F0 establishes only `structural-program-authority-closed` and records the
owner's unexecuted authorization. D0 may establish only bounded non-corpus
interface classifications and counters. F1-F3 may establish only exact frozen
bytes, fresh-corpus custody, and zero-model compatibility. F4 may establish only
one exact non-corpus canary status. F5-F6 may establish only one exact-candidate
aggregate for the frozen 40-case, two-condition AE-SQ2 envelope.

No phase proves provider generalization, product value, clean-host behavior,
field usefulness, production security, release readiness, publication fitness,
or promotion authority. `SQ2-AR` is terminal. A change to program identity,
phase order, model, reasoning, budget, diagnostic persistence, F1 bindings,
corpus count, condition schedule, call isolation, retry rule, consumption point,
global AND, reporting projection, or pass-only edge requires a new owner-
authorized program identity.

## 15. F0 acceptance and next transition

F0 passes only when the plan and authority JSON are strictly closed and ordered,
the raw plan digest matches, AE-SQ1 and `EXECPLAN.md` reproduce their immutable
bindings, the foundation pointer changes only to AE-SQ2, exactly one decision-log
row is appended, mutation reds reject weakened budgets/order/privacy/retry/
routing semantics, JSON parses strictly, targeted and foundation tests pass,
Ruff passes without cache, `git diff --check` passes, and final status contains
only owned or explicitly reported unrelated changes.

F0 performs zero model calls and authors zero corpus cases. The next authorized
transition is to predeclare the four synthetic non-corpus D0 slots and execute
`SQ2-D0` under its bounded diagnostic-only authority. That transition may not
be described as AQ qualification, retry, reopen, resume, or H6.

## 16. Terminal checkpoint after SQ2-D0

AE-SQ2 executed its sole four-call diagnostic at commit
`e2562ca4da5f3dc14fb07c1522f911e2dfe4334d`. The bounded record is
`evals/ae-sq2/d0/diagnostic-record.json`, blob
`f5dc5b67435c78d0b214ac21fc69531c9bae7d3e`, raw SHA-256
`1e2352fe42453b03cafac06e9c2e98638af17ad6a3e5dfaf389baf9da39d6502`,
internal record SHA-256
`5bb323666e5fe54d39df3fb91a65e1dd44c96ac5a4f3c9e967d2481a5eda5e9c`,
and aggregate SHA-256
`d333397b1bc0a633d80ac43bbf1ae6e9b5aafdfb6af5b01ad5493f9fb3292235`.
All four slots classified `schema_unsupported`; every other classification and
all usage counters were zero. This is diagnostic evidence only.

The diagnostic also persisted a one-shot state under the Git common directory.
Its top-level fields included `schema_version`, `custody_key`, `binding`, and
`state_sha256`, plus five nested binding keys. Those fields were not in F0's
exhaustive list of permitted durable D0 fields. The state was safety-motivated
and bounded, but its persistence still violated the frozen authority. Under the
predeclared `budget_or_persistence_violation_route`, AE-SQ2 therefore entered
`SQ2-AR` and is terminal.

- **F1, corpus, preflight, canary, batch, and F6:** not started.
- **AQ:** no result; D0 cannot qualify AQ.
- **AS and every downstream stage:** blocked.
- **AR:** `DO_NOT_RELEASE_OR_PROMOTE`, `STOP`.
- **Retry, reopen, resume, H6, further SQ2 model/corpus work, release,
  publication, promotion, deletion, and migration:** forbidden.

The closed terminal decision is
`evals/ae-sq2/ar/terminal-decision.json`. All AE-SQ2 and durable one-shot state
surfaces remain retained. A repair requires a distinct owner-authorized program
identity; it cannot be an AE-SQ2 retry, continuation, cure, or reinterpretation.
