import json
import os
from typing import Any


class CacheService:
    def __init__(self, cache_file: str):
        self._cache_file = cache_file

    def load(self) -> dict[str, Any]:
        try:
            if os.path.exists(self._cache_file):
                with open(self._cache_file, 'r') as f:
                    return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Cache não encontrado ou corrompido. Erro: {e}")
        return {}

    def save(self, data: dict[str, Any]) -> None:
        try:
            with open(self._cache_file, 'w') as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            print(f"Erro ao salvar o cache: {e}")
