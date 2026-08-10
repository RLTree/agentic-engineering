# AQ3 blinded future activation corpus

This directory is a **proposal-only, blinded, future-run-only** activation corpus. It is not evidence that any candidate passes AQ, and it contains no execution results.

## Scope and custody

- This corpus has no candidate authority, routing authority, effect authority, or claim authority.
- The automatic prompts do not name the four advisers. The eight explicit cases each declare exactly one backticked `$`-prefixed evaluator alias.
- The runner receives prompts only. Expected selections, prohibited selections, precedence, and reference expectations remain hidden labels.
- The parent selects any permitted reference payload; references are expectations for grading, not a blanket loading instruction.
- Each case forbids effect and claim authority.

## Shape

Each split contains 36 cases: 32 automatic and four explicit. Across authoring plus held-out, the automatic distribution is 12 decomposition, 12 task-contract, 12 verification, 12 learning, eight native-sufficient, and eight near-neighbor cases. Near-neighbor cases are evenly split between precedence and exactly-two-owner decisions.

The corpus tests the minimum necessary decision owner: a single-owner case must not stack advisers, a precedence case selects the more specific owner instead of a plausible broader or neighboring owner, an exactly-two case selects only those two owners, and a native-sufficient case selects none.

## Blinding and anti-reuse

`activation-authoring.json` and `activation-heldout.json` are separate frozen splits. No held-out outcome may inform authoring changes. Every case records an AQ3-only identifier, family, nonce, semantic signature, unconsumed status, and a no-replay policy. A future validator must check globally unique IDs/families/nonces/normalized prompts, automatic-name exclusion, explicit one-alias compliance with no residual canonical adviser name, exact expected/prohibited partitioning, precedence/cardinality agreement, and exact reference-trigger coverage.

After either split is used to obtain results, do not replay it for repair or promotion. Create a new blinded future holdout from a changed hypothesis instead.

## Format

`activation-schema.json` is JSON Schema Draft 2020-12. The two corpus files use schema version `3.0`; both contain only unconsumed cases and no route observations or results.
