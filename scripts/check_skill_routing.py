#!/usr/bin/env python3
"""Audit positive, negative, and overlap routing corpus coverage."""
from __future__ import annotations

import argparse, re
from collections import Counter
from _common import load_json, make_report, plugin_root, print_report, results_dir, skill_dirs, write_json

ID_RE=re.compile(r'^RT-\d{3}$')
CASES={'should_invoke','should_not_invoke','overlap'}


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument('--write',action='store_true'); args=parser.parse_args()
    errors: list[str]=[]
    warnings=['This corpus validates routing intent and coverage; it is not a live GPT-5.6 activation benchmark.']
    doc=load_json(plugin_root()/"evals"/"routing-cases.json"); cases=doc.get('cases',[]); valid={p.name for p in skill_dirs()}
    if doc.get('case_count')!=len(cases): errors.append('case_count does not match cases')
    ids=[x.get('id') for x in cases]
    if len(ids)!=len(set(ids)) or any(not isinstance(x,str) or not ID_RE.fullmatch(x) for x in ids): errors.append('routing IDs must be unique RT-### values')
    positive=Counter(); negative=Counter(); counts=Counter()
    for item in cases:
        rid=item.get('id'); case=item.get('case'); expected=item.get('expected_skills'); forbidden=item.get('must_not_select')
        if case not in CASES: errors.append(f'{rid}: invalid case {case!r}'); continue
        counts[case]+=1
        if not isinstance(expected,list) or not isinstance(forbidden,list): errors.append(f'{rid}: expected_skills and must_not_select must be lists'); continue
        if set(expected)&set(forbidden): errors.append(f'{rid}: a skill cannot be both expected and forbidden')
        if set(expected)-valid: errors.append(f'{rid}: unknown expected skills {sorted(set(expected)-valid)}')
        if set(forbidden)-valid: errors.append(f'{rid}: unknown forbidden skills {sorted(set(forbidden)-valid)}')
        if case=='should_invoke' and not expected: errors.append(f'{rid}: should_invoke needs expected_skills')
        if case=='should_not_invoke' and (expected or not forbidden): errors.append(f'{rid}: should_not_invoke needs empty expected_skills and non-empty must_not_select')
        if case=='overlap' and len(expected)<2: errors.append(f'{rid}: overlap needs at least two expected skills')
        if not str(item.get('prompt','')).strip() or not str(item.get('rationale','')).strip(): errors.append(f'{rid}: prompt and rationale are required')
        positive.update(expected); negative.update(forbidden)
    for skill in valid:
        if positive[skill]<4: errors.append(f'{skill}: fewer than four positive/overlap routing cases')
        if negative[skill]<1: errors.append(f'{skill}: no negative routing case')
    if counts['overlap']<8: errors.append('routing corpus needs at least eight overlap cases')
    if counts['should_not_invoke']<len(valid): errors.append('routing corpus needs at least one negative case per skill')
    report=make_report('routing-corpus-audit',not errors,errors,warnings,{
        'routing_cases':len(cases),'should_invoke':counts['should_invoke'],'should_not_invoke':counts['should_not_invoke'],'overlap':counts['overlap'],
        'minimum_positive_cases_per_skill':min(positive[s] for s in valid) if valid else 0,
        'minimum_negative_cases_per_skill':min(negative[s] for s in valid) if valid else 0,
    })
    if args.write: write_json(results_dir()/"routing.json",report)
    print_report(report); return 0 if report['passed'] else 1

if __name__=='__main__': raise SystemExit(main())
