# Issue-to-artifact protocol

Treat the work item as a control-plane object and the durable artifact as the unit of value. The conversation is an execution trace, not the deliverable.

## Intake

Normalize issue into objective, current/desired behavior, constraints, anti-goals, acceptance criteria, risk/approval class and exact artifacts. Link authoritative repository evidence and decisions.

## Plan

Choose smallest fitting architecture for the work itself: direct change, deterministic workflow, bounded exploration loop, or parallel packages. Create dependency-aware tasks with owners and verification.

## Execute

Work in an isolated branch/worktree/environment. Keep changes scoped, preserve public contracts, update tests/docs/ADRs with code, and record decisions/evidence in durable files. Use tools under least privilege.

## Verify

Map each criterion to evidence. Run fast checks during work, then full relevant checks on the exact commit/package/binary/site. Review diff, migrations, generated files, security, performance and operational behavior. Use a fresh review pass for consequential changes.

## Publish

Produce the artifact: branch/PR, package, deployment candidate, report, dataset, migration or decision record. Include digest/commit, files changed, commands and results, screenshots/traces where relevant, assumptions and residual risks.

## Close

Update issue with decision-ready summary and evidence links; resolve or explicitly defer criteria; clean workers/worktrees; reconcile side effects; and promote recurring corrections to repository infrastructure.

## Anti-patterns

“Implemented” without exact artifact; local source checks but packaged output untested; issue scope silently expanded; chat contains the only rationale; worker branch unintegrated; or success declared while approval/effect remains ambiguous.
