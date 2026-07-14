from src.core.cache import CacheService

_CACHE_KEY = "silenced_files"


class SilencedFiles:
    def __init__(self, cache: CacheService) -> None:
        self._cache = cache

    def load(self) -> set[str]:
        return set(self._cache.load().get(_CACHE_KEY, []))

    def silence(self, path: str) -> None:
        data = self._cache.load()
        silenced = set(data.get(_CACHE_KEY, []))
        silenced.add(path)
        data[_CACHE_KEY] = sorted(silenced)
        self._cache.save(data)

    def unsilence(self, path: str) -> None:
        data = self._cache.load()
        silenced = set(data.get(_CACHE_KEY, []))
        silenced.discard(path)
        data[_CACHE_KEY] = sorted(silenced)
        self._cache.save(data)
