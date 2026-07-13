import os
import psutil


def kill_service(service_name: str, base_path: str) -> tuple[bool, str]:
    service_path = os.path.realpath(os.path.join(base_path, service_name))
    try:
        for proc in psutil.process_iter(['cwd', 'pid']):
            try:
                if proc.info['cwd'] and os.path.realpath(proc.info['cwd']) == service_path:
                    parent = psutil.Process(proc.pid)
                    for child in parent.children(recursive=True):
                        child.kill()
                    parent.kill()
                    return True, f"■ Serviço '{service_name}' encerrado."
            except (psutil.NoSuchProcess, psutil.AccessDenied, FileNotFoundError):
                continue
    except Exception as e:
        return False, f"❌ Erro ao encerrar '{service_name}': {e}"
    return False, f"⚠️ Nenhum processo encontrado para '{service_name}'."


def kill_all_services(service_names: set[str], base_path: str) -> list[str]:
    service_paths = {
        name: os.path.realpath(os.path.join(base_path, name))
        for name in service_names
    }
    messages = []
    terminated_pids = set()
    try:
        for proc in psutil.process_iter(['cwd', 'pid']):
            if proc.pid in terminated_pids:
                continue
            try:
                if proc.info['cwd']:
                    proc_cwd = os.path.realpath(proc.info['cwd'])
                    for name, path in service_paths.items():
                        if proc_cwd == path:
                            messages.append(
                                f"-> Encontrado processo correspondente para "
                                f"'{name}' (PID: {proc.pid}). Finalizando..."
                            )
                            parent = psutil.Process(proc.pid)
                            for child in parent.children(recursive=True):
                                child.kill()
                            parent.kill()
                            terminated_pids.add(proc.pid)
                            messages.append(f"-> Processo de '{name}' (e filhos) finalizado.")
                            break
            except (psutil.NoSuchProcess, psutil.AccessDenied, FileNotFoundError):
                continue
    except Exception as e:
        messages.append(f"  -> Aviso durante o encerramento de processos: {e}")
    return messages
