# Evidence-to-change loop

The evidence-to-change loop ensures authentic-use observations alter durable product and system controls rather than remaining dashboards, anecdotes, or postmortem prose.

## Vocabulary
- **observation:** Traceable field fact with workload, versions, outcome, and evidence quality.
- **mechanism hypothesis:** Testable explanation for why the observation occurred.
- **change surface:** Product workflow, UX, requirement, context, prompt/skill, tool, permission, loop/graph, runtime, eval, monitor, documentation, or architecture.
- **closure evidence:** Proof that the intervention addressed the mechanism without unacceptable regression.
- **learning debt:** Material observations lacking a decision, owner, test, or closure.

## Decision procedure
1. Normalize a material observation: event, task segment, outcome, trajectory/effect details, human work, versions, severity, frequency, and evidence limitations.
2. Distinguish symptom, contributing conditions, and candidate mechanism; seek disconfirming traces and successful contrasts.
3. Choose the control layer capable of preventing, detecting, recovering from, or making the behavior easier to use.
4. Create a durable change and at least one regression/eval/monitor that would catch recurrence.
5. Roll out progressively; compare affected segments and guardrails; record keep/revert/narrow decision.
6. Close only when evidence links observation → mechanism → intervention → verification → field result; otherwise retain as learning debt.

## Decision table

| Observed pattern | Likely change surface | Required follow-through |
|---|---|---|
| Repeated user correction | UX, requirement, tool schema or context | Representative fixture plus edit/intervention metric |
| Unsafe or ambiguous effect | Permission, approval, idempotency, reconciliation | Fault/effect test plus incident guardrail |
| Tool misuse or loop thrash | Tool contract, state, stop/recovery policy | Trajectory eval and repeated-action detector |
| Success only with expert workaround | Workflow/product design, onboarding, automation boundary | Success deconstruction and novice cohort evidence |

## Evidence obligations
- Every material field item has owner, status, decision date, linked artifact, and closure criterion.
- A prompt tweak is not the default fix when deterministic controls, UX, tools, state, permissions, or architecture own the failure.
- Successful traces produce reusable patterns and eval fixtures, not only praise.
- No-change decisions record rationale and the evidence threshold that would reopen them.

## Review questions
1. Which mechanism, not merely symptom, does the evidence support?
2. At what control layer can recurrence be prevented or made observable?
3. What test or monitor would have caught this before the field?
4. Did the change improve the intended segment without shifting burden or harm elsewhere?

## Failure patterns
- Dashboard completion: metrics reviewed but no artifact changes.
- Prompt reflex: all failures become instruction edits.
- Incident-only learning: successes, interventions, abandonment, and near misses are ignored.

## Research basis

Grounded in current agent-improvement loops, macro/trajectory evals, SRE incident learning, and human-AI workflow evidence [R71] [R72] [R74] [R93] [R104] [R105].
