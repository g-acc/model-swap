from dataclasses import dataclass, field
import config

@dataclass
class WorkerState:
    url: str
    cached: set[str] = field(default_factory=set)
    loaded: str | None = None


worker = WorkerState(url=config.WORKER_URL)
