# Agentic Engineering for Codex and Rust in 2026

## Research and operational analysis for the Agentic Engineering Codex plugin

**Research lock:** July 22, 2026  
**Artifact:** Agentic Engineering Codex Plugin v2.0  
**Scope:** agentic coding, context and harness engineering, control loops, state graphs, durable execution, multi-agent coordination, agent-first repositories, evaluation, security, observability, protocols, GPT-5.6 Sol operation, Rust agent applications, controlled field learning from authentic use, full-lifecycle product and systems engineering, trustworthy experimentation, production reliability, maintenance, and retirement.

**Evidence base:** 125 mapped sources: 88 class-A official standards, specifications, or project documentation; 28 class-B first-party engineering or research sources; 8 class-C independent research sources; and the class-D user-provided Design Judgment method.

**Confidence note:** confidence values in this package are calibrated engineering judgments about likely positive transfer, not measured probabilities for every repository or task.

---

## Executive synthesis

The most important vocabulary shift is this:

> A prompt is only one input to an agentic system. The quality of the result is determined by the whole control architecture: specification, context assembly, harness, loop policy, state graph, execution environment, tools, verification, recovery, and human decision boundaries.

In 2026, strong agentic-coding practice is increasingly repository- and harness-centered. OpenAI describes the harness as the control plane that owns model calls, tool routing, handoffs, approvals, tracing, recovery, and run state, while the sandbox is the execution plane that actually runs commands and files [R05]. OpenAI’s account of agent-first software development goes further: agents can produce code, tests, CI configuration, documentation, evals, and supporting artifacts, while humans increasingly define priorities, translate feedback into acceptance criteria, and validate outcomes [R03]. Anthropic’s context-engineering work reinforces the same point from another direction: the prompt is not the whole working state; the model acts from a finite, evolving context that must be assembled for signal rather than accumulated indiscriminately [R14].

That leads to six durable principles:

1. **Specify decisions, not adjectives.** “Professional,” “agentic,” “robust,” and “polished” are intentions, not contracts. Replace them with explicit outcomes, invariants, state, interaction, evidence, and handoff requirements.
2. **Use the smallest architecture that fits.** A direct call or deterministic workflow is preferable when the path is known. Add a loop only when the next action must adapt; add a graph when branches, cycles, interrupts, or recovery need to be explicit; add durable execution when runs must survive interruption; add multiple agents only when parallelism or specialization earns the coordination cost [R13].
3. **Separate model judgment from deterministic control.** Models are useful for semantic interpretation, planning under ambiguity, and generation. Code should own schemas, permissions, budgets, routing rules, invariant checks, retries, idempotency, and irreversible effects whenever those can be deterministic.
4. **Treat verification as part of execution.** A production loop is not “keep trying.” It observes, orients, plans, acts, verifies against an oracle, updates durable evidence, and exits or recovers under explicit budgets.
5. **Turn repeated correction into infrastructure.** Recurrent guidance belongs in AGENTS.md, skills, tests, evals, hooks, tool contracts, design-system rules, or approval policy—not repeatedly in chat [R06][R07][R12].
6. **Make the artifact—not the conversation—the unit of value.** The durable output should be reviewable outside the session: a branch, pull request, application, report, run trace, dataset, deployment, or decision record. OpenAI’s Symphony framing makes the issue tracker a control plane and emphasizes durable deliverables over interactive-session throughput [R04].

The result is not merely “better prompting.” It is a way to ask for software systems with enough control structure that Codex can produce coherent, professional, verifiable work with less conversational repair.

---

## 1. The seven-layer map

Most frustrating requests collapse seven different engineering questions into a single prose prompt. Separating them gives you both vocabulary and a diagnostic method.

### Layer 1 — Intent and specification

**Question:** What outcome counts as correct, complete, safe, and useful?

This layer owns the objective, scope, constraints, assumptions, invariants, acceptance criteria, evidence, anti-goals, autonomy boundary, and exact deliverable. A specification is not necessarily long. It is decision-complete.

Useful nouns:

- objective
- scope and non-scope
- deliverable contract
- invariant
- acceptance criterion
- definition of done
- assumption policy
- anti-goal
- evidence contract
- escalation threshold
- irreversible decision

A weak request says: “Make this professional.”  
A stronger request says: “Preserve the existing information architecture, create one dominant decision per view, define responsive transformations at 390, 768, and 1440 pixels, validate keyboard focus and error recovery, and return screenshots from the exact packaged artifact.”

**Failure signal:** the agent asks the same questions repeatedly, fills gaps differently on each run, or optimizes for plausible appearance rather than the intended outcome.

### Layer 2 — Context engineering

**Question:** What information should be in the model’s working context at each step?

Context engineering includes task instructions, repository guidance, retrieved files, tool outputs, summaries, memory, recent state, and provenance. Its goal is not maximal context. It is the minimum sufficient, highest-signal context for the current decision [R14].

Useful nouns:

- context assembly
- context window
- working context
- progressive disclosure
- retrieval policy
- relevance filter
- provenance
- compaction
- summary checkpoint
- context isolation
- stale context
- context poisoning

“Give the agent the whole repository” is not a context strategy. A better strategy is: expose a compact repository map; retrieve the files relevant to the current subtask; load a skill only when its trigger applies; preserve the current state and decision record; summarize or evict low-value history.

**Failure signal:** the agent forgets constraints, follows stale instructions, fixates on irrelevant files, or loses coherence as the session grows.

### Layer 3 — Harness engineering

**Question:** What surrounding machinery makes model capability operable, bounded, observable, and recoverable?

A harness is the control plane around the model: prompts and policies, context assembly, model invocation, tool routing, state management, approvals, tracing, recovery, evaluation, and handoff. OpenAI’s 2026 terminology explicitly separates this control plane from the sandbox or execution plane [R05].

Useful nouns:

- control plane
- execution plane
- harness
- runtime
- sandbox
- tool registry
- approval policy
- run state
- trace
- recovery policy
- effect journal
- worktree
- capability boundary
- least privilege

**Failure signal:** changing prompt wording gives inconsistent improvements because the real deficiency is missing tools, poor repository guidance, weak state, no test oracle, no recovery path, or excessive permissions.

### Layer 4 — Loop engineering

**Question:** How does the system decide what to do next, learn from evidence, and stop?

The loop is the recurring control policy. It defines observation, orientation, planning, action, verification, state update, and termination. A bounded loop has iteration, time, token, tool, cost, and side-effect budgets.

Useful nouns:

- sense–plan–act loop
- observe–orient–plan–act–verify–update
- action budget
- iteration budget
- stop condition
- verification oracle
- retry policy
- repair loop
- evaluator–optimizer
- escalation policy
- convergence criterion

**Failure signal:** the agent researches forever, repeats nearly identical edits, declares success without testing, or never recognizes that it needs a human decision.

### Layer 5 — Graph engineering

**Question:** How are state, branches, cycles, parallel work, interrupts, and recovery made explicit?

A graph consists of typed state, nodes, edges, reducers, entry and exit conditions, checkpoints, and interrupts. LangGraph’s own distinction is useful: a graph can mix deterministic and model-driven nodes while the runtime provides persistence and human-in-the-loop execution [R21][R22][R23][R24].

Useful nouns:

- state schema
- node contract
- edge condition
- conditional edge
- cycle
- reducer
- fan-out / fan-in
- checkpoint
- interrupt
- resume command
- replay
- compensation
- invariant
- subgraph

**Failure signal:** branching logic is hidden inside one giant prompt, retries duplicate effects, human approval cannot resume cleanly, or parallel workers overwrite one another.

### Layer 6 — Agentic systems engineering

**Question:** How do agents, humans, tools, services, memory, policies, and protocols work as one dependable socio-technical system?

This layer owns boundaries and coordination: identity, permissions, delegation, trust, shared state, protocols, observability, failure containment, and operational governance.

Useful nouns:

- agent role
- delegation contract
- orchestrator–worker
- supervisor–worker
- shared-state ownership
- non-overlapping work
- capability token
- trust boundary
- provenance label
- human approval gate
- MCP
- A2A
- cascading failure
- kill switch

**Failure signal:** agents duplicate work, conflict over shared files, pass untrusted content as instructions, or create a chain of effects that no one can reconstruct or stop.

### Layer 7 — Agent-first software engineering

**Question:** How should the repository, workflow, tests, artifacts, and team practices evolve when coding agents are persistent contributors?

This layer treats the repository as an interface for agents and humans. It includes specification-driven development, issue-to-PR orchestration, AGENTS.md, skills, architecture decisions, isolated worktrees, automated checks, exact-delivery QA, evals, and correction-to-infrastructure loops [R03][R04][R06][R07][R32][R33].

Useful nouns:

- agent-ready repository
- repository legibility
- layered AGENTS.md
- skill
- issue as control plane
- worktree isolation
- reviewable diff
- acceptance-to-evidence matrix
- fresh-context review
- exact-delivery test
- architectural fitness function
- correction-to-infrastructure loop

**Failure signal:** the agent repeatedly relearns conventions, broad refactors hide inside small tasks, source code passes while the packaged UI is broken, or review remains a manual archaeological exercise.

---

## 2. The distinctions that make prompts precise

### Model, agent, workflow, harness, runtime, and system

- **Model:** the learned reasoning and generation capability.
- **Model call:** one invocation with a context and expected output.
- **Workflow:** a predefined sequence or routing structure. Model judgment may appear inside stages, but the control path is mostly specified in advance.
- **Agent:** a system in which a model chooses at least some actions or next steps dynamically from feedback.
- **Harness:** the control machinery around the model or agent.
- **Runtime:** the infrastructure that executes and manages runs, including scheduling, persistence, streaming, cancellation, and recovery.
- **Sandbox:** an isolated execution environment with constrained filesystem, process, network, environment, and secrets.
- **Graph:** an explicit control topology of stateful nodes and edges. It may contain agents, deterministic functions, humans, or tools.
- **Agentic system:** the full arrangement of agents, humans, tools, data, services, policy, identity, state, and operations.

This vocabulary prevents a common category error: asking for “an agent” when the desired result is actually a deterministic pipeline with one model transformation, or asking for “a graph” when the need is merely a loop with a single retry edge.

### State, memory, context, and artifact

These are often conflated:

- **State** is the authoritative data that describes where the run is and what decisions have been made.
- **Memory** is information preserved for future use across turns or runs.
- **Context** is the subset of information presented to the model for the current inference.
- **Artifact** is a durable output that can be inspected or used outside the conversation.

A system can have durable state without giving all of it to the model. It can have memory that is never authoritative. It can produce an artifact without retaining conversational history. Good systems deliberately transform state into context rather than treating the two as identical.

### Tool, skill, subagent, service, and protocol

- **Tool:** a callable capability exposed through a schema and behavioral contract.
- **Skill:** a reusable package of instructions, references, scripts, and assets, typically loaded through progressive disclosure [R07][R19].
- **Subagent:** a separate model context delegated a scoped task, often useful for context isolation or fresh review.
- **Service/API:** a deterministic or separately operated system boundary.
- **MCP:** a protocol for exposing tools, resources, and prompts to models or agent clients [R27].
- **A2A:** a protocol for collaboration and task exchange between independent agent peers [R28][R29].

Do not turn every tool into an agent. Do not use A2A for a simple function call. Do not use a subagent where a deterministic script is cheaper, more reliable, and easier to test.

### Persistence, durability, resumability, and replay

- **Persistence:** state is stored beyond an in-memory step.
- **Durability:** the workflow can survive process or machine failure without losing its logical progress.
- **Resumability:** a paused or interrupted run can continue from a meaningful boundary.
- **Replay:** prior event history can deterministically reconstruct workflow state.
- **Idempotency:** repeating an operation with the same identity does not duplicate its externally visible effect.
- **Compensation:** a deliberate action mitigates or reverses a completed effect when true rollback is impossible.

Temporal’s guidance is central here: activities may be delivered at least once, so retry-safe external operations require idempotency or explicit deduplication [R25]. Production testing should kill and restart workers, replay histories, and exercise failure boundaries rather than only test the happy path [R26].

---

## 3. Control-flow patterns and when to use them

Anthropic’s “Building effective agents” remains a useful canonical pattern catalog: prompt chaining, routing, parallelization, orchestrator–workers, evaluator–optimizer, and autonomous agents [R13]. The 2026 refinement is to view these as composable control topologies rather than “agent maturity levels.”

### Direct transformation

Use one model call when the task is bounded, the input is sufficient, and the output can be validated. Examples: classify a support message, rewrite a paragraph under constraints, extract fields into a schema.

Prompt vocabulary: **single bounded transformation, structured output, schema validation, no tool loop.**

### Prompt chain / deterministic workflow

Use a chain when the stages are known and each has a clear handoff: specify → draft → deterministic check → package.

Prompt vocabulary: **stage contract, validated handoff, deterministic routing, fail closed, explicit exit.**

### Router

Use a router when one input class determines one of several specialized paths. Prefer deterministic routing when rules are sufficient; use a model router when classification is semantic.

Prompt vocabulary: **route taxonomy, confidence threshold, fallback route, unknown class, route-specific context.**

### Fan-out / fan-in

Use parallelization when subtasks are independent and their outputs can be merged under a clear aggregation contract. Parallelism is not the same as multiple agents; independent deterministic or model calls can fan out without autonomous peers.

Prompt vocabulary: **dependency graph, non-overlapping ownership, parallel workers, fan-in reducer, merge conflict policy.**

### Evaluator–optimizer loop

Use when a useful oracle or rubric can judge an intermediate artifact and revisions are expected. Coding is a strong fit when tests, linters, types, build output, rendered behavior, or a reviewer can provide concrete feedback [R13].

Prompt vocabulary: **candidate, evaluator, critique schema, repair pass, convergence threshold, maximum iterations, regression protection.**

### Bounded single-agent tool loop

Use when the next action genuinely depends on newly observed evidence. Define tools, state, budgets, stop conditions, and escalation. Do not say merely “work autonomously.”

Prompt vocabulary: **observe–plan–act–verify, action budget, tool policy, stop condition, assumption ledger, escalation threshold.**

### Orchestrator–workers / supervisor–workers

Use when the orchestrator must dynamically decompose work and workers benefit from separate context, tools, or expertise. Require non-overlapping ownership and an integration contract. Anthropic’s multi-agent research system illustrates the value of parallel specialized exploration, but also the coordination and token costs [R20].

Prompt vocabulary: **delegation contract, context isolation, task dependency graph, worker ownership, shared-state rule, aggregation, consequence gate.**

### Explicit state graph

Use when control flow has meaningful branches, cycles, interrupts, long-lived state, or recovery paths. A graph is often the right representation for human approval, durable resumes, conditional retries, and multi-stage business processes [R21][R22][R23][R24].

Prompt vocabulary: **typed state, node contract, conditional edge, reducer, checkpoint, interrupt, resume command, recovery edge, terminal state.**

### Durable workflow

Use when a run may outlive a process, wait on humans or external systems, or perform consequential side effects. Add checkpoints, replay, idempotency, timeouts, cancellation, and effect journaling.

Prompt vocabulary: **durable execution, event history, checkpoint boundary, replay-safe activity, idempotency key, compensation, timeout, heartbeat.**

### Multi-agent system

Use only when specialists or parallel work deliver enough value to offset coordination, observability, shared-state, and security cost. Multi-agent should be a reasoned architecture decision, not a synonym for “advanced.”

Prompt vocabulary: **agent identity, capability boundary, delegation protocol, task ownership, conflict resolution, shared-state authority, trust boundary, kill switch.**

---

## 4. Loop engineering in detail

A strong coding loop can be expressed as:

```text
observe → orient → plan → act → verify → update → exit | recover | escalate
```

### Observe

Collect task, repository, environment, and failure evidence. Inspect relevant AGENTS.md files, architecture, tests, neighboring code, current branch state, logs, and exact user path.

Contract: observations must distinguish facts from assumptions and preserve provenance.

### Orient

Build a situation model: current behavior, intended behavior, constraints, invariants, dependencies, risks, and uncertainty. This prevents premature editing.

Contract: name ranked hypotheses or candidate approaches and what evidence would falsify them.

### Plan

Choose the smallest coherent next action or a dependency-aware sequence. A plan is not ceremonial. It is a control artifact that exposes scope, ordering, parallelizable work, and verification points. OpenAI’s Codex guidance recommends plan-first operation for non-trivial work [R06].

Contract: each plan item has an intended artifact and a check.

### Act

Modify the environment through bounded tools. Use isolated worktrees for parallel runs. Preserve public contracts unless the specification authorizes change. External mutations require identity, scope, and approval policy.

Contract: actions are attributable, permissioned, and retry-safe.

### Verify

Use the strongest available oracle:

1. deterministic schema or invariant check;
2. unit or property test;
3. integration or end-to-end test;
4. type/lint/build check;
5. rendered interaction through real controls;
6. rubric/evaluator;
7. human judgment for weak-oracle decisions.

Contract: a completion claim points to evidence, not confidence.

### Update

Record new state, evidence, decisions, and residual risks. Decide whether to exit, repair, retry, replan, compensate, or escalate.

Contract: state updates are deterministic where possible and append evidence without silently overwriting history.

### Budgets

Every non-trivial loop should have explicit limits:

- maximum model turns or iterations;
- maximum tool calls;
- token/context budget;
- elapsed-time deadline;
- spend budget;
- number and class of external effects;
- retry limits by error class;
- human escalation threshold.

Without budgets, “autonomy” becomes unbounded resource use and unpredictable behavior.

### Failure classes and recovery

Do not use one generic retry policy. Distinguish:

- transient infrastructure failure → backoff and retry;
- deterministic validation failure → repair from structured feedback;
- permission denial → request approval or narrower tool;
- missing context → retrieve or ask under the assumption policy;
- semantic ambiguity → compare alternatives or escalate;
- invariant violation → halt and preserve evidence;
- duplicate-effect risk → deduplicate with idempotency key;
- external partial completion → reconcile or compensate;
- budget exhaustion → checkpoint and hand off.

---

## 5. Graph engineering in detail

A production graph is more than circles and arrows. Its engineering unit is the **state transition contract**.

### Typed state

Define authoritative fields, ownership, provenance, and update rules. Example:

```ts
type RunState = {
  runId: string;
  objective: string;
  phase: 'orient' | 'plan' | 'implement' | 'verify' | 'review' | 'complete' | 'blocked';
  assumptions: Array<{ claim: string; reversible: boolean; source: string }>;
  plan: PlanItem[];
  evidence: EvidenceItem[];
  effects: EffectRecord[];
  budgets: { iterationsLeft: number; toolCallsLeft: number; deadline: string };
  approval?: ApprovalRequest;
  residualRisks: string[];
};
```

The model should not arbitrarily rewrite the entire state object. Nodes should return narrow patches, and reducers should control how lists, counters, and competing parallel updates combine.

### Node contract

Each node should specify:

- input state subset;
- context assembly;
- allowed tools and permissions;
- output schema;
- possible error classes;
- state patch or artifact;
- verification;
- retry and escalation policy.

A node called `do_work` is not a contract. `implement_scoped_change`, `run_targeted_checks`, or `prepare_approval_request` is legible.

### Edge contract

Edges should be named by decision or evidence:

- `tests_passed`
- `repairable_failure`
- `requires_human_decision`
- `budget_exhausted`
- `external_effect_confirmed`
- `invariant_violated`

Avoid routing from unconstrained model prose when a deterministic condition can inspect typed state.

### Reducers and concurrency

Parallel nodes need merge rules. “Shared state” without ownership invites lost updates and conflicts. Use append-only evidence, namespaced worker outputs, compare-and-swap versioning, deterministic reducers, or explicit integration nodes.

### Checkpoints and interrupts

A checkpoint persists state at a meaningful boundary. An interrupt pauses execution and exposes enough context for a person to approve, edit, reject, or redirect. LangGraph’s interrupt model is useful because it preserves state and resumes through a command rather than pretending the human response is an ordinary message [R24].

Place irreversible effects after the approval boundary, not before it. Keep pre-interrupt operations idempotent because they may run again during resume or replay.

### Replay and side effects

Replay reconstructs state by re-executing deterministic workflow logic from history. External effects must not fire twice. Use:

- idempotency keys;
- an effect journal with pending/committed/reconciled states;
- deduplication at the target system;
- a transactional outbox;
- compensation for effects that cannot be rolled back.

### Graph observability

Capture:

- run and trace identifiers;
- node start/end and duration;
- state transition summaries;
- model and tool metadata with redaction;
- approval events;
- retries and recovery class;
- evidence produced;
- external effects;
- terminal outcome.

OpenTelemetry’s GenAI conventions are emerging toward standardized model and agent telemetry, but adoption and schema stability should be treated as an evolving integration surface rather than a finished universal standard [R39].

---

## 6. Harness engineering for Codex

### The harness as a control plane

A useful decomposition is:

```text
CONTROL PLANE
specification · repository guidance · context assembly · loop · graph · tools
permissions · approvals · state · tracing · evaluation · recovery · handoff

TRUST BOUNDARY

EXECUTION PLANE
sandbox · worktree · filesystem · shell · browser · network · services · secrets
```

OpenAI’s Sandbox Agents guide explicitly makes this distinction [R05]. It helps you ask the right question: is the missing capability a reasoning instruction, a context source, a tool, an execution permission, a state primitive, a verifier, or a recovery mechanism?

### Repository guidance: AGENTS.md

AGENTS.md is an open convention for giving coding agents repository instructions [R12]. Strong guidance is:

- short enough to remain salient;
- layered by directory or subsystem;
- specific about commands, invariants, public contracts, and forbidden changes;
- verified against the actual repository;
- updated when a repeated failure reveals a missing rule.

Do not turn AGENTS.md into a complete architecture manual. Use links and progressive disclosure.

### Skills

A skill packages instructions, supporting references, scripts, and assets for a recurring job. OpenAI’s 2026 skill guidance emphasizes progressive disclosure: the agent sees a compact skill description and loads detailed content only when needed [R07]. Skills are appropriate for design QA, deployment, database migration, incident analysis, release preparation, accessibility audits, or organization-specific workflows.

A strong skill has:

- clear triggers and non-triggers;
- a bounded workflow;
- explicit output artifacts;
- deterministic helper scripts where possible;
- validation and examples;
- a test or eval set.

### Isolated execution

Use a sandbox when running untrusted code, browsing untrusted content, mutating repositories, or accessing tools with real consequences. Use isolated worktrees when agents operate in parallel. Worktree isolation does not solve logical overlap; task ownership and merge policy still matter.

### Tool contracts

A tool contract includes more than a function signature:

- purpose and selection guidance;
- typed inputs and outputs;
- stable identifiers;
- error taxonomy;
- side effects and idempotency;
- permissions and target scope;
- latency/cost expectations;
- human-visible description at approval time.

Both MCP and Anthropic’s tool-design guidance emphasize precise tool names, descriptions, and schemas [R18][R27]. The model should not have to infer whether a tool reads, writes, sends, deploys, or purchases.

### Approval policy

Approval should be risk-based, not universal and not theatrical. Ask for approval when an action is:

- irreversible or difficult to compensate;
- externally visible;
- privileged;
- expensive;
- legally or ethically consequential;
- based on unresolved ambiguity;
- broader in scope than the original contract.

