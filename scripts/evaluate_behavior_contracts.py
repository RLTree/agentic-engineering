#!/usr/bin/env python3
"""Evaluate global and per-skill behavioral contracts against skill bodies."""
from __future__ import annotations

import argparse
from _common import load_json, make_report, plugin_root, print_report, results_dir, skill_dirs, write_json


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument('--write',action='store_true'); args=parser.parse_args()
    errors: list[str]=[]; warnings: list[str]=[]
    contracts=load_json(plugin_root()/"evals"/"behavior-contracts.json").get('contracts',[])
    capabilities={x['skill']:x for x in load_json(plugin_root()/"evals"/"capability-map.json").get('skills',[])}
    valid={p.name for p in skill_dirs()}
    if len(contracts)!=len(valid)+1: errors.append(f'expected one global and {len(valid)} skill contracts; found {len(contracts)}')
    ids=[x.get('id') for x in contracts]
    if len(ids)!=len(set(ids)) or any(not isinstance(x,str) or not x for x in ids): errors.append('behavior contract IDs must be unique non-empty strings')
    globals_=[x for x in contracts if x.get('skill')=='*']
    if len(globals_)!=1: errors.append('exactly one global behavior contract is required')
    by_skill={x.get('skill'):x for x in contracts if x.get('skill')!='*'}
    if set(by_skill)!=valid: errors.append(f'per-skill contract mismatch: missing={sorted(valid-set(by_skill))} extra={sorted(set(by_skill)-valid)}')

    for contract in contracts:
        label=contract.get('skill') or contract.get('id')
        if len(contract.get('required',[]))<5: errors.append(f'{label}: fewer than five required behaviors')
        if len(contract.get('forbidden',[]))<3: errors.append(f'{label}: fewer than three forbidden behaviors')
        if len(contract.get('evidence',[]))<2: errors.append(f'{label}: fewer than two evidence obligations')
        if contract.get('skill')=='*': continue
        deliverable=contract.get('deliverable')
        if not isinstance(deliverable,str) or not deliverable.strip(): errors.append(f'{label}: missing deliverable'); continue
        skill_text=(plugin_root()/"skills"/str(label)/"SKILL.md").read_text(encoding='utf-8')
        if deliverable not in skill_text: errors.append(f'{label}: deliverable is not named in SKILL.md')
        if capabilities.get(label,{}).get('deliverable')!=deliverable: errors.append(f'{label}: deliverable differs between behavior and capability contracts')

    report=make_report('behavior-contract-evaluation',not errors,errors,warnings,{
        'contracts':len(contracts),'global_contracts':len(globals_),'skill_contracts':len(by_skill),
        'required_behavior_rules':sum(len(x.get('required',[])) for x in contracts),
        'forbidden_behavior_rules':sum(len(x.get('forbidden',[])) for x in contracts),
        'evidence_obligations':sum(len(x.get('evidence',[])) for x in contracts),
    })
    if args.write: write_json(results_dir()/"behavior-contracts.json",report)
    print_report(report); return 0 if report['passed'] else 1

if __name__=='__main__': raise SystemExit(main())
