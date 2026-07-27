# Protocol conformance and evolution

Interoperability requires more than compiling against an SDK. Test the behavior and wire contract against the supported protocol versions and independent peers.

## Conformance layers

1. transport framing, content types and cancellation;
2. initialization/version/capability negotiation;
3. JSON Schema/wire serialization and error shapes;
4. method/tool/task lifecycle semantics;
5. authentication/authorization and tenant isolation;
6. size, pagination, ordering, streaming and backpressure;
7. retries, duplicate IDs, reconnect and idempotency;
8. security/adversarial payloads;
9. observability and correlation IDs;
10. backward/forward compatibility.

## Test corpus

Store valid and invalid wire fixtures with protocol version. Include unknown fields/methods, missing required data, duplicate requests, out-of-order messages, cancellation at each phase, oversized payload, Unicode/escaping, malicious URLs/paths/markup, stale versions and server restart.

## Independent interoperability

Run against the official test suite if available and at least one independent implementation. Capture exact versions and negotiated capabilities. A test using only the same SDK on both ends can reproduce the same bug.

## Compatibility policy

Declare supported versions, deprecation window, feature negotiation, unknown-field behavior and breaking-change process. Pin dependencies while allowing security updates through reviewed lockfile changes.

## Failure mapping

Convert protocol errors into internal typed errors without losing remote code/request ID/effect ambiguity. Never treat a transport disconnect as proof that an external action failed.

## Release evidence

Schema diff, fixture results, interop matrix, security cases, load/backpressure results and known deviations. Mark untested version/transport combinations explicitly.
