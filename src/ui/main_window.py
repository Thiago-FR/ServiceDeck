import os

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMainWindow, QTabWidget

from src.core.config import APP_NAME
from src.core.resources import resource_path
from src.features.git_manager.ui.git_manager_tab import GitManagerTab
from src.features.path_services.ui.path_services_tab import PathServicesTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setGeometry(150, 80, 1100, 900)

        icon_path = os.path.join(resource_path("app/assets"), "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._services_tab = PathServicesTab()
        self._git_tab = GitManagerTab()

        self._services_tab.base_path_changed.connect(self._git_tab.set_base_path)

        # Passa o path já carregado do cache para o git tab
        if self._services_tab._base_path:
            self._git_tab.set_base_path(self._services_tab._base_path)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._services_tab, "Serviços")
        self._tabs.addTab(self._git_tab, "Git / GitHub")
        self.setCentralWidget(self._tabs)

    def closeEvent(self, event):
        self._services_tab.cleanup()
        event.accept()
