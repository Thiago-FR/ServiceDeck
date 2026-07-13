import os
import platform
import shutil
import subprocess


def _detect_linux_terminal():
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


def open_in_new_terminal(command: str, work_dir: str) -> None:
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
            proc = subprocess.Popen(
                f'start cmd /k "{full_command}"',
                shell=True,
                cwd=work_dir,
            )
            proc._handle = None  # evita OSError no __del__ ao fechar o app
    except Exception as e:
        print(f"Erro ao abrir novo terminal para '{work_dir}': {e}")


def open_with_command(command: str, work_dir: str) -> None:
    if platform.system() == "Windows":
        subprocess.Popen(command, shell=True, cwd=work_dir)
    else:
        subprocess.Popen(command.split(), cwd=work_dir)
