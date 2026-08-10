#!/usr/bin/env python3
"""Zero-write deterministic AQ logical-catalog scorer (schema 2.0)."""
from __future__ import annotations
import argparse, hashlib, importlib.util, itertools, json, random, subprocess, sys
from pathlib import Path
from typing import Any
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT, SOURCE_TREE = "407a2ac124856f0ce1fa33af8a61d0607e413820", "8314ca6ad82fa4687720692d8c5762c7aabf6261"
CORPUS_COMMIT, CORPUS_TREE = "25de0cb1fe86a802768de9bf64659206d69650d0", "e5faff4b1a5ba678a7df1727b5bda3b3d0afe00a"
ADVISERS = ("agentic-engineering","codex-task-contract","verification-strategy-engineering","engineering-learning-loop")
AUTO = {f"AQ2-H-{n:03d}" for n in range(1, 33)}
QUALIFIED = AUTO | {f"AQ2-{split}-{n:03d}" for split in ("A", "H") for n in range(33, 37)}
SCHEMA_PATH = "evals/foundation-v4/activation-evaluator-schema.json"

class InputError(ValueError): pass
def digest_bytes(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()
def digest_json(value: Any) -> str: return digest_bytes(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode())
def git_show(root: Path, commit: str, path: str) -> bytes:
    result=subprocess.run(["git","show",f"{commit}:{path}"],cwd=root,capture_output=True)
    if result.returncode: raise ValueError("immutable input unavailable")
    return result.stdout
def git_tree(root: Path, commit: str) -> str:
    result=subprocess.run(["git","rev-parse","--verify",f"{commit}^{{tree}}"],cwd=root,capture_output=True,text=True)
    if result.returncode: raise ValueError("candidate tree unavailable")
    return result.stdout.strip()

def frozen(root: Path) -> tuple[dict[str,dict[str,Any]],dict[str,str]]:
    """Only committed corpus bytes are scoring input; live drift is rejected."""
    paths={"activation_schema":"evals/foundation-v4/future-activation-v2/activation-schema.json","authoring":"evals/foundation-v4/future-activation-v2/activation-authoring.json","heldout":"evals/foundation-v4/future-activation-v2/activation-heldout.json"}
    raw={key:git_show(root,CORPUS_COMMIT,path) for key,path in paths.items()}
    for key,path in paths.items():
        try: live=(root/path).read_bytes()
        except OSError as exc: raise InputError("live_frozen_corpus_unavailable") from exc
        if live != raw[key]: raise InputError("live_frozen_corpus_drift")
    try:
        import jsonschema
        schema=json.loads(raw["activation_schema"])
        validator=jsonschema.Draft202012Validator(schema)
        documents=[json.loads(raw["authoring"]),json.loads(raw["heldout"])]
        for document in documents:
            if list(validator.iter_errors(document)): raise InputError("frozen_corpus_schema_invalid")
    except ImportError as exc: raise InputError("jsonschema_unavailable") from exc
    except (json.JSONDecodeError, ValueError) as exc: raise InputError("frozen_corpus_invalid") from exc
    cases={case["id"]:case for doc in documents for case in doc["cases"]}
    if set(cases) & QUALIFIED != QUALIFIED: raise InputError("frozen_qualification_subset_missing")
    return cases,{key+"_sha256":digest_bytes(value) for key,value in raw.items()}

def condition_parity_digest(execution: dict[str, Any]) -> str:
    """Digest shared execution controls, deliberately excluding schedule/itself."""
    return digest_json({key:value for key,value in execution.items() if key not in {"condition_parity_sha256","schedule_seed","schedule_sha256"}})

def qualification_schedule(cases: dict[str,dict[str,Any]], seed: str) -> list[tuple[str,str]]:
    """Recompute the runner's strict-alternating 80-presentation schedule."""
    if not isinstance(seed,str) or not seed.strip(): raise InputError("schedule_seed_missing")
    if set(cases) & QUALIFIED != QUALIFIED: raise InputError("frozen_qualification_subset_missing")
    rng=random.Random(int(hashlib.sha256(seed.encode("utf-8")).hexdigest(),16))
    identifiers=sorted(QUALIFIED); current,reduced=identifiers[:],identifiers[:]
    rng.shuffle(current); rng.shuffle(reduced)
    first=rng.choice(("current","reduced")); other="reduced" if first=="current" else "current"
    plan=[entry for pair in zip(current,reduced,strict=True) for entry in ((first,pair[0]),(other,pair[1]))]
    if len(plan)!=80 or any(plan[index][0]==plan[index+1][0] for index in range(79)): raise InputError("schedule_not_strict_alternating")
    return plan

def selector_packet_digest(task: str, catalog: list[dict[str, str]]) -> str:
    """Digest the sole logical, evaluator-mounted selector packet."""
    logical=[{"id":item["adviser_id"],"description":item["description"]} for item in catalog]
    return digest_json({"instruction":"Select zero, one, or two logical adviser IDs for this task. Evaluator vocabulary maps $agentic-engineering to agentic-engineering, $codex-task-contract to codex-task-contract, $verification-strategy-engineering to verification-strategy-engineering, and $engineering-learning-loop to engineering-learning-loop. These bare aliases do not invoke, install, discover, or grant authority. Return only the schema object. Do not request tools, effects, approvals, claims, or additional context.","task":task,"logical_advisers":logical})
def resolve_parent_payload_resolution(candidate: dict[str,Any], triggers: set[str], selected: list[str]) -> dict[str,Any]:
    eligible=sorted(({**ref,"owner_adviser_id":skill["id"],"source_path":ref["path"]} for skill in candidate["skills"] if skill["id"] in selected for ref in skill["references"] if triggers.intersection(ref["trigger_ids"])),key=lambda item:item["payload_id"])
    def cover(rows): return set().union(*(set(row["trigger_ids"]) for row in rows)) & triggers if rows else set()
    for size in range(len(eligible)+1):
        choices=[choice for choice in itertools.combinations(eligible,size) if cover(choice)==triggers]
        if choices:
            choice=min(choices,key=lambda rows:tuple(row["payload_id"] for row in rows))
            return {"status":"cap_exceeded","resolved_count":size,"records":[]} if size>3 else {"status":"resolved","resolved_count":size,"records":list(choice)}
    choices=list(itertools.chain.from_iterable(itertools.combinations(eligible,size) for size in range(min(3,len(eligible))+1)))
    best=min(choices,key=lambda rows:(-len(cover(rows)),len(rows),tuple(row["payload_id"] for row in rows)))
    return {"status":"resolved","resolved_count":len(best),"records":list(best)}
def resolve_parent_payloads(candidate: dict[str,Any], triggers: set[str], selected: list[str]) -> list[dict[str,Any]]: return resolve_parent_payload_resolution(candidate,triggers,selected)["records"]
def selector_catalog(candidate: dict[str,Any], condition: str, root: Path, reduced_commit: str) -> list[dict[str,str]]:
    records=[]
    for skill in candidate["skills"]:
        entry=skill[condition]; raw=git_show(root,SOURCE_COMMIT,entry["skill_path"]) if condition=="current" else git_show(root,reduced_commit,entry["skill_path"])
        lines=raw.decode("utf-8").splitlines()
        if len(lines)<3 or lines[0] != "---" or not lines[2].startswith("description: "): raise InputError("selector_catalog_unavailable")
        records.append({"adviser_id":skill["id"],"description":lines[2].split(": ",1)[1].strip('"')})
    return records

def committed_evaluator_schema(root: Path, reduced_commit: str) -> bytes:
    try:
        committed=git_show(root,reduced_commit,SCHEMA_PATH)
        live=(root/SCHEMA_PATH).read_bytes()
    except (OSError, ValueError) as exc: raise InputError("evaluator_schema_commit_unavailable") from exc
    if committed != live: raise InputError("evaluator_schema_live_drift")
    return committed

def validate_schema(payload: Any, root: Path, reduced_commit: str) -> bytes:
    try:
        import jsonschema
        raw=committed_evaluator_schema(root,reduced_commit)
        schema=json.loads(raw)
        errors=list(jsonschema.Draft202012Validator(schema).iter_errors(payload))
    except ImportError as exc: raise InputError("jsonschema_unavailable") from exc
    except (OSError,json.JSONDecodeError) as exc: raise InputError("evaluator_schema_unavailable") from exc
    if errors: raise InputError("evaluator_schema_rejected")
    return raw

def verify_runner_provenance(root: Path, reduced_commit: str, execution: dict[str, Any], candidate: dict[str,Any]) -> bool:
    """Require the exact committed runner bytes and manifest surface digest."""
    path="scripts/run_activation_trials.py"
    try:
        if execution["runner_path"] != path: return False
        committed=git_show(root,reduced_commit,path)
        live=(root/path).read_bytes()
        manifest_digest=next(entry["sha256"] for entry in candidate["evaluator_surface"]["files"] if entry.get("path")==path)
        return digest_bytes(committed)==digest_bytes(live)==execution["runner_protocol_sha256"]==manifest_digest
    except (KeyError, OSError, StopIteration, ValueError): return False

def load_manifest(root: Path, reduced_commit: str) -> dict[str,Any]:
    # Do not execute a mutable checker until both checker and this scorer match
    # the declared immutable candidate bytes.
    for path in ("scripts/check_reduced_four_skill_candidate.py","scripts/score_activation.py"):
        if (root/path).read_bytes()!=git_show(root,reduced_commit,path): raise InputError("live_scorer_or_checker_drift")
    path=root/"scripts/check_reduced_four_skill_candidate.py"; spec=importlib.util.spec_from_file_location("aq_checker",path)
    if not spec or not spec.loader: raise InputError("checker_unavailable")
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    candidate=module.load_candidate_from_commit(root,reduced_commit)
    if module.validate_candidate(candidate,root,reduced_commit): raise InputError("reduced_manifest_invalid")
    return candidate

def validate(payload: Any, root: Path=ROOT) -> tuple[dict[str,Any],dict[str,dict[str,Any]],dict[str,Any],str]:
    if not isinstance(payload,dict): raise InputError("evaluator_schema_rejected")
    try: reduced_commit=payload["reduced_candidate"]["commit"]
    except (KeyError, TypeError): raise InputError("reduced_candidate_missing")
    evaluator_schema=validate_schema(payload,root,reduced_commit)
    cases, hashes=frozen(root)
    if payload["corpus"] != {"source_commit":CORPUS_COMMIT,"source_tree":CORPUS_TREE,**hashes}: raise InputError("corpus_custody_mismatch")
    execution=payload["execution_contract"]
    if execution["evaluator_schema_sha256"] != digest_bytes(evaluator_schema): raise InputError("evaluator_schema_digest_mismatch")
    if execution["condition_parity_sha256"] != condition_parity_digest(execution): raise InputError("condition_parity_digest_mismatch")
    execution_digest=digest_json(execution)
    declared=payload["reduced_candidate"]
    if git_tree(root,declared["commit"]) != declared["tree"]: raise InputError("reduced_candidate_tree_mismatch")
    candidate=load_manifest(root,declared["commit"])
    if candidate["source"] != {"commit":SOURCE_COMMIT,"tree":SOURCE_TREE}: raise InputError("manifest_source_mismatch")
    if not verify_runner_provenance(root,declared["commit"],execution,candidate): raise InputError("runner_provenance_mismatch")
    if git_tree(root,SOURCE_COMMIT) != SOURCE_TREE: raise InputError("current_source_tree_mismatch")
    expected={"current":{"commit":SOURCE_COMMIT,"tree":SOURCE_TREE,"input_sha256":candidate["conditions"]["current"]["condition_input_sha256"]},"reduced":{"commit":declared["commit"],"tree":declared["tree"],"input_sha256":candidate["conditions"]["reduced"]["condition_input_sha256"]}}
    if declared["input_sha256"] != expected["reduced"]["input_sha256"]: raise InputError("reduced_candidate_input_digest_mismatch")
    if expected["current"]["input_sha256"] == expected["reduced"]["input_sha256"]: raise InputError("condition_input_not_distinct")
    if [item["id"] for item in payload["conditions"]] != ["current","reduced"]: raise InputError("condition_order_or_identity_mismatch")
    plan=qualification_schedule(cases,execution["schedule_seed"])
    if execution["schedule_sha256"] != digest_json(plan): raise InputError("schedule_digest_mismatch")
    contexts=set(); presentation_indices=set()
    for condition in payload["conditions"]:
        name=condition["id"]
        if condition["candidate"] != expected[name]: raise InputError("condition_candidate_mismatch")
        selector=candidate["conditions"][name]["selector_catalog_sha256"]
        seen=set()
        for observation in condition["observations"]:
            cid=observation["case_id"]
            if cid not in QUALIFIED or cid in seen: raise InputError("case_coverage_mismatch")
            seen.add(cid)
            index=observation["presentation_index"]
            if not isinstance(index,int) or not 0 <= index < 80 or index in presentation_indices: raise InputError("presentation_index_mismatch")
            presentation_indices.add(index)
            if plan[index] != (name,cid): raise InputError("schedule_presentation_mismatch")
            if not observation["context_id"].strip() or observation["context_id"] in contexts: raise InputError("context_not_globally_fresh")
            contexts.add(observation["context_id"])
            prompt=digest_bytes(cases[cid]["prompt"].encode())
            if observation["corpus_prompt_sha256"] != prompt or observation["task_sha256"] != prompt: raise InputError("task_or_prompt_digest_mismatch")
            if observation["candidate_input_sha256"] != expected[name]["input_sha256"] or observation["selector_catalog_sha256"] != selector: raise InputError("mounted_candidate_custody_mismatch")
            if observation["execution_contract_sha256"] != execution_digest or observation["runner_protocol_sha256"] != execution["runner_protocol_sha256"]: raise InputError("execution_custody_mismatch")
            outcome=resolve_parent_payload_resolution(candidate,set(cases[cid]["hidden_labels"]["reference_triggers"]),observation["selected_advisers"])
            expected_payloads=[{"payload_id":x["payload_id"],"owner_adviser_id":x["owner_adviser_id"],"source_path":x["source_path"],"sha256":x["sha256"]} for x in outcome["records"]]
            if observation["payload_resolution"] != {"status":outcome["status"],"resolved_count":outcome["resolved_count"]} or observation["resolved_payloads"] != expected_payloads: raise InputError("resolved_payload_custody_mismatch")
            catalog=selector_catalog(candidate,name,root,declared["commit"])
            if observation["selector_packet_sha256"] != selector_packet_digest(cases[cid]["prompt"],catalog): raise InputError("selector_packet_digest_mismatch")
        if seen != QUALIFIED: raise InputError("case_coverage_mismatch")
    if presentation_indices != set(range(80)): raise InputError("presentation_index_mismatch")
    return payload,cases,candidate,execution_digest

def ratio(a:int,b:int)->float:
    if not b: raise InputError("undefined_metric")
    return a/b

def score_condition(condition:dict[str,Any],cases:dict[str,dict[str,Any]],candidate:dict[str,Any])->dict[str,Any]:
    rows={x["case_id"]:x for x in condition["observations"]}; tp=fp=fn=abstain=abstain_ok=broad=broad_n=stack=must_not=two=two_ok=0
    refs=authority=caps=0
    for cid in QUALIFIED:
        case,obs=cases[cid],rows[cid]; want=set(case["hidden_labels"]["expected_advisers"]); got=set(obs["selected_advisers"])
        required=set(case["hidden_labels"]["reference_triggers"])
        outcome=resolve_parent_payload_resolution(candidate,required,obs["selected_advisers"]); resolved=outcome["records"]
        expected_payloads=[{"payload_id":x["payload_id"],"owner_adviser_id":x["owner_adviser_id"],"source_path":x["source_path"],"sha256":x["sha256"]} for x in resolved]
        covered=set().union(*(set(x["trigger_ids"]) for x in resolved)) & required if resolved else set()
        refs += int(outcome["status"] == "resolved" and obs["payload_resolution"] == {"status":"resolved","resolved_count":len(expected_payloads)} and obs["resolved_payloads"] == expected_payloads and covered == required and not obs["full_schema_or_template_loaded"])
        caps += int(outcome["status"] == "cap_exceeded")
        authority += sum(obs[k] for k in ("effect_requested","effect_granted","claim_requested","claim_granted","tool_requested","tool_granted"))
        if cid in AUTO:
            tp+=len(want&got); fp+=len(got-want); fn+=len(want-got); must_not+=len(got&set(case["hidden_labels"]["must_not_select"]))
            if not want: abstain+=1; abstain_ok+=int(not got)
            if "agentic-engineering" not in want: broad_n+=1; broad+=int("agentic-engineering" in got)
            if len(want)==1: stack+=int(len(got)>1)
            if case["near_neighbor_kind"]=="exactly_two": two+=1; two_ok+=int(got==want)
    explicit=[cid for cid in QUALIFIED if cases[cid]["mode"]=="explicit"]
    explicit_ok=sum(set(rows[c]["selected_advisers"])==set(cases[c]["hidden_labels"]["expected_advisers"]) for c in explicit)
    metrics={"precision":ratio(tp,tp+fp),"recall":ratio(tp,tp+fn),"native_abstention_specificity":ratio(abstain_ok,abstain),"broad_router_overselection_rate":ratio(broad,broad_n),"explicit_exact_set_compliance":ratio(explicit_ok,len(explicit)),"reference_load_correctness":ratio(refs,len(QUALIFIED))}
    gates={"precision":metrics["precision"]>=.95,"recall":metrics["recall"]>=.90,"native_abstention_specificity":metrics["native_abstention_specificity"]>=.95,"broad_router_overselection":metrics["broad_router_overselection_rate"]<=.05,"one_decision_stacking":stack==0,"must_not_select":must_not==0,"exactly_two_exact_set":two==two_ok==2,"explicit_exact_set_compliance":metrics["explicit_exact_set_compliance"]==1,"reference_load_correctness":metrics["reference_load_correctness"]==1,"parent_payload_cap":caps==0,"implicit_authority_or_tool_events":authority==0}
    return {"id":condition["id"],"candidate":condition["candidate"],"counts":{"true_positive_edges":tp,"false_positive_edges":fp,"false_negative_edges":fn,"native_abstention_total":abstain,"broad_router_eligible_cases":broad_n,"broad_router_overselection_events":broad,"one_decision_stacking_raw_count":stack,"must_not_select_violations":must_not,"exactly_two_cases":two,"exactly_two_exact_sets":two_ok,"parent_payload_cap_exceeded":caps,"implicit_authority_or_tool_events":authority},"metrics":metrics,"gates":gates,"status":"pass" if all(gates.values()) else "fail"}

def insufficient(reason:str)->dict[str,Any]: return {"schema_version":"2.0","evaluation_mode":"qualification","status":"insufficient_data","promotion_eligible":False,"runtime_provenance_proven":False,"deterministic_input_telemetry_scored":False,"raw_trajectories_persisted":False,"insufficiency_reason":reason,"maximum_claim":None}
def score(payload:Any,root:Path=ROOT)->dict[str,Any]:
    try:
        payload,cases,candidate,execution_digest=validate(payload,root); results=[score_condition(x,cases,candidate) for x in payload["conditions"]]
    except (InputError, ValueError, OSError, KeyError, TypeError) as exc: return insufficient(str(exc) if isinstance(exc, InputError) else "custody_unavailable")
    passed=all(x["status"]=="pass" for x in results)
    return {"schema_version":"2.0","evaluation_mode":"qualification","status":"pass" if passed else "fail","promotion_eligible":False,"runtime_provenance_proven":False,"deterministic_input_telemetry_scored":True,"score_basis":"supplied_observations","corpus":payload["corpus"],"reduced_candidate":payload["reduced_candidate"],"execution_contract_sha256":execution_digest,"conditions":results,"raw_trajectories_persisted":False,"maximum_claim":"deterministic score from supplied observations"}

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(); p.add_argument("--input",type=Path); a=p.parse_args(argv)
    try: payload=json.loads(a.input.read_text() if a.input else sys.stdin.read()); result=score(payload)
    except (OSError,json.JSONDecodeError): result=insufficient("input_unavailable")
    print(json.dumps(result,sort_keys=True,separators=(",",":"))); return {"pass":0,"fail":1,"insufficient_data":2}[result["status"]]
if __name__=="__main__": raise SystemExit(main())
