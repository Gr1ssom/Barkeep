import sys
import logging
import re
import csv
from datetime import datetime
from dateutil.relativedelta import relativedelta
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QMessageBox, QSplitter, QProgressBar, QDialog, QDialogButtonBox,
    QFormLayout, QSpinBox
)
from metrc_api import get_package_id, get_test_results, PREFIXES

CANNABINOID_TEST_TYPES = [
    "Δ9-THC", "THCA", "CBD", "CBDA", "TOTAL THC", "CBN", "THCV", "CBDV", "Δ8-THC", "TOTAL CBD",
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
    "Myrcene", "Beta-Caryophyllene", "Alpha-Pinene", "Beta-Pinene", "Limonene", "Linalool",
    "Terpinolene", "Humulene", "Ocimene", "Geraniol", "Eucalyptol", "Camphene", "Borneol",
    "Delta-3-Carene", "Terpineol", "Farnesene", "Guaiol", "Isopulegol", "Nerolidol"
]

UNIT_WEIGHTS = {
    "MAN000035": ["0.5g", "1g", "2g", "3.5g", "100mg", "250mg", "500mg"],
    "CUL000032": ["1g", "3.5g", "7g", "14g", "28g", "448g"]
}

class Worker(QObject):
    finished = pyqtSignal(dict)        
    error = pyqtSignal(str, str)       
    test_results_ready = pyqtSignal(list, dict)

    def __init__(self, license_code, full_label, parent=None):
        super().__init__(parent)
        self.license_code = license_code
        self.full_label = full_label

    def run(self):
        package_response = get_package_id(self.license_code, self.full_label)
        if not package_response["success"]:
            self.error.emit(package_response.get("error", "Unknown error"), "package details")
            return

        package_id = package_response["package_id"]
        product_name = package_response.get("product_name", self.full_label)
        source_package_label = package_response.get("source_package_label", "N/A")

        test_response = get_test_results(self.license_code, package_id)
        if not test_response["success"]:
            self.error.emit(test_response.get("error", "Unknown error"), "test results")
            return

        test_results = test_response["data"]
        package_info = {
            "product_name": product_name,
            "source_package_label": source_package_label
        }
        self.test_results_ready.emit(test_results, package_info)
        self.finished.emit({"success": True})


