# Failure Attribution and Mechanism Hypotheses

Attribute the earliest controllable cause, not merely the last visible error.

Use a layer-aware trace:

```text
request/specification → context/retrieval → tool contract → harness policy
→ loop/graph decision → runtime/effect → repository/software → product/lifecycle outcome
```

For each candidate cause record:

- evidence-bearing trajectory step;
- responsible layer and owner;
- causal prediction: what else should be true if the hypothesis is correct;
- disconfirming probe;
- smallest repair operator;
- possible displaced failure.

Normalize traces before clustering. Repeated final symptoms may arise from different causes; different symptoms may share one harness flaw. Validate a repair on held-out trajectories and check that it does not weaken another layer.

Evidence basis: R138, R146.
