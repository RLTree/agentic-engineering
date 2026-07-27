# Run No-Change and Repair-Budget Study

Use a frozen set containing unresolved, partially resolved, fully resolved, environment-specific, and irreproducible requests.

Measure:

- correct `no_change`, `partial_change`, `change_required`, and `blocked` decisions;
- undesirable code changes on no-change tasks;
- false abstention on partially resolved tasks;
- repair success by attempt number;
- repeated mechanism attempts without new evidence;
- quality of validator feedback;
- tokens, turns, time, commands, and side effects.

Compare at least two repair budgets and raw versus structured feedback. The study determines project defaults; the plugin does not hardcode “three” as a universal budget.
