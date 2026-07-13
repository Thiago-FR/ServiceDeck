from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.features.git_manager.services.repo_scanner import RepoInfo, RepoStatus

_GROUPS = [
    (RepoStatus.CHANGES, "🔴  Modificados",  "#c0392b"),
    (RepoStatus.AHEAD,   "🟡  Pendentes de push", "#e67e22"),
    (RepoStatus.CLEAN,   "🟢  Sem alteração", "#27ae60"),
]


class RepoListWidget(QWidget):
    repo_selected = pyqtSignal(str)       # full_path do repo clicado
    selection_changed = pyqtSignal(list)  # lista de full_paths marcados com ☑

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checkboxes: dict[str, QCheckBox] = {}
        self._repo_buttons: dict[str, QPushButton] = {}
        self._selected_path: str = ""
        self._build_ui()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def load_repos(self, repos: list[RepoInfo]) -> None:
        self._checkboxes.clear()
        self._repo_buttons.clear()
        self._clear_layout(self._content_layout)

        by_status: dict[RepoStatus, list[RepoInfo]] = {s: [] for s, *_ in _GROUPS}
        for repo in repos:
            by_status[repo.status].append(repo)

        for status, label_text, color in _GROUPS:
            group = by_status[status]
            self._add_separator(label_text, color)
            if group:
                for repo in group:
                    self._add_repo_row(repo)
            else:
                self._add_empty_label()

        self._content_layout.addStretch()
        self.selection_changed.emit(self.get_checked_paths())

    def get_checked_paths(self) -> list[str]:
        return [path for path, cb in self._checkboxes.items() if cb.isChecked()]

    # -------------------------------------------------------------------------
    # UI construction
    # -------------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        check_all = QPushButton("☑ Todos")
        check_all.setFixedWidth(70)
        check_all.clicked.connect(self._check_all)
        uncheck_all = QPushButton("☐ Nenhum")
        uncheck_all.setFixedWidth(80)
        uncheck_all.clicked.connect(self._uncheck_all)
        header.addWidget(check_all)
        header.addWidget(uncheck_all)
        header.addStretch()
        outer.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(2)
        scroll.setWidget(self._content)
        outer.addWidget(scroll)

    def _add_separator(self, text: str, color: str) -> None:
        label = QLabel(text)
        label.setStyleSheet(
            f"color: {color}; font-weight: bold; padding: 4px 2px 2px 2px;"
            "border-bottom: 1px solid #555;"
        )
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._content_layout.addWidget(label)

    def _add_repo_row(self, repo: RepoInfo) -> None:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(4, 1, 4, 1)

        cb = QCheckBox()
        cb.setChecked(True)
        cb.stateChanged.connect(lambda _: self.selection_changed.emit(self.get_checked_paths()))
        self._checkboxes[repo.full_path] = cb

        detail = ""
        if repo.status == RepoStatus.CHANGES:
            detail = f"  ({len(repo.changed_files)} arquivo(s))"
        elif repo.status == RepoStatus.AHEAD:
            detail = f"  ({repo.commits_ahead} commit(s) não publicado(s))"

        name_btn = QPushButton(f"{repo.name}{detail}")
        name_btn.setFlat(True)
        name_btn.setStyleSheet("text-align: left; padding: 2px 4px;")
        name_btn.clicked.connect(lambda _, p=repo.full_path: self._on_repo_clicked(p))
        self._repo_buttons[repo.full_path] = name_btn

        layout.addWidget(cb)
        layout.addWidget(name_btn, stretch=1)
        self._content_layout.addWidget(row)

    def _add_empty_label(self) -> None:
        label = QLabel("  Nenhum")
        label.setStyleSheet("color: #888; padding: 2px 8px; font-style: italic;")
        self._content_layout.addWidget(label)

    # -------------------------------------------------------------------------
    # Select / deselect all
    # -------------------------------------------------------------------------

    def _on_repo_clicked(self, path: str) -> None:
        self._selected_path = path
        for p, btn in self._repo_buttons.items():
            if p == path:
                btn.setStyleSheet(
                    "text-align: left; padding: 2px 4px; "
                    "background-color: #2a5298; color: white; font-weight: bold;"
                )
            else:
                btn.setStyleSheet("text-align: left; padding: 2px 4px;")
        self.repo_selected.emit(path)

    def _check_all(self) -> None:
        for cb in self._checkboxes.values():
            cb.setChecked(True)

    def _uncheck_all(self) -> None:
        for cb in self._checkboxes.values():
            cb.setChecked(False)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
