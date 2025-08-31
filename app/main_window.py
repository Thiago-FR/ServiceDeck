# app/main_window.py

import os
import json
import subprocess
import psutil
from PyQt6.QtWidgets import (
  QWidget,
  QVBoxLayout,
  QHBoxLayout,
  QPushButton,
  QFileDialog,
  QListWidget,
  QLabel,
  QLineEdit,
  QMessageBox,
  QInputDialog,
  QListWidgetItem,
  QTextEdit,
)
from PyQt6.QtCore import QDateTime
from PyQt6.QtGui import QIcon

# Importações de outros módulos do nosso projeto
from .config import CACHE_FILE, APP_NAME
from .monitor import ProcessMonitorThread
from .utils import get_microservices, open_in_new_terminal, resource_path

# Define o caminho base para os assets
# Este caminho é relativo ao diretório onde o main_window.py está localizado
ASSETS_PATH = resource_path('app/assets')


class ServiceDeckApp(QWidget):
    def __init__(self):
        super().__init__()
        self.base_path = ""
        self.start_commands = {}
        self.code_commands = {}
        self.running_services = set()

        self.init_ui()
        self.monitor_thread = ProcessMonitorThread()
        self.monitor_thread.status_update.connect(self.on_status_update)
        self.load_cache()
        self.monitor_thread.start()

    def init_ui(self):
        self.setWindowTitle(f'{APP_NAME}')
        self.setGeometry(200, 200, 800, 700)

        main_layout = QVBoxLayout()

        # --- CORREÇÃO: Criação do log movida para o início ---
        # 1. Cria o widget de log
        log_layout = QVBoxLayout()
        log_layout.addWidget(QLabel("📋 Logs / Status dos Serviços"))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet(
            "background-color: #2b2b2b; color: #f0f0f0; "
            "font-family: Monospace;"
        )
        log_layout.addWidget(self.log_output)
        # --- FIM DA CRIAÇÃO ADIANTADA ---

        window_icon_path = os.path.join(ASSETS_PATH, 'icon.png')
        if os.path.exists(window_icon_path):
            self.setWindowIcon(QIcon(window_icon_path))
        else:
            self.log(
                f"Aviso: Ícone 'icon.png' não encontrado em "
                f"{ASSETS_PATH}"
            )

        path_layout = QHBoxLayout()
        self.path_label = QLabel('Pasta dos Projetos:')
        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        self.browse_button = QPushButton('Procurar...')
        self.browse_button.clicked.connect(self.select_folder)
        path_layout.addWidget(self.path_label)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_button)
        main_layout.addLayout(path_layout)

        lists_layout = QHBoxLayout()
        start_layout = QVBoxLayout()
        start_layout.addWidget(QLabel(
            "🚀 Serviços para Iniciar "
            "(duplo-clique p/ editar)"
        ))
        self.start_list = QListWidget()
        self.start_list.itemDoubleClicked.connect(self.edit_start_command)
        start_layout.addWidget(self.start_list)

        center_layout = QVBoxLayout()
        center_layout.addWidget(QLabel("📦 Serviços Disponíveis"))
        self.available_list = QListWidget()
        center_layout.addWidget(self.available_list)

        code_layout = QVBoxLayout()
        code_layout.addWidget(QLabel("💻 Abrir Com (duplo-clique p/ editar)"))
        self.code_list = QListWidget()
        self.code_list.itemDoubleClicked.connect(self.edit_code_command)
        code_layout.addWidget(self.code_list)

        self.btn_to_start = QPushButton('<')
        self.btn_from_start = QPushButton('>')
        self.btn_to_code = QPushButton('>')
        self.btn_from_code = QPushButton('<')

        self.btn_to_start.clicked.connect(self.move_to_start_list)
        self.btn_from_start.clicked.connect(self.move_from_start_list)
        self.btn_to_code.clicked.connect(self.move_to_code_list)
        self.btn_from_code.clicked.connect(self.move_from_code_list)

        start_buttons_layout = QVBoxLayout()
        start_buttons_layout.addStretch()
        start_buttons_layout.addWidget(self.btn_to_start)
        start_buttons_layout.addWidget(self.btn_from_start)
        start_buttons_layout.addStretch()

        code_buttons_layout = QVBoxLayout()
        code_buttons_layout.addStretch()
        code_buttons_layout.addWidget(self.btn_to_code)
        code_buttons_layout.addWidget(self.btn_from_code)
        code_buttons_layout.addStretch()

        lists_layout.addLayout(start_layout)
        lists_layout.addLayout(start_buttons_layout)
        lists_layout.addLayout(center_layout)
        lists_layout.addLayout(code_buttons_layout)
        lists_layout.addLayout(code_layout)
        main_layout.addLayout(lists_layout)

        main_layout.addLayout(log_layout)

        self.start_button = QPushButton("✅ Iniciar/Sincronizar Tarefas")
        self.start_button.clicked.connect(self.start_tasks)
        main_layout.addWidget(self.start_button)
        self.setLayout(main_layout)

    def log(self, message):
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.log_output.append(f"[{timestamp}] {message}")

    def on_status_update(self, running_services_now):
        services_that_stopped = self.running_services - running_services_now
        for service in services_that_stopped:
            self.log(
              f"🔴 SERVIÇO ENCERRADO: '{service}' não está mais em execução."
            )
        self.running_services = running_services_now

    def start_tasks(self):
        services_to_run = {
            self.start_list.item(i).text()
            for i in range(self.start_list.count())
        }
        code_tasks_to_run = {
            self.code_list.item(i).text()
            for i in range(self.code_list.count())
        }

        if not services_to_run and not code_tasks_to_run:
            self.log("ℹ️ Nenhuma tarefa selecionada para iniciar.")
            return

        self.monitor_thread.set_config(self.base_path, services_to_run)
        self.log("---------------- SINCRONIZANDO ----------------")

        services_to_launch = services_to_run - self.running_services

        for service in self.running_services:
            if service in services_to_run:
                self.log(f"🔵 STATUS: '{service}' já está em execução.")

        for service in services_to_launch:
            self.log(f"▶️ INICIANDO: '{service}'...")
            command = self.start_commands.get(service)
            if command:
                open_in_new_terminal(
                    command,
                    os.path.join(self.base_path, service)
                )
                self.log(
                  f"🟢 LANÇADO: '{service}'. "
                  "O monitor confirmará o status em breve."
                )
                self.running_services.add(service)
            else:
                self.log(
                  f"❌ FALHA: Comando não encontrado para '{service}'."
                )

        for service in code_tasks_to_run:
            command = self.code_commands.get(service)
            if command:
                self.log(f"💻 Abrindo '{service}' com o comando '{command}'...")
                try:
                    subprocess.Popen(
                        command.split(),
                        cwd=os.path.join(self.base_path, service)
                    )
                except Exception as e:
                    self.log(f"❌ Erro ao abrir '{service}': {e}")
            else:
                self.log(
                  (
                    f"❌ FALHA: Comando não encontrado para '{service}' "
                    "na lista da direita."
                  )
                )

    def closeEvent(self, event):
        self.log("Encerrando aplicação e todos os serviços iniciados...")
        self.monitor_thread.stop()
        self.monitor_thread.wait()

        services_to_close = {
            self.start_list.item(i).text()
            for i in range(self.start_list.count())
        }

        if services_to_close and self.base_path:
            self.log(
                f"Tentando finalizar {len(services_to_close)} serviço(s)..."
            )
            # Normaliza os caminhos dos serviços que queremos fechar
            service_paths = {
              name: os.path.realpath(os.path.join(self.base_path, name))
              for name in services_to_close
            }

            terminated_pids = set()
            try:
                for proc in psutil.process_iter(['cwd', 'pid']):
                    if proc.pid in terminated_pids:
                        continue
                    try:
                        if proc.info['cwd']:
                            # Normaliza o CWD do processo atual para uma
                            # comparação confiável
                            proc_cwd = os.path.realpath(proc.info['cwd'])
                            for name, path in service_paths.items():
                                if proc_cwd == path:
                                    self.log(
                                      f"-> Encontrado processo correspondente "
                                      f"para '{name}' (PID: {proc.pid}). "
                                      "Finalizando..."
                                    )
                                    parent_process = psutil.Process(proc.pid)
                                    # Mata primeiro os processos filhos
                                    children = parent_process.children(
                                        recursive=True
                                    )
                                    for child in children:
                                        child.kill()
                                    # Depois mata o processo pai
                                    parent_process.kill()
                                    terminated_pids.add(proc.pid)
                                    self.log(
                                      f"-> Processo de '{name}' (e filhos) "
                                      "finalizado."
                                    )
                                    break
                    except (
                        psutil.NoSuchProcess,
                        psutil.AccessDenied,
                        FileNotFoundError
                    ):
                        # Adicionado FileNotFoundError
                        continue
            except Exception as e:
                self.log(
                  f"  -> Aviso durante o encerramento de processos: {e}"
                )

        self.save_cache()
        event.accept()

    def save_cache(self):
        cache_data = {
            'last_base_path': self.base_path,
            'saved_start_commands': self.start_commands,
            'saved_code_commands': self.code_commands
        }
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache_data, f, indent=4)
        except IOError as e:
            print(f"Erro ao salvar o cache: {e}")

    def load_cache(self):
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r') as f:
                    cache_data = json.load(f)
                    self.base_path = cache_data.get('last_base_path', '')
                    self.start_commands = cache_data.get(
                      'saved_start_commands', {}
                    )
                    self.code_commands = cache_data.get(
                      'saved_code_commands', {}
                    )
                    if self.base_path and os.path.exists(self.base_path):
                        self.path_input.setText(self.base_path)
                        self.monitor_thread.set_config(self.base_path, set())
                        self.populate_available_services()
        except (IOError, json.JSONDecodeError) as e:
            print(f"Cache não encontrado ou corrompido. Erro: {e}")

    def select_folder(self):
        start_path = (
            self.base_path
            if self.base_path and os.path.exists(self.base_path)
            else os.path.expanduser("~")
        )
        folder = QFileDialog.getExistingDirectory(
            self,
            "Selecione a pasta dos microserviços",
            start_path,
        )
        if folder:
            self.base_path = folder
            self.path_input.setText(folder)
            self.monitor_thread.set_config(self.base_path, set())
            self.populate_available_services()
            self.save_cache()

    def populate_available_services(self):
        self.start_list.clear()
        self.available_list.clear()
        self.code_list.clear()
        services, error = get_microservices(self.base_path)
        if error:
            QMessageBox.critical(self, "Erro", error)
            return
        if services:
            self.available_list.addItems(services)

    def move_to_start_list(self):
        selected_items = self.available_list.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            service_name = item.text()
            if service_name in self.start_commands:
                command = self.start_commands[service_name]
            else:
                service_path = os.path.join(self.base_path, service_name)
                if os.path.exists(os.path.join(service_path, 'package.json')):
                    default_command = 'yarn dev'
                elif os.path.exists(
                  os.path.join(service_path, 'requirements.txt')
                ):
                    default_command = (
                      'uvicorn src.main:app --host 0.0.0.0 --port 8000'
                    )
                else:
                    default_command = ''
                command, ok = QInputDialog.getText(
                  self,
                  "Novo Serviço",
                  f"Defina o comando para '{service_name}':",
                  QLineEdit.EchoMode.Normal,
                  default_command,
                )
                if not ok or not command:
                    continue
                self.start_commands[service_name] = command
                self.save_cache()

            self.available_list.takeItem(self.available_list.row(item))
            list_item = QListWidgetItem(service_name)
            list_item.setToolTip(command)
            self.start_list.addItem(list_item)
            self.start_list.sortItems()

    def move_from_start_list(self):
        self._move_item_back_to_center(self.start_list)

    def move_to_code_list(self):
        selected_items = self.available_list.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            service_name = item.text()
            if service_name in self.code_commands:
                command = self.code_commands[service_name]
            else:
                default_command = 'code .'
                command, ok = QInputDialog.getText(
                  self,
                  "Novo Comando 'Abrir Com'",
                  f"Comando para '{service_name}':",
                  QLineEdit.EchoMode.Normal,
                  default_command,
                )
                if not ok or not command:
                    continue
                self.code_commands[service_name] = command
                self.save_cache()

            self.available_list.takeItem(self.available_list.row(item))
            list_item = QListWidgetItem(service_name)
            list_item.setToolTip(command)
            self.code_list.addItem(list_item)
            self.code_list.sortItems()

    def move_from_code_list(self):
        self._move_item_back_to_center(self.code_list)

    def edit_start_command(self, item):
        self._edit_command(
            item,
            self.start_commands,
            "Editar Comando de Início"
        )

    def edit_code_command(self, item):
        self._edit_command(
            item,
            self.code_commands,
            "Editar Comando 'Abrir Com'"
        )

    def _edit_command(self, item, command_dict, title):
        service_name = item.text()
        current_command = command_dict.get(service_name, "")
        new_command, ok = QInputDialog.getText(
            self,
            title,
            f"Comando para '{service_name}':",
            QLineEdit.EchoMode.Normal,
            current_command,
        )
        if ok and new_command is not None:
            command_dict[service_name] = new_command
            item.setToolTip(new_command)
            self.save_cache()

    def _move_item_back_to_center(self, source_list):
        selected_items = source_list.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            source_list.takeItem(source_list.row(item))
            self.available_list.addItem(item.text())
        self.available_list.sortItems()
