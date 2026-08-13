# AE-SQ6 distinct successor qualification program

Status: **ACTIVE — SQ6-F0 AUTHORITY; SQ6-F1A NEXT**
Program: `AE-SQ6`
Candidate: `AE-SQ6-SLEC-6`
Machine authority: `evals/ae-sq6/program-authority.json`
Authority date: 2026-08-13, America/Los_Angeles
Claim ceiling: structural successor authority and unexecuted canonical-receipt repair plan only

## 1. Distinct terminal boundary

AE-SQ6 is a new owner-authorized program with the same qualification goal. It
is not an AE-SQ5 retry, repair, refreeze, reopen, resume, reinterpretation,
continuation, cure, delayed phase, or H6. AE-SQ5 remains terminal at `SQ5-AR`.

The only imported learning is aggregate: the committed SQ5 F1G receipt ended
in one line-feed byte, so it differed from the production canonical JSON bytes.
At detached F2B, the real frozen `_load_base_state` rejected it with
`PreflightError: F1G receipt is not exact canonical UTF-8 JSON` before F2
validation. No SQ5 candidate or active-role byte, task, case, split, corpus,
label, schedule, author material, result, or F2 object crosses the boundary.
The unqualified unpublished SQ5 F2A and F2B objects have no qualification
effect and are permanently prohibited from reuse.

## 2. Closed graph and budgets

```text
SQ6-F0 -> F1A -> F1B -> F1G -> F2A -> F2B -> F3 -> F4 -> F5 -> F6
                     any NOT_PASS -------------------------------> SQ6-AR
                                                            PASS -> SQ6-AS-HANDOFF
```

F0 through F3 and F6 use zero model calls. F4 is one synthetic non-corpus
four-call canary. Only all-four PASS opens F5. F5 conditionally runs exactly 80
presentations with four isolated calls each, at most 320 calls. Every attempt
counts; retries, replay, replacements, extras, duplicates, and top-ups are
forbidden. The total ceiling is 324 and the retry ceiling is zero. Every live
call uses exactly `gpt-5.5` with reasoning effort `medium`, with no fallback.

## 3. F1 implementation, freeze, and preauthor production gate

F1A is one fresh SQ6 candidate/evaluator/runner/schema/test closure, a direct
child of committed F0. It is zero-corpus and zero-model. Active SQ5 candidate
bytes cannot be copied or promoted. F1B is one manifest-only direct child that
binds exact F1A commit, tree, paths, blobs, and raw digests; no semantic change
is permitted afterward.

F1G is one taskless receipt-only direct child of exact F1B. Its writer and the
production verifier use the same canonical serializer: UTF-8 JSON, sorted keys,
compact separators, and no trailing byte or line feed. The positive fixture is
the exact committed F1G blob, not an in-memory dictionary or reformatted copy.
The real target-frozen `_load_base_state` preauthor mode must accept those exact
committed no-line-feed bytes. The same real route must reject the exact receipt
plus one line feed with the frozen `PreflightError` message.

The authoring tool must fail closed: absent the exact committed F1G PASS receipt
and successful target-frozen `_load_base_state` preauthor verification, it
refuses to emit or accept any task or case material. Mocks, source assertions,
mutable-worktree substitution, and dictionary-only tests cannot open authoring.
Any failure is terminal `SQ6-F1G:NOT_PASS->SQ6-AR` with no replacement.

## 4. Fresh corpus and F2 custody

Only after exact committed F1G PASS, two independently routed authors each
create 20 fresh cases. Each sees the taskless SQ6 author contract only and not
the other split, predecessor task material, live material, or outcomes. An
independent nonauthor checks exact authorship, 40 unique cases, strict schema
and semantic closure, historical digest nonreplay, reachability, and the fixed
80-presentation schedule.

F2A is the ordered three-parent merge `[F1G, author A, author B]`. Relative to
F1G its exact `100644` delta is split A, split B, schedule, and corpus manifest.
F2B is the direct child of passing F2A and changes only the canonical run
manifest. It embeds a closed independent PASS receipt and binds F1A, F1B, F1G,
F2A, both authors, both splits, schedule, manifest, and validator. Only exact
F2B PASS opens F3. No result-informed edit or second attempt exists.

## 5. Preflight, live gate, batch, and global AND

F3 is one zero-model preflight. It proves exact Git custody, canonical receipt
compatibility through the production route, schemas, formulas, 2 x 20 and
80 x 4 closure, lifecycle, counters, budgets, privacy, and unclaimed one-shot
state. Failure is terminal; there is no second preflight.

F4 makes exactly four synthetic non-corpus calls. All four must start and
complete once, satisfy provider and local validation, close joins and counters,
and persist no raw content. Only all-four PASS opens F5. F5 runs the fixed batch
without retries. F6 is a deterministic global logical AND: missing, skipped,
undefined, nonfinite, malformed, duplicate, extra, rejected, failed, or
unevaluable values are false. There is no averaging or compensation.

## 6. Durable result, privacy, and next transition

F6 may emit only aggregate-only JSON at
`evals/ae-sq6/f6/aggregate-result.json`. PASS may create only
`evals/ae-sq6/as/handoff.json`; every nonpass route may create only
`evals/ae-sq6/ar/terminal-decision.json`. Handoff is not downstream execution
authority. Raw prompts, task/case content, outputs, events, transcripts,
messages, and presentation-, assessor-, gate-, or score-level material remain
inside evaluator custody.

Even PASS proves at most one exact-candidate aggregate in this frozen 40-case,
two-condition envelope. It does not prove general provider/model, product,
host, field, production, security, release, publication, promotion, or effect
claims.

The next authorized transition is one zero-model, zero-corpus SQ6-F1A commit.
No later phase begins before its immediate durable gate.