The approval UI should show the action, target, scope, data, reason, risk, alternatives, and what will happen on approval or rejection. OpenAI’s agent safety guidance also emphasizes that untrusted data should not be allowed to directly drive agent behavior and that approvals and guardrails should be paired with evals and trace analysis [R09].

### Recovery and resumability

Long-running coding agents need more than a persistent transcript. Preserve:

- issue or run identity;
- current phase and plan;
- checked-out commit/worktree;
- decisions and assumptions;
- tool/effect journal;
- checks already run and evidence;
- approval state;
- next safe action.

A resumed run should orient from state, not repeat the whole history.

---

## 7. Agent-first software engineering

### The repository is an agent interface

OpenAI’s harness-engineering report argues that end-to-end coding autonomy depends on repository-level tooling and guardrails, not only model quality [R03]. An agent-ready repository makes correct behavior discoverable and incorrect behavior difficult.

High-leverage characteristics:

- fast, deterministic setup;
- discoverable architecture and ownership;
- layered AGENTS.md;
- small, stable public interfaces;
- meaningful types and schemas;
- local, targeted tests;
- reproducible builds;
- clear error output;
- isolated worktrees;
- fixtures and seeded environments;
- screenshot or visual-regression paths where UI matters;
- release and rollback scripts;
- architecture fitness checks.

### Specification-driven development

GitHub’s Spec Kit frames agentic software development as a sequence such as constitution → specify → clarify → plan → tasks → implement → converge [R32][R33]. The value is not ceremony; it is keeping consequential product and architecture decisions explicit before code generation accelerates implementation.

For a substantial Codex task, ask for:

1. a situation and repository assessment;
2. an execution-ready specification;
3. a dependency-aware plan;
4. implementation in the smallest coherent slices;
5. verification after each slice;
6. fresh-context review;
7. exact-artifact validation;
8. handoff with decisions, evidence, and residual risk.

### Issue tracker as control plane

OpenAI’s Symphony concept treats issues as durable work objects and orchestrates coding agents around them [R04]. An issue can hold objective, context, acceptance criteria, priority, dependencies, status, and links to artifacts. This is more operationally useful than a chat session because it survives workers, machines, and time.

### Fresh-context review

The implementation context is biased by its own decisions. A fresh review context can inspect the diff, specification, test evidence, and rendered result without inheriting every rationalization. The reviewer should identify defects, scope drift, weak assumptions, missing tests, and unverified claims, then return structured findings for repair.

### Exact-delivery verification

A common failure is verifying source code while shipping a different artifact. Examples:

- source app works; production bundle has missing assets;
- mocked controls work; real controls do not;
- desktop screenshot looks right; mobile overflows;
- unit tests pass; integration auth fails;
- generated files exist; download links are wrong;
- code compiles; browser console is broken.

Ask explicitly to test the **exact packaged or hosted artifact**, through real user controls, at representative viewport and input conditions.

### Correction-to-infrastructure loop

When the same correction appears twice, encode it in the narrowest durable layer:

- product ambiguity → specification template;
- repository convention → AGENTS.md;
- repeated workflow → skill;
- deterministic defect → test or linter;
- architectural drift → fitness function or ADR;
- tool misuse → schema or permission policy;
- approval confusion → approval contract;
- recurring evaluation failure → eval case;
- visual regression → rendered QA or screenshot test.

This is how teams reduce back-and-forth over time.

---

## 8. Evaluation and evidence

### Why agent evals differ from single-response evals

Agents produce trajectories: multiple model calls, tools, state transitions, and environment changes. Anthropic’s 2026 eval guidance stresses that evaluation must account for non-deterministic paths and changing environments, not only a final text answer [R17].

Evaluate at four levels:

1. **Outcome:** Was the task actually completed?
2. **Trajectory:** Were actions efficient, safe, relevant, and policy-compliant?
3. **Recovery:** Did the system respond correctly to failures, interruptions, and ambiguous evidence?
4. **Operations:** Was the run observable, bounded, resumable, and cost-aware?

### Acceptance-to-evidence matrix

For every acceptance criterion, identify:

- the check or observation;
- the environment;
- the expected result;
- the produced evidence;
- the owner of judgment;
- the consequence of failure.

Example:

| Acceptance criterion | Check | Evidence |
|---|---|---|
| Mobile layout has no horizontal overflow | Render exact artifact at 390×844 and compare `scrollWidth` to `clientWidth` | Automated result + screenshot |
| Retried external mutation does not duplicate | Execute same idempotency key twice | Target-system record count + effect journal |
| User can resume after approval | Pause at interrupt, edit state, resume with command | Trace showing checkpoint, approval, and next node |
| Feature preserves public interface | Type check, contract tests, diff review | Test log + API diff |

### Benchmark literacy

SWE-bench Verified uses a curated set of real repository issues and remains useful for patch-generation capability [R34]. Terminal-Bench expands evaluation to terminal tasks in controlled environments [R35]. SWE Atlas broadens software-engineering evaluation beyond issue patching into areas such as tests, question answering, and refactoring [R37]. METR’s time-horizon work estimates the task durations at which frontier models achieve specified success rates, while explicitly noting methodology and task-distribution limitations [R36].

Use benchmarks to understand capability surfaces, not to infer that your repository, task distribution, harness, or human workflow will achieve the same result. Real developer studies can diverge from benchmark gains because environment, familiarity, review, and coordination matter.

### Evals as development infrastructure

An eval set should grow from observed failures. Store:

- task/specification;
- environment fixture;
- expected outcome and invariant;
- grading logic;
- prohibited shortcuts;
- trajectory signals;
- failure taxonomy;
- baseline and regression history.

OpenAI’s work on systematically testing skills treats skills as testable system components rather than static prompt files [R08]. That mindset applies to AGENTS.md, tool contracts, loop policies, and review agents as well.

---

## 9. Security and governance

OWASP’s Agentic Security Initiative organizes risks that go beyond ordinary prompt injection: goal hijacking, tool misuse, identity and privilege abuse, memory poisoning, insecure inter-agent communication, cascading failures, trust exploitation, and rogue behavior [R38]. The engineering response is capability control and provenance, not only content filtering.

### Trust and provenance model

Label context by source and authority:

- system or organization policy;
- user instruction;
- repository-owned guidance;
- trusted service data;
- retrieved external content;
- model-generated hypothesis;
- tool result;
- human approval.

Untrusted content can be evidence but should not silently become instructions. Preserve the distinction in state and context assembly.

### Least privilege

Scope identity and tools by:

- run;
- environment;
- repository;
- path;
- operation class;
- service;
- target resource;
- duration.

Use short-lived credentials and default-deny network or secret access. Do not give a research or review agent deployment permissions because another agent might need them later.

### Side-effect control

For each side-effecting tool, define:

- target and scope;
- preconditions;
- approval class;
- idempotency behavior;
- effect identity;
- rollback or compensation;
- audit record;
- dry-run mode.

### Memory poisoning

Persistent memory needs write policy, provenance, confidence, expiry, review, and deletion. Do not let any retrieved page or model inference become durable memory merely because it was in context once.

### Cascading failure containment

Multi-agent systems can amplify an incorrect assumption across workers. Use scoped delegation, independent verification for consequential conclusions, shared-state ownership, budgets, circuit breakers, and a system-level kill switch.

### Security evals

Test:

- untrusted instructions embedded in files or pages;
- privilege escalation attempts;
- approval bypass;
- tool argument smuggling;
- memory contamination;
- cross-agent impersonation;
- duplicate external effects;
- runaway loops and spend;
- sensitive data in traces or artifacts;
- partial failure and recovery.

---

## 10. Protocol and interface trends

### MCP and A2A

The cleanest current boundary is:

- **MCP** for exposing tools, resources, and context to an agent client;
- **A2A** for collaboration, discovery, communication, and task exchange between independently operated agent peers [R27][R28][R29].

Choose by system boundary, not fashion. A database query is a tool. A separately governed agent service that accepts long-running tasks and returns artifacts may be an A2A peer.

### Agent-driven UI

Google’s A2UI and MCP Apps are directional signals that agent interactions are moving beyond plain chat toward bounded, component-based interfaces [R40][R41]. The mature design principle is stable regardless of protocol: separate conversation, execution timeline, approvals, provenance, and durable artifacts. Do not stream raw tool logs as the primary UX.

### Artifact-centric UX

The user’s mental model should center on the work object: task, branch, report, plan, dataset, review, or deployment. The conversation is one control surface. The run timeline explains progress. Approvals appear at consequential boundaries. The artifact remains editable, versioned, and attributable.

---

## 11. The 2026 trend radar

The fieldbook classifies claims using four evidence levels:

- **A — constraint / standard:** protocol, specification, normative platform behavior, or non-negotiable engineering constraint.
- **B — supported practice:** convergent first-party engineering guidance, mature practitioner evidence, or repeated operational success.
- **C — emerging evidence:** recent implementation pattern, research result, or early ecosystem convergence that is useful but not settled.
- **D — directional signal:** plausible movement worth watching, not a basis for high-risk architecture by itself.

| Trend | Evidence | Practical interpretation |
|---|---:|---|
| Harness engineering becomes first-class | B | Diagnose model + context + tools + runtime + verification, not prompt alone. |
| Repositories become agent-ready products | B | Optimize setup, legibility, tests, invariants, and machine-readable guidance. |
| Skills replace one-off procedural prompts | B | Package repeated workflows with progressive disclosure and evals. |
| Parallel agents use isolated worktrees | B | Separate execution environments and define non-overlapping ownership. |
| Issue trackers become agent control planes | C | Durable task objects coordinate asynchronous work better than chat. |
| Agents become resumable and asynchronous | B | Persist run state, evidence, worktree identity, and approvals. |
| Hybrid deterministic + model graphs | B | Put semantic judgment in model nodes and policy/invariants in code. |
| Interoperability splits into MCP and A2A | A | Use tool/resource protocols separately from peer-agent collaboration. |
| Context engineering replaces context accumulation | B | Curate high-signal context and compact aggressively. |
| Evals and traces become development infrastructure | B | Treat trajectories, recovery, and skills as testable components. |
| Security moves from filtering to capability control | B | Prioritize provenance, least privilege, identity, and side-effect policy. |
| Agent UX becomes artifact-centric | B | Separate conversation, run timeline, artifact, provenance, and approval. |
| Agent-generated interfaces become bounded | D | Generate within vetted component and policy grammars, not arbitrary markup. |
| Benchmarks broaden beyond patch generation | C | Evaluate terminal work, tests, refactoring, Q&A, and long-horizon tasks. |
| Spec-driven development grows for coding agents | C | Preserve product and architecture decisions before rapid implementation. |
| Humans move up the abstraction stack | C | Humans increasingly frame outcomes, resolve ambiguity, and validate evidence. |

The evidence label is part of the recommendation. A directional interface protocol should not be treated like a mature durability primitive. A benchmark improvement should not be treated like a production guarantee.

---

## 12. Translating “professional polish” into engineering contracts

When an output works but feels incoherent, the missing requirement is rarely “more polish.” Decompose the judgment.

### Product truth

- Who uses this?
- What decision or job should become easier?
- What evidence or comparison do they need?
- What is the consequence of error?
- What is the durable work object?

### Information architecture

- What are the top-level objects and relationships?
- What must be visible together for comparison?
- What is primary, secondary, and reference information?
- What changes on mobile rather than merely shrinking?

### Interaction contract

- What states exist: idle, preparing, running, streaming, paused, awaiting approval, failed, recovering, complete, canceled?
- What can the user edit, undo, retry, resume, or inspect?
- Where do approvals appear?
- What happens after refresh or interruption?
- How are uncertainty and provenance shown?

### Visual system

- What is the compositional concept?
- What is the typography hierarchy?
- What density fits the task and expertise?
- What one signature move carries distinction?
- Which familiar controls should remain conventional?
- Which generic AI/SaaS clichés are explicitly rejected?

### Content and tone

- Are labels concrete and domain-specific?
- Are empty, error, and recovery states written?
- Does the interface explain consequences, not only actions?
- Does it distinguish provisional from committed results?

### Verification

- Is the exact artifact rendered at desktop and mobile?
- Are real controls used rather than programmatic state injection?
- Are keyboard, focus, reduced motion, and contrast checked?
- Are console, network, and packaged assets healthy?
- Are screenshots matched to the tested build?

This transformation turns “make it polished” into a set of implementable and reviewable decisions.

---

## 13. A prompt contract for substantial Codex work

Use this structure as a starting point:

```markdown
# Execution Contract

## Objective
State the user or business outcome, not only the implementation activity.

## Situation and context
Describe the repository, audience, current behavior, relevant constraints, and known evidence.

## Deliverable contract
Name every durable artifact and its required format, location, and integration point.

## Constraints
List public interfaces, dependencies, design-system rules, environments, budgets, security boundaries, and compatibility requirements.

## Anti-goals
Name plausible but unwanted interpretations: broad refactor, generic AI dashboard, chat-only UX, new dependency, placeholder data, source-only verification, and so on.

## Execution model
Choose and name the architecture: deterministic workflow, bounded tool loop, explicit state graph, durable workflow, orchestrator–workers, or a combination. Define phases and ownership.

## Autonomy and approval policy
Allow reversible assumptions; require escalation for irreversible, externally visible, privileged, expensive, or product-defining decisions.

## Verification and evidence contract
Map acceptance criteria to tests, builds, rendered behavior, screenshots, traces, or human review. Require exact-delivery validation.

## Output and handoff
Require decisions, files or artifacts changed, commands and results, evidence, assumptions, and residual risks.
```

Add these operating rules:

- Prefer the smallest architecture that fits.
- Use deterministic code for deterministic work.
- Tie every completion claim to evidence.
- Separate facts, assumptions, and hypotheses.
- Preserve provenance and least privilege.
- Encode repeated correction in a durable system layer.
- Stop or escalate when budgets or consequential ambiguity thresholds are reached.

---

## 14. Failure clinic: recurring symptoms and the missing concept

| Symptom | Usually missing | Vocabulary to add |
|---|---|---|
| The agent asks too many questions | Assumption and escalation policy | reversible assumption, consequence threshold, ask-only-if |
| The output works but lacks coherence | Product truth and reference matrix | design direction, hierarchy, interaction contract, anti-cliché audit |
| The agent rewrites too much | Scope and invariants | smallest coherent change, public contract, anti-goal, diff budget |
| The agent loops forever | Exit and budget policy | stop condition, action budget, convergence, escalate |
| Corrections are lost across sessions | Durable guidance | AGENTS.md, ADR, skill, memory write policy |
| The agent says “done,” but UI is broken | Exact-delivery verification | rendered control test, viewport matrix, console health |
| Multiple agents conflict | Ownership and dependency graph | non-overlapping work, worktree, fan-in reducer, integration owner |
| Retries duplicate tickets or messages | Idempotency and effect journal | idempotency key, deduplication, action ledger, compensation |
| Human approval is constant noise | Risk classification | consequence gate, approval class, trusted auto-action |
| The graph cannot resume cleanly | Checkpoint and interrupt semantics | durable state, resume command, idempotent pre-interrupt work |
| Tool use is unpredictable | Tool contract | schema, side effects, permissions, error taxonomy |
| Benchmark success does not transfer | Environment-specific evals | task distribution, fixture, trajectory eval, exact repository evidence |

The diagnostic question is: **Which decision is currently implicit, and which layer should own it?**

---

## 15. Recommended learning sequence

### Pass 1 — Name the layers

Be able to distinguish specification, context, harness, loop, graph, system, and software engineering. Practice diagnosing one disappointing result at each layer.

### Pass 2 — Master the smallest fitting topology

Given a task, choose among direct call, deterministic workflow, router, fan-out/fan-in, evaluator–optimizer, bounded agent loop, explicit graph, durable workflow, and multi-agent system.

### Pass 3 — Write contracts

For one real Codex task, write:

- deliverable contract;
- assumption policy;
- autonomy/approval policy;
- tool contract;
- state and stop conditions;
- acceptance-to-evidence matrix.

### Pass 4 — Build a harness brief

Identify what belongs in AGENTS.md, a skill, a script, a test, an eval, the sandbox, the run state, the trace, and the approval UI.

### Pass 5 — Operationalize correction

Review the last five times you had to correct ChatGPT or Codex. For each correction, choose the durable layer that should prevent recurrence.

### Pass 6 — Evaluate the exact artifact

Run the real user path on the exact deliverable at desktop and mobile. Exercise error, recovery, interruption, and approval states. Preserve matched evidence.

---

## 16. Architecture review questions

Use these before implementation:

1. What is the smallest architecture that satisfies the task?
2. Which decisions require model judgment, and which can be deterministic?
3. What state is authoritative, and who may update it?
4. What information enters model context at each step, and with what provenance?
5. What are the loop’s budgets, stop conditions, and escalation rules?
6. Which edges represent evidence, failure, approval, recovery, or terminal states?
7. Which operations have side effects, and are they idempotent?
8. Where are checkpoints placed, and what can safely replay?
9. What requires human judgment, and what exactly will the approval show?
10. How are tools scoped by identity, target, operation, and duration?
11. How will parallel workers avoid overlap and merge deterministically?
12. What is the verification oracle for every acceptance criterion?
13. How will traces support debugging without leaking sensitive data?
14. What artifact remains after the conversation ends?
15. Which repeated instructions should become repository infrastructure?
16. How will the exact packaged or hosted artifact be tested?

---

## 17. Closing model

A concise mental model:

```text
MODEL
provides semantic capability

+ SPECIFICATION
makes success and boundaries explicit

+ CONTEXT
gives the model the right working evidence

+ HARNESS
controls tools, state, policy, tracing, and recovery

+ LOOP
adapts action to feedback under budgets

+ GRAPH
makes branches, cycles, interrupts, and reducers explicit

+ DURABLE RUNTIME
survives time, failure, and human latency

+ SOFTWARE ENGINEERING
makes the whole arrangement testable, maintainable, and evolvable
```

The professional prompt is therefore not the longest prompt. It is the prompt that places each consequential decision in the correct layer, delegates the rest to durable infrastructure, and requires observable evidence before completion.

---

---

## 18. What changed for Codex and GPT-5.6 Sol by July 2026

The current Codex customization surface makes the packaging decision consequential. Skills are discoverable through compact metadata and load their full instructions only when selected; plugins are installable bundles that can carry multiple skills and, when needed, connectors or MCP servers [R45][R46][R47][R53]. That creates a clear context-engineering rule: do not put an entire agent-systems textbook into one always-on instruction. Use a small routing skill for cross-layer architecture decisions, narrow skills for distinct jobs, local references for deep procedural knowledge, assets for reusable output contracts, and scripts for deterministic validation.

Version 1 established fifteen focused skills rather than one giant “agentic engineering” skill. Version 2 retains that architecture and expands it to twenty-seven skills: the cross-layer router, a lifecycle orchestrator, controlled field learning, ten focused lifecycle disciplines, Rust observability, and the original task-contract, repository, harness, loop, graph, multi-agent, evaluation, security, agent-first, and Rust engineering domains. Trigger descriptions front-load the situations that should activate each skill, negative activation boundaries prevent adjacent-but-wrong selection, and 106 skill-local plus 15 shared references preserve progressive disclosure. This structure is intended to improve activation precision, context economy, lifecycle continuity, and within-skill adherence.

GPT-5.6 Sol is the flagship Codex model for complex coding, computer use, research, and cybersecurity. The official Codex model guidance starts at medium reasoning and exposes deeper settings for harder work [R43][R44]. The engineering implication is not “always select maximum effort.” Sol performs best when it receives a decision-complete task, a legible repository, typed tools, an observable oracle, and enough autonomy to resolve reversible ambiguity. Higher reasoning cannot compensate for missing acceptance criteria, unsafe permissions, stale context, or a loop without a stop condition.

The plugin’s Sol operating profile therefore uses a graduated policy:

- normal implementation and review begin at the default power/medium reasoning;
- high or extra-high is justified by unfamiliar systems, broad evidence, consequential migrations, subtle concurrency, architecture tradeoffs, or weak observability;
- Max is reserved for the hardest coherent single-agent problem where additional depth matters more than latency or cost;
- Ultra or explicit subagents require meaningful parallel work packages, exclusive ownership, result schemas, cancellation, one integration owner, and global verification [R44][R49].

A key 2026 trend is model-side programmatic tool coordination. GPT-5.6 can write and run lightweight programs to coordinate tools, process intermediate results, monitor progress, and choose the next action [R43]. This increases the value of typed, composable tools and deterministic aggregation. It does not remove the need for a harness. Programmatic coordination still needs permission checks, deadlines, bounded concurrency, state, effect safety, trace IDs, and completion evidence.

OpenAI’s descriptions of the Codex loop and App Server reinforce that a production harness is broader than the prompt or model call. It includes thread lifecycle and persistence, configuration and authentication, sandboxed tool execution, skills/extensions, context/event streams, and the underlying iterative agent loop [R50][R51]. The plugin’s harness skill mirrors those responsibilities and adds explicit authorization, effect journals, recovery, evidence, and human approval boundaries.

### Operational consequence

For GPT-5.6 Sol, the highest-leverage prompt improvement is to stop asking for a vague style of intelligence and instead provide a control contract:

1. outcome and exact artifacts;
2. evidence and repository context;
3. constraints, invariants, and anti-goals;
4. smallest fitting topology;
5. authoritative state and effect boundary;
6. autonomy and approval thresholds;
7. acceptance-to-evidence mapping;
8. handoff and residual-risk requirements.

That task shape lets Sol spend its capability on semantic judgment and difficult implementation rather than repeatedly inferring product, safety, and delivery decisions.

---

## 19. Why the plugin ships no default hook, connector, or MCP server

The research supports rich tool and protocol integrations, but it also shows that every connector creates identity, data, permission, injection, availability, and supply-chain obligations [R09][R18][R27][R38][R41]. A plugin intended to improve architecture decisions across arbitrary repositories should not silently acquire network access, credentials, filesystem mutation beyond Codex’s host policy, or external side effects.

The v1 package is therefore instruction-, reference-, asset-, and validator-based. It does not install a hook, launch an MCP server, call the network, or require an agent framework. This design has three advantages:

1. **least privilege:** the plugin cannot widen Codex’s host sandbox or approval policy;
2. **portability:** the same decision system applies to local, cloud, IDE, and repository-specific environments;
3. **auditability:** users can inspect every procedure and template as files before use.

When a project does require MCP, A2A, an issue tracker, a deployment system, or a durable runtime, the corresponding skills force the integration to define typed schemas, identities, capability scopes, approval classes, timeouts, output sanitation, action IDs, reconciliation, and conformance tests. The absence of a bundled connector is not an anti-tool position. It prevents a general decision plugin from making an unearned privilege decision on behalf of every user.

---

## 20. Rust-specific operationalization

Rust is a strong fit for agent infrastructure when correctness depends on explicit state, ownership, concurrency, protocol boundaries, and predictable resource use. It is not automatically safe merely because it is memory-safe. Agent applications can still leak tasks, deadlock through lock/await interactions, accumulate unbounded queues, duplicate remote effects, persist incompatible state, expose credentials through `Debug`, or retry an ambiguous action.

The Rust portion of the plugin is divided into five skills because each failure family has different evidence and review obligations.

