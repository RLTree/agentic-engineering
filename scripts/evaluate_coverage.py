#!/usr/bin/env python3
"""Evaluate scenario, capability, reference, and routing coverage."""
from __future__ import annotations

import argparse
import re
from collections import Counter

from _common import load_json, make_report, plugin_root, print_report, results_dir, skill_dirs, write_json

SC_RE = re.compile(r"^SC-\d{3}$")
RT_RE = re.compile(r"^RT-\d{3}$")
TOPOLOGIES = {"workflow", "bounded_loop", "evaluator_optimizer", "graph", "durable_workflow", "multi_agent"}


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument('--write',action='store_true'); args=parser.parse_args()
    errors: list[str]=[]; warnings: list[str]=[]
    base=plugin_root()/"evals"
    scenarios_doc=load_json(base/"scenarios.json"); routing_doc=load_json(base/"routing-cases.json"); capability_doc=load_json(base/"capability-map.json")
    source_ids={x['id'] for x in load_json(plugin_root()/"SOURCE-MANIFEST.json").get('sources',[])}
    scenarios=scenarios_doc.get('scenarios',[]); routing=routing_doc.get('cases',[]); capabilities=capability_doc.get('skills',[])
    valid={p.name for p in skill_dirs()}

    if scenarios_doc.get('scenario_count') != len(scenarios): errors.append('scenario_count does not match scenarios')
    if len(scenarios) < 3*len(valid): errors.append(f'expected at least {3*len(valid)} scenarios, found {len(scenarios)}')
    ids=[x.get('id') for x in scenarios]
    if len(ids)!=len(set(ids)): errors.append('scenario IDs are not unique')
    if any(not isinstance(x,str) or not SC_RE.fullmatch(x) for x in ids): errors.append('scenario IDs must use SC-###')

    domain_counts=Counter(); skill_counts=Counter()
    for item in scenarios:
        sid=item.get('id')
        domain=item.get('domain')
        if not isinstance(domain,str) or not domain.strip(): errors.append(f'{sid}: domain is required')
        else: domain_counts[domain]+=1
        expected=item.get('expected_skills')
        if not isinstance(expected,list) or not expected: errors.append(f'{sid}: expected_skills must be non-empty'); continue
        unknown=set(expected)-valid
        if unknown: errors.append(f'{sid}: unknown skills {sorted(unknown)}')
        skill_counts.update(expected)
        if item.get('expected_topology') not in TOPOLOGIES: errors.append(f'{sid}: invalid topology {item.get("expected_topology")!r}')
        if len(item.get('required_decisions',[]))<5: errors.append(f'{sid}: fewer than five required decisions')
        if len(item.get('forbidden_behaviors',[]))<3: errors.append(f'{sid}: fewer than three forbidden behaviors')
        if len(item.get('evidence_requirements',[]))<2: errors.append(f'{sid}: fewer than two evidence requirements')
        if item.get('severity') not in {'high','critical'}: errors.append(f'{sid}: severity must be high or critical')
        if not str(item.get('prompt','')).strip(): errors.append(f'{sid}: empty prompt')
    for skill in valid:
        if skill_counts[skill]<3: errors.append(f'{skill}: fewer than three positive scenarios')
    # Each capability map owns one domain; overlap scenarios may mention several skills, so domain count need not equal skill count.
    if any(v<3 for v in domain_counts.values()): errors.append(f'each scenario domain needs at least three cases: {dict(domain_counts)}')

    if routing_doc.get('case_count') != len(routing): errors.append('routing case_count does not match cases')
    rt_ids=[x.get('id') for x in routing]
    if len(rt_ids)!=len(set(rt_ids)): errors.append('routing IDs are not unique')
    if any(not isinstance(x,str) or not RT_RE.fullmatch(x) for x in rt_ids): errors.append('routing IDs must use RT-###')
    if len(routing)<4*len(valid): errors.append(f'expected at least {4*len(valid)} routing cases, found {len(routing)}')

    if len(capabilities)!=len(valid): errors.append(f'capability map must contain {len(valid)} skills, found {len(capabilities)}')
    mapped={x.get('skill') for x in capabilities}
    if mapped!=valid: errors.append(f'capability map mismatch: missing={sorted(valid-mapped)} extra={sorted(mapped-valid)}')
    scenario_set=set(ids); route_set=set(rt_ids)
    for item in capabilities:
        skill=item.get('skill')
        if not str(item.get('domain','')).strip(): errors.append(f'{skill}: missing domain')
        if not str(item.get('deliverable','')).strip(): errors.append(f'{skill}: missing deliverable')
        sources=item.get('source_ids',[])
        if len(sources)<3: errors.append(f'{skill}: needs at least three source IDs')
        if set(sources)-source_ids: errors.append(f'{skill}: unknown sources {sorted(set(sources)-source_ids)}')
        refs=item.get('references',[])
        if len(refs)<3: errors.append(f'{skill}: needs at least three references')
        for ref in refs:
            if not (plugin_root()/"skills"/str(skill)/"references"/ref).is_file(): errors.append(f'{skill}: missing reference {ref}')
        if len(item.get('scenario_ids',[]))<3: errors.append(f'{skill}: needs at least three mapped scenarios')
        if set(item.get('scenario_ids',[]))-scenario_set: errors.append(f'{skill}: unknown scenario IDs')
        if len(item.get('routing_case_ids',[]))<4: errors.append(f'{skill}: needs at least four mapped routing cases')
        if set(item.get('routing_case_ids',[]))-route_set: errors.append(f'{skill}: unknown routing IDs')
        if len(item.get('required_capabilities',[]))<5: errors.append(f'{skill}: fewer than five required capabilities')

    report=make_report('coverage-evaluation',not errors,errors,warnings,{
        'scenarios':len(scenarios),'scenario_domains':len(domain_counts),'minimum_scenarios_per_skill':min(skill_counts.values()) if skill_counts else 0,
        'routing_cases':len(routing),'capability_maps':len(capabilities),'mapped_sources':len({s for x in capabilities for s in x.get('source_ids',[])}),
        'mapped_references':sum(len(x.get('references',[])) for x in capabilities),
    })
    if args.write: write_json(results_dir()/"coverage.json",report)
    print_report(report); return 0 if report['passed'] else 1

if __name__=='__main__': raise SystemExit(main())
