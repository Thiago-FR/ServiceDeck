import os
from dataclasses import dataclass, field
from enum import Enum

import git


class RepoStatus(Enum):
    CHANGES = "changes"   # arquivos modificados/untracked/staged
    AHEAD = "ahead"       # commits locais não publicados
    CLEAN = "clean"       # nada pendente


@dataclass
class ChangedFile:
    path: str
    status: str  # M=modified, A=staged/added, ?=untracked, D=deleted


@dataclass
class RepoInfo:
    name: str
    full_path: str
    status: RepoStatus = RepoStatus.CLEAN
    changed_files: list[ChangedFile] = field(default_factory=list)
    current_branch: str = ""
    branches: list[str] = field(default_factory=list)
    commits_ahead: int = 0
    commits_behind: int = 0

    @property
    def has_changes(self) -> bool:
        return bool(self.changed_files)


def scan_repos(base_path: str) -> tuple[list[RepoInfo], list[str]]:
    """Returns (all_repos_with_git, dirs_without_git)."""
    if not os.path.exists(base_path):
        return [], []

    repos: list[RepoInfo] = []
    no_git: list[str] = []

    for name in sorted(os.listdir(base_path)):
        full_path = os.path.join(base_path, name)
        if not os.path.isdir(full_path) or name.startswith("."):
            continue

        if not os.path.exists(os.path.join(full_path, ".git")):
            no_git.append(name)
            continue

        try:
            repo = git.Repo(full_path)
            changed = _collect_changed_files(repo)
            ahead = _commits_ahead(repo)
            status = _determine_status(changed, ahead)

            repos.append(RepoInfo(
                name=name,
                full_path=full_path,
                status=status,
                changed_files=changed,
                current_branch=_safe_branch_name(repo),
                branches=_list_branches(repo),
                commits_ahead=ahead,
                commits_behind=_commits_behind(repo),
            ))
        except git.InvalidGitRepositoryError:
            no_git.append(name)
        except Exception:
            continue

    return repos, no_git


def _determine_status(changed: list[ChangedFile], ahead: int) -> RepoStatus:
    if changed:
        return RepoStatus.CHANGES
    if ahead > 0:
        return RepoStatus.AHEAD
    return RepoStatus.CLEAN


def _collect_changed_files(repo: git.Repo) -> list[ChangedFile]:
    files: list[ChangedFile] = []
    seen: set[str] = set()

    try:
        for item in repo.index.diff(None):
            if item.a_path not in seen:
                files.append(ChangedFile(item.a_path, "D" if item.deleted_file else "M"))
                seen.add(item.a_path)
    except Exception:
        pass

    try:
        for item in repo.index.diff("HEAD"):
            if item.a_path not in seen:
                files.append(ChangedFile(item.a_path, "D" if item.deleted_file else "A"))
                seen.add(item.a_path)
    except Exception:
        try:
            for entry in repo.index.entries:
                path = entry[0]
                if path not in seen:
                    files.append(ChangedFile(path, "A"))
                    seen.add(path)
        except Exception:
            pass

    try:
        for path in repo.untracked_files:
            if path not in seen:
                files.append(ChangedFile(path, "?"))
                seen.add(path)
    except Exception:
        pass

    return sorted(files, key=lambda f: f.path)


def _commits_ahead(repo: git.Repo) -> int:
    try:
        branch = repo.active_branch
        tracking = branch.tracking_branch()

        if tracking:
            ref = tracking.name
        else:
            # Tenta origin/<branch> como fallback
            try:
                remote_refs = [r.name for r in repo.remote("origin").refs]
                candidate = f"origin/{branch.name}"
                ref = candidate if candidate in remote_refs else None
            except Exception:
                ref = None

        if ref:
            return sum(1 for _ in repo.iter_commits(f"{ref}..{branch.name}"))

        # Branch nunca publicada: conta commits locais como "ahead"
        try:
            return sum(1 for _ in repo.iter_commits(branch.name))
        except Exception:
            return 0

    except Exception:
        return 0


def _commits_behind(repo: git.Repo) -> int:
    """Commits que o remote tem e o local não tem (precisa de pull)."""
    try:
        branch = repo.active_branch
        tracking = branch.tracking_branch()

        if tracking:
            ref = tracking.name
        else:
            try:
                remote_refs = [r.name for r in repo.remote("origin").refs]
                candidate = f"origin/{branch.name}"
                ref = candidate if candidate in remote_refs else None
            except Exception:
                ref = None

        if ref:
            return sum(1 for _ in repo.iter_commits(f"{branch.name}..{ref}"))
        return 0
    except Exception:
        return 0


def _safe_branch_name(repo: git.Repo) -> str:
    try:
        return repo.active_branch.name
    except TypeError:
        return "(detached HEAD)"


def _list_branches(repo: git.Repo) -> list[str]:
    try:
        return sorted(b.name for b in repo.branches)
    except Exception:
        return []
