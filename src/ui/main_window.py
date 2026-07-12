import os

from PyQt6.QtWidgets import QMainWindow, QTabWidget
from PyQt6.QtGui import QIcon

from src.core.config import APP_NAME
from src.core.resources import resource_path
from src.features.path_services.ui.path_services_tab import PathServicesTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setGeometry(200, 200, 800, 700)

        icon_path = os.path.join(resource_path('app/assets'), 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._tabs = QTabWidget()
        self._path_services_tab = PathServicesTab()
        self._tabs.addTab(self._path_services_tab, "Serviços")
        self.setCentralWidget(self._tabs)

    def closeEvent(self, event):
        self._path_services_tab.cleanup()
        event.accept()
