# Exact-delivery verification

Verify the artifact the user or system will consume, not a nearby source tree. Delivery failures often occur after source-level tests pass.

## Identify exact artifact

Examples: plugin ZIP and installed skill discovery; compiled Rust binary/container; published crate; migration executed against supported schema; hosted site; generated SDK; PR commit; report/PDF; deployment image.

Record artifact path/URI, version/commit, content digest, build configuration, target platform and dependencies.

## Verification chain

1. clean build/package from declared inputs;
2. integrity/manifests and expected file inventory;
3. install/load/start in a representative environment;
4. execute primary user/system paths with real controls;
5. exercise error, cancellation, recovery, approval and restart paths;
6. inspect logs/traces/security/network/resource behavior;
7. compare acceptance criteria to evidence;
8. retain matched outputs/screenshots/traces and artifact digest.

## Plugin-specific checks

Manifest schema, marketplace path, unique skill names, concise trigger descriptions, all local links, nonempty references, valid optional UI metadata, no secrets/hooks/MCP dependencies unless declared, install/new-session instructions, and should/should-not-trigger cases.

## Rust-specific checks

`cargo fmt --check`, `cargo check`, unit/integration/doc tests, Clippy with project policy, feature/target matrix, Miri/Loom/fault tests where applicable, dependency/advisory checks, clean release build, startup/shutdown/replay smoke test, and package/container inspection.

## Evidence report

For each criterion include method, exact target digest, environment, result, artifact/log pointer and limitations. Mark skipped/unavailable checks as not executed—not passed. Completion confidence must incorporate residual verification gaps.
