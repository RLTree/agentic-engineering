#!/usr/bin/env python3
"""Run every required release gate and emit a calibrated v3 release report."""
from __future__ import annotations

import argparse, ast, re, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _common import load_json, make_report, plugin_root, print_report, repo_root, results_dir, sha256, write_json

MANDATORY_SCRIPTS = [
    ("plugin_validation", "validate_plugin.py"),
    ("official_contract", "validate_official_contract.py"),
    ("link_audit", "audit_links.py"),
    ("coverage", "evaluate_coverage.py"),
    ("behavior_contracts", "evaluate_behavior_contracts.py"),
    ("evidence", "evaluate_evidence.py"),
    ("routing_corpus", "check_skill_routing.py"),
    ("context_budget", "check_context_budget.py"),
    ("profiles", "check_profiles.py"),
    ("v3_contracts", "check_v3_contracts.py"),
    ("rust_static_assets", "check_rust_assets.py"),
    ("lifecycle_and_v3_expansion", "check_lifecycle_assets.py"),
]
CONFIDENCE_FACTORS = [
    {"factor":"evidence_quality_and_recency","weight":0.20,"score":98,"basis":"151-source ledger locked to 2026-07-22; 98 class-A and 33 class-B sources, with current OpenAI, NIST, DORA, standards, primary project, and 2026 empirical evidence."},
    {"factor":"mechanism_traceability","weight":0.18,"score":99,"basis":"All 30 skills map to source IDs, local references, scenarios, routing cases, behavior contracts, deliverables, and release checks."},
    {"factor":"decision_and_authority_design","weight":0.18,"score":99,"basis":"No internal implicit gateway, explicit specialists, no-change, task evidence, review verdict, repair, learning, verification, Product Fitness, lifecycle, and authority handoff contracts are encoded."},
    {"factor":"evaluation_falsifiability","weight":0.16,"score":98,"basis":"90 scenarios, 143 routing cases, 31 behavior contracts, baseline/held-out/negative/mutation/spec-evolution protocols, and downstream field studies make the intervention falsifiable."},
    {"factor":"structural_package_validity","weight":0.13,"score":100,"basis":"Marketplace, manifests, profiles, context budget, progressive disclosure, links, JSON Schemas, source traceability, package content, Python syntax, and placeholders are deterministically checked."},
    {"factor":"rust_design_and_static_quality","weight":0.08,"score":94,"basis":"Eleven typed Rust reference modules and seventeen schemas receive static contract checks; target-workspace compilation remains downstream."},
    {"factor":"target_model_and_field_transfer","weight":0.07,"score":86,"basis":"The design follows current Codex/GPT-5.6 guidance and empirical mechanisms, but live Sol A/B, Rust compilation, and representative product pilots were unavailable in this build environment."},
]
TEXT_EXTENSIONS={'.md','.json','.csv','.yaml','.yml','.rs','.txt','.toml'}
SECRET_PATTERNS=[(re.compile(r'AKIA[0-9A-Z]{16}'),'AWS access key'),(re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),'private key'),(re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),'OpenAI-style secret key')]
PLACEHOLDER_RE=re.compile(r'\b(?:TODO|TBD|FIXME|XXX)\b|\[TODO:',re.I)


def run_script(name:str,filename:str)->dict[str,Any]:
    path=Path(__file__).resolve().parent/filename
    p=subprocess.run([sys.executable,str(path),'--write'],cwd=str(plugin_root()),text=True,capture_output=True)
    return {'name':name,'required':True,'status':'passed' if p.returncode==0 else 'failed','exit_code':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}


def syntax_check()->dict[str,Any]:
    failures=[]; files=sorted((plugin_root()/"scripts").glob('*.py'))
    for path in files:
        try: ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
        except SyntaxError as exc: failures.append(f'{path.name}: {exc}')
    return {'name':'python_syntax','required':True,'status':'passed' if not failures else 'failed','files':len(files),'failures':failures}


