---
name: design-agentic-authority
description: Use when an interface proposes, authorizes, executes, interrupts, recovers, or explains AI-assisted actions with meaningful user or external consequences.
---

# Agentic Authority and Recovery

The current user decision outranks trace spectacle.

Separate:

```text
suggested → drafted → approved → running → partially completed → completed | failed | cancelled → user confirmed
```

Show three different truths:

1. **Capability:** what the system can and cannot do.
2. **Reliability:** missing inputs, uncertainty, stale sources, and known limitations.
3. **Explanation:** why this proposal appeared and which inputs supported it.

For every consequential action provide the appropriate combination of edit, correct, dismiss, approve, pause, cancel, retry, undo, safe exit, and restoration of the original suggestion. Preview external effects before execution. Never use confidence language to hide missing evidence.

Partial completion, stale plans, conflict, interrupted tools, and recovery are primary product states. A durable receipt says what changed, what did not change, what failed, and what risk remains.

Keep intervention controls visible and comfortably operable. Trace, rationale, and provenance remain inspectable but must not push the present decision below history. Reassurance copy does not count as control.