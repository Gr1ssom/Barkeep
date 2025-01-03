import sys
import logging
import re
import json
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

# **Define Individual Cannabinoids**
INDIVIDUAL_CANNABINOIDS = [
    "Δ9-THC",
    "THCA",
    "CBD",
    "CBDA",
    "CBN",
    "THCV",
    "CBDV",
    "Δ8-THC"
]

# **Define All Cannabinoid Test Types (Including Aggregated)**
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

# Worker class definition
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
            "source_package_label": source_package_label,
            "full_label": self.full_label  # Added FullPackageTag
        }
        self.test_results_ready.emit(test_results, package_info)
        self.finished.emit({"success": True})

# UnitWeightDialog class definition
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

# MetrcApp class definition
class MetrcApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Barkeep by Grissom")
        self.resize(1500, 1000)  # Increased size for better visibility

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
        self.tag_input.returnPressed.connect(self.search_test_results)  # Connect to search_test_results

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
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

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

        self.product_name = "Unknown Product"
        self.test_date = "N/A"
        self.expiration_date = "N/A"
        self.source_package_label_value = "N/A"

        self.approval_number = "N/A"
        self.strain_name = "N/A"
        self.product_description = "N/A"

        self.full_package_tag = "N/A"        # **New Variable for FullPackageTag**
        self.license_selected = "N/A"        # **New Variable for LicenseSelected**

        self.terpenes_data = []

        self.cannabinoid_values = {cannabinoid: "0.0" for cannabinoid in INDIVIDUAL_CANNABINOIDS}

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
                padding: 6px;
                border-radius: 4px;
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
                padding: 6px;
                border: none;
            }
        """)

    def add_one_year(self, date_str):
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        new_date = date_obj + relativedelta(years=1)
        return new_date.strftime("%m/%d/%Y")  # Change to MM/DD/YYYY format

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

            self.cannabinoid_values = self.extract_cannabinoid_values(test_results)
            self.export_button.setEnabled(True)

            self.full_package_tag = package_info.get("full_label", "N/A")
            self.license_selected = self.license_combo.currentText()

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
            self.export_results_to_json(
                self.product_name,
                self.test_date,
                self.expiration_date,
                self.source_package_label_value,
                unit_weight,
                num_labels,
                self.approval_number,
                self.product_description,
                self.strain_name
            )
            QMessageBox.information(self, "Export Complete", "Data exported to current_results.json.")
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
        return new_date.strftime("%m/%d/%Y")  # Change to MM/DD/YYYY format, no timestamp

    def extract_cannabinoid_values(self, results):
        cannabinoid_values = {cannabinoid: "0.0" for cannabinoid in INDIVIDUAL_CANNABINOIDS}
        
        for r in results:
            test_type = r.get("TestTypeName", "")
            result_level = r.get("TestResultLevel", "N/A")
            units = self.extract_units(test_type)
            
            if test_type in INDIVIDUAL_CANNABINOIDS:
                if isinstance(result_level, str):
                    if result_level.lower() != "n/a":
                        try:
                            value = float(result_level)
                            if value > 0:
                                cannabinoid_values[test_type] = f"{round(value, 2)}{units}" if units else f"{round(value, 2)}"
                            else:
                                cannabinoid_values[test_type] = "0.0"
                        except ValueError:
                            cannabinoid_values[test_type] = result_level
                elif isinstance(result_level, (int, float)):
                    if result_level > 0:
                        cannabinoid_values[test_type] = f"{round(result_level, 2)}{units}" if units else f"{round(result_level, 2)}"
                    else:
                        cannabinoid_values[test_type] = "0.0"
                else:
                    cannabinoid_values[test_type] = "0.0"
        
        return cannabinoid_values

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

        final_results = []
        for r in filtered_results:
            concentration = r.get("TestResultLevel", "N/A")
            if isinstance(concentration, str):
                if concentration.lower() != "n/a":
                    try:
                        val = float(concentration)
                        if val == 0.0:
                            continue  # skip zero values
                    except ValueError:
                        pass
                    final_results.append(r)
            elif isinstance(concentration, (int, float)):
                if concentration != 0:
                    final_results.append(r)

        if not final_results:
            self.terpenes_table.setRowCount(0)
            self.terpenes_data = []  # Clear Stored Terpenes Data
            return

        try:
            sorted_results = sorted(
                final_results,
                key=lambda x: float(x.get("TestResultLevel", 0)) if isinstance(x.get("TestResultLevel", 0), (int, float, str)) and str(x.get("TestResultLevel", 0)).replace('.', '', 1).isdigit() else 0,
                reverse=True
            )
        except ValueError:
            sorted_results = final_results

        self.terpenes_data = sorted_results

        self.terpenes_table.setRowCount(len(sorted_results))
        
        for i, result in enumerate(sorted_results):
            original_test_type = result.get("TestTypeName", "N/A")
            units = self.extract_units(original_test_type)
            
            display_name = re.sub(r"\(.*?\)", "", original_test_type).strip()
            display_name = display_name.replace("Mandatory Terpenes", "").strip()
            display_name = display_name.replace("Alpha-", "a-")
            display_name = display_name.replace("Beta-", "b-")

            status = "Passed" if result.get("TestPassed", False) else "Failed"
            concentration = result.get("TestResultLevel", "N/A")
            test_date = result.get("TestPerformedDate", "N/A")

            if isinstance(concentration, str):
                if concentration.lower() != "n/a":
                    try:
                        # Round the concentration to the nearest hundredth
                        concentration_display = f"{round(float(concentration), 2)}%"
                    except ValueError:
                        concentration_display = str(concentration)
                else:
                    concentration_display = str(concentration)
            elif isinstance(concentration, (int, float)):
                # Round the concentration to the nearest hundredth
                concentration_display = f"{round(concentration, 2)}%"
            else:
                concentration_display = "N/A"
            
            self.terpenes_table.setItem(i, 0, QTableWidgetItem(display_name))
            self.terpenes_table.setItem(i, 1, QTableWidgetItem(status))
            self.terpenes_table.setItem(i, 2, QTableWidgetItem(concentration_display))
            self.terpenes_table.setItem(i, 3, QTableWidgetItem(test_date))

        self.terpenes_table.resizeColumnsToContents()

    def simplify_cannabinoid_name(self, test_type):
        test_type = test_type.replace("Raw Plant Material & PreRolls", "")
        test_type = test_type.replace("Mandatory Cannabinoid % and Totals", "")
        test_type = test_type.replace("Vapes & Concentrates", "")
        test_type = test_type.replace("Infused Plant Material & PreRolls", "")  # Added line to remove "Infused Plant Material & PreRolls"
        return test_type.strip()

    def export_results_to_json(
        self, product_name, test_date, expiration_date,
        source_package_label, unit_weight, num_labels,
        approval_number, product_description, strain_name
    ):
        filename = "current_results.json"

        # **Define the dictionary structure for exporting data**
        export_data = {
            "ApprovalNumber": approval_number,
            "ProductDescription": product_description,
            "StrainName": strain_name,
            "ProductName": product_name,
            "FullPackageTag": self.full_package_tag,
            "LicenseSelected": self.license_selected,
            "Cannabinoids": {},
            "TestDate": test_date,
            "ExpirationDate": expiration_date,
            "SourcePackage": source_package_label,
            "UnitWeight": unit_weight,
            "NumLabels": num_labels,
            "TestingFacility": "TES000011",  # Placeholder, can be updated if necessary
            "Terpenes": []  # Will contain a list of terpene details
        }

        # **Add the cannabinoid values to the dictionary**
        for cannabinoid in INDIVIDUAL_CANNABINOIDS:
            value = self.cannabinoid_values.get(cannabinoid, "0.0")
            export_data["Cannabinoids"][cannabinoid] = value

        # **Concatenate Terpenes into a list of dictionaries**
        if self.terpenes_data:
            terpenes_list = []
            for terpene in self.terpenes_data:
                terpene_name = terpene.get("TestTypeName", "N/A")
                concentration = terpene.get("TestResultLevel", "N/A")
                # Clean terpene name and format concentration
                terpene_name = re.sub(r"\s*\(.*?\)", "", terpene_name).strip()
                terpene_name = terpene_name.replace("Mandatory Terpenes", "").strip()
                if isinstance(concentration, str):
                    if concentration.lower() != "n/a":
                        try:
                            concentration = round(float(concentration), 2)  # Round to the nearest hundredth
                            concentration_display = f"{concentration}%"
                        except ValueError:
                            concentration_display = concentration
                    else:
                        concentration_display = concentration
                elif isinstance(concentration, (int, float)):
                    concentration_display = f"{round(concentration, 2)}%"  # Round to the nearest hundredth
                else:
                    concentration_display = "N/A"

                if concentration_display != "N/A":
                    terpenes_list.append({
                        "Name": terpene_name,
                        "Concentration": concentration_display
                    })

            # Sort terpenes list in descending order of concentration
            terpenes_list.sort(key=lambda x: float(x["Concentration"].replace('%', '')) if x["Concentration"] != "N/A" else 0, reverse=True)
            export_data["Terpenes"] = terpenes_list
        else:
            export_data["Terpenes"] = "N/A"

        # **Write the data to a JSON file**
        with open(filename, "w", encoding="utf-8") as jsonfile:
            json.dump(export_data, jsonfile, ensure_ascii=False, indent=4)

        self.log_message(f"Exported results to {filename}. Bartender can now use this file.")

# Main function
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
