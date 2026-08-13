use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeSet, HashMap, HashSet};
use std::env;
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process;
use std::time::Instant;

const EXIT_VALIDATION: i32 = 2;
const EXIT_ABSTENTION: i32 = 3;
const MAX_FILE_BYTES: u64 = 2_000_000;
const MAX_RUNTIME_WORDS: usize = 90;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Registry {
    schema_version: String,
    reviewed_on: String,
    entries: Vec<Entry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Entry {
    id: String,
    evidence_class: String,
    phases: Vec<String>,
    tags: Vec<String>,
    platforms: Vec<String>,
    surface_modes: Vec<String>,
    use_when: Vec<String>,
    avoid_when: Vec<String>,
    counterexample: String,
    observable_test: String,
    claim_ceiling: String,
    payload: String,
    source: Source,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Source {
    title: String,
    url: String,
    authority: String,
    reviewed_on: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Query {
    phase: String,
    #[serde(default)]
    tags: Vec<String>,
    #[serde(default = "default_any")]
    platform: String,
    #[serde(default = "default_any")]
    surface_mode: String,
    #[serde(default = "default_max_entries")]
    max_entries: usize,
    #[serde(default = "default_word_budget")]
    word_budget: usize,
    #[serde(default)]
    allow_trends: bool,
}

fn default_any() -> String { "any".to_string() }
fn default_max_entries() -> usize { 3 }
fn default_word_budget() -> usize { 260 }

#[derive(Debug, Clone, Serialize)]
struct CandidateDecision {
    id: String,
    score: i32,
    reason: String,
}

#[derive(Debug, Clone, Serialize)]
struct SelectedEntry {
    id: String,
    evidence_class: String,
    score: i32,
    payload: String,
    words: usize,
    claim_ceiling: String,
    source_title: String,
}

#[derive(Debug, Clone, Serialize)]
struct QueryResult {
    schema_version: &'static str,
    selected: Vec<SelectedEntry>,
    rejected: Vec<CandidateDecision>,
    words_used: usize,
    word_budget: usize,
    valid_abstention: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct StyleFingerprint {
    schema_version: String,
    artifact_id: String,
    domain: String,
    shared_authority: Option<String>,
    surface: FingerprintSurface,
    palette_roles: Vec<String>,
    typography: Vec<String>,
    shape_depth: Vec<String>,
    composition_shell: Vec<String>,
    interaction_signature: Vec<String>,
    density_energy: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct FingerprintSurface {
    lightness: String,
    material: Vec<String>,
}

#[derive(Debug, Clone, Deserialize)]
struct FingerprintHistory {
    fingerprints: Vec<StyleFingerprint>,
}

#[derive(Debug, Clone, Deserialize)]
struct Review {
    schema_version: String,
    entry_id: String,
    entry_sha256: String,
    decision: String,
    reviewer: String,
    basis: String,
    tests_passed: bool,
}

fn read_bounded(path: &Path) -> Result<Vec<u8>, String> {
    let meta = fs::symlink_metadata(path).map_err(|e| format!("{}: {e}", path.display()))?;
    if meta.file_type().is_symlink() {
        return Err(format!("symlink input rejected: {}", path.display()));
    }
    if !meta.is_file() {
        return Err(format!("not a regular file: {}", path.display()));
    }
    if meta.len() > MAX_FILE_BYTES {
        return Err(format!("file exceeds {MAX_FILE_BYTES} bytes: {}", path.display()));
    }
    fs::read(path).map_err(|e| format!("{}: {e}", path.display()))
}

fn parse_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T, String> {
    let bytes = read_bounded(path)?;
    serde_json::from_slice(&bytes).map_err(|e| format!("invalid JSON in {}: {e}", path.display()))
}

fn words(s: &str) -> usize { s.split_whitespace().count() }

fn contains_bidi(s: &str) -> bool {
    s.chars().any(|c| matches!(c, '\u{202A}'..='\u{202E}' | '\u{2066}'..='\u{2069}'))
}

fn safe_token(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 128
        && s.chars().all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-')
}

fn allowed_phase(p: &str) -> bool {
    matches!(p, "brief" | "direct" | "build" | "edit" | "finish" | "parent" | "evaluate" | "systematize")
}

fn allowed_class(c: &str) -> bool { matches!(c, "N" | "P" | "E" | "H" | "T") }

fn validate_url(url: &str) -> bool {
    if url.starts_with("local://") { return true; }
    if !url.starts_with("https://") { return false; }
    let after = &url[8..];
    !after.contains('@') && !after.is_empty()
}

fn injection_like(s: &str) -> bool {
    let l = s.to_ascii_lowercase();
    ["ignore previous", "system prompt", "execute shell", "run this command", "developer message", "jailbreak"]
        .iter().any(|needle| l.contains(needle))
}

fn validate_entry(e: &Entry) -> Vec<String> {
    let mut errors = Vec::new();
    if !safe_token(&e.id) { errors.push(format!("{}: invalid id", e.id)); }
    if !allowed_class(&e.evidence_class) { errors.push(format!("{}: invalid evidence_class", e.id)); }
    if e.phases.is_empty() || e.phases.iter().any(|p| !allowed_phase(p)) {
        errors.push(format!("{}: invalid phases", e.id));
    }
    if e.tags.is_empty() || e.tags.iter().any(|t| !safe_token(t)) {
        errors.push(format!("{}: invalid tags", e.id));
    }
    if e.platforms.is_empty() || e.surface_modes.is_empty() {
        errors.push(format!("{}: platform/surface scope required", e.id));
    }
    if e.counterexample.trim().len() < 8 { errors.push(format!("{}: counterexample required", e.id)); }
    if e.observable_test.trim().len() < 8 { errors.push(format!("{}: observable_test required", e.id)); }
    if e.claim_ceiling.trim().len() < 8 { errors.push(format!("{}: claim_ceiling required", e.id)); }
    if words(&e.payload) > MAX_RUNTIME_WORDS { errors.push(format!("{}: payload exceeds {MAX_RUNTIME_WORDS} words", e.id)); }
    if !validate_url(&e.source.url) { errors.push(format!("{}: unsafe source URL", e.id)); }
    if contains_bidi(&e.payload) || contains_bidi(&e.source.title) { errors.push(format!("{}: bidirectional controls rejected", e.id)); }
    if injection_like(&e.payload) { errors.push(format!("{}: instruction-like source content rejected", e.id)); }
    if e.source.url.contains("checklist.design") && (e.evidence_class != "H" || e.phases.iter().any(|p| p == "direct")) {
        errors.push(format!("{}: Checklist Design entries must remain H-class and outside direct", e.id));
    }
    errors
}

fn validate_registry(r: &Registry) -> Vec<String> {
    let mut errors = Vec::new();
    if r.schema_version != "dj-authorial-12-registry-v1" { errors.push("unexpected registry schema_version".to_string()); }
    let mut ids = HashSet::new();
    for e in &r.entries {
        if !ids.insert(e.id.clone()) { errors.push(format!("duplicate id: {}", e.id)); }
        errors.extend(validate_entry(e));
    }
    errors
}

fn class_base(c: &str) -> i32 {
    match c { "N" => 50, "P" => 40, "E" => 35, "H" => 20, "T" => 10, _ => 0 }
}

fn norm(s: &str) -> String { s.trim().to_ascii_lowercase().replace('_', "-") }

fn eligible_scope(values: &[String], requested: &str) -> bool {
    values.iter().any(|v| v == "any" || norm(v) == norm(requested))
}

fn query_registry(r: &Registry, q: &Query) -> Result<QueryResult, String> {
    if !allowed_phase(&q.phase) { return Err("invalid query phase".to_string()); }
    if q.tags.is_empty() { return Err("query requires at least one explicit tag".to_string()); }
    if q.max_entries == 0 || q.max_entries > 3 { return Err("max_entries must be 1..=3".to_string()); }
    if q.word_budget == 0 || q.word_budget > 500 { return Err("word_budget must be 1..=500".to_string()); }

    let query_tags: HashSet<String> = q.tags.iter().map(|t| norm(t)).collect();
    let mut eligible = Vec::<(i32, usize, &Entry)>::new();
    let mut rejected = Vec::new();

    for e in &r.entries {
        if !e.phases.iter().any(|p| p == &q.phase) {
            rejected.push(CandidateDecision { id: e.id.clone(), score: 0, reason: "phase-ineligible".to_string() });
            continue;
        }
        if e.evidence_class == "T" && !q.allow_trends {
            rejected.push(CandidateDecision { id: e.id.clone(), score: 0, reason: "trend-opt-in-required".to_string() });
            continue;
        }
        if !eligible_scope(&e.platforms, &q.platform) {
            rejected.push(CandidateDecision { id: e.id.clone(), score: 0, reason: "platform-mismatch".to_string() });
            continue;
        }
        if !eligible_scope(&e.surface_modes, &q.surface_mode) {
            rejected.push(CandidateDecision { id: e.id.clone(), score: 0, reason: "surface-mode-mismatch".to_string() });
            continue;
        }
        let matches = e.tags.iter().filter(|t| query_tags.contains(&norm(t))).count();
        if matches == 0 {
            rejected.push(CandidateDecision { id: e.id.clone(), score: class_base(&e.evidence_class), reason: "no-explicit-tag-match".to_string() });
            continue;
        }
        let mut score = class_base(&e.evidence_class) + (matches as i32 * 20);
        if e.platforms.iter().any(|v| norm(v) == norm(&q.platform)) { score += 5; }
        if e.surface_modes.iter().any(|v| norm(v) == norm(&q.surface_mode)) { score += 3; }
        eligible.push((score, matches, e));
    }

    eligible.sort_by(|a, b| b.0.cmp(&a.0).then_with(|| b.1.cmp(&a.1)).then_with(|| a.2.id.cmp(&b.2.id)));
    let mut selected = Vec::new();
    let mut used = 0usize;
    for (score, _, e) in eligible {
        if selected.len() >= q.max_entries { break; }
        let w = words(&e.payload);
        if used + w > q.word_budget {
            rejected.push(CandidateDecision { id: e.id.clone(), score, reason: "word-budget".to_string() });
            continue;
        }
        selected.push(SelectedEntry {
            id: e.id.clone(), evidence_class: e.evidence_class.clone(), score,
            payload: e.payload.clone(), words: w, claim_ceiling: e.claim_ceiling.clone(),
            source_title: e.source.title.clone(),
        });
        used += w;
    }
    let abstain = selected.is_empty();
    Ok(QueryResult { schema_version: "dj-registry-query-result-v1", selected, rejected, words_used: used, word_budget: q.word_budget, valid_abstention: abstain })
}

fn tokens(values: &[String]) -> BTreeSet<String> { values.iter().map(|v| norm(v)).collect() }

fn jaccard(a: &[String], b: &[String]) -> f64 {
    let aa = tokens(a); let bb = tokens(b);
    let union = aa.union(&bb).count();
    if union == 0 { return 1.0; }
    aa.intersection(&bb).count() as f64 / union as f64
}

fn fingerprint_similarity(a: &StyleFingerprint, b: &StyleFingerprint) -> f64 {
    let light = if a.surface.lightness == b.surface.lightness { 1.0 } else { 0.0 };
    0.04 * light
        + 0.12 * jaccard(&a.surface.material, &b.surface.material)
        + 0.18 * jaccard(&a.palette_roles, &b.palette_roles)
        + 0.16 * jaccard(&a.typography, &b.typography)
        + 0.10 * jaccard(&a.shape_depth, &b.shape_depth)
        + 0.18 * jaccard(&a.composition_shell, &b.composition_shell)
        + 0.12 * jaccard(&a.interaction_signature, &b.interaction_signature)
        + 0.10 * jaccard(&a.density_energy, &b.density_energy)
}

fn compare_fingerprints(current: &StyleFingerprint, history: &[StyleFingerprint], threshold: f64) -> Value {
    let mut comparisons = Vec::new();
    let mut max_unrelated = 0.0f64;
    let mut max_id = None::<String>;
    for prior in history {
        let sim = fingerprint_similarity(current, prior);
        let shared = current.shared_authority.is_some() && current.shared_authority == prior.shared_authority;
        let unrelated = norm(&current.domain) != norm(&prior.domain) && !shared;
        if unrelated && sim > max_unrelated { max_unrelated = sim; max_id = Some(prior.artifact_id.clone()); }
        comparisons.push(json!({"artifact_id": prior.artifact_id, "domain": prior.domain, "similarity": sim, "shared_authority_exemption": shared, "unrelated": unrelated}));
    }
    json!({
        "schema_version": "dj-style-fingerprint-comparison-v1",
        "artifact_id": current.artifact_id,
        "threshold": threshold,
        "max_unrelated_similarity": max_unrelated,
        "most_similar_unrelated": max_id,
        "advisory_flag": max_unrelated >= threshold,
        "authority": "advisory-only",
        "comparisons": comparisons
    })
}

fn validate_fingerprint(f: &StyleFingerprint) -> Vec<String> {
    let mut e = Vec::new();
    if f.schema_version != "dj-authorial-12-style-fingerprint-v1" { e.push("unexpected fingerprint schema".to_string()); }
    if f.artifact_id.trim().len() < 3 || f.domain.trim().len() < 3 { e.push("artifact_id and domain required".to_string()); }
    for (name, values) in [
        ("material", &f.surface.material), ("palette_roles", &f.palette_roles),
        ("typography", &f.typography), ("shape_depth", &f.shape_depth),
        ("composition_shell", &f.composition_shell), ("interaction_signature", &f.interaction_signature),
        ("density_energy", &f.density_energy)
    ] {
        if values.is_empty() || values.iter().any(|v| !safe_token(v)) { e.push(format!("invalid {name}")); }
    }
    e
}

fn validate_truth_spine(v: &Value) -> Vec<String> {
    let mut e = Vec::new();
    if v.get("schema_version").and_then(Value::as_str) != Some("dj-authorial-12-truth-spine-v1") { e.push("unexpected truth-spine schema".to_string()); }
    for name in ["product_truth", "derived_values", "identity_invariants"] {
        let Some(arr) = v.get(name).and_then(Value::as_array) else { e.push(format!("{name} must be an array")); continue; };
        let mut ids = HashSet::new();
        for item in arr {
            for key in ["id", "assertion", "source", "observable_test"] {
                if item.get(key).and_then(Value::as_str).map(str::trim).unwrap_or("").is_empty() { e.push(format!("{name}: missing {key}")); }
            }
            if let Some(id) = item.get("id").and_then(Value::as_str) {
                if !ids.insert(id.to_string()) { e.push(format!("{name}: duplicate id {id}")); }
            }
        }
    }
    let Some(states) = v.get("required_states").and_then(Value::as_array) else { e.push("required_states must be an array".to_string()); return e; };
    if states.is_empty() { e.push("required_states cannot be empty".to_string()); }
    let mut ids = HashSet::new();
    for state in states {
        let id = state.get("id").and_then(Value::as_str).unwrap_or("");
        if id.is_empty() { e.push("state missing id".to_string()); }
        if !ids.insert(id.to_string()) { e.push(format!("duplicate state id {id}")); }
        if state.get("entry").and_then(Value::as_str).unwrap_or("").is_empty() { e.push(format!("state {id}: missing entry")); }
        if state.get("visible_result").and_then(Value::as_str).unwrap_or("").is_empty() { e.push(format!("state {id}: missing visible_result")); }
        if state.get("reachable_by").and_then(Value::as_array).map(|a| a.is_empty()).unwrap_or(true) { e.push(format!("state {id}: reachable_by required")); }
    }
    for key in ["external_effects", "confirmation", "truthful_receipt"] {
        if v.get("effect_boundary").and_then(|x| x.get(key)).and_then(Value::as_str).unwrap_or("").is_empty() { e.push(format!("effect_boundary: missing {key}")); }
    }
    let min = v.get("narrow_width").and_then(|x| x.get("minimum_css_width")).and_then(Value::as_u64).unwrap_or(0);
    if !(320..=480).contains(&min) { e.push("narrow_width.minimum_css_width must be 320..=480".to_string()); }
    if v.get("narrow_width").and_then(|x| x.get("must_remain_visible")).and_then(Value::as_array).map(|a| a.is_empty()).unwrap_or(true) { e.push("narrow_width.must_remain_visible required".to_string()); }
    if v.get("narrow_width").and_then(|x| x.get("overflow_test")).and_then(Value::as_str).unwrap_or("").is_empty() { e.push("narrow_width.overflow_test required".to_string()); }
    e
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut h = Sha256::new(); h.update(bytes); format!("{:x}", h.finalize())
}

fn merge_reviewed_entry(registry_path: &Path, draft_path: &Path, review_path: &Path, output_path: &Path) -> Result<Value, String> {
    if output_path.exists() { return Err("output path already exists".to_string()); }
    let mut registry: Registry = parse_json(registry_path)?;
    let registry_errors = validate_registry(&registry);
    if !registry_errors.is_empty() { return Err(format!("input registry invalid: {}", registry_errors.join("; "))); }
    let draft_bytes = read_bounded(draft_path)?;
    let draft: Entry = serde_json::from_slice(&draft_bytes).map_err(|e| format!("invalid draft JSON: {e}"))?;
    let entry_errors = validate_entry(&draft);
    if !entry_errors.is_empty() { return Err(entry_errors.join("; ")); }
    let review: Review = parse_json(review_path)?;
    if review.schema_version != "dj-authorial-12-entry-review-v1" { return Err("unexpected review schema".to_string()); }
    if review.decision != "approve" || !review.tests_passed { return Err("review is not approved with tests_passed=true".to_string()); }
    if review.reviewer.trim().is_empty() || review.basis.trim().len() < 8 { return Err("reviewer and meaningful basis required".to_string()); }
    if review.entry_id != draft.id { return Err("review entry_id mismatch".to_string()); }
    let actual = sha256_hex(&draft_bytes);
    if actual != review.entry_sha256 { return Err("review hash does not bind exact draft bytes".to_string()); }
    if registry.entries.iter().any(|e| e.id == draft.id) { return Err("entry id already exists".to_string()); }
    registry.entries.push(draft.clone());
    registry.entries.sort_by(|a, b| a.id.cmp(&b.id));
    let errors = validate_registry(&registry);
    if !errors.is_empty() { return Err(errors.join("; ")); }
    let parent = output_path.parent().unwrap_or_else(|| Path::new("."));
    fs::create_dir_all(parent).map_err(|e| format!("create output directory: {e}"))?;
    let tmp = parent.join(format!(".{}.tmp", output_path.file_name().and_then(|x| x.to_str()).unwrap_or("registry")));
    let bytes = serde_json::to_vec_pretty(&registry).map_err(|e| e.to_string())?;
    {
        let mut f = fs::File::create(&tmp).map_err(|e| format!("create temp: {e}"))?;
        f.write_all(&bytes).map_err(|e| format!("write temp: {e}"))?;
        f.sync_all().map_err(|e| format!("sync temp: {e}"))?;
    }
    fs::rename(&tmp, output_path).map_err(|e| format!("atomic rename: {e}"))?;
    Ok(json!({"schema_version": "dj-registry-merge-result-v1", "changed": true, "entry_id": draft.id, "entry_sha256": actual, "output": output_path.display().to_string(), "receipt_created": false}))
}

fn print_help() {
    println!(r#"dj-registry — deterministic evidence retrieval for Design Judgment Authorial 12

USAGE
  dj-registry validate <registry.json>
  dj-registry query <registry.json> <query.json>
  dj-registry compile <registry.json> <query.json>
  dj-registry validate-truth-spine <truth-spine.json>
  dj-registry compare-fingerprints <current.json> <history.json> [threshold]
  dj-registry merge-reviewed-entry <registry.json> <draft.json> <review.json> <output.json>
  dj-registry bench <registry.json>
  dj-registry help

BOUNDARY
  The model interprets the task and emits a structured query. This binary validates,
  filters, ranks, and compiles evidence. It does not choose visual direction or score taste.

ABSTENTION
  Query exit code 3 means no entry cleared eligibility and tag requirements. This is a
  valid result. Do not broaden automatically.

RECEIPTS
  Read commands never write files. merge-reviewed-entry writes only the requested new
  registry output and creates no receipt.

EXIT CODES
  0 success · 2 validation/unsafe input · 3 valid abstention"#);
}

fn emit(value: &impl Serialize) { println!("{}", serde_json::to_string_pretty(value).unwrap()); }

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 { print_help(); return; }
    let result: Result<Option<i32>, String> = match args[1].as_str() {
        "help" | "--help" | "-h" => { print_help(); Ok(None) }
        "validate" if args.len() == 3 => {
            let r: Registry = parse_json(Path::new(&args[2]))?;
            let errors = validate_registry(&r);
            emit(&json!({"valid": errors.is_empty(), "entry_count": r.entries.len(), "errors": errors}));
            if errors.is_empty() { Ok(None) } else { Ok(Some(EXIT_VALIDATION)) }
        }
        "query" | "compile" if args.len() == 4 => {
            let r: Registry = parse_json(Path::new(&args[2]))?;
            let errors = validate_registry(&r);
            if !errors.is_empty() { Err(errors.join("; ")) } else {
                let q: Query = parse_json(Path::new(&args[3]))?;
                let out = query_registry(&r, &q)?;
                let abstain = out.valid_abstention;
                emit(&out);
                if abstain { Ok(Some(EXIT_ABSTENTION)) } else { Ok(None) }
            }
        }
        "validate-truth-spine" if args.len() == 3 => {
            let v: Value = parse_json(Path::new(&args[2]))?;
            let errors = validate_truth_spine(&v);
            emit(&json!({"valid": errors.is_empty(), "errors": errors}));
            if errors.is_empty() { Ok(None) } else { Ok(Some(EXIT_VALIDATION)) }
        }
        "compare-fingerprints" if args.len() == 4 || args.len() == 5 => {
            let current: StyleFingerprint = parse_json(Path::new(&args[2]))?;
            let errors = validate_fingerprint(&current);
            if !errors.is_empty() { Err(errors.join("; ")) } else {
                let bytes = read_bounded(Path::new(&args[3]))?;
                let history: Vec<StyleFingerprint> = match serde_json::from_slice::<FingerprintHistory>(&bytes) {
                    Ok(h) => h.fingerprints,
                    Err(_) => serde_json::from_slice(&bytes).map_err(|e| format!("invalid fingerprint history: {e}"))?,
                };
                for h in &history { let e = validate_fingerprint(h); if !e.is_empty() { return fail(e.join("; ")); } }
                let threshold = args.get(4).and_then(|s| s.parse::<f64>().ok()).unwrap_or(0.72);
                emit(&compare_fingerprints(&current, &history, threshold));
                Ok(None)
            }
        }
        "merge-reviewed-entry" if args.len() == 6 => {
            let out = merge_reviewed_entry(Path::new(&args[2]), Path::new(&args[3]), Path::new(&args[4]), Path::new(&args[5]))?;
            emit(&out); Ok(None)
        }
        "bench" if args.len() == 3 => {
            let r: Registry = parse_json(Path::new(&args[2]))?;
            let errors = validate_registry(&r);
            if !errors.is_empty() { Err(errors.join("; ")) } else {
                let q = Query { phase: "edit".into(), tags: vec!["salience".into(), "counterexample".into()], platform: "web".into(), surface_mode: "any".into(), max_entries: 3, word_budget: 260, allow_trends: false };
                let start = Instant::now();
                let mut selected = 0usize;
                for _ in 0..10_000 { selected += query_registry(&r, &q)?.selected.len(); }
                let elapsed = start.elapsed();
                emit(&json!({"iterations": 10000, "elapsed_ms": elapsed.as_secs_f64()*1000.0, "mean_us": elapsed.as_secs_f64()*1000000.0/10000.0, "selected_total": selected, "files_written": 0}));
                Ok(None)
            }
        }
        _ => Err("invalid command or arguments; run dj-registry help".to_string())
    };
    match result {
        Ok(Some(code)) => process::exit(code),
        Ok(None) => {},
        Err(e) => { eprintln!("error: {e}"); process::exit(EXIT_VALIDATION); }
    }
}

fn fail(message: String) -> ! { eprintln!("error: {message}"); process::exit(EXIT_VALIDATION); }

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    static N: AtomicUsize = AtomicUsize::new(0);
    fn temp_dir() -> PathBuf {
        let n = N.fetch_add(1, Ordering::SeqCst);
        let p = env::temp_dir().join(format!("dj-registry-test-{}-{n}", process::id()));
        let _ = fs::remove_dir_all(&p); fs::create_dir_all(&p).unwrap(); p
    }
    fn source() -> Source { Source { title:"Test".into(), url:"https://example.com/evidence".into(), authority:"test".into(), reviewed_on:"2026-08-12".into() } }
    fn entry(id:&str, phase:&str, tag:&str, class:&str) -> Entry { Entry { id:id.into(), evidence_class:class.into(), phases:vec![phase.into()], tags:vec![tag.into()], platforms:vec!["any".into()], surface_modes:vec!["any".into()], use_when:vec!["needed".into()], avoid_when:vec!["not needed".into()], counterexample:"A valid contextual exception exists.".into(), observable_test:"Observe the intended result directly.".into(), claim_ceiling:"Test claim ceiling only.".into(), payload:"Use this compact positive procedure for the tested decision.".into(), source:source() } }
    fn registry(entries:Vec<Entry>) -> Registry { Registry { schema_version:"dj-authorial-12-registry-v1".into(), reviewed_on:"2026-08-12".into(), entries } }
    fn fp(id:&str, domain:&str, authority:Option<&str>) -> StyleFingerprint { StyleFingerprint { schema_version:"dj-authorial-12-style-fingerprint-v1".into(), artifact_id:id.into(), domain:domain.into(), shared_authority:authority.map(str::to_string), surface:FingerprintSurface{lightness:"light".into(), material:vec!["paper".into()]}, palette_roles:vec!["moss".into(),"coral".into()], typography:vec!["editorial-serif".into()], shape_depth:vec!["rounded-panels".into(),"soft-shadow".into()], composition_shell:vec!["hero-plus-card-grid".into()], interaction_signature:vec!["drawer-inspector".into()], density_energy:vec!["calm-editorial".into()] } }

    #[test] fn validates_registry() { assert!(validate_registry(&registry(vec![entry("salience-test","edit","salience","E")])).is_empty()); }
    #[test] fn rejects_duplicate_ids() { assert!(validate_registry(&registry(vec![entry("same","edit","a","E"),entry("same","edit","b","H")])).iter().any(|x|x.contains("duplicate"))); }
    #[test] fn query_selects_explicit_tag() { let r=registry(vec![entry("a","edit","salience","E"),entry("b","direct","salience","E")]); let q=Query{phase:"edit".into(),tags:vec!["salience".into()],platform:"any".into(),surface_mode:"any".into(),max_entries:3,word_budget:260,allow_trends:false}; let o=query_registry(&r,&q).unwrap(); assert_eq!(o.selected[0].id,"a"); }
    #[test] fn query_abstains_without_match() { let r=registry(vec![entry("a","edit","salience","E")]); let q=Query{phase:"edit".into(),tags:vec!["motion".into()],platform:"any".into(),surface_mode:"any".into(),max_entries:3,word_budget:260,allow_trends:false}; assert!(query_registry(&r,&q).unwrap().valid_abstention); }
    #[test] fn trend_requires_opt_in() { let r=registry(vec![entry("trend","edit","trend","T")]); let q=Query{phase:"edit".into(),tags:vec!["trend".into()],platform:"any".into(),surface_mode:"any".into(),max_entries:3,word_budget:260,allow_trends:false}; assert!(query_registry(&r,&q).unwrap().valid_abstention); }
    #[test] fn checklist_cannot_enter_direct() { let mut e=entry("checklist","direct","payment","H"); e.source.url="https://www.checklist.design/flows/making-a-payment".into(); assert!(validate_entry(&e).iter().any(|x|x.contains("Checklist"))); }
    #[test] fn fingerprint_flags_unrelated_house_style() { let a=fp("a","library",None); let b=fp("b","agentic",None); let v=compare_fingerprints(&a,&[b],0.72); assert_eq!(v["advisory_flag"],true); }
    #[test] fn shared_authority_exempts_similarity() { let a=fp("a","home","brand-x".into()); let b=fp("b","settings","brand-x".into()); let v=compare_fingerprints(&a,&[b],0.72); assert_eq!(v["advisory_flag"],false); }
    #[test] fn truth_spine_rejects_missing_states() { let v=json!({"schema_version":"dj-authorial-12-truth-spine-v1","product_truth":[],"derived_values":[],"identity_invariants":[],"required_states":[],"effect_boundary":{"external_effects":"none","confirmation":"n/a","truthful_receipt":"local only"},"narrow_width":{"minimum_css_width":320,"must_remain_visible":["decision"],"overflow_test":"scrollWidth equals clientWidth"}}); assert!(!validate_truth_spine(&v).is_empty()); }
    #[test] fn query_is_byte_inert() { let d=temp_dir(); let p=d.join("sentinel"); fs::write(&p,b"same").unwrap(); let before=fs::read(&p).unwrap(); let r=registry(vec![entry("a","edit","salience","E")]); let q=Query{phase:"edit".into(),tags:vec!["salience".into()],platform:"any".into(),surface_mode:"any".into(),max_entries:3,word_budget:260,allow_trends:false}; let _=query_registry(&r,&q).unwrap(); assert_eq!(before,fs::read(&p).unwrap()); assert_eq!(fs::read_dir(&d).unwrap().count(),1); }
    #[test] fn reviewed_merge_is_exact_and_receipt_free() { let d=temp_dir(); let rp=d.join("registry.json"); let dp=d.join("draft.json"); let vp=d.join("review.json"); let op=d.join("out.json"); fs::write(&rp,serde_json::to_vec_pretty(&registry(vec![])).unwrap()).unwrap(); let e=entry("new-entry","edit","salience","H"); let bytes=serde_json::to_vec_pretty(&e).unwrap(); fs::write(&dp,&bytes).unwrap(); let review=json!({"schema_version":"dj-authorial-12-entry-review-v1","entry_id":"new-entry","entry_sha256":sha256_hex(&bytes),"decision":"approve","reviewer":"independent-reviewer","basis":"Counterexample and held-out tests passed.","tests_passed":true}); fs::write(&vp,serde_json::to_vec_pretty(&review).unwrap()).unwrap(); let out=merge_reviewed_entry(&rp,&dp,&vp,&op).unwrap(); assert_eq!(out["receipt_created"],false); assert!(op.exists()); assert_eq!(fs::read_dir(&d).unwrap().count(),4); }
    #[test] fn reviewed_merge_rejects_hash_mismatch() { let d=temp_dir(); let rp=d.join("registry.json"); let dp=d.join("draft.json"); let vp=d.join("review.json"); let op=d.join("out.json"); fs::write(&rp,serde_json::to_vec_pretty(&registry(vec![])).unwrap()).unwrap(); let e=entry("new-entry","edit","salience","H"); fs::write(&dp,serde_json::to_vec_pretty(&e).unwrap()).unwrap(); let review=json!({"schema_version":"dj-authorial-12-entry-review-v1","entry_id":"new-entry","entry_sha256":"bad","decision":"approve","reviewer":"reviewer","basis":"A sufficiently detailed review basis.","tests_passed":true}); fs::write(&vp,serde_json::to_vec_pretty(&review).unwrap()).unwrap(); assert!(merge_reviewed_entry(&rp,&dp,&vp,&op).unwrap_err().contains("hash")); assert!(!op.exists()); }
}
