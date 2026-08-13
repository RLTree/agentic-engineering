#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
PLUGIN="$ROOT/plugin/design-judgment"
ENGINE="$PLUGIN/engine-rust/target/release/dj-registry"
DIST="$ROOT/dist"
STAGE="$ROOT/.package-stage"

rm -rf "$DIST" "$STAGE"
mkdir -p "$DIST" "$STAGE"

"$ROOT/scripts/validate-package.sh"

# Ship the verified Linux Work binary alongside source. No target tree is packaged.
mkdir -p "$PLUGIN/bin/linux-x86_64"
cp "$ENGINE" "$PLUGIN/bin/linux-x86_64/dj-registry"
chmod 0755 "$PLUGIN/bin/linux-x86_64/dj-registry"

# One final manifest per durable package boundary.
(
  cd "$PLUGIN"
  find . -type f ! -path './engine-rust/target/*' -print0 | sort -z | xargs -0 sha256sum > PACKAGE-SHA256SUMS.txt
)

PLUGIN_STAGE="$STAGE/design-judgment-authorial-12.0.0-experimental.1"
mkdir -p "$PLUGIN_STAGE"
rsync -a --exclude target/ "$PLUGIN/" "$PLUGIN_STAGE/"
(
  cd "$STAGE"
  zip -X -q -r "$DIST/design-judgment-authorial-12.0.0-experimental.1.zip" "$(basename "$PLUGIN_STAGE")"
)

OVERLAY_STAGE="$STAGE/design-judgment-authorial-12-work-overlay-2026-08-13"
mkdir -p "$OVERLAY_STAGE/plugin" "$OVERLAY_STAGE/analysis" "$OVERLAY_STAGE/scripts"
cp "$ROOT/START-HERE.md" "$ROOT/MASTER-WORK-EXECUTION-PROMPT.md" "$ROOT/EVALUATION-PROTOCOL.md" "$OVERLAY_STAGE/"
cp "$ROOT/README.md" "$OVERLAY_STAGE/"
cp "$ROOT/analysis/FORENSIC-REPORT.md" "$ROOT/analysis/independent-seven-condition-scores.json" "$OVERLAY_STAGE/analysis/"
cp "$DIST/design-judgment-authorial-12.0.0-experimental.1.zip" "$OVERLAY_STAGE/plugin/"
rsync -a --exclude target/ "$PLUGIN/" "$OVERLAY_STAGE/plugin/source/"
cp "$ROOT/scripts/validate-package.sh" "$OVERLAY_STAGE/scripts/"
(
  cd "$OVERLAY_STAGE"
  find . -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS.txt
)
(
  cd "$STAGE"
  zip -X -q -r "$DIST/design-judgment-authorial-12-work-overlay-2026-08-13.zip" "$(basename "$OVERLAY_STAGE")"
)

MATERIALS_STAGE="$STAGE/design-judgment-authorial-12-final-materials-2026-08-13"
mkdir -p "$MATERIALS_STAGE"
cp "$DIST/design-judgment-authorial-12.0.0-experimental.1.zip" "$DIST/design-judgment-authorial-12-work-overlay-2026-08-13.zip" "$MATERIALS_STAGE/"
cp "$ROOT/README.md" "$ROOT/START-HERE.md" "$ROOT/EVALUATION-PROTOCOL.md" "$ROOT/analysis/FORENSIC-REPORT.md" "$ROOT/analysis/independent-seven-condition-scores.json" "$MATERIALS_STAGE/"
(
  cd "$MATERIALS_STAGE"
  find . -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS.txt
)
(
  cd "$STAGE"
  zip -X -q -r "$DIST/design-judgment-authorial-12-final-materials-2026-08-13.zip" "$(basename "$MATERIALS_STAGE")"
)

(
  cd "$DIST"
  sha256sum *.zip > SHA256SUMS.txt
  for z in *.zip; do unzip -tq "$z" >/dev/null; done
)

bench_json=$("$ENGINE" bench "$PLUGIN/registry/registry.json")
entry_count=$(jq '.entries|length' "$PLUGIN/registry/registry.json")
plugin_sha=$(sha256sum "$DIST/design-judgment-authorial-12.0.0-experimental.1.zip" | cut -d' ' -f1)
overlay_sha=$(sha256sum "$DIST/design-judgment-authorial-12-work-overlay-2026-08-13.zip" | cut -d' ' -f1)
materials_sha=$(sha256sum "$DIST/design-judgment-authorial-12-final-materials-2026-08-13.zip" | cut -d' ' -f1)
binary_sha=$(sha256sum "$PLUGIN/bin/linux-x86_64/dj-registry" | cut -d' ' -f1)

jq -n \
  --arg schema_version "dj-authorial-12-final-verification-v1" \
  --arg plugin_sha256 "$plugin_sha" \
  --arg overlay_sha256 "$overlay_sha" \
  --arg materials_sha256 "$materials_sha" \
  --arg binary_sha256 "$binary_sha" \
  --argjson entry_count "$entry_count" \
  --argjson benchmark "$bench_json" \
  '{schema_version:$schema_version,passed:true,plugin_sha256:$plugin_sha256,work_overlay_sha256:$overlay_sha256,final_materials_sha256:$materials_sha256,registry_binary_sha256:$binary_sha256,registry_entry_count:$entry_count,benchmark:$benchmark,receipt_policy:{read_receipts:0,per_candidate_receipts:0,durable_release_receipts:1},claim_boundary:"Package integrity and engine correctness passed; design superiority remains unproven."}' \
  > "$DIST/FINAL-VERIFICATION.json"

printf 'Built:\n'
ls -lh "$DIST"
