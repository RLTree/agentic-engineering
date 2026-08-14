# AE-SQ8 distinct successor qualification program

Status: **ACTIVE — SQ8-F0 AUTHORITY; SQ8-F1A NEXT**
Program: `AE-SQ8`
Candidate: `AE-SQ8-SLEC-8`
Machine authority: `evals/ae-sq8/program-authority.json`
Authority date: 2026-08-13, America/Los_Angeles
Claim ceiling: structural successor authority and unexecuted F3 receipt-interface repair plan only

## 1. Distinct terminal boundary

AE-SQ8 is a new owner-authorized program, not an AE-SQ7 retry, repair,
refreeze, reopen, resume, reinterpretation, continuation, cure, or delayed
phase. AE-SQ7 remains terminal at `SQ7-AR`. Only terminal/interface provenance
and the external digest-only historical inventory may cross the boundary. No
SQ7 candidate, active-role, task, case, split, corpus, label, schedule, author,
result, F2, F3, or execution byte may be reused.

## 2. Closed graph and budgets

```text
SQ8-F0 -> F1A -> F1B -> F1G -> F2A -> F2B -> F3 -> F4 -> F5 -> F6
            any NOT_PASS ------------------------------------------> SQ8-AR
                                                               PASS -> SQ8-AS-HANDOFF
```

F0 through F3 and F6 use zero model calls. F4 is exactly four synthetic
non-corpus calls; all four must PASS before F5. F5 is exactly 80 presentations
with four isolated calls each, at most 320 calls. Every attempt counts. The
total ceiling is 324 and retry ceiling is zero. Every live call uses exactly
`gpt-5.5` at reasoning effort `medium`, without fallback.

## 3. Fresh F1 and mandatory preauthor full-F3 boundary gate

F1A is one fresh SQ8 candidate/evaluator/runner/schema/test closure and direct
child of F0. Every active role has fresh bytes and may not alias any SQ7 active
blob or raw digest. It is zero-corpus and zero-model. F1B is its manifest-only
freeze, binding exact F1A commit, tree, paths, blobs, and raw digests. No
semantic change follows F1B.

F1G is a taskless, corpus-free, zero-model receipt-only child of F1B. Before
any author route opens, it must execute the actual target-frozen production
`_f3_checks` and `build_f3_record`, or an exactly equivalent complete F3
boundary, on a synthetic zero-corpus/no-model fixture. The positive fixture
uses the closed nested interface `receipt.validator.validator_id` and must
produce F3 `PASS` with every check true. Three exact reds must fail closed:
top-level `receipt.validator_id`, missing nested `validator_id`, and wrong
nested placement. A source assertion, isolated field lookup, mock, dictionary
only test, partial checker, or alternate boundary cannot satisfy this gate.

The canonical F1G receipt is sorted compact UTF-8 JSON with no trailing byte.
The author CLI refuses to emit or accept any task/case material unless the
exact committed F1G receipt records a PASS from that full production-real F3
boundary. Any failure routes immediately to
`SQ8-F1G:NOT_PASS->SQ8-AR`, without replacement.

## 4. Fresh corpus, F2, and F3 custody

Only after F1G PASS, two independently routed authors each create 20 fresh
cases. Neither sees the other split, predecessor material, live material, or
outcomes. An independent nonauthor validates strict schema and semantic
closure, 40 unique cases, historical digest nonreplay using only the external
digest inventory, reachability, and the fixed 80-presentation schedule.

F2A is the ordered three-parent merge `[F1G, author A, author B]`; its exact
`100644` delta is split A, split B, schedule, and corpus manifest. F2B is its
direct child and changes only the canonical run manifest. It embeds a closed
independent PASS receipt binding F1A, F1B, F1G, F2A, both authors and splits,
schedule, manifest, and validator. Only exact F2B PASS opens F3. No edit,
replacement, replay, or second attempt exists.

F3 is one zero-model preflight through the same production boundary proven at
F1G. It verifies exact Git custody, schemas, formulas, 2 x 20 and 80 x 4
closure, lifecycle, counters, budgets, privacy, nested validator identity, and
unclaimed one-shot state. Failure is terminal.

## 5. Live execution, global AND, privacy, and outcomes

F4 makes exactly four synthetic non-corpus calls. F5 runs only after all four
PASS and has no retries. F6 is a deterministic global logical AND: missing,
skipped, undefined, nonfinite, malformed, duplicate, extra, rejected, failed,
or unevaluable values are false. There is no averaging or compensation.

F6 may emit only aggregate-only JSON at
`evals/ae-sq8/f6/aggregate-result.json`. PASS may create only
`evals/ae-sq8/as/handoff.json`; every nonpass route may create only
`evals/ae-sq8/ar/terminal-decision.json`. Handoff is not downstream authority.
Raw prompts, task/case content, outputs, events, transcripts, messages, and
presentation-, assessor-, gate-, or score-level material remain private.

Even PASS proves at most one exact candidate aggregate in this frozen 40-case,
two-condition envelope. It does not prove general provider/model, product,
host, field, production, security, release, publication, promotion, or effect
claims. The next authorized transition is one zero-model, zero-corpus SQ8-F1A
commit; no later phase begins before its immediate durable gate.
