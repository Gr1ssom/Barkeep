import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QComboBox, QTableWidget, QTableWidgetItem, 
    QMessageBox
)
from metrc_api import get_package_id, get_test_results

class MetrcApp(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("METRC Test Results (v2)")
        self.setGeometry(100, 100, 800, 600)  # Optional: Set window size
        
        # License selection
        self.license_label = QLabel("Select License:")
        self.license_combo = QComboBox()
        self.license_combo.addItems(["MAN000035", "CUL000032"])
        
        # Partial tag input
        self.tag_label = QLabel("Enter Partial Tag:")
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("e.g., 23570 for MAN000035")
        
        # Search button
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_test_results)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)  
        self.results_table.setHorizontalHeaderLabels(["Test Type", "Status", "Result", "Date"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # Layouts
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.license_label)
        input_layout.addWidget(self.license_combo)
        input_layout.addWidget(self.tag_label)
        input_layout.addWidget(self.tag_input)
        input_layout.addWidget(self.search_button)
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.results_table)
        
        self.setLayout(main_layout)
    
    def search_test_results(self):
        license_code = self.license_combo.currentText()
        partial_tag = self.tag_input.text().strip()
        
        if not partial_tag:
            QMessageBox.warning(self, "Input Error", "Please enter a partial tag.")
            return

        prefix = PREFIXES.get(license_code)
        if not prefix:
            QMessageBox.warning(self, "License Error", f"No prefix found for license {license_code}.")
            return
        
        full_label = prefix + partial_tag
        self.log_message(f"Full package label constructed: {full_label}")
        
        # Get packageId
        package_id = get_package_id(license_code, full_label)
        if package_id is None:
            QMessageBox.warning(self, "API Error", "Failed to retrieve package details. Check debug.log for details.")
            return
        
        # Get test results
        test_results = get_test_results(license_code, package_id)
        if test_results is None:
            QMessageBox.warning(self, "API Error", "Failed to retrieve test results. Check debug.log for details.")
            return
        
        if not test_results:
            QMessageBox.information(self, "No Results", "No test results found for this package.")
        else:
            self.populate_table(test_results)
    
    def populate_table(self, results):
        # Clear existing rows
        self.results_table.setRowCount(0)
        
        # Ensure results is a list
        if not isinstance(results, list):
            QMessageBox.warning(self, "Data Error", "Unexpected data format received from API.")
            logging.error("Expected a list of test results, got: %s", type(results))
            return
        
        self.results_table.setRowCount(len(results))
        
        for i, result in enumerate(results):
            if not isinstance(result, dict):
                logging.error("Expected a dict for test result, got: %s", type(result))
                continue  # Skip this entry
            
            # Extract data using correct keys
            test_type = result.get("TestTypeName", "N/A")
            status = "Passed" if result.get("TestPassed", False) else "Failed"
            test_result = result.get("TestResultLevel", "N/A")
            test_date = result.get("TestPerformedDate", "N/A")
            
            self.results_table.setItem(i, 0, QTableWidgetItem(test_type))
            self.results_table.setItem(i, 1, QTableWidgetItem(status))
            self.results_table.setItem(i, 2, QTableWidgetItem(str(test_result)))
            self.results_table.setItem(i, 3, QTableWidgetItem(test_date))
        
        self.results_table.resizeColumnsToContents()
    
    def log_message(self, message):
        # Optional: Implement if you want to display log messages in the UI
        print(message)  # For simplicity, using print. You can enhance this as needed.

# Global prefixes (duplicate from metrc_api.py for access in main.py)
PREFIXES = {
    "MAN000035": "1A40C03000043950000",
    "CUL000032": "1A40C030000332D0000"
}

def main():
    app = QApplication(sys.argv)
    window = MetrcApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
