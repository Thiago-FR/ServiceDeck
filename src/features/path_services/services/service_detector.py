import os


def get_microservices(path: str) -> tuple[list[str] | None, str | None]:
    if not os.path.exists(path):
        return None, f"O diretório '{path}' não foi encontrado."
    try:
        services = sorted(
            d for d in os.listdir(path)
            if os.path.isdir(os.path.join(path, d)) and not d.startswith('.')
        )
        return services, None
    except Exception as e:
        return None, f"Ocorreu um erro ao acessar o diretório: {e}"


def detect_default_start_command(service_path: str) -> str:
    if os.path.exists(os.path.join(service_path, 'package.json')):
        return 'yarn dev'
    if os.path.exists(os.path.join(service_path, 'requirements.txt')):
        return 'uvicorn src.main:app --host 0.0.0.0 --port 8000'
    return ''
