# Lifecycle stage map

Use the stage map to locate the current decision, expose missing predecessor evidence, and preserve feedback to earlier assumptions. Stages are concurrent decision systems, not mandatory sequential departments.

## Vocabulary
- **lifecycle posture:** Which decision systems are active, upcoming, deferred, blocked, or being revisited.
- **decision horizon:** How long a decision is expected to remain valid before evidence or conditions require review.
- **thin slice:** The smallest end-to-end product increment that can test a material assumption in representative conditions.
- **feedback edge:** A named path by which field, quality, security, or operational evidence changes an earlier requirement or decision.
- **retirement obligation:** A future duty for migration, data disposition, contract closure, evidence preservation, or dependency removal.

## Decision procedure
1. State the product outcome, system boundary, operating envelope, consequential effects, and current decision.
2. Mark discovery, validation, specification, architecture/planning, construction/quality, secure release, operations/SRE, experimentation, maintenance, and retirement as active/upcoming/deferred/revisit.
3. For each active stage, name the claim, evidence, owner, decision rule, artifact, and trigger that sends work backward or forward.
4. Choose the highest-risk uncertainty and define the smallest slice or investigation capable of changing the decision.
5. Review cross-lifecycle threads: security, privacy, accessibility, reliability, cost, traceability, human decision rights, data/model/tool versions, and retirement.

## Decision table

| Stage condition | Action | Do not |
|---|---|---|
| High uncertainty, reversible choice | Run discovery/validation and a thin slice | Write detailed downstream plans as facts |
| High consequence or irreversible commitment | Deepen requirements, tradeoff analysis, assurance and approval | Use speed as justification to skip evidence |
| Product already in use | Run operations, field learning, maintenance and discovery concurrently | Freeze requirements because release occurred |
| Declining value or replacement available | Begin deprecation/retirement evidence early | Wait for an incident or forced shutdown |

## Evidence obligations
- Every stage transition identifies the decision it enables and the evidence that could block it.
- Requirements and architecture remain linked to tests, operational signals, field outcomes, and retirement responsibilities.
- Deferred work has rationale, owner, deadline or trigger; “later” is not a plan.
- Human approval is explicit for value tradeoffs, residual-risk acceptance, and irreversible changes.

## Review questions
1. Which lifecycle decision are we actually making now?
2. What evidence is missing because an upstream assumption was never tested?
3. What field or operational signal would force us to revisit this plan?
4. What obligation are we creating for maintainers, operators, users, or retirement?

## Failure patterns
- Stage theater: producing phase documents without a decision or evidence rule.
- Forward-only planning: no edge from production learning back to discovery, requirements, architecture, or evals.
- Premature commitment: deep implementation before the riskiest assumption is discriminated.

## Research basis

Grounded in lifecycle standards, agile service development, SRE, and deployed-AI monitoring [R75] [R83] [R84] [R90] [R91].
