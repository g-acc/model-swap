import httpx
from typing import Iterator
from state import WorkerState
import config

WORKER_TIMEOUT = 600.0 #seconds; large models upload can be slow
INFER_TIMEOUT = 300.0  # seconds; inference can be slow for large prompts

def load_from_local_store(state: WorkerState, model_name:str) -> None:
    r = httpx.post(f"{state.url}/load_model_from_local_store",
                   headers={'X-Model-Name': model_name},
                            timeout=WORKER_TIMEOUT)
    r.raise_for_status()

def load_from_store(state: WorkerState, model_name: str, file_path: str) -> None:
    with open(file_path, "rb") as f:
        r = httpx.post(f"{state.url}/load_model_from_store",
                       headers={"X-Model-Name": model_name},
                       content=f,
                       timeout=WORKER_TIMEOUT)
        r.raise_for_status()

def cache_model(state: WorkerState, model_name: str, file_path: str) -> None:
    with open(file_path, "rb") as f:
        r = httpx.post(f"{state.url}/cache_model",
                       headers={"X-Model-Name": model_name},
                       content=f,
                       timeout=WORKER_TIMEOUT)
        r.raise_for_status()

# The HTTP senders above are the fallback path; send_model dispatches to them.
_HTTP_SENDERS = {
    "load_model_from_store": load_from_store,
    "cache_model": cache_model,
}

def send_model(state: WorkerState, model_name: str, file_path: str, endpoint: str) -> None:
    """Send a model file to the worker using the configured transport.

    http: delegate to load_from_store / cache_model (file rides in the body).
    rdma: send the file over RDMA, then trigger the worker with a metadata-only
          HTTP call. If RDMA fails and fallback is allowed, use the HTTP sender.
    """
    http_send = _HTTP_SENDERS[endpoint]
    if config.TRANSPORT != "rdma":
        http_send(state, model_name, file_path)
        return

    import rdma
    try:
        rdma.send(config.WORKER_RDMA_HOST, config.WORKER_RDMA_PORT, model_name, file_path)
    except Exception:
        if not config.ALLOW_FALLBACK:
            raise  # benchmark: never silently file TCP timings under "rdma"
        print("[transport] RDMA send failed, falling back to HTTP")
        http_send(state, model_name, file_path)
        return

    # Bytes are already on the worker's disk; the HTTP call just triggers it.
    r = httpx.post(f"{state.url}/{endpoint}",
                   headers={"X-Model-Name": model_name, "X-Transport": "rdma"},
                   timeout=WORKER_TIMEOUT)
    r.raise_for_status()

def infer(state: WorkerState, prompt: str, model: str, max_tokens: int = 512) -> Iterator[bytes]:
    with httpx.stream("POST", f"{state.url}/infer",
                      json={"prompt": prompt, "model": model, "max_tokens": max_tokens},
                      timeout=INFER_TIMEOUT) as r:
        r.raise_for_status()
        yield from r.iter_bytes()
