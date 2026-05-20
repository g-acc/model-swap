from typing import Protocol
from collections import OrderedDict


class CachePolicy(Protocol):
    name: str

    def contains(self, key: str) -> bool: ...
    def access(self, key: str) -> None: ...
    def admit(self, key: str, size: int = 0, cost: float = 0.0) -> list[str]: ...
    def members(self) -> list[str]: ...


class LRUPolicy:
    name = "lru"

    def __init__(self, capacity: int):
        self.capacity = capacity
        self._cache: "OrderedDict[str, None]" = OrderedDict()

    def contains(self, key: str) -> bool:
        return key in self._cache

    def access(self, key: str) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)

    def admit(self, key: str, size: int = 0, cost: float = 0.0) -> list[str]:
        self._cache[key] = None
        self._cache.move_to_end(key)
        if len(self._cache) > self.capacity:
            evicted, _ = self._cache.popitem(last=False)
            return [evicted]
        return []

    def members(self) -> list[str]:
        return list(self._cache.keys())
