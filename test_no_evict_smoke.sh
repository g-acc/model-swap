#!/usr/bin/env zsh
#
# No-eviction smoke test.
# Requires:
#   model_store_server/config.py: CACHE_POLICY = "no-evict", MAX_CACHE_SIZE = 2
# Start the model store server + inference worker, then run this.

set -uo pipefail
STORE_URL="${STORE_URL:-http://localhost:8000}"

post() {
  local label="$1"
  local model="$2"
  echo
  echo "=== ${label} ==="
  curl -N --no-progress-meter -w '\n[http %{http_code}, %{time_total}s]\n' \
    -X POST "${STORE_URL}/user_request" \
    -H 'Content-Type: application/json' \
    -d "{\"prompt\":\"hi\",\"model\":\"${model}\",\"max_tokens\":8}"
}

post "1. first model              -> expect: load_from_store, cached=[tinygemma3]" \
     "tinygemma3.gguf"

post "2. second model             -> expect: load_from_store, cached=[tinygemma3, SmolLM2]" \
     "SmolLM2-135M-Instruct-Q8_0.gguf"

post "3. third model (FULL)       -> expect: 503 rejected, cached unchanged" \
     "qwen2.5-0.5b-instruct-q4_k_m.gguf"

post "4. repeat first model       -> expect: already_loaded OR load_from_cache, still 200" \
     "tinygemma3.gguf"

echo
echo "=== done. check server log for action=rejected on step 3 ==="
