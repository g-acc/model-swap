from dataclasses import dataclass, field
from typing import Protocol
from collections import OrderedDict


@dataclass
class AdmitResult:
    admitted: bool
    evicted: list[str] = field(default_factory=list)


class CachePolicy(Protocol):
    name: str

    def contains(self, key: str) -> bool: ...
    def access(self, key: str) -> None: ...
    def admit(self, key: str, size: int = 0, cost: float = 0.0) -> AdmitResult: ...
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

    def admit(self, key: str, size: int = 0, cost: float = 0.0) -> AdmitResult:
        self._cache[key] = None
        self._cache.move_to_end(key)
        evicted: list[str] = []
        if len(self._cache) > self.capacity:
            ev, _ = self._cache.popitem(last=False)
            evicted.append(ev)
        return AdmitResult(admitted=True, evicted=evicted)

    def members(self) -> list[str]:
        return list(self._cache.keys())


class NoEvictionPolicy:
    name = "no-evict"

    def __init__(self, capacity: int):
        self.capacity = capacity
        self._cache: set[str] = set()
        self._order: list[str] = []  # for stable members() ordering

    def contains(self, key: str) -> bool:
        return key in self._cache

    def access(self, key: str) -> None:
        pass

    def admit(self, key: str, size: int = 0, cost: float = 0.0) -> AdmitResult:
        if key in self._cache:
            return AdmitResult(admitted=True)
        if len(self._cache) >= self.capacity:
            return AdmitResult(admitted=False)
        self._cache.add(key)
        self._order.append(key)
        return AdmitResult(admitted=True)

    def members(self) -> list[str]:
        return list(self._order)


def build_policy(name: str, capacity: int) -> CachePolicy:
    if name == "lru":
        return LRUPolicy(capacity=capacity)
    if name == "no-evict":
        return NoEvictionPolicy(capacity=capacity)
    raise ValueError(f"unknown CACHE_POLICY: {name!r}")
