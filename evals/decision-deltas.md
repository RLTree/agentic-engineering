# Expected Decision Deltas

The plugin should cause the following observable changes relative to an equivalent prompt without the plugin:

1. **Architecture:** fewer unjustified loops/graphs/multi-agent systems; more explicit reasons for escalation and de-escalation.
2. **Specification:** more exact deliverables, anti-goals, assumption/approval boundaries, and acceptance evidence before implementation.
3. **Control:** permissions, validation, state transitions, budgets and effects move from model prose into deterministic mechanisms.
4. **Loops/graphs:** authoritative state, stop/recovery paths, replay semantics and terminal evidence become explicit.
5. **Multi-agent:** work packages become independent, owned, schema-bound and integrated by one authority.
6. **Evaluation/security:** trajectory, recovery, provenance, capability and incident behavior are tested in addition to outcome.
7. **Software delivery:** repository files, plans, tests, evals, artifacts and handoffs carry decisions beyond the conversation.
8. **Rust:** provider/framework/protocol/runtime details remain adapters; tasks are tracked/bounded/cancellable; effects are journaled/reconcilable; verification broadens beyond `cargo check`.

Potential regressions to measure: excessive process for narrow tasks, over-triggering adjacent skills, longer latency/token use, template-driven verbosity, or architecture recommendations that are too conservative. Routing negatives and architecture de-escalation cases exist to constrain these failure modes.
