from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.features.git_manager.services.git_operations import (
    CommitInfo,
    get_commit_diff,
    get_unpushed_commits,
    reset_branch,
    revert_commit,
)


class UnpushedCommitsDialog(QDialog):
    def __init__(self, repo_path: str, repo_name: str, branch: str, parent=None):
        super().__init__(parent)
        self._repo_path = repo_path
        self._commits: list[CommitInfo] = []
        self._selected_commit: CommitInfo | None = None

        self.setWindowTitle(f"Commits não publicados — {repo_name}  ({branch})")
        self.resize(960, 620)
        self._build_ui()
        self._load_commits()

    # -------------------------------------------------------------------------
    # UI
    # -------------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Esquerda: lista de commits
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("Commits não publicados:"))
        self._commit_list = QListWidget()
        self._commit_list.currentRowChanged.connect(self._on_commit_selected)
        left_layout.addWidget(self._commit_list)

        # Direita: arquivos + diff
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_splitter = QSplitter(Qt.Orientation.Vertical)

        files_widget = QWidget()
        files_layout = QVBoxLayout(files_widget)
        files_layout.setContentsMargins(0, 0, 0, 0)
        files_layout.addWidget(QLabel("Arquivos deste commit:"))
        self._files_list = QListWidget()
        self._files_list.setMaximumHeight(130)
        files_layout.addWidget(self._files_list)

        diff_widget = QWidget()
        diff_layout = QVBoxLayout(diff_widget)
        diff_layout.setContentsMargins(0, 0, 0, 0)
        diff_layout.addWidget(QLabel("Diferenças (linhas verdes = adicionado, vermelhas = removido):"))
        self._diff_view = QTextEdit()
        self._diff_view.setReadOnly(True)
        font = QFont("Courier New", 9)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._diff_view.setFont(font)
        self._diff_view.setStyleSheet(
            "QTextEdit { background-color: #1e1e1e; color: #d4d4d4;"
            " border: 1px solid #444; }"
        )
        diff_layout.addWidget(self._diff_view)

        right_splitter.addWidget(files_widget)
        right_splitter.addWidget(diff_widget)
        right_splitter.setStretchFactor(0, 1)
        right_splitter.setStretchFactor(1, 4)
        right_layout.addWidget(right_splitter)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter, stretch=1)
        layout.addLayout(self._build_actions())

    def _build_actions(self) -> QHBoxLayout:
        row = QHBoxLayout()

        soft_btn = QPushButton("↩ Desfazer (Soft)")
        soft_btn.setToolTip("Desfaz os commits mas mantém os arquivos prontos para commitar de novo.")
        soft_btn.clicked.connect(lambda: self._reset("soft"))
        row.addWidget(soft_btn)
        row.addWidget(self._info_label(
            "Desfaz os commits mas mantém os arquivos já selecionados (staged).\n"
            'Use quando quiser refazer o commit com outra mensagem ou conteúdo.'
        ))
        row.addSpacing(6)

        mixed_btn = QPushButton("↩ Desfazer (Revisão)")
        mixed_btn.setToolTip("Desfaz os commits e deixa os arquivos modificados mas não selecionados.")
        mixed_btn.clicked.connect(lambda: self._reset("mixed"))
        row.addWidget(mixed_btn)
        row.addWidget(self._info_label(
            "Desfaz os commits e deixa os arquivos modificados mas não selecionados.\n"
            'Use quando quiser revisar quais arquivos entrarão no próximo commit.'
        ))
        row.addSpacing(6)

        hard_btn = QPushButton("🗑 Descartar tudo")
        hard_btn.setStyleSheet("QPushButton { color: #c0392b; font-weight: bold; }")
        hard_btn.setToolTip("IRREVERSÍVEL: desfaz os commits E descarta as alterações nos arquivos.")
        hard_btn.clicked.connect(lambda: self._reset("hard"))
        row.addWidget(hard_btn)
        row.addWidget(self._info_label(
            "⚠️ IRREVERSÍVEL — desfaz os commits E descarta todas as alterações nos arquivos.\n"
            "Use apenas se tiver certeza de que não precisa mais dessas mudanças."
        ))
        row.addSpacing(6)

        self._revert_btn = QPushButton("↩ Reverter commit")
        self._revert_btn.setEnabled(False)
        self._revert_btn.setToolTip("Cria um novo commit que faz o oposto do commit selecionado.")
        self._revert_btn.clicked.connect(self._revert_selected)
        row.addWidget(self._revert_btn)
        row.addWidget(self._info_label(
            "Cria um novo commit que desfaz as mudanças do commit selecionado.\n"
            "O histórico fica intacto — nada é apagado, só é adicionado o oposto.\n"
            "Selecione um commit na lista antes de usar."
        ))

        row.addStretch()

        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(self.accept)
        row.addWidget(close_btn)

        return row

    @staticmethod
    def _info_label(tooltip: str) -> QLabel:
        lbl = QLabel("ℹ")
        lbl.setToolTip(tooltip)
        lbl.setStyleSheet(
            "QLabel { color: #5b9bd5; font-weight: bold; padding: 0 2px; }"
        )
        lbl.setCursor(Qt.CursorShape.WhatsThisCursor)
        return lbl

    # -------------------------------------------------------------------------
    # Data loading
    # -------------------------------------------------------------------------

    def _load_commits(self) -> None:
        self._commits = get_unpushed_commits(self._repo_path)
        self._commit_list.clear()
        for c in self._commits:
            self._commit_list.addItem(f"{c.short_hash}  {c.date}  {c.message}")
        if self._commits:
            self._commit_list.setCurrentRow(0)
        else:
            self._diff_view.setPlainText("Nenhum commit não publicado encontrado.")

    def _on_commit_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._commits):
            self._revert_btn.setEnabled(False)
            return
        commit = self._commits[row]
        self._selected_commit = commit
        self._revert_btn.setEnabled(True)

        self._files_list.clear()
        for f in commit.files:
            self._files_list.addItem(f)

        diff = get_commit_diff(self._repo_path, commit.hash)
        self._render_diff(diff)

    def _render_diff(self, diff_text: str) -> None:
        self._diff_view.clear()
        cursor = self._diff_view.textCursor()

        fmt_normal = QTextCharFormat()
        fmt_normal.setBackground(QColor("#1e1e1e"))
        fmt_normal.setForeground(QColor("#d4d4d4"))

        fmt_add = QTextCharFormat()
        fmt_add.setBackground(QColor("#1a3a1a"))
        fmt_add.setForeground(QColor("#73c991"))

        fmt_remove = QTextCharFormat()
        fmt_remove.setBackground(QColor("#3a1a1a"))
        fmt_remove.setForeground(QColor("#f14c4c"))

        fmt_header = QTextCharFormat()
        fmt_header.setBackground(QColor("#1e1e1e"))
        fmt_header.setForeground(QColor("#569cd6"))

        for line in diff_text.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                cursor.setCharFormat(fmt_add)
            elif line.startswith("-") and not line.startswith("---"):
                cursor.setCharFormat(fmt_remove)
            elif line.startswith("@@") or line.startswith("diff ") or line.startswith("index "):
                cursor.setCharFormat(fmt_header)
            else:
                cursor.setCharFormat(fmt_normal)
            cursor.insertText(line + "\n")

        self._diff_view.setTextCursor(cursor)
        self._diff_view.moveCursor(QTextCursor.MoveOperation.Start)

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def _reset(self, mode: str) -> None:
        labels = {
            "soft": "Desfazer (Soft) — arquivos ficam prontos para commitar novamente",
            "mixed": "Desfazer (Revisão) — arquivos ficam modificados mas não selecionados",
            "hard": "Descartar tudo — IRREVERSÍVEL, todas as alterações serão perdidas",
        }
        text = (
            f"Confirma: {labels[mode]}?\n\n"
            f"Isso afetará todos os {len(self._commits)} commit(s) não publicados."
        )

        if mode == "hard":
            answer = QMessageBox.warning(
                self,
                "⚠️ Ação irreversível",
                f"ATENÇÃO!\n\n{text}\n\nEssa ação não pode ser desfeita.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
        else:
            answer = QMessageBox.question(
                self,
                "Confirmar",
                text,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )

        if answer != QMessageBox.StandardButton.Yes:
            return

        result = reset_branch(self._repo_path, mode)
        QMessageBox.information(self, "Resultado", result.message)
        if result.success:
            self.accept()

    def _revert_selected(self) -> None:
        if not self._selected_commit:
            return
        c = self._selected_commit
        answer = QMessageBox.question(
            self,
            "Reverter commit",
            f"Reverter o commit:\n\n{c.short_hash}  {c.message}\n\n"
            "Isso cria um novo commit que faz o oposto. O histórico original fica preservado.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        result = revert_commit(self._repo_path, c.hash)
        QMessageBox.information(self, "Resultado", result.message)
        if result.success:
            self._load_commits()
