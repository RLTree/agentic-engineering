# Field-Learning and Full-Lifecycle Vocabulary

Use this lexicon when the intent is clear but the professional term is missing. Each entry names a decision or artifact Codex can operationalize. Definitions are scoped to agentic software products.

## Authentic use, exposure, and autonomy

| Term | Operational meaning | Useful prompt phrase |
|---|---|---|
| authentic use | Use with representative people, tasks, data, environments, dependencies, timing, and consequences. | “Design authentic use rather than a convenience demo.” |
| ecological validity | Degree to which evidence reflects real operating conditions. | “State which dimensions of ecological validity remain weak.” |
| representative workload | Deliberately sampled task distribution, including routine, edge, interrupted, and high-consequence cases. | “Stratify a representative workload by task and risk.” |
| convenience sample | Easily available users or tasks that may not represent intended operation. | “Do not generalize from the convenience sample.” |
| operating envelope | Versioned boundary of eligible users, tasks, data, models, tools, environments, effects, budgets, and exclusions. | “Define the operating envelope and material-change triggers.” |
| consequence tier | Classification of potential impact from a task, decision, or effect. | “Assign consequence tiers and controls.” |
| exposure unit | Entity assigned to a behavior, such as user, account, repository, task, or organization. | “Choose the correct exposure unit and contamination boundary.” |
| eligibility | Rule determining whether an exposure unit may enter a rollout or experiment. | “Record eligibility separately from assignment.” |
| assignment | Decision that an eligible unit receives a variant or operating mode. | “Instrument assignment integrity.” |
| exposure | Evidence that the assigned unit actually encountered the behavior. | “Join assignment to actual exposure.” |
| treatment integrity | Whether the intended version and behavior were actually delivered. | “Block conclusions when treatment integrity is uncertain.” |
| observe-only | Live instrumentation without generated output influencing work. | “Begin in observe-only mode.” |
| shadow mode | Live inputs generate counterfactual output with no operational influence. | “Use shadow mode to test integration and latency.” |
| silent trial | Prospective shadow evaluation under predeclared endpoints and reporting. | “Design a silent trial before recommendation mode.” |
| recommendation-only | Agent advice is visible; humans retain decisions and effects. | “Measure reliance and correction in recommendation-only use.” |
| approval-gated action | Exact proposed effect requires authorization before execution. | “Require approval of target, parameters, consequence, and evidence.” |
| bounded autonomy | Preauthorized action inside a narrow envelope, budget, and stop policy. | “Permit bounded autonomy only for reversible task classes.” |
| progressive autonomy | Evidence-based movement through increasing authority stages. | “Define promotion, narrowing, and stop evidence for autonomy.” |
| effect budget | Deterministic cap on writes, deployments, messages, spend, or affected records. | “Set per-run and per-period effect budgets.” |
| blast radius | Maximum plausible scope of impact from failure. | “Limit blast radius at every rollout stage.” |
| kill switch | Tested mechanism to stop new work or effects rapidly. | “Name the kill-switch owner and verification.” |
| bake time | Predeclared observation interval before promotion. | “Set bake time from outcome latency and rare-failure risk.” |
| canary | Limited production exposure compared with a baseline to reduce release risk. | “Use a representative canary with explicit rollback.” |
| rollout ring | Ordered cohort or environment for progressive exposure. | “Define rings, entry criteria, and promotion authority.” |
| holdout | Persistent comparison population that remains on baseline behavior. | “Use a holdout for durable effects and check contamination.” |
| friction budget | Deliberate allocation of human review or approval effort. | “Place friction where it prevents consequential error.” |
| calibrated reliance | Accepting, checking, correcting, or rejecting output in proportion to actual reliability and risk. | “Measure calibrated reliance, not acceptance alone.” |
| intervention | Human action that changes, stops, corrects, or recovers agent work. | “Treat interventions as first-class evidence.” |
| override | Human or policy decision replacing a proposed action. | “Record override reason and outcome.” |
| near miss | Unacceptable outcome prevented by chance, control, or intervention. | “Harvest near misses into controls and regressions.” |
| ambiguous effect | External action whose outcome is unknown after dispatch. | “Reconcile ambiguous effects before redispatch.” |

## Field evidence and learning

