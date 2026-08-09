# Research and Compatibility Update Policy

## Current authority

`docs/foundations/current-2026-08-08.md` and
`docs/foundations/register.csv` are the sole current external-research authority.
`RESEARCH.md`, `RESEARCH-V3-ADDENDUM.md`, `SOURCE-MANIFEST.json`, and
`EVIDENCE-MATRIX.csv` are historical lineage through 2026-07-22. Their source
count, coverage, and length do not establish package quality or release validity.

Use official or primary sources first. Recheck version-sensitive guidance at
the point of use and follow the review trigger in the current register.

## Decision-delta workflow

For a source change:

1. identify the exact old and new claim and its `foundation_id`;
2. identify the affected current repository decision and its canonical owner;
3. choose `no_change`, `update`, `replace`, or `retire`;
4. name the cheapest falsifier for the proposed decision delta;
5. change only the canonical source, code, test, configuration, skill, or
   reference that consumes the decision;
6. add or update a held-out case only when behavior could materially change;
7. validate at the narrowest affected boundary before broader release checks;
8. add one compact row to `docs/foundations/decision-log.csv` only when the
   decision must survive the session.

A source change does not automatically update the historical manifest, evidence
matrix, monograph, every skill, a schema, a template, a receipt, or a release
claim. `no_change` is a valid result when the current decision remains supported.

## Persistence and claims

Persist only adopted cross-session decisions, canonical implementation or tests,
or evidence with a named consumer or custody need. Routine source discovery,
validation, creator/reviewer work, and no-op review remain zero-write by default.

Source review supports only the exact stated principle. Structural validation
supports only the checked package structure. Activation, isolated adviser value,
composition, clean-host behavior, and field usefulness require their own stage
evidence and cannot be inferred from source inventory or documentation.

## Compatibility and retirement

Before retiring guidance, identify current readers and package consumers,
migrate or remove them, prove the rendered package no longer contains the active
surface, and rerun the affected checks. Use Git history for superseded material;
do not create an in-repository archive. Never silently reinterpret an effect,
approval, protocol, or replay contract for an in-flight system.
