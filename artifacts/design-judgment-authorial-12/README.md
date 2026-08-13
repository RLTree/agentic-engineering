# Design Judgment Authorial 12.0.0-experimental.1

This isolated artifact tree contains the proposed successor to Authorial 11.1, the independent seven-condition forensic re-review, a compact Rust registry engine, and the Work testing overlay.

## Core hypothesis

Authorial 11.1 materially raised the visual and authorial ceiling, but the ten unrelated artifacts converged on a recognizable house prior: warm paper, moss/teal/green with rust/coral/gold accents, classic serif or restrained system type, rounded panels, and soft elevation. Authorial 12 keeps the successful stage separation while adding two narrow corrections:

1. **Prior Escape** in `design-direct`: identify both the category default and the model's own recent cross-task prior before deriving directions.
2. **Truth Spine** in the build handoff: carry only the few invariants whose failure explained the ten Authorial 11.1 repairs.

A parent-only style fingerprint is advisory. It can request re-derivation when unrelated outputs are too similar, but it cannot choose a style or block an artifact by itself.

## Stage architecture

```text
Optional Brief Studio
→ design-direct
→ world card + truth spine
→ fresh native build or one specialist
→ design-edit
→ design-finish
→ parent verification
→ optional design-systematize
```

Each stage runs in a fresh context. The creator never receives registry administration, scoring, reviewer output, discarded directions, or campaign identity.

## Test boundary

The supplied August 12 handoff contains 70 joined candidates, but no final blind numeric review for slot 07. The analysis in this package is an independent forensic re-review, not a replacement for a fresh blind panel.

## Build

```bash
cd engine-rust
cargo test --locked --all-targets
cargo build --locked --release
cd ..
./scripts/package.sh
```

The GitHub Actions workflow runs the same gates and uploads the final archives.