| Term | Operational meaning | Useful prompt phrase |
|---|---|---|
| learning charter | Decision, uncertainty, exposure, evidence, and owner that justify field work. | “Write the learning charter before instrumentation.” |
| field observation | Structured record of context, versions, task, trajectory, effect, outcome, intervention, and evidence quality. | “Emit a versioned field-observation record.” |
| evidence strength | Confidence warranted by representativeness, validity, identification, consistency, and relevance. | “Grade evidence strength and limits.” |
| evidence coverage | Portion and distribution of the operating envelope represented by trustworthy evidence. | “Show coverage gaps by envelope stratum.” |
| outcome evidence | Evidence that the intended real-world result occurred. | “Join agent output to downstream outcome evidence.” |
| trajectory evidence | Evidence about state, tools, actions, errors, retries, approvals, and recovery. | “Preserve trajectory evidence for diagnosis.” |
| effect evidence | Evidence that an action was prepared, authorized, dispatched, confirmed, reconciled, or compensated. | “Require effect-state evidence.” |
| human-work evidence | Framing, review, approval, correction, recovery, support, and maintenance effort. | “Account for displaced and newly created human work.” |
| observational evidence | Naturally occurring evidence useful for diagnosis but vulnerable to confounding. | “Use observation to form hypotheses, not automatic causal claims.” |
| causal evidence | Evidence supporting attribution of outcome differences to an intervention. | “Choose a defensible causal design.” |
| triangulation | Combining methods whose strengths and weaknesses complement one another. | “Triangulate metrics, traces, interviews, and incidents.” |
| qualitative evidence | Structured evidence about workflow, language, mental models, reliance, and mechanisms. | “Pair quantitative outcomes with qualitative mechanism evidence.” |
| contextual inquiry | Observation and questioning during real work. | “Use contextual inquiry to expose hidden workflow constraints.” |
| critical incident | Detailed account of a particularly successful, failed, or risky episode. | “Sample critical incidents, not only average sessions.” |
| success deconstruction | Analysis of why a successful case worked and whether it generalizes. | “Deconstruct representative successes for enabling conditions.” |
| failure signature | Stable classification of a recurring mechanism or observable pattern. | “Cluster traces by failure signature.” |
| mechanism hypothesis | Testable explanation of how a product condition caused an observation. | “State competing mechanism hypotheses.” |
| regression harvesting | Turning failures, corrections, near misses, and incidents into durable tests or evals. | “Harvest each material failure into a regression.” |
| evidence-to-change loop | Observation → mechanism → intervention → regression → rollout → result → decision. | “Close the evidence-to-change loop.” |
| field-learning ledger | Durable history linking observations, decisions, changes, verification, and outcomes. | “Update the field-learning ledger after every review.” |
| learning velocity | Rate at which important uncertainty is resolved with representative evidence. | “Optimize learning velocity, not experiment count.” |
| evidence-to-change latency | Time from meaningful observation to verified product response. | “Track evidence-to-change latency with quality guardrails.” |
| instrumentation debt | Missing, unsafe, unjoinable, ambiguous, or untrusted evidence infrastructure. | “Treat instrumentation debt as a release risk.” |
| denominator problem | Inability to interpret incidents or successes because total eligible/exposed cases are unknown. | “Preserve denominators for every rate.” |
| survivorship bias | Learning only from cases that remained observable or completed. | “Capture abandonment and missing users.” |
| selection bias | Systematic difference between observed and target populations. | “State selection mechanisms and generalization limits.” |
| confounding | Alternative cause associated with both exposure and outcome. | “List plausible confounders before claiming impact.” |
| novelty effect | Temporary response to newness or attention. | “Separate novelty from durable value.” |
| learning effect | Outcome changes as users learn the product or workflow. | “Model first-use and mature-use separately.” |
| carryover | Treatment influence persists after assignment changes. | “Specify carryover and washout policy.” |

## Metrics and experimentation

