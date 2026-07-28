# Correction-to-infrastructure ladder

Every repeated correction is evidence that a decision is living at the wrong layer. Promote it to the cheapest durable mechanism that can enforce it.

## Ladder

1. **Task contract:** run-specific outcome, scope or assumption.
2. **AGENTS.md:** stable repository convention or command.
3. **Skill/reference/template:** reusable judgment process or artifact form.
4. **Plan/ADR:** consequential tradeoff and rationale.
5. **Type/schema/API:** invalid states or inputs become unrepresentable/rejectable.
6. **Test/eval:** desired behavior becomes regressible evidence.
7. **Linter/script/CI gate:** deterministic rule is automatically enforced.
8. **Harness policy/capability/approval:** privileged or safety-critical rule enforced outside model.
9. **Architecture change:** recurring failure removed by ownership/boundary/topology redesign.

## Selection questions

- Is the correction specific to this task or stable across work?
- Is it judgment or deterministic?
- What is the severity and recurrence rate?
- Can invalid behavior be prevented rather than detected?
- Does enforcement need authority outside the model?
- What maintenance burden does the mechanism add?

## Promotion record

For a recurring correction record examples, frequency, impact, root layer, selected mechanism, counterexamples, test/eval, owner and removal/revisit condition.

## Avoid overfitting

A single weird failure should not create global instructions that trigger everywhere. Add positive, negative and ambiguous routing/eval cases. Keep AGENTS.md concise; put depth in skills/references and deterministic rules in code.

## Success metric

Measure reduced correction turns, fewer repeated failures, higher accepted-change rate, lower risky-action rate and faster evidence-backed completion—not documentation volume.
