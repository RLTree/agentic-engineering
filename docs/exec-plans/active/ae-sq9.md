# AE-SQ9 clean-process qualification successor

Status: **ACTIVE — SQ9-F0 AUTHORITY; SQ9-F1A NEXT**
Program: `AE-SQ9`
Candidate: `AE-SQ9-SLEC-9`
Machine authority: `evals/ae-sq9/program-authority.json`
Authority date: 2026-08-13, America/Los_Angeles
Claim ceiling: structural successor authority and unexecuted clean-process F2B acceptance repair only

## 1. Distinct terminal boundary

AE-SQ9 is a new owner-authorized program, not an SQ8 retry, repair, refreeze,
reopen, resume, reinterpretation, continuation, cure, or delayed phase. SQ8
remains terminal at `SQ8-AR`. Only aggregate terminal/process-interface
provenance and the external digest-only historical inventory may cross the
boundary. No SQ8 candidate, active-role, task, case, split, corpus, label,
schedule, author, F2, result, or execution byte may be reused.

## 2. Closed graph and budgets

```text
SQ9-F0 -> F1A -> F1B -> F1G -> F2A -> F2B -> F2G -> F3 -> F4 -> F5 -> F6
            any NOT_PASS ------------------------------------------------> SQ9-AR
                                                                     PASS -> SQ9-AS-HANDOFF
```

F0 through F3, including F2G, use zero model calls. F4 is exactly four
synthetic non-corpus calls and every call must PASS before F5. F5 is exactly
80 presentations with four isolated calls each, at most 320 calls. Every
attempt counts. The total ceiling is 324 and retry ceiling is zero. Every live
call uses exactly `gpt-5.5` at reasoning effort `medium`, without fallback.

## 3. Fresh F1 and mandatory clean-process integration gate

F1A is a mechanically fresh SQ9 candidate/evaluator/runner/schema/test closure
and direct child of F0. Every active role has fresh bytes and may not alias any
SQ8 active blob or raw digest. F1B is its manifest-only freeze. No semantic
change follows F1B.

F1G is a taskless receipt-only child of F1B. Before authoring opens it must
build a synthetic zero-corpus Git graph with the exact production F2A/F2B
shape and invoke the target-frozen `verify_ae_sq9_f2b.py` command. The verifier
must start a fresh child interpreter, load only exact target-frozen modules,
run the actual production `_load_base_state`, and emit aggregate status only.

The positive fixture deliberately imports `resolve_ae_sq9_slec` in the parent;
the fresh child must still PASS. Required reds are: resolver poisoning inside
the child, same-process validation followed by loader invocation, wrong
commit, wrong tree, wrong blob/raw digest, noncanonical run-manifest bytes, and
missing or top-level-only validator identity. Every red fails closed. Mocks,
source assertions, dictionary-only checks, or alternate loaders cannot satisfy
F1G. The canonical F1G receipt is compact sorted UTF-8 JSON with no trailing
byte, and the author CLI refuses task material without its exact committed
PASS.

## 4. Fresh corpus and durable F2 acceptance

Only after F1G PASS, two independently routed authors each create 20 fresh
cases. Neither sees the other split, predecessor material, live material, or
outcomes. An independent nonauthor performs one aggregate validation decision
using only the external digest inventory.

F2A is the ordered three-parent merge `[F1G, author A, author B]` and adds only
split A, split B, schedule, and corpus manifest as `100644` canonical JSON.
F2B is its direct child and adds only the canonical run manifest with a closed
independent receipt. Neither transient validation output nor in-process loader
acceptance constitutes F2B PASS.

F2G is a receipt-only direct child of F2B. Its sole artifact
`evals/ae-sq9/f2/f2b-loader-gate.json` binds the exact F1A/F1B/F1G/F2A/F2B
commits and trees, verifier path/blob/raw digest, child executable identity,
command arguments, clean-interpreter custody, target-frozen module ledger,
production loader result, aggregate PASS, zero corpus persistence, and zero
model calls. F2G is created only after one clean-child verifier attempt. A
rejection is terminal and no second verifier process may be launched. Only an
exact committed `SQ9-F2G:PASS` opens F3.

Before launching the child, the verifier must atomically claim owner-only
durable state at `.git-common-dir/.ae-sq9-f2g/state.json`. The claim binds the
exact F2B, verifier and executable identities plus canonical arguments. Its
only statuses are `claimed`, `completed`, and `invalid`; crash, rejection,
cleanup failure, parent drift, or missing receipt is terminal. Reset, deletion,
replacement, or relaunch cannot restore eligibility. On PASS the completed
state binds the exact canonical F2G receipt raw digest and eventual commit;
F3 verifies both the Git receipt and durable state before any preflight work.

## 5. Preflight, live execution, privacy, and outcomes

F3 is one zero-model preflight from exact F2G. F4 makes exactly four synthetic
non-corpus calls. F5 runs only after all four PASS and has no retries. F6 is a
deterministic global logical AND: every missing, skipped, undefined, nonfinite,
malformed, duplicate, extra, rejected, failed, or unevaluable value is false.
There is no averaging or compensation.

F6 may emit only aggregate JSON at `evals/ae-sq9/f6/aggregate-result.json`.
PASS may create only `evals/ae-sq9/as/handoff.json`; every nonpass route may
create only `evals/ae-sq9/ar/terminal-decision.json`. Raw prompts, task/case
content, outputs, events, transcripts, messages, and presentation-, assessor-,
gate-, or score-level material remain private.

Even PASS proves at most one exact candidate aggregate in the frozen 40-case,
two-condition SQ9 envelope. It does not prove general provider/model, product,
host, field, production, security, release, publication, promotion, or effect
claims. The next authorized transition is one zero-model, zero-corpus SQ9-F1A
commit; no authoring or later phase begins before its immediate durable gate.
