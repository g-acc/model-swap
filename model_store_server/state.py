from dataclasses import dataclass
import config
from cache_policy import CachePolicy, LRUPolicy


@dataclass
class WorkerState:
    url: str
    policy: CachePolicy
    loaded: str | None = None


worker = WorkerState(
    url=config.WORKER_URL,
    policy=LRUPolicy(capacity=config.MAX_CACHE_SIZE),
)
