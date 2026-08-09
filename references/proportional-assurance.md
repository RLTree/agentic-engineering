# Proportional Assurance

Assurance intensity should follow consequence, reversibility, novelty, uncertainty, blast radius, and oracle quality—not task size alone.

| Profile | Typical use | Minimum posture |
|---|---|---|
| Micro | local, reversible, no behavior/effect change | current-state check, focused validation, clean diff |
| Standard | bounded behavior change with good oracle | reproduction or requirement trace, targeted tests, review, artifact check |
| Elevated | cross-boundary, stateful, concurrent, data, security, migration, or operational change | explicit failure model, independent review, integration/fault evidence, rollback |
| Critical | irreversible or high-consequence external effect | authority review, threat and misuse cases, staged exposure, stop/recovery, same-surface proof |

Profiles tailor evidence; they never weaken security, privacy, authorization, provenance, or destructive-effect boundaries.

Current foundation: SSDF 1.1 is controlling and SSDF 1.2 remains draft provisional
(`F-SSDF-11`, `F-SSDF-12-DRAFT`). Historical lineage: R128, R132; R151 is a
non-authoritative duplicate of the draft entry.
