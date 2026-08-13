# Start here — Design Judgment Authorial 12

## Status

Authorial 12 is a frozen experimental candidate derived from the August 12 seven-condition forensic review. It is not promoted over native, v1.3, v9, or Authorial 11.1 until the attached evaluation protocol passes.

## Preflight

```bash
cd plugin/design-judgment/engine-rust
cargo test --locked --all-targets
cargo build --locked --release
cd ../../..
./scripts/validate-package.sh
```

The registry binary must validate the frozen registry, compile the sample query under budget, validate the Truth Spine example, flag the unrelated style-fingerprint example, and report zero read-side file writes.

## Existing Work thread

1. Preserve all prior packages, results, condition maps, and scores.
2. Install Authorial 12 as a new immutable condition; do not overwrite Authorial 11.1.
3. Keep Stage C locked until the fresh protocol is frozen and the package hash is recorded.
4. Use GPT-5.6 Luna Max for parent/creator/editor/finisher and GPT-5.6 Sol High for independent selection and review.
5. Give every stage a fresh context.
6. Do not send registry administration, condition identity, discarded directions, scoring, or reviewer output to creators.
7. Keep objective verification parent-owned.
8. Treat registry abstention as valid; do not broaden queries automatically.

## Core change from Authorial 11.1

Authorial 12 adds:

- Prior Escape before direction generation;
- provenance for world-card commitments;
- an advisory cross-task style fingerprint;
- a compact Truth Spine for exact build invariants;
- unanchored design critique before detector evidence;
- explicit initial-versus-repaired scoring.

## Primary files

- `analysis/FORENSIC-REPORT.md`
- `analysis/independent-seven-condition-scores.json`
- `EVALUATION-PROTOCOL.md`
- `MASTER-WORK-EXECUTION-PROMPT.md`
- `plugin/design-judgment/`

## Claim boundary

The package and engine can be validated mechanically. Superior design judgment remains an empirical question.