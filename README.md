# Barkeep by Grissom

**Barkeep by Grissom** is a proprietary application designed to streamline cannabis package testing data retrieval and label generation. This software integrates directly with the METRC API to pull lab testing results, process data efficiently, and export it to a CSV file compatible with Bartender Barcode Printing software. The application is built using Python and PyQt5 for an intuitive graphical interface.

---

## Features

- **License-Based Package Lookup:** Query packages using partial tags under multiple licenses.
- **Dynamic Data Retrieval:** Fetch lab test results for cannabinoids, terpenes, expiration dates, source packages, and more via METRC API integration.
- **Customizable Results Filtering:** Only display relevant and meaningful test results, filtering unnecessary data.
- **CSV Export for Label Printing:** Seamlessly export test results and package details into a pre-configured CSV file for use with Bartender Barcode Printing.
- **Unit Weight Customization:** Prompt users for unit weight and number of labels before exporting data.
- **User-Friendly Interface:** Simple, clean, and professionally styled UI with progress tracking and error handling.

---

## Requirements

### System
- **Operating System:** Windows (preferred for Bartender Barcode Printing compatibility)
- **Python Version:** Python 3.8 or higher

### Libraries
Ensure the following Python libraries are installed:
- `PyQt5`
- `requests`
- `python-dotenv`
- `dateutil`
- `logging`

To install dependencies, run:
```bash
pip install PyQt5 requests python-dotenv python-dateutil
```

---

## Setup Instructions

1. **Clone or Download Repository**
   - Clone the repository or download the project files into a folder of your choice.

2. **Set Up Environment Variables**
   - Create a `.env` file in the project root with the following variables:
     ```plaintext
     VENDOR_API_KEY=your_vendor_api_key
     USER_API_KEY=your_user_api_key
     ```
   - Replace `your_vendor_api_key` and `your_user_api_key` with valid credentials for accessing the METRC API.

3. **Install Dependencies**
   - Run the following command in the project directory:
     ```bash
     pip install -r requirements.txt
     ```

4. **Run the Application**
   - Launch the application by running:
     ```bash
     python main.py
     ```

5. **Using the Application**
   - Select the license, enter the partial package tag, and click "Search" or press "Enter."
   - Review fetched data for cannabinoids, terpenes, and other package details.
   - Click "Export" to save the results as a CSV file for Bartender Barcode Printing.

---

## Exported CSV Structure

The exported CSV file (`current_results.csv`) contains the following fields:

| Column             | Description                                    |
|--------------------|------------------------------------------------|
| ApprovalNumber     | The approval number of the package.            |
| ProductDescription | The product description (e.g., Vape, Flower).  |
| StrainName         | The strain name of the product.                |
| ProductName        | Full name of the product.                      |
| THCResult          | THC concentration and unit.                    |
| CBDResult          | CBD concentration and unit.                    |
| TestDate           | Date the lab tests were performed.             |
| ExpirationDate     | Calculated expiration date (1 year later).     |
| SourcePackage      | The package this product was derived from.     |
| UnitWeight         | Weight of the package unit (e.g., 3.5g).       |
| NumLabels          | Number of labels specified by the user.        |
| TestingFacility    | Predefined testing facility ID ("TES000011").  |

---

## Known Issues & Limitations

- This software is tied to METRC API limits. Users with high request volumes may encounter rate limits.
- Requires a stable internet connection to fetch data from METRC.
- Export file assumes compliance with Bartender Barcode Printing's CSV file format.

---

## Licensing & Proprietary Notice

**Barkeep by Grissom** is a proprietary software solution. Unauthorized use, distribution, or reproduction of this software is strictly prohibited.

This software is licensed solely to the user or organization purchasing it. Redistribution or modification for commercial purposes without prior written consent is a violation of this agreement.

For licensing inquiries, contact **[your email address]**.

---

## Support

For support or questions, contact dylan@robustmo.com
