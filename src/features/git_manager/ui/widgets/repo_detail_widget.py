from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.features.git_manager.services.repo_scanner import RepoInfo, RepoStatus


class RepoDetailWidget(QWidget):
    commit_message_changed = pyqtSignal()
    files_selection_changed = pyqtSignal()
    pr_title_changed = pyqtSignal()
    branch_fields_changed = pyqtSignal()
    checkout_requested = pyqtSignal(str)
    silence_requested = pyqtSignal(list)   # stash
    unsilence_requested = pyqtSignal(list)
    discard_requested = pyqtSignal(list)
    hide_requested = pyqtSignal(list)      # cache (app-level)
    unhide_requested = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_checkboxes: dict[str, QCheckBox] = {}
        self._silenced_checkboxes: dict[str, QCheckBox] = {}
        self._hidden_checkboxes: dict[str, QCheckBox] = {}
        self._build_ui()
        self.setEnabled(False)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def load_repo(
        self,
        repo: RepoInfo,
        silenced: list[str] | None = None,
        hidden: set[str] | None = None,
    ) -> None:
        self.setEnabled(True)
        self._populate_files(repo, silenced or [], hidden or set())
        self._populate_branches(repo)

    def refresh_branches(self, repo: RepoInfo) -> None:
        self._populate_branches(repo)

    def get_selected_files(self) -> list[str]:
        return [p for p, cb in self._file_checkboxes.items() if cb.isChecked()]

    def get_commit_message(self) -> str:
        return self._commit_msg.text().strip()

    def set_commit_message(self, text: str) -> None:
        self._commit_msg.blockSignals(True)
        self._commit_msg.setText(text)
        self._commit_msg.blockSignals(False)

    def get_pr_title(self) -> str:
        return self._pr_title.text().strip()

    def set_pr_title(self, text: str) -> None:
        self._pr_title.blockSignals(True)
        self._pr_title.setText(text)
        self._pr_title.blockSignals(False)

    def get_pr_body(self) -> str:
        return self._pr_body.toPlainText().strip()

    def set_pr_body(self, text: str) -> None:
        self._pr_body.blockSignals(True)
        self._pr_body.setPlainText(text)
        self._pr_body.blockSignals(False)

    def get_work_branch(self) -> str:
        return self._current_branch_combo.currentText()

    def get_base_branch(self) -> str:
        return self._base_branch.currentText()

    def get_new_branch_suffix(self) -> str:
        return ""

    def set_new_branch_suffix(self, text: str) -> None:
        pass

    def get_new_branch_name(self) -> str:
        return ""

    # -------------------------------------------------------------------------
    # UI construction
    # -------------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(self._build_branch_row())
        layout.addWidget(self._build_files_group())
        layout.addWidget(self._build_commit_group())
        layout.addWidget(self._build_pr_group())

    def _build_branch_row(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        self._current_branch_combo = QComboBox()
        self._current_branch_combo.setStyleSheet("font-weight: bold; color: #4CAF50;")
        self._current_branch_combo.setEnabled(False)
        self._current_branch_combo.currentTextChanged.connect(self._on_checkout_requested)
        layout.addWidget(QLabel("Branch atual:"))
        layout.addWidget(self._current_branch_combo, stretch=1)
        return widget

    def _build_files_group(self) -> QGroupBox:
        group = QGroupBox("Arquivos Modificados")
        layout = QVBoxLayout(group)

        self._files_tabs = QTabWidget()
        self._files_tabs.setMaximumHeight(420)

        # ── Tab 0: arquivos ativos ──────────────────────────────────────────
        active_w = QWidget()
        al = QVBoxLayout(active_w)
        al.setContentsMargins(4, 4, 4, 4)
        al.setSpacing(4)

        ah = QHBoxLayout()
        b = QPushButton("☑ Todos")
        b.setFixedWidth(70)
        b.clicked.connect(self._select_all_files)
        ah.addWidget(b)
        b = QPushButton("☐ Nenhum")
        b.setFixedWidth(80)
        b.clicked.connect(self._deselect_all_files)
        ah.addWidget(b)
        ah.addStretch()
        self._silence_btn = QPushButton("🔇 Silenciar")
        self._silence_btn.setToolTip("Move para stash — permite trocar de branch")
        self._silence_btn.clicked.connect(self._emit_silence)
        self._hide_btn = QPushButton("👁 Ocultar")
        self._hide_btn.setToolTip(
            "Oculta da lista — não inclui em commits deste app, mas não afeta o git"
        )
        self._hide_btn.clicked.connect(self._emit_hide)
        ah.addWidget(self._silence_btn)
        ah.addWidget(self._hide_btn)
        al.addLayout(ah)

        sa = QScrollArea()
        sa.setWidgetResizable(True)
        self._files_container = QWidget()
        self._files_layout = QVBoxLayout(self._files_container)
        self._files_layout.setContentsMargins(2, 2, 2, 2)
        self._files_layout.setSpacing(2)
        sa.setWidget(self._files_container)
        al.addWidget(sa)
        self._files_tabs.addTab(active_w, "📁 Arquivos")

        # ── Tab 1: silenciados (stash) ──────────────────────────────────────
        silenced_w = QWidget()
        sl = QVBoxLayout(silenced_w)
        sl.setContentsMargins(4, 4, 4, 4)
        sl.setSpacing(4)

        sh = QHBoxLayout()
        b = QPushButton("☑ Todos")
        b.setFixedWidth(70)
        b.clicked.connect(self._select_all_silenced)
        sh.addWidget(b)
        b = QPushButton("☐ Nenhum")
        b.setFixedWidth(80)
        b.clicked.connect(self._deselect_all_silenced)
        sh.addWidget(b)
        sh.addStretch()
        self._activate_btn = QPushButton("🔔 Ativar selecionados")
        self._activate_btn.clicked.connect(self._emit_unsilence)
        self._discard_btn = QPushButton("🗑 Descartar selecionados")
        self._discard_btn.setStyleSheet("QPushButton { color: #c0392b; }")
        self._discard_btn.clicked.connect(self._emit_discard)
        sh.addWidget(self._activate_btn)
        sh.addWidget(self._discard_btn)
        sl.addLayout(sh)

        ssa = QScrollArea()
        ssa.setWidgetResizable(True)
        self._silenced_container = QWidget()
        self._silenced_layout = QVBoxLayout(self._silenced_container)
        self._silenced_layout.setContentsMargins(2, 2, 2, 2)
        self._silenced_layout.setSpacing(2)
        ssa.setWidget(self._silenced_container)
        sl.addWidget(ssa)
        self._silenced_tab_idx = self._files_tabs.addTab(silenced_w, "🔇 Silenciados")
        self._files_tabs.setTabVisible(self._silenced_tab_idx, False)

        # ── Tab 2: ocultos (cache) ──────────────────────────────────────────
        hidden_w = QWidget()
        hl = QVBoxLayout(hidden_w)
        hl.setContentsMargins(4, 4, 4, 4)
        hl.setSpacing(4)

        hh = QHBoxLayout()
        b = QPushButton("☑ Todos")
        b.setFixedWidth(70)
        b.clicked.connect(self._select_all_hidden)
        hh.addWidget(b)
        b = QPushButton("☐ Nenhum")
        b.setFixedWidth(80)
        b.clicked.connect(self._deselect_all_hidden)
        hh.addWidget(b)
        hh.addStretch()
        self._show_btn = QPushButton("👁 Mostrar selecionados")
        self._show_btn.clicked.connect(self._emit_unhide)
        hh.addWidget(self._show_btn)
        hl.addLayout(hh)

        hsa = QScrollArea()
        hsa.setWidgetResizable(True)
        self._hidden_container = QWidget()
        self._hidden_layout = QVBoxLayout(self._hidden_container)
        self._hidden_layout.setContentsMargins(2, 2, 2, 2)
        self._hidden_layout.setSpacing(2)
        hsa.setWidget(self._hidden_container)
        hl.addWidget(hsa)
        self._hidden_tab_idx = self._files_tabs.addTab(hidden_w, "👁 Ocultos")
        self._files_tabs.setTabVisible(self._hidden_tab_idx, False)

        layout.addWidget(self._files_tabs)
        return group

    def _build_commit_group(self) -> QGroupBox:
        group = QGroupBox("Commit")
        layout = QHBoxLayout(group)
        self._commit_msg = QLineEdit()
        self._commit_msg.setPlaceholderText("Mensagem do commit...")
        self._commit_msg.textChanged.connect(lambda: self.commit_message_changed.emit())
        copy_btn = QPushButton("→ Copiar para todos")
        copy_btn.setObjectName("copy_commit")
        layout.addWidget(QLabel("Mensagem:"))
        layout.addWidget(self._commit_msg, stretch=1)
        layout.addWidget(copy_btn)
        return group

    def _build_pr_group(self) -> QGroupBox:
        group = QGroupBox("Pull Request")
        layout = QVBoxLayout(group)

        base_row = QHBoxLayout()
        self._base_branch = QComboBox()
        self._base_branch.currentTextChanged.connect(self._on_base_branch_changed)
        base_row.addWidget(QLabel("Branch de destino:"))
        base_row.addWidget(self._base_branch, stretch=1)

        title_row = QHBoxLayout()
        self._pr_title = QLineEdit()
        self._pr_title.setPlaceholderText("Título do PR...")
        self._pr_title.textChanged.connect(lambda: self.pr_title_changed.emit())
        copy_title_btn = QPushButton("→ Copiar para todos")
        copy_title_btn.setObjectName("copy_pr_title")
        title_row.addWidget(QLabel("Título:"))
        title_row.addWidget(self._pr_title, stretch=1)
        title_row.addWidget(copy_title_btn)

        body_header = QHBoxLayout()
        copy_body_btn = QPushButton("→ Copiar para todos")
        copy_body_btn.setObjectName("copy_pr_body")
        body_header.addWidget(QLabel("Descrição (markdown):"))
        body_header.addStretch()
        body_header.addWidget(copy_body_btn)

        self._pr_body = QTextEdit()
        self._pr_body.setPlaceholderText(
            "Descrição do PR em markdown...\n\nExemplo:\n## O que foi feito\n- ✅ Item 1\n- 🔧 Item 2"
        )
        self._pr_body.setMinimumHeight(80)

        layout.addLayout(base_row)
        layout.addLayout(title_row)
        layout.addLayout(body_header)
        layout.addWidget(self._pr_body)
        return group

    # -------------------------------------------------------------------------
    # Populate
    # -------------------------------------------------------------------------

    def _populate_files(
        self, repo: RepoInfo, silenced: list[str], hidden: set[str]
    ) -> None:
        self._clear_layout(self._files_layout)
        self._clear_layout(self._silenced_layout)
        self._clear_layout(self._hidden_layout)
        self._file_checkboxes.clear()
        self._silenced_checkboxes.clear()
        self._hidden_checkboxes.clear()

        silenced_set = set(silenced)

        for cf in repo.changed_files:
            if cf.path in silenced_set:
                continue
            if cf.path in hidden:
                cb = QCheckBox(cf.path)
                cb.setChecked(False)
                cb.setStyleSheet("color: #888;")
                self._hidden_checkboxes[cf.path] = cb
                self._hidden_layout.addWidget(cb)
                continue
            cb = QCheckBox(f"[{cf.status}] {cf.path}")
            cb.setChecked(True)
            cb.stateChanged.connect(lambda _: self.files_selection_changed.emit())
            self._file_checkboxes[cf.path] = cb
            self._files_layout.addWidget(cb)

        for path in silenced:
            cb = QCheckBox(path)
            cb.setChecked(False)
            self._silenced_checkboxes[path] = cb
            self._silenced_layout.addWidget(cb)

        self._set_tab_visibility(
            self._silenced_tab_idx, silenced, "🔇 Silenciados"
        )
        hidden_shown = [p for p in hidden if any(cf.path == p for cf in repo.changed_files)]
        self._set_tab_visibility(
            self._hidden_tab_idx, hidden_shown, "👁 Ocultos"
        )

    def _set_tab_visibility(
        self, idx: int, items: list, base_label: str
    ) -> None:
        has = bool(items)
        self._files_tabs.setTabVisible(idx, has)
        if has:
            self._files_tabs.setTabText(idx, f"{base_label} ({len(items)})")

    def _populate_branches(self, repo: RepoInfo) -> None:
        self._current_branch_combo.blockSignals(True)
        self._current_branch_combo.clear()
        for branch in repo.branches:
            self._current_branch_combo.addItem(branch)
        if repo.current_branch:
            idx = self._current_branch_combo.findText(repo.current_branch)
            if idx >= 0:
                self._current_branch_combo.setCurrentIndex(idx)
        can_switch = repo.status != RepoStatus.CHANGES
        self._current_branch_combo.setEnabled(can_switch)
        self._current_branch_combo.setToolTip(
            "Clique para trocar de branch"
            if can_switch
            else "Faça commit ou descarte as alterações para trocar de branch"
        )
        self._current_branch_combo.blockSignals(False)

        current_sel = self._base_branch.currentText()
        self._base_branch.blockSignals(True)
        self._base_branch.clear()
        for branch in repo.branches:
            if branch != repo.current_branch:
                self._base_branch.addItem(branch)
        if current_sel and self._base_branch.findText(current_sel) >= 0:
            self._base_branch.setCurrentText(current_sel)
        self._base_branch.blockSignals(False)

    # -------------------------------------------------------------------------
    # Bulk actions — active files
    # -------------------------------------------------------------------------

    def _select_all_files(self) -> None:
        for cb in self._file_checkboxes.values():
            cb.setChecked(True)

    def _deselect_all_files(self) -> None:
        for cb in self._file_checkboxes.values():
            cb.setChecked(False)

    def _emit_silence(self) -> None:
        sel = [p for p, cb in self._file_checkboxes.items() if cb.isChecked()]
        if sel:
            self.silence_requested.emit(sel)

    def _emit_hide(self) -> None:
        sel = [p for p, cb in self._file_checkboxes.items() if cb.isChecked()]
        if sel:
            self.hide_requested.emit(sel)

    # ── Silenced (stash) ────────────────────────────────────────────────────

    def _select_all_silenced(self) -> None:
        for cb in self._silenced_checkboxes.values():
            cb.setChecked(True)

    def _deselect_all_silenced(self) -> None:
        for cb in self._silenced_checkboxes.values():
            cb.setChecked(False)

    def _emit_unsilence(self) -> None:
        sel = [p for p, cb in self._silenced_checkboxes.items() if cb.isChecked()]
        if sel:
            self.unsilence_requested.emit(sel)

    def _emit_discard(self) -> None:
        sel = [p for p, cb in self._silenced_checkboxes.items() if cb.isChecked()]
        if sel:
            self.discard_requested.emit(sel)

    # ── Hidden (cache) ──────────────────────────────────────────────────────

    def _select_all_hidden(self) -> None:
        for cb in self._hidden_checkboxes.values():
            cb.setChecked(True)

    def _deselect_all_hidden(self) -> None:
        for cb in self._hidden_checkboxes.values():
            cb.setChecked(False)

    def _emit_unhide(self) -> None:
        sel = [p for p, cb in self._hidden_checkboxes.items() if cb.isChecked()]
        if sel:
            self.unhide_requested.emit(sel)

    # ── Branch ─────────────────────────────────────────────────────────────

    def _on_base_branch_changed(self) -> None:
        self.branch_fields_changed.emit()

    def _on_checkout_requested(self, branch: str) -> None:
        if branch:
            self.checkout_requested.emit(branch)

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