| Term | Operational meaning | Useful prompt phrase |
|---|---|---|
| metric contract | Definition of purpose, construct, unit, population, event, attribution, aggregation, thresholds, quality checks, and limits. | “Write a metric contract before reading results.” |
| primary outcome | Predeclared measure most directly tied to the decision. | “Name one primary outcome and practical threshold.” |
| diagnostic metric | Measure of the hypothesized mechanism. | “Add diagnostics that distinguish failure mechanisms.” |
| guardrail metric | Measure that blocks optimization when unacceptable degradation occurs. | “Use consequence-specific guardrails.” |
| countermetric | Measure exposing the predictable downside of optimizing the primary metric. | “Pair speed with quality and rework countermetrics.” |
| data-quality metric | Evidence that assignment, exposure, joins, and measurement are trustworthy. | “Make data-quality failures blocking.” |
| sample ratio mismatch | Observed assignment ratio differs implausibly from configured ratio. | “Diagnose SRM before product interpretation.” |
| minimum detectable effect | Smallest effect a design is likely to detect at chosen error/power levels. | “Align sample size to the minimum useful effect.” |
| minimum practically important difference | Smallest effect worth acting on regardless of statistical significance. | “Predeclare practical significance.” |
| sequential analysis | Valid inference under planned repeated looks or adaptive stopping. | “Use a sequential method rather than opportunistic peeking.” |
| peeking | Repeatedly checking ordinary tests and stopping on a favorable result. | “Prevent peeking-driven false positives.” |
| multiple testing | Inflated false positives from many metrics, variants, or segments. | “Predeclare primary analyses and correction policy.” |
| interference | One unit’s treatment changes another unit’s outcome. | “Choose an assignment unit that contains spillover.” |
| contamination | Units receive or are influenced by the other variant. | “Measure cross-variant contamination.” |
| practical significance | Business/user importance of an effect, distinct from statistical significance. | “Report both statistical and practical significance.” |
| heterogeneous effect | Treatment effect differs across populations or task strata. | “Inspect predeclared high-risk and high-value segments.” |
| instrumentation effect | Measurement changes behavior or system performance. | “Test whether instrumentation alters latency or use.” |
| experiment fidelity | The intended treatment, assignment, exposure, and analysis were implemented as designed. | “Verify experiment fidelity before interpretation.” |
| advance/hold/narrow/revert/stop | Explicit decision set richer than ship/no-ship. | “Precommit all five decision outcomes.” |

## Product discovery and validation

| Term | Operational meaning | Useful prompt phrase |
|---|---|---|
| problem framing | Evidence-backed description of actors, outcomes, current conditions, consequences, and constraints. | “Frame the problem without embedding the solution.” |
| opportunity statement | Product-improvable condition stated without locking architecture. | “Generate competing opportunity statements.” |
| job/work outcome | Result a person or organization is trying to achieve in context. | “Study the work outcome, not requested features alone.” |
| current-state journey | Existing sequence of work, systems, handoffs, decisions, and failures. | “Map the current-state journey and recovery.” |
| system of record | Authoritative source for a business or technical fact. | “Name systems of record and update authority.” |
| workaround | Informal behavior compensating for product/process limitations. | “Treat workarounds as discovery evidence.” |
| assumption map | Explicit user, value, data, capability, workflow, risk, and economic assumptions. | “Rank assumptions by consequence and uncertainty.” |
| riskiest assumption test | Cheapest credible test of the assumption most likely to invalidate the direction. | “Test the riskiest assumption before deeper build.” |
| concierge test | Humans manually deliver the proposed value to test demand and workflow. | “Use concierge delivery before automation.” |
| Wizard-of-Oz test | Interface appears automated while humans perform hidden operations. | “Use Wizard-of-Oz only with clear ethical controls.” |
| technical spike | Time-bounded code built to answer a feasibility question, not become production by accident. | “Define the spike question and discard/productionize criteria.” |
| walking skeleton | Minimal deployable end-to-end path through real boundaries. | “Build a walking skeleton with telemetry and rollback.” |
| thin vertical slice | Small end-to-end product capability designed to resolve uncertainty. | “Plan slices by evidence unlocked.” |
| prototype theater | Impressive demonstration that avoids the highest-risk assumptions. | “Review for prototype theater.” |
| go/pivot/stop criteria | Predeclared evidence thresholds for continuing, changing direction, or ending work. | “Commit go, pivot, and stop rules before the demo.” |

## Requirements, systems, and architecture

