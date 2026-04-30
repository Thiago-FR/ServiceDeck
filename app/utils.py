# app/utils.py

# Contém funções auxiliares genéricas para manipulação de arquivos e processos.

import os
import shutil
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


def _detect_linux_terminal():
    """Detecta o emulador de terminal disponível no sistema."""
    terminals = [
        ('gnome-terminal', lambda cmd: ['gnome-terminal', '--', 'bash', '-ic', cmd]),
        ('konsole',        lambda cmd: ['konsole', '-e', 'bash', '-ic', cmd]),
        ('xfce4-terminal', lambda cmd: ['xfce4-terminal', '-e', f'bash -ic "{cmd}"']),
        ('xterm',          lambda cmd: ['xterm', '-e', f'bash -ic "{cmd}"']),
        ('x-terminal-emulator', lambda cmd: ['x-terminal-emulator', '-e', f'bash -ic "{cmd}"']),
    ]
    for name, builder in terminals:
        if shutil.which(name):
            return builder
    return None


def open_in_new_terminal(command, work_dir):
    """Executa um comando em um novo terminal."""
    system = platform.system()
    try:
        if system == "Linux":
            full_command = f'cd "{work_dir}" && {command}; exec bash'
            builder = _detect_linux_terminal()
            if builder:
                subprocess.Popen(builder(full_command))
            else:
                print(f"Nenhum emulador de terminal encontrado para '{work_dir}'.")
        elif system == "Windows":
            full_command = f'title={os.path.basename(work_dir)} && {command}'
            subprocess.Popen(
                f'start cmd /k "{full_command}"',
                shell=True,
                cwd=work_dir
              )
    except Exception as e:
        print(f"Erro ao abrir novo terminal para '{work_dir}': {e}")