### Rust agentic architecture

The architecture skill keeps the domain independent from providers and frameworks. It models run/task/action IDs, state, decisions, proposed effects, capabilities, budgets, approvals, and evidence as typed domain concepts. Application services validate model proposals and turn them into authorized effects through ports. Provider SDKs, Rig or other frameworks, databases, MCP/A2A, and Tokio runtime types remain adapters [R18][R66][R67][R69][R70].

The key pattern is a decision/effect split:

```text
model proposes typed decision/effect
  -> parse and semantic validation
  -> policy and capability check
  -> approval when required
  -> effect intent journaled
  -> adapter dispatch under deadline
  -> reconcile and verify
  -> versioned state transition and evidence
```

This boundary improves testability and prevents vendor callback structures from becoming the application’s permanent domain model.

### Tokio runtime engineering

Tokio’s documentation makes cancellation and task completion explicit concerns; its graceful-shutdown guidance uses signal detection, cancellation tokens, and waiting for tasks [R55]. Tokio tasks are cooperatively scheduled, so blocking/non-yielding work can stall core threads [R56]. Semaphores and bounded channels make concurrency and pressure visible [R57].

The runtime skill therefore requires:

- a task ownership tree and tracked joins;
- propagated cancellation and absolute deadlines;
- bounded queues and per-resource semaphores;
- explicit overload behavior;
- no locks across model/network/tool awaits;
- isolation of blocking/CPU-heavy work;
- graceful shutdown that stops intake, cancels, drains, reconciles effects, checkpoints, and flushes evidence under a final deadline;
- tests at every await and effect boundary.

### Durability and effects

Durability is not “run the Tokio process for a long time.” It is the ability to reconstruct authoritative state and safely resume after process loss, deployment, human delay, duplicate delivery, or partial external success. The plugin uses an effect journal state machine, stable action/idempotency IDs, outbox/inbox patterns, optimistic concurrency, replay versioning, and explicit reconciliation. Durable execution platforms such as Restate are presented as options to evaluate against hard semantics rather than mandatory dependencies [R25][R26][R68].

The hardest test is crash after remote success but before the local result is recorded. A correct system resumes by looking up the action/idempotency ID and reconciling authoritative external state. It does not blindly resend.

### MCP and A2A

The MCP tools specification requires JSON Schema, but schemas are only the beginning. Servers need input validation, authorization, rate limits, timeouts, logging, output sanitation, and clear human visibility for consequential calls [R27]. The official Rust SDK supplies protocol machinery [R66]; the application still owns domain policy.

A2A addresses a different boundary: independently operated agents that advertise capabilities and exchange task lifecycle, messages, and artifacts. The official Rust SDK provides A2A v1 protocol types and async client/server support [R67]. The plugin keeps A2A DTOs in an adapter crate, maps external task IDs to durable internal state, authenticates peers, limits delegation, and requires independent interoperability tests.

### Rust verification

The verification ladder uses `cargo fmt`, `cargo check`, tests, Clippy, clean release builds, scenario/effect tests, Loom for small synchronization components, Miri for compatible unsafe/FFI-sensitive tests, and RustSec-based dependency checks [R58][R59][R60][R61][R62][R63][R64][R65]. `cargo check` is deliberately not treated as a complete build because official documentation notes that some diagnostics require code generation [R58].

The package includes adaptable Rust fragments for typed domain state, effect journals, tracked Tokio supervision, schema-first tools, and deterministic test fakes. They are examples, not a version-pinned crate. The release environment lacked `cargo` and `rustc`, so the package records Rust compilation as a target-environment test rather than a passed local gate. That limitation lowers empirical-transfer confidence and is visible in the release report.

---

## 21. Decision deltas: how the evidence changed the plugin

A research-backed plugin should make clear what decisions were caused by evidence.

### From one monolithic skill to a router plus focused skills

**Baseline instinct:** put all research in one giant SKILL.md so it is always available.  
**Evidence:** Codex skills use progressive disclosure; discovery depends on concise metadata; focused skills improve routing and avoid context bloat [R07][R45][R53].  
**Decision:** retain the architecture router, add a lifecycle orchestrator and focused field/lifecycle skills, and hold depth in 106 skill-local plus 15 shared references instead of an always-on monolith.

### From “agentic by default” to architecture escalation

**Baseline instinct:** use loops, graphs, or several agents for difficult work.  
**Evidence:** workflow-versus-agent distinctions and production multi-agent accounts show that adaptive autonomy and coordination have costs [R10][R13][R20][R30][R49].  
**Decision:** direct call → deterministic workflow → bounded loop → explicit graph → durable workflow → multi-agent, with a named requirement for every escalation.

### From retry advice to effect-state protocols

**Baseline instinct:** use exponential backoff for failures.  
**Evidence:** durable systems and interrupt/replay guidance show that at-least-once execution and ambiguous external effects require idempotency and reconciliation, not blind retry [R24][R25][R26].  
**Decision:** typed failure classes, stable action IDs, intent-before-dispatch journal, timeout phase, reconcile/compensate paths, and crash-point tests.

### From broad permissions to consequence-based capabilities

**Baseline instinct:** let the agent use all tools in a sandbox and ask for confirmation occasionally.  
**Evidence:** agent safety, MCP, and OWASP guidance distinguish sandboxing, authorization, approvals, input/output trust, and governance [R09][R27][R38].  
**Decision:** capabilities scoped by actor/operation/target/environment/duration; approval payloads show normalized consequence; sandbox is treated as an independent execution boundary.

### From final-answer quality to trajectory evidence

**Baseline instinct:** evaluate whether the final answer or code passes tests.  
**Evidence:** agent eval literature emphasizes multi-turn trajectories, tool behavior, recovery, graders, and environment [R08][R17][R35][R36][R37].  
**Decision:** separate outcome, trajectory, recovery, safety, and operational dimensions; every completion claim links to exact evidence.

### From framework-centric Rust to ports, typed state, and adapters

**Baseline instinct:** select an agent framework and organize the code around its abstractions.  
**Evidence:** protocol/SDK/framework surfaces evolve, while Rust’s strongest leverage is typed state, explicit ownership, and testable boundaries [R54][R55][R66][R67][R68][R69][R70].  
**Decision:** provider/framework/protocol/runtime isolation; domain decisions and effects remain portable; framework adoption requires an explicit record.

### From maximum Sol effort to graduated model use

**Baseline instinct:** use Max/Ultra for the best result.  
**Evidence:** official Codex model guidance begins with medium and identifies Sol as flagship; subagents are most useful for highly parallel work [R44][R49].  
**Decision:** default medium, escalate reasoning for named difficulty, and require an Ultra delegation/fan-in protocol.

---

## 22. Confidence model, validation boundary, and update policy

The requested threshold is interpreted as at least 95% calibrated confidence that installing and appropriately invoking this plugin will improve the related decision process and expected output quality relative to giving GPT-5.6 Sol only an underspecified request. It is not a claim that every project outcome has a 95% probability of success.

The release score combines:

- evidence quality, recency, and source diversity;
- traceability from findings to skill behavior;
- skill routing and behavior-contract coverage;
- structural/plugin validity and link integrity;
- Rust architecture/static-quality review;
- target-model empirical transfer.

The last dimension is intentionally scored lower because this environment did not contain a Codex CLI/session runner and could not execute a blind Sol A/B suite. It also lacked Cargo/rustc, so the Rust fragments could not be compiled here. Those checks are not represented as passed. The package includes exact downstream protocols for both.

A release above the threshold additionally requires all mandatory deterministic gates to pass: manifest/marketplace structure, unique skills, frontmatter, reference/link integrity, concise metadata budget, scenario/behavior/routing coverage, source/evidence consistency, JSON/schema validity, Rust static anti-pattern checks, absence of placeholders/secrets, and reproducible file manifests.

The plugin is current to **July 22, 2026 (America/Los_Angeles)**. Model names, Codex plugin formats, protocol versions, SDK APIs, and framework maturity can change. `UPDATE-POLICY.md` requires re-verification before hard-coding those unstable details, and the source manifest records access dates for current documentation.

## 23. Authentic-use engineering: the missing discipline

The missing concept is not simply “dogfooding,” “user testing,” “telemetry,” or “production evaluation.” It is a governed engineering system for learning from representative work while the cost of changing the product is still low.

This report uses **authentic-use engineering** as the umbrella term:

> Authentic-use engineering is the deliberate exposure of a product or agent to representative work inside an explicit operating envelope, with proportionate authority, joinable instrumentation, human oversight, and a closed evidence-to-change loop.

The purpose is not to ship unfinished software indiscriminately. The purpose is to replace untested assumptions with evidence about actual tasks, users, environments, tools, data, effects, interruptions, incentives, and recovery paths. Offline benchmarks, synthetic tasks, scripted demos, and retrospective datasets remain valuable, but they are preflight evidence. They cannot establish that the product fits real work, that users calibrate reliance correctly, that integrations behave under live conditions, or that operators can detect and recover from failures [R71][R73][R74][R75][R77][R78].

This discipline resolves a common product-development trap:

```text
assumption-heavy concept
        ↓
deep implementation
        ↓
late user exposure
        ↓
workflow mismatch, hidden safety problems, weak instrumentation
        ↓
expensive redesign or metric theater
```

The preferred loop is:

```text
explicit assumptions and risks
        ↓
smallest testable product slice
        ↓
controlled exposure to representative work
        ↓
joined outcome, trajectory, effect, intervention, and human-work evidence
        ↓
mechanism diagnosis
        ↓
product / eval / tool / policy / constraint change
        ↓
progressive re-exposure or stop
```

The key word is **controlled**. Consequential work creates better evidence only when exposure, authority, data, effects, and escalation are bounded. “Use it in production and see what happens” is not authentic-use engineering. It is unmanaged risk.

### 23.1 What authentic use adds beyond ordinary evaluation

A conventional evaluation asks whether the system succeeds on a defined task distribution. Authentic-use engineering also asks:

- Is the task distribution representative of the work that matters?
- Does the product enter the workflow at the right point?
- Does it change human behavior, coordination, or incentives?
- Are users appropriately relying on, correcting, or bypassing it?
- Which tools and dependencies fail under live timing, permissions, and data conditions?
- Do outputs cause intended effects, ambiguous effects, duplicated effects, or hidden downstream work?
- Can operators diagnose and recover before harm compounds?
- Which failures should become eval cases, tool constraints, interface changes, policies, or architecture changes?
- Does the product create durable value after novelty, training, and local champions are removed?

These questions require prospective use evidence. Silent or shadow trials are one controlled mechanism: the system observes live inputs and produces counterfactual outputs without influencing the actual decision or effect. Research on silent trials shows why prospective workflow and integration evidence can reveal problems that retrospective validation misses, while also demonstrating the need for precise reporting and predeclared transition criteria [R77][R78].

### 23.2 Consequential does not mean autonomous

A task can be consequential even when the agent has no direct side effects. A recommendation can change a financial, medical, security, operational, legal, hiring, deployment, or architectural decision. Therefore, the authority model must describe both **direct effect authority** and **decision influence**.

Use four questions:

1. **What may the system observe?** Inputs, metadata, history, tools, environments, and derived information.
2. **What may the system decide or recommend?** The semantic or planning decisions assigned to it.
3. **What may the system cause?** Files changed, messages sent, code merged, resources created, records updated, money spent, credentials used, or external actions taken.
4. **What must a human or deterministic control authorize?** Risk acceptance, irreversible commitments, high-blast-radius effects, policy exceptions, and transitions to broader exposure.

Anthropic’s empirical work on autonomy in practice reinforces that autonomy is graded and contextual. The appropriate question is not “Is this agent autonomous?” but “Within which task, environment, duration, effect, and oversight boundaries may it operate, and what evidence justifies that boundary?” [R73].

---

## 24. Vocabulary for field learning, evidence, and progressive autonomy

Vocabulary matters because it makes design decisions promptable. The following terms are deliberately operational rather than promotional.

### Authentic use

Use involving representative users, tasks, data, environments, dependencies, timing, and consequences. Authenticity is dimensional: a study can have real users but synthetic tasks, or real tasks but a nonrepresentative environment.

### Representative workload

A sampled distribution of tasks that reflects the cases the product is intended to handle, including routine work, edge cases, high-value cases, interruptions, incomplete inputs, and failure-prone situations. It is not a convenience sample of easy demonstrations.

### Ecological validity

The degree to which evidence reflects the conditions under which the product will actually be used. High benchmark validity does not imply high ecological validity.

### Operating envelope

The explicit boundary within which evidence and authorization are valid. It includes eligible users, task classes, data classes, models, tools, environments, integrations, effect types, resource budgets, quality thresholds, monitoring, exclusions, and escalation rules. Material change outside the envelope triggers reassessment rather than silent extrapolation [R75][R76].

### Operational design domain

A related term from safety-critical engineering: the conditions under which a system is designed to function. For agentic products, “operating envelope” is usually more useful because it also includes organizational authority, effects, budgets, and evidence thresholds.

### Exposure unit

The entity assigned to a treatment or operating mode: user, account, repository, task, session, organization, request, or time window. Choosing the wrong unit can create contamination or misleading analysis.

### Assignment

The decision that an exposure unit is eligible for a variant, feature, or autonomy level.

### Exposure

Evidence that the unit actually encountered the variant or behavior. Assignment without exposure should not be counted as equivalent use.

### Treatment integrity

The degree to which the intended variant was actually delivered and isolated from conflicting variants, fallbacks, stale configuration, or partial deployment.

### Sample ratio mismatch

A statistically inconsistent difference between intended and observed assignment proportions. It is a diagnostic symptom of potential assignment, eligibility, logging, survivorship, execution, or analysis failure. An unresolved sample ratio mismatch invalidates confident product conclusions [R80].

### Shadow mode / silent mode

The system processes representative live inputs and records what it would have done, but cannot influence the operational decision or effect. Shadow mode validates data, workflow, latency, integration, and counterfactual behavior. It does not validate human reliance or downstream impact because users may not see or act on the result [R77][R78].

### Observe-only mode

The system records state and behavior without generating a user-facing recommendation or effect. This is often the first live instrumentation step.

### Recommendation-only mode

The system produces advice or a proposed action, but a human remains responsible for evaluation and execution. This validates usefulness and reliance behavior but still creates decision influence.

### Approval-gated action

The system prepares an exact action and evidence package; a human or policy engine authorizes that specific effect before execution. Approval must reveal target, scope, parameters, reversibility, credentials, expected impact, and evidence—not merely ask “Continue?”

### Bounded autonomy

The system may execute without per-action approval inside a narrow envelope with explicit permissions, budgets, stop rules, monitoring, and recovery. Bounded autonomy is earned for specific task/effect classes, not granted globally.

### Progressive autonomy

A staged increase in authority based on evidence from lower-risk operating modes. The promotion decision considers task performance, severe failures, intervention burden, effect integrity, recovery, observability, distribution coverage, and residual risk.

### Blast radius

The maximum plausible scope of impact from a failure or mistaken action: number of users, records, repositories, services, dollars, credentials, environments, or downstream decisions affected.

### Effect budget

A deterministic bound on external actions, such as maximum writes, deployments, messages, financial value, affected records, or privilege level per run or time window.

### Intervention

A human action that changes, stops, corrects, constrains, or recovers the system’s work. Interventions are evidence, not noise. They can reveal missing context, poor controls, weak interfaces, incorrect assumptions, or appropriate oversight.

### Override

A human or policy decision that replaces the system’s proposed decision or action. Record the reason and downstream result rather than only the fact that an override occurred.

### Near miss

A condition that could have caused an unacceptable outcome but was prevented by chance, a control, a human intervention, or limited exposure. Near misses deserve regression and control analysis even when no final harm occurred.

### Ambiguous effect

An external action whose outcome is unknown—for example, a network timeout after sending a request. Ambiguous effects require reconciliation before redispatch to avoid duplicate or conflicting actions.

### Human work

The time and cognitive effort required to frame tasks, provide context, inspect outputs, correct errors, approve actions, reconcile effects, recover failures, and maintain the system. Product value should account for displaced and newly created human work.

### Friction budget

The acceptable amount and location of human effort. Removing every checkpoint is not the goal; place friction where it prevents consequential error and remove it where it adds no information or control.

### Calibrated reliance

A user’s tendency to accept, verify, correct, or reject system output in proportion to actual reliability and task risk. Raw adoption or acceptance rate is not a sufficient measure of appropriate reliance [R93][R94].

### Field observation

A structured record connecting context, system versions, task, trajectory, effects, outcome, interventions, evidence quality, and privacy classification for a unit of authentic use.

### Outcome evidence

Evidence about whether the user or system achieved the intended real-world result—not merely whether the agent returned an answer.

### Trajectory evidence

Evidence about the path taken: reasoning-relevant state transitions, tools, attempts, approvals, failures, retries, costs, latency, and recovery.

### Effect evidence

Evidence that an intended external action was prepared, authorized, dispatched, confirmed, reconciled, compensated, or left ambiguous.

### Evidence coverage

The proportion and distribution of intended operating conditions for which trustworthy evidence exists. A large volume of homogeneous data can still have poor coverage.

### Evidence strength

The degree to which an observation supports a decision. Strength depends on representativeness, measurement validity, causal identification, sample size, consistency, independence, and relevance to the exact operating envelope.

### Observational evidence

Evidence from naturally occurring use without controlled assignment. It is essential for diagnosis, hypothesis generation, rare-event detection, workflow understanding, and safety monitoring. It does not by itself establish that a product change caused an outcome.

### Causal evidence

Evidence from a design that supports attribution of outcome differences to an intervention—often randomized experiments, but sometimes strong quasi-experimental or interrupted designs when randomization is infeasible.

### Metric contract

A predeclared definition of a metric’s decision purpose, population, unit, event semantics, attribution window, aggregation, direction, minimum detectable change, exclusions, data-quality tests, guardrails, and limitations.

### Guardrail metric

A measure that constrains optimization by detecting unacceptable harm or degradation, such as severe-error rate, security incident rate, human correction burden, latency, reliability, accessibility, or downstream rework.

### Countermetric

A measure chosen to expose the predictable downside of optimizing the primary metric. For example, pair task completion with correction burden, or deployment frequency with change failure rate.

### Holdout

A persistent comparison population that does not receive the new behavior, used to estimate longer-term or cumulative effects. Holdouts require stable identity, contamination analysis, and ethical justification.

### Bake time

A predeclared observation period at an exposure level before promotion. It should reflect system latency, delayed outcomes, rare failures, traffic cycles, and dependency behavior rather than an arbitrary waiting period.

### Novelty and learning effects

Early behavior changes caused by attention, unfamiliarity, enthusiasm, or adaptation rather than durable product value.

### Carryover effect

A treatment effect that persists after assignment changes, compromising simple crossover comparisons.

### Intervention fidelity

The degree to which the intended product, tool, policy, or harness change was implemented as specified. A failed experiment may be an implementation failure rather than a product-theory failure.

### Regression harvesting

The practice of converting observed failures, near misses, overrides, and costly corrections into durable fixtures, eval tasks, property tests, threat cases, or policy tests.

### Evidence-to-change latency

Time from a meaningful field observation to an implemented, evaluated, and deployed response. It is a useful learning-system measure when paired with evidence quality and safety, but dangerous if optimized as speed alone.

### Learning velocity

The rate at which the team resolves important uncertainty with representative evidence. It is not feature throughput, experiment count, or telemetry volume.

### Instrumentation debt

Missing, ambiguous, high-cardinality, privacy-unsafe, unjoinable, or untrusted telemetry that prevents diagnosis and decision-making. Instrumentation debt is product debt because it blocks learning and safe operation.

### Decision record

A durable record of the question, evidence, uncertainty, alternatives, decision owner, chosen action, constraints, revisit trigger, and outcome. Decision records allow Codex and humans to reason from history without treating old conclusions as timeless rules.

---

## 25. The controlled field-learning system

A controlled field-learning system has nine interacting components. Leaving one implicit creates predictable blind spots.

### 25.1 Learning charter

Define the decision the field exposure is intended to inform. A charter answers:

- What uncertainty matters now?
- What product or architecture decision will change based on the evidence?
- Why are offline or proxy methods insufficient?
- What is the minimum representative exposure needed?
- What outcomes are beneficial, neutral, unacceptable, or unknown?
- Who owns promotion, hold, narrowing, revert, and stop decisions?

Without a decision-linked charter, teams collect telemetry without knowing what action it should inform.

### 25.2 Assumption and risk map

List assumptions by class:

- user and workflow assumptions;
- value and adoption assumptions;
- data availability and quality assumptions;
- model and tool capability assumptions;
- integration and latency assumptions;
- human oversight and reliance assumptions;
- security, privacy, legal, and policy assumptions;
- operational, economic, and support assumptions.

For each assumption, record importance, uncertainty, cheapest discriminating evidence, owner, and stop condition. Test assumptions with high consequence and high uncertainty first. A polished implementation does not reduce product-theory uncertainty.

### 25.3 Representative work sample

Construct a field sample deliberately. Stratify by:

- user role and expertise;
- task frequency and value;
- complexity and ambiguity;
- data sensitivity;
- tool and dependency set;
- reversibility and effect risk;
- expected duration;
- environment or repository type;
- failure history;
- accessibility and interaction needs;
- interrupted and resumed work;
- low-resource, degraded, or partial-data conditions.

Record exclusions. “Internal employees who volunteered” may be useful for early exposure, but it is not automatically representative of customers, reluctant users, novices, high-stakes operators, or hostile environments.

### 25.4 Operating envelope

The operating envelope is both a product specification and a safety control. At minimum define:

| Dimension | Required decision |
|---|---|
| Users | Eligible roles, training, support, opt-in/notice, exclusions |
| Tasks | Allowed task classes, prohibited tasks, consequence tiers |
| Data | Allowed classifications, minimization, retention, redaction |
| Models | Exact provider/model/configuration and change policy |
| Tools | Allowlisted tools, schemas, credentials, permission scope |
| Environment | Repositories, services, networks, regions, dependency assumptions |
| Effects | Allowed effect classes, budgets, reversibility, idempotency |
| Autonomy | Mode, approvals, intervention and override rights |
| Quality | Minimum outcome and severe-failure thresholds |
| Reliability | Latency, availability, degradation, recovery expectations |
| Monitoring | Required signals, freshness, joins, alert ownership |
| Escalation | Hold, narrow, revert, stop, incident, and reassessment triggers |

The evidence is valid only for the envelope observed. A new model, new tool, expanded permissions, different user population, or different effect class can be a material system change requiring re-evaluation [R75].

### 25.5 Autonomy and exposure ladder

Use the lowest stage that can resolve the current uncertainty:

1. **Replay/offline.** Historical or synthetic inputs; no live workflow contact.
2. **Observe-only.** Live state is instrumented; no generated output influences work.
3. **Shadow/silent.** Live inputs produce counterfactual output; no user or system effect.
4. **Recommendation-only.** Users see advice; humans own decisions and effects.
5. **Approval-gated.** Exact proposed actions require explicit authorization.
6. **Bounded autonomy.** Preauthorized effects within a narrow envelope and budget.
7. **Broader autonomy.** Expanded tasks or effects after sustained, representative evidence.

