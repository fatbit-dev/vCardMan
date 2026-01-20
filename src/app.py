from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLineEdit, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QMessageBox
from PyQt5.QtCore import pyqtSlot
import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("vCard Manager")
        self.setGeometry(100, 100, 400, 200)
        self.init_ui()

    def init_ui(self):
        outer_layout = QHBoxLayout()
        left_pane = QWidget()
        right_pane = QWidget()
        # Create central widget and layout
        # central_widget = QWidget()
        # self.setCentralWidget(central_widget)
        # layout = QVBoxLayout(central_widget)
        self.setCentralWidget(outer_layout)

        # Add label and input field
        self.label = QLabel("Enter your name:")
        self.input_field = QLineEdit()
        # layout.addWidget(self.input_field)
        # layout.addWidget(self.label)
        left_pane.addWidget(self.label)
        left_pane.addWidget(self.input_field)

        # Add button
        self.button = QPushButton("Greet Me")
        self.button.clicked.connect(self.on_button_click)
        # layout.addWidget(self.button)
        right_pane.addWidget(self.button)

    @pyqtSlot()
    def on_button_click(self):
        name = self.input_field.text().strip()
        if name:
            QMessageBox.information(self, "Greeting", f"Hello, {name}!")
        else:
            QMessageBox.warning(self, "Warning", "Please enter a name.")

# Main execution
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


# import sys
# from PyQt5.QtWidgets import QApplication, QWidget

# app = QApplication(sys.argv)
# window = QWidget()
# window.setWindowTitle("PyQt5 Test Window")
# window.resize(400, 300)
# window.show()
# sys.exit(app.exec_())
