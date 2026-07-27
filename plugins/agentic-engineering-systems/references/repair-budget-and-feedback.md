# Repair Budgets and Structured Feedback

Every adaptive repair loop needs an explicit budget and a semantic circuit breaker.

Track each attempt by:

- hypothesis and mechanism class;
- changed variable;
- validator and candidate identity;
- structured feedback containing failure location, observed value, and admissible alternatives;
- evidence gained;
- repeated-mechanism count;
- cost, time, tool calls, and side effects.

Most gains in studied repair loops occurred within the first three to four iterations. Do not treat that number as universal; calibrate it on representative tasks. Stop earlier when attempts repeat the same mechanism without new evidence, severe risk appears, effects are ambiguous, or the oracle is untrustworthy.

Root decisions after a circuit break:

```text
change_hypothesis | change_feedback | change_tool_or_oracle | reduce_scope
redesign_architecture | request_human_decision | revert | stop
```

Evidence basis: R136, R137.
