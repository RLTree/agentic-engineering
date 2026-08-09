# Risk-Based Evidence Ladder

Escalate evidence only when a lower rung cannot support the claim.

```text
static/schema check
→ focused unit or contract test
→ integration and artifact check
→ fault/concurrency/security/performance check
→ representative journey
→ progressive rollout or controlled field evidence
→ repeated use and operations evidence
```

Define the claim first. Then select the lowest rung that can falsify it. A higher rung does not erase a failure at a lower authoritative boundary, and broad test volume does not compensate for missing same-surface evidence.

Use proportional assurance profiles:

- **micro:** reversible, local, no behavior or effect change;
- **standard:** bounded behavior change with strong deterministic oracle;
- **elevated:** cross-boundary, stateful, concurrent, data, security, or operational change;
- **critical:** irreversible, external, safety-, security-, privacy-, or mission-significant effect.

Current foundation: SSDF 1.1 is controlling and SSDF 1.2 remains draft provisional
(`F-SSDF-11`, `F-SSDF-12-DRAFT`). Historical lineage: R128, R132; R151 is a
non-authoritative duplicate of the draft entry.
