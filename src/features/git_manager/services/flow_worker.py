from dataclasses import dataclass
from typing import Callable

from PyQt6.QtCore import QThread, pyqtSignal

from src.features.git_manager.services.git_operations import (
    branch_exists_locally,
    commit_files,
    create_and_merge_branch,
    merge_into_branch,
    push_repo,
)
from src.features.git_manager.services.github_provider import GitHubProvider
from src.features.git_manager.services.provider_detector import detect_provider
from src.features.git_manager.services.git_operations import get_remote_url


@dataclass
class FlowTask:
    path: str
    name: str
    work_branch: str
    base_branch: str
    new_branch: str
    commit_message: str
    files: list[str]
    pr_title: str
    pr_body: str
    token: str


class FlowWorker(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, tasks: list[FlowTask]):
        super().__init__()
        self._tasks = tasks
        self._providers = {"github": GitHubProvider()}

    def run(self) -> None:
        for task in self._tasks:
            self._run_task(task)
        self.finished.emit()

    def _run_task(self, t: FlowTask) -> None:
        # 1. Commit
        if t.files and t.commit_message:
            self.log.emit(f"💾 [{t.name}] Commitando {len(t.files)} arquivo(s)...")
            result = commit_files(t.path, t.files, t.commit_message)
            self.log.emit(result.message)
            if not result.success:
                return

        # 2. Nova branch + merge
        branch_to_push = t.work_branch
        if t.new_branch:
            self.log.emit(f"⚙️ [{t.name}] Preparando branch '{t.new_branch}'...")
            if branch_exists_locally(t.path, t.new_branch):
                result = merge_into_branch(t.path, t.work_branch, t.new_branch)
            else:
                result = create_and_merge_branch(
                    t.path, t.work_branch, t.base_branch, t.new_branch
                )
            self.log.emit(result.message)
            if not result.success:
                return
            branch_to_push = t.new_branch

        # 3. Push work branch (se diferente da nova branch)
        if t.new_branch and t.work_branch != branch_to_push:
            result = push_repo(t.path, token=t.token, branch=t.work_branch)
            self.log.emit(result.message)

        # 4. Push branch principal
        result = push_repo(t.path, token=t.token, branch=branch_to_push)
        self.log.emit(result.message)
        if not result.success:
            return

        # 5. PR
        if not t.pr_title:
            self.log.emit(f"⚠️ [{t.name}] Título do PR vazio, PR não criado.")
            return

        remote_url = get_remote_url(t.path)
        if not remote_url:
            self.log.emit(f"⚠️ [{t.name}] Sem remote origin.")
            return

        provider_name = detect_provider(remote_url) or "github"
        provider = self._providers.get(provider_name)
        if not provider:
            self.log.emit(f"⚠️ [{t.name}] Provider '{provider_name}' não suportado.")
            return

        try:
            pr = provider.create_pull_request(
                token=t.token,
                remote_url=remote_url,
                head_branch=branch_to_push,
                base_branch=t.base_branch,
                title=t.pr_title,
                body=t.pr_body,
            )
            self.log.emit(f"✅ PR #{pr.number} criado: {pr.url}")
        except Exception as e:
            self.log.emit(f"❌ [{t.name}] {e}")


class GenericWorker(QThread):
    """Worker genérico: executa fn(emit) em background e emite finished."""
    log = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, fn: Callable[[Callable[[str], None]], None]):
        super().__init__()
        self._fn = fn

    def run(self) -> None:
        self._fn(self.log.emit)
        self.finished.emit()
