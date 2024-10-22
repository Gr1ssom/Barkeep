import re
import sys
import fitz  # PyMuPDF
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QFileDialog, QLabel, QVBoxLayout


class PDFToFormattedTextConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        # GUI layout
        layout = QVBoxLayout()
        
        self.label = QLabel("Select a PDF file to convert")
        layout.addWidget(self.label)
        
        self.openButton = QPushButton('Open PDF', self)
        self.openButton.clicked.connect(self.open_pdf)
        layout.addWidget(self.openButton)
        
        self.convertButton = QPushButton('Convert and Format Text for BarTender', self)
        self.convertButton.clicked.connect(self.convert_to_formatted_text)
        self.convertButton.setEnabled(False)  # Disable until PDF is loaded
        layout.addWidget(self.convertButton)
        
        self.setLayout(layout)
        self.setWindowTitle('PDF to Formatted Text Converter')
        self.setGeometry(300, 300, 400, 200)
    
    def open_pdf(self):
        # File dialog to open PDF
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open PDF File", "", "PDF Files (*.pdf);;All Files (*)", options=options)
        if file_name:
            self.label.setText(f"Selected PDF: {file_name}")
            self.pdf_path = file_name
            self.convertButton.setEnabled(True)
    
    def extract_data(self, pdf_path):
        # Use PyMuPDF to extract text from PDF
        doc = fitz.open(pdf_path)
        text_data = []

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)  # Load a page
            text = page.get_text("text")    # Extract plain text

            # Remove extra spaces between letters using regex
            cleaned_text = re.sub(r'(?<=\w)\s(?=\w)', '', text)

            text_data.append(cleaned_text)
        
        return text_data

    def format_for_bartender(self, text):
        # Extract important fields and format them as CSV-style output

        # Extracting the fields like Batch Number, Testing Tag, Cannabinoid Results
        batch_number = re.search(r'BATCH\s+NO\s*:\s*(\d+)', text)
        testing_tag = re.search(r'METRC\s+SRC\s+TAG\s*:\s*([\w\d]+)', text)
        total_thc = re.search(r'TOTAL\s+THC\s*=\s*\(\s*THCA\s*X\s*0\.877\s*\)\s*\+\s*THC', text)
        total_cbd = re.search(r'TOTAL\s+CBD\s*=\s*\(\s*CBDA\s*X\s*0\.877\s*\)\s*\+\s*CBD', text)

        # Test results by analytes (just an example for structure)
        analyte_results = re.findall(r'(\w+)\s*(PASS|FAIL)', text)

        # Start formatting the output
        formatted_data = []
        
        # Add headers first
        formatted_data.append("Batch Number, Testing Tag, Total THC, Total CBD, Analyte, Result")

        # Add batch number and testing tag
        if batch_number and testing_tag:
            formatted_data.append(f"{batch_number.group(1)}, {testing_tag.group(1)}, ")

        # Add cannabinoid profile data (THC, CBD)
        if total_thc:
            formatted_data[-1] += f"{total_thc.group(0)}, "
        else:
            formatted_data[-1] += "N/A, "
        
        if total_cbd:
            formatted_data[-1] += f"{total_cbd.group(0)}, "
        else:
            formatted_data[-1] += "N/A, "

        # Add test results (e.g., Pass/Fail for each analyte)
        for analyte, result in analyte_results:
            formatted_data.append(f", , , , {analyte}, {result}")

        return "\n".join(formatted_data)

    def convert_to_formatted_text(self):
        # Extract data from PDF
        data = self.extract_data(self.pdf_path)
        
        # Save dialog for formatted text
        options = QFileDialog.Options()
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Formatted Text File", "", "Text Files (*.txt);;All Files (*)", options=options)
        
        if save_path:
            # Write the formatted text data for BarTender
            with open(save_path, mode='w', encoding='utf-8') as file:
                for line in data:
                    formatted_text = self.format_for_bartender(line)
                    file.write(formatted_text + "\n")
            
            self.label.setText(f"Formatted text saved at: {save_path}")
        else:
            self.label.setText("Save canceled.")
        

def main():
    # Main entry point for the application
    app = QApplication(sys.argv)
    ex = PDFToFormattedTextConverter()
    ex.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
