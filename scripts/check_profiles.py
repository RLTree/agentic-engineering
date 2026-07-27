#!/usr/bin/env python3
"""Validate advisory skill profiles and profile-rendering output."""
from __future__ import annotations

import argparse, hashlib, json, subprocess, sys
from _common import load_json, make_report, plugin_root, print_report, results_dir, skill_dirs, write_json

EXPECTED={'core','lifecycle','rust','ultragoal','full'}
EXPECTED_DIGESTS = {
    "core": "a9494b6dc0cdee51790d63a1273cfef138c71e67b2815e113b9dfea19df00940",
    "lifecycle": "6cf61fd7606da97ef185260cc3f7fb4cd17ec9fd5650a46b431b6fb4c7611e41",
    "rust": "84121f8c9b2a52d62746bf2c18b290ec9aa0437109e46c6a0b9b3685d366ac85",
    "ultragoal": "a2d2a098a035654f7c40837b3fd58032c4e7d250cba302c23055adb446d13ea3",
    "full": "8fadb8437c4c7b31427effce2565660a7ba70230628700b58234a482c7de8625",
}


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument('--write',action='store_true'); args=parser.parse_args()
    errors: list[str]=[]; warnings: list[str]=[]; valid={p.name for p in skill_dirs()}; root=plugin_root()/"profiles"
    found={p.stem for p in root.glob('*.json')}
    if found!=EXPECTED: errors.append(f'profile set mismatch: missing={sorted(EXPECTED-found)} extra={sorted(found-EXPECTED)}')
    profile_sizes={}
    for name in sorted(found):
        doc=load_json(root/f'{name}.json'); enabled=doc.get('enabled_skills')
        if doc.get('schema_version')!='1.0' or doc.get('profile')!=name: errors.append(f'{name}: invalid profile metadata')
        if not isinstance(enabled,list) or len(enabled)!=len(set(enabled)): errors.append(f'{name}: enabled_skills must be a unique list'); continue
        digest = hashlib.sha256((root / f"{name}.json").read_bytes()).hexdigest()
        if digest != EXPECTED_DIGESTS[name]:
            errors.append(f"{name}: profile bytes differ from the locked release profile")
        if set(enabled)-valid: errors.append(f'{name}: unknown skills {sorted(set(enabled)-valid)}')
        front=doc.get('implicit_front_door')
        if front != 'external:harness-ultragoal':
            errors.append(f'{name}: must declare the external Harness UltraGoal front door')
        if name == 'ultragoal' and 'agentic-engineering' in enabled:
            errors.append('ultragoal: must expose only explicit specialist advisers')
        profile_sizes[name]=len(enabled)
        proc=subprocess.run([sys.executable,str(plugin_root()/"scripts"/"render_profile_config.py"),name],text=True,capture_output=True)
        if proc.returncode!=0: errors.append(f'{name}: profile renderer failed: {proc.stderr.strip()}')
        elif proc.stdout.count('[[skills.config]]')!=len(valid): errors.append(f'{name}: renderer did not emit one entry per installed skill')
    full=set(load_json(root/'full.json').get('enabled_skills',[])) if (root/'full.json').is_file() else set()
    if full!=valid: errors.append('full profile must contain every skill exactly once')
    for subset in ('core','lifecycle','rust','ultragoal'):
        if (root/f'{subset}.json').is_file() and not set(load_json(root/f'{subset}.json').get('enabled_skills',[]))<full:
            errors.append(f'{subset}: must be a proper subset of full')
    report=make_report('profile-validation',not errors,errors,warnings,{'profiles':len(found),'profile_sizes':profile_sizes,'skills':len(valid)})
    if args.write: write_json(results_dir()/"profiles.json",report)
    print_report(report); return 0 if report['passed'] else 1

if __name__=='__main__': raise SystemExit(main())
