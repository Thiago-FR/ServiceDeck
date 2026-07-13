from PyQt6.QtCore import QDateTime
from PyQt6.QtWidgets import QTextEdit, QVBoxLayout, QLabel, QWidget


class LogWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("📋 Logs / Status dos Serviços"))
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(
            "background-color: #2b2b2b; color: #f0f0f0; font-family: Monospace;"
        )
        layout.addWidget(self._output)

    def append(self, message: str) -> None:
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self._output.append(f"[{timestamp}] {message}")
