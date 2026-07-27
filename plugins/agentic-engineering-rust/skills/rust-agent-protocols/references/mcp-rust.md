# MCP in Rust

Use MCP for agent-to-tool/resource/prompt integration when interoperability is valuable. Treat the MCP server as a security boundary and adapter, not as the owner of application policy.

## Implementation shape

```text
MCP transport/session
  -> protocol request validation
  -> authenticated principal/capability context
  -> tool/resource registry
  -> application use case
  -> structured bounded result
```

The official MCP ecosystem includes a Rust SDK. Verify the current SDK/spec version and transport features at implementation time; pin compatible versions and test protocol negotiation.

## Tool contracts

Publish precise input/output JSON Schemas, semantic descriptions, side-effect and approval expectations. Tool annotations are hints and may be untrusted; authorization remains server-side. Keep stable tool names and version breaking changes explicitly.

## Security

Authenticate transport or gateway as appropriate. Authorize each operation/target, validate inputs, rate-limit, bound output, sanitize content, redact logs and apply deadlines. Protect against path traversal, SSRF, command injection, tenant confusion and tool-result prompt injection. Do not expose ambient process credentials to all tools.

## Human visibility

Clients should show which tool is invoked and confirm consequential operations. Return normalized intent/effect metadata so approval surfaces are accurate.

## Lifecycle

Handle initialize/capability negotiation, cancellation, disconnect, backpressure and shutdown. Decide whether in-flight effects continue after client disconnect and record them through the effect journal.

## Testing

Protocol conformance, schema compatibility, unknown method/tool, malformed/cancelled request, concurrent sessions, capability mismatch, auth/tenant boundaries, output injection, large results, timeout after dispatch and client reconnect.

## Architecture rule

MCP DTOs stay in the adapter crate. Convert to domain/application types immediately so protocol evolution does not permeate the system.