Promotion is not automatic. Each stage answers different questions:

| Stage | Can establish | Cannot establish alone |
|---|---|---|
| Replay/offline | repeatability, known-task performance, basic tool correctness | workflow fit, live integration, user reliance |
| Observe-only | baseline workflow and data conditions | system usefulness or action quality |
| Shadow | live input fit, latency, integration, counterfactual behavior | human response, actual downstream impact |
| Recommendation | usefulness, reliance, correction and decision influence | direct effect safety without human mediation |
| Approval-gated | proposed action quality, approval burden, effect execution under review | unattended behavior |
| Bounded autonomy | autonomous operation inside the envelope | general safety outside the envelope |

### 25.6 Instrumentation contract

Instrumentation is part of the product contract, not a logging afterthought. Every field observation should be joinable across these identities:

```text
product_version
model_configuration_version
prompt_policy_version
harness_version
tool_contract_version
operating_envelope_version
experiment_or_rollout_id
assignment_id
exposure_id
user_or_account_pseudonym
task_id
run_id
action_id
effect_id
trace_id
observation_id
```

Not every backend event needs every identifier, but the evidence pipeline must support reliable joins from user/task exposure to run, action, effect, outcome, and intervention. Trace IDs are diagnostic identifiers; they are not durable effect IDs or authorization identities [R123].

Capture five evidence planes:

1. **Task and context:** intent, task class, consequence tier, environment, relevant constraints.
2. **Trajectory:** state transitions, model/tool versions, tool calls, latency, budgets, errors, retries, recovery.
3. **Effects:** prepared, authorized, dispatched, confirmed, ambiguous, reconciled, compensated.
4. **Outcome:** user or system result, quality assessment, downstream rework, delayed consequences.
5. **Human work:** framing, review, approval, correction, override, recovery, abandonment, confidence, support effort.

OpenAI’s agent improvement loop and macro-evaluation examples motivate connecting real traces and feedback to evaluation and harness changes rather than storing unstructured transcripts [R71][R72].

### 25.7 Review cadence and triage

Use several review horizons:

- **Per-run:** severe failure, unauthorized effect, privacy/security event, ambiguous effect, stop-rule breach.
- **Daily or exposure-batch:** trace integrity, novel failure clusters, interventions, guardrails, distribution drift.
- **Promotion review:** sufficient coverage, outcome quality, severe-failure upper bound, human burden, effect integrity, recovery proof, data quality.
- **Periodic system review:** operating envelope validity, model/tool changes, emergent workarounds, long-term effects, support and economic sustainability.

Triage observations by consequence, recurrence, detectability, mechanism confidence, and leverage. A rare high-severity near miss can outrank a common cosmetic error.

### 25.8 Evidence-to-change loop

Every important observation should enter a structured loop:

```text
observation
  → classify consequence and evidence quality
  → reproduce or gather corroboration where feasible
  → form a mechanism hypothesis
  → choose intervention layer
  → encode regression or monitor
  → implement change
  → verify intervention fidelity
  → progressively expose
  → measure result
  → keep, revise, revert, or stop
```

Choose the intervention layer based on mechanism:

| Observed mechanism | Prefer changing |
|---|---|
| User cannot express intent | product interaction, vocabulary aid, task contract |
| Missing or stale information | context assembly, retrieval, repository guidance |
| Model chooses unsafe or incoherent next step | loop policy, graph transition, deterministic guard |
| Tool arguments are ambiguous | tool schema, validation, preview, authorization |
| Duplicate or unknown external action | effect journal, idempotency, reconciliation |
| Human approves without understanding | approval UX, evidence, consequence display |
| Same semantic error recurs | eval fixture, prompt/skill, domain model, tool affordance |
| System succeeds but creates heavy review work | product workflow, automation boundary, quality threshold |
| Metric improves while real outcome worsens | metric contract, countermetric, causal design |
| Failure appears only under live dependencies | resilience design, capacity, timeouts, degradation, runbook |

Do not default every failure to prompt editing. The highest-leverage correction often belongs in product design, tool affordances, deterministic constraints, state, data, repository structure, test infrastructure, or permissions.

### 25.9 Decision and change ledger

Maintain a ledger with:

- observation and source evidence;
- affected population and envelope;
- severity and confidence;
- mechanism hypothesis and alternatives;
- chosen intervention and owner;
- regression/eval/monitor added;
- rollout and decision criteria;
- result and residual uncertainty;
- keep, revert, narrow, or revisit decision.

This ledger prevents anecdote-driven oscillation and allows Codex to discover what the team has already learned.

---

## 26. Instrumentation that supports product learning

Observability and product analytics overlap but are not interchangeable.

- **Operational observability** asks why the system is behaving this way now.
- **Product analytics** asks how users and workflows engage with the product.
- **Evaluation evidence** asks whether behavior satisfies a defined quality contract.
- **Experiment telemetry** asks whether exposure to a change caused a meaningful difference.
- **Safety monitoring** asks whether harms, near misses, policy breaches, or uncontained effects are occurring.

A field-learning system needs all five, joined where appropriate.

### 26.1 Design signals from decisions backward

Do not start with “What can we log?” Start with:

1. Which decisions must be made?
2. Which failure mechanisms could make those decisions wrong?
3. Which observable facts distinguish those mechanisms?
4. Which identities and versions are needed to join the evidence?
5. What is the minimum data required?
6. What retention, access, privacy, and deletion controls apply?
7. How will telemetry quality itself be tested?

This produces decision-grade evidence rather than an expensive lake of events.

### 26.2 A minimum field-observation schema

A field observation should support, directly or by reference:

```text
Observation
├── identity
│   ├── observation_id
│   ├── occurred_at / recorded_at
│   └── source and evidence strength
├── envelope
│   ├── envelope_version
│   ├── autonomy_level
│   ├── consequence_tier
│   └── eligibility / assignment / exposure
├── system
│   ├── product, model, prompt/policy, harness, graph, tool versions
│   └── environment and dependency versions
├── task
│   ├── task_id, class, intended outcome
│   └── representative-sample stratum
├── trajectory
│   ├── run/action/tool transitions
│   ├── budgets, latency, errors, recovery
│   └── evidence and trace links
├── effects
│   ├── effect_id, type, target, authorization
│   └── prepared/dispatched/confirmed/ambiguous/reconciled/compensated
├── outcome
│   ├── outcome class and quality dimensions
│   ├── delayed outcome link
│   └── severe failure / near miss
├── human work
│   ├── intervention, override, correction, approval, abandonment
│   ├── time/effort and reason
│   └── user-reported confidence or qualitative note
└── governance
    ├── privacy class, retention and access
    ├── incident / decision / experiment links
    └── redaction status
```

### 26.3 Outcome labels are not enough

A binary success label hides important distinctions:

- completed correctly without intervention;
- completed correctly after expected approval;
- completed correctly after unexpected correction;
- partially completed with useful artifact;
- abandoned because of product friction;
- technically successful but operationally harmful;
- failed safely before effect;
- failed with recoverable effect;
- failed with ambiguous or duplicate effect;
- succeeded on immediate metric but created downstream rework.

Use a typed outcome taxonomy and preserve the trajectory needed to explain it.

### 26.4 Human intervention as a first-class signal

Instrument:

- when intervention occurred;
- whether it was invited or emergency;
- what the human saw at that moment;
- intervention type;
- reason category and free-text evidence where permitted;
- time and cognitive burden;
- whether the intervention improved the outcome;
- whether the same condition was detectable automatically;
- whether the intervention should remain a deliberate decision right.

Low intervention is not automatically good. It can mean safe automation, silent failure, user disengagement, or overreliance. High intervention can mean poor quality or appropriately placed oversight.

### 26.5 Privacy, security, and minimization

Agent telemetry is unusually likely to contain source code, credentials, personal information, proprietary documents, tool results, or sensitive decisions. OpenTelemetry’s security guidance places responsibility for minimization, consent, redaction, protection, and review on the implementer [R121].

Use these defaults:

- do not record raw prompts, completions, files, or tool payloads by default;
- record structured classifications, hashes, references, lengths, and derived quality signals where sufficient;
- maintain explicit allowlists for span attributes and metric labels;
- pseudonymize stable user/account identifiers when identity is needed;
- separate operational telemetry from restricted research content;
- enforce retention by evidence purpose;
- support deletion or legal holds where required;
- review third-party instrumentation, not only application code;
- treat telemetry export as a privileged data path;
- keep authorization secrets out of traces and logs;
- record redaction/version policy so historical evidence is interpretable.

### 26.6 Cardinality and cost

Unbounded task IDs, file paths, prompts, user IDs, URLs, error strings, and tool arguments can overwhelm metrics backends and leak data. Put high-cardinality values in traces or controlled evidence stores, not metric labels. Metrics should use bounded dimensions such as task class, consequence tier, autonomy stage, outcome class, error class, tool family, and system version.

### 26.7 Sampling

Uniform random sampling can discard the observations most needed for learning. Use layered retention:

1. retain all security incidents, severe failures, ambiguous effects, unauthorized actions, and emergency interventions;
2. retain all first occurrences of a novel failure signature;
3. retain a representative stratified sample of routine successes;
4. retain targeted samples for under-covered operating-envelope strata;
5. use tail or latency sampling for performance problems;
6. document sampling probability so estimates can be interpreted.

### 26.8 Telemetry verification

Test the evidence system:

- schema and version validation;
- missing join detection;
- assignment/exposure consistency;
- clock and ordering behavior;
- duplicate event handling;
- retry and reconnect behavior;
- process shutdown and exporter flush;
- redaction and allowlist enforcement;
- high-cardinality rejection;
- privacy classification;
- representative sampling;
- alert freshness and ownership;
- reconstruction of a known scenario from emitted evidence.

Instrumentation that cannot be trusted should block promotion, just as broken tests would.

---

## 27. Evidence hierarchy and decision discipline

Evidence quality is multidimensional. The following ladder is not a universal ranking, but a useful prompt for what each method can establish.

| Evidence form | Strengths | Main limits | Appropriate use |
|---|---|---|---|
| Expert judgment | fast, contextual, useful under sparse evidence | bias, confidence without calibration | frame risk and hypotheses |
| Anecdote/support report | reveals real pain and unexpected behavior | unknown denominator, selection bias | identify cases to investigate |
| Structured trace review | mechanism and trajectory detail | labor-intensive, sampled | diagnose behavior and create evals |
| Usability/qualitative study | mental model, workflow, reliance, language | small samples, facilitator effects | product and interaction decisions |
| Offline representative eval | repeatable, fast, regression-friendly | distribution and workflow gap | preflight and change detection |
| Shadow/silent prospective study | live data/integration/workflow evidence without effects | no actual user reliance or downstream effect | concept and readiness validation |
| Approval-gated field use | real usefulness and effect proposals under oversight | human mediation changes behavior | early consequential use |
| Observational cohort | broad naturalistic evidence, rare-event discovery | confounding and selection | monitoring and hypothesis generation |
| Randomized controlled experiment | strong causal attribution under valid design | cost, ethics, interference, metric limits | product-effect decisions |
| Progressive rollout/canary | limits blast radius and tests operational health | comparison may be biased unless designed | release safety and live verification |
| Longitudinal holdout | durability and cumulative effect | identity, contamination, ethics, opportunity cost | long-term product effect |
| Incident/near-miss analysis | high-value systemic learning | outcome-dependent selection | controls, resilience, regression |

The discipline is to match the claim to the method. Examples:

- A shadow trial can support “the integration receives the needed data with acceptable latency.”
- It cannot support “users will make better decisions with the recommendation.”
- An observational increase in adoption can support “use changed after launch.”
- It cannot establish “the feature caused better outcomes” without a defensible comparison.
- A randomized experiment can support a causal effect on measured outcomes.
- It cannot establish safety for unmeasured rare harms or populations excluded from the experiment.

### 27.1 Triangulation

Use complementary methods when the decision has multiple dimensions:

```text
quantitative outcome evidence
+ trajectory and effect evidence
+ qualitative workflow evidence
+ safety and reliability evidence
= stronger decision case
```

Microsoft’s experimentation guidance explicitly supports combining qualitative and quantitative methods, and its GenAI product experience emphasizes continuous improvement across offline and online evidence rather than one metric [R79][R82].

### 27.2 Precommitment

Before exposure, record:

- decision and owner;
- hypothesis and mechanism;
- population and unit;
- primary outcome;
- diagnostic and guardrail metrics;
- minimum effect or threshold that matters;
- analysis and exclusion rules;
- sample/exposure and bake-time logic;
- stop and rollback rules;
- multiple-testing or sequential-testing method;
- expected novelty, learning, interference, and carryover risks;
- qualitative review plan;
- what result causes advance, hold, narrow, pivot, revert, or stop.

Precommitment reduces the ability to reinterpret noise as success after seeing the data.

### 27.3 Metrics are models, not reality

A metric encodes assumptions about value and measurement. Require a metric contract with:

- decision purpose;
- construct being represented;
- event definition and source;
- numerator, denominator, aggregation, and attribution;
- unit and population;
- eligible/excluded cases;
- direction and practical significance;
- expected latency and observation window;
- data-quality checks;
- known gaming paths;
- countermetrics and guardrails;
- owner and retirement condition.

Avoid one composite “agent quality” score that lets frequent low-risk successes hide rare catastrophic failures.

---

## 28. Continuous experimentation for agentic products

Agentic products complicate experimentation because outputs are stochastic, trajectories vary, users adapt, tool effects may be irreversible, and model/provider versions may change during the study.

### 28.1 Experiment object

A product experiment should version:

- product behavior;
- model and inference configuration;
- prompts/policies/skills;
- harness, graph, tools, and permissions;
- data and retrieval policy;
- operating envelope;
- assignment logic;
- exposure logging;
- evaluation and metric contracts.

Otherwise the “treatment” is not stable enough to interpret.

### 28.2 Unit and interference

Choose the unit that contains likely spillover. User-level assignment may fail when:

- teammates share agent outputs;
- repositories receive changes from multiple variants;
- one agent changes shared tools or memory;
- organizational processes adapt;
- a deployment affects all users;
- model caches or shared state cross variants.

Use account, repository, team, cluster, or time-block assignment where needed, and record contamination.

### 28.3 Outcome, diagnostic, guardrail, and data-quality measures

A balanced experiment includes:

- **outcome:** real product value, such as successful task completion, lead time to accepted artifact, defect-free change, or incident resolution;
- **diagnostic:** mechanism, such as relevant tool selection or context retrieval quality;
- **guardrail:** unacceptable degradation, such as severe failure, duplicate effect, review burden, security event, latency, cost, or accessibility failure;
- **data quality:** sample ratio, exposure completeness, missing joins, instrumentation version, and delayed-outcome completeness.

### 28.4 Sequential decisions and peeking

Repeatedly checking conventional p-values and stopping when a result becomes favorable inflates false-positive risk. Use a predeclared sequential method, fixed horizon, or decision framework appropriate to the context. Operational safety alerts are separate: a severe guardrail breach may trigger immediate stop regardless of statistical power.

### 28.5 Multiple metrics and segments

Agent products generate many possible metrics and slices. Predeclare primary outcomes and high-priority segments. Treat exploratory segment findings as hypotheses requiring confirmation unless the analysis plan supports them. Always inspect safety-relevant segments even when not powered for product uplift.

### 28.6 Novelty, learning, and adaptation

Users learn how to prompt, review, and route work. The agent may also adapt through memory or updated tools. Early uplift can reflect novelty; early harm can reflect onboarding. Measure:

- first-use versus mature-use behavior;
- user learning and prompt burden;
- product configuration changes;
- model or policy drift;
- support and training effects;
- delayed downstream quality.

Long-term experiments have additional identity, selection, survivorship, and trend pitfalls [R81].

### 28.7 Progressive rollout versus causal experiment

They can be combined but answer different questions.

- A **progressive rollout** controls operational risk.
- A **randomized experiment** estimates causal product impact.

A canary with handpicked expert users may be safe and informative but causally biased. A randomized experiment at broad exposure may estimate effect but create unacceptable risk without staged rollout. Design both explicitly [R107][R112].

### 28.8 Decision outcomes

Do not force every experiment into “ship” or “do not ship.” Use:

- advance exposure;
- hold and gather more evidence;
- narrow to a successful envelope;
- pivot the mechanism;
- improve instrumentation;
- revert;
- stop the product direction;
- retain as a human-assist tool rather than autonomous capability;
- move a behavior into deterministic tooling;
- preserve a control or approval because it is doing useful work.

---

## 29. Product discovery and concept validation for agentic systems

Agentic product discovery must study the work system, not only the desired feature.

### 29.1 Discover the work

Document:

- actors, goals, incentives, expertise, and decision rights;
- current workflow and handoffs;
- artifacts, systems of record, and informal workarounds;
- frequency, duration, variability, and interruptions;
- consequences of delay, error, omission, and unauthorized action;
- data and access constraints;
- current verification and recovery practices;
- where judgment is semantic versus deterministic;
- where users need control, explanation, preview, or reversibility;
- value of partial results;
- support and maintenance burden.

GOV.UK discovery guidance emphasizes understanding the problem, users, constraints, and whether to proceed before committing to build [R90]. HAX and PAIR add human-AI-specific concerns such as expectation setting, correction, control, uncertainty, mental models, and graceful failure [R93][R94].

### 29.2 Separate opportunity from solution

An opportunity statement describes a costly or risky condition in the current work. It should not smuggle in the chosen architecture.

Weak:

> Users need a multi-agent graph to automate incident response.

Stronger:

> On-call engineers lose time reconstructing cross-service context and coordinating reversible diagnostic actions during high-severity incidents; delayed context and ambiguous ownership increase time to mitigation.

The second statement can be tested with workflow evidence and admits multiple interventions.

### 29.3 Concept evidence

A concept can be tested with progressively more realistic artifacts:

- storyboard or workflow simulation;
- concierge/manual service;
- prompt and tool spike;
- read-only integration;
- historical replay;
- Wizard-of-Oz interaction;
- shadow system;
- recommendation-only thin slice;
- approval-gated end-to-end slice.

Choose the cheapest artifact that exposes the highest-risk assumption. Do not build a production graph to learn that users do not trust the result format.

### 29.4 Feasibility dimensions

Feasibility is not only “the model can do it.” Evaluate:

- task and model capability;
- data availability, rights, freshness, and quality;
- tool and integration behavior;
- latency and cost envelope;
- deterministic verification or human review;
- effect safety and reversibility;
- security, privacy, policy, and compliance;
- observability and supportability;
- operational ownership and incident response;
- economic sustainability;
- adaptability when models, tools, or regulations change.

### 29.5 Go, pivot, or stop

A concept evidence case should end with a decision, not a demo. State:

- evidence that supports the opportunity;
- evidence that contradicts it;
- unresolved assumptions;
- successful and failed envelope strata;
- implementation and operating cost;
- risk and control burden;
- recommended next exposure stage;
- explicit stop or pivot conditions.

Stopping a weak direction before deep implementation is a successful product outcome.

---

## 30. Requirements and systems engineering for agentic products

Requirements translate representative needs and constraints into verifiable product and system commitments.

### 30.1 Operational concept

An operational concept describes how the future system participates in real work:

- actors and responsibilities;
- mission or product outcomes;
- initiating and terminating conditions;
- normal, degraded, emergency, and recovery modes;
- human-agent interaction and decision rights;
- external systems and interfaces;
- information and effect flows;
- security and privacy boundaries;
- support, maintenance, and retirement assumptions.

This prevents requirements from becoming a list of UI features detached from operation [R84][R85].

### 30.2 Mission threads

A mission thread is an end-to-end scenario across actors and systems. Include:

1. trigger and preconditions;
2. task and consequence class;
3. information sources;
4. agent and human decisions;
5. tool and effect sequence;
6. verification and approval;
7. outcome and evidence;
8. degraded and failure branches;
9. recovery and reconciliation;
10. observability and support.

Mission threads reveal missing interfaces, ownership, state, and recovery requirements.

### 30.3 Requirement types

Use distinct types:

- stakeholder need;
- product outcome requirement;
- functional requirement;
- quality-attribute requirement;
- interface contract;
- data requirement;
- model/tool constraint;
- security/privacy requirement;
- operational and support requirement;
- verification requirement;
- transition, migration, and retirement requirement.

### 30.4 Quality-attribute scenarios

Turn “fast,” “reliable,” “secure,” “usable,” and “maintainable” into scenarios with source, stimulus, environment, artifact, response, and response measure [R88]. Example:

> During a provider timeout after an effect may have been dispatched, the effect gateway records the action as ambiguous, prevents automatic redispatch, alerts the owner within two minutes, and reconciles the outcome within the defined recovery objective.

This is architecture- and test-relevant. “Handle timeouts gracefully” is not.

### 30.5 Traceability

Maintain bidirectional links among:

```text
stakeholder need
↔ operational concept / mission thread
↔ requirement and quality-attribute scenario
↔ architecture decision and control
↔ implementation unit
↔ verification/eval/experiment
↔ release and operating evidence
↔ field observation / incident / change decision
```

Traceability should support impact analysis, not paperwork theater. Automate links where possible, but review semantic correctness.

### 30.6 Baseline and change control

Agentic systems change when models, prompts, policies, tools, data, dependencies, or permissions change—even if application code does not. Treat these as configuration-controlled system elements. Define what constitutes:

- editorial change;
- behaviorally relevant change;
- security-relevant change;
- operating-envelope change;
- experiment-treatment change;
- revalidation or reauthorization trigger.

---

## 31. Architecture and evidence-driven delivery planning

Architecture should be selected to resolve quality and risk requirements, not to demonstrate technical sophistication.

### 31.1 Architecture tradeoff analysis

For each candidate architecture:

- map quality-attribute scenarios;
- identify sensitivity points;
- identify tradeoff points;
- state assumptions and evidence;
- identify failure modes and blast radius;
- identify operational and migration cost;
- identify reversibility;
- record risks, non-risks, and unknowns.

ATAM-style analysis is useful because it makes tradeoffs and assumptions explicit before they become expensive [R89].

### 31.2 Evidence-driven thin slices

A thin slice is the smallest end-to-end implementation that resolves important uncertainty. It should traverse real boundaries: context, model, tool, state, effect, verification, telemetry, and user interaction where relevant.

Prioritize slices by:

```text
learning value × consequence × uncertainty × architectural leverage
──────────────────────────────────────────────────────────────────
implementation cost × exposure risk × irreversibility
```

A thin slice is not merely a reduced feature list. It is an evidence instrument.

### 31.3 Walking skeleton

Build a minimal deployable path with:

- repository and CI structure;
- versioned configuration;
- one representative mission thread;
- identity and state model;
- one safe tool/effect path;
- observability and evidence joins;
- verification ladder;
- rollback or disable path;
- operator ownership.

This reveals integration and operational risk early.

### 31.4 Delivery plan as a decision network

Plan work around decisions and evidence, not only components. A delivery item should state:

- uncertainty or requirement addressed;
- exact artifact;
- dependencies and ownership;
- test/eval/field evidence;
- exposure stage;
- acceptance and stop conditions;
- decision unlocked.

### 31.5 Capacity and dependency planning

Agentic workloads can amplify downstream calls and create bursty, long-running, or recursive behavior. Plan:

