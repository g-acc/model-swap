import os

MODELS_DIR = "./models"
WORKER_URL = os.environ.get("WORKER_URL", "http://localhost:8080")
MAX_CACHE_SIZE = 2  # max number of models cached on each worker's disk
TTL_SECONDS = 5  # used by ttl, lru-ttl
CACHE_POLICY = "lru-ttl"  # "lru" | "no-evict" | "ttl" | "lru-ttl"

# Transport used to send model files to the worker.
TRANSPORT = os.environ.get("TRANSPORT", "http").lower()  # "http" | "rdma"
ALLOW_FALLBACK = os.environ.get("ALLOW_FALLBACK", "0").lower() in {"1", "true", "yes"}
WORKER_RDMA_HOST = os.environ.get("WORKER_RDMA_HOST", "localhost")
WORKER_RDMA_PORT = int(os.environ.get("WORKER_RDMA_PORT", 8081))
