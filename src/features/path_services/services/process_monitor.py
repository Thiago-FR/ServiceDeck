import os
import threading
import psutil
from PyQt6.QtCore import QThread, pyqtSignal


class ProcessMonitorThread(QThread):
    status_update = pyqtSignal(set)

    def __init__(self):
        super().__init__()
        self._running = True
        self._base_path = ""
        self._services_to_monitor = set()
        self._stop_event = threading.Event()

    def set_config(self, base_path: str, services_set: set) -> None:
        self._base_path = base_path
        self._services_to_monitor = services_set

    def run(self) -> None:
        while self._running:
            if not self._services_to_monitor or not self._base_path:
                self._stop_event.wait(3)
                continue

            currently_running = set()
            service_paths = {
                name: os.path.join(self._base_path, name)
                for name in self._services_to_monitor
            }

            for proc in psutil.process_iter(['cwd']):
                try:
                    if proc.info['cwd']:
                        for name, path in service_paths.items():
                            if os.path.samefile(proc.info['cwd'], path):
                                currently_running.add(name)
                                break
                except (psutil.NoSuchProcess, psutil.AccessDenied, FileNotFoundError):
                    continue

            self.status_update.emit(currently_running)
            self._stop_event.wait(3)

    def stop(self) -> None:
        self._running = False
        self._stop_event.set()
