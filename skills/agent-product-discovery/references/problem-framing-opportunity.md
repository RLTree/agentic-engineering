# Problem framing and opportunity

A good problem frame names the actor, workflow, desired outcome, current constraints, consequence, and evidence—without presupposing an agent, chat interface, model, or autonomy level.

## Vocabulary
- **job/outcome:** Progress or result the stakeholder seeks in context.
- **problem statement:** Evidence-bounded description of current friction or risk.
- **opportunity hypothesis:** Testable claim that an intervention can improve an outcome for a segment under stated conditions.
- **constraint:** Non-negotiable technical, policy, legal, economic, accessibility, or workflow condition.
- **anti-goal:** Outcome or behavior the product explicitly must not optimize or enable.

## Decision procedure
1. Describe actor/role, triggering context, current workflow, desired outcome, observed friction/consequence, and evidence.
2. Map adjacent stakeholders, incentives, handoffs, exceptions, controls, and current alternatives.
3. Separate root problem from proposed mechanism; rewrite “build an agent that…” into an outcome question.
4. Estimate value, frequency, severity, urgency, willingness/ability to change, and strategic fit with ranges and evidence.
5. Write opportunity hypothesis, anti-goals, operating boundaries, and stop/pivot criteria.

## Decision table

| Frame quality | Example form | Decision value |
|---|---|---|
| Weak solution frame | “Users need an AI copilot” | Low; assumes mechanism |
| Workflow frame | “Reviewers spend X effort reconciling Y under Z constraints” | High; testable baseline |
| Outcome frame | “Reduce verified time-to-decision without raising error or review burden” | High; supports alternatives |
| Unbounded aspiration | “Make work 10× better” | Low; gameable and unverifiable |

## Evidence obligations
- Baseline and desired outcome are observable.
- Problem evidence includes consequence and affected stakeholder, not only preference.
- Agentic architecture is one candidate intervention, not the definition of the problem.
- Anti-goals and risk boundaries prevent metric optimization from distorting product intent.

## Review questions
1. Would this problem remain if no generative model existed?
2. What current workaround demonstrates real value or pain?
3. Who benefits, who pays, and who bears risk?
4. What simpler intervention competes with an agentic one?

## Failure patterns
- Technology-first framing: model capability substituted for user need.
- Unmeasurable aspiration: no baseline, population, consequence, or boundary.
- Stakeholder flattening: requester preference treated as the whole system outcome.

## Research basis

Grounded in discovery and human-centered AI design guidance [R90] [R93] [R94].
