# SLO and error budget

SLOs translate user-visible reliability and quality into operating decisions. Agentic products need service, outcome, effect-safety, and human-work indicators; a technically available model call can still produce an unusable or unsafe service.

## Vocabulary
- **SLI:** Quantitative measure of a service behavior over a defined population/window.
- **SLO:** Target for an SLI with scope, threshold and period.
- **error budget:** Allowed unreliability: one minus the SLO, used to balance change and reliability.
- **burn rate:** Rate at which error budget is consumed relative to the window.
- **quality SLI:** Measure of task outcome, accepted result, correction, safety or verified effect—not only infrastructure response.

## Decision procedure
1. Identify critical user journeys and consequential agent/effect paths; define what “good” means from the user/operator perspective.
2. Select a small set of SLIs for availability, latency, task/outcome quality, tool/effect success/ambiguity, freshness, safety and human review burden as relevant.
3. Specify population, event, good/valid criteria, window, target, exclusions, data quality and segmentation.
4. Set error-budget policy: alerting/burn rates, release/ramp decisions, reliability work, incident review and exception authority.
5. Validate indicators against representative traces and user outcomes; prevent easy gaming or missing-case exclusion.
6. Review targets as product, workload, autonomy and consequences evolve.

## Decision table

| Journey | Possible SLI | Caution |
|---|---|---|
| Recommendation | accepted/correct with bounded review time | acceptance may reflect blind trust |
| Tool action | confirmed correct effect / valid attempts | exclude ambiguous outcome carefully |
| Agent task | verified outcome within deadline/cost | avoid model self-report |
| Recovery | restored state without duplicate effect | include silent corruption |
| Service | successful useful responses | HTTP 200 is insufficient |

## Evidence obligations
- Invalid/missing telemetry is measured separately and cannot improve the SLI by disappearing failures.
- SLOs are segmented for high-risk tasks and affected cohorts where averages would hide harm.
- Error budgets influence rollout and engineering priority; they are not reporting-only.
- Safety or security hard limits may override an available error budget.

## Review questions
1. Does this indicator reflect user/system value or merely component activity?
2. Can the agent game the denominator, abstain, or hide missing events?
3. What release decision follows budget burn?
4. Which severe event is unacceptable even if the monthly target passes?

## Failure patterns
- Availability-only SRE: useful/correct/effect-safe outcomes omitted.
- Vanity SLO: target chosen because current system already passes.
- Error budget without policy: no consequence for burning it.

## Research basis

Based on Google SRE SLO/error-budget practice and agent outcome/effect evaluation [R72] [R103].
