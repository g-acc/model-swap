MODELS_DIR = "./models"
WORKER_URL = "http://localhost:8080"
MAX_CACHE_SIZE = 2  # max number of models cached on each worker's disk
TTL_SECONDS = 5  # used by ttl
CACHE_POLICY = "ttl"  # "lru" | "no-evict" | "ttl"
