# Agent threat model

Model the agent as a privileged interpreter of mixed-trust inputs. The principal risk is not only malicious model output; it is the composition of untrusted content, broad capabilities, persistent state and automated effects.

## Assets

Protect credentials and capability tokens; source code and proprietary context; user/private data; model/system instructions; run state and memory; external accounts/resources; deployment and supply-chain integrity; traces and audit evidence; and human trust in approval surfaces.

## Actors and trust zones

- user/requesting principal;
- model and model provider;
- harness/control plane;
- tool/MCP/A2A servers;
- sandbox/worker;
- retrieved documents/web/repository content;
- durable stores and message queues;
- external services;
- human approver/operator.

Draw data and control flows. Label identity, authentication, authorization, encryption, persistence, data classification and provenance at each boundary.

## Threat categories

1. **Instruction injection and control confusion:** untrusted text attempts to override policy or redirect tools.
2. **Excessive agency:** the run has more capability, scope, duration or autonomy than the objective requires.
3. **Tool/protocol abuse:** misleading descriptions, schema tricks, output injection, target substitution, SSRF, path traversal or command injection.
4. **Data leakage:** context, traces, model calls or worker artifacts expose sensitive information.
5. **State/memory poisoning:** false or malicious facts persist and influence later runs.
6. **Effect integrity:** duplicate, unauthorized, ambiguous or incorrectly targeted external actions.
7. **Coordination attacks:** a worker impersonates authority, expands delegation or poisons shared state/fan-in.
8. **Availability/cost:** unbounded loops, queues, fan-out, retries or adversarial tool output exhaust resources.
9. **Supply chain:** compromised dependencies, plugins, MCP servers, generated code or build inputs.
10. **Audit evasion:** missing IDs, altered evidence, redaction gaps or untraceable approval/effect.

## Controls

Use provenance labels and instruction/data separation; least-privilege capability grants; schema validation and semantic target normalization; risk-based approval; bounded context/output/loops/concurrency; sandbox plus independent authorization; stable action IDs and effect journal; checkpoint integrity and state versioning; dependency pinning/scanning; trace redaction; kill switch and incident response.

## Abuse cases

For each threat write attacker goal, preconditions, attack path, affected assets, preventive/detective/recovery controls, residual risk and test. Include benign failures that create the same hazard, such as stale state causing a wrong target.

## Release gate

Block release when an irreversible/high-impact effect lacks authorization/idempotency/reconciliation, untrusted content can modify policy, sensitive data has no classification/redaction, or incident containment cannot stop further effects.
