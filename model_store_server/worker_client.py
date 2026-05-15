import httpx
from state import WorkerState

WORKER_TIMEOUT = 600.0 #seconds; large models upload can be slow

def load_from_cache(state: WorkerState, model_name:str) -> None:
    r = httpx.post(f"{state.url}/load_model_from_cache",
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
