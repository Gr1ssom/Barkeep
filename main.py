import sys
import logging
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QLabel, QHBoxLayout, QMessageBox
)
from metrc_api import MetrcAPI

# Configure logging to log errors to output.txt
logging.basicConfig(filename='output.txt', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')


class MetrcApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("METRC Lab Test Results")
        self.setGeometry(200, 200, 800, 600)
        self.metrc_api = MetrcAPI()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        main_widget = QWidget()

        # License selection
        self.license_dropdown = QComboBox()
        self.license_dropdown.addItems(["CUL000032", "MAN000035"])
        top_layout.addWidget(QLabel("Select License:"))
        top_layout.addWidget(self.license_dropdown)

        # Tag entry field
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Enter partial tag (e.g., 23559 or 28331)")
        top_layout.addWidget(QLabel("Tag:"))
        top_layout.addWidget(self.tag_input)

        # Search button
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_lab_test_results)
        top_layout.addWidget(self.search_button)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Test Name", "Result", "Date", "Notes"])

        layout.addLayout(top_layout)
        layout.addWidget(self.results_table)
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

    def search_lab_test_results(self):
        tag_input = self.tag_input.text().strip()
        license_number = self.license_dropdown.currentText()

        if not tag_input:
            self.show_error("Tag input is empty. Please enter a partial tag.")
            return

        try:
            # Fetch active packages filtered by partial tag and LabTestingState
            matching_packages = self.metrc_api.get_active_packages(license_number, partial_tag=tag_input)

            if not matching_packages:
                self.show_error("No packages with 'TestPassed' state found matching the given tag.")
                return

            # Use the first matching package to fetch its lab test results
            selected_package = matching_packages[0]["Label"]
            test_results = self.metrc_api.get_lab_test_results(selected_package, license_number)

            # Display the test results in the table
            self.display_results(test_results)
        except ValueError as e:
            error_message = str(e)
            self.log_error(error_message)
            self.show_error(error_message)

    def display_results(self, test_results):
        self.results_table.setRowCount(0)
        for result in test_results:
            row_position = self.results_table.rowCount()
            self.results_table.insertRow(row_position)
            self.results_table.setItem(row_position, 0, QTableWidgetItem(result.get('TestName', 'N/A')))
            self.results_table.setItem(row_position, 1, QTableWidgetItem(result.get('Result', 'N/A')))
            self.results_table.setItem(row_position, 2, QTableWidgetItem(result.get('TestDate', 'N/A')))
            self.results_table.setItem(row_position, 3, QTableWidgetItem(result.get('Notes', 'N/A')))

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def log_error(self, message):
        logging.error(message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MetrcApp()
    window.show()
    sys.exit(app.exec_())
