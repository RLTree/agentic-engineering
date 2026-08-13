# AE-SQ6 distinct successor qualification program

Status: **TERMINAL — SQ6-F2 NOT_PASS -> SQ6-AR**
Program: `AE-SQ6`
Candidate: `AE-SQ6-SLEC-6`
Machine authority: `evals/ae-sq6/program-authority.json`
Authority date: 2026-08-13, America/Los_Angeles
Claim ceiling: exact committed-object custody and aggregate frozen-validator evidence only; no F2 qualification, preflight, model, runtime-success, downstream, release, or effect claim

## 0. Terminal closeout (2026-08-13)

AE-SQ6 is permanently terminal. F1A
`bc097d0d690578e68a5e667897381cdfb123c725` (tree
`716b9cd881f30825efb996b1261832403475f1dc`), F1B
`278816cf9161e72822fe89197ea4570ec6c1ced6` (tree
`eda37945d5d390118f9edd5ae498b43ec6eede56`, freeze raw SHA-256
`201c61fc6e12938ec666ae1346e212f69a068aae1b05afb8e8749c532b64f7d9`),
and F1G `421ba8911139d48630f411d2af50541590f0dc93` (tree
`685a3784001e07b67c21719019a8c6c6c5e01527`, receipt raw SHA-256
`85ebe24435750ff9809ad3307af347688fa2a661af3dfe7c6012558c66c230ce`)
remain sealed historical objects. Independently routed author A
`ba59d6da1e564d859e584dd0ebe3958d961dc9ef` (tree
`ec36e54c6e67d604d802778c62777b0b43200031`, split blob
`2afa046966fdf9bfcb277cf672168c7cc5ee4e3c`, raw/content SHA-256
`ae18a859f0200db63aa4472121a211987c091e5f4a63eeb2ce58e1c60b49cb32`)
and author B `d62711dcb70133561d51aa5aadd897ef4426573f` (tree
`214ae7ffd58006058a6dd546657195895b90382c`, split blob
`59ab7f94460ab14aaf8fb2f5026d591110ebc466`, raw/content SHA-256
`ca93e97f8502b45bdf87f8dd52e20bb3b1ecad40645e705102868d4f926d6ca8`)
are consumed.

The sole frozen `validate_corpora` attempt returned
`errors=[selected_reference_anchor]`, `holds=[]`, with 40 qualified case IDs.
Its aggregate profile was none 6, single 16, two 8, cap 4, explicit 4,
uncertain 2; all six two-slot pairs were represented. It completed 400
cross-split comparisons, whose maximum similarity was
`0.2638888888888889`, below the frozen `0.80` threshold, against 768
historical digests. These passing subchecks cannot compensate for the exact
reference-anchor failure. The frozen `SQ6-F2:NOT_PASS->SQ6-AR` edge applies.

No F2A or F2B was created. F3 was not attempted, one-shot state is absent,
and model, canary, and batch calls are all zero. No replacement, replay,
repair, refreeze, reinterpretation, retry, reopen, or downstream route exists
in AE-SQ6. All SQ6 task, corpus, label, schedule, author, and result bytes are
permanently prohibited from successor reuse. The durable terminal artifact is
`evals/ae-sq6/ar/terminal-decision.json`.

The remaining sections preserve preterminal authority as history only. The
sole next route is distinct owner-authorized AE-SQ7 in
`docs/exec-plans/active/ae-sq7.md`.

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

This historical transition is closed by the terminal section above. No later
AE-SQ6 phase is authorized.
