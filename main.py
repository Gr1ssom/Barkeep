import sys
import logging
import re
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QMessageBox, QSplitter, QProgressBar
)
from metrc_api import get_package_id, get_test_results, PREFIXES

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
    "Beta-Caryophyllene",
    "Alpha-Pinene",
    "Beta-Pinene",
    "Limonene",
    "Linalool",
    "Terpinolene",
    "Humulene",
    "Ocimene",
    "Geraniol",
    "Eucalyptol",
    "Camphene",
    "Borneol",
    "Delta-3-Carene",
    "Terpineol",
    "Farnesene",
    "Guaiol",
    "Isopulegol",
    "Nerolidol"
]

class Worker(QObject):
    finished = pyqtSignal(dict)        # Emitted when done: { "success": bool, ... }
    error = pyqtSignal(str, str)       # Emitted on error with context
    test_results_ready = pyqtSignal(list)  # Emitted when test results are fetched

    def __init__(self, license_code, full_label, parent=None):
        super().__init__(parent)
        self.license_code = license_code
        self.full_label = full_label

    def run(self):
        # Run the API calls in this thread
        package_response = get_package_id(self.license_code, self.full_label)
        if not package_response["success"]:
            self.error.emit(package_response.get("error", "Unknown error"), "package details")
            return

        package_id = package_response["package_id"]
        test_response = get_test_results(self.license_code, package_id)
        if not test_response["success"]:
            self.error.emit(test_response.get("error", "Unknown error"), "test results")
            return

        test_results = test_response["data"]
        self.test_results_ready.emit(test_results)
        self.finished.emit({"success": True})

