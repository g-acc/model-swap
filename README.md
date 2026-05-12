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
pip install flask
```

## Running Inference worker

```bash
python inference_worker.py
```

The server listens on `0.0.0.0:8080` by default.
