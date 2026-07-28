# Assumption and risk map

Map the beliefs that must be true for the product to create value and operate responsibly. Rank evidence work by the product of consequence, uncertainty, irreversibility, dependency, and time-to-learn—not by which prototype is easiest to demo.

## Vocabulary
- **assumption:** A proposition currently treated as true without sufficient evidence.
- **risk:** Potential consequence of uncertainty on value, safety, delivery, operations, or lifecycle continuity.
- **critical assumption:** An assumption whose failure would invalidate the concept, architecture, or investment.
- **discriminating test:** The least expensive observation likely to separate viable from non-viable explanations.
- **option value:** Benefit of delaying an irreversible commitment while gathering evidence.

## Decision procedure
1. Inventory assumptions across desirability, workflow/adoption, model capability, data, tools/effects, security/privacy, legal/policy, integration, performance/cost, reliability, operations, organization, and retirement.
2. For each, estimate consequence, uncertainty, irreversibility, coupling, detectability, and evidence latency; label existing evidence and provenance.
3. Identify assumption chains where one belief depends on another; avoid testing a downstream feature before a prerequisite.
4. Choose the smallest discriminating prototype, spike, observation, analysis, or controlled exposure for the top risks.
5. Define pass/partial/fail and stop/pivot conditions before running the test; update the map after results.

## Decision table

| Risk pattern | Preferred evidence | Avoid |
|---|---|---|
| Unknown user/workflow value | Observation and prototype in context | Technical benchmark first |
| Unknown model/tool capability | Representative task set and failure taxonomy | Curated demo |
| Unknown integration/performance | Executable spike with real interfaces/load | Architecture diagram only |
| Unknown safety/authorization | Threat/effect analysis plus controlled tests | Broad autonomous pilot |

## Evidence obligations
- Every high-ranked assumption has an owner, evidence plan, decision date, and downstream commitments it blocks.
- Evidence states the operating conditions and versions exercised.
- Negative or mixed results update scope and architecture; they are not reclassified as “learning” while investment continues unchanged.
- Retirement, vendor dependency, and operational burden assumptions enter the map early.

## Review questions
1. Which belief would make the whole concept unwise if false?
2. What test can fail quickly without building the product?
3. Are we testing the riskiest assumption or the most visually impressive one?
4. What irreversible choice can remain open until better evidence exists?

## Failure patterns
- Prototype momentum: a successful demo becomes product approval.
- Risk register theater: risks listed without discriminating evidence or decision consequences.
- Assumption nesting: a test depends on multiple unverified conditions and yields ambiguous results.

## Research basis

Grounded in lifecycle validation, discovery, quality-attribute and architecture risk methods, and deployed-agent evidence [R77] [R88] [R89] [R90] [R91].
