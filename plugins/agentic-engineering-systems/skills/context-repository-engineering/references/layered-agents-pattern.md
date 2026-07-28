# Layered AGENTS.md pattern

Codex reads AGENTS.md guidance before work and applies more specific files as it descends the repository. Use that hierarchy to keep stable, high-value instructions close to the code they govern.

## Root guidance

Keep root `AGENTS.md` concise and repository-wide:

- product/system purpose;
- architecture map and dependency direction;
- global invariants and security boundaries;
- standard build/test/lint commands;
- generated-file and migration rules;
- completion/evidence expectations;
- links to deeper guidance.

## Scoped guidance

Add nested `AGENTS.md` only when the subtree has materially different conventions: a Rust crate with strict no-unsafe rules, generated protocol bindings, a UI package with visual QA, or an infrastructure area with approval requirements.

A nested file should state what it overrides or adds. Avoid copying root guidance; duplication drifts.

## Recommended form

```markdown
# Scope
Applies to: `crates/runtime/**`

## Invariants
- Every spawned task is tracked and cancelled/joined.
- Channels are bounded and overload behavior is explicit.
- No lock is held across model/network/tool await.

## Commands
- Fast: `cargo check -p runtime && cargo test -p runtime`
- Full: `cargo clippy --workspace --all-targets --all-features -- -D warnings`

## Evidence before completion
- cancellation and saturation tests;
- trace IDs on spawned work;
- no public API change without approval.
```

## Content placement test

- Stable repository expectation? AGENTS.md.
- Detailed reusable procedure? Skill.
- Large reference or standard? Link/reference file.
- Deterministic enforcement? Test/linter/schema/policy.
- Task-specific decision? Plan/ADR/task contract.

## Maintenance

Review guidance after repeated agent corrections, incidents, architecture changes, and release failures. Remove obsolete rules and replace prose with enforceable mechanisms where possible. Test a fresh task at each scope to detect conflicting instructions or over-triggering.
