# METRC Package Testing Results Application

## Overview
A Python application to search for active METRC packages by license and partial tag number, displaying testing results in a user-friendly interface.

## Prerequisites
- Python 3.7 or later
- `PyQt5` and `requests` libraries

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/metrc-app.git
   cd metrc-app
   ```

2. Install dependencies:
   ```bash
   pip install PyQt5 requests
   ```

3. Update API keys in `metrc_api.py`.

## Usage
Run the application:
```bash
python main.py
```

1. Select a license (`CUL000032` or `MAN000035`).
2. Enter a partial tag number.
3. View testing results in the table.

## Notes
- Ensure internet connectivity for API requests.
- Respect API rate limits.

## License
MIT

