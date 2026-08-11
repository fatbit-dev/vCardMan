import sys
import os

# Ensure src/ is on the path so the vcardman package is importable regardless
# of the working directory the script is launched from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from PyQt5.QtWidgets import QApplication

from vcardman.ui.main_window import MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
