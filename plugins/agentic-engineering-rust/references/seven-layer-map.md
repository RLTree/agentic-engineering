# Seven-layer map for agentic engineering

Use this map to locate the decision that is currently implicit. A prompt can mention every layer, but each decision should have one durable owner.

## 1. Intent and specification

Defines the outcome, scope, constraints, invariants, anti-goals, acceptance criteria, evidence, autonomy and exact deliverables.

**Ask:** What must be true when the work is complete? Which plausible interpretation is explicitly unwanted?

**Durable owners:** issue, task contract, specification, ADR, acceptance-to-evidence matrix.

## 2. Context engineering

Controls which instructions, repository facts, retrieved files, tool outputs, summaries, memory and provenance enter the model's working context at each decision.

**Ask:** What is the minimum sufficient, highest-signal context now? What is stale, untrusted or merely historical?

**Durable owners:** layered `AGENTS.md`, repository map, plan/progress file, retrieval policy, skill references, compaction checkpoint.

## 3. Harness engineering

Builds the control plane around the model: model invocation, tool registry, policy, sandbox, run state, approvals, tracing, recovery and handoff.

**Ask:** Which guarantees must surround model behavior rather than depend on prompt compliance?

**Durable owners:** runner, tool gateway, policy engine, state store, sandbox configuration, approval service, trace pipeline.

## 4. Loop engineering

Defines how the system repeatedly observes, orients, plans, acts, verifies, updates and stops or escalates under budgets.

**Ask:** Why must the next action adapt to evidence? What proves progress or convergence?

**Durable owners:** loop controller, budget ledger, retry/repair policy, verification oracle, stop/escalation rules.

## 5. Graph engineering

Makes state, nodes, edges, branches, cycles, fan-out/fan-in, reducers, checkpoints and interrupts explicit.

**Ask:** Which transitions need typed contracts, deterministic routing or resumability?

**Durable owners:** graph definition, state schema, node contracts, edge predicates, reducer laws, checkpoint store.

## 6. Agentic systems engineering

Coordinates agents, humans, tools, services, data, identity, permissions, protocols, operations and trust boundaries.

**Ask:** Who owns each decision and side effect? How can the system be inspected, constrained, stopped and recovered?

**Durable owners:** delegation protocol, IAM policy, service contracts, MCP/A2A interfaces, operational runbooks, incident controls.

## 7. Agent-first software engineering

Adapts repositories and delivery workflows for coding agents as persistent contributors.

**Ask:** How will an unfamiliar agent discover the architecture, make the smallest coherent change, prove it and leave a reviewable artifact?

**Durable owners:** repository guidance, specs, plans, worktrees, tests, evals, CI, review rules, delivery evidence, correction-to-infrastructure loop.

## Diagnostic rule

When an output disappoints, do not immediately lengthen the prompt. Ask:

1. Which consequential decision was implicit?
2. Which layer should own it?
3. What durable artifact or mechanism should encode it?
4. What observable evidence will show the correction worked?

A repeated correction is evidence that the decision belongs in infrastructure, not another conversational reminder.
