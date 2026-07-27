# Skill Behavior Evaluation

Evaluate a skill as a routed behavioral intervention, not a document.

Minimum case set:

- explicit invocation;
- implicit trigger;
- contextual/noisy trigger;
- negative control;
- overlap with adjacent skills;
- missing access or unavailable tool;
- ordinary small work;
- consequential work;
- already-fixed/no-change work;
- adversarial proxy or specification-gaming attempt.

Compare with a no-skill or prior-version baseline. Score activation, following, composition, recovery, verified outcome, authority compliance, safety, style, command/tool thrashing, tokens, latency, cost, and repository cleanliness. Use JSONL traces and deterministic graders first; add structured model graders where rules cannot capture the product requirement. Add held-out, mutation, and spec-evolution cases for consequential skills.

Evidence basis: R127, R140.
