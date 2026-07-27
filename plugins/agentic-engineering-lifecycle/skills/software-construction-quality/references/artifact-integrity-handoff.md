# Artifact integrity and handoff

A handoff is complete when another person or agent can reproduce what changed, why, how it was verified, what remains uncertain, and how to operate or reverse it using the exact delivered artifacts.

## Vocabulary
- **provenance:** Trace of source, dependencies, build steps, environment and attestations that produced an artifact.
- **manifest:** Machine-readable inventory of files, versions, hashes, dependencies and metadata.
- **reproducibility:** Ability to obtain equivalent output from declared source/toolchain/configuration.
- **handoff evidence:** Decision, implementation, verification, operational and residual-risk information needed by the next owner.
- **closure gap:** Claimed completion without a delivered artifact, reproducible evidence, or owner for residual work.

## Decision procedure
1. Identify delivery boundary: source commit, package/container/binary/config/migration/model/prompt/skill bundle and environment.
2. Build from clean inputs; capture toolchain, dependency lock, SBOM/provenance, configuration and artifact hashes.
3. Run verification from or against the exact package and record commands/results.
4. Audit archive paths, permissions, symlinks, secrets, residue, unexpected binaries and missing files.
5. Prepare handoff: decisions, changes, acceptance mapping, known limitations, rollout/rollback, operations, data migration, evidence and owners.
6. Independently extract/install/run release checks; compare source and archive hashes.

## Decision table

| Handoff claim | Evidence | Failure |
|---|---|---|
| “This is what was reviewed” | commit + artifact hash + manifest | rebuilt untracked package |
| “Tests passed” | commands, versions, results on exact artifact | verbal assertion |
| “Safe to release” | release/rollback/PRR evidence | CI green alone |
| “Maintainable” | ownership, docs, dependency/retirement plan | code dump |

## Evidence obligations
- No secret or environment-specific residue is packaged.
- Every required file is present and every extra file is intentional.
- Limitations and unexecuted checks are explicit.
- Rollback and migration artifacts are delivered alongside the change.

## Review questions
1. Can a fresh environment reproduce or verify this package?
2. Does the archive contain exactly the reviewed source and assets?
3. What does the next operator need during failure or rollback?
4. Which confidence claim is unsupported by executable evidence?

## Failure patterns
- Source/artifact mismatch: tests run on a tree different from delivery.
- Handoff by summary: no manifests, commands, links or owners.
- Success inflation: missing toolchain or environment checks omitted from report.

## Research basis

Uses SLSA provenance, CycloneDX SBOM, secure release and reproducible release engineering [R98] [R99] [R108].
