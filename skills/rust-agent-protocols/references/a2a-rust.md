# A2A in Rust

Use an agent-to-agent protocol when independently operated agents need capability discovery, task lifecycle, messages/artifacts and long-running coordination. Do not use A2A merely for internal function calls that a typed service API or queue handles more simply.

## Boundary distinction

MCP primarily connects a model/agent to tools, resources and prompts. A2A connects peer agents/services that own their own reasoning and task lifecycle. A system may use both, but keep trust and identity boundaries distinct.

## Rust architecture

Place A2A wire types and SDK integration in an adapter crate. Convert agent cards/capabilities, task IDs/status, messages, parts and artifacts into internal typed contracts. Persist the mapping between external task ID and internal run/task ID.

## Agent card/capability discovery

Treat remote metadata as untrusted. Pin or allowlist endpoints/identities, validate signatures/transport, bound capabilities and do not grant local privilege based solely on advertised skills.

## Task lifecycle

Map submitted/running/input-required/completed/failed/cancelled (according to the current protocol version) to internal lifecycle explicitly. Define cancellation propagation, retry/reconnect, artifact integrity, message ordering and timeout behavior. Long waits require durable internal state.

## Security

Authenticate both sides, authorize task type/data/effects, classify transmitted content, redact traces and limit delegation depth. A remote agent cannot claim human approval or expand the caller’s capabilities without verifiable authority.

## Testing

Official SDK/spec conformance, version negotiation, unknown capability, duplicate task submission, reconnect/resume, cancellation race, malformed artifact, remote prompt injection, partial failure, identity mismatch and interop with at least one independent implementation.

## Adoption test

A2A should reduce custom coordination code or enable a real organizational boundary. Otherwise prefer a simpler internal API with the same typed task/evidence contract.
