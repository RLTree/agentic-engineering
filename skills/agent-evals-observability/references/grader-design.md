# Grader design

Graders are measurement instruments. Their reliability, independence and blind spots must be tested rather than assumed.

## Grader types

- deterministic tests/schema/invariants;
- authoritative external-state comparison;
- reference or diff-based checks;
- static analysis/security policy;
- model rubric grader;
- pairwise preference;
- calibrated human review.

Prefer deterministic evidence for deterministic properties. Use model graders for semantic quality where a rubric and examples can bound judgment.

## Rubric structure

Define criterion, observable anchors for fail/partial/pass/excellent, severity, required evidence, forbidden behavior and tie-breaking. Split dimensions that can fail independently: correctness, completeness, coherence, maintainability, efficiency, recovery, safety.

## Grader validation

- agreement with expert labels on a representative set;
- false-positive/false-negative analysis by severity;
- robustness to verbosity, formatting, self-claims and prompt injection in artifacts;
- consistency across paraphrases and order changes;
- leakage check: grader must not see hidden answer unless intended;
- version and drift monitoring.

## Evidence-first grading

Require the candidate to supply artifact and evidence references, but verify them independently. Treat self-reported test success as a claim until logs/artifacts support it. Grade exact packaged/deployed output when delivery quality matters.

## Pairwise versus absolute

Pairwise comparison is useful for subtle quality differences but can hide both outputs being unacceptable. Combine it with absolute gates for invariants and safety.

## Uncertainty

Allow `insufficient_evidence` rather than forcing pass/fail. Record grader confidence separately from task score. Escalate high-impact disagreements to human review and add them to calibration fixtures.
