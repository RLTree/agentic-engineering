# CI and supply-chain controls for Rust agent systems

Agentic applications combine privileged automation, generated code and fast-moving SDK/protocol dependencies. CI should verify code, exact artifacts and dependency provenance.

## Pipeline stages

1. locked dependency restore and toolchain pin/verification;
2. formatting, check, test, Clippy and docs;
3. feature/target/MSRV matrix;
4. schema/protocol snapshots and generated-code drift;
5. concurrency/fault/Miri/Loom jobs as applicable;
6. advisory, license and secret scanning;
7. clean release build/package/container with SBOM/provenance where required;
8. startup/shutdown/replay smoke and exact artifact integrity;
9. signed/policy-controlled publish/deploy with approval.

## Dependencies

Commit `Cargo.lock` for applications; follow library policy for lockfile publishing while testing resolved dependencies. Review diffs for build scripts, proc macros, native/FFI and network-capable dependencies. Use RustSec-compatible advisory tooling such as `cargo-audit` or organizational equivalents, and define severity/exception ownership.

## Generated code

Record generator and source version. Regenerate in CI and fail drift where deterministic. Treat model-generated code as untrusted source requiring the same review/tests; do not grant generated build scripts automatic privilege.

## Secrets and permissions

Use short-lived CI identities and environment-scoped deployment permissions. Untrusted pull requests must not receive release secrets. Separate read/test from publish/deploy jobs and protect approval rules.

## Reproducibility

Pin Rust toolchain, base images and critical generators; use locked/frozen builds as policy permits; record artifact digests and source commit. Verify the package/container contents and licenses, not only compilation.

## Failure handling

Skipped optional tools are visible as not executed. Security exceptions have owner, rationale and expiry. A passing aggregate pipeline cannot override a failed critical invariant or supply-chain gate.
