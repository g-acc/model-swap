from dataclasses import dataclass, field
from typing import Protocol
from collections import OrderedDict
import time


@dataclass
class AdmitResult:
    admitted: bool
    evicted: list[str] = field(default_factory=list)


class CachePolicy(Protocol):
    name: str

    def sweep(self) -> list[str]: ...
    def contains(self, key: str) -> bool: ...
    def access(self, key: str) -> None: ...
    def admit(self, key: str, size: int = 0, cost: float = 0.0) -> AdmitResult: ...
    def members(self) -> list[str]: ...


class LRUPolicy:
    name = "lru"

    def __init__(self, capacity: int):
        self.capacity = capacity
        self._cache: "OrderedDict[str, None]" = OrderedDict()

    def sweep(self) -> list[str]:
        return []

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

    def sweep(self) -> list[str]:
        return []

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


class TTLPolicy:
    name = "ttl"

    def __init__(self, ttl_seconds: float):
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, float] = {}

    def sweep(self) -> list[str]:
        now = time.monotonic()
        expired = [k for k, t in self._cache.items() if now - t > self.ttl_seconds]
        for k in expired:
            del self._cache[k]
        return expired

    def contains(self, key: str) -> bool:
        return key in self._cache

    def access(self, key: str) -> None:
        if key in self._cache:
            self._cache[key] = time.monotonic()

    def admit(self, key: str, size: int = 0, cost: float = 0.0) -> AdmitResult:
        self._cache[key] = time.monotonic()
        return AdmitResult(admitted=True)

    def members(self) -> list[str]:
        return list(self._cache.keys())


class LRUTTLPolicy:
    name = "lru-ttl"

    def __init__(self, capacity: int, ttl_seconds: float):
        self.capacity = capacity
        self.ttl_seconds = ttl_seconds
        self._cache: "OrderedDict[str, float]" = OrderedDict()  # key -> last_access_time

    def sweep(self) -> list[str]:
        now = time.monotonic()
        expired = [k for k, t in self._cache.items() if now - t > self.ttl_seconds]
        for k in expired:
            del self._cache[k]
        return expired

    def contains(self, key: str) -> bool:
        return key in self._cache

    def access(self, key: str) -> None:
        if key in self._cache:
            self._cache[key] = time.monotonic()
            self._cache.move_to_end(key)

    def admit(self, key: str, size: int = 0, cost: float = 0.0) -> AdmitResult:
        self._cache[key] = time.monotonic()
        self._cache.move_to_end(key)
        evicted: list[str] = []
        if len(self._cache) > self.capacity:
            ev, _ = self._cache.popitem(last=False)
            evicted.append(ev)
        return AdmitResult(admitted=True, evicted=evicted)

    def members(self) -> list[str]:
        return list(self._cache.keys())


def build_policy(name: str, capacity: int, ttl_seconds: float) -> CachePolicy:
    if name == "lru":
        return LRUPolicy(capacity=capacity)
    if name == "no-evict":
        return NoEvictionPolicy(capacity=capacity)
    if name == "ttl":
        return TTLPolicy(ttl_seconds=ttl_seconds)
    if name == "lru-ttl":
        return LRUTTLPolicy(capacity=capacity, ttl_seconds=ttl_seconds)
    raise ValueError(f"unknown CACHE_POLICY: {name!r}")
