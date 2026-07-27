---
name: product-fitness-engineering
description: Use when representative user value, journey quality, intervention burden, recovery, or continuance must be assessed.
---
# Product Fitness Engineering

## Core principle

Product fitness is representative evidence that intended users can reach and retain verified value with acceptable risk, intervention, recovery, and supervisory burden inside a declared operating envelope.

## Outcome

Produce a **Product Fitness Evidence Plan** for learning whether the product helps the intended user complete consequential work in the intended context—not merely whether code, tests, telemetry, or an agent run exists.

## Workflow

1. **Define the audience and work.** Name the user or operator, job to be done, context, consequence level, alternatives, first value event, desired outcome, and reason for continuance.
2. **Declare the operating envelope.** Specify repositories, tasks, environments, integrations, permissions, autonomy, and excluded populations.
3. **Choose representative evidence.** Sample real work across important variation. Distinguish agent-use, expert-use, new-user, repeated-use, and human-use evidence.
4. **Instrument the journey.** Join task, trajectory, action, effect, outcome, intervention, recovery, near miss, and surrounding human work. Minimize content collection and preserve privacy.
5. **Run two complementary views.**
   - a read-only **Field Pulse** for time-windowed value, reliability, guardrails, evidence quality, and missing-data signals;
   - a **Product Journey Review** that follows complete representative workflows through success, error, diagnosis, recovery, and retained state.
6. **Measure supervisory work.** Record time to verified value, human interventions, review rounds, correction effort, context switching, cognitive load, trust burden, and recovery burden.
7. **Interpret cautiously.** Separate assignment from exposure, activity from value, correlation from causation, and first use from continuance. Record contradictory and subgroup evidence.
8. **Decide.** Return advance, hold, narrow, revert, stop, redesign, or gather-more-evidence with a claim ceiling and evidence-to-change handoff.

## Output contract

Include:

- audience, job, context, value, outcome, and continuance hypothesis;
- representative-work sample and operating envelope;
- exposure/autonomy state and decision rights;
- Field Pulse metric contracts and data-quality checks;
- end-to-end journey map and scenario matrix;
- intervention, recovery, near-miss, risk, accessibility, and human-work evidence;
- privacy, retention, sampling, and cardinality policy;
- advance/hold/narrow/revert/stop thresholds;
- evidence-to-change record and maximum supported product claim.

## Hard rules

- Agent-use evidence cannot be relabeled as human-use evidence.
- Install success, passing tests, task throughput, satisfaction, or one successful journey cannot alone prove product fitness.
- Do not add a telemetry platform solely to satisfy a report row.
- Field Pulse is a read model; it cannot promote a product claim.

## Common failures

- Relabeling agent-use, expert-use, or one successful journey as representative human-use evidence.
- Confusing activity, throughput, install success, telemetry presence, or satisfaction with verified value.
- Ignoring correction, review, cognitive, diagnosis, and recovery work transferred to people.
- Letting a read-only pulse or reviewer promote a product claim.


## References

- `references/field-pulse-contract.md`
- `references/journey-review-contract.md`
- `references/developer-supervisory-work.md`
- `references/fitness-evidence-and-claim-ceilings.md`
- `../../references/product-fitness-observation.md`

Use `../../assets/templates/product-fitness-field-pulse.md`, `../../assets/templates/product-journey-review.md`, and `../../assets/templates/product-fitness-evidence-plan.md`.
