# AE-SQ4 terminal qualification record

Status: **TERMINAL — SQ4-AR; DO NOT RELEASE OR PROMOTE**
Program: `AE-SQ4`
Candidate: `AE-SQ4-SLEC-4`
Terminal record: `evals/ae-sq4/ar/terminal-decision.json`
Authority date: 2026-08-13, America/Los_Angeles
Claim ceiling: structural F2A and standalone corpus validation only; not F2 PASS, qualification, runtime, or provider evidence

## Outcome

AE-SQ4 is terminal at `SQ4-AR`. Its exact terminal edge is:

```text
SQ4-F2:NOT_PASS -> SQ4-AR
```

No retry, reopen, resume, repair, refreeze, continuation, corpus reuse, F2A
reuse, or H6 is permitted. SQ4 may not create F2B, run F3, make a canary or
batch call, score F6, open downstream work, release, publish, or promote.

## Sealed evidence

F1A commit `3762efae80ead1461d973b4737c5dcab6bae026a` and tree
`6a071b4ee33246cc2ef448cf4d574f51abc89348` froze the implementation. F1B
commit `6357b87cfae9e488bbb1489541ec03d577803463` and tree
`6a04e5aa846cbe196425c58671bf390c499b4d59` froze the manifest without
changing the implementation identity.

Two independently routed author objects were sealed as commits
`c2a38ef3b797ca8350102eca7e0bd9dc480332eb` and
`1629eb1c4054d54f397346613a56dba22fcbd607`. Their exact merge object is F2A
commit `8b1a26dc6951d7052429197af5d8dffe3636bbb3`, tree
`fd76825a250466fbfabff8b75d307cb8cb017814`, with ordered parents F1B, author
A, and author B.

That exact F2A evidence is retained at both
`refs/heads/codex/ae-sq4-f2-not-pass` and
`refs/remotes/origin/codex/ae-sq4-f2-not-pass`; both refs must resolve to exact
commit `8b1a26dc6951d7052429197af5d8dffe3636bbb3`. This terminal packet does not
authorize moving either ref.

Aggregate-only independent recomputation passed the standalone corpus checks:
40 cases, 768 historical digests, 400 similarity checks, maximum similarity
0.406626506 below 0.80, and combined corpus SHA-256
`feaa03f2afd815bbc661d6c9de99c2cf53410f472206b2a2cd4b964f5bb1f122`.
This was recomputed evidence, not a prior durable receipt, and it did not prove
the frozen runner could accept the corpus.

## Decisive failure

Both sealed splits bind their authority to F1B:

```text
candidate_commit = 6357b87cfae9e488bbb1489541ec03d577803463
candidate_tree   = 6a04e5aa846cbe196425c58671bf390c499b4d59
```

The frozen runner requires the actual F1A implementation identity:

```text
candidate_commit = 3762efae80ead1461d973b4737c5dcab6bae026a
candidate_tree   = 6a071b4ee33246cc2ef448cf4d574f51abc89348
```

The exact fail-closed result is:

```text
PreflightError: corpus split authority is not the frozen F1 candidate
```

The standalone validator PASS and correct F2A topology cannot compensate for
this frozen runtime contract failure. F2 is therefore `NOT_PASS`.

## Calls and later stages

SQ4 made zero diagnostic, canary, batch, or other model calls. F2B was not
created; F3 preflight was not attempted; the one-shot state was not claimed;
F4, F5, and F6 were not entered; no Aggregate Qualification (AQ) result exists;
and downstream remains closed.

All SQ4 Git objects and evidence are retained without rewrite, deletion, or
migration. The only lawful next route is the separately authorized AE-SQ5
program at `docs/exec-plans/active/ae-sq5.md`. That new program must freeze a
fresh candidate and author a fresh corpus. Nothing in AE-SQ5 changes this
terminal record.
