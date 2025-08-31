# main.py

# Ponto de entrada principal para a aplicação ServiceDeck.
# Responsável por criar e executar a aplicação PyQt.

import sys
from PyQt6.QtWidgets import QApplication
from app.main_window import ServiceDeckApp


def main():
    """Inicia o loop de eventos da aplicação."""
    app = QApplication(sys.argv)
    ex = ServiceDeckApp()
    ex.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
