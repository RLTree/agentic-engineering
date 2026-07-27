# Task Evidence and Review Contracts

A worker receives a bounded **Task Evidence Packet** and returns evidence; it never receives authority to redefine the goal, shared schema, public API, migration, or final acceptance.

Packet essentials:

- goal, candidate, plan, task, lease, worker, and context identities;
- exact path and semantic ownership plus forbidden surfaces;
- assumptions, settled decisions, interfaces, tool/effect permissions, budget, deadline, and cancellation lineage;
- required verification and return schema;
- changed surfaces, evidence, concerns, blockers, and residual risk.

A reviewer returns a **Review Verdict** bound to the exact candidate and scope:

```text
pass | pass_with_findings | reject | blocked
```

The verdict records evidence inspected, requirements checked, findings, unverifiable claims, independence, and rerun conditions. Review is advisory unless a root-owned policy explicitly makes the verdict a gate. Agent success reports and reviewer consensus are not substitutes for independent verification.

Evidence basis: R130, R136, R146.
