import os

from PyQt6.QtWidgets import QMessageBox, QPushButton, QVBoxLayout, QWidget

from src.core.cache import CacheService
from src.core.config import CACHE_FILE
from src.features.path_services.services.process_monitor import ProcessMonitorThread
from src.features.path_services.services.service_detector import get_microservices
from src.features.path_services.services.service_killer import kill_all_services, kill_service
from src.features.path_services.services.service_launcher import (
    open_in_new_terminal,
    open_with_command,
)
from src.features.path_services.ui.widgets.folder_picker import FolderPickerWidget
from src.features.path_services.ui.widgets.service_lists_panel import ServiceListsPanel
from src.ui.log_widget import LogWidget


class PathServicesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._base_path = ""
        self._running_services: set[str] = set()
        self._cache = CacheService(CACHE_FILE)

        self._folder_picker = FolderPickerWidget()
        self._lists_panel = ServiceListsPanel()
        self._log = LogWidget()
        self._start_button = QPushButton("✅ Iniciar/Sincronizar Tarefas")

        self._monitor = ProcessMonitorThread()

        self._connect_signals()
        self._build_layout()
        self._load_cache()
        self._monitor.start()

    # -------------------------------------------------------------------------
    # Layout & wiring
    # -------------------------------------------------------------------------

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(self._folder_picker)
        layout.addWidget(self._lists_panel)
        layout.addWidget(self._log)
        layout.addWidget(self._start_button)

    def _connect_signals(self) -> None:
        self._folder_picker.folder_changed.connect(self._on_folder_changed)
        self._lists_panel.stop_requested.connect(self._on_stop_requested)
        self._monitor.status_update.connect(self._on_status_update)
        self._start_button.clicked.connect(self._start_tasks)

    # -------------------------------------------------------------------------
    # Signal handlers
    # -------------------------------------------------------------------------

    def _on_folder_changed(self, path: str) -> None:
        self._base_path = path
        self._lists_panel.set_base_path(path)
        self._monitor.set_config(path, set())
        self._populate_services()
        self._save_cache()

    def _on_stop_requested(self, service_name: str) -> None:
        if not service_name:
            self._lists_panel.update_stop_button(self._running_services)
            return
        success, message = kill_service(service_name, self._base_path)
        self._log.append(message)

    def _on_status_update(self, running_now: set[str]) -> None:
        for service in self._running_services - running_now:
            self._log.append(f"🔴 SERVIÇO ENCERRADO: '{service}' não está mais em execução.")
        self._running_services = running_now
        self._lists_panel.set_running(running_now)
        self._lists_panel.update_stop_button(running_now)

    # -------------------------------------------------------------------------
    # Service orchestration
    # -------------------------------------------------------------------------

    def _populate_services(self) -> None:
        services, error = get_microservices(self._base_path)
        if error:
            QMessageBox.critical(self, "Erro", error)
            return
        self._lists_panel.populate(services or [])

    def _start_tasks(self) -> None:
        services_to_run = self._lists_panel.get_start_services()
        code_tasks = self._lists_panel.get_code_services()

        if not services_to_run and not code_tasks:
            self._log.append("ℹ️ Nenhuma tarefa selecionada para iniciar.")
            return

        self._monitor.set_config(self._base_path, services_to_run)
        self._log.append("---------------- SINCRONIZANDO ----------------")

        self._launch_pending_services(services_to_run)
        self._open_code_tasks(code_tasks)

    def _launch_pending_services(self, services_to_run: set[str]) -> None:
        start_commands = self._lists_panel.get_start_commands()
        for service in self._running_services & services_to_run:
            self._log.append(f"🔵 STATUS: '{service}' já está em execução.")

        for service in services_to_run - self._running_services:
            command = start_commands.get(service)
            if not command:
                self._log.append(f"❌ FALHA: Comando não encontrado para '{service}'.")
                continue
            self._log.append(f"▶️ INICIANDO: '{service}'...")
            open_in_new_terminal(command, os.path.join(self._base_path, service))
            self._log.append(
                f"🟢 LANÇADO: '{service}'. O monitor confirmará o status em breve."
            )
            self._running_services.add(service)
            self._lists_panel.set_running(self._running_services)

    def _open_code_tasks(self, code_tasks: set[str]) -> None:
        code_commands = self._lists_panel.get_code_commands()
        for service in code_tasks:
            command = code_commands.get(service)
            if not command:
                self._log.append(
                    f"❌ FALHA: Comando não encontrado para '{service}' na lista da direita."
                )
                continue
            self._log.append(f"💻 Abrindo '{service}' com o comando '{command}'...")
            try:
                open_with_command(command, os.path.join(self._base_path, service))
            except Exception as e:
                self._log.append(f"❌ Erro ao abrir '{service}': {e}")

    # -------------------------------------------------------------------------
    # Cache
    # -------------------------------------------------------------------------

    def _save_cache(self) -> None:
        self._cache.save({
            "last_base_path": self._base_path,
            "saved_start_commands": self._lists_panel.get_start_commands(),
            "saved_code_commands": self._lists_panel.get_code_commands(),
        })

    def _load_cache(self) -> None:
        data = self._cache.load()
        base_path = data.get("last_base_path", "")
        start_commands = data.get("saved_start_commands", {})
        code_commands = data.get("saved_code_commands", {})

        self._lists_panel.load_commands(start_commands, code_commands)

        if not base_path or not os.path.exists(base_path):
            return

        self._base_path = base_path
        self._folder_picker.set_path(base_path)
        self._lists_panel.set_base_path(base_path)
        self._monitor.set_config(base_path, set())
        self._populate_services()

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    def cleanup(self) -> None:
        self._log.append("Encerrando aplicação e todos os serviços iniciados...")
        self._monitor.stop()
        self._monitor.wait()

        services = self._lists_panel.get_start_services()
        if services and self._base_path:
            self._log.append(f"Tentando finalizar {len(services)} serviço(s)...")
            for message in kill_all_services(services, self._base_path):
                self._log.append(message)

        self._save_cache()
