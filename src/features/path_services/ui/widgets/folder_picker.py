import os

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget


class FolderPickerWidget(QWidget):
    folder_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_path = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._input = QLineEdit()
        self._input.setReadOnly(True)

        browse = QPushButton("Procurar...")
        browse.clicked.connect(self._on_browse)

        layout.addWidget(QLabel("Pasta dos Projetos:"))
        layout.addWidget(self._input)
        layout.addWidget(browse)

    def set_path(self, path: str) -> None:
        self._current_path = path
        self._input.setText(path)

    def _on_browse(self) -> None:
        start = (
            self._current_path
            if self._current_path and os.path.exists(self._current_path)
            else os.path.expanduser("~")
        )
        folder = QFileDialog.getExistingDirectory(
            self, "Selecione a pasta dos microserviços", start
        )
        if not folder:
            return
        self._current_path = folder
        self._input.setText(folder)
        self.folder_changed.emit(folder)
