import os
from dataclasses import dataclass, field

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.core.cache import CacheService
from src.core.config import CACHE_FILE
from src.features.git_manager.services.flow_worker import FlowTask, FlowWorker, GenericWorker
from src.features.git_manager.services.git_operations import (
    branch_exists_locally,
    checkout_branch,
    checkout_new_branch,
    commit_files,
    create_branch_from,
    delete_branch,
    get_remote_url,
    init_repo,
    merge_into_branch,
    pull_repo,
    push_repo,
)
from src.features.git_manager.services.github_provider import GitHubProvider
from src.features.git_manager.services.provider_detector import detect_provider
from src.features.git_manager.services.repo_scanner import RepoInfo, RepoStatus, scan_repos
from src.features.git_manager.services.token_store import TokenStore
from src.features.git_manager.ui.widgets.repo_detail_widget import RepoDetailWidget
from src.features.git_manager.ui.widgets.repo_list_widget import RepoListWidget
from src.features.git_manager.ui.widgets.token_config_widget import TokenConfigWidget
from src.ui.log_widget import LogWidget

_CACHE_KEY_BRANCH_SUFFIX = "git_branch_suffix"
_REFRESH_INTERVAL_MS = 5000


def _is_complete_branch_name(name: str) -> bool:
    """Válido se não vazio, não termina com '/' e tem sufixo real após qualquer '/'."""
    stripped = name.strip()
    return bool(stripped) and not stripped.endswith("/") and bool(stripped.split("/")[-1])


@dataclass
class RepoState:
    commit_message: str = ""
    pr_title: str = ""
    pr_body: str = ""
    new_branch_suffix: str = ""
    work_branch: str = ""
    base_branch: str = ""
    selected_files: list[str] = field(default_factory=list)


class GitManagerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._base_path = ""
        self._repos: dict[str, RepoInfo] = {}
        self._current_repo_path = ""
        self._repo_states: dict[str, RepoState] = {}
        self._committed_repos: set[str] = set()
        self._checked_paths: list[str] = []
        self._cache = CacheService(CACHE_FILE)
        self._token_store = TokenStore()
        self._providers = {"github": GitHubProvider()}

        self._build_ui()
        self._setup_timer()
        self._update_action_buttons()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def set_base_path(self, path: str) -> None:
        self._base_path = path
        self._refresh_repos()

    # -------------------------------------------------------------------------
    # Layout
    # -------------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self._token_config = TokenConfigWidget()
        self._token_config.token_validated.connect(self._on_token_validated)
        layout.addWidget(self._token_config)

        # Painel superior: lista + detalhe lado a lado
        lists_splitter = QSplitter(Qt.Orientation.Horizontal)
        lists_splitter.addWidget(self._build_left_panel())
        lists_splitter.addWidget(self._build_right_panel())
        lists_splitter.setStretchFactor(0, 1)
        lists_splitter.setStretchFactor(1, 3)

        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(lists_splitter)
        top_layout.addWidget(self._build_bulk_branch_bar())
        top_layout.addWidget(self._build_branch_status_bar())
        top_layout.addWidget(self._build_action_bar())

        # Log redimensionável verticalmente
        self._log = LogWidget()

        vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        vertical_splitter.addWidget(top_widget)
        vertical_splitter.addWidget(self._log)
        vertical_splitter.setStretchFactor(0, 3)
        vertical_splitter.setStretchFactor(1, 1)

        layout.addWidget(vertical_splitter, stretch=1)

    def _build_left_panel(self) -> QWidget:
        self._repo_list = RepoListWidget()
        self._repo_list.repo_selected.connect(self._on_repo_selected)
        self._repo_list.selection_changed.connect(self._on_selection_changed)

        refresh_btn = QPushButton("🔄 Atualizar agora")
        refresh_btn.clicked.connect(self._refresh_repos)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(self._repo_list)
        layout.addWidget(refresh_btn)
        return panel

    def _build_right_panel(self) -> QWidget:
        self._detail = RepoDetailWidget()
        self._detail.findChild(QPushButton, "copy_commit").clicked.connect(
            self._copy_commit_to_all
        )
        self._detail.findChild(QPushButton, "copy_pr_title").clicked.connect(
            self._copy_pr_title_to_all
        )
        self._detail.findChild(QPushButton, "copy_pr_body").clicked.connect(
            self._copy_pr_body_to_all
        )
        self._detail.commit_message_changed.connect(self._update_action_buttons)
        self._detail.files_selection_changed.connect(self._update_action_buttons)
        self._detail.pr_title_changed.connect(self._update_action_buttons)
        self._detail.branch_fields_changed.connect(self._update_action_buttons)
        self._detail.checkout_requested.connect(self._checkout_branch)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(self._detail)
        return panel

    def _build_bulk_branch_bar(self) -> QGroupBox:
        group = QGroupBox("Criar branch nos repos marcados ☑")
        layout = QHBoxLayout(group)

        self._bulk_base_combo = QComboBox()
        self._bulk_base_combo.setMinimumWidth(120)
        self._bulk_base_combo.currentTextChanged.connect(self._update_bulk_preview)

        self._bulk_name_input = QLineEdit()
        self._bulk_name_input.setPlaceholderText("ex: feature/minha-feature")
        self._bulk_name_input.textChanged.connect(self._update_bulk_preview)

        self._bulk_branch_btn = QPushButton("🌿 Criar branch")
        self._bulk_branch_btn.setEnabled(False)
        self._bulk_branch_btn.clicked.connect(self._create_bulk_branch)

        layout.addWidget(QLabel("Criar a partir de:"))
        layout.addWidget(self._bulk_base_combo)
        layout.addWidget(QLabel("Nome da branch:"))
        layout.addWidget(self._bulk_name_input, stretch=1)
        layout.addWidget(self._bulk_branch_btn)
        return group

    def _build_action_bar(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)

        self._commit_btn = QPushButton("💾 Commit ☑")
        self._commit_btn.setToolTip("Apenas commita os arquivos selecionados")
        self._commit_btn.clicked.connect(self._commit_all)

        self._push_btn = QPushButton("🚀 Push ☑")
        self._push_btn.setToolTip("Apenas envia commits para o remote")
        self._push_btn.clicked.connect(self._push_all)

        self._pr_btn = QPushButton("🔀 Criar PRs ☑")
        self._pr_btn.setToolTip("Cria PRs para branches já publicadas")
        self._pr_btn.clicked.connect(self._create_prs)

        self._flow_btn = QPushButton("⚡ Executar fluxo ☑")
        self._flow_btn.setToolTip("Commit → Push → Criar PR (tudo em um clique)")
        self._flow_btn.clicked.connect(self._execute_full_flow)

        layout.addWidget(self._commit_btn)
        layout.addWidget(self._push_btn)
        layout.addWidget(self._pr_btn)
        layout.addWidget(self._flow_btn)
        return bar

    def _build_branch_status_bar(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(4, 0, 4, 0)

        self._branch_status_label = QLabel("Selecione um repositório")
        self._branch_status_label.setStyleSheet("font-size: 11px; color: #888;")

        self._pull_btn = QPushButton("⬇ Pull")
        self._pull_btn.setToolTip("Atualiza a branch com commits do remote")
        self._pull_btn.setEnabled(False)
        self._pull_btn.clicked.connect(self._pull_current_repo)

        self._delete_branch_btn = QPushButton("🗑 Deletar branch")
        self._delete_branch_btn.setToolTip("Deleta uma branch local (e opcionalmente do remote)")
        self._delete_branch_btn.setEnabled(False)
        self._delete_branch_btn.clicked.connect(self._delete_branch_dialog)

        layout.addWidget(self._branch_status_label, stretch=1)
        layout.addWidget(self._pull_btn)
        layout.addWidget(self._delete_branch_btn)
        return bar

    def _update_branch_status_bar(self, repo: "RepoInfo") -> None:
        parts = []
        if repo.commits_ahead > 0:
            parts.append(f"↑ {repo.commits_ahead} à frente")
        if repo.commits_behind > 0:
            parts.append(f"↓ {repo.commits_behind} atrás do remote")
        if not parts:
            parts = ["✅ Sincronizada"]
        color = "#e67e22" if repo.commits_behind > 0 else "#27ae60"
        self._branch_status_label.setText(
            f"{repo.current_branch}  —  {' | '.join(parts)}"
        )
        self._branch_status_label.setStyleSheet(f"font-size: 11px; color: {color};")
        self._pull_btn.setEnabled(repo.commits_behind > 0)
        self._delete_branch_btn.setEnabled(len(repo.branches) > 1)

    def _setup_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_repos)
        self._timer.setInterval(_REFRESH_INTERVAL_MS)

    # -------------------------------------------------------------------------
    # Button state management
    # -------------------------------------------------------------------------

    def _update_action_buttons(self) -> None:
        self._save_current_state()
        checked = set(self._checked_paths)
        self._commit_btn.setEnabled(self._can_commit(checked))
        self._push_btn.setEnabled(self._can_push(checked))
        self._pr_btn.setEnabled(self._can_create_prs(checked))
        self._flow_btn.setEnabled(bool(checked) and bool(self._repos))
        self._update_bulk_preview()

    def _can_commit(self, checked: set[str]) -> bool:
        return any(
            bool(self._repo_states[p].commit_message) and bool(self._repo_states[p].selected_files)
            for p in checked if p in self._repo_states
        )

    def _can_push(self, checked: set[str]) -> bool:
        for path in checked:
            if path in self._committed_repos:
                return True
            repo = self._repos.get(path)
            if repo and repo.status == RepoStatus.AHEAD:
                return True
        return False

    def _can_create_prs(self, checked: set[str]) -> bool:
        return any(
            bool(self._repo_states[p].pr_title)
            and bool(self._repo_states[p].base_branch)
            for p in checked if p in self._repo_states
        )

    def _update_bulk_preview(self) -> None:
        base = self._bulk_base_combo.currentText()
        name = self._bulk_name_input.text().strip()
        self._bulk_branch_btn.setEnabled(bool(base and name and self._checked_paths))

    # -------------------------------------------------------------------------
    # Repo scanning & timer
    # -------------------------------------------------------------------------

    def _refresh_repos(self) -> None:
        if not self._base_path:
            return

        repos, no_git = scan_repos(self._base_path)
        new_paths = {r.full_path for r in repos}

        for path in list(self._repo_states.keys()):
            if path not in new_paths:
                self._repo_states.pop(path, None)

        suffix = self._load_branch_suffix()
        for repo in repos:
            if repo.full_path not in self._repo_states:
                self._repo_states[repo.full_path] = RepoState(
                    work_branch=repo.current_branch,
                    base_branch=repo.branches[0] if repo.branches else "",
                    new_branch_suffix=suffix,
                )

        self._repos = {r.full_path: r for r in repos}
        self._repo_list.load_repos(repos)
        self._refresh_bulk_branches(repos)
        self._refresh_detail_if_current(repos)

        if no_git:
            self._log.append(
                f"⚠️ Sem .git: {', '.join(no_git)}. Use 'git init' se necessário."
            )

        if not repos and no_git:
            self._offer_git_init(no_git)

        if not self._timer.isActive() and self._base_path:
            self._timer.start()

        self._update_action_buttons()

    def _refresh_detail_if_current(self, repos: list[RepoInfo]) -> None:
        if not self._current_repo_path:
            return
        updated = next((r for r in repos if r.full_path == self._current_repo_path), None)
        if updated:
            self._detail.refresh_branches(updated)
            self._update_branch_status_bar(updated)

    def _refresh_bulk_branches(self, repos: list[RepoInfo]) -> None:
        all_branches: set[str] = set()
        for repo in repos:
            all_branches.update(repo.branches)
        current = self._bulk_base_combo.currentText()
        self._bulk_base_combo.blockSignals(True)
        self._bulk_base_combo.clear()
        for branch in sorted(all_branches):
            self._bulk_base_combo.addItem(branch)
        if current in all_branches:
            self._bulk_base_combo.setCurrentText(current)
        self._bulk_base_combo.blockSignals(False)

    def _offer_git_init(self, dirs_without_git: list[str]) -> None:
        answer = QMessageBox.question(
            self,
            "Nenhum repositório git encontrado",
            "Nenhuma pasta com .git foi encontrada.\nDeseja inicializar repositórios agora?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        for name in dirs_without_git:
            result = init_repo(os.path.join(self._base_path, name))
            self._log.append(result.message)

    # -------------------------------------------------------------------------
    # Selection handlers
    # -------------------------------------------------------------------------

    def _on_selection_changed(self, checked_paths: list[str]) -> None:
        self._checked_paths = checked_paths
        self._update_action_buttons()

    def _on_repo_selected(self, repo_path: str) -> None:
        self._save_current_state()
        repo = self._repos.get(repo_path)
        if not repo:
            return
        self._current_repo_path = repo_path
        self._detail.load_repo(repo)
        self._restore_state(repo_path)
        self._update_branch_status_bar(repo)

    def _on_token_validated(self, provider: str, _token: str) -> None:
        self._log.append(f"✅ Token {provider} configurado com sucesso.")
        self._update_action_buttons()

    # -------------------------------------------------------------------------
    # State persistence
    # -------------------------------------------------------------------------

    def _save_current_state(self) -> None:
        path = self._current_repo_path
        if not path or path not in self._repo_states:
            return
        self._repo_states[path] = RepoState(
            commit_message=self._detail.get_commit_message(),
            pr_title=self._detail.get_pr_title(),
            pr_body=self._detail.get_pr_body(),
            new_branch_suffix=self._detail.get_new_branch_suffix(),
            work_branch=self._detail.get_work_branch(),
            base_branch=self._detail.get_base_branch(),
            selected_files=self._detail.get_selected_files(),
        )

    def _restore_state(self, repo_path: str) -> None:
        state = self._repo_states.get(repo_path)
        if not state:
            return
        self._detail.set_commit_message(state.commit_message)
        self._detail.set_pr_title(state.pr_title)
        self._detail.set_pr_body(state.pr_body)
        self._detail.set_new_branch_suffix(state.new_branch_suffix)

    # -------------------------------------------------------------------------
    # Copy to all
    # -------------------------------------------------------------------------

    def _copy_commit_to_all(self) -> None:
        msg = self._detail.get_commit_message()
        for state in self._repo_states.values():
            state.commit_message = msg
        self._log.append("📋 Mensagem de commit copiada para todos os repos.")
        self._update_action_buttons()

    def _copy_pr_title_to_all(self) -> None:
        title = self._detail.get_pr_title()
        for state in self._repo_states.values():
            state.pr_title = title
        self._log.append("📋 Título do PR copiado para todos os repos.")
        self._update_action_buttons()

    def _copy_pr_body_to_all(self) -> None:
        body = self._detail.get_pr_body()
        for state in self._repo_states.values():
            state.pr_body = body
        self._log.append("📋 Descrição do PR copiada para todos os repos.")

    # -------------------------------------------------------------------------
    # Actions (operate on checked repos only)
    # -------------------------------------------------------------------------

    def _commit_all(self) -> None:
        self._save_current_state()
        self._log.append("--- COMMIT ---")
        snapshots = [
            (p, list(self._repo_states[p].selected_files), self._repo_states[p].commit_message)
            for p in self._checked_paths if p in self._repo_states
        ]
        committed: list[str] = []

        def _do_commit(emit):
            for path, files, msg in snapshots:
                if not files or not msg:
                    continue
                r = commit_files(path, files, msg)
                emit(r.message)
                if r.success:
                    committed.append(path)

        self._start_worker(
            self._commit_btn, "💾 Commitando...", _do_commit,
            lambda: [self._committed_repos.add(p) for p in committed],
        )

    def _push_all(self) -> None:
        token = self._token_store.load("github")
        self._log.append("--- PUSH ---")
        to_push = [
            p for p in self._checked_paths
            if p in self._committed_repos
            or (self._repos.get(p) and self._repos[p].status == RepoStatus.AHEAD)
        ]
        pushed: list[str] = []

        def _do_push(emit):
            for path in to_push:
                r = push_repo(path, token=token)
                emit(r.message)
                if r.success:
                    pushed.append(path)

        self._start_worker(
            self._push_btn, "🚀 Enviando...", _do_push,
            lambda: [self._committed_repos.discard(p) for p in pushed],
        )

    def _create_prs(self) -> None:
        self._save_current_state()
        token = self._token_store.load("github")
        if not token:
            self._log.append("❌ Configure o token do GitHub antes de criar PRs.")
            return

        self._log.append("--- CRIANDO PRs ---")
        state_items: list[tuple[str, RepoState]] = []
        for p in self._checked_paths:
            s = self._repo_states.get(p)
            if not s or not s.pr_title or not s.base_branch:
                continue
            state_items.append((p, RepoState(
                commit_message=s.commit_message,
                pr_title=s.pr_title,
                pr_body=s.pr_body,
                new_branch_suffix=s.new_branch_suffix,
                work_branch=s.work_branch,
                base_branch=s.base_branch,
                selected_files=list(s.selected_files),
            )))

        def _do_prs(emit):
            for path, state in state_items:
                self._open_pr(path, state, state.work_branch, token, emit)
                new_branch = state.new_branch_suffix.strip()
                if not _is_complete_branch_name(new_branch):
                    continue
                name = os.path.basename(path)
                if branch_exists_locally(path, new_branch):
                    emit(f"ℹ️ [{name}] Branch '{new_branch}' já existe, fazendo merge.")
                else:
                    result = create_branch_from(path, state.base_branch, new_branch)
                    emit(result.message)
                    if not result.success:
                        continue
                result = merge_into_branch(path, state.work_branch, new_branch)
                emit(result.message)
                if not result.success:
                    continue
                result = push_repo(path, token=token, branch=new_branch)
                emit(result.message)
                self._open_pr(path, state, new_branch, token, emit)

        self._start_worker(self._pr_btn, "🔀 Criando PRs...", _do_prs, lambda: None)

    def _execute_full_flow(self) -> None:
        self._save_current_state()
        token = self._token_store.load("github")
        self._log.append("--- EXECUTAR FLUXO ---")

        tasks: list[FlowTask] = []
        for path in self._checked_paths:
            state = self._repo_states.get(path)
            if not state:
                continue
            repo_info = self._repos.get(path)
            files = state.selected_files or (
                [f.path for f in repo_info.changed_files] if repo_info else []
            )
            new_branch = state.new_branch_suffix.strip()
            tasks.append(FlowTask(
                path=path,
                name=os.path.basename(path),
                work_branch=state.work_branch,
                base_branch=state.base_branch,
                new_branch=new_branch if _is_complete_branch_name(new_branch) else "",
                commit_message=state.commit_message,
                files=files,
                pr_title=state.pr_title,
                pr_body=state.pr_body,
                token=token,
            ))

        if not tasks:
            return

        self._set_all_busy(self._flow_btn, "⏳ Executando...")

        self._worker = FlowWorker(tasks)
        self._worker.log.connect(self._log.append)
        self._worker.finished.connect(self._on_flow_finished)
        self._worker.start()

    def _on_flow_finished(self) -> None:
        self._set_all_idle()

    def _open_pr(
        self,
        path: str,
        state: "RepoState",
        head_branch: str,
        token: str,
        emit=None,
    ) -> None:
        log = emit or self._log.append
        name = os.path.basename(path)

        if not state.pr_title:
            log(f"⚠️ [{name}] Título do PR vazio, pulando.")
            return

        if not token:
            log("❌ Token não configurado, PR não criado.")
            return

        remote_url = get_remote_url(path)
        if not remote_url:
            log(f"⚠️ [{name}] Sem remote origin.")
            return

        provider_name = detect_provider(remote_url) or "github"
        provider = self._providers.get(provider_name)
        if not provider:
            log(f"⚠️ [{name}] Provider '{provider_name}' não suportado.")
            return

        if not self._branch_exists_on_remote(remote_url, head_branch, token):
            log(f"⚠️ [{name}] Branch '{head_branch}' não existe no remote. Fazendo push...")
            result = push_repo(path, token=token, branch=head_branch)
            log(result.message)
            still_missing = not self._branch_exists_on_remote(remote_url, head_branch, token)
            if not result.success and still_missing:
                return

        try:
            pr = provider.create_pull_request(
                token=token,
                remote_url=remote_url,
                head_branch=head_branch,
                base_branch=state.base_branch,
                title=state.pr_title,
                body=state.pr_body,
            )
            log(f"✅ PR #{pr.number} criado: {pr.url}")
        except Exception as e:
            log(f"❌ [{name}] Erro ao criar PR: {e}")

    def _start_worker(self, btn: QPushButton, busy_text: str, fn, on_finish) -> None:
        self._set_all_busy(btn, busy_text)
        self._worker = GenericWorker(fn)
        self._worker.log.connect(self._log.append)
        self._worker.finished.connect(lambda: self._on_worker_finished(on_finish))
        self._worker.start()

    def _on_worker_finished(self, on_finish) -> None:
        on_finish()
        self._set_all_idle()

    def _set_all_busy(self, active_btn: QPushButton, text: str) -> None:
        for btn in (self._commit_btn, self._push_btn, self._pr_btn, self._flow_btn):
            btn.setEnabled(False)
        active_btn.setText(text)

    def _set_all_idle(self) -> None:
        self._commit_btn.setText("💾 Commit ☑")
        self._push_btn.setText("🚀 Push ☑")
        self._pr_btn.setText("🔀 Criar PRs ☑")
        self._flow_btn.setText("⚡ Executar fluxo ☑")
        self._update_action_buttons()

    def _checkout_branch(self, branch: str) -> None:
        if not self._current_repo_path:
            return
        result = checkout_branch(self._current_repo_path, branch)
        self._log.append(result.message)
        if result.success:
            if self._current_repo_path in self._repo_states:
                self._repo_states[self._current_repo_path].work_branch = branch
            self._refresh_repos()

    def _pull_current_repo(self) -> None:
        if not self._current_repo_path:
            return
        token = self._token_store.load("github")
        self._log.append("--- PULL ---")
        path = self._current_repo_path

        def work(emit):
            r = pull_repo(path, token=token)
            emit(r.message)

        self._run_background(work, self._refresh_repos)

    def _delete_branch_dialog(self) -> None:
        if not self._current_repo_path:
            return
        repo = self._repos.get(self._current_repo_path)
        if not repo:
            return

        other_branches = [b for b in repo.branches if b != repo.current_branch]
        if not other_branches:
            self._log.append("⚠️ Não há outras branches para deletar.")
            return

        from PyQt6.QtWidgets import QInputDialog
        msg = f"Repo: {repo.name}   Atual: {repo.current_branch}\n\nSelecione a branch a deletar:"
        branch, ok = QInputDialog.getItem(
            self, "Deletar branch", msg, other_branches, 0, False,
        )
        if not ok:
            return

        also_remote = QMessageBox.question(
            self,
            "Remover do remote?",
            f"Deletar '{branch}' também do remote (origin)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes

        token = self._token_store.load("github") if also_remote else ""
        result = delete_branch(
            self._current_repo_path, branch, also_remote=also_remote, token=token
        )
        self._log.append(result.message)
        if result.success:
            self._refresh_repos()

    def _run_background(self, fn, on_finish=None) -> None:
        self._worker = GenericWorker(fn)
        self._worker.log.connect(self._log.append)
        if on_finish:
            self._worker.finished.connect(on_finish)
        self._worker.start()

    def _branch_exists_on_remote(self, remote_url: str, branch: str, token: str) -> bool:
        from src.features.git_manager.services.provider_detector import parse_owner_repo
        import requests as req

        parsed = parse_owner_repo(remote_url)
        if not parsed:
            return False
        owner, repo = parsed
        resp = req.get(
            f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=10,
        )
        return resp.status_code == 200

    def _create_bulk_branch(self) -> None:
        base = self._bulk_base_combo.currentText()
        new_branch = self._bulk_name_input.text().strip()
        if not base or not new_branch or not self._checked_paths:
            return

        self._log.append(f"--- CRIAR BRANCH '{new_branch}' NOS REPOS MARCADOS ---")
        for path in self._checked_paths:
            result = checkout_new_branch(path, base, new_branch)
            self._log.append(result.message)

    # -------------------------------------------------------------------------
    # Branch suffix cache
    # -------------------------------------------------------------------------

    def _save_branch_suffix(self) -> None:
        suffix = self._detail.get_new_branch_suffix()
        self._save_branch_suffix_value(suffix)

    def _save_branch_suffix_value(self, suffix: str) -> None:
        if not suffix:
            return
        data = self._cache.load()
        data[_CACHE_KEY_BRANCH_SUFFIX] = suffix
        self._cache.save(data)

    def _load_branch_suffix(self) -> str:
        return self._cache.load().get(_CACHE_KEY_BRANCH_SUFFIX, "")
