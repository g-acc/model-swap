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

For GPU support, reinstall `llama-cpp-python` with the appropriate backend after `uv sync`:
```bash
# Metal (macOS)
CMAKE_ARGS="-DGGML_METAL=on" uv pip install llama-cpp-python
# CUDA
CMAKE_ARGS="-DGGML_CUDA=on" uv pip install llama-cpp-python
```

## Running Inference Worker

```bash
cd inference_worker

# Without a default model (load later via endpoints)
uv run inference_worker.py

# With a default model loaded at startup
MODEL_PATH=/path/to/model.gguf uv run inference_worker.py

# Optional env vars
#   N_GPU_LAYERS  — layers offloaded to GPU (-1 = all, default: -1)
#   N_CTX         — context window size (default: 2048)
```

The server listens on `0.0.0.0:8080` by default.
