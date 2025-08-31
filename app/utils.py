# app/utils.py

# Contém funções auxiliares genéricas para manipulação de arquivos e processos.

import os
import subprocess
import platform
import sys


def resource_path(relative_path):
    """ Retorna o caminho absoluto para o recurso """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..'))

    return os.path.join(base_path, relative_path)


def get_microservices(path):
    """Encontra todos os subdiretórios no caminho base."""
    if not os.path.exists(path):
        return None, f"O diretório '{path}' não foi encontrado."
    try:
        services = [
            d for d in os.listdir(path)
            if os.path.isdir(os.path.join(path, d)) and not d.startswith('.')
        ]
        services.sort()
        return services, None
    except Exception as e:
        return None, f"Ocorreu um erro ao acessar o diretório: {e}"


def open_in_new_terminal(command, work_dir):
    """Executa um comando em um novo terminal."""
    system = platform.system()
    try:
        if system == "Linux":
            full_command = f'cd "{work_dir}" && {command}; exec bash'
            subprocess.Popen(
                ['gnome-terminal', '--', 'bash', '-c', full_command]
              )
        elif system == "Windows":
            full_command = f'title={os.path.basename(work_dir)} && {command}'
            subprocess.Popen(
                f'start cmd /k "{full_command}"',
                shell=True,
                cwd=work_dir
              )
    except Exception as e:
        print(f"Erro ao abrir novo terminal para '{work_dir}': {e}")
