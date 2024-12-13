import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QComboBox, QTableWidget, QTableWidgetItem, 
    QMessageBox
)
from metrc_api import get_package_id, get_test_results
import logging

# Define the specific cannabinoid and terpene test types
# Expanded to include all relevant TestTypeName values from the API
CANNABINOID_TEST_TYPES = [
    "Δ9-THC",
    "THCA",
    "CBD",
    "CBDA",
    "TOTAL THC",
    "CBN",
    "THCV",
    "CBDV",
    "Δ8-THC",
    "TOTAL CBD",
    "Total CBD (mg/serving) Mandatory Cannabinoid % and Totals",
    "Total CBD (mg/unit) Raw Plant Material & Prerolls",
    "CBD (%) Mandatory Cannabinoid % and Totals",
    "CBDA (%) Mandatory Cannabinoid % and Totals",
    "Total THC (mg/serving) Mandatory Cannabinoid % and Totals",
    "Total THC (mg/unit) Raw Plant Material & PreRolls",
    "Delta-9 THC (mg/serving) Raw Plant Material & PreRolls",
    "Total Delta-9 THC (mg/serving) Mandatory Cannabinoid % and Totals",
    "Total Delta-9 THC (mg/unit) Raw Plant Material & PreRolls",
    "Delta-9 THC (%) Mandatory Cannabinoid % and Totals",
    "Total Delta-9 THC (%) Mandatory Cannabinoid % and Totals",
]

TERPENE_TEST_TYPES = [
    "Myrcene",
    "Limonene",
    "Pinene",
    "Linalool",
    "Caryophyllene",
    "Terpinolene",
    "Humulene",
    "Ocimene",
    "Geraniol",
    "Eucalyptol",
    # Add more terpenes as needed
]

