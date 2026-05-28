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
  local out
  out=$(curl -sS -N \
    -w '\n__TIMING__ %{http_code} %{time_connect} %{time_starttransfer} %{time_total} %{size_download}' \
    -X POST "${STORE_URL}/user_request" \
    -H 'Content-Type: application/json' \
    -d "{\"prompt\":\"hi\",\"model\":\"${model}\",\"max_tokens\":8}")
  local timing_line body http connect ttfb total bytes gen tps
  timing_line=$(echo "$out" | grep '^__TIMING__')
  body=$(echo "$out" | grep -v '^__TIMING__')
  echo "$body"
  read -r _ http connect ttfb total bytes <<< "$timing_line"
  gen=$(awk "BEGIN {printf \"%.3f\", $total - $ttfb}")
  tps=$(awk "BEGIN {if ($gen+0 > 0) printf \"%.1f\", $bytes / $gen; else print \"n/a\"}")
  echo "[http $http | tcp_connect=${connect}s  time_to_first_byte=${ttfb}s  generation=${gen}s  total=${total}s | throughput=~${tps} bytes/s]"
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
