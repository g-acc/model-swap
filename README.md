# MODEL SWAP

## Model Server
A Flask HTTP server that owns the on-disk model store and routes user inference requests to a single inference worker.

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

| Setting | Default | Description |
|---------|---------|-------------|
| `MODELS_DIR` | `./models` | Directory the server reads `.gguf` files from |
| `WORKER_URL` | `http://localhost:8080` | Inference worker base URL |
| `MAX_CACHE_SIZE` | `2` | Max models tracked in the worker's on-disk cache (LRU eviction) |

TODO: add the rest

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

Models live in /inference_worker/model_cache

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
```bash
The response is streamed as `text/plain`, so use `curl -N` (or `--no-buffer`) to see tokens as they arrive. `max_tokens` is optional and defaults to `512`.

```bash
curl -N -X POST http://localhost:8000/user_request \
   -H "Content-Type: application/json" \
   -d '{"prompt": "Explain transformers in one sentence.", "model": "ggml-org_models_tinyllamas_stories15M-q4_0.gguf", "max_tokens": 512}'
```

## Running Model Server
```bash
cd model_store_server 

uv run model_store_server.py
```

Models live in /model_store_server/models

The server listens on `0.0.0.0:8000` by default.

## End to end example on a single machine

1. Run the inference worker in one window.
2. Run the model store server in another window.
3. Place a `.gguf` file in `model_store_server/models/`.
4. Send an inference request to the model store server (see the `curl -N` example above).

The first request for a given model streams the file from the store to the worker and is slow. Subsequent requests for the same model (or any model still in the worker's cache) skip the upload and are fast.
