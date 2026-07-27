#!/usr/bin/env python3
"""Statically validate Rust reference fragments and all JSON Schemas."""
from __future__ import annotations

import argparse, json, re
from pathlib import Path
try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    Draft202012Validator=None
from _common import make_report, plugin_root, print_report, results_dir, write_json

EXPECTED_RUST={
    'README.md','agent_domain.rs','effect_journal.rs','runtime_supervisor.rs','testkit.rs','tool_contract.rs',
    'field_observation.rs','rollout_gate.rs','telemetry_policy.rs','control_evidence.rs','repair_budget.rs','learning_record.rs',
}
TOKENS={
    'agent_domain.rs':('RunStatus','ProposedEffect','StateVersion','TransitionError'),
    'effect_journal.rs':('EffectStatus','EffectJournal','DispatchOutcome','reconcile'),
    'runtime_supervisor.rs':('CancellationToken','JoinSet','Semaphore','timeout'),
    'testkit.rs':('ScriptedModel','ModelRequest','ModelDecision','assert_consumed'),
    'tool_contract.rs':('JsonSchema','TryFrom','ToolError','deny_unknown_fields'),
    'field_observation.rs':('ObservationId','OutcomeClass','EffectState','EvidenceStrength'),
    'rollout_gate.rs':('RolloutDecision','Advance','Hold','Revert'),
    'telemetry_policy.rs':('TelemetryPolicy','PrivacyClass','SamplingDecision','metric_label'),
    'control_evidence.rs':('TaskEvidencePacket','Ownership','ReviewVerdict','ReviewDecision'),
    'repair_budget.rs':('RepairAttempt','RepairPolicy','RepairDecision','mechanism_class'),
    'learning_record.rs':('NoChangeDecision','LearningRecord','ChangeDisposition','AdoptionDecision'),
}
FORBIDDEN={r'\.unwrap\s*\(':'unwrap',r'\.expect\s*\(':'expect',r'\bunsafe\b':'unsafe',r'unbounded_channel':'unbounded channel',r'mpsc::unbounded':'unbounded channel',r'std::thread::spawn':'untracked thread',r'serde_json::Value':'untyped JSON boundary'}
EXPECTED_SCHEMAS={
    'delegation-result.schema.json','evidence-item.schema.json','experiment-contract.schema.json','field-observation.schema.json',
    'lifecycle-decision-record.schema.json','metric-contract.schema.json','operating-envelope.schema.json','run-state.schema.json',
    'tool-contract.schema.json','trace-event.schema.json','no-change-decision.schema.json','verification-mode-contract.schema.json',
    'task-evidence-packet.schema.json','review-verdict.schema.json','repair-loop-contract.schema.json','learning-adoption-record.schema.json','skill-eval-case.schema.json',
}


def strip(text:str)->str:
    # Sufficient lexical erasure for delimiter balance; raw-string support is intentionally conservative.
    text=re.sub(r'//.*','',text)
    text=re.sub(r'/\*.*?\*/','',text,flags=re.S)
    text=re.sub(r'"(?:\\.|[^"\\])*"','""',text)
    return text


def delimiter_errors(path:Path,text:str)->list[str]:
    pairs={')':'(',']':'[','}':'{'}; stack=[]; errors=[]
    for i,ch in enumerate(strip(text)):
        if ch in '([{': stack.append((ch,i))
        elif ch in ')]}':
            if not stack or stack[-1][0]!=pairs[ch]: errors.append(f'{path.name}: unmatched {ch} at byte {i}'); break
            stack.pop()
    if stack: errors.append(f'{path.name}: unclosed {stack[-1][0]} at byte {stack[-1][1]}')
    return errors


def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument('--write',action='store_true'); args=parser.parse_args()
    errors=[]; warnings=['Rust fragments receive static checks here; compilation remains a downstream gate when cargo/rustc are available.']
    rust_root=plugin_root()/"assets"/"rust"; schema_root=plugin_root()/"assets"/"schemas"
    actual={p.name for p in rust_root.iterdir() if p.is_file()}
    if actual!=EXPECTED_RUST: errors.append(f'Rust asset mismatch: missing={sorted(EXPECTED_RUST-actual)} extra={sorted(actual-EXPECTED_RUST)}')
    lines=0
    for filename,tokens in TOKENS.items():
        path=rust_root/filename
        if not path.is_file(): continue
        text=path.read_text(encoding='utf-8'); lines+=len(text.splitlines())
        for token in tokens:
            if token not in text: errors.append(f'{filename}: missing {token}')
        for pattern,reason in FORBIDDEN.items():
            if re.search(pattern,text): errors.append(f'{filename}: forbidden {reason}')
        errors.extend(delimiter_errors(path,text))
    readme=(rust_root/'README.md').read_text(encoding='utf-8') if (rust_root/'README.md').is_file() else ''
    for phrase in ('not a version-pinned crate','cargo','rustc','does not claim','control_evidence.rs','repair_budget.rs','learning_record.rs'):
        if phrase not in readme: errors.append(f'Rust README missing {phrase!r}')

    schemas={p.name for p in schema_root.glob('*.json')}
    if schemas!=EXPECTED_SCHEMAS: errors.append(f'schema set mismatch: missing={sorted(EXPECTED_SCHEMAS-schemas)} extra={sorted(schemas-EXPECTED_SCHEMAS)}')
    for path in sorted(schema_root.glob('*.json')):
        try: schema=json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc: errors.append(f'{path.name}: invalid JSON: {exc}'); continue
        if schema.get('$schema')!='https://json-schema.org/draft/2020-12/schema': errors.append(f'{path.name}: wrong schema draft')
        if schema.get('type')!='object' or schema.get('additionalProperties') is not False: errors.append(f'{path.name}: top-level must be a closed object')
        if not schema.get('required') or not schema.get('properties'): errors.append(f'{path.name}: properties and required must be non-empty')
        if Draft202012Validator is None: errors.append('jsonschema package unavailable')
        else:
            try: Draft202012Validator.check_schema(schema)
            except Exception as exc: errors.append(f'{path.name}: invalid schema: {exc}')

    rust_skills={
        'rust-agentic-architecture':('typed','provider','effect'),'rust-agent-runtime':('CancellationToken','backpressure','shutdown'),
        'rust-agent-durability':('idempotency','journal','reconcile'),'rust-agent-protocols':('MCP','A2A','schema'),
        'rust-agent-verification':('cargo','concurrency','supply-chain'),'rust-agent-observability':('tracing','OpenTelemetry','cardinality'),
    }
    for skill,tokens in rust_skills.items():
        d=plugin_root()/"skills"/skill; aggregate='\n'.join([ (d/'SKILL.md').read_text(encoding='utf-8'), *[p.read_text(encoding='utf-8') for p in (d/'references').glob('*.md')] ])
        for token in tokens:
            if token.lower() not in aggregate.lower(): errors.append(f'{skill}: missing guidance term {token}')
    report=make_report('rust-asset-static-check',not errors,errors,warnings,{
        'rust_files':len([x for x in actual if x.endswith('.rs')]),'rust_reference_lines':lines,'json_schemas':len(schemas),
        'forbidden_patterns':len(FORBIDDEN),'rust_skills':len(rust_skills),'compile_status':'not_executed_in_this_environment',
    })
    if args.write: write_json(results_dir()/"rust-assets.json",report)
    print_report(report); return 0 if report['passed'] else 1

if __name__=='__main__': raise SystemExit(main())
