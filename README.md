# MODEL SWAP

## Model Server
TODO

## Inference Worker

A Flask HTTP server that manages model loading and caching for llama.cpp-based inference.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/load_model_from_store` | Receive a model file from the model store, store it, and load it into GPU |
| POST | `/load_model_from_cache` | Load an already-cached model into GPU by name |
| POST | `/cache_model` | Receive a model file from the model store and cache it without loading into GPU |

TODO: add the rest

## Setup

```bash
cd inference_worker
uv sync
```


## Running Inference Worker

```bash
cd inference_worker

uv run inference_worker.py
```

The server listens on `0.0.0.0:8080` by default.

## Sample Requests

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
