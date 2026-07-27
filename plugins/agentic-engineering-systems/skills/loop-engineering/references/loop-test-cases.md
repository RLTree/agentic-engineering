# Loop test cases

Test loops as trajectories through state and evidence, not only by final text. Use deterministic fake tools where possible and preserve traces for grading.

## Core scenarios

1. **Immediate success:** first action satisfies oracle; loop stops without extra work.
2. **Recoverable transient:** pre-dispatch timeout retries once under policy and succeeds.
3. **Invalid action:** schema/semantic error causes repair, not unchanged retry.
4. **Stale state:** conflict triggers refresh and replan.
5. **Verification regression:** new artifact scores worse; best-so-far remains authoritative.
6. **Repeated semantic action:** paraphrased duplicate is detected and strategy changes/stops.
7. **Ambiguous external effect:** timeout after dispatch triggers reconciliation before any repeat.
8. **Permission denial:** loop does not route around policy; it escalates or chooses a safe alternative.
9. **Budget exhaustion:** checkpoint and honest partial handoff occur before hard limit.
10. **Cancellation during await:** no new action starts; in-flight effect is reconciled; tasks drain.
11. **Contradictory evidence:** provenance is compared and uncertainty remains explicit.
12. **Human interrupt/resume:** state survives, pre-interrupt work is not duplicated.

## Assertions

For each scenario assert:

- terminal state and reason;
- semantic action sequence;
- budget accounting;
- state versions/checkpoints;
- effect journal entries;
- policy/approval decisions;
- acceptance evidence;
- absence of forbidden actions;
- no task/effect left unowned.

## Property checks

- success implies every required criterion has evidence;
- action count never exceeds budget;
- identical action ID cannot produce duplicate journal completion;
- state version increases monotonically;
- cancellation prevents subsequent dispatch;
- irreversible effects never occur without required approval;
- trace and state share stable correlation IDs.

## Grading

Separate outcome, trajectory, recovery, and safety scores. A loop that reaches the right answer through unsafe or wasteful behavior should fail trajectory or safety even when outcome passes.
