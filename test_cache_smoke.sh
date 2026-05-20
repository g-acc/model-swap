#!/usr/bin/env zsh
#
# Smoke test for cache policy behavior. Start the model store server and an
# inference worker first, then run this script and check the store server log
# for the `action=` and `evicted=` fields to verify the expected sequence.
#
# Usage:
#   ./test_cache_smoke.sh
#   STORE_URL=http://10.0.0.70:8000 ./test_cache_smoke.sh

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

post "1. baseline                 -> expect: load_from_store, cached=[tinygemma3]" \
     "tinygemma3.gguf"

post "2. repeat                   -> expect: already_loaded" \
     "tinygemma3.gguf"

post "3. second model             -> expect: load_from_store, cached=[tinygemma3, SmolLM2]" \
     "SmolLM2-135M-Instruct-Q8_0.gguf"

post "4. third model (evict LRU)  -> expect: load_from_store, evicted=[tinygemma3]" \
     "qwen2.5-0.5b-instruct-q4_k_m.gguf"

post "5. re-load evicted          -> expect: load_from_store, evicted=[SmolLM2]" \
     "tinygemma3.gguf"

echo
echo "=== done. check server log for action= and evicted= values ==="
