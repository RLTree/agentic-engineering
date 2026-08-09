# Validation scripts

## Current release check

```text
python3 scripts/release_check.py
```

The default command is zero-write. It validates the complete four-package candidate, captures its identity, and returns only the checks actually executed, their observations, and structural claim states. A passing result is evidence of package structure only. It is not activation, advice-value, composition, host-installation, protocol, or field evidence.

An output file is opt-in and requires both flags:

```text
python3 scripts/release_check.py --write --output evals/results/agentic-pack-set.json
```

Use this only when a named consumer needs the rendered package-set description. The command does not create per-check receipts by default.

## Structural helpers

`package_validation.py` supplies the release check's package, marketplace, manifest, skill-identity, and package-content validation. Archive validation remains an AH responsibility. The test suite is the current executable specification for the structural negative cases.

## Historical inventory diagnostics

The remaining scripts inspect historical Version 2/3 inventories, source lineage, routing corpora, static assets, or development contracts. They are useful diagnostics but are not mandatory A1 release gates and do not establish behavioral quality. In particular, source counts, coverage totals, schemas, and static Rust checks do not prove activation, useful advice, host behavior, or field value.

Some legacy scripts accept `--write` for an explicit development report under `evals/results/`. Do not run those write modes for ordinary release validation.
