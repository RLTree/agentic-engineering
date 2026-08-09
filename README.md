# Agentic Engineering 4.0.0 package set

Agentic Engineering is a local marketplace of four explicit, proposal-only advisory packs. It helps a host choose and document engineering decisions; it does not install services, widen permissions, make network calls, or grant itself authority to perform effects.

> **Research authority:** `docs/foundations/current-2026-08-08.md` and its
> register control current decisions. `RESEARCH.md`, `RESEARCH-V3-ADDENDUM.md`,
> `SOURCE-MANIFEST.json`, and `EVIDENCE-MATRIX.csv` are historical lineage
> snapshots through 2026-07-22, not current release or behavioral evidence.

## Current identity

| Axis | Current value | Meaning |
|---|---|---|
| Package-set version | `4.0.0` | The coordinated four-pack candidate described here. |
| Package versions | `4.0.0` | The version in each package manifest. |
| Marketplace contract | `1.0` | The schema version of `.agents/plugins/marketplace.json`. |
| Foundation snapshot | `2026-08-08` | Current research decision authority, not package behavior evidence. |

The marketplace contains 30 unique skills: 8 core, 10 lifecycle, 7 Rust, and 5 systems skills.

| Pack | Skills | Scope |
|---|---:|---|
| `agentic-engineering` | 8 | Control architecture, governed learning, verification, and product decisions. |
| `agentic-engineering-lifecycle` | 10 | Discovery through retirement decision support. |
| `agentic-engineering-rust` | 7 | Rust architecture, runtime, durability, protocol, verification, and observability advice. |
| `agentic-engineering-systems` | 5 | Repository, workflow, and multi-agent decision support. |

All four packs remain explicit. Harness UltraGoal is the separate external implicit front door when a host chooses to use one; Agentic Engineering skills do not receive effect or claim authority.

## Research authority and evidence

`docs/foundations/current-2026-08-08.md` and `docs/foundations/register.csv` are the current external-research authority. The historical surfaces named above remain useful for provenance and vocabulary, but do not establish current implementation guidance or release quality.

The default release command checks the package structure of the exact local candidate only. Its passing result supports a structural-package claim, not activation, useful advice, composition, host installation, or field usefulness. Those claims have separate gates in `EXECPLAN.md` and `EVALUATION.md`.

## Validation

```text
python3 scripts/release_check.py
python3 -m unittest discover -s tests -v
```

The release command is zero-write by default and returns the candidate identity, the checks actually run, and their observations. An explicit `--write --output` pair can persist a rendered package-set description for a named consumer.

See `scripts/README.md` for the current structural validators and the status of historical inventory diagnostics.

## Installation and limits

Use the host's current marketplace workflow to add this repository and install only the packs needed for the task. Start a fresh host session if discovery needs refresh. No local package validation proves a host journey; installation, discovery, coexistence, and removal require the later AH stage on an authorized clean host.

The included Rust material is advisory source material, not a supported crate. No field evaluation is authorized by this package set. AF requires separate authorization and cannot be inferred from structural validation.
