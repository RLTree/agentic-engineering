#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
PLUGIN="$ROOT/plugin/design-judgment"
ENGINE="$PLUGIN/engine-rust/target/release/dj-registry"

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

[[ -x "$ENGINE" ]] || fail "release registry binary missing; build engine-rust first"
[[ -f "$PLUGIN/registry/registry.json" ]] || fail "registry missing"
[[ -f "$ROOT/EVALUATION-PROTOCOL.md" ]] || fail "evaluation protocol missing"
[[ -f "$ROOT/analysis/FORENSIC-REPORT.md" ]] || fail "forensic report missing"

# Producer package must not contain Python runtime or receipt churn directories.
if find "$PLUGIN" -type f \( -name '*.py' -o -name '*.pyc' \) -print -quit | grep -q .; then
  fail "Python runtime found inside producer plugin"
fi
if find "$PLUGIN" -type d \( -name '__pycache__' -o -name 'receipts' \) -print -quit | grep -q .; then
  fail "cache or receipts directory found inside producer plugin"
fi
pass "no Python runtime, caches, or receipt directory"

# All JSON must parse.
while IFS= read -r -d '' f; do jq -e . "$f" >/dev/null || fail "invalid JSON: $f"; done < <(find "$ROOT" -type f -name '*.json' -print0)
pass "all JSON parses"

# Active stage skills remain compact.
while IFS= read -r -d '' f; do
  words=$(wc -w < "$f" | tr -d ' ')
  [[ "$words" -le 520 ]] || fail "skill exceeds 520 words: $f ($words)"
done < <(find "$PLUGIN" -type f -name SKILL.md -print0)
pass "all active skill bodies are <= 520 words"

# Registry validation and representative retrieval.
"$ENGINE" validate "$PLUGIN/registry/registry.json" | jq -e '.valid == true and .entry_count >= 15' >/dev/null
"$ENGINE" query "$PLUGIN/registry/registry.json" "$PLUGIN/examples/query-direct.json" | jq -e '.valid_abstention == false and (.selected|length) >= 2 and .words_used <= .word_budget' >/dev/null
"$ENGINE" validate-truth-spine "$PLUGIN/examples/truth-spine.json" | jq -e '.valid == true' >/dev/null
"$ENGINE" compare-fingerprints "$PLUGIN/examples/fingerprint-current.json" "$PLUGIN/examples/fingerprint-history.json" 0.72 | jq -e '.advisory_flag == true and .authority == "advisory-only"' >/dev/null
pass "registry query, Truth Spine, and fingerprint examples pass"

# Read commands must be byte-inert and receipt-free.
before=$(mktemp)
after=$(mktemp)
trap 'rm -f "$before" "$after"' EXIT
find "$PLUGIN" -type f ! -path '*/target/*' -print0 | sort -z | xargs -0 sha256sum > "$before"
"$ENGINE" validate "$PLUGIN/registry/registry.json" >/dev/null
"$ENGINE" query "$PLUGIN/registry/registry.json" "$PLUGIN/examples/query-direct.json" >/dev/null
"$ENGINE" validate-truth-spine "$PLUGIN/examples/truth-spine.json" >/dev/null
"$ENGINE" compare-fingerprints "$PLUGIN/examples/fingerprint-current.json" "$PLUGIN/examples/fingerprint-history.json" >/dev/null
find "$PLUGIN" -type f ! -path '*/target/*' -print0 | sort -z | xargs -0 sha256sum > "$after"
cmp -s "$before" "$after" || fail "read commands changed plugin bytes"
if find "$PLUGIN" -type f -iname '*receipt*' -print -quit | grep -q .; then
  fail "unexpected receipt file in producer plugin"
fi
pass "read commands are byte-inert and receipt-free"

# Reject obvious path hazards and symlinks.
if find "$ROOT" -type l -print -quit | grep -q .; then fail "symlink found in package tree"; fi
if find "$ROOT" -path '*/../*' -print -quit | grep -q .; then fail "unsafe path found"; fi
pass "no symlinks or unsafe paths"

# Benchmark is informational, but must execute and remain read-only.
"$ENGINE" bench "$PLUGIN/registry/registry.json" | jq -e '.iterations == 10000 and .files_written == 0 and .mean_us < 5000' >/dev/null
pass "registry benchmark gate"

printf '\nAuthorial 12 package validation passed.\n'
