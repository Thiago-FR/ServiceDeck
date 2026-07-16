from src.core.cache import CacheService

_CACHE_KEY = "hidden_files"


class HiddenFiles:
    def __init__(self, cache: CacheService) -> None:
        self._cache = cache

    def load(self) -> set[str]:
        return set(self._cache.load().get(_CACHE_KEY, []))

    def hide(self, paths: list[str]) -> None:
        data = self._cache.load()
        hidden = set(data.get(_CACHE_KEY, []))
        hidden.update(paths)
        data[_CACHE_KEY] = sorted(hidden)
        self._cache.save(data)

    def unhide(self, paths: list[str]) -> None:
        data = self._cache.load()
        hidden = set(data.get(_CACHE_KEY, []))
        hidden.difference_update(paths)
        data[_CACHE_KEY] = sorted(hidden)
        self._cache.save(data)