class MetrcApp(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("METRC Test Results (v2)")
        self.setGeometry(100, 100, 1200, 800)  # Increased window size for better layout
        
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
        
        # Status label
        self.status_label = QLabel("")
        
        # Cannabinoids table
        self.cannabinoids_table = QTableWidget()
        self.cannabinoids_table.setColumnCount(4)  
        self.cannabinoids_table.setHorizontalHeaderLabels(["Test Type", "Status", "Result", "Date"])
        self.cannabinoids_table.horizontalHeader().setStretchLastSection(True)
        self.cannabinoids_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.cannabinoids_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # Terpenes table
        self.terpenes_table = QTableWidget()
        self.terpenes_table.setColumnCount(4)  
        self.terpenes_table.setHorizontalHeaderLabels(["Terpene", "Status", "Concentration", "Date"])
        self.terpenes_table.horizontalHeader().setStretchLastSection(True)
        self.terpenes_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.terpenes_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # Layouts
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.license_label)
        input_layout.addWidget(self.license_combo)
        input_layout.addWidget(self.tag_label)
        input_layout.addWidget(self.tag_input)
        input_layout.addWidget(self.search_button)
        
        tables_layout = QHBoxLayout()
        
        # Cannabinoids Section
        cannabinoids_layout = QVBoxLayout()
        cannabinoids_label = QLabel("Cannabinoid Test Results")
        cannabinoids_layout.addWidget(cannabinoids_label)
        cannabinoids_layout.addWidget(self.cannabinoids_table)
        
        # Terpenes Section
        terpenes_layout = QVBoxLayout()
        terpenes_label = QLabel("Terpene Test Results")
        terpenes_layout.addWidget(terpenes_label)
        terpenes_layout.addWidget(self.terpenes_table)
        
        tables_layout.addLayout(cannabinoids_layout)
        tables_layout.addLayout(terpenes_layout)
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.status_label)
        main_layout.addLayout(tables_layout)
        
        self.setLayout(main_layout)
    
    def search_test_results(self):
        license_code = self.license_combo.currentText()
        partial_tag = self.tag_input.text().strip()
        
        if not partial_tag:
            QMessageBox.warning(self, "Input Error", "Please enter a partial tag.")
            return

        # Optional: Validate partial_tag format (e.g., digits only)
        if not partial_tag.isdigit():
            QMessageBox.warning(self, "Input Error", "Partial tag must contain only digits.")
            return

        prefix = PREFIXES.get(license_code)
        if not prefix:
            QMessageBox.warning(self, "License Error", f"No prefix found for license {license_code}.")
            return
        
        full_label = prefix + partial_tag
        self.log_message(f"Full package label constructed: {full_label}")
        self.status_label.setText("Fetching package details...")
        
        # Get packageId
        package_response = get_package_id(license_code, full_label)
        if not package_response["success"]:
            error_message = package_response.get("error", "Unknown error.")
            if error_message == "Unauthorized":
                QMessageBox.critical(self, "Authentication Error", "Unauthorized access. Please check your API credentials and permissions.")
            elif error_message == "packageId not found":
                QMessageBox.warning(self, "Not Found", "Package ID not found for the provided label.")
            else:
                QMessageBox.warning(self, "API Error", f"Failed to retrieve package details: {error_message}")
            self.status_label.setText("Error fetching package details.")
            return
        
        package_id = package_response["package_id"]
        self.log_message(f"Retrieved packageId: {package_id}")
        self.status_label.setText("Fetching test results...")
        
        # Get test results
        test_response = get_test_results(license_code, package_id)
        if not test_response["success"]:
            error_message = test_response.get("error", "Unknown error.")
            if "pageSize" in error_message:
                QMessageBox.critical(self, "API Parameter Error", f"API Error: {error_message}")
            elif error_message == "Unauthorized":
                QMessageBox.critical(self, "Authentication Error", "Unauthorized access when fetching test results. Please check your API credentials and permissions.")
            else:
                QMessageBox.warning(self, "API Error", f"Failed to retrieve test results: {error_message}")
            self.status_label.setText("Error fetching test results.")
            return
        
        test_results = test_response["data"]
        if not test_results:
            QMessageBox.information(self, "No Results", "No test results found for this package.")
            self.status_label.setText("No test results found.")
        else:
            # Populate cannabinoids and terpenes tables
            self.populate_cannabinoids_table(test_results)
            self.populate_terpenes_table(test_results)
            self.status_label.setText("Test results fetched successfully.")
    
    def populate_cannabinoids_table(self, results):
        try:
            # Clear existing rows
            self.cannabinoids_table.setRowCount(0)
            
            # Ensure results is a list
            if not isinstance(results, list):
                QMessageBox.warning(self, "Data Error", "Unexpected data format received from API.")
                logging.error("Expected a list of test results, got: %s", type(results))
                return
            
            # Filter results to include only specific cannabinoid test types
            filtered_results = [
                result for result in results 
                if isinstance(result, dict) and any(ct in result.get("TestTypeName", "") for ct in CANNABINOID_TEST_TYPES)
            ]
            
            if not filtered_results:
                QMessageBox.information(self, "No Results", "No specified cannabinoid test results found for this package.")
                self.cannabinoids_table.setRowCount(0)
                return
            
            self.cannabinoids_table.setRowCount(len(filtered_results))
            
            for i, result in enumerate(filtered_results):
                # Extract data using correct keys
                test_type = result.get("TestTypeName", "N/A")
                status = "Passed" if result.get("TestPassed", False) else "Failed"
                test_result = result.get("TestResultLevel", "N/A")
                test_date = result.get("TestPerformedDate", "N/A")
                
                # Handle different units by extracting from TestTypeName
                # Example: "Total THC (mg/unit) Raw Plant Material & PreRolls"
                if "(" in test_type and ")" in test_type:
                    unit = test_type.split("(")[1].split(")")[0]
                    display_result = f"{test_result} {unit}"
                else:
                    display_result = str(test_result)
                
                self.cannabinoids_table.setItem(i, 0, QTableWidgetItem(test_type))
                self.cannabinoids_table.setItem(i, 1, QTableWidgetItem(status))
                self.cannabinoids_table.setItem(i, 2, QTableWidgetItem(display_result))
                self.cannabinoids_table.setItem(i, 3, QTableWidgetItem(test_date))
            
            self.cannabinoids_table.resizeColumnsToContents()
        except Exception as e:
            logging.exception("Error populating cannabinoids table: %s", e)
            QMessageBox.critical(self, "Data Binding Error", "An error occurred while displaying cannabinoid test results.")
    
    def populate_terpenes_table(self, results):
        try:
            # Clear existing rows
            self.terpenes_table.setRowCount(0)
            
            # Ensure results is a list
            if not isinstance(results, list):
                QMessageBox.warning(self, "Data Error", "Unexpected data format received from API.")
                logging.error("Expected a list of test results, got: %s", type(results))
                return
            
            # Filter results to include only specific terpene test types
            filtered_results = [
                result for result in results 
                if isinstance(result, dict) and any(tt in result.get("TestTypeName", "") for tt in TERPENE_TEST_TYPES)
            ]
            
            if not filtered_results:
                QMessageBox.information(self, "No Results", "No specified terpene test results found for this package.")
                self.terpenes_table.setRowCount(0)
                return
            
            self.terpenes_table.setRowCount(len(filtered_results))
            
            for i, result in enumerate(filtered_results):
                # Extract data using correct keys
                terpene = result.get("TestTypeName", "N/A")
                status = "Passed" if result.get("TestPassed", False) else "Failed"
                concentration = result.get("TestResultLevel", "N/A")
                test_date = result.get("TestPerformedDate", "N/A")
                
                # Handle different units by extracting from TestTypeName
                if "(" in terpene and ")" in terpene:
                    unit = terpene.split("(")[1].split(")")[0]
                    display_concentration = f"{concentration} {unit}"
                else:
                    display_concentration = str(concentration)
                
                self.terpenes_table.setItem(i, 0, QTableWidgetItem(terpene))
                self.terpenes_table.setItem(i, 1, QTableWidgetItem(status))
                self.terpenes_table.setItem(i, 2, QTableWidgetItem(display_concentration))
                self.terpenes_table.setItem(i, 3, QTableWidgetItem(test_date))
            
            self.terpenes_table.resizeColumnsToContents()
        except Exception as e:
            logging.exception("Error populating terpenes table: %s", e)
            QMessageBox.critical(self, "Data Binding Error", "An error occurred while displaying terpene test results.")
    
    def log_message(self, message):
        # Optional: Implement if you want to display log messages in the UI
        logging.info(message)  # Logging instead of print for better traceability

# Global prefixes (moved to the top for better accessibility)
PREFIXES = {
    "MAN000035": "1A40C03000043950000",
    "CUL000032": "1A40C030000332D0000"
}

def main():
    # Configure logging to display messages on the console as well
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(console_formatter)
    logging.getLogger().addHandler(console_handler)
    
    app = QApplication(sys.argv)
    window = MetrcApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
