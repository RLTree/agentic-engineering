# Sustainment, debt, and dependencies

Sustainment manages continued product value and system health across corrective, adaptive, perfective, preventive, security, model/eval, data and operational work. Debt is prioritized by risk and option loss, not aesthetic discomfort.

## Vocabulary
- **corrective maintenance:** Repair of observed defects or incidents.
- **adaptive maintenance:** Change required by environment, provider, platform, policy, workload or dependency evolution.
- **perfective maintenance:** Improvement to value, performance, usability or maintainability.
- **preventive maintenance:** Work reducing future failure or change cost.
- **lifecycle debt:** Deferred obligation that increases risk, cost, coupling or loss of future options.

## Decision procedure
1. Review continuing user need, task distribution, outcome quality, reliability/SLOs, security/privacy, support and operator burden, cost, model/tool drift, dependencies and alternatives.
2. Inventory debt and maintenance items with origin, affected claims, consequence, recurrence, detectability, effort, deadline/expiry and owner.
3. Classify and prioritize by user/system risk, error budget, vulnerability, dependency end-of-life, migration lead time and option value.
4. Define health metrics and thresholds for invest, contain, replace, deprecate or retire.
5. Deliver small verified maintenance slices; update compatibility, baselines, field monitors and retirement obligations.
6. Periodically remove stale flags, paths, prompts/skills, models, tools, data, dashboards, permissions and documents.

## Decision table

| Signal | Likely action | Do not |
|---|---|---|
| Recurring incident mechanism | systemic correction | patch symptoms repeatedly |
| Dependency EOL/security issue | upgrade/replace with migration | wait for forced outage |
| Low value, high support cost | deprecate/retire analysis | hide in backlog |
| Model/eval drift | refresh evidence/envelope | assume benchmark permanence |

## Evidence obligations
- Maintenance decisions link to current field/operational evidence and affected users.
- Dependency inventory includes models, tools, protocols, data and vendors—not only libraries.
- Debt items have exit criteria; “temporary” paths expire.
- Reliability/security work is not indefinitely displaced by feature throughput.

## Review questions
1. Does this capability still earn its complexity and risk?
2. Which deferred obligation is closing future options fastest?
3. What dependency change will force action with the longest lead time?
4. What can be removed safely now?

## Failure patterns
- Backlog landfill: no health signal or decision threshold.
- Feature monopoly: all capacity goes to visible additions.
- Model permanence: behavior and evidence assumed stable across version drift.

## Research basis

Grounded in lifecycle maintenance, SRE error budgets, secure dependency management, and DORA operating evidence [R83] [R95] [R103] [R110].
