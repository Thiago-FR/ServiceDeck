#!/bin/bash

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv venv
    echo "Instalando dependências..."
    venv/bin/pip install PyQt6 psutil --quiet
fi

exec venv/bin/python main.py "$@"