- per-resource concurrency;
- queue and backpressure policy;
- token/model/tool budgets;
- dependency quotas and rate limits;
- latency and timeout allocation;
- cancellation and abandonment;
- degraded modes;
- cost attribution;
- capacity tests at representative trajectories, not only requests per second.

---

## 32. Software construction and quality engineering

Agent-mediated construction should increase evidence density, not merely code volume.

### 32.1 Small batches and fast feedback

Prefer small coherent changes that can be independently reviewed, tested, reverted, and attributed. Codex should:

- state the contract before implementation;
- inspect existing architecture and constraints;
- change the smallest relevant surface;
- add or update tests and evidence with the code;
- run the fast verification ladder frequently;
- run exact delivery verification before handoff;
- record residual uncertainty honestly.

### 32.2 Verification ladder

A general ladder:

1. formatting and static checks;
2. schema and contract validation;
3. unit and property tests;
4. integration and adapter tests;
5. graph/loop/state-machine tests;
6. tool authorization and effect tests;
7. security and misuse tests;
8. performance, saturation, timeout, and cancellation tests;
9. fault, crash, resume, and reconciliation tests;
10. offline agent outcome/trajectory evals;
11. exact packaged-artifact verification;
12. controlled field evidence.

Passing a lower rung does not imply a higher rung passed.

### 32.3 Review roles

Use review modes deliberately:

- semantic/product review;
- architecture and systems review;
- security/privacy review;
- code and test review;
- operational readiness review;
- fresh-context review by an agent or human not immersed in the implementation history.

Fresh-context review is valuable because long sessions normalize assumptions and local workarounds.

### 32.4 Defect learning

For material defects:

- classify escape stage and detection gap;
- identify enabling system conditions;
- add the narrow regression;
- decide whether the durable fix belongs in code, schema, tool, harness, eval, repository guidance, review policy, observability, or lifecycle gate;
- verify the corrective action in the exact delivery path.

### 32.5 Artifact integrity

Verify what users receive, not only source files. Depending on product:

- build from a clean environment;
- validate package contents and paths;
- test checksums and signatures;
- run migrations and rollback;
- test startup/shutdown;
- inspect generated assets;
- verify configuration defaults;
- scan secrets and provenance;
- test the install or deployment procedure from the packaged artifact.

---

## 33. Secure development, release engineering, and progressive delivery

Security belongs throughout the lifecycle. NIST SSDF, its AI profile, SLSA, CISA guidance, and OWASP agent guidance converge on integrating secure design, protected development/build processes, provenance, risk analysis, verification, and vulnerability response rather than treating security as a final scan [R95][R97][R98][R100][R124][R125].

### 33.1 Threat model the whole agentic system

Include:

- users, operators, developers, model/provider, tools, external services, other agents, and adversaries;
- prompts, retrieved content, memory, repository instructions, tool output, model output, and telemetry as distinct trust domains;
- credentials, tokens, models, prompts, data, code, artifacts, decisions, effects, and evidence as assets;
- goal manipulation, prompt injection, memory poisoning, confused deputy, excessive agency, tool abuse, insecure output handling, supply-chain compromise, denial of service, and cascading failures;
- control-plane and execution-plane boundaries;
- authorization independent of model intent;
- containment, detection, response, and recovery.

### 33.2 Secure by default

Examples:

- no ambient production credentials;
- read-only or sandboxed tools by default;
- least-privilege, task-scoped capabilities;
- allowlisted network and tool destinations;
- schema and semantic validation;
- exact-effect preview and authorization;
- idempotency and reconciliation;
- sensitive-data minimization;
- safe failure and bounded retries;
- disabled or narrow experimental autonomy by default.

### 33.3 Supply-chain evidence

A release package may include:

- source revision;
- dependency lockfiles;
- SBOM or equivalent component inventory;
- vulnerability and license policy results;
- build provenance;
- builder and environment identity;
- test/eval evidence;
- artifact hashes/signatures;
- deployment manifest;
- model, prompt, policy, tool, and data configuration versions.

SLSA and CycloneDX provide standards-based mechanisms for provenance and component representation [R98][R99].

### 33.4 Progressive delivery contract

Before rollout define:

- target cohorts and exclusion rules;
- deployment rings or percentages;
- assignment/exposure instrumentation;
- minimum sample and bake time;
- operational, product, safety, security, and human-work guardrails;
- comparison baseline;
- severe-event immediate stop rules;
- advance, hold, narrow, and revert authority;
- rollback method and tested recovery objective;
- post-rollback reconciliation;
- communication and incident paths.

Canary controllers and feature flags implement exposure; they do not decide that exposure is safe or authorized [R107][R112][R113][R114][R115].

---

## 34. Production readiness and SRE for agentic products

A product is not production-ready because it passed functional tests. Production readiness is a multidisciplinary evidence case.

### 34.1 Production readiness review

Review:

- service purpose, users, consequence tiers, and ownership;
- architecture, dependencies, quotas, and capacity;
- state, durability, effect safety, and data lifecycle;
- security, privacy, credentials, and abuse controls;
- SLIs, SLOs, error budget, dashboards, and alerts;
- logs/traces/metrics and evidence joins;
- timeout, retry, backpressure, cancellation, and degradation;
- deployment, rollback, configuration, and feature exposure;
- incident roles, runbooks, support, and escalation;
- backup, restore, reconciliation, and disaster recovery;
- cost and resource controls;
- field-learning and change-management process;
- known risks, exceptions, and expiration dates.

Google’s production-readiness and launch practices make this evidence explicit before operational handoff [R102][R106].

### 34.2 SLIs and SLOs for agents

Useful SLIs can include:

- end-to-end task outcome within a time bound;
- confirmed effect without duplicate or ambiguity;
- severe failure rate;
- safe-stop or recovery success;
- approval latency and burden;
- trace/evidence completeness;
- model/tool dependency availability;
- queue wait, run latency, and cost;
- stale-context or stale-state rate;
- policy-denied action rate;
- human correction or abandonment for specified task classes.

Separate service reliability from semantic quality. A system can be available and wrong, or semantically useful but operationally unreliable.

### 34.3 Error-budget policy

Define what happens when reliability falls outside the accepted envelope:

- freeze exposure expansion;
- reduce autonomy or effect budget;
- pause experiments;
- prioritize reliability work;
- narrow task classes;
- disable failing tools/providers;
- require incident review;
- reset only after defined recovery evidence.

Error budgets are decision mechanisms, not dashboard decoration [R103].

### 34.4 Incident learning

An incident record should connect:

- impact and affected envelope;
- timeline and detection;
- system versions and recent changes;
- decision/effect path;
- contributing conditions;
- response, containment, and recovery;
- human and automation behavior;
- why controls did or did not work;
- corrective actions by layer;
- regression/eval/monitor additions;
- owner, due date, and effectiveness review.

Use blameless analysis to improve conditions and controls while preserving accountability for owned actions [R104][R105].

### 34.5 Toil and support burden

Measure manual review, exception handling, reconciliation, support tickets, prompt repair, access provisioning, telemetry repair, and incident work. An agent that saves user time but creates unsustainable operator toil is not a mature product.

---

## 35. Maintenance, evolution, deprecation, and retirement

Agentic products have unusually dynamic dependencies: models, providers, prompts, retrieval corpora, tools, protocols, permissions, feature flags, and evaluation datasets. Maintenance must monitor both software and behavioral drift.

### 35.1 Change taxonomy

Classify changes:

- implementation-only with no intended behavior change;
- dependency or runtime change;
- prompt, skill, policy, or context change;
- model/provider/configuration change;
- tool schema or permission change;
- data source or retrieval change;
- operating-envelope expansion;
- metric/eval/grader change;
- security or privacy control change;
- lifecycle status change.

Map each class to required tests, evals, reviews, rollout, and reauthorization.

### 35.2 Maintenance evidence

Track:

- incidents and near misses;
- regression and field-eval trends;
- distribution and data drift;
- dependency and model changes;
- SLO and error-budget history;
- security advisories and exceptions;
- human correction and support burden;
- telemetry quality;
- cost and capacity;
- aging decisions and expiring waivers;
- product value by operating-envelope segment.

### 35.3 Deprecation

A deprecation plan defines:

- deprecated capability and rationale;
- affected users, tasks, APIs, data, and dependencies;
- replacement or alternative;
- communication and support timeline;
- migration tooling and evidence;
- compatibility and rollback period;
- telemetry to measure migration;
- final disable criteria;
- owner and escalation.

### 35.4 Retirement

Retirement is not deleting a deployment. It includes:

- confirming product and legal authority;
- inventorying services, agents, models, data, credentials, queues, schedules, flags, integrations, dashboards, alerts, documentation, and support channels;
- migrating users and critical workflows;
- revoking credentials and permissions;
- draining and reconciling in-flight effects;
- retaining or deleting data according to policy;
- preserving required evidence and decision records;
- removing routing, DNS, dependencies, and spend;
- testing that no critical journey still depends on the service;
- monitoring after disable;
- recording closure and lessons.

GOV.UK retirement guidance and systems lifecycle standards support treating retirement as a planned phase with user, data, dependency, and continuity concerns [R84][R92].

---

## 36. The full-lifecycle assurance model

The plugin represents the lifecycle as ten decision domains with continuous feedback, not a one-way sequence.

```text
Discover
  ↔ Validate concept and feasibility
  ↔ Specify needs, requirements, and mission threads
  ↔ Architect and plan evidence-driven slices
  ↔ Construct and verify
  ↔ Secure and release progressively
  ↔ Operate with SRE controls
  ↔ Experiment and learn from authentic use
  ↔ Maintain and evolve
  ↔ Deprecate and retire
```

Field evidence can send work back to any earlier domain. An intervention pattern may reveal a discovery problem; a near miss may change requirements; a canary failure may change architecture; a support burden may narrow the operating envelope; a weak long-term effect may retire the feature.

### 36.1 Lifecycle stage contracts

| Domain | Primary decision | Minimum artifact | Evidence to proceed |
|---|---|---|---|
| Discovery | Is the problem important, representative, and worth addressing? | Product Discovery Evidence Brief | user/work evidence, constraints, opportunity and alternatives |
| Concept/feasibility | Can a useful, safe, operable intervention exist? | Concept and Feasibility Evidence Case | critical-assumption tests, thin prototype/spike, go/pivot/stop criteria |
| Requirements/systems | What must the product and system do under which conditions? | Operational Concept and Traceability Baseline | mission threads, requirements, quality scenarios, verification links |
| Architecture/planning | Which structure and slices best address risk and quality? | Architecture and Evidence-Driven Delivery Plan | tradeoff analysis, risk retirement, dependency/capacity plan |
| Construction/quality | Does the implementation satisfy the contracts? | Construction and Quality Evidence Plan | layered tests/evals, review, artifact integrity, residual uncertainty |
| Secure release | Is the exact artifact safe and ready for controlled exposure? | Secure Release Evidence Package | threat/control evidence, provenance, rollout and rollback proof |
| Production/SRE | Can the product be operated, detected, recovered, and supported? | Production Readiness and Reliability Plan | SLOs, capacity, observability, incident/recovery evidence, ownership |
| Experimentation | Did the product cause useful outcomes without unacceptable harm? | Product Experiment and Decision Contract | valid assignment/exposure, outcomes, guardrails, causal/qualitative analysis |
| Maintenance | Should the system change, narrow, sustain, or deprecate? | Maintenance, Deprecation, and Retirement Plan | health, value, incidents, dependencies, burden, change evidence |
| Retirement | Can value and obligations be preserved while removing the system? | Retirement closure record | migration, reconciliation, revocation, data/evidence handling, post-close checks |

### 36.2 Assurance case

An assurance case is a structured argument that claims are supported by evidence under stated assumptions. For an agentic product:

- **Claim:** The product is fit for a defined operating envelope and exposure stage.
- **Subclaims:** It is useful, usable, semantically adequate, reliable, secure, privacy-preserving, controllable, recoverable, supportable, and economically sustainable.
- **Evidence:** Requirements, tests, evals, field observations, experiments, incidents, reviews, provenance, SLOs, and human-work evidence.
- **Assumptions:** Population, workload, models, tools, environment, permissions, dependencies, and change rate.
- **Defeaters:** Evidence that could invalidate the claim, such as severe failure, drift, broken instrumentation, changed model, or expansion outside the envelope.

The assurance case evolves; it is not a permanent certification.

### 36.3 Readiness is claim-specific

Avoid a single “ready” state. A product may be:

- ready for internal shadow use;
- ready for recommendation-only use by trained experts;
- ready for bounded autonomous effects on reversible low-risk tasks;
- not ready for high-consequence tasks or broad populations.

Readiness should always name the envelope and authority level.

---

## 37. Agent-mediated lifecycle operating model

An agent can accelerate analysis, artifact production, verification, and evidence synthesis, but decision rights must remain explicit.

### 37.1 Appropriate agent responsibilities

Codex can:

- synthesize research and repository evidence;
- draft interview guides, assumption maps, operational concepts, requirements, mission threads, quality scenarios, ADRs, test plans, runbooks, and experiment contracts;
- inspect code, traces, incidents, support reports, and telemetry schemas;
- generate thin slices, adapters, tests, eval fixtures, instrumentation, dashboards-as-code, rollout configuration, and migration tooling;
- validate traceability, schema, links, package contents, and evidence coverage;
- cluster field failures and propose mechanism hypotheses;
- compare decisions against stated constraints;
- identify missing evidence and contradictions;
- perform fresh-context review.

### 37.2 Human decision rights

Humans should retain ownership of:

- product values and whose outcomes matter;
- research consent and ethical boundaries;
- risk acceptance and legal/policy interpretation;
- irreversible commitments;
- operating-envelope expansion;
- autonomy promotion for consequential effects;
- interpretation of ambiguous stakeholder evidence;
- staffing, budget, and organizational commitments;
- launch, incident, deprecation, and retirement accountability.

The agent can prepare evidence and recommendations; it should not manufacture authority.

### 37.3 Agent evidence discipline

When using Codex across the lifecycle, require it to label:

- observed fact;
- source and version;
- inference;
- assumption;
- recommendation;
- uncertainty;
- missing evidence;
- decision owner;
- revisit trigger.

This prevents fluent synthesis from erasing epistemic boundaries.

### 37.4 Artifact-centered collaboration

Store durable artifacts in the repository or product system:

- discovery evidence;
- assumption/risk map;
- operational concept and mission threads;
- requirements and traceability;
- architecture decisions;
- test/eval/experiment contracts;
- field-learning ledger;
- release and readiness evidence;
- incident and change records;
- maintenance and retirement plans.

The conversation is a working medium, not the system of record.

---

## 38. Rust agent observability and field-learning implementation

Rust is well suited to making agentic state and evidence explicit through types, but observability still requires intentional architecture.

### 38.1 Domain identities

Define newtypes for durable identities:

```rust
RunId
TaskId
ActionId
EffectId
ObservationId
ExperimentId
AssignmentId
ExposureId
EnvelopeVersion
ModelConfigVersion
HarnessVersion
ToolContractVersion
```

Do not use a trace ID as the only business or effect identity. Traces can be sampled, split, restarted, or absent; durable effects require stable application identities [R123].

### 38.2 `tracing` spans and events

Use spans for owned operations with duration and nested context:

- product request or task;
- agent run;
- loop iteration or graph node;
- tool invocation;
- approval wait;
- external effect;
- recovery/reconciliation;
- experiment exposure.

Use events for facts inside those operations:

- decision made;
- validation failed;
- retry classified;
- budget crossed;
- intervention received;
- effect confirmed or ambiguous;
- guardrail breached.

The `tracing` ecosystem is designed for structured contextual diagnostics in async Rust [R118].

### 38.3 OpenTelemetry boundary

Use OpenTelemetry for vendor-neutral export and cross-service propagation [R119][R120]. Keep domain evidence types independent of OTel so:

- storage and backend can change;
- semantic contracts are reviewed rather than inherited accidentally;
- high-value evidence can be retained even when trace sampling drops spans;
- operational traces remain separable from governed field-research records.

### 38.4 Async context propagation

Common failure: spawning a Tokio task without preserving the relevant tracing span or durable ownership. Require:

- named/owned task handles;
- explicit span instrumentation on spawned futures;
- cancellation propagation;
- deadline and budget propagation;
- stable run/action IDs in task state;
- shutdown flush and timeout behavior;
- tests that reconstruct context across spawned tasks, channels, and adapters.

### 38.5 Metrics

Use bounded labels:

```text
task_class
consequence_tier
autonomy_level
outcome_class
effect_state
error_class
tool_family
model_config_version
harness_version
rollout_stage
```

Do not use prompts, file paths, arbitrary tool names, user IDs, URLs, or raw error messages as metric labels.

### 38.6 Feature and rollout context

OpenFeature provides a vendor-neutral evaluation context and Rust SDK [R115][R117]. In Rust:

- use an adapter owned by the application;
- pass stable pseudonymous targeting keys only when required;
- record flag key, variant, reason, provider, and error code;
- distinguish eligibility, assignment, evaluation, and actual exposure;
- include experiment/rollout IDs in field observations;
- never use feature-flag evaluation as authorization for a privileged effect.

### 38.7 Privacy and sampling policy as code

Encode:

- prohibited field classes;
- allowlisted metric labels;
- redaction rules;
- maximum attribute lengths;
- retention class;
- deterministic representative sampling;
- priority retention for severe failure, near miss, ambiguous effect, security event, and human intervention;
- schema and policy versions.

The plugin’s `telemetry_policy.rs` and `field_observation.rs` are adaptable reference fragments, not a framework dependency.

### 38.8 Verification

Test Rust observability with:

- in-memory subscriber/exporter assertions;
- span-parent and W3C propagation cases;
- async spawn/channel context cases;
- cancellation and graceful-shutdown flush;
- redaction and prohibited-field property tests;
- cardinality-budget tests;
- deterministic sampling tests;
- high-priority retention tests;
- duplicate and ordering behavior;
- trace-to-observation join completeness;
- rollout-gate state-machine tests;
- crash/restart behavior for durable observation and effect records.

OpenTelemetry’s GenAI semantic conventions are useful but evolving; adopt stable fields selectively and version product-specific fields [R122].

---

## 39. Prompt vocabulary and output contracts for Codex

The following phrases convert intuition into actionable requests.

### 39.1 Ask for authentic-use engineering

> Use `$authentic-use-engineering` to design the smallest safe controlled field-learning program for this product. Define the representative workload, operating envelope, autonomy/exposure ladder, decision rights, instrumentation and evidence joins, severe-event stop rules, review cadence, and observation-to-product/eval/tool/policy change loop. Distinguish what offline, shadow, recommendation-only, approval-gated, and bounded-autonomy evidence can establish.

### 39.2 Ask for a product discovery evidence brief

> Use `$agent-product-discovery` to study the work system rather than assume the solution. Produce a Product Discovery Evidence Brief with actors, current workflow, consequential decisions, artifacts and systems of record, failure/recovery paths, human work, representative research sample, opportunity statements, alternatives, assumptions, and evidence-based go/stop questions.

### 39.3 Ask for concept and feasibility validation

> Use `$concept-feasibility-validation` to identify the highest-consequence, highest-uncertainty assumptions and choose the cheapest discriminating artifact for each. Include shadow, concierge, replay, spike, or approval-gated thin-slice options; define evidence strength, feasibility dimensions, operating-envelope limits, and go/pivot/stop criteria before deeper implementation.

### 39.4 Ask for systems requirements

> Use `$requirements-systems-engineering` to produce an Operational Concept and Traceability Baseline. Define actors and decision rights, normal/degraded/recovery modes, mission threads, functional and quality-attribute requirements, interfaces, data/effect constraints, verification methods, bidirectional traceability, configuration baseline, and material-change triggers.

### 39.5 Ask for evidence-driven architecture and planning

> Use `$architecture-delivery-planning` to compare the smallest viable architectures against quality-attribute scenarios. Record sensitivity and tradeoff points, assumptions, failure modes, reversibility, dependency/capacity needs, and rejected alternatives. Plan thin vertical slices by uncertainty retired and decision unlocked, not component count.

### 39.6 Ask for construction and verification

> Use `$software-construction-quality` to create a Construction and Quality Evidence Plan. Define small-batch ownership, verification ladder, property/state-machine/fault/eval cases, exact artifact checks, fresh-context review, defect-to-regression process, and an acceptance-to-evidence matrix. Do not claim skipped or unavailable checks passed.

### 39.7 Ask for secure release

> Use `$secure-delivery-release` to produce a Secure Release Evidence Package. Cover agent-specific threat boundaries, secure defaults, dependency/SBOM/provenance evidence, exact artifact identity, progressive rollout cohorts, assignment/exposure integrity, guardrails, bake time, authorization, rollback, reconciliation, and keep/hold/narrow/revert/stop rules.

### 39.8 Ask for production readiness

> Use `$production-readiness-sre` to run a production-readiness review. Define ownership, architecture and dependency risks, capacity and backpressure, SLIs/SLOs/error budget, alerts and runbooks, incident roles, recovery and reconciliation, degradation, rollback, telemetry quality, support/toil, known risks, and the exact operating envelope approved for launch.

### 39.9 Ask for product experimentation

> Use `$continuous-product-experimentation` to create a Product Experiment and Decision Contract. Predeclare hypothesis and mechanism, unit and population, treatment versions, assignment/exposure, primary outcome, diagnostic/counter/guardrail/data-quality metrics, sample and bake-time logic, SRM and contamination checks, qualitative review, novelty/carryover risks, and advance/hold/narrow/pivot/revert/stop decisions.

### 39.10 Ask for maintenance and retirement

> Use `$maintenance-retirement-engineering` to create a sustainment, deprecation, and retirement plan covering model/tool/dependency drift, SLO and field-evidence trends, security advisories, support burden, change classes and revalidation, migration, communication, credential/effect reconciliation, data handling, evidence retention, disable verification, and post-retirement monitoring.

### 39.11 Ask for Rust observability

> Use `$rust-agent-observability` to design a Rust Agent Observability Contract using typed domain IDs, `tracing` spans/events, OpenTelemetry propagation/export, bounded metrics, privacy/cardinality/sampling policy, feature exposure context, field-observation records, human intervention signals, effect-state evidence, shutdown flush, and propagation/redaction/sampling/join tests.

### 39.12 Ask for the full lifecycle

> Use `$agentic-product-lifecycle` as the orchestrator. Tailor the lifecycle to this product, identify current decision maturity, and produce a Lifecycle Assurance Plan spanning discovery, concept/feasibility, operational concept and requirements, architecture and thin-slice planning, construction and quality, secure release, production readiness/SRE, authentic-use learning and experimentation, maintenance, and retirement. For every domain state the decision, owner, artifact, evidence, readiness threshold, feedback path, and stop/revisit trigger.

---

## 40. Failure clinic for authentic-use and lifecycle work

