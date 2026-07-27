# No-Change and Abstention

Action is not the only successful outcome.

Before modifying software for a reported issue:

1. reproduce the stated failure on the current candidate and intended surface;
2. inspect whether the issue is fully fixed, partially fixed, environment-specific, stale, or still present;
3. distinguish missing evidence from evidence that no change is needed;
4. return one disposition: `no_change`, `partial_change`, `change_required`, or `blocked`;
5. support the disposition with current evidence and identify any documentation, test, or monitoring work that remains justified.

Do not make a cosmetic or speculative edit merely to demonstrate activity. Conversely, do not abstain when only part of the requirement is satisfied. Treat `NoChangeDecision` as a first-class artifact and evaluate agents on appropriate inaction.

Evidence basis: R135.
