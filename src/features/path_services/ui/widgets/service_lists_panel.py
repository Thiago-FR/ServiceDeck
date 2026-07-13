import os

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.features.path_services.services.service_detector import detect_default_start_command


class ServiceListsPanel(QWidget):
    stop_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._base_path = ""
        self._start_commands: dict[str, str] = {}
        self._code_commands: dict[str, str] = {}

        self._build_ui()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def set_base_path(self, path: str) -> None:
        self._base_path = path

    def populate(self, services: list[str]) -> None:
        self._start_list.clear()
        self._available_list.clear()
        self._code_list.clear()
        self._available_list.addItems(services)

    def set_running(self, running: set[str]) -> None:
        default_color = self._start_list.palette().color(QPalette.ColorRole.Text)
        for i in range(self._start_list.count()):
            item = self._start_list.item(i)
            color = QColor("#4CAF50") if item.text() in running else default_color
            item.setForeground(color)

    def get_start_services(self) -> set[str]:
        return {self._start_list.item(i).text() for i in range(self._start_list.count())}

    def get_code_services(self) -> set[str]:
        return {self._code_list.item(i).text() for i in range(self._code_list.count())}

    def get_start_commands(self) -> dict[str, str]:
        return dict(self._start_commands)

    def get_code_commands(self) -> dict[str, str]:
        return dict(self._code_commands)

    def load_commands(
        self,
        start_commands: dict[str, str],
        code_commands: dict[str, str],
    ) -> None:
        self._start_commands = start_commands
        self._code_commands = code_commands

    def is_stop_enabled(self) -> bool:
        return self._stop_button.isEnabled()

    def selected_start_service(self) -> str | None:
        selected = self._start_list.selectedItems()
        return selected[0].text() if selected else None

    def update_stop_button(self, running: set[str]) -> None:
        selected = self._start_list.selectedItems()
        enabled = bool(selected and selected[0].text() in running)
        self._stop_button.setEnabled(enabled)

    # -------------------------------------------------------------------------
    # UI construction
    # -------------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)

        self._start_list = QListWidget()
        self._start_list.itemDoubleClicked.connect(self._edit_start_command)
        self._start_list.itemSelectionChanged.connect(
            lambda: self.stop_requested.emit("")
        )

        self._stop_button = QPushButton("■ Parar Selecionado")
        self._stop_button.setEnabled(False)
        self._stop_button.clicked.connect(self._on_stop_clicked)

        start_col = QVBoxLayout()
        start_col.addWidget(QLabel("🚀 Serviços para Iniciar (duplo-clique p/ editar)"))
        start_col.addWidget(self._start_list)
        start_col.addWidget(self._stop_button)

        self._available_list = QListWidget()
        center_col = QVBoxLayout()
        center_col.addWidget(QLabel("📦 Serviços Disponíveis"))
        center_col.addWidget(self._available_list)

        self._code_list = QListWidget()
        self._code_list.itemDoubleClicked.connect(self._edit_code_command)
        code_col = QVBoxLayout()
        code_col.addWidget(QLabel("💻 Abrir Com (duplo-clique p/ editar)"))
        code_col.addWidget(self._code_list)

        layout.addLayout(start_col)
        layout.addLayout(self._build_arrow_buttons(self._move_to_start, self._move_from_start))
        layout.addLayout(center_col)
        layout.addLayout(self._build_arrow_buttons(self._move_to_code, self._move_from_code))
        layout.addLayout(code_col)

    def _build_arrow_buttons(self, on_left, on_right) -> QVBoxLayout:
        btn_left = QPushButton("<")
        btn_right = QPushButton(">")
        btn_left.clicked.connect(on_left)
        btn_right.clicked.connect(on_right)

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(btn_left)
        layout.addWidget(btn_right)
        layout.addStretch()
        return layout

    # -------------------------------------------------------------------------
    # Item movement
    # -------------------------------------------------------------------------

    def _move_to_start(self) -> None:
        for item in self._available_list.selectedItems():
            command = self._resolve_start_command(item.text())
            if command is None:
                continue
            self._available_list.takeItem(self._available_list.row(item))
            self._add_to_list(self._start_list, item.text(), command)

    def _move_from_start(self) -> None:
        self._move_back(self._start_list)

    def _move_to_code(self) -> None:
        for item in self._available_list.selectedItems():
            command = self._resolve_code_command(item.text())
            if command is None:
                continue
            self._available_list.takeItem(self._available_list.row(item))
            self._add_to_list(self._code_list, item.text(), command)

    def _move_from_code(self) -> None:
        self._move_back(self._code_list)

    def _move_back(self, source: QListWidget) -> None:
        for item in source.selectedItems():
            source.takeItem(source.row(item))
            self._available_list.addItem(item.text())
        self._available_list.sortItems()

    def _add_to_list(self, target: QListWidget, name: str, command: str) -> None:
        list_item = QListWidgetItem(name)
        list_item.setToolTip(command)
        target.addItem(list_item)
        target.sortItems()

    # -------------------------------------------------------------------------
    # Command resolution
    # -------------------------------------------------------------------------

    def _resolve_start_command(self, service_name: str) -> str | None:
        if service_name in self._start_commands:
            return self._start_commands[service_name]

        default = detect_default_start_command(os.path.join(self._base_path, service_name))
        command, ok = QInputDialog.getText(
            self, "Novo Serviço",
            f"Defina o comando para '{service_name}':",
            QLineEdit.EchoMode.Normal, default,
        )
        if not ok or not command:
            return None
        self._start_commands[service_name] = command
        return command

    def _resolve_code_command(self, service_name: str) -> str | None:
        if service_name in self._code_commands:
            return self._code_commands[service_name]

        command, ok = QInputDialog.getText(
            self, "Novo Comando 'Abrir Com'",
            f"Comando para '{service_name}':",
            QLineEdit.EchoMode.Normal, "code .",
        )
        if not ok or not command:
            return None
        self._code_commands[service_name] = command
        return command

    # -------------------------------------------------------------------------
    # Command editing
    # -------------------------------------------------------------------------

    def _edit_start_command(self, item: QListWidgetItem) -> None:
        self._edit_command(item, self._start_commands, "Editar Comando de Início")

    def _edit_code_command(self, item: QListWidgetItem) -> None:
        self._edit_command(item, self._code_commands, "Editar Comando 'Abrir Com'")

    def _edit_command(
        self, item: QListWidgetItem, commands: dict[str, str], title: str
    ) -> None:
        service_name = item.text()
        new_command, ok = QInputDialog.getText(
            self, title,
            f"Comando para '{service_name}':",
            QLineEdit.EchoMode.Normal,
            commands.get(service_name, ""),
        )
        if not ok or new_command is None:
            return
        commands[service_name] = new_command
        item.setToolTip(new_command)

    # -------------------------------------------------------------------------
    # Stop button
    # -------------------------------------------------------------------------

    def _on_stop_clicked(self) -> None:
        name = self.selected_start_service()
        if name:
            self.stop_requested.emit(name)
