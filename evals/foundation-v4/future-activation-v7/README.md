# AQ7 future-activation corpus contract

This directory is a content-free, freeze-ready contract for two future blinded corpus roots: `AQ7-authoring` and `AQ7-heldout`. Each root contains exactly 36 cases (`AQ7-A-001`–`AQ7-A-036` or `AQ7-H-001`–`AQ7-H-036`): 32 automatic cases and 4 cases with one exact frozen explicit token. It is not a corpus and contains no prompts, labels, outcomes, or results.

The automatic distribution is six single-owner cases for each of the four atoms (24), four native/no-advice, two exactly-two, and two mechanically defined near-neighbors: exactly one `exclusion` and one `uncertainty`. A near-neighbor has a same-rule positive predicate and either that rule's exclusion predicate present or a relevant predicate uncertain, while deriving no atom. The four explicit cases invoke one frozen token per atom. Each split has a separate future-split-local nonce source and SHA-256 nonce/prompt hashes.

## Boundary and precedence

| Surface | Allowed data | Not allowed |
| --- | --- | --- |
| Model packet | task text only; runner-owned instruction and predicate order | nonce or prompt hashes, grading labels, selected atoms, advisers, requests, payloads |
| Parent deterministic resolver | schema-valid ordered predicate facts, exact task-token parse, frozen policy and base catalog | model authority, effects, external action, outcome/result inputs |
| Grading only | expected facts, selection, advisers, exact complement of advisers that must not be selected, requests, canonical resolved payload expectations | packet or inference inputs |

An exact, schema-valid qualified invocation takes precedence over automatic eligibility. Multiple qualified invocations are ambiguous; an unrecognized invocation-like token selects nothing; more than two automatic eligible atoms is `cap_exceeded` and selects nothing.

Automatic task text contains no `$` token and no canonical adviser name after case-insensitive normalization that removes spaces, hyphens, and underscores. Explicit task text has exactly one recognized frozen token and no other invocation-like token; these parse-wide checks are validator-owned invariants because JSON Schema cannot express token counting and normalization safely.

## Freeze procedure

1. Author fresh, future-only packets under the appropriate split root. Do not use results, historical corpus content, replay material, or hidden-label inputs.
2. Hash each nonce and prompt, then enforce uniqueness within its split. `prompt_sha256` is SHA-256 of the Unicode NFC-normalized task text.
3. Obtain exactly the ordered 12 predicate facts as the grading label.
4. Derive selection status, atoms, adviser mapping, the complement `expected_must_not_select_advisers`, owner-qualified requests, and the canonical resolved payload tuple mechanically from the frozen H3 protocol, frozen reference policy, and compact-reference candidate metadata. The tuple has zero to two payloads, each with its owner, ID, and SHA-256; its declared count equals its length. Do not author these projections independently.
5. Populate grading-only labels and validate the closed Draft 2020-12 shape before freezing.

The schema's `x-freeze-invariants` declares the two cross-case uniqueness checks and the required derivation source. Draft 2020-12 validates each closed JSON shape; a freeze validator must additionally enforce those declared cross-case invariants and exact derived projection.

The deterministic projection sources are fixed by the schema: H3 commit `ccbe06be9a2ef5feca4104b6918985ee9c4527c0` / tree `dd20449fdc45a73c55adb349d8c828687728ef4d`; reference-policy commit `c4e661a926e0ace78d9da83f71d9c52d311abb72` / tree `f2abb05d32a888c9054ef2e7ab3ad0f08547de88`; and base-candidate commit `f09a0544acf4b7a95fff796434273511a0683ca9` / tree `38c8c8adf3bb633d33200df1ec65f33e985ae244`, `evals/foundation-v4/reduced-four-skills/candidate.json` SHA-256 `854f67bdd03e7121bd20e5513ef61ac806d016b3a5f1d6e5891bf4d9e546eb1f`.

This contract is `future-only-unconsumed` and establishes structural closure only. It makes no runtime, provider, product, efficacy, promotion, authority, completion, or external-effect claim. It makes no model call and consumes no result or replay input; freezing may create the authorized corpus commit.