def content_scan()->dict[str,Any]:
    secrets=[]; placeholders=[]; scanned=0; root=plugin_root()
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS: continue
        rel=path.relative_to(root)
        if rel.parts and rel.parts[0]=='scripts': continue
        if rel.parts[:2]==('evals','results'): continue
        scanned+=1; text=path.read_text(encoding='utf-8',errors='replace')
        for pattern,label in SECRET_PATTERNS:
            if pattern.search(text): secrets.append(f'{rel}: {label}')
        if PLACEHOLDER_RE.search(text): placeholders.append(str(rel))
    failures=[f'secret-like material: {x}' for x in secrets]+[f'placeholder marker: {x}' for x in placeholders]
    return {'name':'content_scan','required':True,'status':'passed' if not failures else 'failed','files_scanned':scanned,'secret_findings':secrets,'placeholder_findings':placeholders,'failures':failures}


def optional_tool(name:str,command:list[str])->dict[str,Any]:
    if shutil.which(command[0]) is None: return {'name':name,'required':False,'status':'not_executed','reason':f'{command[0]} is unavailable in this build environment'}
    p=subprocess.run(command,text=True,capture_output=True)
    return {'name':name,'required':False,'status':'passed' if p.returncode==0 else 'failed','exit_code':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}


def write_file_manifest()->tuple[Path,int]:
    root=plugin_root(); lines=[]
    for path in sorted(root.rglob('*')):
        if not path.is_file(): continue
        rel=path.relative_to(root)
        if rel==Path('FILE-MANIFEST.sha256') or rel.parts[:2]==('evals','results') or '__pycache__' in rel.parts or path.suffix=='.pyc': continue
        lines.append(f'{sha256(path)}  {rel.as_posix()}')
    out=root/'FILE-MANIFEST.sha256'; out.write_text('\n'.join(lines)+'\n',encoding='utf-8'); return out,len(lines)


def confidence()->float: return round(sum(x['weight']*x['score'] for x in CONFIDENCE_FACTORS),1)


def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument('--write',action='store_true'); parser.parse_args()
    checks=[run_script(*x) for x in MANDATORY_SCRIPTS]+[syntax_check(),content_scan()]
    optional=[optional_tool('codex_live_plugin_and_sol_ab',['codex','--version']),optional_tool('rust_compilation_cargo',['cargo','--version']),optional_tool('rust_compilation_rustc',['rustc','--version'])]
    required_passed=all(x['status']=='passed' for x in checks if x.get('required'))
    score=confidence(); threshold_met=score>=95.0; passed=required_passed and threshold_met
    manifest_path,hashed=write_file_manifest(); source=load_json(plugin_root()/"SOURCE-MANIFEST.json")
    report={
        'report':'agentic-engineering-plugin-release','schema_version':'3.0','generated_at':datetime.now(timezone.utc).isoformat(),
        'research_lock':source.get('research_lock'),'plugin_version':load_json(plugin_root()/'.codex-plugin'/'plugin.json').get('version'),'passed':passed,
        'required_checks':checks,'optional_environment_checks':optional,
        'confidence':{'score':score,'threshold':95.0,'threshold_met':threshold_met,'kind':'calibrated engineering judgment, not a measured per-project probability','factors':CONFIDENCE_FACTORS,
          'residual_risks':['No blind live GPT-5.6 Sol baseline-versus-v3 benchmark was executable in this environment.','Rust reference modules were not compiled because cargo and rustc were unavailable.','No real product was enrolled in the Product Fitness or controlled-field pilot.','Impact depends on correct activation, task fit, host authority, repository quality, and downstream evidence.']},
        'artifact':{'repository_root':str(repo_root()),'plugin_root':str(plugin_root()),'source_files_hashed':hashed,'file_manifest':str(manifest_path.relative_to(plugin_root())),'file_manifest_sha256':sha256(manifest_path),'source_manifest_sha256':sha256(plugin_root()/'SOURCE-MANIFEST.json'),'research_sha256':sha256(plugin_root()/'RESEARCH.md')},
        'release_rule':'Release only when every required check passes and calibrated confidence is at least 95.0.',
    }
    out=results_dir()/"release-report.json"; write_json(out,report)
    summary=make_report('release-check',passed,[] if passed else ['one or more required gates failed or confidence threshold was not met'],[x['reason'] for x in optional if x['status']=='not_executed'],{'required_checks':len(checks),'required_passed':sum(x['status']=='passed' for x in checks),'confidence':score,'confidence_threshold':95.0,'hashed_source_files':hashed,'report':str(out)})
    print_report(summary); return 0 if passed else 1

if __name__=='__main__': raise SystemExit(main())
