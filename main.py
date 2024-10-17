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
        # Add commas between certain known field patterns
        text = re.sub(r'(CERTIFICATE OF ANALYSIS)', r'\1,', text)
        text = re.sub(r'(PRODUCED: \w+ \d{1,2}, \d{4})', r'\1,', text)
        text = re.sub(r'(SAMPLE: [\w\s\-]+)', r'\1,', text)
        text = re.sub(r'(BATCH: \w+)', r'\1,', text)
        text = re.sub(r'(CANNABINOID PROFILE BY UPLC-UV)', r'\1,', text)
        text = re.sub(r'(TOTAL CBD = \( CBDA X 0\.877 \) \+ CBD)', r'\1,', text)
        text = re.sub(r'(TOTAL THC = \( THCA X 0\.877 \) \+ THC)', r'\1,', text)
        text = re.sub(r'(DRY-WEIGHT AMOUNTS SHOWN)', r'\1,', text)
        text = re.sub(r'(MOISTURE CONTENT BY MOISTURE BALANCE)', r'\1,', text)
        text = re.sub(r'(WATER ACTIVITY BY HYGROMETER)', r'\1,', text)
        text = re.sub(r'(PASS)', r'\1,', text)
        # Add other known field delimiters here as needed
        return text

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
