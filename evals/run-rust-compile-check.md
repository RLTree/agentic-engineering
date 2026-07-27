# Downstream Rust Compile and Runtime Check

This protocol was **not executed** in the release environment because `cargo`, `rustc`, and a Rust toolchain were unavailable. The Rust assets are architecture fragments, not a published crate.

## Setup

1. Create a clean temporary Rust workspace using the project’s supported stable/MSRV toolchain.
2. Copy `assets/rust/*.rs` into a small library crate and wire modules explicitly.
3. Choose and pin current compatible versions of `tokio`, `tokio-util`, `async-trait`, `thiserror`, `anyhow`, `serde`, and `schemars` according to the target repository. Do not infer production versions from this document.
4. Add unit tests for state transitions, fake model script consumption, effect status/reconciliation, supervisor cancellation, deadline, child error and bounded shutdown.

## Required commands

Adapt features/targets to the pinned crate, then run:

```bash
cargo fmt --all -- --check
cargo check --workspace --all-targets
cargo test --workspace
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo build --workspace --release
```

Run supported feature combinations and target/MSRV jobs. Add `cargo miri test` for compatible unsafe/FFI-sensitive code and Loom tests for any extracted synchronization primitives. Run RustSec-compatible advisory checks under repository policy.

## Required fault scenarios

- cancellation before permit, during work, and during shutdown;
- deadline while waiting and while executing;
- child task returns error or panics;
- shutdown drain deadline;
- two workers prepare the same action;
- crash after remote success before journal confirmation;
- same idempotency key with a different arguments digest;
- serialization/schema snapshots and invalid wire input.

## Evidence

Record toolchain/dependency versions, commands, exit codes, test output, exact source digest, warnings, skipped checks and residual limitations. Fix compile/lint/design problems in the plugin assets or clarify that a fragment is pseudocode; never mark an unavailable command passed.
