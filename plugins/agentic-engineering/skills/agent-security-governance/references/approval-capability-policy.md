# Approval and capability policy

Authorization and approval are different. Authorization defines what an identity may do; approval supplies informed consent for a specific consequence. Neither should be delegated to the model.

## Capability tuple

Represent grants as:

```text
(subject, operation, target, environment, data class, effect class,
 constraints, issued_by, issued_at, expires_at, delegation_depth)
```

Use allowlists and short duration. Separate read/write/admin and development/staging/production. A sandbox grant does not imply network, account or production authorization.

## Approval classes

- **None:** read-only, low-sensitivity, bounded operations already within task authority.
- **Batch:** homogeneous reversible local changes with visible target list.
- **Per action:** external communication, deployment, production mutation, permission/data-boundary change, material cost or difficult rollback.
- **Two-person/independent:** high-impact security, finance, deletion, policy or safety decisions.
- **Prohibited:** actions outside product/system policy regardless of user request.

## Approval surface

Show normalized action, actor, exact target/environment, inputs or diff, expected result, side effects, reversibility/rollback, data shared, cost/blast radius, evidence, alternatives, expiration and what is not being approved. Protect against target substitution between approval and dispatch with hashes/version checks.

## Delegation

A worker cannot widen the parent’s grant. Derive narrower child capabilities and limit delegation depth. Parent remains responsible for integration and must not accept a worker’s claim that approval was obtained without a verifiable reference.

## Denial behavior

On denial, stop the effect path, preserve state/evidence, offer a lower-risk alternative if valid, and never route around the policy through another tool or agent. Treat repeated attempts as a security signal.

## Tests

Wrong environment/target, expired grant, stale approval, changed arguments after approval, batched mixed-risk actions, delegated privilege expansion, output injection, duplicate dispatch and cancellation after approval but before effect.
