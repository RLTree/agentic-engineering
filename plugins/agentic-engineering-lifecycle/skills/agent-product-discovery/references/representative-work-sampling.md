# Representative work sampling

Representative sampling defines the workload population and deliberately captures variation that affects product value, safety, reliability, and human effort. Volume from easy or enthusiastic cases is not representativeness.

## Vocabulary
- **workload population:** The intended distribution of users, tasks, data, environments, tools, stakes, and time conditions.
- **sampling frame:** The practical list or mechanism from which cases are selected.
- **coverage cell:** A meaningful combination of dimensions requiring evidence.
- **severity oversample:** Deliberate enrichment of rare high-impact cases for failure discovery, not prevalence estimation.
- **selection bias:** Systematic difference between observed participants/tasks and the intended population.

## Decision procedure
1. Define population and decision: what claims require representativeness and at what granularity.
2. Choose dimensions such as task type, frequency, novelty, risk, user expertise, language, accessibility, data sensitivity, tool/effect type, environment, urgency, and failure history.
3. Build coverage cells and identify rare severe cases, non-users, abandoners, and missing data.
4. Select purposive, stratified, random, time-window, journey, or incident-based sampling appropriate to the claim.
5. Record inclusion, refusal, missingness, weights/limitations, and changes caused by observation.
6. Review saturation for qualitative mechanisms and statistical uncertainty for quantitative estimates separately.

## Decision table

| Claim | Sampling need | Analysis caution |
|---|---|---|
| Discover mechanisms | Purposive maximum variation | Do not estimate prevalence |
| Estimate ordinary rate | Probability/stratified sample | Account for missingness and weights |
| Find rare severe failure | Severity oversample/red team | Do not report raw sample rate as population rate |
| Evaluate rollout impact | Valid assignment plus exposure sample | Check contamination and attrition |

## Evidence obligations
- Easy cases cannot dominate simply because they generate more traces.
- Non-completion, abandonment, denial, and escalation cases remain in the evidence set.
- Representativeness is rechecked after product use changes the task/user distribution.
- Privacy and consent constraints are included in the sampling design, not handled after collection.

## Review questions
1. What population does this sample actually represent?
2. Which dimension could reverse the conclusion if under-sampled?
3. Are we confusing severity-discovery sampling with prevalence estimation?
4. Who never enters the telemetry and why?

## Failure patterns
- Convenience pilot generalized to the market.
- Survivorship evidence: only completed tasks or active users retained.
- Average-only analysis: harmful or high-value segments disappear.

## Research basis

Supported by field-evidence methods, monitoring questions, human-AI workflow
research, and experiment validity. NIST AI 800-4 is descriptive rather than a
prescribed sampling method (`F-NIST-AI800-4`). Historical lineage: [R75] [R77]
[R79] [R93] [R94].