| Term | Operational meaning | Useful prompt phrase |
|---|---|---|
| operational concept | How actors and the future system work across normal, degraded, emergency, and recovery modes. | “Produce an operational concept before feature requirements.” |
| mission thread | End-to-end scenario crossing actors, systems, decisions, effects, verification, and recovery. | “Write representative mission threads.” |
| stakeholder need | Desired outcome or constraint in stakeholder language. | “Trace needs to requirements and evidence.” |
| functional requirement | Observable behavior the system must provide. | “Make functional requirements testable.” |
| quality attribute | Cross-cutting property such as reliability, security, usability, or maintainability. | “Turn quality attributes into scenarios.” |
| quality-attribute scenario | Source, stimulus, environment, artifact, response, and response measure. | “Use measurable quality-attribute scenarios.” |
| verification | Evidence that implementation satisfies specified requirements. | “Separate verification from validation.” |
| validation | Evidence that the right product works for intended use. | “Validate against representative mission outcomes.” |
| bidirectional traceability | Links from needs to implementation/evidence and back. | “Require traceability that supports impact analysis.” |
| baseline | Approved version of requirements/configuration used for controlled change. | “Baseline model, prompts, tools, permissions, and requirements.” |
| material change | Change large enough to invalidate prior evidence or authorization. | “Define material-change and revalidation triggers.” |
| sensitivity point | Architectural decision where small change strongly affects a quality attribute. | “Identify sensitivity points.” |
| tradeoff point | Decision affecting multiple quality attributes in tension. | “Document architecture tradeoff points.” |
| architecture risk | Unproven decision that may prevent quality goals. | “Retire architecture risks with targeted slices.” |
| architecture fitness function | Automated check that protects an architectural property. | “Encode stable constraints as fitness functions.” |
| ADR | Durable architecture decision record with context, choice, consequences, and revisit trigger. | “Write an ADR with evidence and consequences.” |
| decision-evidence graph | Links decisions, claims, artifacts, evidence, owners, and feedback. | “Build the lifecycle decision-evidence graph.” |

## Construction, release, and reliability

| Term | Operational meaning | Useful prompt phrase |
|---|---|---|
| small batch | Coherent change that can be reviewed, verified, attributed, and reverted independently. | “Split work into small evidence-complete batches.” |
| verification ladder | Ordered layers of static, unit, integration, fault, eval, artifact, and field evidence. | “State which ladder rungs passed or remain unexecuted.” |
| exact-artifact verification | Testing the package, image, binary, deployment, or migration users receive. | “Verify the exact delivered artifact.” |
| fresh-context review | Review by a human/agent not immersed in implementation history. | “Run a fresh-context review against the contract.” |
| defect escape | Defect discovered after the stage where it could have been caught. | “Classify the escape and detection gap.” |
| secure by default | Safe configuration without requiring customers to discover protective settings. | “Make least privilege and safe failure the defaults.” |
| threat model | Assets, actors, trust boundaries, abuse cases, controls, detection, and response. | “Threat-model model, tools, memory, telemetry, and effects.” |
| SBOM | Machine-readable inventory of software components and dependencies. | “Link the SBOM to artifact provenance and vulnerability policy.” |
| provenance | Evidence connecting an artifact to source, build process, and environment. | “Require verifiable build provenance.” |
| progressive delivery | Controlled release through staged exposure and evidence-based promotion. | “Separate deployment mechanism from promotion decision.” |
| rollback | Return to prior behavior or artifact after a release problem. | “Exercise rollback before production expansion.” |
| roll-forward | Correcting by deploying a new version when rollback is unsafe or impossible. | “Define rollback versus roll-forward policy.” |
| reconciliation | Determine actual state after ambiguous or partial effects. | “Reconcile before retrying external effects.” |
| production readiness review | Evidence review for ownership, architecture, capacity, failure, observability, security, rollout, and operation. | “Run PRR before broad exposure.” |
| SLI | Quantitative measure of service behavior. | “Define semantic and operational SLIs separately.” |
| SLO | Target range for an SLI over a window. | “Attach ownership and consequence to every SLO.” |
| error budget | Allowed unreliability used to govern release and reliability investment. | “Define what happens when the error budget is exhausted.” |
| graceful degradation | Reduced capability that preserves critical outcomes under failure. | “Specify degraded modes and user communication.” |
| backpressure | Mechanism limiting intake when downstream capacity is exhausted. | “Define bounded queues and overload behavior.” |
| toil | Repetitive manual operational work lacking durable value. | “Measure review, reconciliation, and support toil.” |
| runbook | Tested operational procedure for detection, diagnosis, mitigation, and recovery. | “Link alerts to owned runbooks.” |
| blameless postmortem | System-focused incident analysis with owned corrective actions. | “Create regressions and control changes from the postmortem.” |

