import os
import re
from dataclasses import dataclass

import git


@dataclass
class OperationResult:
    success: bool
    message: str


def commit_files(repo_path: str, file_paths: list[str], message: str) -> OperationResult:
    try:
        repo = git.Repo(repo_path)
        repo.index.add(file_paths)
        repo.index.commit(message)
        return OperationResult(True, f"✅ Commit realizado em '{_name(repo_path)}'.")
    except Exception as e:
        return OperationResult(False, f"❌ Erro ao commitar '{_name(repo_path)}': {e}")


def push_repo(repo_path: str, token: str = "", branch: str = "") -> OperationResult:
    try:
        repo = git.Repo(repo_path)
        original_url = repo.remote("origin").url

        if token:
            auth_url = _inject_token(original_url, token)
            repo.git.remote("set-url", "origin", auth_url)

        try:
            target_branch = branch or _safe_current_branch(repo)
            repo.git.push("origin", target_branch, "--set-upstream")
            return OperationResult(
                True, f"🚀 Push realizado em '{_name(repo_path)}' ({target_branch})."
            )
        finally:
            if token:
                repo.git.remote("set-url", "origin", original_url)

    except git.GitCommandError as e:
        stderr = str(e.stderr).strip() if e.stderr else str(e)
        return OperationResult(False, f"❌ Erro ao fazer push em '{_name(repo_path)}': {stderr}")
    except Exception as e:
        return OperationResult(False, f"❌ Erro ao fazer push em '{_name(repo_path)}': {e}")


def create_branch_from(
    repo_path: str,
    base_branch: str,
    new_branch: str,
) -> OperationResult:
    """Cria branch sem mudar o checkout atual."""
    try:
        repo = git.Repo(repo_path)
        repo.git.branch(new_branch, base_branch)
        return OperationResult(
            True, f"🌿 Branch '{new_branch}' criada a partir de '{base_branch}'."
        )
    except git.GitCommandError as e:
        stderr = str(e.stderr).strip() if e.stderr else str(e)
        return OperationResult(False, f"❌ Erro ao criar branch '{new_branch}': {stderr}")
    except Exception as e:
        return OperationResult(False, f"❌ Erro ao criar branch '{new_branch}': {e}")


def checkout_new_branch(
    repo_path: str,
    base_branch: str,
    new_branch: str,
) -> OperationResult:
    """Cria branch E faz checkout para ela."""
    try:
        repo = git.Repo(repo_path)
        repo.git.checkout("-b", new_branch, base_branch)
        return OperationResult(True, f"🌿 Branch '{new_branch}' criada e ativa.")
    except git.GitCommandError as e:
        stderr = str(e.stderr).strip() if e.stderr else str(e)
        return OperationResult(False, f"❌ Erro ao criar branch '{new_branch}': {stderr}")
    except Exception as e:
        return OperationResult(False, f"❌ Erro ao criar branch '{new_branch}': {e}")


def pull_repo(repo_path: str, token: str = "") -> OperationResult:
    try:
        repo = git.Repo(repo_path)
        original_url = repo.remote("origin").url
        if token:
            repo.git.remote("set-url", "origin", _inject_token(original_url, token))
        try:
            repo.git.pull()
            return OperationResult(True, f"⬇ Pull realizado em '{_name(repo_path)}'.")
        finally:
            if token:
                repo.git.remote("set-url", "origin", original_url)
    except git.GitCommandError as e:
        stderr = str(e.stderr).strip() if e.stderr else str(e)
        return OperationResult(False, f"❌ Erro ao fazer pull em '{_name(repo_path)}': {stderr}")
    except Exception as e:
        return OperationResult(False, f"❌ Erro ao fazer pull em '{_name(repo_path)}': {e}")


def delete_branch(
    repo_path: str,
    branch: str,
    also_remote: bool = False,
    token: str = "",
) -> OperationResult:
    try:
        repo = git.Repo(repo_path)
        repo.git.branch("-D", branch)
        msg = f"🗑 Branch '{branch}' deletada localmente em '{_name(repo_path)}'."
        if also_remote:
            original_url = repo.remote("origin").url
            try:
                if token:
                    repo.git.remote("set-url", "origin", _inject_token(original_url, token))
                repo.git.push("origin", "--delete", branch)
                msg += " Removida do remote também."
            except git.GitCommandError as e:
                stderr = str(e.stderr).strip() if e.stderr else str(e)
                msg += f" (Falha ao remover do remote: {stderr})"
            finally:
                if token:
                    repo.git.remote("set-url", "origin", original_url)
        return OperationResult(True, msg)
    except git.GitCommandError as e:
        stderr = str(e.stderr).strip() if e.stderr else str(e)
        return OperationResult(False, f"❌ Erro ao deletar branch '{branch}': {stderr}")
    except Exception as e:
        return OperationResult(False, f"❌ Erro ao deletar branch '{branch}': {e}")


def checkout_branch(repo_path: str, branch: str) -> OperationResult:
    """Troca para uma branch existente (sem criar)."""
    try:
        repo = git.Repo(repo_path)
        repo.git.checkout(branch)
        return OperationResult(
            True, f"✅ [{_name(repo_path)}] Trocou para branch '{branch}'."
        )
    except git.GitCommandError as e:
        stderr = str(e.stderr).strip() if e.stderr else str(e)
        return OperationResult(False, f"❌ Erro ao trocar branch: {stderr}")
    except Exception as e:
        return OperationResult(False, f"❌ Erro ao trocar branch: {e}")


