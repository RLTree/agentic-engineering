# Thin-slice risk planning

Plan delivery around the smallest end-to-end slices that retire the highest risks and produce acceptance or field evidence. Component completion and ticket volume are weak proxies for product learning.

## Vocabulary
- **vertical slice:** End-to-end behavior crossing UI/API, domain, data, tools/effects, operations and evidence.
- **risk-first sequencing:** Ordering work by uncertainty/consequence reduction rather than component dependency alone.
- **walking skeleton:** Minimal deployable path proving architecture, integration and delivery mechanisms.
- **decision latency:** Time from identifying uncertainty to obtaining evidence and acting on it.
- **integration debt:** Risk accumulated when components remain uncombined until late delivery.

## Decision procedure
1. List decisions and risks blocking value, safety, architecture, operations or exposure.
2. Define a walking skeleton that exercises identity, state, tool/effect boundary, trace, verification, deploy and rollback.
3. Slice by representative mission thread and outcome; include quality/security/operability evidence within each slice.
4. Order slices by information gain, risk retirement, reversibility, dependency and ability to support authentic-use learning.
5. Set work-in-progress limits, ownership boundaries, integration cadence, acceptance evidence and stop/pivot triggers.
6. Review delivery metrics alongside product/evidence outcomes; adjust plan when learning changes priorities.

## Decision table

| Slice type | Primary evidence | Anti-pattern |
|---|---|---|
| Architecture skeleton | Build/deploy/trace/recover path | Months of component scaffolding |
| Workflow slice | Representative end-to-end outcome | UI and backend roadmaps separated |
| Risk spike | Discriminating result | Open-ended research ticket |
| Field-learning slice | Controlled authentic-use decision | Big-bang beta |

## Evidence obligations
- Each slice has a user/system outcome and evidence, not just code scope.
- Security, observability, rollback and operations are built with the slice.
- Parallel work has exclusive ownership or explicit merge/fan-in contracts.
- A milestone may be canceled when evidence removes its rationale.

## Review questions
1. What decision or risk does this slice retire?
2. Can it be deployed, observed, rolled back and learned from independently?
3. Are we postponing integration or consequential effects to the end?
4. What is the smallest slice that tests the architecture under real constraints?

## Failure patterns
- Horizontal milestone: layers “complete” with no usable outcome.
- Risk-last plan: easy features precede critical uncertainty.
- Evidence-free velocity: throughput rises while decision latency and rework worsen.

## Research basis

Combines agile beta/thin-slice delivery, SRE launch practice, DORA evidence, and controlled field learning [R91] [R102] [R106] [R110].
