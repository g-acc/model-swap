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
| POST | `/load_model_from_local_store` | Load an already-cached model into GPU by name |
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
| `TRANSPORT` | `"http"` | `http` or `rdma`. Selects how model bytes reach the worker. |
| `ALLOW_FALLBACK` | `0` | If `1`, a failed RDMA send retries over HTTP. |
| `WORKER_RDMA_HOST` | `"localhost"` | Worker hostname for the RDMA endpoint. |
| `WORKER_RDMA_PORT` | `8081` | Worker port for the RDMA listener. |

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

Possible `action` values: `already_loaded`, `load_from_local_store`, `load_from_store`, `rejected` (`no-evict` only).

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

The server listens on `0.0.0.0:8080` by default.

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

The server listens on `0.0.0.0:8000` by default.

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

| Script | Policy | What it checks |
|--------|--------|----------------|
| `./test_cache_smoke.sh` | `lru` | First miss, hit, fill, LRU eviction, re-load of evicted model |
| `./test_no_evict_smoke.sh` | `no-evict` | Cache fills, third model returns HTTP 503 with no transfer attempted |
| `./test_ttl_smoke.sh` | `ttl` (set `TTL_SECONDS=5`) | Cache hit within window, sleep, sweep on next admit |
| `./test_lru_ttl_smoke.sh` | `lru-ttl` (set `MAX_CACHE_SIZE=2`, `TTL_SECONDS=5`) | Both eviction paths fire: capacity-based then time-based |

Override the default endpoint with `STORE_URL=http://host:8000 ./test_*.sh`.
