# AQ6 future activation corpus

This directory is a future-only, authoring-blinded corpus for the frozen H3 decision-certificate proposal. It contains no observation result, replay, replacement corpus, or promoted finding.

## Stable split contract

Both blinded splits validate against `activation-schema.json` (JSON Schema Draft 2020-12). The authoring split uses root `corpus_id` `AQ6-authoring`, IDs `AQ6-A-001` through `AQ6-A-036`, and nonces beginning `aq6-authoring-`. The independent held-out split uses root `corpus_id` `AQ6-heldout`, IDs `AQ6-H-001` through `AQ6-H-036`, and nonces beginning `aq6-heldout-`. The root conditional enforces the matching ID and nonce namespace for every case. Each split contains exactly 36 cases; authoring has 32 automatic cases and 4 explicit cases. Every case has the same closed top-level field set:

`id`, `nonce`, `family`, `prompt`, `normalized_prompt`, `prompt_sha256`, `mode`, `expected_decision_atoms`, `expected_advisers`, `must_not_select`, `reference_triggers`, `deterministic_reference_expectations`, `authority_prohibitions`, `effect_prohibitions`, `claim_prohibitions`, `exactly_two`, `precedence`, `declared_invocation`, `condition_blind`, `blinding_flags`, and `full_schema_or_template_expected`.

Automatic prompts have no canonical adviser name and no dollar-sign token. Explicit prompts have exactly one qualified invocation token. Expected logical atoms are ordered according to the frozen protocol and contain at most two entries. Adviser IDs are the exact parent mapping of those atoms. Reference expectations contain zero through three payload identifiers and their catalog SHA-256 values in canonical lexicographic minimal-cover order; that tuple need not match the declared order of the trigger records. References are parent-resolved only.

Deterministic reference coverage is over reachable canonical minimal-cover payloads. `aq-verify-oracle-quality` is dominated by `aq-verify-mode-selection`: its declared trigger set is a strict subset, so lexicographic minimal cover selects `aq-verify-mode-selection`. It is therefore intentionally not separately reachable or required. This is frozen base-catalog structure, not a corpus omission.

The corpus is structurally validated for schema shape, case counts, prompt hashes, unique IDs/nonces, atom-to-adviser mapping, explicit-token rules, and reference-catalog closure. That evidence establishes only structural corpus integrity. It does not establish model behavior, runtime behavior, efficacy, promotion, authority, effects, or external claims.
