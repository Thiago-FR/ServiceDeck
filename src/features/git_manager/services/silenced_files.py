import git

from src.features.git_manager.services.git_operations import OperationResult

_STASH_NAME = "servicedeck-silenciados"


class SilencedFiles:
    def get_silenced(self, repo_path: str) -> list[str]:
        try:
            repo = git.Repo(repo_path)
            idx = self._find_stash_index(repo)
            if idx is None:
                return []
            output = repo.git.stash("show", f"stash@{{{idx}}}", "--name-only")
            return [f.strip() for f in output.splitlines() if f.strip()]
        except Exception:
            return []

    def silence(self, repo_path: str, files: list[str]) -> OperationResult:
        if not files:
            return OperationResult(True, "")
        try:
            repo = git.Repo(repo_path)
            currently = self.get_silenced(repo_path)
            self._pop_stash(repo)
            all_files = list(dict.fromkeys(currently + files))
            self._push_stash(repo, all_files)
            return OperationResult(True, f"🔇 {len(files)} arquivo(s) silenciado(s).")
        except Exception as e:
            return OperationResult(False, f"❌ Erro ao silenciar: {e}")

    def unsilence(self, repo_path: str, files: list[str]) -> OperationResult:
        if not files:
            return OperationResult(True, "")
        try:
            repo = git.Repo(repo_path)
            currently = self.get_silenced(repo_path)
            self._pop_stash(repo)
            remaining = [f for f in currently if f not in set(files)]
            if remaining:
                self._push_stash(repo, remaining)
            return OperationResult(True, f"🔔 {len(files)} arquivo(s) restaurado(s).")
        except Exception as e:
            return OperationResult(False, f"❌ Erro ao restaurar: {e}")

    def discard(self, repo_path: str, files: list[str]) -> OperationResult:
        if not files:
            return OperationResult(True, "")
        try:
            repo = git.Repo(repo_path)
            currently = self.get_silenced(repo_path)
            self._pop_stash(repo)
            for f in files:
                try:
                    repo.git.restore(f)
                except Exception:
                    try:
                        repo.git.checkout("--", f)
                    except Exception:
                        pass
            remaining = [f for f in currently if f not in set(files)]
            if remaining:
                self._push_stash(repo, remaining)
            return OperationResult(True, f"🗑 {len(files)} arquivo(s) descartado(s).")
        except Exception as e:
            return OperationResult(False, f"❌ Erro ao descartar: {e}")

    def _find_stash_index(self, repo: git.Repo) -> int | None:
        try:
            stash_list = repo.git.stash("list")
            for line in stash_list.splitlines():
                if _STASH_NAME in line:
                    return int(line.split("{")[1].split("}")[0])
            return None
        except Exception:
            return None

    def _pop_stash(self, repo: git.Repo) -> None:
        idx = self._find_stash_index(repo)
        if idx is not None:
            repo.git.stash("pop", f"stash@{{{idx}}}")

    def _push_stash(self, repo: git.Repo, files: list[str]) -> None:
        repo.git.stash("push", "--include-untracked", "-m", _STASH_NAME, "--", *files)
