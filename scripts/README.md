# Validation and Release Scripts

Every script accepts `--write` and stores a machine-readable report under `evals/results/`.

| Script | Gate |
|---|---|
| `validate_plugin.py` | marketplace, manifest, 30 skills, frontmatter, local references, no internal implicit gateway, docs, and privilege floor |
| `validate_official_contract.py` | Codex progressive disclosure, concise trigger-only descriptions, and specialist isolation |
| `audit_links.py` | local Markdown links and path safety |
| `evaluate_coverage.py` | 90 scenarios, 30 capability maps, 143 routes, references, and source IDs |
| `evaluate_behavior_contracts.py` | one global and 30 per-skill deliverable/required/forbidden/evidence contracts |
| `evaluate_evidence.py` | 151-source ledger, exact evidence matrix, class ratios, mappings, and complete research citation |
| `check_skill_routing.py` | positive, negative, and overlap routing coverage for every skill |
| `check_context_budget.py` | conservative 8,000-character discovery estimate, 7,600 release limit, and no internal implicit gateway |
| `check_profiles.py` | core, lifecycle, Rust, and full skill-selection profiles and renderer output |
| `check_v3_contracts.py` | new skills, references, templates, schema satisfiability, and closed-object negative tests |
| `check_rust_assets.py` | 11 Rust modules, prohibited patterns, delimiters, 17 schemas, and six Rust skills |
| `check_lifecycle_assets.py` | cumulative field-learning, lifecycle, Product Fitness, learning, verification, research, and eval expansion |
| `release_check.py` | all mandatory gates, syntax, content scan, confidence threshold, hashes, and aggregate report |

## Release command

```text
python scripts/release_check.py --write
```

A successful run writes individual reports, `evals/results/release-report.json`, and `FILE-MANIFEST.sha256`. It reports but never fabricates unavailable live Codex, field-pilot, Cargo, or rustc evidence.
