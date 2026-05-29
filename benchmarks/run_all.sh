#!/usr/bin/env zsh
#
# Run all four smoke tests in sequence and generate a timing chart for each.
#
# Each test requires a different CACHE_POLICY in model_store_server/config.py.
# The script pauses between tests so you can reconfigure and restart the server.
#
# Usage:
#   ./benchmarks/run_all.sh
#   STORE_URL=http://10.0.0.70:8000 ./benchmarks/run_all.sh
#
# If the inference worker's model_cache lives somewhere other than the default,
# override MODEL_CACHE_DIR:
#   MODEL_CACHE_DIR=/path/to/model_cache ./benchmarks/run_all.sh

set -uo pipefail

SCRIPT_DIR="${0:A:h}"
REPO_ROOT="${SCRIPT_DIR}/.."
STORE_URL="${STORE_URL:-http://localhost:8000}"
MODEL_CACHE_DIR="${MODEL_CACHE_DIR:-${REPO_ROOT}/inference_worker/model_cache}"
OUT_DIR="${SCRIPT_DIR}"

# ── helpers ───────────────────────────────────────────────────────────────────

die() { echo "ERROR: $*" >&2; exit 1; }

check_server() {
  curl -sf --connect-timeout 3 -o /dev/null "${STORE_URL}/user_request" -X POST \
    -H 'Content-Type: application/json' -d '{}' 2>/dev/null || true
  # We just want to know the port is open; a 400 response is fine.
  if ! curl -s --connect-timeout 3 -o /dev/null -w "%{http_code}" \
       "${STORE_URL}/user_request" -X POST \
       -H 'Content-Type: application/json' -d '{}' 2>/dev/null | grep -qE '^[0-9]+$'; then
    die "Cannot reach model store server at ${STORE_URL}.\nStart it with: cd model_store_server && uv run model_store_server.py"
  fi
}

clear_model_cache() {
  local cache="${MODEL_CACHE_DIR}"
  if [[ ! -d "$cache" ]]; then
    echo "  (model cache dir not found at ${cache}, skipping)"
    return
  fi
  local files=("${cache}"/*.gguf(N))  # (N) suppresses error if no matches
  if [[ ${#files[@]} -eq 0 ]]; then
    echo "  model cache already empty."
  else
    echo "  Clearing ${#files[@]} model file(s) from ${cache}..."
    rm -f "${files[@]}"
    echo "  Done."
  fi
}

pause() {
  echo
  echo "──────────────────────────────────────────────────────────"
  echo "  $1"
  echo "  Restart the store server after updating config."
  echo "──────────────────────────────────────────────────────────"
  read "?  Press Enter when ready (Ctrl-C to abort)... "
  echo
  clear_model_cache
  echo
}

run_smoke() {
  local script="$1"
  local title="$2"
  local slug="$3"
  local out_txt="${OUT_DIR}/${slug}.txt"
  local out_png="${OUT_DIR}/${slug}.png"

  echo "==> ${title}"
  STORE_URL="${STORE_URL}" "${REPO_ROOT}/${script}" 2>&1 | tee "${out_txt}"
  uv run "${SCRIPT_DIR}/plot_run.py" "${out_txt}" -o "${out_png}" --title "${title}"
  echo "    chart saved → ${out_png}"
}

# ── main ──────────────────────────────────────────────────────────────────────

echo "Smoke test runner"
echo "STORE_URL = ${STORE_URL}"
echo "Output    = ${OUT_DIR}/"
echo

check_server

pause 'Set CACHE_POLICY = "lru", MAX_CACHE_SIZE = 2 in model_store_server/config.py and restart the store server.'
run_smoke "test_cache_smoke.sh"    "LRU policy"      "lru"

pause 'Set CACHE_POLICY = "no-evict", MAX_CACHE_SIZE = 2 in model_store_server/config.py and restart the store server.'
run_smoke "test_no_evict_smoke.sh" "No-evict policy" "no_evict"

pause 'Set CACHE_POLICY = "ttl", TTL_SECONDS = 5 in model_store_server/config.py and restart the store server.'
run_smoke "test_ttl_smoke.sh"      "TTL policy"      "ttl"

pause 'Set CACHE_POLICY = "lru-ttl", MAX_CACHE_SIZE = 2, TTL_SECONDS = 5 in model_store_server/config.py and restart the store server.'
run_smoke "test_lru_ttl_smoke.sh"  "LRU+TTL policy"  "lru_ttl"

echo
echo "All done. Charts generated:"
for slug in lru no_evict ttl lru_ttl; do
  f="${OUT_DIR}/${slug}.png"
  [[ -f "$f" ]] && echo "  ${f}"
done
