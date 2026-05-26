from dataclasses import dataclass
import config
from cache_policy import CachePolicy, build_policy


@dataclass
class WorkerState:
    url: str
    policy: CachePolicy
    loaded: str | None = None


worker = WorkerState(
    url=config.WORKER_URL,
    policy=build_policy(
        config.CACHE_POLICY,
        capacity=config.MAX_CACHE_SIZE,
        ttl_seconds=config.TTL_SECONDS,
    ),
)