| Symptom | Missing concept or control | Better request |
|---|---|---|
| “We dogfood it, but learn mostly from anecdotes.” | field observation schema and decision ledger | Require representative sampling, joinable evidence, mechanism hypotheses, and evidence-to-change records. |
| “The demo works; real tasks fail.” | ecological validity and representative workload | Stratify real tasks, environments, interruptions, dependencies, and consequence tiers. |
| “We collect many traces but cannot decide what to change.” | learning charter and decision-linked instrumentation | Start from decisions and failure mechanisms; specify the action each signal can inform. |
| “Users approve almost everything.” | calibrated reliance and approval quality | Measure review behavior, reasons, correction, outcome, and whether approvals expose exact consequences. |
| “Autonomy is either on or off.” | progressive autonomy and operating envelope | Define staged authority with promotion, narrowing, and stop evidence per task/effect class. |
| “Shadow mode performed well, so we automated.” | evidence-claim mismatch | State that shadow validates input/integration/counterfactual output, not human reliance or effect safety. |
| “Success rate improved after launch.” | causal evidence and metric contract | Define comparison, exposure, outcome, guardrails, data quality, and plausible confounding. |
| “The experiment is significant.” | practical significance and trustworthy analysis | Predeclare minimum useful effect, SRM checks, multiple testing, delayed outcomes, and guardrails. |
| “The average is good.” | tail, segment, and severe-event analysis | Preserve consequence-weighted failures and inspect envelope strata independently. |
| “Every field failure becomes a prompt tweak.” | intervention-layer diagnosis | Choose among product, context, tool, state, harness, policy, architecture, eval, and UX changes. |
| “We shipped a flag, so rollout is safe.” | exposure is not authorization | Add cohorts, guardrails, bake time, stop authority, rollback, effect budgets, and reconciliation. |
| “Functional tests pass, therefore production-ready.” | lifecycle assurance case | Require security, reliability, capacity, observability, support, field evidence, and exact artifact proof. |
| “The agent wrote requirements from the feature idea.” | operational concept and discovery evidence | Derive requirements from actors, mission threads, constraints, failures, and quality scenarios. |
| “Architecture was chosen before the risky assumptions were tested.” | evidence-driven thin slices | Run spikes and walking skeletons targeted at uncertainty and quality tradeoffs. |
| “Metrics are too expensive and noisy.” | cardinality and sampling policy | Bound labels, prioritize severe/novel cases, and retain representative successes. |
| “A timeout caused the action twice.” | ambiguous effect and reconciliation | Use stable action/effect IDs, effect journal, idempotency, and reconcile before redispatch. |
| “The model changed but the release record did not.” | configuration-controlled system identity | Version model, prompt/policy, harness, tools, data, envelope, and evals as treatment components. |
| “The product saves user time but consumes the operations team.” | total human work and toil | Measure framing, review, support, reconciliation, incident, and maintenance burden. |
| “The service is unused but cannot be shut down.” | retirement engineering | Inventory dependencies, migrate users, revoke access, reconcile effects, handle data, and verify disable. |
| “Codex produced a complete lifecycle plan with no evidence labels.” | epistemic discipline | Require facts, sources, inferences, assumptions, uncertainty, owners, and revisit triggers. |

---

## 41. Research-backed plugin expansion decisions

### From production traces to controlled field learning

The original plugin emphasized traces as evaluation and observability evidence. The expansion adds a complete field-learning control system because traces alone do not define representative exposure, authority, causal interpretation, human work, or how observations change the product [R71][R72][R75].

### From “dogfood early” to operating-envelope engineering

Informal internal use is replaced with explicit users, tasks, data, tools, models, effects, budgets, exclusions, monitoring, and stop rules. This preserves learning value while constraining extrapolation and risk [R73][R75][R76].

### From binary autonomy to progressive autonomy

The plugin now distinguishes observe-only, shadow, recommendation, approval-gated, bounded-autonomy, and broader-autonomy stages. Promotion requires evidence appropriate to the exact task and effect class [R73][R77][R78].

### From telemetry volume to decision-grade evidence

New contracts require outcome, trajectory, effect, intervention, recovery, and human-work evidence with stable identities, system versions, privacy policy, sampling, and join tests [R71][R72][R119][R121][R123].

### From metrics to metric contracts

The plugin now prohibits using aggregate satisfaction, benchmark score, adoption, acceptance, or success rate as sole product evidence. Metric contracts, SRM checks, guardrails, qualitative evidence, and causal design are required where the decision claims causality [R79][R80][R81][R82].

### From phase checklist to lifecycle assurance network

The lifecycle is represented as iterative decisions, artifacts, evidence, readiness thresholds, and feedback paths. Standards support tailoring and concurrent lifecycle processes rather than a mandatory waterfall [R83][R84][R87].

### From feature requirements to operational concepts and mission threads

Requirements engineering now begins with actors, work, decision rights, modes, interfaces, effects, and recovery. Quality attributes are made measurable through scenarios and traced to verification [R85][R86][R88].

### From architecture preference to risk-retiring slices

Architecture recommendations must state quality tradeoffs, sensitivity points, assumptions, and the evidence that would justify or overturn the choice. Delivery slices are selected by uncertainty retired and decision unlocked [R89].

### From “tests passed” to release and production evidence

Secure development, provenance, exact artifacts, progressive delivery, production readiness, SLOs, incidents, and rollback become explicit lifecycle contracts [R95][R98][R102][R103][R106][R107][R108].

### From deployment to sustainment and retirement

Model/tool/configuration drift, support burden, dependency risk, deprecation, migration, effect reconciliation, data disposition, and closure evidence are now first-class [R83][R84][R92].

### From Rust logs to typed field observability

Rust assets now model domain identities, field observations, rollout decisions, privacy/cardinality/sampling policy, `tracing`, OpenTelemetry, and feature exposure as explicit contracts [R115][R118][R119][R121][R123].

---

## 42. Confidence boundary for the expansion

The research-backed expansion is expected to improve decision quality because it converts broad aspirations into routable skills, explicit artifacts, deterministic schemas, evidence maps, behavior contracts, routing cases, validators, and release gates. The strongest support is for the underlying practices: representative task evaluation, post-deployment monitoring, human oversight, lifecycle tailoring, requirements traceability, quality-attribute analysis, secure development, progressive delivery, SRE, experimentation integrity, and structured observability.

The confidence claim is bounded:

- It is a calibrated engineering judgment about likely positive transfer when the skills are correctly invoked.
- It is not a guarantee that every project or decision improves.
- It does not replace domain-specific legal, safety, clinical, financial, accessibility, security, or organizational review.
- A live blind comparison using GPT-5.6 Sol and compilation of the adaptable Rust fragments remain downstream validation steps when the relevant runner and Rust toolchain are available.
- The plugin can improve the structure of evidence and decisions; it cannot manufacture representative access, trustworthy outcome labels, causal identification, or organizational follow-through.

The practical release threshold is therefore based on evidence traceability, routing precision, behavior-contract coverage, asset integrity, schema validation, static Rust checks, clean-package verification, and explicit residual-risk accounting—not on an unsupported claim of universal improvement.

# Source catalog

Evidence classes: **A** official primary documentation/standard/SDK; **B** first-party engineering/model report; **C** independent research/benchmark/practitioner synthesis; **D** user-provided design/process artifact.

