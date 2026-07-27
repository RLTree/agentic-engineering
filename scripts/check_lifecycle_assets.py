#!/usr/bin/env python3
"""Validate cumulative v2 lifecycle assets plus v3 governed-learning expansion."""
from __future__ import annotations

import argparse, json, re
from _common import load_json, make_report, plugin_root, print_report, results_dir, write_json

V2_SKILLS={
    'agentic-product-lifecycle':'Lifecycle Assurance Plan','authentic-use-engineering':'Controlled Field-Learning Plan',
    'agent-product-discovery':'Product Discovery Evidence Brief','concept-feasibility-validation':'Concept and Feasibility Evidence Case',
    'requirements-systems-engineering':'Operational Concept and Traceability Baseline','architecture-delivery-planning':'Architecture and Evidence-Driven Delivery Plan',
    'software-construction-quality':'Construction and Quality Evidence Plan','secure-delivery-release':'Secure Release Evidence Package',
    'production-readiness-sre':'Production Readiness and Reliability Plan','continuous-product-experimentation':'Product Experiment and Decision Contract',
    'maintenance-retirement-engineering':'Maintenance, Deprecation, and Retirement Plan','rust-agent-observability':'Rust Agent Observability Contract',
}
V3_SKILLS={
    'engineering-learning-loop':'Learning Adoption Record','verification-strategy-engineering':'Verification Mode Contract','product-fitness-engineering':'Product Fitness Evidence Plan',
}
V2_SHARED={'full-lifecycle-map.md','lifecycle-evidence-and-readiness.md','agent-mediated-product-operating-model.md','controlled-field-learning-system.md','field-evidence-ladder.md','autonomy-and-exposure-ladder.md','metric-and-causal-evidence.md','field-lifecycle-vocabulary.md'}
V3_SHARED={'no-change-and-abstention.md','repair-budget-and-feedback.md','task-evidence-and-review-contracts.md','skill-behavior-evaluation.md','product-fitness-observation.md','proportional-assurance.md','knowledge-evolution-and-garbage-collection.md','gpt-5.6-execution-selection.md'}
RESEARCH_TERMS=(
    'authentic-use engineering','operating envelope','representative workload','assignment','exposure','ambiguous effect','near miss','metric contract','error budget','retirement',
    'no-change','repair loops are budgeted experiments','verification is selected','held-out','mutation','specification-evolution','product fitness','continuous agent security',
)


def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument('--write',action='store_true'); args=parser.parse_args()
    errors=[]; warnings=['This gate proves package completeness and traceability, not live product effectiveness, legal approval, or field fitness.']
    root=plugin_root(); skills={**V2_SKILLS,**V3_SKILLS}
    for skill,deliverable in skills.items():
        d=root/'skills'/skill; path=d/'SKILL.md'
        if not path.is_file(): errors.append(f'missing skill {skill}'); continue
        text=path.read_text(encoding='utf-8')
        if deliverable not in text: errors.append(f'{skill}: missing deliverable {deliverable}')
        expected=4
        count=len(list((d/'references').glob('*.md')))
        if count!=expected: errors.append(f'{skill}: expected {expected} focused references, found {count}')
    shared={p.name for p in (root/'references').glob('*.md')}
    missing=(V2_SHARED|V3_SHARED)-shared
    if missing: errors.append(f'missing shared lifecycle/v3 references: {sorted(missing)}')

    source=load_json(root/'SOURCE-MANIFEST.json'); ids=[x['id'] for x in source.get('sources',[])]
    expected=[f'R{i:02d}' for i in range(1,152)]
    if ids!=expected or source.get('source_count')!=151: errors.append('source expansion must be contiguous R01..R151 with source_count 151')
    research=(root/'RESEARCH.md').read_text(encoding='utf-8'); lower=research.lower()
    for term in RESEARCH_TERMS:
        if term not in lower: errors.append(f'research missing term {term!r}')
    cited=set(re.findall(r'\[(R\d{2,3})\]',research))
    if set(expected)-cited: errors.append(f'research missing source citations {sorted(set(expected)-cited)}')

    scenarios=load_json(root/'evals'/'scenarios.json').get('scenarios',[])
    routes=load_json(root/'evals'/'routing-cases.json').get('cases',[])
    contracts={x.get('skill') for x in load_json(root/'evals'/'behavior-contracts.json').get('contracts',[])}
    capabilities={x.get('skill') for x in load_json(root/'evals'/'capability-map.json').get('skills',[])}
    sc_counts={s:0 for s in skills}; pos={s:0 for s in skills}; neg={s:0 for s in skills}
    for item in scenarios:
        for s in item.get('expected_skills',[]):
            if s in sc_counts: sc_counts[s]+=1
    for item in routes:
        for s in item.get('expected_skills',[]):
            if s in pos: pos[s]+=1
        for s in item.get('must_not_select',[]):
            if s in neg: neg[s]+=1
    for s in skills:
        if sc_counts[s]<3: errors.append(f'{s}: fewer than three scenarios')
        if pos[s]<4: errors.append(f'{s}: fewer than four positive/overlap routes')
        if neg[s]<1: errors.append(f'{s}: missing negative route')
        if s not in contracts: errors.append(f'{s}: missing behavior contract')
        if s not in capabilities: errors.append(f'{s}: missing capability map')

    report=make_report('lifecycle-and-v3-expansion-check',not errors,errors,warnings,{
        'lifecycle_skills':len(V2_SKILLS),'v3_skills':len(V3_SKILLS),'shared_references':len(V2_SHARED|V3_SHARED),
        'sources':len(ids),'scenarios_for_expansion':sum(sc_counts.values()),'positive_routes_for_expansion':sum(pos.values()),
        'negative_routes_for_expansion':sum(neg.values()),
    })
    if args.write: write_json(results_dir()/"lifecycle-expansion.json",report)
    print_report(report); return 0 if report['passed'] else 1

if __name__=='__main__': raise SystemExit(main())