def branch_exists_locally(repo_path: str, branch: str) -> bool:
    try:
        repo = git.Repo(repo_path)
        return branch in [b.name for b in repo.branches]
    except Exception:
        return False


def merge_into_branch(
    repo_path: str,
    source_branch: str,
    target_branch: str,
) -> OperationResult:
    """Faz merge de source em target e volta para a branch original."""
    try:
        repo = git.Repo(repo_path)
        original = _safe_current_branch(repo)
        stashed = _stash_if_needed(repo)
        try:
            repo.git.checkout(target_branch)
            repo.git.merge(source_branch)
            repo.git.checkout(original)
        finally:
            if stashed:
                repo.git.stash("pop")
        return OperationResult(
            True, f"🔀 Merge de '{source_branch}' em '{target_branch}' concluído."
        )
    except git.GitCommandError as e:
        stderr = str(e.stderr).strip() if e.stderr else str(e)
        try:
            repo.git.checkout(original)
        except Exception:
            pass
        return OperationResult(False, f"❌ Conflito no merge: {stderr}")
    except Exception as e:
        return OperationResult(False, f"❌ Erro no merge: {e}")


def create_and_merge_branch(
    repo_path: str,
    current_branch: str,
    base_branch: str,
    new_branch: str,
) -> OperationResult:
    """Cria new_branch a partir de base_branch, faz merge de current_branch e volta."""
    conflict = _validate_branch_name(repo_path, new_branch)
    if conflict:
        return OperationResult(
            False,
            f"❌ Nome inválido '{new_branch}': conflito com branch existente '{conflict}'."
        )

    try:
        repo = git.Repo(repo_path)
        stashed = _stash_if_needed(repo)
        try:
            repo.git.branch(new_branch, base_branch)
            repo.git.checkout(new_branch)
            repo.git.merge(current_branch)
            repo.git.checkout(current_branch)
        finally:
            if stashed:
                repo.git.stash("pop")
        return OperationResult(
            True,
            f"🔀 Branch '{new_branch}' criada de '{base_branch}' com merge de '{current_branch}'.",
        )
    except git.GitCommandError as e:
        stderr = str(e.stderr).strip() if e.stderr else str(e)
        try:
            repo.git.checkout(current_branch)
        except Exception:
            pass
        return OperationResult(False, f"❌ Erro no workflow de branch: {stderr}")
    except Exception as e:
        return OperationResult(False, f"❌ Erro no workflow de branch: {e}")


def merge_branch_into(
    repo_path: str,
    source_branch: str,
    target_branch: str,
) -> OperationResult:
    try:
        repo = git.Repo(repo_path)
        repo.git.checkout(target_branch)
        repo.git.merge(source_branch)
        return OperationResult(
            True, f"🔀 Merge de '{source_branch}' em '{target_branch}' concluído.",
        )
    except git.GitCommandError as e:
        return OperationResult(False, f"❌ Conflito ao fazer merge: {e}")
    except Exception as e:
        return OperationResult(False, f"❌ Erro ao fazer merge: {e}")


def get_remote_url(repo_path: str) -> str | None:
    try:
        repo = git.Repo(repo_path)
        return repo.remote("origin").url
    except Exception:
        return None


def init_repo(repo_path: str) -> OperationResult:
    try:
        git.Repo.init(repo_path)
        return OperationResult(True, f"✅ Repositório inicializado em '{repo_path}'.")
    except Exception as e:
        return OperationResult(False, f"❌ Erro ao inicializar repositório: {e}")


def _inject_token(url: str, token: str) -> str:
    # Converte SSH → HTTPS se necessário: git@github.com:owner/repo.git
    ssh_match = re.match(r"git@([\w.]+):([\w./-]+?)(?:\.git)?$", url)
    if ssh_match:
        host, path = ssh_match.group(1), ssh_match.group(2)
        url = f"https://{host}/{path}.git"

    # Remove token existente se houver, depois injeta o novo
    url = re.sub(r"^(https?://)[^@]+@", r"\1", url)
    return re.sub(r"^(https?://)(.*)", rf"\1{token}@\2", url)


def _validate_branch_name(repo_path: str, new_branch: str) -> str | None:
    """Retorna mensagem de erro ou None se o nome for válido."""
    if not new_branch or new_branch.endswith("/"):
        return "nome incompleto (não pode terminar com '/')"
    try:
        repo = git.Repo(repo_path)
        existing = {b.name for b in repo.branches}
        parts = new_branch.split("/")
        for i in range(1, len(parts)):
            prefix = "/".join(parts[:i])
            if prefix in existing:
                return f"prefixo '{prefix}' já existe como branch"
    except Exception:
        pass
    return None


def _stash_if_needed(repo: git.Repo) -> bool:
    """Faz stash se houver mudanças não commitadas. Retorna True se fez stash."""
    try:
        if repo.is_dirty(untracked_files=True):
            repo.git.stash("push", "--include-untracked", "-m", "servicedeck-auto-stash")
            return True
    except Exception:
        pass
    return False


def _safe_current_branch(repo: git.Repo) -> str:
    try:
        return repo.active_branch.name
    except TypeError:
        return "HEAD"


def _name(repo_path: str) -> str:
    return os.path.basename(repo_path)
