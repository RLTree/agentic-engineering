# Prototype and spike strategy

Choose artifacts for learning power, not resemblance to a finished product. A prototype explores user/workflow/value; a technical spike reduces implementation or operational uncertainty; a pilot exercises an integrated system in a bounded real context.

## Vocabulary
- **prototype:** Disposable or evolvable representation used to learn about workflow, interaction, value, or policy.
- **technical spike:** Time-bounded implementation used to answer a technical feasibility or risk question.
- **Wizard-of-Oz:** Human-performed capability presented through the proposed workflow to test value and interaction without full automation.
- **concierge test:** High-touch manual delivery used to understand the end-to-end outcome and hidden work.
- **pilot:** Bounded integrated use with representative participants and explicit operational controls.

## Decision procedure
1. Write one primary learning question and the decision result must change.
2. Select fidelity by uncertainty: paper/workflow prototype, clickable prototype, model/tool experiment, integration spike, load/fault test, shadow run, recommendation-only pilot, or bounded field slice.
3. Identify intentionally fake, manual, stubbed, or uncontrolled components; prevent their results from being mistaken for system evidence.
4. Define participant/task sample, success and guardrail evidence, timebox, cleanup, data handling, and stop criteria.
5. Run, capture raw observations, compare alternatives, and record what transfers—or does not transfer—to production.
6. Decide discard, repeat, narrow, pivot, promote into a hardened slice, or stop.

## Decision table

| Question | Artifact | Production inference limit |
|---|---|---|
| Does workflow solve the right problem? | Low/medium fidelity prototype | No reliability or scale claim |
| Can model/tool perform representative task? | Executable experiment | No adoption or effect-safety claim |
| Can integration meet latency/cost? | Technical spike | No maintainability claim unless designed/tested |
| Can joint workflow create value safely? | Controlled pilot | Only inside exercised envelope |

## Evidence obligations
- Prototype code and data are labeled disposable or production-intent; promotion requires explicit hardening review.
- The artifact contains only enough capability to answer the stated question.
- Manual labor, expert assistance, curated inputs, and excluded cases are measured and disclosed.
- A pilot includes rollback, support, privacy, authorization, and incident paths.

## Review questions
1. What decision becomes possible after this artifact?
2. Which component is being simulated, and how could that inflate results?
3. What hidden operator labor makes the experience appear automated?
4. Would a cheaper or safer artifact answer the same question?

## Failure patterns
- Demo as evidence: visual fluency mistaken for workflow value or operability.
- Prototype-to-production drift: exploratory shortcuts quietly become architecture.
- Multi-question experiment: too many unknowns make failure uninterpretable.

## Research basis

Uses agile alpha/beta guidance, human-AI prototyping, and field-learning practice [R91] [R93] [R94].
