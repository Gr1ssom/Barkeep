import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QLabel, QHBoxLayout
)
from metrc_api import MetrcAPI

class MetrcApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("METRC Package Testing Results")
        self.setGeometry(200, 200, 800, 600)
        self.metrc_api = MetrcAPI()
        self.initUI()

    def initUI(self):
        # Layouts
        layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        main_widget = QWidget()

        # Dropdown for licenses
        self.license_dropdown = QComboBox()
        self.license_dropdown.addItems(["CUL000032", "MAN000035"])
        top_layout.addWidget(QLabel("Select License:"))
        top_layout.addWidget(self.license_dropdown)

        # Input field for tag number
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Enter partial tag number")
        top_layout.addWidget(QLabel("Tag Number:"))
        top_layout.addWidget(self.tag_input)

        # Search button
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_packages)
        top_layout.addWidget(self.search_button)

        # Table for results
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Test Name", "Result", "Date", "Notes"])

        # Add layouts to the main layout
        layout.addLayout(top_layout)
        layout.addWidget(self.results_table)
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

    def search_packages(self):
        # Get the selected license and tag input
        license_number = self.license_dropdown.currentText()
        partial_tag = self.tag_input.text()

        try:
            packages = self.metrc_api.get_active_packages(license_number)
            filtered_packages = [
                pkg for pkg in packages if isinstance(pkg, dict) and 'Label' in pkg and partial_tag.lower() in pkg['Label'].lower()
            ]
            self.display_results(filtered_packages)
        except ValueError as e:
            print(f"Error: {e}")

    def display_results(self, packages):
        self.results_table.setRowCount(0)  # Clear existing rows
        for pkg in packages:
            try:
                test_results = self.metrc_api.get_testing_results(pkg['Id'])
                for result in test_results:
                    row_position = self.results_table.rowCount()
                    self.results_table.insertRow(row_position)
                    self.results_table.setItem(row_position, 0, QTableWidgetItem(result['TestName']))
                    self.results_table.setItem(row_position, 1, QTableWidgetItem(result['Result']))
                    self.results_table.setItem(row_position, 2, QTableWidgetItem(result['TestDate']))
                    self.results_table.setItem(row_position, 3, QTableWidgetItem(result.get('Notes', '')))
            except ValueError as e:
                print(f"Error fetching test results for package {pkg['Id']}: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MetrcApp()
    window.show()
    sys.exit(app.exec_())
