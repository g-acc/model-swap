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

## Sample Model Swap Server

### Send inference request
```bash
curl -X POST http://localhost:8000/user_request \      
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain transformers in one sentence.", "model": "ggml-org_models_tinyllamas_stories15M-q4_0.gguf"}'
```

## Running Model Server
```bash
cd model_swap_server 

uv run model_swap_server.py
```

Models live in /model_swap_server/models

The server listens on `0.0.0.0:8000` by default.

## End to end example on a single machine

Run inference worker in one terminal.

Run model swap server in another terminal.
Be sure to have models available in /model_store_server/models.

Send an inference request to the model swap server.