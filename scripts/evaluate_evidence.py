#!/usr/bin/env python3
"""Validate source ledger, evidence matrix, research citations, and skill traceability."""
from __future__ import annotations

import argparse, csv, re
from collections import Counter
from _common import load_json, make_report, plugin_root, print_report, results_dir, skill_dirs, write_json


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument('--write',action='store_true'); args=parser.parse_args()
    errors: list[str]=[]
    warnings: list[str]=[
        'Historical source-ledger integrity only; source count, coverage, ratios, and monograph length do not prove package quality or release validity.'
    ]
    doc=load_json(plugin_root()/"SOURCE-MANIFEST.json"); sources=doc.get('sources',[])
    if doc.get('source_count')!=len(sources): errors.append('source_count does not match sources')
    ids=[x.get('id') for x in sources]; expected=[f'R{i:02d}' for i in range(1,len(sources)+1)]
    if ids!=expected: errors.append(f'source IDs must be contiguous {expected[0]}..{expected[-1]} in order')
    if len(ids)!=len(set(ids)): errors.append('source IDs are not unique')
    classes=Counter(x.get('evidence_class') for x in sources)
    if set(classes)-{'A','B','C','D'}: errors.append(f'unknown evidence classes {sorted(set(classes)-{"A","B","C","D"})}')
    for x in sources:
        for key in ('id','evidence_class','topic','source','date','type','key_finding','operationalization','url'):
            if not str(x.get(key,'')).strip(): errors.append(f'{x.get("id")}: missing {key}')
        if not isinstance(x.get('affected_skills'),list) or not x.get('affected_skills'): errors.append(f'{x.get("id")}: affected_skills must be non-empty')

    with (plugin_root()/"EVIDENCE-MATRIX.csv").open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
    matrix_ids=[x.get('id') for x in rows]
    if matrix_ids!=ids: errors.append('evidence matrix must contain exactly one ordered row per source')
    if len(rows)!=len(sources): errors.append('evidence matrix row count differs from source manifest')

    research=(plugin_root()/"RESEARCH.md").read_text(encoding='utf-8')
    cited=set(re.findall(r'\[(R\d{2,3})\]',research))
    missing=set(ids)-cited
    if missing: errors.append(f'research does not cite source IDs {sorted(missing)}')
    unknown=cited-set(ids)
    if unknown: errors.append(f'research cites unknown source IDs {sorted(unknown)}')
    word_count=len(re.findall(r"\b[\w'-]+\b",research))
    if word_count<26000: errors.append(f'research synthesis is unexpectedly short: {word_count} words')

    valid={p.name for p in skill_dirs()}; covered=Counter()
    for x in sources:
        for skill in x.get('affected_skills',[]):
            if skill == 'all skills':
                covered.update(valid)
            elif skill not in valid:
                errors.append(f'{x.get("id")}: unknown affected skill {skill}')
            else:
                covered[skill]+=1
    for skill in valid:
        if covered[skill]<3: errors.append(f'{skill}: fewer than three mapped evidence sources')

    a=classes['A']/len(sources) if sources else 0; ab=(classes['A']+classes['B'])/len(sources) if sources else 0
    if a<0.60: errors.append(f'class-A source ratio below 0.60: {a:.3f}')
    if ab<0.85: errors.append(f'class-A+B source ratio below 0.85: {ab:.3f}')
    report=make_report('evidence-evaluation',not errors,errors,warnings,{
        'sources':len(sources),**{f'class_{k}':classes[k] for k in 'ABCD'},'primary_source_ratio':round(a,4),
        'authoritative_source_ratio':round(ab,4),'research_word_count':word_count,'source_ids_cited':len(cited),'skills_covered':len(covered),
    })
    if args.write: write_json(results_dir()/"evidence.json",report)
    print_report(report); return 0 if report['passed'] else 1

if __name__=='__main__': raise SystemExit(main())
