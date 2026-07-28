# Browser, Field, and Effect Verification

Source inspection cannot prove a user-visible journey or an external effect.

For browser or device work, derive scenarios from complete flows: entry, action, branch, side effect, destination, error, recovery, and retained state. Bind screenshots or recordings to the exact build and scenario; they are evidence pointers, not self-validating proof.

For external effects, verify prepared, dispatched, confirmed, ambiguous, reconciled, and compensated states. A timeout is not evidence that an effect failed. Never redispatch an ambiguous effect without reconciliation or an idempotency contract.

Field evidence requires an operating envelope, exposure/assignment integrity, privacy policy, severe-event stop rule, and a claim ceiling.

Evidence basis: R130, R141, R147.
