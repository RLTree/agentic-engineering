#!/usr/bin/env python3
"""Validate new v3 contract schemas, templates, references, and anti-gaming mechanisms."""
from __future__ import annotations

import argparse, json
from pathlib import Path
from jsonschema import Draft202012Validator
from _common import make_report, plugin_root, print_report, results_dir, write_json

NEW_SKILLS={
    'engineering-learning-loop':'Learning Adoption Record',
    'verification-strategy-engineering':'Verification Mode Contract',
    'product-fitness-engineering':'Product Fitness Evidence Plan',
}
NEW_SCHEMAS={
    'no-change-decision.schema.json','verification-mode-contract.schema.json','task-evidence-packet.schema.json',
    'review-verdict.schema.json','repair-loop-contract.schema.json','learning-adoption-record.schema.json','skill-eval-case.schema.json',
}
NEW_TEMPLATES={
    'no-change-decision.md','verification-mode-contract.md','task-evidence-packet.md','review-verdict.md','repair-loop-contract.md',
    'learning-adoption-record.md','product-fitness-field-pulse.md','product-journey-review.md','product-fitness-evidence-plan.md',
    'skill-behavior-eval-case.jsonl','knowledge-projection-card.md','proportional-assurance-profile.md',
}
SHARED={
    'no-change-and-abstention.md','repair-budget-and-feedback.md','task-evidence-and-review-contracts.md','skill-behavior-evaluation.md',
    'product-fitness-observation.md','proportional-assurance.md','knowledge-evolution-and-garbage-collection.md','gpt-5.6-execution-selection.md',
}


def sample(schema):
    if 'const' in schema: return schema['const']
    if 'enum' in schema: return schema['enum'][0]
    typ=schema.get('type')
    if typ=='object':
        props=schema.get('properties',{}); return {k:sample(props[k]) for k in schema.get('required',[]) if k in props}
    if typ=='array':
        n=max(1,int(schema.get('minItems',0))) if schema.get('minItems',0) else 0
        return [sample(schema.get('items',{})) for _ in range(n)]
    if typ=='integer': return max(int(schema.get('minimum',0)),1)
    if typ=='number': return max(float(schema.get('minimum',0)),1.0)
    if typ=='boolean': return False
    if typ=='null': return None
    return 'x'


def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument('--write',action='store_true'); args=parser.parse_args()
    errors=[]; warnings=['Schema-generated smoke instances prove structural satisfiability, not domain correctness or live interoperability.']
    root=plugin_root()
    for skill,deliverable in NEW_SKILLS.items():
        d=root/'skills'/skill; text=(d/'SKILL.md').read_text(encoding='utf-8') if (d/'SKILL.md').is_file() else ''
        if deliverable not in text: errors.append(f'{skill}: missing deliverable {deliverable}')
        refs=list((d/'references').glob('*.md'))
        if len(refs)!=4: errors.append(f'{skill}: expected four references, found {len(refs)}')
    actual_schemas={p.name for p in (root/'assets'/'schemas').glob('*.json')}
    if not NEW_SCHEMAS<=actual_schemas: errors.append(f'missing v3 schemas {sorted(NEW_SCHEMAS-actual_schemas)}')
    actual_templates={p.name for p in (root/'assets'/'templates').iterdir() if p.is_file()}
    if not NEW_TEMPLATES<=actual_templates: errors.append(f'missing v3 templates {sorted(NEW_TEMPLATES-actual_templates)}')
    actual_shared={p.name for p in (root/'references').glob('*.md')}
    if not SHARED<=actual_shared: errors.append(f'missing v3 shared references {sorted(SHARED-actual_shared)}')

    satisfiable=0; closed_rejections=0
    for filename in sorted(NEW_SCHEMAS):
        schema=json.loads((root/'assets'/'schemas'/filename).read_text(encoding='utf-8'))
        Draft202012Validator.check_schema(schema); validator=Draft202012Validator(schema)
        instance=sample(schema)
        errs=list(validator.iter_errors(instance))
        if errs: errors.append(f'{filename}: generated required-field instance is invalid: {errs[0].message}')
        else: satisfiable+=1
        invalid=dict(instance); invalid['__unexpected__']=True
        if not list(validator.iter_errors(invalid)): errors.append(f'{filename}: closed-object negative case unexpectedly passed')
        else: closed_rejections+=1

    research=(root/'RESEARCH-V3-ADDENDUM.md').read_text(encoding='utf-8').lower()
    for term in ('no-change','repair loops are budgeted experiments','held-out','mutation','specification-evolution','product fitness','continuous agent security'):
        if term not in research: errors.append(f'v3 research addendum missing {term!r}')
    for protocol in ('run-no-change-and-repair-study.md','run-skill-behavior-ab.md','run-product-fitness-pilot.md'):
        if not (root/'evals'/protocol).is_file(): errors.append(f'missing downstream protocol {protocol}')
    report=make_report('v3-contract-check',not errors,errors,warnings,{
        'new_skills':len(NEW_SKILLS),'new_schemas':len(NEW_SCHEMAS),'schema_satisfiable_smokes':satisfiable,
        'closed_object_negative_rejections':closed_rejections,'new_templates':len(NEW_TEMPLATES),'new_shared_references':len(SHARED),
    })
    if args.write: write_json(results_dir()/"v3-contracts.json",report)
    print_report(report); return 0 if report['passed'] else 1

if __name__=='__main__': raise SystemExit(main())
