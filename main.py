import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QLabel, QHBoxLayout, QMessageBox
)
from metrc_api import MetrcAPI

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

        self.license_dropdown = QComboBox()
        self.license_dropdown.addItems(["CUL000032", "MAN000035"])  # Add license options
        top_layout.addWidget(QLabel("Select License:"))
        top_layout.addWidget(self.license_dropdown)

        self.package_id_input = QLineEdit()
        self.package_id_input.setPlaceholderText("Enter partial package ID")
        top_layout.addWidget(QLabel("Package ID:"))
        top_layout.addWidget(self.package_id_input)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_lab_test_results)
        top_layout.addWidget(self.search_button)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Test Name", "Result", "Date", "Notes"])

        layout.addLayout(top_layout)
        layout.addWidget(self.results_table)
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

    def search_lab_test_results(self):
        package_id = self.package_id_input.text().strip()
        license_number = self.license_dropdown.currentText()

        if not package_id:
            self.show_error("Package ID input is empty. Please enter a partial or full package ID.")
            return

        try:
            # Fetch active packages
            active_packages = self.metrc_api.get_active_packages(license_number)

            # Debugging: Print all packages
            print(f"All Active Packages: {active_packages}")

            # Filter packages matching the partial package ID
            matching_packages = [
                pkg for pkg in active_packages if package_id in pkg.get("Label", "")
            ]

            if not matching_packages:
                self.show_error("No matching packages found.")
                return

            # Debugging: Print matching packages
            print(f"Matching Packages: {matching_packages}")

            # Ensure the package has lab testing data
            valid_packages = [
                pkg for pkg in matching_packages if pkg.get("LabTestingState") in ("Submitted", "Tested")
            ]

            if not valid_packages:
                self.show_error("No valid lab test results available for the matching packages.")
                return

            # Use the first valid package to fetch its lab test results
            first_match = valid_packages[0]["Label"]
            test_results = self.metrc_api.get_lab_test_results(first_match, license_number)

            # Display results in the table
            self.display_results(test_results)
        except ValueError as e:
            self.show_error(str(e))

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MetrcApp()
    window.show()
    sys.exit(app.exec_())
