#!/usr/bin/env python3
"""Enforce a conservative Codex skill-discovery budget and no internal gateway."""
from __future__ import annotations

import argparse, json, yaml
from _common import make_report, parse_frontmatter, plugin_root, print_report, results_dir, skill_dirs, write_json

FALLBACK_LIMIT=8000
RELEASE_LIMIT=7600


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument('--write',action='store_true'); args=parser.parse_args()
    errors: list[str]=[]; warnings: list[str]=[]
    desc_chars=0; names_chars=0; implicit=[]; per_skill={}
    for d in skill_dirs():
        fields,_=parse_frontmatter(d/'SKILL.md'); desc=fields.get('description',''); name=fields.get('name','')
        desc_chars+=len(desc); names_chars+=len(name); per_skill[name]=len(desc)
        cfg=yaml.safe_load((d/'agents'/'openai.yaml').read_text(encoding='utf-8'))
        if (cfg.get('policy') or {}).get('allow_implicit_invocation'): implicit.append(name)
    # Conservative rendering estimate includes names, descriptions, separators, and a 12% host-format margin.
    raw=names_chars+desc_chars+len(per_skill)*12
    estimate=int(raw*1.12)
    if desc_chars>RELEASE_LIMIT: errors.append(f'description payload {desc_chars} exceeds release limit {RELEASE_LIMIT}')
    if estimate>FALLBACK_LIMIT: errors.append(f'conservative rendered estimate {estimate} exceeds fallback limit {FALLBACK_LIMIT}')
    if implicit: errors.append(f'Agentic co-install must expose no implicit skill; found {implicit}')
    if max(per_skill.values(),default=0)>180: errors.append('one or more descriptions exceed 180 characters')
    headroom=FALLBACK_LIMIT-estimate
    if headroom<1000: warnings.append('discovery headroom is below 1,000 characters; add skills only with profile or gateway consolidation')
    report=make_report('context-budget-check',not errors,errors,warnings,{
        'skills':len(per_skill),'description_chars':desc_chars,'name_chars':names_chars,'conservative_rendered_estimate':estimate,
        'fallback_limit':FALLBACK_LIMIT,'headroom':headroom,'implicit_skills':implicit,'largest_description':max(per_skill.values(),default=0),
    })
    if args.write: write_json(results_dir()/"context-budget.json",report)
    print_report(report); return 0 if report['passed'] else 1

if __name__=='__main__': raise SystemExit(main())
