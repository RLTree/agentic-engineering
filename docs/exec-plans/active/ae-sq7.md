# AE-SQ7 distinct successor qualification program

Status: **ACTIVE — SQ7-F0 AUTHORITY; SQ7-F1A NEXT**
Program: `AE-SQ7`
Candidate: `AE-SQ7-SLEC-7`
Machine authority: `evals/ae-sq7/program-authority.json`
Authority date: 2026-08-13, America/Los_Angeles
Claim ceiling: structural successor authority and unexecuted selected-reference-anchor repair plan only

## 1. Distinct terminal boundary

AE-SQ7 is a new owner-authorized program, not an AE-SQ6 retry, repair,
refreeze, reopen, resume, reinterpretation, continuation, cure, or delayed
phase. AE-SQ6 remains terminal at `SQ6-AR`. Only the aggregate failure contract
crosses the boundary: the sole frozen SQ6 corpus validation attempt failed
`selected_reference_anchor`. No SQ6 candidate, active-role, task, case, split,
corpus, label, schedule, author, result, or F2 byte may be reused.

## 2. Closed graph and budgets

```text
SQ7-F0 -> F1A -> F1B -> F1G -> F2A -> F2B -> F3 -> F4 -> F5 -> F6
            any NOT_PASS ------------------------------------------> SQ7-AR
                                                               PASS -> SQ7-AS-HANDOFF
```

F0 through F3 and F6 use zero model calls. F4 is exactly four synthetic
non-corpus calls; all four must PASS before F5. F5 is exactly 80 presentations
with four isolated calls each, at most 320 calls. Every attempt counts. The
total ceiling is 324 and retry ceiling is zero. Every live call uses exactly
`gpt-5.5` at reasoning effort `medium`, without fallback.

## 3. Fresh F1 and two preauthor production gates

F1A is one fresh SQ7 candidate/evaluator/runner/schema/test closure and direct
child of F0. Every active role must have fresh bytes and must not alias any SQ6
active-role blob or raw digest. It is zero-corpus and zero-model. F1B is its
manifest-only freeze, binding the exact F1A commit, tree, paths, blobs, and raw
digests. No semantic change follows F1B.

Before any author route opens, F1G must pass both production-real gates. First,
its taskless receipt is canonical sorted compact UTF-8 JSON with no trailing
byte; exact committed bytes must pass the real target-frozen `_load_base_state`
preauthor mode, while the same bytes plus one line feed must fail closed.

Second, a synthetic non-corpus selected-reference fixture must run through the
exact target-frozen production validator and resolver. The positive fixture
contains reference-requiring selected anchors and must PASS. Exact red fixtures
that omit the selected reference anchor or supply the wrong selected reference
anchor must each fail with `selected_reference_anchor`. Source assertions,
mocks, dictionary-only checks, and alternate resolver routes cannot satisfy the
gate. The authoring tool refuses to emit or accept task/case material until the
exact committed F1G receipt proves both gates. Any failure routes immediately
to `SQ7-F1G:NOT_PASS->SQ7-AR`, with no replacement.

## 4. Fresh corpus and F2 custody

Only after F1G PASS, two independently routed authors each create 20 fresh
cases. Neither sees the other split, any predecessor task material, live
material, or outcomes. An independent nonauthor validates strict schema and
semantic closure, 40 unique cases, historical digest nonreplay, reachability,
selected-reference anchors, and the fixed 80-presentation schedule.

F2A is the ordered three-parent merge `[F1G, author A, author B]`; its exact
`100644` delta is split A, split B, schedule, and corpus manifest. F2B is its
direct child and changes only the canonical run manifest, embedding a closed
independent PASS receipt that binds F1A, F1B, F1G, F2A, both authors and splits,
schedule, manifest, and validator. Only exact F2B PASS opens F3. No edit,
replacement, or second attempt exists.

## 5. Preflight, live execution, global AND, and custody

F3 is one zero-model preflight proving exact Git custody, both F1G production
gates, schemas, formulas, 2 x 20 and 80 x 4 closure, lifecycle, counters,
budgets, privacy, and unclaimed one-shot state. Failure is terminal.

F4 makes exactly four synthetic non-corpus calls. F5 runs only after all four
PASS and has no retries. F6 is a deterministic global logical AND: missing,
skipped, undefined, nonfinite, malformed, duplicate, extra, rejected, failed,
or unevaluable values are false. There is no averaging or compensation.

F6 may emit only aggregate-only JSON at
`evals/ae-sq7/f6/aggregate-result.json`. PASS may create only
`evals/ae-sq7/as/handoff.json`; every nonpass route may create only
`evals/ae-sq7/ar/terminal-decision.json`. Handoff is not downstream authority.
Raw prompts, task/case content, outputs, events, transcripts, messages, and
presentation-, assessor-, gate-, or score-level material remain private.

Even PASS proves at most one exact candidate aggregate in this frozen 40-case,
two-condition envelope. It does not prove general provider/model, product,
host, field, production, security, release, publication, promotion, or effect
claims. The next authorized transition is one zero-model, zero-corpus SQ7-F1A
commit; no later phase begins before its immediate durable gate.
