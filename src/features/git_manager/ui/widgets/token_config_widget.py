from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from src.features.git_manager.services.github_provider import GitHubProvider
from src.features.git_manager.services.token_store import TokenStore


class TokenConfigWidget(QWidget):
    token_validated = pyqtSignal(str, str)  # provider, token

    def __init__(self, parent=None):
        super().__init__(parent)
        self._store = TokenStore()
        self._provider = GitHubProvider()
        self._build_ui()
        self._load_saved_token()

    def get_token(self, provider: str = "github") -> str:
        return self._store.load(provider)

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._status_label = QLabel("⚪ Token não configurado")
        self._token_input = QLineEdit()
        self._token_input.setPlaceholderText("GitHub Personal Access Token")
        self._token_input.setEchoMode(QLineEdit.EchoMode.Password)

        validate_btn = QPushButton("Validar")
        validate_btn.clicked.connect(self._on_validate)

        clear_btn = QPushButton("Limpar")
        clear_btn.clicked.connect(self._on_clear)

        layout.addWidget(QLabel("🔑 Token GitHub:"))
        layout.addWidget(self._token_input, stretch=1)
        layout.addWidget(validate_btn)
        layout.addWidget(clear_btn)
        layout.addWidget(self._status_label)

    def _on_validate(self) -> None:
        token = self._token_input.text().strip()
        if not token:
            self._status_label.setText("⚠️ Digite um token")
            return

        self._status_label.setText("⏳ Validando...")
        if self._provider.validate_token(token):
            self._store.save("github", token)
            self._status_label.setText("✅ Token válido")
            self.token_validated.emit("github", token)
        else:
            self._status_label.setText("❌ Token inválido")

    def _on_clear(self) -> None:
        self._token_input.clear()
        self._store.clear("github")
        self._status_label.setText("⚪ Token não configurado")

    def _load_saved_token(self) -> None:
        token = self._store.load("github")
        if not token:
            return
        self._token_input.setText(token)
        self._status_label.setText("✅ Token salvo")
