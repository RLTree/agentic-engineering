# Rust runtime fault matrix

Use this matrix to turn async failure modes into executable tests and operational decisions.

| Fault | Injection point | Expected behavior | Evidence |
|---|---|---|---|
| Queue saturation | before enqueue/permit | wait/reject/shed per policy; bounded memory | queue metrics, typed error |
| Receiver closed | send/response channel | owner sees failure; run transitions safely | trace + terminal/repair state |
| Caller cancellation | every await boundary | no new action; owned children cancel/drain | task tracker empty |
| Deadline | queue/connect/stream/verify | typed phase; effect ambiguity reconciled | error + journal |
| Child panic | spawned node/tool task | JoinError observed; containment policy | panic trace, run state |
| Slow/blocking code | core worker | isolated/limited; watchdog signal | runtime latency metrics |
| Lock contention | state/update path | bounded wait/no lock across external await | timeout/test instrumentation |
| Dependency outage | model/tool/store | backoff/circuit/fallback/escalate | attempt budget, state |
| Crash before dispatch | journaled intent | safe resume/retry by action ID | journal status |
| Crash after remote success | before result record | reconcile; no duplicate | external lookup + journal |
| Checkpoint failure | state transition | do not claim durable progress; contain/retry | store error, old version |
| Telemetry failure | emit/flush | bounded degradation; core path policy explicit | dropped count |
| Shutdown | all phases | quiesce/cancel/drain/reconcile by deadline | shutdown report |
| Clock jump | deadlines/leases | monotonic time for durations; lease validation | deterministic clock test |

## Test harness

Use dependency fakes with programmable barriers and fault points, a deterministic or paused clock, bounded channels, and trace capture. Give tests a hard outer timeout so deadlocks fail instead of hanging CI.

## Leak checks

After each scenario assert task tracker empty, permits restored, channels closed as expected, temporary resources removed, no unrecorded external effect, and terminal/checkpoint state consistent.

## Production signals

Alert on stuck task age, queue oldest age, runaway retries, dirty shutdown, ambiguous effects, checkpoint lag, panic rate and cancellation latency—not only process uptime.