class MetrcApp(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("METRC Test Results (v2)")
        # Adjust initial window size
        self.resize(1300, 900)
        
        # Create a font for input fields
        input_font = QFont()
        input_font.setPointSize(12)  # Adjust as needed

        # License selection
        self.license_label = QLabel("Select License:")
        self.license_combo = QComboBox()
        self.license_combo.addItems(["MAN000035", "CUL000032"])
        self.license_combo.setFont(input_font)  # Increase font size
        
        # Partial tag input
        self.tag_label = QLabel("Enter Partial Tag:")
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("e.g., 23570 for MAN000035")
        self.tag_input.setFont(input_font)  # Increase font size

        # Search button
        self.search_button = QPushButton("Search")
        
        # Status label
        self.status_label = QLabel("")
        
        # Progress bar for loading indication
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)

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
        
        # Connect search button clicked
        self.search_button.clicked.connect(self.search_test_results)

        # Cannabinoids Section Layout
        cannabinoids_layout = QVBoxLayout()
        cannabinoids_label = QLabel("Cannabinoid Test Results")
        cannabinoids_layout.addWidget(cannabinoids_label)
        cannabinoids_layout.addWidget(self.cannabinoids_table)
        
        cannabinoids_widget = QWidget()
        cannabinoids_widget.setLayout(cannabinoids_layout)

        # Terpenes Section Layout
        terpenes_layout = QVBoxLayout()
        terpenes_label = QLabel("Terpene Test Results")
        terpenes_layout.addWidget(terpenes_label)
        terpenes_layout.addWidget(self.terpenes_table)

        terpenes_widget = QWidget()
        terpenes_widget.setLayout(terpenes_layout)

        # Use a splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(cannabinoids_widget)
        splitter.addWidget(terpenes_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        main_layout = QVBoxLayout()
        # Reduce margins and spacing
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(splitter)
        
        # Give the splitter more priority in vertical space
        main_layout.setStretchFactor(splitter, 1)

        self.setLayout(main_layout)

        self.thread = None  # We'll use this to reference the QThread

    def search_test_results(self):
        license_code = self.license_combo.currentText()
        partial_tag = self.tag_input.text().strip()
        
        if not partial_tag:
            QMessageBox.warning(self, "Input Error", "Please enter a partial tag.")
            return

        if not partial_tag.isdigit():
            QMessageBox.warning(self, "Input Error", "Partial tag must contain only digits.")
            return

        prefix = PREFIXES.get(license_code)
        if not prefix:
            QMessageBox.warning(self, "License Error", f"No prefix found for license {license_code}.")
            return
        
        full_label = prefix + partial_tag
        self.log_message(f"Full package label constructed: {full_label}")
        self.status_label.setText("Fetching package details and test results...")

        # Show progress bar
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)
        
        # Create a thread and a worker
        self.thread = QThread()
        self.worker = Worker(license_code, full_label)
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.error.connect(self.handle_error)
        self.worker.test_results_ready.connect(self.handle_test_results)
        self.worker.finished.connect(self.worker_done)

        # Start the thread
        self.thread.start()

    def handle_error(self, error_message, context):
        self.progress_bar.setVisible(False)
        if error_message == "Unauthorized":
            QMessageBox.critical(self, "Authentication Error", f"Unauthorized access when fetching {context}. Please check your API credentials and permissions.")
        elif error_message == "packageId not found":
            QMessageBox.warning(self, "Not Found", f"Package ID not found when fetching {context}.")
        else:
            QMessageBox.warning(self, "API Error", f"Failed to retrieve {context}: {error_message}")
        self.status_label.setText(f"Error fetching {context}.")
        # Stop the thread
        self.thread.quit()
        self.thread.wait()

    def handle_test_results(self, test_results):
        if not test_results:
            QMessageBox.information(self, "No Results", "No test results found for this package.")
            self.status_label.setText("No test results found.")
            self.populate_cannabinoids_table([])
            self.populate_terpenes_table([])
        else:
            self.populate_cannabinoids_table(test_results)
            self.populate_terpenes_table(test_results)
            self.status_label.setText("Test results fetched successfully.")

    def worker_done(self, result):
        self.progress_bar.setVisible(False)
        self.thread.quit()
        self.thread.wait()

    def simplify_cannabinoid_name(self, test_type):
        # Remove known phrases
        test_type = test_type.replace("Raw Plant Material & PreRolls", "")
        test_type = test_type.replace("Mandatory Cannabinoid % and Totals", "")
        
        # Remove parentheses and their contents
        test_type = re.sub(r"\(.*?\)", "", test_type).strip()
        
        # Remove leading "Total "
        if test_type.lower().startswith("total "):
            test_type = test_type[6:].strip()
        
        test_type_lower = test_type.lower()
        
        if "cbda" in test_type_lower:
            return "CBDA"
        elif "cbn" in test_type_lower:
            return "CBN"
        elif "cbdv" in test_type_lower:
            return "CBDV"
        elif "cbd" in test_type_lower:
            return "CBD"
        elif "thca" in test_type_lower:
            return "THCA"
        elif "thcv" in test_type_lower:
            return "THCV"
        elif "delta-9 thc" in test_type_lower or "Δ9-thc" in test_type_lower or "thc(" in test_type_lower:
            return "THC"
        elif "thc" in test_type_lower:
            return "THC"
        
        return test_type
    
    def populate_cannabinoids_table(self, results):
        try:
            self.cannabinoids_table.setRowCount(0)
            
            filtered_results = [
                result for result in results 
                if isinstance(result, dict) and any(ct in result.get("TestTypeName", "") for ct in CANNABINOID_TEST_TYPES)
            ]
            
            if not filtered_results:
                self.cannabinoids_table.setRowCount(0)
                return
            
            self.cannabinoids_table.setRowCount(len(filtered_results))
            
            for i, result in enumerate(filtered_results):
                original_test_type = result.get("TestTypeName", "N/A")
                
                # Simplify the displayed name
                test_type = self.simplify_cannabinoid_name(original_test_type)
                
                status = "Passed" if result.get("TestPassed", False) else "Failed"
                test_result = result.get("TestResultLevel", "N/A")
                test_date = result.get("TestPerformedDate", "N/A")
                
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
            self.terpenes_table.setRowCount(0)
            
            filtered_results = [
                result for result in results
                if isinstance(result, dict) and any(tt in result.get("TestTypeName", "") for tt in TERPENE_TEST_TYPES)
            ]
            
            if not filtered_results:
                self.terpenes_table.setRowCount(0)
                return
            
            self.terpenes_table.setRowCount(len(filtered_results))
            
            for i, result in enumerate(filtered_results):
                terpene = result.get("TestTypeName", "N/A")
                status = "Passed" if result.get("TestPassed", False) else "Failed"
                concentration = result.get("TestResultLevel", "N/A")
                test_date = result.get("TestPerformedDate", "N/A")
                
                self.terpenes_table.setItem(i, 0, QTableWidgetItem(terpene))
                self.terpenes_table.setItem(i, 1, QTableWidgetItem(status))
                self.terpenes_table.setItem(i, 2, QTableWidgetItem(str(concentration)))
                self.terpenes_table.setItem(i, 3, QTableWidgetItem(test_date))
            
            self.terpenes_table.resizeColumnsToContents()
        except Exception as e:
            logging.exception("Error populating terpenes table: %s", e)
            QMessageBox.critical(self, "Data Binding Error", "An error occurred while displaying terpene test results.")
    
    def log_message(self, message):
        logging.info(message)

def main():
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