**[R01] [OpenAI — Introducing the Codex app](https://openai.com/index/introducing-the-codex-app/).** 2026-02-02. *Class B; Codex and coding agents; first-party engineering report.* Codex uses isolated worktrees, skills, automations, sandboxing, and parallel agent surfaces. Operationalized as: Require artifact isolation, scoped parallelism, and reusable skills rather than transcript-only guidance.

**[R02] [OpenAI — Codex for every role, tool, and workflow](https://openai.com/index/codex-for-every-role-tool-and-workflow/).** 2026-06-02. *Class B; Codex and coding agents; first-party product/engineering report.* Codex expands beyond code edits to hosted artifacts, sites, annotations, and broader workflows. Operationalized as: Make the exact durable artifact and its user-facing verification the unit of completion.

**[R03] [OpenAI — Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/).** 2026-02-11. *Class B; Harness engineering; first-party engineering report.* Agent-first engineering shifts effort toward environment design, repository legibility, intent specification, feedback loops, and verification. Operationalized as: Center the plugin on layer ownership, repository readiness, harness design, and evidence-backed completion.

**[R04] [OpenAI — An open-source spec for Codex orchestration: Symphony](https://openai.com/index/open-source-codex-orchestration-symphony/).** 2026-04-27. *Class B; Orchestration; first-party engineering report.* Issue trackers and durable work objects can serve as control planes for always-on coding-agent orchestration. Operationalized as: Provide issue-to-artifact, durable plan, ownership, and handoff protocols.

**[R05] [OpenAI — The next evolution of the Agents SDK](https://openai.com/index/the-next-evolution-of-the-agents-sdk/).** 2026-04-15. *Class A; Runtime and sandboxing; first-party official architecture.* The harness can be separated from sandboxed compute for security, durability, and scale. Operationalized as: Separate control plane, execution plane, permissions, run state, and effects in harness blueprints.

**[R06] [OpenAI — Codex best practices](https://developers.openai.com/codex/learn/best-practices).** 2026. *Class A; Codex practice; official documentation.* High-quality tasks specify goal, context, constraints, and done-when; reusable guidance belongs in AGENTS.md and plans. Operationalized as: Ship execution-contract, layered AGENTS.md, plan, and evidence templates.

**[R07] [OpenAI — Build skills](https://developers.openai.com/codex/build-skills).** 2026. *Class A; Skills and context; official documentation.* Skills use progressive disclosure and may package focused instructions, references, assets, and scripts. Operationalized as: Use a narrow router plus focused skills; keep deep material in references and deterministic checks in scripts.

**[R08] [OpenAI — Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills).** 2026-01-22. *Class B; Evaluation; first-party evaluation guidance.* Reusable skills need systematic trigger and behavior evaluations derived from realistic failures. Operationalized as: Include should/should-not-trigger cases, behavior contracts, scenarios, and failure-derived eval guidance.

**[R09] [OpenAI — Safety in building agents](https://developers.openai.com/api/docs/guides/agent-builder-safety).** 2026. *Class A; Agent security; official documentation.* Structured boundaries, approvals, guardrails, and trace-based evaluation reduce prompt-injection and unsafe-action risk. Operationalized as: Encode provenance separation, capability/approval policies, and safety/recovery evals.

**[R10] [OpenAI — A practical guide to building AI agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/).** 2025. *Class A; Architecture patterns; official guide.* Agent systems combine model, tools, instructions, guardrails, and orchestration; single-agent simplicity is often preferable. Operationalized as: Apply smallest-fitting-architecture escalation and make multi-agent an earned choice.

**[R11] [Martin Fowler — Harness engineering for coding agent users](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html).** 2025. *Class C; Harness engineering; independent practitioner synthesis.* Harnesses combine feedforward guides and feedback sensors around coding agents. Operationalized as: Use explicit control/feedback mechanisms and distinguish prompt advice from executable controls.

**[R12] [AGENTS.md — open format](https://agents.md/).** 2025. *Class A; Repository context; open standard/convention.* AGENTS.md is an open repository convention for instructions to coding agents. Operationalized as: Provide layered AGENTS.md guidance and promotion rules for repeated corrections.

**[R13] [Anthropic — Building effective agents](https://www.anthropic.com/engineering/building-effective-agents).** 2024-12-19. *Class B; Architecture patterns; first-party engineering report.* Workflows have predefined paths while agents adapt their process; simple composable patterns should be preferred. Operationalized as: Define architecture escalation from direct call and deterministic workflow to bounded loop, graph, and multi-agent.

**[R14] [Anthropic — Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).** 2025-09-29. *Class B; Context engineering; first-party engineering report.* Context is a finite attention budget; high-signal retrieval, curation, provenance, and compaction matter more than maximal volume. Operationalized as: Add context classes, retrieval policy, progressive disclosure, and compaction checkpoints.

**[R15] [Anthropic — Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents).** 2025-11-26. *Class B; Long-running agents; first-party engineering report.* Long-running work benefits from initialization, progress files, compaction, resumable state, and fresh-session continuation. Operationalized as: Provide durable plan/handoff formats and state/checkpoint requirements.

**[R16] [Anthropic — Claude Code best practices](https://www.anthropic.com/engineering/claude-code-best-practices).** 2026. *Class B; Coding-agent practice; first-party engineering guidance.* Concise repository guidance, verification loops, hooks/permissions, and scoped parallel work improve coding-agent outcomes. Operationalized as: Require fast/full validation, concise guidance, ownership, and fresh verification while avoiding default privileged hooks.

**[R17] [Anthropic — Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).** 2026-01-09. *Class B; Agent evaluation; first-party engineering report.* Multi-turn agents require evaluation of trajectories, graders, environments, and lifecycle behavior, not only final answers. Operationalized as: Split outcome, trajectory, recovery, safety, and operational evals.

**[R18] [Anthropic — Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents).** 2025-09-11. *Class B; Tool design; first-party engineering report.* Tool names, descriptions, schemas, examples, boundaries, and tool-specific evals materially affect agent behavior. Operationalized as: Ship a semantic tool contract with schemas, effects, errors, permissions, and adversarial tests.

**[R19] [Anthropic — Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills).** 2025-10-16. *Class B; Agent skills; first-party engineering report.* Modular procedural knowledge can be packaged for progressive, reusable agent capability. Operationalized as: Keep skill jobs narrow and place depth in local references/assets.

**[R20] [Anthropic — How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system).** 2025-06-13. *Class B; Multi-agent systems; first-party engineering report.* Multi-agent systems require careful decomposition, independent work, coordination, integration, evaluation, and cost control. Operationalized as: Gate multi-agent use and provide delegation, ownership, fan-in, partial-failure, and coordination metrics.

**[R21] [LangChain — LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview).** 2026. *Class A; Graphs and state; official project documentation.* Explicit state graphs can combine deterministic and model-driven nodes with persistence and human-in-the-loop execution. Operationalized as: Define state/node/edge contracts and use graphs only when consequential control flow must be explicit.

**[R22] [LangChain — LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api).** 2026. *Class A; Graphs and state; official project documentation.* Graph APIs expose state, nodes, edges, reducers, branches, joins, and super-step execution. Operationalized as: Provide reducer, join, edge, node, and graph verification contracts.

**[R23] [LangChain — LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence).** 2026. *Class A; Persistence; official project documentation.* Checkpointers preserve thread state while stores support broader memory; durability has explicit state semantics. Operationalized as: Separate checkpoints from memory/cache and require versioned state/replay tests.

**[R24] [LangChain — LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts).** 2026. *Class A; Human interrupts; official project documentation.* Interrupts persist state and resume later; code before an interrupt may replay and must be idempotent. Operationalized as: Split prepare/approve/execute, validate stale resumes, and test replay around interrupts.

**[R25] [Temporal — Activity Definition / idempotency](https://docs.temporal.io/activity-definition).** 2026. *Class A; Durable effects; official project documentation.* At-least-once activity execution requires granular, idempotent effects and stable keys. Operationalized as: Require action IDs, effect journals, idempotency and reconciliation around external effects.

**[R26] [Temporal — Pre-production testing](https://docs.temporal.io/develop/test-suite).** 2026. *Class A; Durability testing; official project documentation.* Killing/restarting workers tests replay, idempotency, retries, and recovery before production. Operationalized as: Include crash-point and replay fault matrices for graphs and Rust runtimes.

**[R27] [Model Context Protocol — Tools specification](https://modelcontextprotocol.io/specification/draft/server/tools).** 2026. *Class A; Tools and protocols; open protocol specification.* MCP tools use JSON Schema and model-controlled invocation but require validation, access control, clear user visibility, timeouts, logging, and safe output handling. Operationalized as: Encode schema-first tools, server-side authorization, approval visibility, output sanitation, and MCP conformance.

**[R28] [A2A Protocol — A2A v1.0 announcement/specification](https://a2a-protocol.org/latest/announcing-1.0/).** 2026. *Class A; Agent protocols; open protocol specification/announcement.* A2A defines interoperable agent discovery, task lifecycle, artifacts, identity, and enterprise controls. Operationalized as: Treat A2A as a peer-agent boundary with durable task mapping, identity, cancellation, and conformance tests.

**[R29] [A2A Protocol — A2A and MCP comparison](https://a2a-protocol.org/latest/topics/a2a-and-mcp/).** 2026. *Class A; Protocol boundaries; official protocol guidance.* MCP primarily addresses agent-to-tool/resource integration while A2A addresses peer-agent interaction. Operationalized as: Keep tool and peer-agent boundaries distinct and do not adopt either protocol without a real interoperability need.

**[R30] [Google Agent Development Kit — workflow agents](https://google.github.io/adk-docs/agents/workflow-agents/).** 2026. *Class A; Workflow patterns; official project documentation.* Sequential, parallel, and loop agents provide deterministic orchestration patterns. Operationalized as: Distinguish deterministic workflows/fan-out from adaptive loops and multi-agent systems.

**[R31] [Microsoft Agent Framework — workflows](https://learn.microsoft.com/en-us/agent-framework/workflows/).** 2026. *Class A; Workflow graphs; official documentation.* Typed routing, graph workflows, checkpointing, and human-in-the-loop are first-class orchestration concerns. Operationalized as: Require typed routes, checkpoints, interrupts, and verification matrices.

**[R32] [GitHub — Spec Kit](https://github.com/github/spec-kit).** 2026. *Class A; Spec-driven development; official open-source project.* Spec-driven development packages constitution, specification, planning, tasks, and implementation for coding agents. Operationalized as: Provide an execution contract, architecture brief, plan, ADR, and acceptance matrix.

**[R33] [GitHub Spec Kit — Agentic SDD reference](https://github.com/github/spec-kit/blob/main/docs/reference/overview.md).** 2026. *Class A; Spec-driven development; official project documentation.* Agentic SDD separates clarify, plan, checklist, tasks, analysis, implementation, and convergence. Operationalized as: Use phase-specific artifacts and make convergence evidence explicit.

**[R34] [SWE-bench — Verified](https://www.swebench.com/verified.html).** 2026. *Class C; Coding benchmarks; benchmark.* Human-validated real GitHub issue-to-patch tasks provide a more reliable coding benchmark subset. Operationalized as: Prefer repository-grounded, exact-task eval fixtures and accepted-artifact evidence.

**[R35] [Stanford / Laude Institute — Terminal-Bench](https://www.tbench.ai/).** 2026. *Class C; Agent benchmarks; benchmark.* Terminal-environment tasks test practical execution across software and systems domains. Operationalized as: Evaluate tools, trajectories, state, and environment interaction—not only text generation.

**[R36] [METR — Task-Completion Time Horizons](https://metr.org/time-horizons/).** 2026-05-08. *Class C; Reliability measurement; independent research/benchmark.* Model reliability varies with task duration and should be represented as curves/distributions rather than a single capability claim. Operationalized as: Calibrate autonomy and verification to task horizon; avoid treating model capability as deterministic.

**[R37] [Research paper — SWE Atlas](https://arxiv.org/html/2605.08366v1).** 2026-05-08. *Class C; Coding-agent benchmark; research paper.* Coding-agent evaluation should include repository Q&A, tests, refactoring, and work beyond issue resolution. Operationalized as: Broaden eval scenarios across architecture, verification, maintenance, and repository understanding.

**[R38] [OWASP — Agentic Security Initiative](https://genai.owasp.org/initiatives/agentic-security-initiative/).** 2026. *Class A; Agent security; industry security initiative.* Agentic systems introduce risks across identity, tools, memory, protocols, actions, governance, and supply chains. Operationalized as: Ship a threat model, injection/provenance policy, capability/approval controls, and incident protocol.

**[R39] [OpenTelemetry — GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/).** 2026. *Class A; Observability; open standard documentation.* Emerging conventions standardize telemetry vocabulary for model and agent operations. Operationalized as: Align trace events where practical while versioning an internal semantic/evidence schema and protecting sensitive data.

**[R40] [Google — Introducing A2UI](https://developers.googleblog.com/introducing-a2ui-an-open-project-for-agent-driven-interfaces/).** 2025-12. *Class B; Agent UX; first-party project announcement.* Structured, bounded agent-generated interfaces are an emerging direction for agent-to-user interaction. Operationalized as: Treat interactive approvals and artifacts as explicit contracts rather than unconstrained generated UI.

**[R41] [Model Context Protocol — MCP Apps](https://modelcontextprotocol.io/docs/extensions/apps).** 2026. *Class A; Agent UX; official protocol extension documentation.* MCP-backed apps can add interactive user surfaces to tool integrations. Operationalized as: Keep UI optional and consequence-focused; the plugin ships instruction assets without mandatory connectors or apps.

**[R42] `User-provided Design Judgment Codex plugin`.** 2026. *Class D; Design method; user-provided artifact.* A six-gate method separates situation, evidence, divergence, commitment, interaction contract, and verification with calibrated confidence. Operationalized as: Reuse evidence traceability, explicit decision commitment, behavior contracts, and release-gate discipline for this plugin.

**[R43] [OpenAI — GPT-5.6: Frontier intelligence that scales with your ambition](https://openai.com/index/gpt-5-6/).** 2026-07-09. *Class B; GPT-5.6; first-party model announcement.* GPT-5.6 adds stronger coding and tool-heavy programmatic execution that can coordinate tools, process intermediate results, and choose next actions. Operationalized as: Optimize prompts for decision-complete contracts, typed tools, programmatic aggregation, and evidence-backed stopping.

**[R44] [OpenAI — Codex models](https://developers.openai.com/codex/models).** 2026-07-22 accessed. *Class A; GPT-5.6 Sol; official documentation.* GPT-5.6 Sol is the flagship Codex model for complex coding, computer use, research, and cybersecurity; medium is the default power setting and deeper effort is available. Operationalized as: Ship a Sol operating profile and reserve high/Max/Ultra for named complexity rather than using maximum effort by default.

**[R45] [OpenAI — Build skills (current Codex documentation)](https://developers.openai.com/codex/build-skills).** 2026-07-22 accessed. *Class A; Skills; official documentation.* Skill metadata is discovered before full instructions; concise front-loaded trigger descriptions and focused jobs improve selection. Operationalized as: Create focused skills with trigger-oriented descriptions, negative activation boundaries, named output contracts, and deep local references; split broad domains when activation conditions or decision artifacts differ.

**[R46] [OpenAI — Skills & Plugins](https://developers.openai.com/codex/skills-and-plugins).** 2026-07-22 accessed. *Class A; Plugins; official documentation.* A skill is a focused reusable workflow; a plugin is an installable bundle that can combine skills and connectors/MCP. Operationalized as: Package the operationalization as an installable plugin while keeping external connectors optional.

**[R47] [OpenAI — Build plugins](https://learn.chatgpt.com/docs/build-plugins).** 2026-07-22 accessed. *Class A; Plugins; official documentation.* Codex plugins use a manifest and can package skills under a marketplace structure for installation and sharing. Operationalized as: Follow the current `.codex-plugin/plugin.json`, `skills/`, and marketplace layout and validate it statically.

**[R48] [OpenAI — Custom instructions with AGENTS.md](https://developers.openai.com/codex/agent-configuration/agents-md).** 2026-07-22 accessed. *Class A; Repository instructions; official documentation.* Codex reads AGENTS.md before work and applies layered repository guidance. Operationalized as: Provide layered AGENTS.md pattern and keep stable rules out of per-task prompts.

**[R49] [OpenAI — Subagents](https://developers.openai.com/codex/subagents).** 2026-07-22 accessed. *Class A; Subagents; official documentation.* Codex can spawn specialized parallel agents and collect their results; this is most useful for highly parallel work. Operationalized as: Require explicit delegation, ownership, evidence, fan-in, cancellation, and a multi-agent entry gate.

**[R50] [OpenAI — Unrolling the Codex agent loop](https://openai.com/index/unrolling-the-codex-agent-loop/).** 2026-01-23. *Class B; Agent loops; first-party engineering report.* The Codex harness implements an iterative user/model/tool loop with context assembly and execution logic. Operationalized as: Make observe/plan/act/verify/update and tool/effect state explicit instead of relying on a vague iterative prompt.

**[R51] [OpenAI — Unlocking the Codex harness: how we built the App Server](https://openai.com/index/unlocking-the-codex-harness/).** 2026-02-04. *Class B; Harness architecture; first-party engineering report.* The Codex harness includes thread persistence, configuration/authentication, tool execution, skills, sandboxing, and a stable event stream through App Server. Operationalized as: Treat lifecycle, state, tools, extensions, configuration, authentication, and events as harness concerns.

**[R52] [OpenAI — The next evolution of the Agents SDK](https://openai.com/index/the-next-evolution-of-the-agents-sdk/).** 2026-04-15. *Class B; Agent runtime; first-party engineering report.* Separating harness from compute supports controlled sandbox execution and long-horizon work. Operationalized as: Keep execution identities and sandboxes separate from the control plane and persist state outside ephemeral workers.

**[R53] [OpenAI — Codex customization overview](https://developers.openai.com/codex/customization/overview).** 2026-07-22 accessed. *Class A; Codex customization; official documentation.* Skills are discoverable, reusable workflows with richer instructions, scripts, and references without loading all content up front. Operationalized as: Use progressive disclosure and avoid monolithic always-on guidance.

**[R54] [OpenAI — Codex changelog](https://developers.openai.com/codex/changelog).** 2026-07-22 accessed. *Class A; Codex releases; official changelog.* Codex surfaces, plugin management, permissions, subagent visibility, and model support evolve rapidly. Operationalized as: Add a research/update policy and avoid hard-coding unstable availability or UI details beyond the research lock.

**[R55] [Tokio — Graceful Shutdown](https://tokio.rs/tokio/topics/shutdown).** 2026-07-22 accessed. *Class A; Rust runtime; official project documentation.* Graceful shutdown combines detection, cancellation tokens, and waiting for tasks to finish. Operationalized as: Require stop-intake, cancellation propagation, tracked drain, reconciliation, persistence, and a final deadline.

**[R56] [Tokio — runtime documentation](https://docs.rs/tokio/latest/tokio/runtime/).** 2026-07-22 accessed. *Class A; Rust runtime; official crate documentation.* Tokio schedules async tasks cooperatively; blocking or non-yielding work can stall core threads and runtime lifetime has explicit semantics. Operationalized as: Separate blocking work, supervise tasks, and make task/runtime ownership explicit.

**[R57] [Tokio — Semaphore](https://docs.rs/tokio/latest/tokio/sync/struct.Semaphore.html).** 2026-07-22 accessed. *Class A; Rust backpressure; official crate documentation.* Semaphores bound concurrent access by permits and await capacity. Operationalized as: Use per-resource bounded concurrency with cancellation/deadlines and overload metrics.

**[R58] [The Cargo Book — cargo check](https://doc.rust-lang.org/cargo/commands/cargo-check.html).** 2026-07-22 accessed. *Class A; Rust verification; official language/tool documentation.* `cargo check` type-checks packages without final code generation and is faster, but some code-generation errors remain outside its coverage. Operationalized as: Use `cargo check` as an early gate, not a substitute for tests and release builds.

**[R59] [The Cargo Book — cargo test](https://doc.rust-lang.org/cargo/commands/cargo-test.html).** 2026-07-22 accessed. *Class A; Rust verification; official language/tool documentation.* `cargo test` compiles and runs unit, integration, and documentation tests. Operationalized as: Include workspace/unit/integration/doc tests in the verification ladder.

**[R60] [The Cargo Book — cargo clippy](https://doc.rust-lang.org/cargo/commands/cargo-clippy.html).** 2026-07-22 accessed. *Class A; Rust verification; official language/tool documentation.* Clippy is an official toolchain component for additional lint analysis. Operationalized as: Include project-policy Clippy checks and do not claim unavailable linting passed.

**[R61] [The Cargo Book — cargo fmt](https://doc.rust-lang.org/cargo/commands/cargo-fmt.html).** 2026-07-22 accessed. *Class A; Rust verification; official language/tool documentation.* Rustfmt is an official toolchain component invoked through Cargo for formatting. Operationalized as: Include deterministic format checks in fast and release gates.

**[R62] [The Cargo Book — cargo miri / Miri](https://doc.rust-lang.org/cargo/commands/cargo-miri.html).** 2026-07-22 accessed. *Class A; Rust undefined behavior; official language/tool documentation.* Miri runs compatible binaries/tests in an interpreter and can detect classes of undefined behavior; it is a nightly optional component. Operationalized as: Use Miri selectively for unsafe/FFI-sensitive code and report it separately from ordinary tests.

**[R63] [Tokio project — Loom](https://docs.rs/loom/latest/loom/).** 2026-07-22 accessed. *Class A; Rust concurrency testing; official project/crate documentation.* Loom explores concurrent executions of small synchronization tests using state reduction. Operationalized as: Use Loom for narrow concurrency primitives while retaining integration and process fault tests.

**[R64] [RustSec Advisory Database](https://rustsec.org/).** 2026-07-22 accessed. *Class A; Rust supply chain; official ecosystem security project.* RustSec provides a vulnerability advisory database and tooling such as cargo-audit for Cargo.lock. Operationalized as: Include dependency advisory/exception policy and exact artifact provenance in CI guidance.

**[R65] [The Cargo Book — Continuous Integration](https://doc.rust-lang.org/cargo/guide/continuous-integration.html).** 2026-07-22 accessed. *Class A; Rust CI; official language/tool documentation.* Cargo documents build/check/test patterns for CI and highlights target/version considerations. Operationalized as: Provide PR/release verification matrices rather than one local command.

**[R66] [Model Context Protocol — official Rust SDK](https://github.com/modelcontextprotocol/rust-sdk).** 2026-07-22 accessed. *Class A; MCP Rust; official SDK repository.* The official Rust SDK supports building MCP clients and servers exposing tools, resources, and prompts. Operationalized as: Keep MCP in an adapter crate, validate/authorize server-side, and run protocol/security conformance tests.

**[R67] [A2A Project — official Rust SDK (a2a-rs)](https://github.com/a2aproject/a2a-rs).** 2026-07-22 accessed. *Class A; A2A Rust; official SDK repository.* The Rust workspace implements A2A v1 protocol types plus async client/server and gRPC support. Operationalized as: Isolate A2A wire types, map durable task lifecycle, authenticate peers, and test independent interoperability.

**[R68] [Restate — Rust SDK documentation](https://docs.restate.dev/develop/rust/overview).** 2026-07-22 accessed. *Class A; Rust durability; official project documentation.* Rust applications can use a durable execution platform for persisted invocations and workflow/service semantics. Operationalized as: Present durable runtime adoption as an option requiring hard-semantics proof, not a default framework dependency.

**[R69] [Rig — Observability documentation](https://docs.rig.rs/docs/concepts/observability).** 2026-07-22 accessed. *Class A; Rust observability; official project documentation.* Rust agent frameworks expose tracing/observability integration but application evidence and policy remain separate concerns. Operationalized as: Keep framework telemetry behind adapters and require run/action/evidence IDs independent of one framework.

**[R70] [Schemars — JSON Schema generation for Rust](https://docs.rs/schemars/latest/schemars/).** 2026-07-22 accessed. *Class A; Rust schemas; official crate documentation.* Schemars derives JSON Schema from Rust types, supporting schema-first protocol/tool surfaces while still requiring review for compatibility and semantics. Operationalized as: Provide typed wire DTOs and schema snapshots but require semantic validation and protocol compatibility tests.

**[R71] [OpenAI — Agent Improvement Loop](https://developers.openai.com/cookbook/examples/agents_sdk/agent_improvement_loop).** 2026-05-12. *Class A; Agent improvement loops; official engineering cookbook.* A production-grade improvement loop starts with real traces, gathers human and model feedback, converts findings into evals, and changes prompts, tools, policy, or harness behavior before re-running the loop. Operationalized as: Require a trace-to-change ledger that links field observations to hypotheses, regression fixtures, product or harness changes, rollout evidence, and keep/revert decisions. Affected skills: `authentic-use-engineering`, `agent-evals-observability`, `agentic-product-lifecycle`.

**[R72] [OpenAI — Macro Evals for Agentic Systems](https://developers.openai.com/cookbook/examples/partners/macro_evals_for_agentic_systems/macro_evals_for_agentic_systems).** 2026-07-22 accessed. *Class A; Agent evaluation; official engineering cookbook.* Agentic systems require evaluation across end-to-end outcomes, trajectories, tool behavior, and interaction patterns rather than isolated model responses alone. Operationalized as: Make authentic-use evidence joinable to outcome, trajectory, intervention, recovery, and system-version records; use field-derived cases to maintain macro evals. Affected skills: `authentic-use-engineering`, `agent-evals-observability`, `continuous-product-experimentation`, `software-construction-quality`.

**[R73] [Anthropic — Measuring AI agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy).** 2026-06-25. *Class B; Human oversight and autonomy; first-party empirical research report.* Real use shows autonomy is graded and shaped by task duration, intervention, human oversight, and deployment context; capability does not imply unrestricted authority. Operationalized as: Use an autonomy-and-exposure ladder with observed intervention burden, effect risk, and recovery evidence as promotion criteria rather than treating autonomy as binary. Affected skills: `authentic-use-engineering`, `agent-security-governance`, `agentic-product-lifecycle`.

**[R74] [Anthropic — Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).** 2026-01-09. *Class B; Agent evaluation; first-party engineering report.* Useful agent evaluations start from representative tasks and failure modes, combine multiple graders and transcript inspection, and mature through an iterative process rather than a single score. Operationalized as: Require task-distribution coverage, grader calibration, trace review, failure-derived regressions, and explicit limits on what offline evals prove. Affected skills: `authentic-use-engineering`, `agent-evals-observability`, `software-construction-quality`.

**[R75] [NIST AI 800-4 — A Methodology for Assessing and Managing Post-Deployment AI Risks](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.800-4.pdf).** 2026-03. *Class A; Deployed AI monitoring; official government publication.* Post-deployment AI risk management requires continuous monitoring, context-specific impact assessment, incident handling, change management, stakeholder feedback, and documented reassessment as conditions evolve. Operationalized as: Make controlled field learning a governed post-deployment assurance activity with operating envelopes, escalation thresholds, observation quality, incident links, and reauthorization after material change. Affected skills: `authentic-use-engineering`, `production-readiness-sre`, `continuous-product-experimentation`, `maintenance-retirement-engineering`, `agent-security-governance`.

**[R76] [NIST AI RMF — Core and Playbook](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/).** 2026-07-22 accessed. *Class A; AI risk lifecycle; official government framework.* AI risk work spans Govern, Map, Measure, and Manage and should be continuous, context-sensitive, documented, and connected to human and organizational decision rights. Operationalized as: Map lifecycle artifacts and field-learning decisions to governance, context, measurement, and risk-treatment responsibilities rather than treating evaluation as an isolated technical task. Affected skills: `agentic-product-lifecycle`, `authentic-use-engineering`, `agent-security-governance`, `requirements-systems-engineering`.

**[R77] [Nature Medicine — Silent trials in healthcare AI: a scoping review](https://www.nature.com/articles/s44360-025-00048-z).** 2025-04-14. *Class C; Silent and shadow evaluation; independent peer-reviewed research.* Silent deployment can test workflow fit, data quality, calibration, integration, and operational behavior without influencing decisions, but inconsistent terminology and reporting limit comparability. Operationalized as: Define shadow or silent operation precisely, record exposure and counterfactual outputs, prohibit unapproved effects, and specify evidence required to advance beyond observation-only operation. Affected skills: `authentic-use-engineering`, `concept-feasibility-validation`, `continuous-product-experimentation`.

**[R78] [The silent trial — a bridge from algorithms to clinical practice](https://pmc.ncbi.nlm.nih.gov/articles/PMC9424628/).** 2022-08-18. *Class C; Silent evaluation; independent peer-reviewed research.* Prospective silent evaluation reveals performance, implementation, and workflow problems that retrospective validation cannot expose while avoiding direct impact on live decisions. Operationalized as: Use prospective shadow-mode trials where risk warrants, with predeclared endpoints, representative workflow coverage, mismatch review, and transition criteria. Affected skills: `authentic-use-engineering`, `concept-feasibility-validation`, `production-readiness-sre`.

**[R79] [Microsoft Research — Patterns of Trustworthy Experimentation: During-Experiment Stage](https://www.microsoft.com/en-us/research/group/experimentation-platform-exp/articles/patterns-of-trustworthy-experimentation-during-experiment-stage/).** 2021-01-25. *Class B; Online experimentation; first-party research guidance.* Trustworthy online experiments require treatment integrity, data-quality checks, trustworthy analysis, monitoring during exposure, and protection against interpretation pitfalls. Operationalized as: Require assignment, exposure, outcome, and telemetry integrity checks; freeze decision rules before reading results; stop or invalidate experiments with unresolved data-quality failures. Affected skills: `continuous-product-experimentation`, `authentic-use-engineering`, `production-readiness-sre`.

**[R80] [Microsoft Research — Diagnosing Sample Ratio Mismatch in A/B Testing](https://www.microsoft.com/en-us/research/articles/diagnosing-sample-ratio-mismatch-in-a-b-testing/).** 2020-08-17. *Class B; Experiment data quality; first-party research guidance.* Sample ratio mismatch is a symptom of assignment, execution, logging, analysis, or survivorship problems and can make apparent treatment effects untrustworthy. Operationalized as: Make sample-ratio and exposure-integrity checks blocking experiment gates; diagnose the mechanism before using results for product decisions. Affected skills: `continuous-product-experimentation`, `authentic-use-engineering`.

**[R81] [Microsoft Research — Pitfalls of Long-Term Online Controlled Experiments](https://www.microsoft.com/en-us/research/publication/pitfalls-of-long-term-online-controlled-experiments/).** 2016-12-01. *Class C; Long-term experimentation; peer-reviewed practitioner research.* Long-running experiments can be distorted by identity instability, survivorship and selection bias, novelty, carryover, and misleading trends. Operationalized as: Require long-horizon metric and cohort reasoning, stable assignment analysis, carryover policy, and explicit limits on extrapolating short-term effects. Affected skills: `continuous-product-experimentation`, `maintenance-retirement-engineering`.

**[R82] [Microsoft Research — Experimentation in Generative AI: C++ Team Practices for Continuous Improvement](https://www.microsoft.com/en-us/research/articles/experimentation-in-genai-c-teams-practices-for-continuous-improvement/).** 2024-11-12. *Class B; Generative-AI experimentation; first-party engineering report.* Generative-AI product development benefits from complementary offline evaluation, online experimentation, qualitative inspection, feedback, and continuous iteration because no single measure captures quality. Operationalized as: Combine controlled metrics with trace review and user/workflow evidence; use field failures to update offline datasets and product mechanisms. Affected skills: `authentic-use-engineering`, `continuous-product-experimentation`, `agent-product-discovery`.

**[R83] [ISO/IEC/IEEE 12207:2026 — Software life cycle processes](https://www.iso.org/standard/90219.html).** 2026. *Class A; Software lifecycle; international standard.* Software lifecycle work is a set of interrelated technical, management, agreement, and support processes that can be tailored to context and iterated across the life of a system. Operationalized as: Represent the lifecycle as an assurance network with tailored decisions, artifacts, evidence, roles, and feedback paths rather than a mandatory waterfall. Affected skills: `agentic-product-lifecycle`, `software-construction-quality`, `secure-delivery-release`, `maintenance-retirement-engineering`.

**[R84] [ISO/IEC/IEEE 15288:2023 — System life cycle processes](https://www.iso.org/standard/81702.html).** 2023. *Class A; Systems lifecycle; international standard.* Systems engineering spans conception through utilization, support, and retirement, integrating stakeholder needs, architecture, verification, validation, transition, operation, and disposal. Operationalized as: Keep product, software, operational, support, and retirement decisions connected; require mission threads and lifecycle-wide evidence continuity. Affected skills: `agentic-product-lifecycle`, `requirements-systems-engineering`, `production-readiness-sre`, `maintenance-retirement-engineering`.

**[R85] [ISO/IEC/IEEE 29148:2018 — Requirements engineering](https://www.iso.org/standard/72089.html).** 2018. *Class A; Requirements engineering; international standard.* Good requirements are derived from stakeholder needs and operational concepts, are traceable and verifiable, and include interfaces, constraints, and quality attributes. Operationalized as: Create operational concepts, mission threads, requirement quality checks, bidirectional traceability, verification methods, and controlled baselines. Affected skills: `requirements-systems-engineering`, `agent-product-discovery`, `concept-feasibility-validation`.

**[R86] [ISO/IEC 25010:2023 — Product quality model](https://www.iso.org/standard/78176.html).** 2023. *Class A; Product quality models; international standard.* Software and ICT product quality is multi-dimensional; functional correctness alone does not establish reliability, security, compatibility, usability, maintainability, or other quality characteristics. Operationalized as: Use explicit quality-attribute scenarios and evidence plans so agent-generated software is not judged only by feature completion or passing unit tests. Affected skills: `requirements-systems-engineering`, `architecture-delivery-planning`, `software-construction-quality`, `production-readiness-sre`.

**[R87] [ISO/IEC/IEEE 24748-1:2024 — Life cycle management](https://www.iso.org/standard/84709.html).** 2024. *Class A; Lifecycle management; international standard.* Lifecycle management requires selection and tailoring of processes, integrated planning, decision management, configuration control, information management, measurement, and risk management. Operationalized as: Require lifecycle tailoring, decision records, baselines, evidence ownership, measurements, and change triggers across all plugin lifecycle skills. Affected skills: `agentic-product-lifecycle`, `architecture-delivery-planning`, `maintenance-retirement-engineering`.

**[R88] [Software Engineering Institute — Quality Attribute Workshop Collection](https://www.sei.cmu.edu/library/quality-attribute-workshop-collection/).** 2026-07-22 accessed. *Class B; Quality attributes; official engineering method.* Stakeholder-driven quality-attribute scenarios make vague nonfunctional concerns concrete through stimulus, environment, artifact, response, and response measure. Operationalized as: Require measurable quality-attribute scenarios before architecture commitments and use them as construction, test, and production evidence targets. Affected skills: `requirements-systems-engineering`, `architecture-delivery-planning`, `production-readiness-sre`.

**[R89] [Software Engineering Institute — Architecture Tradeoff Analysis Method](https://www.sei.cmu.edu/library/atam-method-for-architecture-evaluation/).** 2026-07-22 accessed. *Class B; Architecture evaluation; official engineering method.* Architecture evaluation should expose quality-attribute tradeoffs, sensitivity points, risks, non-risks, and assumptions before costs are locked in. Operationalized as: Use explicit tradeoff analysis and risk themes to prioritize thin slices, spikes, and evidence rather than selecting architecture by fashion or agent preference. Affected skills: `architecture-delivery-planning`, `concept-feasibility-validation`, `agentic-engineering`.

**[R90] [GOV.UK Service Manual — How the discovery phase works](https://www.gov.uk/service-manual/agile-delivery/how-the-discovery-phase-works).** 2026-07-22 accessed. *Class A; Product discovery; official government product guidance.* Discovery is for understanding the problem, users, constraints, current journeys, risks, and whether a service should proceed—not for prematurely building the solution. Operationalized as: Require representative research, current-state evidence, problem framing, assumptions, constraints, and a go/stop recommendation before deeper implementation. Affected skills: `agent-product-discovery`, `agentic-product-lifecycle`, `concept-feasibility-validation`.

**[R91] [GOV.UK Service Manual — How the beta phase works](https://www.gov.uk/service-manual/agile-delivery/how-the-beta-phase-works).** 2026-07-22 accessed. *Class A; Incremental delivery; official government product guidance.* Beta builds and improves a working service in small releases, learns from real users, manages operational readiness, and addresses accessibility, security, performance, and support needs. Operationalized as: Use thin vertical slices, controlled real-use exposure, progressive delivery, operational readiness, and recurring evidence reviews before broader release. Affected skills: `concept-feasibility-validation`, `architecture-delivery-planning`, `software-construction-quality`, `secure-delivery-release`.

**[R92] [GOV.UK Service Manual — Retiring your service](https://www.gov.uk/service-manual/technology/retiring-your-service).** 2026-07-22 accessed. *Class A; Service retirement; official government product guidance.* Service retirement requires user communication, migration or alternatives, data and dependency handling, support planning, and evidence that critical journeys remain protected. Operationalized as: Treat retirement as an engineered lifecycle phase with owner, inventory, communication, migration, rollback, evidence retention, and post-close verification. Affected skills: `maintenance-retirement-engineering`, `agentic-product-lifecycle`.

**[R93] [Microsoft — Guidelines for Human-AI Interaction](https://www.microsoft.com/en-us/haxtoolkit/ai-guidelines/).** 2026-07-22 accessed. *Class B; Human-AI product design; first-party research-backed design guidance.* Human-AI systems should set expectations, support efficient invocation, make uncertainty and limits legible, allow correction and dismissal, learn cautiously, and support global controls. Operationalized as: Include expectation, intervention, override, recovery, feedback, and control behavior in discovery, concept, field-learning, and production-readiness evidence. Affected skills: `agent-product-discovery`, `concept-feasibility-validation`, `authentic-use-engineering`, `production-readiness-sre`.

**[R94] [Google PAIR — People + AI Guidebook](https://pair.withgoogle.com/guidebook/).** 2026-07-22 accessed. *Class B; Human-centered AI; first-party design guidance.* Human-centered AI development connects user needs, data and model capabilities, mental models, explainability, feedback, control, errors, and graceful failure throughout product design. Operationalized as: Use human-work evidence, calibrated expectations, controllability, recovery, and qualitative research as product requirements rather than post-build polish. Affected skills: `agent-product-discovery`, `concept-feasibility-validation`, `requirements-systems-engineering`, `authentic-use-engineering`.

**[R95] [NIST SP 800-218 — Secure Software Development Framework 1.1](https://csrc.nist.gov/pubs/sp/800/218/final).** 2022-02. *Class A; Secure software development; official government standard guidance.* Secure development integrates preparation, protection of software, production of well-secured software, and vulnerability response into the development lifecycle. Operationalized as: Require threat/risk work, protected build environments, review and testing, provenance, vulnerability handling, and evidence before release. Affected skills: `secure-delivery-release`, `software-construction-quality`, `maintenance-retirement-engineering`.

**[R96] [NIST SP 800-218 Rev. 1 Initial Public Draft](https://csrc.nist.gov/pubs/sp/800/218/r1/ipd).** 2025-12. *Class A; Secure software development; official government draft guidance.* The evolving SSDF revision reinforces lifecycle-wide secure software practices and updates implementation considerations for modern development environments. Operationalized as: Mark draft-derived guidance as provisional, keep plugin security rules tied to stable principles, and review the source when the standard is finalized. Affected skills: `secure-delivery-release`, `maintenance-retirement-engineering`.

**[R97] [NIST SP 800-218A — Secure Software Development Practices for Generative AI and Dual-Use Foundation Models](https://csrc.nist.gov/pubs/sp/800/218/a/final).** 2024-07. *Class A; AI secure development; official government guidance.* AI software development adds model, data, provenance, evaluation, misuse, supply-chain, and deployment risks that should be integrated into secure development practices. Operationalized as: Extend threat models and release evidence to prompts, models, tools, datasets, evaluations, agent permissions, and model/provider changes. Affected skills: `secure-delivery-release`, `agent-security-governance`, `authentic-use-engineering`.

**[R98] [SLSA v1.2 specification](https://slsa.dev/spec/v1.2/).** 2025-09. *Class A; Supply-chain provenance; official open specification.* Build provenance and progressively stronger build integrity controls make software artifacts traceable to source, build process, and protected infrastructure. Operationalized as: Require artifact identity, provenance, reproducible or verifiable build steps, protected release credentials, and exact delivered-artifact checks. Affected skills: `secure-delivery-release`, `software-construction-quality`, `agent-first-software-engineering`.

**[R99] [CycloneDX 1.7 specification](https://cyclonedx.org/specification/overview/).** 2025-10. *Class A; Software bill of materials; official open specification.* CycloneDX provides machine-readable BOM models for components, services, dependencies, vulnerabilities, attestations, and other supply-chain information. Operationalized as: Generate and validate an SBOM or equivalent inventory for release where appropriate and link it to artifact provenance and vulnerability policy. Affected skills: `secure-delivery-release`, `maintenance-retirement-engineering`.

**[R100] [CISA — Secure by Design](https://www.cisa.gov/securebydesign).** 2026-07-22 accessed. *Class A; Secure by design; official government guidance.* Software manufacturers should make secure outcomes the default, reduce customer security burden, treat security as a core product requirement, and improve transparency and accountability. Operationalized as: Make secure defaults, least privilege, safe failure, product-level security outcomes, and ownership explicit from discovery through maintenance. Affected skills: `agent-product-discovery`, `requirements-systems-engineering`, `secure-delivery-release`, `maintenance-retirement-engineering`.

**[R101] [CISA — Software Bill of Materials resources](https://www.cisa.gov/topics/information-communications-technology-supply-chain-security/sbom).** 2026-07-22 accessed. *Class A; Software bill of materials; official government guidance.* An SBOM is a formal component inventory that supports vulnerability identification, risk assessment, transparency, and coordinated response across the software lifecycle. Operationalized as: Require release and maintenance processes to retain component inventory, ownership, update policy, and linkages to vulnerability response and retirement. Affected skills: `secure-delivery-release`, `maintenance-retirement-engineering`.

**[R102] [Google SRE — Evolving SRE Engagement Model / Production Readiness Review](https://sre.google/sre-book/evolving-sre-engagement-model/).** 2026-07-22 accessed. *Class A; Production readiness; official engineering handbook.* A production readiness review examines architecture, dependencies, capacity, failure modes, monitoring, alerts, runbooks, rollout, and operational ownership before service handoff or launch. Operationalized as: Require a production-readiness evidence package with owners, SLOs, capacity, dependencies, failure/recovery tests, observability, runbooks, rollout, and rollback. Affected skills: `production-readiness-sre`, `secure-delivery-release`, `architecture-delivery-planning`.

**[R103] [Google SRE — Embracing Risk](https://sre.google/sre-book/embracing-risk/).** 2026-07-22 accessed. *Class A; Reliability economics; official engineering handbook.* Service-level objectives and error budgets translate reliability into an explicit risk and investment decision, balancing reliability work against product velocity. Operationalized as: Define SLIs/SLOs and an error-budget policy with release, escalation, experimentation, and remediation consequences rather than treating reliability as a slogan. Affected skills: `production-readiness-sre`, `continuous-product-experimentation`, `maintenance-retirement-engineering`.

**[R104] [Google SRE — Managing Incidents](https://sre.google/sre-book/managing-incidents/).** 2026-07-22 accessed. *Class A; Incident management; official engineering handbook.* Effective incident response uses clear command roles, communication, operational coordination, escalation, and disciplined recovery under pressure. Operationalized as: Require incident roles, severity, escalation, containment, communication, evidence capture, and recovery/reconciliation procedures for consequential agent systems. Affected skills: `production-readiness-sre`, `agent-security-governance`, `maintenance-retirement-engineering`.

**[R105] [Google SRE — Postmortem Culture](https://sre.google/sre-book/postmortem-culture/).** 2026-07-22 accessed. *Class A; Incident learning; official engineering handbook.* Blameless postmortems focus on contributing system conditions, impact, timeline, detection, response, and owned corrective actions to prevent recurrence. Operationalized as: Turn incidents and field failures into mechanism-based learning records, owned corrections, regression evidence, and follow-through checks rather than anecdotes or blame. Affected skills: `production-readiness-sre`, `authentic-use-engineering`, `maintenance-retirement-engineering`.

**[R106] [Google SRE — Reliable Product Launches at Scale](https://sre.google/sre-book/reliable-product-launches/).** 2026-07-22 accessed. *Class A; Launch engineering; official engineering handbook.* Reliable launches depend on repeatable launch reviews, explicit risk criteria, capacity and dependency checks, monitoring, rollback, and organizational learning from prior launches. Operationalized as: Use a launch evidence package and progressive rollout contract, not calendar pressure or code completion, as the basis for production exposure. Affected skills: `secure-delivery-release`, `production-readiness-sre`, `architecture-delivery-planning`.

**[R107] [Google SRE Workbook — Canarying Releases](https://sre.google/workbook/canarying-releases/).** 2026-07-22 accessed. *Class A; Progressive delivery; official engineering handbook.* Canarying limits exposure while comparing a new version with a baseline and requires representative traffic, useful metrics, enough observation time, and automated or explicit rollback criteria. Operationalized as: Define cohorts, exposure steps, guardrails, analysis windows, hold/advance/revert rules, and effect containment for agent releases. Affected skills: `secure-delivery-release`, `continuous-product-experimentation`, `production-readiness-sre`.

**[R108] [Google SRE — Release Engineering](https://sre.google/sre-book/release-engineering/).** 2026-07-22 accessed. *Class A; Release engineering; official engineering handbook.* Reliable releases are reproducible, automated, self-service where safe, auditable, and built from well-defined source and build inputs. Operationalized as: Require deterministic release pipelines, artifact provenance, controlled permissions, repeatable rollback, and release evidence independent of a developer session. Affected skills: `secure-delivery-release`, `software-construction-quality`.

**[R109] [Google SRE — Testing for Reliability](https://sre.google/sre-book/testing-reliability/).** 2026-07-22 accessed. *Class A; Reliability testing; official engineering handbook.* Reliability requires layered tests including unit, integration, system, load, configuration, and failure-oriented testing; no single test class establishes production readiness. Operationalized as: Build a verification ladder aligned to quality attributes, dependencies, failure modes, rollout, and exact artifacts; record skipped or unavailable evidence honestly. Affected skills: `software-construction-quality`, `production-readiness-sre`, `rust-agent-verification`.

**[R110] [DORA — DORA metrics](https://dora.dev/guides/dora-metrics/).** 2026-07-22 accessed. *Class A; Delivery performance; official research program guidance.* Software delivery performance should be understood with a balanced set of throughput and stability measures, interpreted in context rather than optimized as isolated targets. Operationalized as: Track delivery flow and stability as diagnostics, avoid ranking teams or gaming a composite score, and connect measures to product outcomes and learning speed. Affected skills: `agentic-product-lifecycle`, `architecture-delivery-planning`, `software-construction-quality`, `production-readiness-sre`.

**[R111] [Google Cloud — 2025 DORA Report: AI-Assisted Software Development](https://cloud.google.com/resources/content/2025-dora-ai-assisted-software-development-report).** 2025-09-23. *Class B; AI-assisted software development; first-party research report.* AI assistance can amplify both strengths and weaknesses of a software delivery system; organizational capabilities, feedback quality, platform engineering, and control practices shape outcomes. Operationalized as: Treat agent use as a sociotechnical change, measure downstream flow and stability, and invest in repository, platform, evaluation, and feedback infrastructure rather than model access alone. Affected skills: `agentic-product-lifecycle`, `agent-first-software-engineering`, `software-construction-quality`.

**[R112] [Microsoft Azure Well-Architected Framework — Safe deployment practices](https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/safe-deployments).** 2026-07-22 accessed. *Class A; Safe deployment; official engineering guidance.* Safe deployment reduces blast radius through progressive exposure, health evaluation, bake time, rollback, separation of concerns, and deployment controls. Operationalized as: Require ringed rollout, stop/rollback criteria, health and business guardrails, ownership, and recovery evidence; do not confuse a feature flag with authorization. Affected skills: `secure-delivery-release`, `production-readiness-sre`, `continuous-product-experimentation`.

**[R113] [Argo Rollouts documentation](https://argo-rollouts.readthedocs.io/en/stable/).** 2026-07-22 accessed. *Class A; Progressive delivery; official project documentation.* Argo Rollouts supports canary and blue-green strategies, analysis runs, pauses, promotion, and rollback for Kubernetes workloads. Operationalized as: Treat rollout controllers as execution mechanisms under a predeclared evidence and authorization contract; keep product decisions outside controller defaults. Affected skills: `secure-delivery-release`, `production-readiness-sre`.

**[R114] [Flagger documentation](https://docs.flagger.app/).** 2026-07-22 accessed. *Class A; Progressive delivery; official project documentation.* Flagger automates progressive delivery using service-mesh or ingress traffic shifting, metrics, analysis, promotion, and rollback. Operationalized as: Use automated rollout only with trustworthy metrics, minimum exposure, explicit failure handling, and independent authorization for consequential effects. Affected skills: `secure-delivery-release`, `continuous-product-experimentation`.

**[R115] [OpenFeature — Evaluation Context specification](https://openfeature.dev/specification/sections/evaluation-context/).** 2026-07-22 accessed. *Class A; Feature evaluation context; official open specification.* Evaluation context carries targeting information through a feature-evaluation transaction and has defined merge precedence and lifecycle semantics. Operationalized as: Version rollout context, distinguish assignment from exposure, propagate stable non-sensitive identifiers, and record evaluated variant and reason with field evidence. Affected skills: `continuous-product-experimentation`, `secure-delivery-release`, `rust-agent-observability`.

**[R116] [OpenFeature — Evaluation Context concepts](https://openfeature.dev/docs/reference/concepts/evaluation-context/).** 2026-07-22 accessed. *Class A; Feature flag privacy; official project documentation.* Targeting context may contain sensitive information and should be minimized, protected, and handled consistently across providers and hooks. Operationalized as: Ban raw sensitive content from default rollout context, use allowlists and pseudonymous stable IDs, and document retention and access policy. Affected skills: `continuous-product-experimentation`, `rust-agent-observability`, `agent-security-governance`.

**[R117] [OpenFeature Rust SDK](https://openfeature.dev/docs/reference/sdks/server/rust/).** 2026-07-22 accessed. *Class A; Rust feature evaluation; official project documentation.* The Rust SDK provides a vendor-neutral feature-flag API with evaluation context, providers, hooks, and typed evaluation details. Operationalized as: Keep feature evaluation behind a Rust adapter, propagate context explicitly, expose reason/error details to telemetry, and do not treat flags as permission checks. Affected skills: `rust-agent-observability`, `secure-delivery-release`, `continuous-product-experimentation`.

**[R118] [tracing crate documentation](https://docs.rs/tracing/latest/tracing/).** 2026-07-22 accessed. *Class A; Rust instrumentation; official crate documentation.* Rust tracing models structured, contextual diagnostics as spans and events, supporting async-aware instrumentation and subscriber-based collection. Operationalized as: Instrument run/action/tool/effect/approval/recovery boundaries with stable domain IDs, propagate spans through owned tasks, and keep event fields structured. Affected skills: `rust-agent-observability`, `rust-agent-runtime`.

**[R119] [OpenTelemetry Rust documentation](https://opentelemetry.io/docs/languages/rust/).** 2026-07-22 accessed. *Class A; Rust observability; official project documentation.* OpenTelemetry Rust provides APIs and SDKs for traces, metrics, logs, context propagation, and export through vendor-neutral telemetry pipelines. Operationalized as: Use OTel at system boundaries, bridge tracing context intentionally, test propagation and shutdown/flush behavior, and preserve domain semantics independently of a backend. Affected skills: `rust-agent-observability`, `rust-agent-runtime`, `production-readiness-sre`.

**[R120] [OpenTelemetry — Observability primer](https://opentelemetry.io/docs/concepts/observability-primer/).** 2026-07-22 accessed. *Class A; Observability; official project documentation.* Observability is the ability to understand internal system state from outputs; instrumentation emits traces, metrics, and logs that serve different but complementary diagnostic purposes. Operationalized as: Design telemetry from decisions and failure mechanisms backward, with joinable signals and explicit diagnostic questions rather than indiscriminate logging. Affected skills: `rust-agent-observability`, `production-readiness-sre`, `authentic-use-engineering`.

**[R121] [OpenTelemetry — Handling sensitive data](https://opentelemetry.io/docs/security/handling-sensitive-data/).** 2026-01-14. *Class A; Telemetry privacy; official project security guidance.* Telemetry can capture personal, credential, financial, health, or behavioral data; implementers own minimization, consent, protection, redaction, and review. Operationalized as: Apply allowlists, privacy classifications, redaction, bounded retention, access controls, and sampling policies; do not record raw prompts or tool payloads by default. Affected skills: `rust-agent-observability`, `authentic-use-engineering`, `agent-security-governance`.

**[R122] [OpenTelemetry — GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/).** 2026-07-22 accessed. *Class A; Generative-AI telemetry; official open specification.* GenAI semantic conventions define evolving common attributes and events for model, agent, and tool telemetry, with stability levels and privacy implications that require review. Operationalized as: Adopt stable conventions selectively, namespace product-specific domain fields, version schemas, and avoid relying on experimental attributes as immutable contracts. Affected skills: `rust-agent-observability`, `agent-evals-observability`, `authentic-use-engineering`.

**[R123] [W3C Trace Context Recommendation](https://www.w3.org/TR/trace-context/).** 2021-11-23. *Class A; Distributed tracing; web standard.* Trace Context standardizes propagation of trace identifiers and flags across process and service boundaries while defining interoperability and privacy considerations. Operationalized as: Propagate W3C context across agent services and tools, but keep trace identity separate from authorization and from durable business/effect identity. Affected skills: `rust-agent-observability`, `harness-engineering`, `production-readiness-sre`.

**[R124] [OWASP — AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html).** 2026-07-22 accessed. *Class A; Agent security; official security guidance.* Agent systems face prompt injection, excessive agency, tool abuse, memory poisoning, data leakage, unsafe output handling, and denial-of-service risks that require layered controls. Operationalized as: Carry security constraints into authentic-use operating envelopes, tool contracts, telemetry, approvals, effect integrity, incident response, and release gates. Affected skills: `agent-security-governance`, `authentic-use-engineering`, `secure-delivery-release`, `production-readiness-sre`.

**[R125] [OWASP — Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/).** 2026. *Class A; Agentic risk taxonomy; official community standard.* Agentic applications introduce risks around goals, identity and privilege, tool use, memory and context, inter-agent trust, cascading failures, and insufficient monitoring or governance. Operationalized as: Use the taxonomy as threat-model prompts and coverage checks, not a substitute for system-specific assets, trust boundaries, misuse cases, and effect analysis. Affected skills: `agent-security-governance`, `secure-delivery-release`, `authentic-use-engineering`, `agentic-product-lifecycle`.

---

# Agentic Engineering 3.0 Research Addendum

**Research lock:** July 22, 2026, America/Los_Angeles  
**Scope:** Evidence added after Agentic Engineering 2.0 and the UltraGoal, Compound Engineering, and Superpowers comparison.

## Executive decision

Version 3 retains the original control-architecture and full-lifecycle model, but changes how the plugin activates, learns, verifies, repairs, coordinates, and judges product value.

The upgrade operationalizes nine decisions:

1. **One implicit front door.** Specialist skills remain explicit. The release gate estimates the complete discovery payload and stays below a conservative limit because Codex may shorten or omit skills when the initial list crowds the prompt.
2. **No-change is a successful result.** A request to fix software does not prove a defect still exists. Current behavior must be reproduced, and `no_change`, `partial_change`, `change_required`, and `blocked` are distinct outcomes.
3. **Verification is selected, not ritualized.** TDD remains valuable where observing a test fail proves the oracle, but characterization, property, state-machine, differential, mutation, concurrency, browser, effect, rollout, or field evidence may be more appropriate.
4. **Repair loops are budgeted experiments.** Each attempt changes one material mechanism or gains new evidence. Structured feedback records failure location, observed value, and admissible alternatives. Repeated mechanisms trip a semantic circuit breaker.
5. **Skills are behavior-tested.** Explicit, implicit, contextual, negative, overlap, no-change, and adversarial cases are compared with a baseline. Consequential skills add held-out, mutation, and specification-evolution evaluation.
6. **Workers and reviewers exchange typed evidence.** A root-owned Task Evidence Packet defines identity, ownership, permissions, budgets, and verification. A Review Verdict is candidate-bound and cannot independently promote claims.
7. **Observed outcomes enter a governed learning loop.** Facts, interpretations, and mechanism hypotheses remain separate. One learning record produces the smallest intervention, held-out validation, authority handoff, freshness, supersession, and retirement.
8. **Product Fitness measures value and supervisory work.** Field Pulse and Product Journey Review complement controlled exposure by measuring representative outcomes, intervention, recovery, cognitive load, and continuance without confusing activity or telemetry with fit.
9. **Security continuously adapts.** Identity, authorization, containment, red-team discovery, monitored deployment, updates, and recovery replace the assumption that a fixed guardrail set permanently proves robustness.

## Evidence synthesis

### Leaner routing and configuration

OpenAI’s current skill documentation describes progressive disclosure and a bounded initial skill list. GPT-5.6 guidance reports directional internal evidence that leaner system prompts improved coding-agent scores while substantially reducing tokens and cost, and advises choosing Programmatic Tool Calling, multi-agent, Pro, and reasoning settings by task shape and representative evaluation. This supports a stable outcome contract, one host-owned implicit gateway, concise trigger-only descriptions, explicit specialists, and configuration changes instead of multiple prompting dialects.

### Appropriate inaction

FixedBench evaluates already-resolved software requests and reports substantial action bias across contemporary models and harnesses. Reproduction instructions help but can create false abstention on partially fixed cases. The plugin therefore makes current-behavior reproduction and four-way change disposition first-class, then evaluates both unnecessary action and premature abstention.

### Repair-loop proportionality

A July 2026 empirical study found most gains in examined repair workflows within the first three to four iterations and emphasized orchestration and feedback design. A paired study found large improvements from feedback that exposed location, observed value, and admissible alternatives. The plugin does not hardcode three attempts; it makes budget an evaluated project parameter and adds a semantic stop when the mechanism repeats without new evidence.

### Contextual verification over procedural ritual

TDAD reports that code–test impact context reduced regressions in its studied configurations, while TDD prompting alone increased them. TDDev reports that browser acceptance infrastructure improved web-app generation but that mismatching enforcement protocol to model behavior erased benefit and multiplied cost. An empirical repository study finds agent-generated tests more likely to add mocks. Together these results support a Verification Mode Contract, explicit oracle and mock policy, and representative same-surface evidence rather than universal TDD.

### Anti-gaming skill evaluation

OpenAI’s skill-evaluation guidance calls for explicit, implicit, contextual, and negative cases with JSONL trajectory and artifact grading. Test-Driven AI Agent Definition adds visible/hidden splits, semantic mutation, and specification evolution. Version 3 combines these into an evaluation ladder that measures activation, following, composition, recovery, verified outcome, authority, safety, and efficiency.

### Layer-aware learning and knowledge lifecycle

HarnessFix reports held-out improvements from normalizing failed traces, localizing the responsible step and harness layer, clustering recurring flaws, and applying scoped repair operators. Compound Engineering demonstrates the value of capturing one durable learning at a time, while OpenAI’s harness account emphasizes feeding repeated failures back into tools, guardrails, documentation, and repository structure. Version 3 adopts the compounding mechanism but retains one authoritative registry, generated projections, and explicit freshness/supersession/retirement.

### Human and product outcomes

DORA’s current AI guidance emphasizes user-centricity, small batches, and AI-accessible internal evidence. Longitudinal and mixed-method studies identify supervisory engineering—direction, evaluation, and correction—as a growing category of work and show that perceived productivity can coexist with worse flow or cognitive load. A 2026 meta-analysis finds moderate but heterogeneous productivity benefits and no significant overall learning effect. Product Fitness therefore measures value, intervention, verification burden, ownership, recovery, and continuance rather than code volume, token use, or agent activity alone.

### Continuous agent security

NIST’s 2026 agent initiative and identity work emphasize interoperable standards, explicit identity, authorization, and secure adoption. NIST’s continuous-monitor-and-update research argues that no finite fixed guardrail set can be universally robust against adaptive adversarial prompts. Version 3 retains mandatory security boundaries and adds continuous red-team discovery, monitored deployment, updates, containment, and recovery.

## What Version 3 deliberately does not adopt

- a mandatory skill invocation whenever there is a remote possibility of relevance;
- brainstorming or approval gates for every small change;
- TDD as the only legitimate verification method;
- fresh subagent plus multiple reviewers for every task;
- unlimited review/fix loops;
- a second lifecycle, goal, plan, evidence, or knowledge authority beside the host system;
- token reduction, command count, reviewer consensus, or telemetry presence as standalone success metrics;
- product-fit claims from agent use, installation, one journey, or aggregate activity.

## Residual uncertainty

The package includes deterministic structural, schema, routing, evidence, context-budget, and static Rust checks. This environment does not provide a live Codex executable or Rust toolchain, so the blind GPT-5.6 Sol A/B, behavior evals, compile checks, and real Product Fitness pilot remain downstream protocols. The confidence score therefore reflects evidence quality, mechanism specificity, static validity, and falsifiability—not a measured probability of improvement on every repository.


## Version 3 source traceability

- Codex progressive disclosure, skill discovery, behavior evaluation, and lean GPT-5.6 orchestration: [R126] [R127] [R128].
- Compound Engineering and Superpowers mechanisms and limitations: [R129] [R130].
- User-centricity, small batches, internal evidence, and supervisory engineering: [R131] [R132] [R133] [R134].
- No-change/action bias and bounded repair-loop evidence: [R135] [R136] [R137] [R138].
- Contextual verification, hidden/mutation/evolution evaluation, browser acceptance, and mock quality: [R139] [R140] [R141] [R142].
- File-backed context, longitudinal developer experience, human-centered collaboration, and heterogeneous productivity effects: [R143] [R144] [R145] [R146].
- Agent standards, continuous security, measurement probes, identity/authority, and secure lifecycle practice: [R147] [R148] [R149] [R150] [R151].
