# app/config.py

# Centraliza as constantes e configurações da aplicação.

import os
import sys


def _get_cache_file():
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:
        base = os.environ.get(
            'XDG_CONFIG_HOME',
            os.path.join(os.path.expanduser('~'), '.config')
        )
    cache_dir = os.path.join(base, 'ServiceDeck')
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, 'cache.json')


CACHE_FILE = _get_cache_file()
APP_NAME = 'ServiceDeck'
APP_VERSION = '1.0'
