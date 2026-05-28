# MODEL SWAP

## Model Server
A Flask HTTP server that owns the on-disk model store and routes user inference
requests to a single inference worker. Cache state for the worker (what's
loaded on GPU, what's on its disk cache) lives in the store server, and an
swappable cache policy decides what to evict when the cache is full or stale.

## Inference Worker

A Flask HTTP server that manages model loading and caching for llama.cpp-based inference.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/load_model_from_store` | Receive a model file from the model store, store it, and load it into GPU |
| POST | `/load_model_from_cache` | Load an already-cached model into GPU by name |
| POST | `/cache_model` | Receive a model file from the model store and cache it without loading into GPU |
| POST | `/user_request` | Accepts `{prompt, model, max_tokens}`. Ensures `model` is loaded on the worker, then streams the worker's inference response back to the client |

## Configuration

`model_store_server/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `MODELS_DIR` | `./models` | Directory the server reads `.gguf` files from |
| `WORKER_URL` | `http://localhost:8080` | Inference worker base URL |
| `MAX_CACHE_SIZE` | `2` | Max models tracked in the worker's on-disk cache (used by `lru`, `no-evict`, `lru-ttl`) |
| `TTL_SECONDS` | `5` | Stale-entry timeout in seconds (used by `ttl`, `lru-ttl`) |
| `CACHE_POLICY` | `"lru"` | One of `lru`, `no-evict`, `ttl`, `lru-ttl` |

## Cache policies

| Policy | Behavior | Inspiration |
|--------|----------|-------------|
| `lru` | Evict least-recently-used when cache reaches `MAX_CACHE_SIZE`. | Default in vLLM-LoRA, Ray Serve, KServe, SageMaker MME |
| `no-evict` | Refuse new admissions once full; returns HTTP 503 to the user. | Triton EXPLICIT mode |
| `ttl` | Evict any entry untouched for `TTL_SECONDS`. No capacity bound. | llama-swap |
| `lru-ttl` | Both bounds active: capacity-based LRU eviction *and* time-based TTL sweep. | Ollama (`keep_alive`) |

Every `/user_request` log line on the store server reports which policy was active, the cache action taken, timings, the post-request cache contents, and any evictions:

```
[/user_request] ts=... policy=lru-ttl model=qwen.gguf action=load_from_store decision_ms=0.02 worker_ms=459.2 cached=[...] evicted=[...]
```

Possible `action` values: `already_loaded`, `load_from_cache`, `load_from_store`, `rejected` (`no-evict` only).

## Setup

Inference worker:
```bash
cd inference_worker
uv sync
```

Model store server:
```bash
cd model_store_server
uv sync
```

## Running Inference Worker

```bash
cd inference_worker

uv run inference_worker.py
```

Models live in `/inference_worker/model_cache`.

The inference worker listens on `0.0.0.0:8080` by default.

## Sample Inference Worker Requests

### Cache a model
```bash
curl -X POST http://localhost:8080/cache_model \
  -H "X-Model-Name: my-model.gguf" \
  -H "Transfer-Encoding: chunked" \
  --data-binary @- < /path/to/my-model.gguf
```

### Load a model from store (send file + load into GPU)
```bash
curl -X POST http://localhost:8080/load_model_from_store \
  -H "X-Model-Name: my-model.gguf" \
  -H "Transfer-Encoding: chunked" \
  --data-binary @- < /path/to/my-model.gguf
```

## Sample Model Store Server

### Send inference request

The response is streamed as `text/plain`, so use `curl -N` (or `--no-buffer`)
to see tokens as they arrive. `max_tokens` is optional and defaults to `512`.

```bash
curl -N -X POST http://localhost:8000/user_request \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain transformers in one sentence.", "model": "tinygemma3.gguf", "max_tokens": 512}'
```

## Running Model Server
```bash
cd model_store_server

uv run model_store_server.py
```

Models live in `/model_store_server/models`.

The model swap server listens on `0.0.0.0:8000` by default.

## End to end example on a single machine

1. Run the inference worker in one window.
2. Run the model store server in another window.
3. Place a `.gguf` file in `model_store_server/models/`.
4. Send an inference request to the model store server (see the `curl -N` example above).

The first request for a given model streams the file from the store to the
worker and is slow. Subsequent requests for the same model (or any model still
in the worker's cache) skip the upload and are fast.

## Smoke tests

Four shell scripts at the repo root exercise each cache policy. Before
running, set the matching `CACHE_POLICY` (and `MAX_CACHE_SIZE` / `TTL_SECONDS`)
in `model_store_server/config.py` and restart the store server.

Make sure the correct models are in the model store server:
- tinygemma3.gguf: https://huggingface.co/ggml-org/tinygemma3-GGUF/tree/main
- SmolLM2-135M-Instruct-Q8_0.gguf: https://huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF/blob/main/SmolLM2-135M-Instruct-Q8_0.gguf
- qwen2.5-0.5b-instruct-q4_k_m.gguf: https://huggingface.co/Growcompany/Qwen2.5-0.5B-Instruct-Q4_K_M-GGUF/tree/main

And be sure to delete the inference_worker's model cache between runs!

| Script | Policy | What it checks |
|--------|--------|----------------|
| `./test_cache_smoke.sh` | `lru` | First miss, hit, fill, LRU eviction, re-load of evicted model |
| `./test_no_evict_smoke.sh` | `no-evict` | Cache fills, third model returns HTTP 503 with no transfer attempted |
| `./test_ttl_smoke.sh` | `ttl` (set `TTL_SECONDS=5`) | Cache hit within window, sleep, sweep on next admit |
| `./test_lru_ttl_smoke.sh` | `lru-ttl` (set `MAX_CACHE_SIZE=2`, `TTL_SECONDS=5`) | Both eviction paths fire: capacity-based then time-based |

Override the default endpoint with `STORE_URL=http://host:8000 ./test_*.sh`.

Each step prints a timing summary line:
```
[http 200 | tcp_connect=0.000s  time_to_first_byte=0.208s  generation=0.030s  total=0.238s | throughput=~933 bytes/s]
```

- **tcp_connect** — TCP handshake time; negligible on localhost, non-zero in multi-node deployments
- **time_to_first_byte** — dominated by model load/swap when a cache miss occurs; near-zero on `already_loaded` hits
- **generation** — time spent streaming the response tokens (`total - time_to_first_byte`)
- **throughput** — bytes per second during generation (~4× for approximate tokens/sec on English text)

The inference worker also logs per-request metrics to its console:
```
[infer] TTFT: 0.045s
[infer] tokens=8 total=0.075s tps=106.7
```

## Benchmarks

`benchmarks/plot_run.py` parses smoke test output and renders a stacked bar chart showing the timing breakdown (tcp_connect / time_to_first_byte / generation) for each step, colored by cache action.

No install needed — `uv` handles the `matplotlib` dependency automatically.

### Generate a chart

Pipe a smoke test directly:
```bash
./test_cache_smoke.sh 2>&1 | uv run benchmarks/plot_run.py --title "LRU policy"
# → saves benchmarks/smoke_bench.png
```

Save output first, then plot:
```bash
./test_ttl_smoke.sh 2>&1 > benchmarks/ttl_run.txt
uv run benchmarks/plot_run.py benchmarks/ttl_run.txt
# → saves benchmarks/ttl_run.png
```

Explicit output path:
```bash
./test_lru_ttl_smoke.sh 2>&1 | uv run benchmarks/plot_run.py --title "LRU+TTL" -o benchmarks/lru_ttl.png
```

### Color key

| Color | Cache action |
|-------|-------------|
| Orange | `load_from_store` — model fetched from store and loaded into GPU |
| Blue | `load_from_cache` — model already on disk, loaded into GPU |
| Green | `already_loaded` — no swap needed |
| Gray | `rejected` — cache full, request denied (no-evict policy) |
