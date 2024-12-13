import os
import requests
import logging
from logging.handlers import RotatingFileHandler
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Set up logging to a file called debug.log with rotation
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

handler = RotatingFileHandler("debug.log", maxBytes=5*1024*1024, backupCount=2)  # 5MB per file
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)
logger.addHandler(handler)

API_BASE = "https://api-mo.metrc.com"

API_KEY = os.getenv("VENDOR_API_KEY")
USER_KEY = os.getenv("USER_API_KEY")

# Prefixes used to construct full package labels from partial tags
PREFIXES = {
    "MAN000035": "1A40C03000043950000",
    "CUL000032": "1A40C030000332D0000"
}

def get_package_id(license_code: str, full_label: str):
    """
    Given a license code and a full package label, retrieve the package details 
    from Metrc and return the packageId (numeric ID).
    Endpoint: GET /packages/v2/{packageLabel}?licenseNumber={licenseNumber}
    """
    endpoint = f"{API_BASE}/packages/v2/{full_label}?licenseNumber={license_code}"
    logging.info("Requesting package details from: %s", endpoint)

    try:
        response = requests.get(endpoint, auth=HTTPBasicAuth(API_KEY, USER_KEY))
    except requests.RequestException as e:
        logging.exception("Network error while contacting Metrc API for package details: %s", e)
        return None

    if response.status_code == 200:
        logging.debug("Successful response received for packageLabel=%s", full_label)
        try:
            package_data = response.json()
            logging.debug("Package Data JSON: %s", package_data)  # Log the raw JSON

            # Extract packageId
            if isinstance(package_data, dict):
                package_id = package_data.get("Id")
                if package_id:
                    logging.debug("Found packageId=%s for label=%s", package_id, full_label)
                    return package_id
                else:
                    logging.error("packageId not found in the response for label=%s", full_label)
                    return None
            else:
                logging.error("Unexpected JSON structure for package details: %s", package_data)
                return None
        except ValueError:
            logging.error("Invalid JSON response for packageLabel=%s: %s", full_label, response.text)
            return None
    else:
        logging.error(
            "Error %d from Metrc API for packageLabel=%s: %s", 
            response.status_code, full_label, response.text
        )
        return None

def get_test_results(license_code: str, package_id: int, page_number=1, page_size=10):
    """
    Given a license code and a packageId, retrieve the lab test results from Metrc.
    Endpoint: GET /labtests/v2/results?licenseNumber={licenseNumber}&packageId={packageId}&pageNumber={pageNumber}&pageSize={pageSize}
    Returns:
        A list of test result dicts or None if an error occurred.
    """
    endpoint = (
        f"{API_BASE}/labtests/v2/results?"
        f"licenseNumber={license_code}&"
        f"packageId={package_id}&"
        f"pageNumber={page_number}&"
        f"pageSize={page_size}"
    )
    logging.info("Requesting test results from: %s", endpoint)

    try:
        response = requests.get(endpoint, auth=HTTPBasicAuth(API_KEY, USER_KEY))
    except requests.RequestException as e:
        logging.exception("Network error while contacting Metrc API for test results: %s", e)
        return None

    if response.status_code == 200:
        logging.debug("Successful response received for packageId=%s", package_id)
        try:
            test_results = response.json()
            logging.debug("Test Results JSON: %s", test_results)  # Log the raw JSON

            # Extract the list of test results from the "Data" key
            if isinstance(test_results, dict) and "Data" in test_results:
                return test_results["Data"]
            elif isinstance(test_results, list):
                return test_results
            else:
                logging.error("Unexpected JSON structure for test results: %s", test_results)
                return None
        except ValueError:
            logging.error("Invalid JSON response for packageId=%s: %s", package_id, response.text)
            return None
    else:
        logging.error(
            "Error %d from Metrc API for packageId=%s: %s", 
            response.status_code, package_id, response.text
        )
        return None
