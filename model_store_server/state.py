from dataclasses import dataclass, field
import config
from collections import OrderedDict

@dataclass
class WorkerState:
    url: str
    max_cache_size: int = 2
    cached: "OrderedDict[str, None]"= field(default_factory=OrderedDict)
    loaded: str | None = None


    def touch(self, model: str) -> None:

        if model in self.cached:
            self.cached.move_to_end(model)

    def add_to_cache(self, model: str) -> str | None:
        self.cached[model] = None
        self.cached.move_to_end(model)

        if len(self.cached) > self.max_cache_size:
            evicted, _ = self.cached.popitem(last=False)
            return evicted

        return None

worker = WorkerState(url=config.WORKER_URL, max_cache_size=config.MAX_CACHE_SIZE)
