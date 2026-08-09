# Supply-chain provenance

Agentic products include source, dependencies, models, prompts, skills, tools, protocol schemas, datasets, containers, infrastructure and build systems. Inventory and provenance must cover the whole behavior-producing supply chain.

## Current implementation reader and claim ceiling

Use final **NIST SSDF 1.1** as the controlling secure-development baseline. **SSDF 1.2 draft** guidance may inform proposals but is provisional and cannot establish conformance. Use **SLSA v1.2** (approved 2025-11-24), evaluating the Source and Build tracks separately. SLSA attestations establish provenance/integrity claims about declared source, build, and artifact relationships; they do not establish behavior, safety, deployment success, or release readiness. This reference yields a proposed evidence plan until the exact artifact and independently verified evidence are available.

## Vocabulary
- **SBOM:** Machine-readable inventory of software components and dependencies.
- **attestation:** Signed or verifiable statement about build, test, review or provenance.
- **build provenance:** Evidence linking an artifact to source, builder, parameters and dependencies.
- **dependency confusion:** Resolution of an unintended package due to naming or registry precedence.
- **model/tool provenance:** Identity, version, provider, configuration and policy of model or external capability used at runtime.

## Decision procedure
1. Inventory first- and third-party source, crates/packages, containers, actions, models, prompts/skills, datasets, tools/MCP/A2A endpoints, infrastructure modules and build services.
2. Pin and lock dependencies; control registries, checksums, signatures, identities and update policy.
3. Generate SBOM and provenance for exact artifacts; evaluate SLSA Source and Build evidence separately; record model/tool/schema/config versions separately when not embedded.
4. Scan vulnerabilities, licenses, malicious packages, secrets and policy violations; assess exploitability and reachability.
5. Harden CI/CD identities, runners, permissions, branch/review rules, artifact signing and release promotion.
6. Define update, emergency patch, compromise, rollback, revocation, vendor exit and retirement procedures.

## Decision table

| Asset | Integrity evidence | Runtime control |
|---|---|---|
| Source/dependencies | commit, lockfile, SBOM, signature | allowlisted registry/version |
| Build/container | provenance/attestation/hash | verified deployment admission |
| Model/prompt/skill | version/config/content hash | approved policy and rollout |
| Tool/protocol | schema/version/server identity | server auth and capability policy |
| Dataset/index | lineage/classification/checksum | access and freshness rules |

## Evidence obligations
- The delivered artifact can be traced to reviewed source and a declared builder.
- Model or tool “latest” aliases are not adequate for reproducible assurance.
- Third-party compromise assumptions and revocation paths are rehearsed for critical dependencies.
- SBOM/provenance generation is automated and independently checked.

## Review questions
1. What behavior-producing asset is missing from the inventory?
2. Can a runtime dependency change without a source commit?
3. Who can publish/promote/sign artifacts?
4. How will we identify and contain a compromised provider or package?

## Failure patterns
- Code-only SBOM: model, prompt, tool and infrastructure dependencies omitted.
- Unverifiable build: artifact provenance stops at CI success.
- Floating production: mutable tags or latest versions defeat reproduction.

## Research basis

Based on final NIST SSDF 1.1, provisional SSDF 1.2 draft material, SLSA v1.2, CycloneDX and CISA supply-chain guidance [R95] [R98] [R99] [R101].
