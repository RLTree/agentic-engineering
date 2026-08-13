---
name: design-transaction
description: Use when building a conventional multi-step form, checkout, request, application, booking, payment, or other commitment flow.
---

# Conventional Transaction

Use familiar controls and make the commitment boundary unmistakable.

Build this lifecycle:

```text
orient → collect → preserve work → validate → review and edit → commit → truthful receipt
```

- Show current step, remaining scope, and what the user needs before starting.
- Preserve entered work across validation, back navigation, and recoverable failure.
- Validate near the relevant field without blocking unrelated progress prematurely.
- Make domain choices explicit; do not hide consequential options behind defaults.
- Provide a real review state with edit paths before commitment.
- Name the consequence on the final action. Never let “Continue” conceal purchase, submission, deletion, or authorization.
- After commitment, state exactly what happened, what did not happen, identifiers or totals, and the next available action.
- Support cancellation, correction, and retry where the product permits them.
- Keep touch, keyboard, focus, error, and narrow-width paths comfortably operable.

Expression belongs in copy precision, product content, and calm detail. Do not make a routine transaction unfamiliar merely to appear original.