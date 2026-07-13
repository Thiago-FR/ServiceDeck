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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_checkboxes: dict[str, QCheckBox] = {}
        self._build_ui()
        self.setEnabled(False)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def load_repo(self, repo: RepoInfo) -> None:
        self.setEnabled(True)
        self._populate_files(repo)
        self._populate_branches(repo)

    def refresh_branches(self, repo: RepoInfo) -> None:
        self._populate_branches(repo)

    def get_selected_files(self) -> list[str]:
        return [path for path, cb in self._file_checkboxes.items() if cb.isChecked()]

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
        return self._new_branch_suffix.text().strip()

    def set_new_branch_suffix(self, text: str) -> None:
        self._new_branch_suffix.blockSignals(True)
        self._new_branch_suffix.setText(text)
        self._new_branch_suffix.blockSignals(False)
        # self._update_branch_preview()

    def get_new_branch_name(self) -> str:
        return self.get_new_branch_suffix()

    # -------------------------------------------------------------------------
    # UI construction
    # -------------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(self._build_files_group())
        layout.addWidget(self._build_commit_group())
        layout.addWidget(self._build_pr_group())
        layout.addWidget(self._build_branch_group())

    def _build_files_group(self) -> QGroupBox:
        group = QGroupBox("Arquivos Modificados")
        layout = QVBoxLayout(group)

        header = QHBoxLayout()
        select_all_btn = QPushButton("☑ Selecionar todos")
        select_all_btn.clicked.connect(self._select_all_files)
        deselect_btn = QPushButton("☐ Desmarcar todos")
        deselect_btn.clicked.connect(self._deselect_all_files)
        header.addWidget(select_all_btn)
        header.addWidget(deselect_btn)
        header.addStretch()
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(150)
        self._files_container = QWidget()
        self._files_layout = QVBoxLayout(self._files_container)
        self._files_layout.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(self._files_container)
        layout.addWidget(scroll)
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

    def _build_branch_group(self) -> QGroupBox:
        group = QGroupBox("Copiar branch")
        layout = QVBoxLayout(group)

        row1 = QHBoxLayout()
        self._current_branch_combo = QComboBox()
        self._current_branch_combo.setStyleSheet("font-weight: bold; color: #4CAF50;")
        self._current_branch_combo.setEnabled(False)
        self._current_branch_combo.setToolTip("Sem alterações locais: clique para trocar de branch")
        self._current_branch_combo.currentTextChanged.connect(self._on_checkout_requested)
        self._base_branch = QComboBox()
        self._base_branch.currentTextChanged.connect(self._on_base_branch_changed)
        row1.addWidget(QLabel("Branch atual:"))
        row1.addWidget(self._current_branch_combo, stretch=1)
        row1.addWidget(QLabel("Branch de destino:"))
        row1.addWidget(self._base_branch, stretch=1)

        row2 = QHBoxLayout()
        self._new_branch_suffix = QLineEdit()
        self._new_branch_suffix.setPlaceholderText("ex: tentativa1, feat/login")
        self._new_branch_suffix.textChanged.connect(self._on_suffix_changed)
        row2.addWidget(QLabel("Nova branch:"))
        row2.addWidget(self._new_branch_suffix, stretch=1)

        layout.addLayout(row1)
        layout.addLayout(row2)
        return group

    def _build_pr_group(self) -> QGroupBox:
        group = QGroupBox("Pull Request")
        layout = QVBoxLayout(group)

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
        self._pr_body.setMinimumHeight(100)

        layout.addLayout(title_row)
        layout.addLayout(body_header)
        layout.addWidget(self._pr_body)
        return group

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _populate_files(self, repo: RepoInfo) -> None:
        while self._files_layout.count():
            item = self._files_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._file_checkboxes.clear()

        for changed_file in repo.changed_files:
            label = f"[{changed_file.status}] {changed_file.path}"
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.stateChanged.connect(lambda _: self.files_selection_changed.emit())
            self._file_checkboxes[changed_file.path] = cb
            self._files_layout.addWidget(cb)

    def _populate_branches(self, repo: RepoInfo) -> None:
        # --- Branch atual (combo para trocar quando limpo) ---
        self._current_branch_combo.blockSignals(True)
        self._current_branch_combo.clear()
        for branch in repo.branches:
            self._current_branch_combo.addItem(branch)
        if repo.current_branch:
            idx = self._current_branch_combo.findText(repo.current_branch)
            if idx >= 0:
                self._current_branch_combo.setCurrentIndex(idx)
        can_switch = repo.status == RepoStatus.CLEAN
        self._current_branch_combo.setEnabled(can_switch)
        tip = (
            "Clique para trocar de branch"
            if can_switch
            else "Faça commit ou descarte as alterações para trocar de branch"
        )
        self._current_branch_combo.setToolTip(tip)
        self._current_branch_combo.blockSignals(False)

        # --- Branch de destino (exclui current) ---
        current_selection = self._base_branch.currentText()
        self._base_branch.blockSignals(True)
        self._base_branch.clear()
        for branch in repo.branches:
            if branch != repo.current_branch:
                self._base_branch.addItem(branch)
        if current_selection and self._base_branch.findText(current_selection) >= 0:
            self._base_branch.setCurrentText(current_selection)
        self._base_branch.blockSignals(False)

    def _select_all_files(self) -> None:
        for cb in self._file_checkboxes.values():
            cb.setChecked(True)

    def _deselect_all_files(self) -> None:
        for cb in self._file_checkboxes.values():
            cb.setChecked(False)

    def _on_base_branch_changed(self) -> None:
        self.branch_fields_changed.emit()

    def _on_suffix_changed(self) -> None:
        self.branch_fields_changed.emit()

    def _on_checkout_requested(self, branch: str) -> None:
        if branch:
            self.checkout_requested.emit(branch)
