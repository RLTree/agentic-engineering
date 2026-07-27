---
name: graph-workflow-engineering
description: "Use when branches, cycles, joins, interrupts, checkpoints, replay, or typed shared state must be explicit."
---

# Graph and Workflow Engineering

## Core principle

Represent consequential control topology as typed state transitions. Make each node independently understandable, each edge justified by evidence, and each replay safe for the effects that may already have occurred.

## Workflow

### 1. Establish graph necessity and boundary

Name the branches, cycles, joins, interrupts or recovery paths that need explicit structure. Keep purely local deterministic logic inside nodes rather than exploding every function into a graph.

### 2. Define authoritative state

Specify identifiers, immutable inputs, mutable fields, evidence, approvals, effect receipts, versions and terminal status. Separate durable workflow state from large artifacts referenced by URI or content hash.

### 3. Write node contracts

For every node record purpose, owner, preconditions, input projection, output delta, effects, idempotency, timeout, retry class, emitted evidence and errors. Use [the state/node/edge contract](references/state-node-edge-contract.md).

### 4. Write edge contracts

Make routing predicates deterministic where possible. Define default/error edges, cycles, max visits, join semantics and terminal edges. Do not use model-generated labels as unvalidated edge selectors.

### 5. Define reducers and fan-in

Specify commutativity, associativity, ordering, conflict policy, missing worker behavior and provenance. Read [reducers, checkpoints and interrupts](references/reducers-checkpoints-interrupts.md).

### 6. Place checkpoints and interrupts

Checkpoint before consequential effects and at resumable human boundaries. Ensure work before an interrupt is idempotent because resume may replay the node. Record approval payload/version and stale-decision policy.

### 7. Version and migrate

Plan for state-schema, node and prompt/model changes. Define whether in-flight runs continue on the old graph, migrate or restart.

### 8. Test the graph as a graph

Cover every edge, cycle bound, join order, duplicate delivery, crash point, stale approval, partial fan-out, replay and terminal state. Use [the graph verification matrix](references/graph-verification-matrix.md).

## Output contract

Return a **Graph Contract** containing:

- graph purpose and boundary;
- typed state schema;
- node contract table;
- edge/route table;
- reducer and ownership rules;
- checkpoint, interrupt and resume contract;
- effect idempotency and recovery policy;
- version/migration strategy;
- graph-level verification matrix.

## Common failures

- **One giant node:** branching exists only in instructions. Externalize consequential transitions.
- **State soup:** one untyped map lets every node mutate everything. Use projections and owned fields.
- **Last-writer-wins without authority:** parallel results are “combined” without conflict semantics. Define laws and provenance.
- **Interrupt before unguarded side effect:** pre-interrupt effects can repeat. Make them idempotent or move the interrupt boundary.
- **Edge ambiguity:** multiple routes match or none do. Define precedence and default/error behavior.
- **Untested topology:** node unit tests pass while cycles, joins and replay fail. Test paths and invariants.

## References

- [State, node and edge contract](references/state-node-edge-contract.md)
- [Reducers, checkpoints and interrupts](references/reducers-checkpoints-interrupts.md)
- [Graph verification matrix](references/graph-verification-matrix.md)
- [Graph versioning and migration](references/graph-versioning.md)

## Shared references

- [Seven-layer map](../../references/seven-layer-map.md)
- [Architecture escalation](../../references/architecture-escalation.md)
- [GPT-5.6 Sol operating profile](../../references/gpt-5.6-sol-operating-profile.md)
- [Evidence and confidence](../../references/evidence-and-confidence.md)
