from __future__ import annotations
import copy, json, os, subprocess, sys, unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import score_activation as aq

ROOT=Path(__file__).resolve().parents[1]

class AQScorerTests(unittest.TestCase):
 def setUp(self):
  self.cases,self.hashes=aq.frozen(ROOT)
  self.manifest=json.loads((ROOT/"evals/foundation-v4/reduced-four-skills/candidate.json").read_text())
  self.reduced_commit="f"*40; self.reduced_tree="e"*40
 def runtime(self):
  return patch.multiple(aq,load_manifest=lambda root,commit:self.manifest,git_tree=lambda root,commit: aq.SOURCE_TREE if commit==aq.SOURCE_COMMIT else aq.CORPUS_TREE if commit==aq.CORPUS_COMMIT else self.reduced_tree,committed_evaluator_schema=lambda root,commit:(ROOT/aq.SCHEMA_PATH).read_bytes(),selector_catalog=lambda *args:[{"adviser_id":name,"description":name} for name in aq.ADVISERS],verify_runner_provenance=lambda *args:True)
 def payload(self,mode="synthetic_test"):
  execution={"model":"gpt-5.5","reasoning":"medium","cli_path":"codex","cli_version":"test","cli_sha256":"a"*64,"tools_sha256":"b"*64,"host_surface_sha256":"c"*64,"runner_path":"scripts/run_activation_trials.py","runner_protocol_sha256":"d"*64,"schedule_seed":"synthetic qualification seed","schedule_sha256":"","evaluator_schema_sha256":aq.digest_bytes((ROOT/aq.SCHEMA_PATH).read_bytes()),"zero_write":True,"raw_trajectories_persisted":False,"condition_parity_sha256":""}
  plan=aq.qualification_schedule(self.cases,execution["schedule_seed"]); execution["schedule_sha256"]=aq.digest_json(plan)
  execution["condition_parity_sha256"]=aq.condition_parity_digest(execution)
  digest=aq.digest_json(execution); cs=[]
  for name in ("current","reduced"):
   candidate={"commit":aq.SOURCE_COMMIT,"tree":aq.SOURCE_TREE,"input_sha256":self.manifest["conditions"][name]["condition_input_sha256"]} if name=="current" else {"commit":self.reduced_commit,"tree":self.reduced_tree,"input_sha256":self.manifest["conditions"][name]["condition_input_sha256"]}
   rows=[]
   for cid in sorted(aq.QUALIFIED):
    case=self.cases[cid]; selected=list(case["hidden_labels"]["expected_advisers"]); expected=[{"payload_id":x["payload_id"],"owner_adviser_id":x["owner_adviser_id"],"source_path":x["source_path"],"sha256":x["sha256"]} for x in aq.resolve_parent_payloads(self.manifest,set(case["hidden_labels"]["reference_triggers"]),selected)]
    prompt=aq.digest_bytes(case["prompt"].encode()); selector=self.manifest["conditions"][name]["selector_catalog_sha256"]; presentation_index=next(index for index,item in enumerate(plan) if item==(name,cid)); rows.append({"case_id":cid,"presentation_index":presentation_index,"context_id":f"{name}-{cid}","corpus_prompt_sha256":prompt,"task_sha256":prompt,"candidate_input_sha256":candidate["input_sha256"],"selector_catalog_sha256":selector,"selector_packet_sha256":aq.selector_packet_digest(case["prompt"],[{"adviser_id":x,"description":x} for x in aq.ADVISERS]),"execution_contract_sha256":digest,"runner_protocol_sha256":execution["runner_protocol_sha256"],"parse_status":"parsed","selected_advisers":selected,"payload_resolution":{"status":"resolved","resolved_count":len(expected)},"resolved_payloads":expected,"effect_requested":False,"effect_granted":False,"claim_requested":False,"claim_granted":False,"tool_requested":False,"tool_granted":False,"full_schema_or_template_loaded":False})
   cs.append({"id":name,"candidate":candidate,"adviser_universe":list(aq.ADVISERS),"observations":rows})
  return {"schema_version":"3.0","evaluation_mode":"qualification","provenance_mode":mode,"corpus":{"source_commit":aq.CORPUS_COMMIT,"source_tree":aq.CORPUS_TREE,**self.hashes},"reduced_candidate":{"commit":self.reduced_commit,"tree":self.reduced_tree,"input_sha256":self.manifest["conditions"]["reduced"]["condition_input_sha256"]},"execution_contract":execution,"conditions":cs}
 def row(self,p,condition,cid): return next(x for c in p["conditions"] if c["id"]==condition for x in c["observations"] if x["case_id"]==cid)
 def remount(self,p,condition,cid):
  row=self.row(p,condition,cid); case=self.cases[cid]; outcome=aq.resolve_parent_payload_resolution(self.manifest,set(case["hidden_labels"]["reference_triggers"]),row["selected_advisers"])
  row["payload_resolution"]={"status":outcome["status"],"resolved_count":outcome["resolved_count"]}
  row["resolved_payloads"]=[{"payload_id":x["payload_id"],"owner_adviser_id":x["owner_adviser_id"],"source_path":x["source_path"],"sha256":x["sha256"]} for x in outcome["records"]]
 def test_synthetic_and_live_claim_ceilings(self):
  with self.runtime():
   result=aq.score(self.payload(),ROOT); self.assertEqual(result["status"],"pass"); self.assertFalse(result["promotion_eligible"]); self.assertFalse(result["runtime_provenance_proven"]); self.assertTrue(result["deterministic_input_telemetry_scored"]); self.assertEqual(result["maximum_claim"],"deterministic score from supplied observations")
   result=aq.score(self.payload("live_runner"),ROOT); self.assertEqual(result["status"],"pass"); self.assertFalse(result["promotion_eligible"]); self.assertFalse(result["runtime_provenance_proven"]); self.assertTrue(result["deterministic_input_telemetry_scored"])
   rendered=json.dumps(result)
   self.assertNotIn("live_runner",rendered); self.assertNotIn("provider",rendered); self.assertNotIn("product",rendered)
   self.assertFalse(hasattr(aq,"score_evaluator_owned")); self.assertFalse(hasattr(aq,"EvaluatorRunEvidence"))
 def test_thresholds_and_noncompensation(self):
  p=self.payload()
  for cid in ("AQ3-H-001","AQ3-H-002","AQ3-H-003","AQ3-H-004"):
   self.row(p,"reduced",cid)["selected_advisers"]=[]; self.row(p,"reduced",cid)["resolved_payloads"]=[]; self.remount(p,"reduced",cid)
  with self.runtime():
   r=aq.score(p,ROOT); self.assertEqual(r["status"],"fail"); self.assertEqual(r["conditions"][0]["status"],"pass"); self.assertFalse(r["runtime_provenance_proven"]); self.assertTrue(r["deterministic_input_telemetry_scored"]); self.assertEqual(r["maximum_claim"],"deterministic score from supplied observations")
  p=self.payload(); self.row(p,"current","AQ3-H-025")["selected_advisers"]=["agentic-engineering"]
  # Its matching parent payload set must follow the selected set, so this is complete poor telemetry.
  self.row(p,"current","AQ3-H-025")["resolved_payloads"]=[]
  self.remount(p,"current","AQ3-H-025")
  self.row(p,"current","AQ3-H-026")["selected_advisers"]=["agentic-engineering"]
  self.row(p,"current","AQ3-H-026")["resolved_payloads"]=[]
  self.remount(p,"current","AQ3-H-026")
  with self.runtime():
   r=aq.score(p,ROOT)["conditions"][0]; self.assertGreater(r["metrics"]["broad_router_overselection_rate"],.05); self.assertFalse(r["gates"]["broad_router_overselection"])
 def test_must_not_and_exactly_two_gates(self):
  p=self.payload(); self.row(p,"current","AQ3-H-007")["selected_advisers"].append("agentic-engineering")
  with self.runtime(): r=aq.score(p,ROOT)["conditions"][0]; self.assertFalse(r["gates"]["must_not_select"])
  p=self.payload(); self.row(p,"current","AQ3-H-031")["selected_advisers"]=["agentic-engineering"]
  self.row(p,"current","AQ3-H-031")["resolved_payloads"]=[{"payload_id":x["payload_id"],"owner_adviser_id":x["owner_adviser_id"],"source_path":x["source_path"],"sha256":x["sha256"]} for x in aq.resolve_parent_payloads(self.manifest,set(self.cases["AQ3-H-031"]["hidden_labels"]["reference_triggers"]),["agentic-engineering"])]
  self.remount(p,"current","AQ3-H-031")
  with self.runtime(): r=aq.score(p,ROOT)["conditions"][0]; self.assertFalse(r["gates"]["exactly_two_exact_set"])
 def test_wrong_nonprohibited_adviser_with_empty_payload_is_complete_fail(self):
  p=self.payload(); row=self.row(p,"current","AQ3-H-001"); row["selected_advisers"]=["verification-strategy-engineering"]; self.remount(p,"current","AQ3-H-001")
  with self.runtime():
   result=aq.score(p,ROOT); self.assertEqual(result["status"],"fail"); self.assertFalse(result["conditions"][0]["gates"]["reference_load_correctness"])
 def test_execplan_metric_boundaries_are_direct(self):
  p=self.payload(); condition=p["conditions"][0]; edges=[(cid,a) for cid in sorted(aq.AUTO) for a in self.cases[cid]["hidden_labels"]["expected_advisers"]]
  def choose(n):
   for cid in aq.AUTO: self.row(p,"current",cid)["selected_advisers"]=[]
   for cid,a in edges[:n]: self.row(p,"current",cid)["selected_advisers"].append(a)
  choose(19); self.row(p,"current","AQ3-H-025")["selected_advisers"]=["engineering-learning-loop"]
  r=aq.score_condition(condition,self.cases,self.manifest); self.assertEqual(r["metrics"]["precision"],.95); self.assertTrue(r["gates"]["precision"])
  choose(18); self.row(p,"current","AQ3-H-025")["selected_advisers"]=["engineering-learning-loop"]
  self.assertFalse(aq.score_condition(condition,self.cases,self.manifest)["gates"]["precision"])
  choose(27); self.assertEqual(aq.score_condition(condition,self.cases,self.manifest)["metrics"]["recall"],.9)
  choose(26); self.assertFalse(aq.score_condition(condition,self.cases,self.manifest)["gates"]["recall"])
  p=self.payload(); condition=p["conditions"][0]; self.row(p,"current","AQ3-H-025")["selected_advisers"]=["agentic-engineering"]; self.assertFalse(aq.score_condition(condition,self.cases,self.manifest)["gates"]["native_abstention_specificity"])
  p=self.payload(); condition=p["conditions"][0]; self.row(p,"current","AQ3-H-001")["effect_requested"]=True; self.assertFalse(aq.score_condition(condition,self.cases,self.manifest)["gates"]["implicit_authority_or_tool_events"])
 def test_payload_owner_and_custody_mismatches_are_insufficient(self):
  for mutate in (lambda p:self.row(p,"current","AQ3-H-001")["resolved_payloads"].__setitem__(0,{**self.row(p,"current","AQ3-H-001")["resolved_payloads"][0],"owner_adviser_id":"engineering-learning-loop"}),lambda p:self.row(p,"current","AQ3-H-001").__setitem__("task_sha256","0"*64),lambda p:self.row(p,"current","AQ3-H-001").__setitem__("selector_packet_sha256","0"*64),lambda p:p["reduced_candidate"].__setitem__("input_sha256","0"*64),lambda p:p["execution_contract"].__setitem__("condition_parity_sha256","0"*64),lambda p:p["execution_contract"].__setitem__("model","terra"),lambda p:p["conditions"][1]["candidate"].__setitem__("commit",aq.SOURCE_COMMIT),lambda p:p["conditions"][0]["observations"].__setitem__(0,{**p["conditions"][0]["observations"][0],"context_id":p["conditions"][1]["observations"][0]["context_id"]})):
   with self.subTest(mutate=mutate):
    p=self.payload(); mutate(p)
    with self.runtime(): self.assertEqual(aq.score(p,ROOT)["status"],"insufficient_data")
 def test_forged_capacity_status_is_insufficient_and_true_cap_fails_gate(self):
  p=self.payload(); row=p["conditions"][0]["observations"][0]; row["payload_resolution"]={"status":"cap_exceeded","resolved_count":4}; row["resolved_payloads"]=[]
  with self.runtime(): self.assertEqual(aq.score(p,ROOT)["status"],"insufficient_data")
  candidate={"skills":[{"id":"agentic-engineering","references":[{"payload_id":f"p{i}","path":"plugins/x","sha256":"0"*64,"trigger_ids":[f"t{i}"],"content_class":"compact-reference","full_schema_or_template":False} for i in range(4)]}]}
  outcome=aq.resolve_parent_payload_resolution(candidate,{"t0","t1","t2","t3"},["agentic-engineering"])
  self.assertEqual((outcome["status"],outcome["resolved_count"],outcome["records"]),("cap_exceeded",4,[]))
  with patch.object(aq,"resolve_parent_payload_resolution",return_value=outcome):
   direct=aq.score_condition(p["conditions"][0],self.cases,candidate)
  self.assertEqual(direct["counts"]["parent_payload_cap_exceeded"],40); self.assertFalse(direct["gates"]["parent_payload_cap"])
 def test_schedule_and_index_reds_are_insufficient(self):
  mutations=(
   lambda p:p["execution_contract"].__setitem__("schedule_seed","different seed"),
   lambda p:p["execution_contract"].__setitem__("schedule_sha256","0"*64),
   lambda p:self.row(p,"current",p["conditions"][0]["observations"][0]["case_id"]).__setitem__("presentation_index",80),
   lambda p:self.row(p,"reduced",p["conditions"][1]["observations"][0]["case_id"]).__setitem__("presentation_index",p["conditions"][0]["observations"][0]["presentation_index"]),
   lambda p:self.row(p,"current",p["conditions"][0]["observations"][0]["case_id"]).__setitem__("case_id",p["conditions"][0]["observations"][1]["case_id"]),
  )
  for mutate in mutations:
   with self.subTest(mutate=mutate):
    p=self.payload(); mutate(p)
    with self.runtime(): self.assertEqual(aq.score(p,ROOT)["status"],"insufficient_data")
 def test_runner_provenance_requires_exact_path_and_all_three_digests(self):
  raw=b"runner bytes"; digest=aq.digest_bytes(raw)
  execution={"runner_path":"scripts/run_activation_trials.py","runner_protocol_sha256":digest}
  candidate={"evaluator_surface":{"files":[{"path":"scripts/run_activation_trials.py","sha256":digest}]}}
  with TemporaryDirectory() as temp:
   root=Path(temp); path=root/execution["runner_path"]; path.parent.mkdir(parents=True); path.write_bytes(raw)
   with patch.object(aq,"git_show",return_value=raw):
    self.assertTrue(aq.verify_runner_provenance(root,"f"*40,execution,candidate))
    self.assertFalse(aq.verify_runner_provenance(root,"f"*40,{**execution,"runner_path":"scripts/other.py"},candidate))
    self.assertFalse(aq.verify_runner_provenance(root,"f"*40,{**execution,"runner_protocol_sha256":"0"*64},candidate))
    self.assertFalse(aq.verify_runner_provenance(root,"f"*40,execution,{"evaluator_surface":{"files":[{"path":"scripts/run_activation_trials.py","sha256":"0"*64}]}}))
 def test_schema_closed_and_live_corpus_drift_fail_closed(self):
  p=self.payload(); p["counts"]={}
  with self.runtime(): self.assertEqual(aq.score(p,ROOT)["status"],"insufficient_data")
  with TemporaryDirectory() as temp:
   root=Path(temp); (root/"evals/foundation-v4").mkdir(parents=True)
   for path in ("activation-schema.json","activation-authoring.json","activation-heldout.json"):
    raw=(ROOT/"evals/foundation-v4/future-activation-v3"/path).read_bytes(); target=root/"evals/foundation-v4/future-activation-v3"/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw+b" ")
   raw=(ROOT/"evals/foundation-v4/activation-evaluator-schema.json").read_bytes(); (root/"evals/foundation-v4/activation-evaluator-schema.json").write_bytes(raw+b" ")
   with self.runtime(): self.assertEqual(aq.score(self.payload(),root)["status"],"insufficient_data")
 def test_evaluator_schema_is_commit_bound(self):
  with TemporaryDirectory() as temp:
   root=Path(temp); path=root/aq.SCHEMA_PATH; path.parent.mkdir(parents=True); path.write_bytes(b'{"type":"object"}')
   with patch.object(aq,"git_show",return_value=b'{"type":"object","additionalProperties":false}'):
    with self.assertRaises(aq.InputError): aq.committed_evaluator_schema(root,self.reduced_commit)
   with patch.object(aq,"git_show",return_value=path.read_bytes()): self.assertEqual(aq.committed_evaluator_schema(root,self.reduced_commit),path.read_bytes())
 def test_cli_zero_write(self):
  # Invalid stdin still proves CLI has a single JSON stdout record and creates no cwd files.
  with TemporaryDirectory() as temp:
   d=Path(temp); before=list(d.iterdir()); done=subprocess.run([sys.executable,str(ROOT/"scripts/score_activation.py")],cwd=d,input="{}",capture_output=True,text=True,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
   self.assertEqual(done.returncode,2); self.assertEqual(json.loads(done.stdout)["status"],"insufficient_data"); self.assertEqual(before,list(d.iterdir()))
if __name__=="__main__": unittest.main()