## Maintenance and retirement

| Term | Operational meaning | Useful prompt phrase |
|---|---|---|
| sustainment | Ongoing work preserving value, safety, reliability, and compatibility. | “Define sustainment evidence and ownership.” |
| drift | Change in task, data, model, tool, user, or environment distribution. | “Monitor envelope and behavior drift.” |
| revalidation | Repeating appropriate evidence after material change. | “Map change classes to revalidation.” |
| deprecation | Announced transition away from a capability with migration support. | “Define deprecation timeline and user continuity.” |
| migration | Movement of users, data, workflows, or integrations to a replacement. | “Instrument migration completeness and failures.” |
| decommissioning | Controlled disabling and removal of a service or component. | “Disable, observe, reconcile, then remove.” |
| retirement | End-of-life process including migration, revocation, data handling, evidence retention, and closure. | “Engineer retirement as a lifecycle phase.” |
| evidence continuity | Preservation of records needed for audit, incident, legal, or learning after change/retirement. | “Define evidence retention after closure.” |
| orphaned dependency | Consumer or job still relying on a supposedly retired system. | “Test for orphaned dependencies after disable.” |
| post-close monitoring | Observation period after shutdown to detect hidden use or failure. | “Set post-close monitoring and reopen criteria.” |

## Agent-mediated and Rust observability

| Term | Operational meaning | Useful prompt phrase |
|---|---|---|
| epistemic label | Marker distinguishing fact, inference, assumption, recommendation, and unknown. | “Label epistemic status in every lifecycle artifact.” |
| decision right | Authority to choose, approve, reject, or accept risk. | “Assign human and agent decision rights.” |
| assurance case | Structured claim supported by evidence under assumptions with possible defeaters. | “Build a revisable assurance case for the envelope.” |
| trace ID | Diagnostic identifier for distributed telemetry, not authorization or durable effect identity. | “Keep trace IDs separate from business/effect IDs.” |
| domain identity | Stable application-level ID for run, task, action, effect, observation, or exposure. | “Use typed Rust newtypes for domain identities.” |
| span | Structured contextual operation with duration and parentage. | “Create spans around owned run/tool/effect work.” |
| event | Structured fact occurring inside or between operations. | “Emit typed decision and effect-state events.” |
| context propagation | Transfer of trace and selected product context across tasks and services. | “Test propagation through Tokio tasks and channels.” |
| baggage | Propagated key-value context; potentially sensitive and costly. | “Allowlist baggage and never use it as authorization.” |
| semantic convention | Shared naming/schema convention for telemetry. | “Version experimental GenAI semantic conventions.” |
| high cardinality | Very many distinct label values, which harms cost and reliability. | “Keep IDs and raw text out of metric labels.” |
| tail sampling | Sampling after observing trace properties, useful for retaining slow/error traces. | “Retain severe and rare traces independently of routine sampling.” |
| priority retention | Always retain specified high-value events such as security failures or ambiguous effects. | “Encode priority-retention rules.” |
| pseudonymization | Replacing identity with a stable surrogate; still potentially personal data. | “Treat hashes as pseudonyms, not anonymity.” |
| redaction | Removal or transformation of sensitive fields. | “Redact at source and verify policy.” |
| exporter backpressure | Telemetry pipeline inability to accept data without blocking or loss. | “Define nonblocking failure and loss accounting.” |
| graceful telemetry shutdown | Bounded flush and shutdown of telemetry pipeline. | “Test exporter flush on Tokio shutdown.” |
| feature evaluation context | Attributes used to evaluate a rollout/feature variant. | “Minimize and version evaluation context.” |
| rollout decision function | Pure rule mapping trustworthy evidence to advance, hold, narrow, revert, or stop. | “Keep rollout decisions deterministic and testable.” |
| observable intervention | Intervention recorded with context, reason, burden, and outcome. | “Make human correction visible in Rust field evidence.” |

## Source anchors

This vocabulary operationalizes the field-learning, post-deployment monitoring, experimentation, lifecycle, requirements, architecture, secure-development, SRE, and observability findings summarized in `RESEARCH.md`, especially [R71]–[R125].
