# Review and defect learning

Review should challenge decisions, interfaces, effects, evidence and maintainability—not merely formatting. Repeated defects are signals to change the repository, tool, schema, test, harness or process so future agents cannot reproduce them easily.

## Vocabulary
- **fresh-context review:** Inspection by a reviewer or agent without the implementation session’s hidden assumptions.
- **defect escape:** Failure detected after the stage where it could have been prevented or cheaply found.
- **recurrence class:** Shared mechanism behind multiple symptoms or incidents.
- **correction capture:** Conversion of a review correction into durable guidance or deterministic control.
- **reviewability:** Ease with which intent, behavior, risk and evidence can be reconstructed.

## Decision procedure
1. Prepare a review packet: decision, requirements/ADRs, semantic diff, risk, tests/evidence, generated portions, migrations, rollout and known gaps.
2. Use fresh-context review for consequential changes; inspect state, authorization, effects, errors, recovery, observability, privacy and lifecycle burden.
3. Classify findings by mechanism and earliest prevention/detection layer.
4. Fix the defect and add a durable prevention: type/schema, API/tool contract, linter, test/eval, repository rule, template, permission, runtime invariant or training example.
5. Track defect origin, escape point, recurrence and time-to-detection; review patterns periodically.
6. Verify correction effectiveness in future changes and field outcomes.

## Decision table

| Finding | Durable correction | Weak response |
|---|---|---|
| Repeated invalid tool args | closed schema + contract tests | prompt “be careful” |
| Hidden state/effect ambiguity | typed state + journal/reconciliation | extra logging only |
| Reviewer misses authority change | semantic review checklist + policy test | more reviewers |
| Agent ignores repo convention | AGENTS/skill + example + linter | chat correction |

## Evidence obligations
- Review comments distinguish preference from requirement/risk.
- Generated code receives the same or stronger scrutiny as handwritten code.
- Correction artifacts live near the control layer that enforces them.
- Defect metrics are used for system improvement, not individual punishment.

## Review questions
1. What assumption was visible only to the implementer?
2. At which earlier layer could this defect have been prevented deterministically?
3. Is the proposed fix local, or does the recurrence class require a system change?
4. Did review inspect exact delivery and operational implications?

## Failure patterns
- Style-only review: structural and effect risks untouched.
- Comment treadmill: same correction repeated in future sessions.
- Blame metric: defect counts suppress reporting instead of improving controls.

## Research basis

Draws on agent-first engineering correction loops, SRE postmortem culture, secure SDLC, and reviewability practice [R95] [R105] [R110].
