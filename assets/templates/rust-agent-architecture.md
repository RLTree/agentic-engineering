# Rust Agent Architecture

## Domain outcome and invariants

## Workspace/modules and dependency direction

## Typed domain state, decisions, effects, and transitions

## Ports and adapters
| Port | Semantic contract | Adapter(s) | Cancellation/deadline | Error/effect semantics |
|---|---|---|---|---|

## Tokio runtime tree
- task ownership:
- bounded queues/semaphores:
- cancellation/deadlines:
- supervision:
- graceful shutdown:

## Durability and effect journal

## MCP/A2A or other protocol boundaries

## Security/capabilities/approval

## Observability and evidence

## Verification matrix
- fmt/check/test/clippy/release:
- features/targets/MSRV:
- concurrency/fault/replay:
- protocol/adapter contracts:
- supply chain/exact artifact:

## Decisions and residual risks
