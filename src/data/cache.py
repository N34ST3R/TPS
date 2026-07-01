import time
from collections import defaultdict


class InMemoryCache:
    def __init__(self):
        self._store = {}
        self._timestamps = {}

    def get(self, key: str, ttl: int = 60):
        if key in self._store:
            if time.time() - self._timestamps[key] < ttl:
                return self._store[key]
            del self._store[key]
            del self._timestamps[key]
        return None

    def set(self, key: str, value):
        self._store[key] = value
        self._timestamps[key] = time.time()

    def invalidate(self, key: str):
        self._store.pop(key, None)
        self._timestamps.pop(key, None)


cache = InMemoryCache()
