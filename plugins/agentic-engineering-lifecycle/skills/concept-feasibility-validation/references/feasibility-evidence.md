# Feasibility evidence

Feasibility is multidimensional: a system can be technically possible yet undesirable, unsafe, economically unsustainable, legally impermissible, operationally unserviceable, or dependent on unavailable organizational change.

## Vocabulary
- **technical feasibility:** Ability to implement required behavior and quality attributes with available technologies.
- **operational feasibility:** Ability to deploy, monitor, support, recover, and govern the system in its intended environment.
- **workflow feasibility:** Fit with roles, incentives, decision rights, timing, handoffs, and user capability.
- **economic feasibility:** Expected value relative to build, run, review, support, risk, migration, and retirement cost.
- **assurance feasibility:** Ability to produce evidence sufficient for required safety, security, compliance, and stakeholder confidence.

## Decision procedure
1. Define the proposed operating concept and top lifecycle assumptions.
2. Assess desirability/workflow, technical capability, data, integration, performance/cost, security/privacy, compliance, reliability/operations, organization, supply chain, and retirement.
3. For each dimension, choose representative evidence and explicit thresholds; record dependencies and transfer assumptions.
4. Exercise failure, recovery, review burden, edge segments, and adverse conditions—not only nominal success.
5. Assemble a feasibility case with supported, conditional, unsupported, and unknown claims; calculate next option-value decision.

## Decision table

| Dimension | Evidence example | Red flag |
|---|---|---|
| Model/task | Representative corpus plus trajectory/error analysis | Average score hides severe segment |
| Tool/effect | Sandbox and real-adapter reconciliation tests | Unknown external outcome |
| Operations | Load/fault/shutdown plus runbook exercise | Requires heroic manual recovery |
| Economics | Per-outcome cost with review/support burden | Only inference-token cost counted |
| Governance | Policy mapping and approval/appeal workflow | No accountable authority |

## Evidence obligations
- Evidence includes failure distribution and human effort, not only task success.
- Costs cover acquisition, integration, inference, tools, observability, review, support, incidents, compliance, migration, and exit.
- Third-party/model/provider dependencies have alternatives, contracts, quotas, data terms, and exit assumptions.
- Unknowns that affect go/no-go remain visible; confidence language cannot close them.

## Review questions
1. Which feasibility dimension is most likely to kill the concept after deeper investment?
2. What evidence comes from the actual deployment environment?
3. What human work or organizational change is required to sustain success?
4. Can we assure and retire the system, not merely build it?

## Failure patterns
- Technical-only feasibility: a working model call is treated as product viability.
- Happy-path economics: hidden review, failure and support costs omitted.
- Provider optimism: limits, data terms, lock-in, outage and retirement ignored.

## Research basis

Synthesizes lifecycle, quality, secure development, SRE and deployed-AI monitoring [R75] [R83] [R86] [R95] [R102].
