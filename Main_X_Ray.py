import sys
from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("X_Ray_ui.ui", self)

app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())