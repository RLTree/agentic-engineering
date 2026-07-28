# Go, pivot, hold, and stop criteria

Predeclared decision criteria protect validation from sunk-cost bias and post-hoc storytelling. Criteria should include value, harm, workflow, feasibility, economics, evidence validity, and strategic/lifecycle fit.

## Vocabulary
- **go:** Evidence justifies the next bounded commitment, not unlimited implementation.
- **conditional go:** Proceed only inside a narrowed scope or after named evidence/control closes.
- **pivot:** Change user, problem, workflow, mechanism, envelope, autonomy, architecture, or business model based on evidence.
- **hold:** Pause commitment while collecting specific evidence or resolving an external dependency.
- **stop:** Terminate or retire the concept because expected value or assurance is insufficient.

## Decision procedure
1. State the decision horizon and maximum commitment under consideration.
2. Define primary value threshold, workflow/adoption evidence, safety/security/privacy guardrails, technical/operational thresholds, economic bounds, and evidence-validity conditions.
3. Specify segment-level and severe-event criteria that override a favorable average.
4. Precommit actions for go/conditional/pivot/hold/stop and name decision authority.
5. After evidence, run an adversarial review: alternative explanations, missing cohorts, invalid measurements, and sunk-cost pressure.
6. Record decision, rationale, residual uncertainty, next smallest commitment, and revisit/termination trigger.

## Decision table

| Evidence pattern | Decision | Next move |
|---|---|---|
| Value and guardrails supported | Go to next thin slice | Increase commitment minimally |
| Value only in bounded segment | Conditional go/narrow | Encode envelope and validate segment |
| Mechanism works, workflow/value fails | Pivot | Change interaction or problem |
| Evidence invalid or key dependency pending | Hold | Repair measurement or dependency |
| Critical value/safety/economic assumption fails | Stop | Preserve learning and close obligations |

## Evidence obligations
- Criteria are written before seeing the decisive result.
- A “go” never authorizes work beyond the evidence-supported envelope.
- Severe safety, privacy, security, legal, or irreversible-effect failures can be hard stops.
- Stop includes data/artifact cleanup, stakeholder communication, and learning preservation.

## Review questions
1. What result would make us stop despite enthusiasm?
2. Are thresholds materially tied to user/system outcomes or easy activity metrics?
3. Is a conditional result being rhetorically converted into full approval?
4. What is the least irreversible next commitment?

## Failure patterns
- Goalpost drift: thresholds change after unfavorable results.
- Perpetual pivot: the concept is never allowed to fail.
- Binary gate: mixed evidence is forced into go/no-go without narrowing or targeted follow-up.

## Research basis

Based on disciplined product validation, experiment contracts, risk-tailored lifecycle decisions, and human-AI evidence [R79] [R90] [R91] [R93].