class UnitWeightDialog(QDialog):
    def __init__(self, unit_weight_options, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Label Details")
        form_layout = QFormLayout(self)

        self.unit_weight_combo = QComboBox()
        self.unit_weight_combo.addItems(unit_weight_options)
        form_layout.addRow("Unit Weight:", self.unit_weight_combo)

        self.num_labels_spin = QSpinBox()
        self.num_labels_spin.setMinimum(1)
        self.num_labels_spin.setValue(1)
        form_layout.addRow("Number of Labels:", self.num_labels_spin)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        form_layout.addRow(button_box)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    def get_values(self):
        return self.unit_weight_combo.currentText(), self.num_labels_spin.value()


class MetrcApp(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Barkeep by Grissom")
        self.resize(1300, 900)
        
        input_font = QFont()
        input_font.setPointSize(12)

        logo_label = QLabel("RobustMo")

        self.license_label = QLabel("Select License:")
        self.license_combo = QComboBox()
        self.license_combo.addItems(["MAN000035", "CUL000032"])
        self.license_combo.setFont(input_font)
        
        self.tag_label = QLabel("Enter Partial Tag:")
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("e.g., 23570 for MAN000035")
        self.tag_input.setFont(input_font)
        # Pressing Enter triggers search
        self.tag_input.returnPressed.connect(self.search_test_results)

        self.search_button = QPushButton("Search")
        
        self.status_label = QLabel("")
        self.expiration_label = QLabel("Expiration Date: N/A")
        self.source_package_label = QLabel("Source Package: N/A")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)

        self.cannabinoids_table = QTableWidget()
        self.cannabinoids_table.setColumnCount(4)
        self.cannabinoids_table.setHorizontalHeaderLabels(["Test Type", "Status", "Result", "Date"])
        self.cannabinoids_table.horizontalHeader().setStretchLastSection(True)
        self.cannabinoids_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.cannabinoids_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.cannabinoids_table.setAlternatingRowColors(True)

        self.terpenes_table = QTableWidget()
        self.terpenes_table.setColumnCount(4)
        self.terpenes_table.setHorizontalHeaderLabels(["Terpene", "Status", "Concentration", "Date"])
        self.terpenes_table.horizontalHeader().setStretchLastSection(True)
        self.terpenes_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.terpenes_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.terpenes_table.setAlternatingRowColors(True)
        
        top_layout = QHBoxLayout()
        top_layout.addWidget(logo_label)
        top_layout.addStretch()

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.license_label)
        input_layout.addWidget(self.license_combo)
        input_layout.addWidget(self.tag_label)
        input_layout.addWidget(self.tag_input)
        input_layout.addWidget(self.search_button)
        
        self.search_button.clicked.connect(self.search_test_results)

        cannabinoids_layout = QVBoxLayout()
        cannabinoids_label = QLabel("Cannabinoid Test Results")
        cannabinoids_layout.addWidget(cannabinoids_label)
        cannabinoids_layout.addWidget(self.cannabinoids_table)
        
        cannabinoids_widget = QWidget()
        cannabinoids_widget.setLayout(cannabinoids_layout)

        terpenes_layout = QVBoxLayout()
        terpenes_label = QLabel("Terpene Test Results")
        terpenes_layout.addWidget(terpenes_label)
        terpenes_layout.addWidget(self.terpenes_table)

        terpenes_widget = QWidget()
        terpenes_widget.setLayout(terpenes_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(cannabinoids_widget)
        splitter.addWidget(terpenes_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        export_layout = QHBoxLayout()
        self.export_button = QPushButton("Export")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.handle_export_click)
        export_layout.addStretch()
        export_layout.addWidget(self.export_button)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        main_layout.addLayout(top_layout)
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.expiration_label)
        main_layout.addWidget(self.source_package_label)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(splitter)
        main_layout.addLayout(export_layout)
        
        main_layout.setStretchFactor(splitter, 1)

        self.setLayout(main_layout)

        self.thread = None

        # Variables to store extracted data
        self.product_name = "Unknown Product"
        self.thc_value = "N/A"
        self.cbd_value = "N/A"
        self.test_date = "N/A"
        self.expiration_date = "N/A"
        self.source_package_label_value = "N/A"

        self.approval_number = "N/A"
        self.strain_name = "N/A"
        self.product_description = "N/A"

        self.setStyleSheet("""
            QWidget {
                background-color: #f7f7f7; 
                font-size: 12pt; 
                font-family: Arial, sans-serif;
            }
            QLabel {
                color: #333; 
            }
            QComboBox, QLineEdit, QPushButton {
                background: #fff;
                border: 1px solid #ccc;
                padding: 4px;
                border-radius: 3px;
            }
            QComboBox QAbstractItemView {
                background: #fff;
                border: 1px solid #ccc;
            }
            QPushButton {
                background-color: #CE1000; 
                color: #fff;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #B10E00;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #666;
            }
            QTableWidget {
                border: 1px solid #aaa;
                gridline-color: #ccc;
                selection-background-color: #CE1000;
                alternate-background-color: #eaeaea;
            }
            QHeaderView::section {
                background-color: #CE1000;
                color: #fff;
                font-weight: bold;
                padding: 4px;
                border: none;
            }
        """)

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

        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)
        
        self.thread = QThread()
        self.worker = Worker(license_code, full_label)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.error.connect(self.handle_error)
        self.worker.test_results_ready.connect(self.handle_test_results)
        self.worker.finished.connect(self.worker_done)

        self.thread.start()

    def handle_error(self, error_message, context):
        self.progress_bar.setVisible(False)
        if error_message == "Unauthorized":
            QMessageBox.critical(self, "Authentication Error", f"Unauthorized access when fetching {context}. Check API credentials.")
        elif error_message == "packageId not found":
            QMessageBox.warning(self, "Not Found", f"Package ID not found when fetching {context}.")
        else:
            QMessageBox.warning(self, "API Error", f"Failed to retrieve {context}: {error_message}")
        self.status_label.setText(f"Error fetching {context}.")
        self.thread.quit()
        self.thread.wait()

    def handle_test_results(self, test_results, package_info):
        if not test_results:
            QMessageBox.information(self, "No Results", "No test results found for this package.")
            self.status_label.setText("No test results found.")
            self.populate_cannabinoids_table([])
            self.populate_terpenes_table([])
            self.export_button.setEnabled(False)
        else:
            self.populate_cannabinoids_table(test_results)
            self.populate_terpenes_table(test_results)
            self.status_label.setText("Test results fetched successfully.")

            self.product_name = package_info.get("product_name", "Unknown Product")
            self.source_package_label_value = package_info.get("source_package_label", "N/A")
            self.test_date = self.extract_test_date(test_results)
            self.expiration_date = "N/A"
            if self.test_date != "N/A":
                self.expiration_date = self.add_one_year(self.test_date)

            self.parse_product_name(self.product_name)

            self.expiration_label.setText(f"Expiration Date: {self.expiration_date}")
            self.source_package_label.setText(f"Source Package: {self.source_package_label_value}")

            self.thc_value, self.cbd_value = self.extract_thc_cbd_values(test_results)
            self.export_button.setEnabled(True)

    def parse_product_name(self, product_name):
        self.approval_number = "N/A"
        self.strain_name = "N/A"
        self.product_description = "N/A"

        if ':' in product_name:
            parts = product_name.split(':', 1)
            self.approval_number = parts[0].strip()
            rest = parts[1].strip()
        else:
            rest = product_name

        words = rest.split()
        if len(words) >= 1:
            # Last word is strain name
            self.strain_name = words[-1]
            if len(words) > 1:
                self.product_description = " ".join(words[:-1]).strip()
            else:
                self.product_description = ""
        else:
            self.strain_name = "N/A"
            self.product_description = rest

    def worker_done(self, result):
        self.progress_bar.setVisible(False)
        self.thread.quit()
        self.thread.wait()

    def handle_export_click(self):
        license_code = self.license_combo.currentText()
        unit_weights = UNIT_WEIGHTS.get(license_code, ["3.5g"])

        dialog = UnitWeightDialog(unit_weights, self)
        if dialog.exec_() == QDialog.Accepted:
            unit_weight, num_labels = dialog.get_values()
            self.export_results_to_csv(
                self.product_name, self.thc_value, self.cbd_value,
                self.test_date, self.expiration_date,
                self.source_package_label_value, unit_weight, num_labels,
                self.approval_number, self.product_description, self.strain_name
            )
            QMessageBox.information(self, "Export Complete", "Data exported to current_results.csv.")
        else:
            pass

    def log_message(self, message):
        logging.info(message)

    def extract_test_date(self, results):
        for r in results:
            if "TestPerformedDate" in r and r["TestPerformedDate"] != "N/A":
                date_str = r["TestPerformedDate"]
                try:
                    datetime.strptime(date_str, "%Y-%m-%d")
                    return date_str
                except ValueError:
                    return "N/A"
        return "N/A"

    def add_one_year(self, date_str):
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        new_date = date_obj + relativedelta(years=1)
        return new_date.strftime("%Y-%m-%d")

    def extract_thc_cbd_values(self, results):
        thc_value = "N/A"
        cbd_value = "N/A"
        for r in results:
            test_type = r.get("TestTypeName", "").lower()
            result_level = r.get("TestResultLevel", "N/A")
            result_str = str(result_level)
            units = self.extract_units(r.get("TestTypeName", ""))
            
            if "thc" in test_type and "n/a" not in result_str.lower():
                thc_value = f"{result_str} {units}" if units else result_str

            if "cbd" in test_type and "n/a" not in result_str.lower():
                cbd_value = f"{result_str} {units}" if units else result_str

        return thc_value, cbd_value

    def extract_units(self, test_type):
        units = ""
        unit_match = re.search(r"\((.*?)\)", test_type)
        if unit_match:
            units = unit_match.group(1)
        return units

    def populate_cannabinoids_table(self, results):
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
            test_type = self.simplify_cannabinoid_name(original_test_type)
            
            status = "Passed" if result.get("TestPassed", False) else "Failed"
            test_result = result.get("TestResultLevel", "N/A")
            test_date = result.get("TestPerformedDate", "N/A")

            units = self.extract_units(original_test_type)
            if units and test_result != "N/A":
                display_result = f"{test_result} {units}"
            else:
                display_result = str(test_result)
            
            self.cannabinoids_table.setItem(i, 0, QTableWidgetItem(test_type))
            self.cannabinoids_table.setItem(i, 1, QTableWidgetItem(status))
            self.cannabinoids_table.setItem(i, 2, QTableWidgetItem(display_result))
            self.cannabinoids_table.setItem(i, 3, QTableWidgetItem(test_date))
        
        self.cannabinoids_table.resizeColumnsToContents()
    
    def populate_terpenes_table(self, results):
        self.terpenes_table.setRowCount(0)
        filtered_results = [
            result for result in results
            if isinstance(result, dict) and any(tt in result.get("TestTypeName", "") for tt in TERPENE_TEST_TYPES)
        ]

        # Filter out terpenes with no concentration (N/A or zero)
        final_results = []
        for r in filtered_results:
            concentration = str(r.get("TestResultLevel", "N/A"))
            if concentration.lower() != "n/a":
                # Check if numeric and zero
                try:
                    val = float(concentration)
                    if val == 0.0:
                        continue  # skip zero values
                except ValueError:
                    # Not numeric, but not 'N/A' either, so keep it
                    pass
                final_results.append(r)

        if not final_results:
            self.terpenes_table.setRowCount(0)
            return

        self.terpenes_table.setRowCount(len(final_results))
        
        for i, result in enumerate(final_results):
            original_test_type = result.get("TestTypeName", "N/A")
            units = self.extract_units(original_test_type)
            
            display_name = re.sub(r"\(.*?\)", "", original_test_type).strip()
            
            status = "Passed" if result.get("TestPassed", False) else "Failed"
            concentration = result.get("TestResultLevel", "N/A")
            test_date = result.get("TestPerformedDate", "N/A")

            if units and concentration != "N/A":
                display_concentration = f"{concentration} {units}"
            else:
                display_concentration = str(concentration)
            
            # Remove "Mandatory Terpenes"
            display_name = display_name.replace("Mandatory Terpenes", "").strip()
            # Replace Alpha- with a-, Beta- with b-
            display_name = display_name.replace("Alpha-", "a-")
            display_name = display_name.replace("Beta-", "b-")

            self.terpenes_table.setItem(i, 0, QTableWidgetItem(display_name))
            self.terpenes_table.setItem(i, 1, QTableWidgetItem(status))
            self.terpenes_table.setItem(i, 2, QTableWidgetItem(display_concentration))
            self.terpenes_table.setItem(i, 3, QTableWidgetItem(test_date))
        
        self.terpenes_table.resizeColumnsToContents()

    def simplify_cannabinoid_name(self, test_type):
        test_type = test_type.replace("Raw Plant Material & PreRolls", "")
        test_type = test_type.replace("Mandatory Cannabinoid % and Totals", "")
        test_type = test_type.replace("Vapes & Concentrates", "")

        return test_type.strip()

    def export_results_to_csv(self, product_name, thc_value, cbd_value, test_date, expiration_date, source_package_label, unit_weight, num_labels, approval_number, product_description, strain_name):
        filename = "current_results.csv"
        headers = [
            "ApprovalNumber",
            "ProductDescription",
            "StrainName",
            "ProductName",
            "THCResult",
            "CBDResult",
            "TestDate",
            "ExpirationDate",
            "SourcePackage",
            "UnitWeight",
            "NumLabels",
            "TestingFacility"
        ]
        row = [
            approval_number,
            product_description,
            strain_name,
            product_name,
            thc_value,
            cbd_value,
            test_date,
            expiration_date,
            source_package_label,
            unit_weight,
            str(num_labels),
            "TES000011"
        ]

        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            writer.writerow(row)

        self.log_message(f"Exported results to {filename}. Bartender can now use this file.")


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
