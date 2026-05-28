#!/usr/bin/env zsh
#
# TTL-only smoke test.
# Requires:
#   model_store_server/config.py: CACHE_POLICY = "ttl", TTL_SECONDS = 5
# Start the model store server + inference worker, then run this.

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

post "1. load model A           -> expect: load_from_store, cached=[A]" "tinygemma3.gguf"
post "2. load model B           -> expect: load_from_store, cached=[A, B]" "SmolLM2-135M-Instruct-Q8_0.gguf"
post "3. immediate access A     -> expect: load_from_cache (still warm)" "tinygemma3.gguf"

echo
echo "--- sleeping 7s to exceed TTL_SECONDS=5 ---"
sleep 7

post "4. load model C after TTL -> expect: load_from_store, evicted=[A, B]" "qwen2.5-0.5b-instruct-q4_k_m.gguf"

echo
echo "=== done. step 4's log line should show evicted=[A, B] from TTL sweep ==="
